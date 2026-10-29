"""
Mock Identity Provider (OIDC & OAuth 2.0 Authorization Server).

Provides RFC 8414 Authorization Server Metadata, RFC 7517 JWKS Key Set,
RFC 7662 Token Introspection, and OAuth 2.0 token issuance endpoints.
Used inside test-bed container stack or in-memory testing.
"""

import time
import json
from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import jwt

# Generate persistent RSA keypair for mock IdP
_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_public_key = _private_key.public_key()
_public_numbers = _public_key.public_numbers()

def int_to_base64url(n: int) -> str:
    import base64
    b = n.to_bytes((n.bit_length() + 7) // 8, byteorder="big")
    return base64.urlsafe_b64encode(b).decode("utf-8").rstrip("=")

_kid = "test-key-2026-01"
_jwks = {
    "keys": [
        {
            "kty": "RSA",
            "use": "sig",
            "alg": "RS256",
            "kid": _kid,
            "n": int_to_base64url(_public_numbers.n),
            "e": int_to_base64url(_public_numbers.e),
        }
    ]
}

def mint_token(
    sub: str = "test-admin@corp.example.com",
    scope: str = "sp:admin sp:operator",
    exp_delta: int = 3600,
    issuer: str = "http://localhost:8080/realms/mcp-test",
    audience: str = "sp-mcp-server",
    kid: str = _kid,
    private_key=_private_key,
) -> str:
    now = int(time.time())
    payload = {
        "sub": sub,
        "iss": issuer,
        "aud": audience,
        "iat": now,
        "exp": now + exp_delta,
        "scope": scope,
        "authmodel": "oidc_bearer",
    }
    return jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": kid})

async def openid_configuration(request):
    base_url = str(request.base_url).rstrip("/")
    return JSONResponse({
        "issuer": f"{base_url}/realms/mcp-test",
        "authorization_endpoint": f"{base_url}/realms/mcp-test/protocol/openid-connect/auth",
        "token_endpoint": f"{base_url}/realms/mcp-test/protocol/openid-connect/token",
        "jwks_uri": f"{base_url}/realms/mcp-test/protocol/openid-connect/certs",
        "introspection_endpoint": f"{base_url}/realms/mcp-test/protocol/openid-connect/token/introspect",
        "response_types_supported": ["code", "token"],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ["RS256"],
        "scopes_supported": ["openid", "profile", "email", "sp:admin", "sp:operator", "sp:readonly"],
        "code_challenge_methods_supported": ["S256"],
    })

async def jwks_endpoint(request):
    return JSONResponse(_jwks)

async def token_introspection(request):
    form = await request.form()
    token = form.get("token")
    if not token:
        return JSONResponse({"active": False})
    try:
        payload = jwt.decode(token, _public_key, algorithms=["RS256"], options={"verify_aud": False})
        return JSONResponse({
            "active": True,
            "sub": payload.get("sub"),
            "scope": payload.get("scope", ""),
            "exp": payload.get("exp"),
            "client_id": "test-mcp-client",
        })
    except Exception:
        return JSONResponse({"active": False})

routes = [
    Route("/.well-known/openid-configuration", openid_configuration),
    Route("/realms/mcp-test/.well-known/openid-configuration", openid_configuration),
    Route("/realms/mcp-test/protocol/openid-connect/certs", jwks_endpoint),
    Route("/realms/mcp-test/protocol/openid-connect/token/introspect", token_introspection, methods=["POST"]),
]

app = Starlette(routes=routes)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
