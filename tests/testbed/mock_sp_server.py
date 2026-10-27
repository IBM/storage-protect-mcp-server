"""
Mock IBM Storage Protect TCP Socket Daemon Emulator.

Listens on TCP port 1500 (or configured port) to emulate IBM Storage Protect
server socket behavior for network layer resilience tests and test-bed execution.
"""

import socket
import threading
import sys
import os

PORT = int(os.environ.get("SP_SERVER_PORT", 1500))

def handle_client(conn, addr):
    try:
        data = conn.recv(1024)
        if not data:
            return
        # Basic SP handshake banner
        banner = b"IBM Storage Protect Server Version 8.1.18.000\r\nSESSIONSECURITY=STRICT\r\nOK\r\n"
        conn.sendall(banner)
    except Exception:
        pass
    finally:
        conn.close()

def run_server(port=PORT):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", port))
    server.listen(128)
    print(f"Mock SP Server listening on port {port}")
    try:
        while True:
            conn, addr = server.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
    except KeyboardInterrupt:
        pass
    finally:
        server.close()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    run_server(port)
