# GitHub Copilot Instructions for aws-mcp-lambda-gateway

## Project Overview

This project provides an AWS Lambda gateway for the Model Context Protocol (MCP). It enables MCP servers to be deployed and accessed through AWS Lambda functions, allowing AI assistants and other clients to interact with MCP servers in a serverless environment.

## Tech Stack

- **Infrastructure as Code**: Terraform
- **Cloud Provider**: AWS (Lambda, API Gateway, IAM)
- **Protocol**: Model Context Protocol (MCP)
- **Deployment**: Serverless architecture

## Repository Structure

- Infrastructure and deployment configurations using Terraform
- AWS Lambda function code for MCP gateway
- Configuration files for AWS services

## Coding Guidelines

### Terraform

- Use consistent naming conventions for resources (lowercase with hyphens)
- Always include descriptions for variables and outputs
- Use Terraform modules for reusable components
- Tag all AWS resources appropriately
- Keep state files secure and never commit them to version control
- Use `.tfvars` files for environment-specific configurations (excluded from version control)

### AWS Lambda

- Follow AWS Lambda best practices for performance and cost optimization
- Implement proper error handling and logging
- Use environment variables for configuration
- Keep functions small and focused on single responsibilities
- Implement proper IAM permissions following least privilege principle

### General Guidelines

- Write clear, descriptive commit messages
- Document infrastructure changes thoroughly
- Include README updates when adding new features
- Follow security best practices for AWS resources
- Never commit sensitive data, credentials, or secrets

## Security Considerations

- All IAM roles and policies should follow the principle of least privilege
- Sensitive data must be stored in AWS Secrets Manager or Parameter Store
- API endpoints should be properly secured with authentication
- Regular security audits of Lambda functions and API Gateway configurations
- Use AWS CloudWatch for monitoring and alerting

## Build and Deployment

### Prerequisites
- Terraform installed and configured
- AWS CLI configured with appropriate credentials
- Access to the target AWS account

### Terraform Commands
```bash
# Initialize Terraform
terraform init

# Plan infrastructure changes
terraform plan

# Apply infrastructure changes
terraform apply

# Destroy infrastructure (use with caution)
terraform destroy
```

### Validation
- Always run `terraform plan` before applying changes
- Review the plan output carefully for unexpected changes
- Test Lambda functions in a development environment before production deployment

## Testing

- Test infrastructure changes in a non-production environment first
- Validate Terraform configurations using `terraform validate`
- Use `terraform fmt` to ensure consistent formatting
- Test Lambda functions locally when possible before deployment

## Documentation

- Keep this instructions file updated as the project evolves
- Document all infrastructure components and their purposes
- Maintain clear README files with setup and deployment instructions
- Document any architectural decisions and trade-offs
