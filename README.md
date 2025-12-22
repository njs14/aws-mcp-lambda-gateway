# MCP Gateway

Serverless MCP proxy with OAuth discovery. IDEs auto-discover authentication via Cognito.

## Deploy

Push to `main` branch — GitHub Actions handles it.

Or manually:
```bash
sam build && sam deploy
```

## Create Test User

```bash
aws cognito-idp admin-create-user \
  --user-pool-id <from-outputs> \
  --username you@example.com \
  --temporary-password TempPass123! \
  --message-action SUPPRESS

aws cognito-idp admin-set-user-password \
  --user-pool-id <from-outputs> \
  --username you@example.com \
  --password YourPermanentPass123! \
  --permanent
```

## IDE Setup

**Cursor** (Settings → MCP Servers):
```json
{
  "mcpServers": {
    "my-gateway": {
      "url": "https://YOUR_CLOUDFRONT_DOMAIN/mcp/context7"
    }
  }
}
```

## Verify OAuth Discovery

```bash
curl https://YOUR_CLOUDFRONT_DOMAIN/.well-known/oauth-protected-resource
```

## Monitoring

- **Dashboard:** CloudWatch → Dashboards → `mcp-gateway`
- **Alarms:** Auth failures, server errors, high latency, Lambda errors
- **Metrics:** Request count, latency percentiles, errors by type
