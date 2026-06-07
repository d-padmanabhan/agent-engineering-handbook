---
name: infrastructure-iac
description: Infrastructure as Code best practices for Terraform, Docker, Ansible, and CloudFormation. Covers secure-by-default configurations, multi-stage builds, state management, and modular patterns. Use when working with .tf, Dockerfile, docker-compose.yml, .yaml/.yml Ansible files, CloudFormation templates, or when asking about IaC, containers, or infrastructure automation.
---

# Infrastructure as Code

## Guiding Principles

1. **Security First**: Non-root users, minimal images, secret management
2. **Reproducibility**: Pin versions, deterministic builds, locked dependencies
3. **Modularity**: Reusable modules, DRY patterns, clear interfaces
4. **State Management**: Remote state, locking, backup strategies

## Tool Selection

| Use Case | Tool |
|----------|------|
| Cloud infrastructure | Terraform |
| Containers | Docker |
| Configuration management | Ansible |
| AWS-native IaC | CloudFormation |

## Terraform Quick Reference

### Essential Commands

```bash
terraform init                    # Initialize working directory
terraform plan                    # Preview changes
terraform plan -out=tfplan        # Save plan for apply
terraform apply tfplan            # Apply saved plan
terraform fmt -recursive          # Format all files
terraform validate                # Validate configuration
```

### Critical Patterns

```hcl
# 1. Pin provider versions
terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
  }
}

# 2. Use for_each for stability
resource "aws_subnet" "private" {
  for_each = var.private_subnets  # NOT: count
}

# 3. Validate inputs
variable "environment" {
  type = string
  validation {
    condition     = can(regex("^(dev|staging|prod)$", var.environment))
    error_message = "Must be: dev, staging, prod."
  }
}

# 4. Mark sensitive data
variable "db_password" {
  type      = string
  sensitive = true
}

# 5. Lifecycle protection
resource "aws_s3_bucket" "state" {
  lifecycle {
    prevent_destroy = true
  }
}
```

## Docker Quick Reference

### Multi-Stage Build

```dockerfile
# Build stage
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

# Production stage
FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules

USER node
EXPOSE 3000
CMD ["node", "dist/index.js"]
```

### Best Practices

```dockerfile
# Pin versions
FROM python:3.14.0-slim-bookworm

# Run as non-root
RUN useradd -m appuser
USER appuser

# Layer optimization
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost:8080/health || exit 1
```

## Naming Conventions

| Tool | Convention | Example |
|------|------------|---------|
| Terraform | snake_case | `aws_vpc.main` |
| Docker | lowercase, hyphens | `my-app:1.0.0` |
| Ansible | snake_case | `install_packages` |
| CloudFormation | Hungarian | `pEnvironment`, `rVpc` |

## Security Checklist

- [ ] No secrets in code (use vaults/secret managers)
- [ ] Non-root containers
- [ ] Minimal base images
- [ ] Version pinning
- [ ] Vulnerability scanning
- [ ] State encryption (Terraform)
- [ ] Network segmentation

## Detailed References

- **Terraform**: See [references/terraform.md](references/terraform.md)
- **Docker**: See [references/docker.md](references/docker.md)
- **Ansible**: See [references/ansible.md](references/ansible.md)
- **Configuration**: See [references/configuration.md](references/configuration.md)
- **CloudFormation**: See [references/cloudformation.md](references/cloudformation.md)
