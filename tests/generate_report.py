#!/usr/bin/env python3
"""
Allure Test Execution and Report Generation Utility.

This script executes the pytest test automation suite, records Allure test results,
and compiles the standalone Allure HTML report.

Usage:
    python tests/generate_report.py [optional pytest args...]

Examples:
    python tests/generate_report.py
    python tests/generate_report.py tests/test_sec_oauth2.py
    python tests/generate_report.py -k "oauth2"
    python tests/generate_report.py --serve
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "allure-results"
REPORT_DIR = PROJECT_ROOT / "allure-report"


def setup_allure_metadata(results_dir: Path) -> None:
    """Inject environment metadata and defect categories into the results directory."""
    results_dir.mkdir(parents=True, exist_ok=True)

    # 1. environment.properties
    env_file = results_dir / "environment.properties"
    env_content = (
        f"Platform={sys.platform}\n"
        f"Python.Version={sys.version.split()[0]}\n"
        "Project=ibm-storage-protect-mcp-server\n"
        "TestFramework=pytest-allure\n"
        "SecurityControls=OA-8,DAUTH-10,DAUTH-11,ACC-3,POL-4,NET-1,RG-1,CRED-3\n"
        "Vulnerabilities=VUL0790479,VUL0790697\n"
    )
    env_file.write_text(env_content, encoding="utf-8")

    # 2. categories.json
    categories_file = results_dir / "categories.json"
    categories = [
        {
            "name": "Security Authorization Denials",
            "matchedStatuses": ["failed"],
            "messageRegex": ".*AUTHORIZATION_DENIED.*|.*AUTHENTICATION_REQUIRED.*|.*Forbidden.*",
        },
        {
            "name": "Platform Compatibility Skips",
            "matchedStatuses": ["skipped"],
            "messageRegex": ".*POSIX.*",
        },
    ]
    categories_file.write_text(json.dumps(categories, indent=2), encoding="utf-8")


def run_tests_and_generate_report(args=None) -> int:
    """Run pytest with Allure results and generate the HTML report."""
    if args is None:
        args = sys.argv[1:]

    serve_requested = False
    if "--serve" in args:
        serve_requested = True
        args = [a for a in args if a != "--serve"]

    # Ensure PYTHONPATH includes src
    env = os.environ.copy()
    src_dir = str(PROJECT_ROOT / "src")
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{src_dir}{os.pathsep}{existing_pythonpath}" if existing_pythonpath else src_dir

    pytest_cmd = [
        sys.executable,
        "-m",
        "pytest",
        f"--alluredir={RESULTS_DIR}",
        "--clean-alluredir",
    ]
    if args:
        pytest_cmd.extend(args)
    else:
        pytest_cmd.append("tests")

    print(f"==> Running test suite: {' '.join(pytest_cmd)}")
    result = subprocess.run(pytest_cmd, cwd=str(PROJECT_ROOT), env=env)

    # Populate environment metadata and categories in allure-results
    setup_allure_metadata(RESULTS_DIR)

    # Generate Allure HTML report
    allure_bin = shutil.which("allure")
    if not allure_bin:
        print("\n[WARNING] 'allure' command-line binary not found in PATH.")
        print(f"Allure results have been generated in: {RESULTS_DIR}")
        print("To generate the HTML report manually, install Allure CLI and run:")
        print(f"    allure generate {RESULTS_DIR} -o {REPORT_DIR} --clean")
        return result.returncode

    print(f"\n==> Compiling Allure HTML report from {RESULTS_DIR} -> {REPORT_DIR}...")
    gen_cmd = [allure_bin, "generate", str(RESULTS_DIR), "-o", str(REPORT_DIR), "--clean"]
    gen_res = subprocess.run(gen_cmd, shell=(sys.platform == "win32"), capture_output=True, text=True)

    if gen_res.returncode == 0:
        index_html = REPORT_DIR / "index.html"
        print("==> Allure report generated successfully!")
        print(f"    Report Index: {index_html.as_uri()}")
        if serve_requested:
            print("\n==> Starting Allure report server...")
            subprocess.run([allure_bin, "open", str(REPORT_DIR)], shell=(sys.platform == "win32"))
    else:
        print(f"[ERROR] Allure report generation failed:\n{gen_res.stderr}")

    return result.returncode


if __name__ == "__main__":
    sys.exit(run_tests_and_generate_report())
