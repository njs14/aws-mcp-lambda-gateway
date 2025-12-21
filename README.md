# MCP Gateway

Serverless MCP proxy with Cognito auth.

## Deploy

```bash
sam build
sam deploy
```

## Create Test User

After deploy, run the command from stack outputs:

```bash
aws cognito-idp admin-create-user \
  --user-pool-id <from-outputs> \
  --username you@example.com \
  --temporary-password TempPass123! \
  --message-action SUPPRESS
```

## Get Token

```bash
aws cognito-idp initiate-auth \
  --client-id <from-outputs> \
  --auth-flow USER_PASSWORD_AUTH \
  --auth-parameters USERNAME=you@example.com,PASSWORD=YourNewPassword123!
```

## Test

```bash
curl -H "Authorization: Bearer <token>" \
  https://<cloudfront-domain>/mcp/context7/
```
