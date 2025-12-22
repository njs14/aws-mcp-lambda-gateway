"""
MCP Gateway - Proxy with Cognito JWT auth and MCP OAuth discovery.

Implements:
- RFC 9728: OAuth 2.0 Protected Resource Metadata
- MCP Authorization Spec (2025-06-18)
"""

import json
import os
import time
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
from jose import jwt, JWTError

# Config
ALLOWED_SERVERS: dict = json.loads(os.environ.get("ALLOWED_SERVERS", "{}"))
COGNITO_ISSUER = os.environ.get("COGNITO_ISSUER", "")
COGNITO_AUDIENCE = os.environ.get("COGNITO_AUDIENCE", "")
COGNITO_DOMAIN = os.environ.get("COGNITO_DOMAIN", "")  # e.g., mcp-gateway-xxx.auth.us-east-1.amazoncognito.com
GATEWAY_URL = os.environ.get("GATEWAY_URL", "")  # CloudFront URL
JWKS_URL = f"{COGNITO_ISSUER}/.well-known/jwks.json"

STRIP_REQUEST_HEADERS = {"host", "x-forwarded-for", "x-forwarded-proto", "x-amzn-trace-id", "authorization"}
STRIP_RESPONSE_HEADERS = {"transfer-encoding", "connection", "keep-alive"}

app = FastAPI(title="MCP Gateway", docs_url=None, redoc_url=None)
security = HTTPBearer(auto_error=False)

_jwks_cache: dict = {}
_jwks_fetched_at: float = 0


def log_audit(event: str, **kwargs):
    print(json.dumps({"event": event, "ts": time.time(), **kwargs}))


async def get_jwks() -> dict:
    global _jwks_cache, _jwks_fetched_at
    if time.time() - _jwks_fetched_at < 3600 and _jwks_cache:
        return _jwks_cache
    async with httpx.AsyncClient() as client:
        resp = await client.get(JWKS_URL, timeout=5)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        _jwks_fetched_at = time.time()
    return _jwks_cache


def get_signing_key(token: str, jwks: dict) -> dict:
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    raise JWTError(f"Key {kid} not found in JWKS")


@app.get("/health")
async def health():
    return {"status": "ok", "servers": list(ALLOWED_SERVERS.keys())}


# RFC 9728: OAuth 2.0 Protected Resource Metadata
@app.get("/.well-known/oauth-protected-resource")
async def oauth_protected_resource():
    """Tell MCP clients where to authenticate."""
    return JSONResponse({
        "resource": GATEWAY_URL,
        "authorization_servers": [f"https://{COGNITO_DOMAIN}"],
        "scopes_supported": ["openid", "email", "profile"],
        "bearer_methods_supported": ["header"],
        "resource_documentation": f"{GATEWAY_URL}/health"
    })


def build_www_authenticate() -> str:
    """Build WWW-Authenticate header per MCP spec."""
    resource_metadata_url = f"{GATEWAY_URL}/.well-known/oauth-protected-resource"
    return f'Bearer realm="{GATEWAY_URL}", resource_metadata="{resource_metadata_url}"'


async def validate_jwt_with_challenge(creds: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> dict:
    """Validate JWT, return proper WWW-Authenticate on failure."""
    www_auth = build_www_authenticate()
    
    if not creds:
        log_audit("auth_failure", reason="missing_token")
        raise HTTPException(
            status_code=401,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": www_auth}
        )
    
    token = creds.credentials
    try:
        jwks = await get_jwks()
        signing_key = get_signing_key(token, jwks)
        
        claims = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            issuer=COGNITO_ISSUER,
            options={"require_exp": True, "verify_aud": False}
        )
        
        if claims.get("client_id") != COGNITO_AUDIENCE and claims.get("aud") != COGNITO_AUDIENCE:
            raise JWTError("Invalid audience/client_id")
        
        return claims
    except JWTError as e:
        log_audit("auth_failure", reason="invalid_token", error=str(e))
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token: {e}",
            headers={"WWW-Authenticate": www_auth}
        )
    except httpx.HTTPError as e:
        log_audit("auth_failure", reason="jwks_fetch_failed", error=str(e))
        raise HTTPException(status_code=503, detail="Unable to validate token")


@app.api_route("/mcp/{server_name}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def proxy_mcp(server_name: str, path: str, request: Request, claims: dict = Depends(validate_jwt_with_challenge)):
    start = time.time()
    user = claims.get("sub", claims.get("username", "unknown"))
    
    if server_name not in ALLOWED_SERVERS:
        log_audit("mcp_request", server=server_name, status="blocked", user=user)
        raise HTTPException(403, f"Server '{server_name}' not in allowlist")
    
    upstream_url = f"{ALLOWED_SERVERS[server_name]}/{path}"
    headers = {k: v for k, v in request.headers.items() if k.lower() not in STRIP_REQUEST_HEADERS}
    headers["X-Forwarded-User"] = user
    body = await request.body()
    
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            if "text/event-stream" in request.headers.get("accept", ""):
                async def stream():
                    async with client.stream(request.method, upstream_url, headers=headers, content=body, params=request.query_params) as resp:
                        async for chunk in resp.aiter_bytes():
                            yield chunk
                log_audit("mcp_request", server=server_name, path=path, status="streaming", user=user)
                return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})
            else:
                resp = await client.request(request.method, upstream_url, headers=headers, content=body, params=request.query_params)
                log_audit("mcp_request", server=server_name, path=path, status=resp.status_code, user=user, latency_ms=round((time.time()-start)*1000, 2))
                resp_headers = {k: v for k, v in resp.headers.items() if k.lower() not in STRIP_RESPONSE_HEADERS}
                return JSONResponse(content=resp.json() if "application/json" in resp.headers.get("content-type", "") else resp.text, status_code=resp.status_code, headers=resp_headers)
    except httpx.TimeoutException:
        log_audit("mcp_request", server=server_name, status="timeout", user=user)
        raise HTTPException(504, "Upstream timeout")
    except httpx.HTTPError as e:
        log_audit("mcp_request", server=server_name, status="error", user=user, error=str(e))
        raise HTTPException(502, f"Upstream error: {e}")
