# MCP Gateway

Lightweight serverless proxy for MCP server governance. Deploys to AWS Lambda with Lambda Web Adapter.

## Features

- **Allowlist enforcement**: Only approved MCP servers can be accessed
- **Audit logging**: All invocations logged to CloudWatch with structured JSON
- **Streaming support**: Works with SSE/streaming MCP responses
- **Zero cold-start impact**: Lambda Web Adapter keeps the FastAPI app warm within the container

## Quick Start

### Prerequisites

- AWS SAM CLI (`brew install aws-sam-cli` or [install guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html))
- Docker
- AWS credentials configured

### Deploy

```bash
# Build the container image
sam build

# Deploy (first time - will prompt for parameters)
sam deploy --guided

# Subsequent deployments
sam deploy
```

### Configure Allowed Servers

Edit `samconfig.toml` or pass parameter overrides:

```bash
sam deploy --parameter-overrides \
  'AllowedServersJson={"context7":"https://mcp.context7.com/mcp","notion":"https://mcp.notion.com/mcp","github":"https://api.githubcopilot.com/mcp"}'
```

## Usage

### Endpoint Pattern

```
https://{api-id}.execute-api.{region}.amazonaws.com/{stage}/mcp/{server_name}/{path}
```

### Example Requests

```bash
# Health check
curl https://xxx.execute-api.us-east-1.amazonaws.com/dev/health

# List allowed servers
curl https://xxx.execute-api.us-east-1.amazonaws.com/dev/servers

# Proxy to Context7
curl -X POST https://xxx.execute-api.us-east-1.amazonaws.com/dev/mcp/context7/resolve-library-id \
  -H "Content-Type: application/json" \
  -d '{"libraryName": "react"}'
```

### Kiro/Q Developer Registry Entry

Point your MCP registry at this gateway:

```json
{
  "servers": [
    {
      "server": {
        "name": "context7",
        "description": "Library documentation (via gateway)",
        "version": "1.0.0",
        "remotes": [{
          "type": "streamable-http",
          "url": "https://xxx.execute-api.us-east-1.amazonaws.com/dev/mcp/context7"
        }]
      }
    }
  ]
}
```

## Audit Logging

All MCP invocations are logged as structured JSON to CloudWatch:

```json
{
  "event": "mcp_invocation",
  "server": "context7",
  "path": "resolve-library-id",
  "method": "POST",
  "status": 200,
  "latency_ms": 142.5,
  "user": "anonymous",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### CloudWatch Logs Insights Queries

```sql
-- Invocations by server
fields @timestamp, server, path, status, latency_ms
| filter event = "mcp_invocation"
| stats count() by server

-- Errors in last hour
fields @timestamp, server, path, error
| filter event = "mcp_error"
| sort @timestamp desc

-- Blocked requests (policy violations)
fields @timestamp, server, user
| filter event = "mcp_blocked"
```

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│   Client    │────▶│ API Gateway  │────▶│ Lambda + LWA    │
│ (Kiro/etc)  │     │  (HTTP API)  │     │ (FastAPI proxy) │
└─────────────┘     └──────────────┘     └────────┬────────┘
                                                  │
                         ┌────────────────────────┼────────────────────────┐
                         ▼                        ▼                        ▼
                  ┌─────────────┐         ┌─────────────┐         ┌─────────────┐
                  │  Context7   │         │   Notion    │         │   GitHub    │
                  └─────────────┘         └─────────────┘         └─────────────┘
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ALLOWED_SERVERS` | JSON map of server name → URL | `{}` |
| `AWS_LWA_PORT` | Port for Lambda Web Adapter | `8080` |
| `AWS_LWA_INVOKE_MODE` | Lambda response mode | `response_stream` |

### Adding New Servers

1. Update `AllowedServersJson` parameter
2. Redeploy: `sam deploy`
3. Update your MCP registry file with the new gateway URL

## Cost Estimate

| Component | Estimated Monthly Cost |
|-----------|----------------------|
| Lambda (1M requests, 500ms avg) | ~$3-5 |
| API Gateway (1M requests) | ~$3.50 |
| CloudWatch Logs (1GB) | ~$0.50 |
| **Total** | **~$7-10/month** |

## Limitations

- **HTTP/SSE MCP servers only**: stdio-based servers not supported
- **120s timeout**: Lambda max timeout, but sufficient for most MCP calls
- **Cold starts**: First request after idle may take 5-10s (use Provisioned Concurrency if needed)

## Local Development

```bash
cd src
pip install -r requirements.txt

# Set test config
export ALLOWED_SERVERS='{"context7":"https://mcp.context7.com/mcp"}'

# Run locally
uvicorn mcp_gateway:app --reload --port 8080
```

## Cleanup

```bash
sam delete --stack-name mcp-gateway-dev
```
