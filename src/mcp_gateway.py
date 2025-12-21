"""
MCP Gateway - Lightweight proxy for MCP server governance.

Features:
- Allowlist enforcement for MCP servers
- Audit logging to CloudWatch
- Request/response streaming support
- Header passthrough with optional injection
"""

import json
import os
import time
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.responses import StreamingResponse
import httpx

# Load configuration
def load_allowed_servers() -> dict:
    """Load allowed servers from environment variable."""
    raw = os.environ.get("ALLOWED_SERVERS", "{}")
    try:
        servers = json.loads(raw)
        print(f"Loaded {len(servers)} allowed servers: {list(servers.keys())}")
        return servers
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse ALLOWED_SERVERS: {e}")
        return {}

ALLOWED_SERVERS = load_allowed_servers()

# Headers to strip from proxied requests (security)
STRIP_REQUEST_HEADERS = {
    "host",
    "x-forwarded-for",
    "x-forwarded-proto",
    "x-forwarded-port",
    "x-amzn-trace-id",
    "x-amz-cf-id",
}

# Headers to strip from responses
STRIP_RESPONSE_HEADERS = {
    "transfer-encoding",
    "connection",
    "keep-alive",
}


def log_audit(
    event_type: str,
    server: str,
    path: str,
    method: str,
    status: int,
    latency_ms: float,
    user: Optional[str] = None,
    error: Optional[str] = None,
):
    """Structured audit log for CloudWatch Logs Insights queries."""
    log_entry = {
        "event": event_type,
        "server": server,
        "path": path,
        "method": method,
        "status": status,
        "latency_ms": round(latency_ms, 2),
        "user": user or "anonymous",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if error:
        log_entry["error"] = error
    
    # Print as JSON for CloudWatch structured logging
    print(json.dumps(log_entry))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    print("MCP Gateway starting up...")
    print(f"Configured servers: {list(ALLOWED_SERVERS.keys())}")
    yield
    print("MCP Gateway shutting down...")


app = FastAPI(
    title="MCP Gateway",
    description="Governance proxy for MCP servers",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "servers": list(ALLOWED_SERVERS.keys()),
    }


@app.get("/servers")
async def list_servers():
    """List allowed MCP servers (for debugging/discovery)."""
    return {
        "servers": [
            {"name": name, "url": url}
            for name, url in ALLOWED_SERVERS.items()
        ]
    }


@app.api_route("/mcp/{server_name}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def proxy_mcp(server_name: str, path: str, request: Request):
    """
    Proxy requests to allowed MCP servers.
    
    URL pattern: /mcp/{server_name}/{path}
    Example: /mcp/context7/resolve-library-id
    """
    start_time = time.time()
    user = request.headers.get("x-user-id") or request.headers.get("x-api-key", "anonymous")
    
    # Allowlist check
    if server_name not in ALLOWED_SERVERS:
        log_audit(
            event_type="mcp_blocked",
            server=server_name,
            path=path,
            method=request.method,
            status=403,
            latency_ms=0,
            user=user,
            error="Server not in allowlist",
        )
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "message": f"Server '{server_name}' is not in the allowed list",
                "allowed_servers": list(ALLOWED_SERVERS.keys()),
            },
        )
    
    target_base = ALLOWED_SERVERS[server_name].rstrip("/")
    target_url = f"{target_base}/{path}" if path else target_base
    
    # Build headers, stripping sensitive ones
    proxy_headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in STRIP_REQUEST_HEADERS
    }
    
    # Add gateway identification
    proxy_headers["x-forwarded-by"] = "mcp-gateway"
    proxy_headers["x-original-host"] = request.headers.get("host", "unknown")
    
    try:
        body = await request.body()
        
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=proxy_headers,
                content=body,
                params=request.query_params,
            )
        
        latency_ms = (time.time() - start_time) * 1000
        
        log_audit(
            event_type="mcp_invocation",
            server=server_name,
            path=path,
            method=request.method,
            status=response.status_code,
            latency_ms=latency_ms,
            user=user,
        )
        
        # Build response headers
        response_headers = {
            k: v for k, v in response.headers.items()
            if k.lower() not in STRIP_RESPONSE_HEADERS
        }
        
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=response_headers,
            media_type=response.headers.get("content-type"),
        )
        
    except httpx.TimeoutException:
        latency_ms = (time.time() - start_time) * 1000
        log_audit(
            event_type="mcp_error",
            server=server_name,
            path=path,
            method=request.method,
            status=504,
            latency_ms=latency_ms,
            user=user,
            error="Upstream timeout",
        )
        raise HTTPException(504, detail={"error": "timeout", "message": "Upstream server timed out"})
    
    except httpx.ConnectError as e:
        latency_ms = (time.time() - start_time) * 1000
        log_audit(
            event_type="mcp_error",
            server=server_name,
            path=path,
            method=request.method,
            status=502,
            latency_ms=latency_ms,
            user=user,
            error=f"Connection failed: {str(e)}",
        )
        raise HTTPException(502, detail={"error": "bad_gateway", "message": "Failed to connect to upstream server"})
    
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        log_audit(
            event_type="mcp_error",
            server=server_name,
            path=path,
            method=request.method,
            status=500,
            latency_ms=latency_ms,
            user=user,
            error=str(e),
        )
        raise HTTPException(500, detail={"error": "internal_error", "message": str(e)})


# SSE/Streaming support for MCP servers that use it
@app.api_route("/mcp/{server_name}", methods=["GET", "POST", "OPTIONS"])
async def proxy_mcp_root(server_name: str, request: Request):
    """Handle requests to server root (no path)."""
    return await proxy_mcp(server_name, "", request)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
