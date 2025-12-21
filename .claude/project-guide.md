# MCP Gateway - Project Guide

## Project Overview

This is a serverless AWS Lambda-based MCP (Model Context Protocol) gateway that proxies requests to approved MCP servers. It provides governance, audit logging, and access control for MCP server interactions.

## Architecture

- **Lambda Function**: ARM64 container-based (Python 3.12 + FastAPI)
- **API Gateway**: HTTP API for routing
- **Infrastructure**: SAM (Serverless Application Model)
- **CI/CD**: GitHub Actions with AWS OIDC authentication

## Key Files

```
.
├── template.yaml              # SAM template (CloudFormation)
├── samconfig.toml            # SAM deployment configuration
├── src/
│   ├── Dockerfile            # ARM64 Lambda container
│   ├── mcp_gateway.py        # FastAPI application
│   └── requirements.txt      # Python dependencies
└── .github/workflows/
    └── deploy.yml            # GitHub Actions deployment workflow
```

## Deployment Configuration

### Critical SAM Config Settings (samconfig.toml)

**IMPORTANT**: Both `dev` and `prod` sections MUST have:
```toml
resolve_s3 = true              # Auto-create S3 bucket for artifacts
s3_prefix = "mcp-gateway"      # S3 prefix for organization
resolve_image_repos = true     # Auto-create ECR repo for Docker images
```

**Why**: SAM reads the config file BEFORE CLI flags, and config values take precedence over CLI flags. Missing these will cause deployment failures.

### Workflow Configuration (.github/workflows/deploy.yml)

The workflow uses:
- **Python 3.12**: Matches Lambda runtime
- **Docker Buildx + QEMU**: Required for ARM64 builds on x86_64 runners
- **AWS OIDC**: Secure credential-less authentication
- **SAM CLI**: Build and deploy

**Key Steps**:
1. Setup Python 3.12
2. Setup SAM CLI
3. Setup Docker Buildx (for cross-platform builds)
4. Setup QEMU (for ARM64 emulation)
5. Configure AWS credentials (via OIDC)
6. SAM Build
7. SAM Deploy (using `--config-env dev` or `prod`)

## Common Issues & Solutions

### 1. SAM Build Fails - "cannot build ARM64 image"

**Cause**: GitHub Actions runners are x86_64, can't build ARM64 without emulation

**Solution**: Workflow includes Docker Buildx + QEMU setup:
```yaml
- name: Set up Docker Buildx
  uses: docker/setup-buildx-action@v3

- name: Set up QEMU
  uses: docker/setup-qemu-action@v3
  with:
    platforms: arm64
```

### 2. SAM Deploy Fails - "Missing option --image-repositories"

**Cause**: Container-based Lambda needs ECR repository

**Solution**: `resolve_image_repos = true` in samconfig.toml (already configured)

### 3. SAM Deploy Fails - "S3 Bucket not specified"

**Cause**: SAM needs S3 bucket for CloudFormation artifacts

**Solution**: `resolve_s3 = true` in samconfig.toml (already configured)

### 4. GitHub Environment Error

**Cause**: Workflow referenced GitHub environment that doesn't exist

**Solution**: Removed `environment:` declaration from workflow (fixed in PR #8)

### 5. Config vs CLI Flags Precedence

**Problem**: CLI flags like `--resolve-s3` being ignored

**Cause**: When using `--config-env`, SAM reads config file first and ignores CLI flags for settings that exist in config

**Solution**: Put all settings in samconfig.toml, don't rely on CLI flags

## AWS Requirements

### Required GitHub Secrets

- `AWS_ROLE_ARN`: IAM role ARN for GitHub Actions OIDC authentication

### Setting up GitHub OIDC (one-time)

```bash
aws cloudformation deploy \
  --template-file infrastructure/github-oidc.yaml \
  --stack-name github-oidc-mcp-gateway \
  --parameter-overrides \
    GitHubOrg=<your-org> \
    GitHubRepo=aws-mcp-lambda-gateway \
  --capabilities CAPABILITY_NAMED_IAM
```

Get the role ARN:
```bash
aws cloudformation describe-stacks \
  --stack-name github-oidc-mcp-gateway \
  --query 'Stacks[0].Outputs[?OutputKey==`RoleArn`].OutputValue' \
  --output text
```

Add to GitHub Secrets as `AWS_ROLE_ARN`.

## Local Development

```bash
cd src
pip install -r requirements.txt

# Set test config
export ALLOWED_SERVERS='{"context7":"https://mcp.context7.com/mcp"}'

# Run locally
uvicorn mcp_gateway:app --reload --port 8080
```

## Deployment Workflow

### Manual Deployment
```bash
sam build
sam deploy --config-env dev
```

### GitHub Actions (Automatic)
- Push to `main` → auto-deploys to dev
- Manual trigger → choose dev or prod environment

## Troubleshooting Deployments

### View GitHub Actions Logs
```bash
gh run list --limit 5
gh run view <run-id>
```

### View CloudFormation Stack
```bash
aws cloudformation describe-stacks --stack-name mcp-gateway-dev
aws cloudformation describe-stack-events --stack-name mcp-gateway-dev
```

### View Lambda Logs
```bash
aws logs tail /aws/lambda/mcp-gateway-dev --follow
```

### Common SAM CLI Commands
```bash
sam build                                    # Build the application
sam deploy --config-env dev                  # Deploy to dev
sam deploy --config-env prod                 # Deploy to prod
sam delete --stack-name mcp-gateway-dev      # Delete stack
sam logs --stack-name mcp-gateway-dev        # View logs
```

## Configuration Reference

### Environment-specific Settings

**Dev Environment** (`samconfig.toml` → `[dev.deploy.parameters]`)
- Stack: `mcp-gateway-dev`
- Allowed servers: context7, notion

**Prod Environment** (`samconfig.toml` → `[prod.deploy.parameters]`)
- Stack: `mcp-gateway-prod`
- Allowed servers: context7 only

### Template Parameters

- `Environment`: dev/staging/prod (affects resource names)
- `AllowedServersJson`: JSON mapping of server names to URLs

## Key Learnings from Setup

1. **ARM64 requires QEMU**: Can't build ARM64 images on x86_64 without emulation
2. **Config file > CLI flags**: SAM config file takes precedence when using `--config-env`
3. **Container images need ECR**: `resolve_image_repos = true` is essential
4. **SAM needs S3**: `resolve_s3 = true` for CloudFormation artifacts
5. **GitHub environments optional**: Don't use `environment:` in workflow unless configured

## Future Improvements

- [ ] Add custom domain name for API Gateway
- [ ] Add CloudWatch alarms for errors/latency
- [ ] Add X-Ray tracing for debugging
- [ ] Add automated testing in CI/CD
- [ ] Add Provisioned Concurrency to reduce cold starts
- [ ] Add VPC configuration if MCP servers require private access
