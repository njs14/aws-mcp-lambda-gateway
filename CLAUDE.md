# MCP Gateway

Serverless MCP proxy for personal use. CloudFront + Lambda Function URL + Cognito.

## Architecture

```
IDE ──► CloudFront ──► Lambda Function URL ──► MCP Server
            │                 │
      (Firewall Mgr)    (Cognito JWT)
```

## Deploy

```bash
sam build && sam deploy
```

## Key Files

- `template.yaml` - SAM (CloudFront + Lambda + Cognito)
- `src/mcp_gateway.py` - FastAPI proxy
- `src/Dockerfile` - Lambda Web Adapter

## After Deploy

1. Create a Cognito user (command in stack outputs)
2. Get a token from Cognito
3. Call gateway with `Authorization: Bearer <token>`

## Swapping to Okta

Change env vars in template.yaml:
- `COGNITO_ISSUER` → `OKTA_ISSUER`
- `COGNITO_AUDIENCE` → `OKTA_AUDIENCE`

Update Python to use `aud` claim instead of `client_id`.
