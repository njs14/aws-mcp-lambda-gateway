# MCP Gateway

Serverless MCP proxy with OAuth discovery for IDE integration.

## Architecture

```
IDE ──► CloudFront ──► Lambda Function URL ──► MCP Server
            │                 │
      (Firewall Mgr)    (JWT validation)
                              │
                        Cognito (IdP)
```

Implements MCP Authorization Spec (2025-06-18) with RFC 9728 Protected Resource Metadata.

## Deploy

Push to `main` — GitHub Actions deploys automatically.

Or: `sam build && sam deploy`

## Key Files

- `template.yaml` - SAM (CloudFront + Lambda + Cognito + Monitoring)
- `src/mcp_gateway.py` - FastAPI proxy with OAuth discovery
- `src/Dockerfile` - Lambda Web Adapter

## Monitoring

**Metrics** (MCPGateway namespace):
- `RequestCount` - Total requests by server
- `AuthFailureCount` - Auth failures by reason
- `ServerErrorCount` - 5xx errors
- `BlockedRequestCount` - Requests to non-allowlisted servers
- `Latency` - Request latency in ms

**Alarms:**
- `mcp-gateway-auth-failures` - >10 auth failures in 5 min
- `mcp-gateway-server-errors` - >5 server errors in 5 min
- `mcp-gateway-high-latency` - p99 latency >5s
- `mcp-gateway-lambda-errors` - Any Lambda errors

**Dashboard:** `mcp-gateway` in CloudWatch

## OAuth Discovery

IDEs discover auth automatically via:
```
GET /.well-known/oauth-protected-resource
```

## Swapping to Okta

Update env vars:
- `COGNITO_ISSUER` → Okta issuer URL
- `COGNITO_AUDIENCE` → Okta client ID  
- `COGNITO_DOMAIN` → Okta auth domain
