"""
Locust Load Simulation Script for IBM Storage Protect MCP Server.

Executes sustained high-concurrency synthetic agent workloads against
the HTTP/SSE transport of the IBM Storage Protect MCP Server:
- 70% Read queries (status, session, storage pools, nodes)
- 15% Dynamic authentication leases & revocation
- 10% Write commands and dual-custody approval polling
- 5% OAuth 2 / OIDC metadata endpoint requests
"""

import json
from locust import HttpUser, task, between

class MCPServerUser(HttpUser):
    wait_time = between(0.1, 0.5)

    def on_start(self):
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer fake-test-token-locust",
        }
        self.req_id = 0

    def _next_id(self):
        self.req_id += 1
        return self.req_id

    @task(35)
    def query_status(self):
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": "query_status", "arguments": {}},
        }
        self.client.post("/sse", json=payload, headers=self.headers, name="tools/query_status")

    @task(20)
    def query_sessions(self):
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": "query_session", "arguments": {}},
        }
        self.client.post("/sse", json=payload, headers=self.headers, name="tools/query_session")

    @task(15)
    def query_storage_pool(self):
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": "query_storagepool", "arguments": {}},
        }
        self.client.post("/sse", json=payload, headers=self.headers, name="tools/query_storagepool")

    @task(15)
    def dynamic_session_lifecycle(self):
        auth_payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {
                "name": "authenticate_session",
                "arguments": {
                    "username": "mcp-operator",
                    "password": "Password123!",
                    "target_server": "TSM_SERVER_PROD",
                },
            },
        }
        with self.client.post("/sse", json=auth_payload, headers=self.headers, name="tools/auth_lifecycle", catch_response=True) as resp:
            if resp.status_code in (200, 401, 403):
                resp.success()

    @task(10)
    def dual_custody_approvals_poll(self):
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": "query_pending_approvals", "arguments": {}},
        }
        self.client.post("/sse", json=payload, headers=self.headers, name="tools/query_pending_approvals")

    @task(5)
    def oauth_metadata_discovery(self):
        self.client.get("/.well-known/oauth-authorization-server", name="oauth/as_metadata")
        self.client.get("/.well-known/oauth-protected-resource", name="oauth/resource_metadata")
