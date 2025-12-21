# AWS STS Assume Role GitHub Action

This repository contains a reusable GitHub Action workflow for assuming an AWS IAM role using AWS STS (Security Token Service).

## Overview

The `aws-sts-assume-role.yml` workflow provides a standardized way to assume AWS IAM roles in your GitHub Actions workflows. This is useful for:

- Cross-account AWS access
- Implementing least-privilege access patterns
- Temporary credential management
- Secure AWS operations in CI/CD pipelines

## Prerequisites

1. **AWS IAM Role**: An IAM role in your AWS account with:
   - A trust policy that allows your AWS user/role to assume it
   - Appropriate permissions for the actions you need to perform

2. **GitHub Secrets**: Configure the following secrets in your repository:
   - `AWS_ACCESS_KEY_ID`: Your AWS access key ID
   - `AWS_SECRET_ACCESS_KEY`: Your AWS secret access key

## Usage

### Basic Usage

```yaml
name: My Workflow

on:
  push:
    branches: [main]

jobs:
  deploy:
    uses: ./.github/workflows/aws-sts-assume-role.yml
    with:
      role-to-assume: arn:aws:iam::123456789012:role/MyDeploymentRole
      aws-region: us-east-1
    secrets:
      AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
      AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```

### Advanced Usage with Custom Parameters

```yaml
jobs:
  deploy:
    uses: ./.github/workflows/aws-sts-assume-role.yml
    with:
      role-to-assume: arn:aws:iam::123456789012:role/MyDeploymentRole
      aws-region: us-west-2
      role-session-name: MyCustomSession
      role-duration-seconds: 7200  # 2 hours
    secrets:
      AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
      AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```

### Using Outputs

```yaml
jobs:
  assume-role:
    uses: ./.github/workflows/aws-sts-assume-role.yml
    with:
      role-to-assume: arn:aws:iam::123456789012:role/MyRole
    secrets:
      AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
      AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
  
  use-outputs:
    needs: assume-role
    runs-on: ubuntu-latest
    steps:
      - name: Display Assumed Role Info
        run: |
          echo "Assumed Role: ${{ needs.assume-role.outputs.assumed-role-arn }}"
          echo "Account ID: ${{ needs.assume-role.outputs.aws-account-id }}"
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `aws-region` | AWS Region to use | No | `us-east-1` |
| `role-to-assume` | AWS IAM Role ARN to assume | Yes | - |
| `role-session-name` | Name for the role session | No | `GitHubActions` |
| `role-duration-seconds` | Role session duration (900-43200 seconds) | No | `3600` |

## Secrets

| Secret | Description | Required |
|--------|-------------|----------|
| `AWS_ACCESS_KEY_ID` | AWS Access Key ID | Yes |
| `AWS_SECRET_ACCESS_KEY` | AWS Secret Access Key | Yes |

## Outputs

| Output | Description |
|--------|-------------|
| `assumed-role-arn` | ARN of the assumed role |
| `aws-account-id` | AWS Account ID where the role was assumed |

## IAM Role Trust Policy Example

Your AWS IAM role should have a trust policy that allows assumption. Here's an example:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::YOUR_ACCOUNT_ID:user/YOUR_IAM_USER"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "optional-external-id"
        }
      }
    }
  ]
}
```

## Security Best Practices

1. **Use OIDC Instead of Long-lived Credentials**: For enhanced security, consider using GitHub's OIDC provider instead of storing AWS credentials as secrets. This eliminates the need for long-lived AWS credentials.

2. **Principle of Least Privilege**: Grant only the minimum permissions required for your workflow.

3. **Limit Role Duration**: Set `role-duration-seconds` to the minimum time needed for your workflow.

4. **Rotate Credentials**: Regularly rotate your AWS access keys stored in GitHub secrets.

5. **Use External ID**: For cross-account access, consider adding an External ID condition to your trust policy.

## Migrating to OIDC (Recommended)

For better security, consider migrating to OIDC authentication:

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/MyRole
          aws-region: us-east-1
```

## Troubleshooting

### Error: "User is not authorized to perform: sts:AssumeRole"

- Verify the IAM user has `sts:AssumeRole` permission
- Check the role's trust policy allows your IAM user/role to assume it
- Ensure the role ARN is correct

### Error: "Role session duration exceeded"

- The `role-duration-seconds` exceeds the maximum session duration configured for the role
- Check the role's "Maximum session duration" setting in AWS IAM

## Example Workflows

See the `example-assume-role.yml` file in this repository for a complete working example.

## License

See the LICENSE file in this repository.
