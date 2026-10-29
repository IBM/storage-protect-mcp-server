#!/usr/bin/env python3
"""
Dynamic Fault Injection CLI Shim for IBM Storage Protect (dsmadmc).

Intercepts invocations of dsmadmc in the test-bed container or local testing environment.
Reads dynamic fault injection rules from a JSON config file (specified by
SP_FAULT_INJECTOR_CONFIG or /tmp/sp_fault_injection.json) to simulate:
- Process hangs / watchdog timeouts
- Error exit codes (ANS1017E, ANS1025E, ANS1353E, ANR2017E, etc.)
- Corrupted outputs
- Simulated normal mock responses
"""

import sys
import os
import json
import time

DEFAULT_CONFIG_PATH = os.environ.get("SP_FAULT_INJECTOR_CONFIG", "/tmp/sp_fault_injection.json")

def load_fault_rules():
    config_path = os.environ.get("SP_FAULT_INJECTOR_CONFIG", DEFAULT_CONFIG_PATH)
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("rules", [])
        except Exception as e:
            sys.stderr.write(f"Warning: could not parse fault injection config: {e}\n")
    return []

def main():
    args_str = " ".join(sys.argv[1:])
    rules = load_fault_rules()

    # Check for matching fault injection rule
    for rule in rules:
        match_cmd = rule.get("match_cmd", "")
        if match_cmd and (match_cmd.lower() in args_str.lower()):
            # Check for delay / hang injection
            delay = rule.get("delay_seconds", 0)
            if delay > 0:
                time.sleep(delay)

            # Check for process kill
            if rule.get("action") == "kill":
                sys.exit(137)

            stdout = rule.get("stdout", "")
            stderr = rule.get("stderr", "")
            exit_code = rule.get("exit_code", 0)

            if stdout:
                sys.stdout.write(stdout + "\n")
            if stderr:
                sys.stderr.write(stderr + "\n")
            sys.exit(exit_code)

    # Default fallback mock responses if no fault rule matched
    if "QUERY STATUS" in args_str.upper():
        sys.stdout.write(
            "IBM Storage Protect Server Version 8, Release 1, Level 18.0\n"
            "Server Name: TSM_SERVER_PROD\n"
            "Server Address: spsvr01.corp.example.com\n"
            "Server Port: 1500\n"
            "Session Security: STRICT\n"
        )
        sys.exit(0)
    elif "QUERY ADMIN" in args_str.upper():
        sys.stdout.write(
            "Administrator Name: MCP-SVC-SYSTEM\n"
            "System Privilege: Yes\n"
            "Policy Privilege: Yes\n"
            "Storage Privilege: Yes\n"
            "Operator Privilege: Yes\n"
            "Session Security: STRICT\n"
            "Days Since Last Access: 0\n"
            "Invalid Password Limit: 3\n"
        )
        sys.exit(0)
    elif "QUERY SESSION" in args_str.upper():
        sys.stdout.write(
            "Sess Number: 1042\n"
            "Comm. Method: Tcp/Ip\n"
            "Sess State: Idle\n"
            "Wait Time: 0 S\n"
            "Bytes Sent: 1.2 M\n"
            "Bytes Recvd: 450 K\n"
            "Sess Type: Admin\n"
            "Platform: Linux\n"
            "Client Name: MCP-SVC-SYSTEM\n"
            "Media Access Status:\n"
        )
        sys.exit(0)
    elif "QUERY OCCUPANCY" in args_str.upper():
        sys.stdout.write(
            "Node Name: APP_PROD_01\n"
            "Type: Bkup\n"
            "Filespace Name: /data\n"
            "Storage Pool Name: POOL_TIER1\n"
            "Number of Files: 15200\n"
            "Physical Space Occupied (MB): 45200.5\n"
            "Logical Space Occupied (MB): 45200.5\n"
        )
        sys.exit(0)
    elif "DEFINE SCRATCHPADENTRY" in args_str.upper():
        sys.stdout.write("ANR2000I DEFINE SCRATCHPADENTRY: Command accepted.\n")
        sys.exit(0)
    else:
        # Default success response
        sys.stdout.write("ANR2000I Command completed successfully.\n")
        sys.exit(0)

if __name__ == "__main__":
    main()
