# AWS Engineering Patterns

**Goal:** Build secure, scalable, maintainable AWS infrastructure following best practices for Platform Engineering, Zero Trust, and EKS.

> [!IMPORTANT]
> Use the AWS Well-Architected Framework as the baseline for AWS design and review decisions: [AWS Well-Architected Framework](https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html)
>
> [!IMPORTANT]
> Treat AWS Service Quotas as a first-class design constraint (regional/account limits). Validate quotas early for the services you depend on, request quota increases before rollout, and bake the limits into scaling and architecture decisions: [AWS Service Quotas User Guide](https://docs.aws.amazon.com/servicequotas/latest/userguide/intro.html)

## AWS Engineering Philosophy

**Guiding Principles:**

- **Security First**: Zero Trust architecture, least privilege, defense in depth, encryption everywhere
- **Infrastructure as Code**: All infrastructure defined in code (Terraform, CloudFormation, CDK); no manual changes
- **Observability**: Comprehensive logging, metrics, and tracing; monitor everything
- **Cost Optimization**: Right-sizing, reserved instances, spot instances; measure and optimize continuously
- **Disaster Recovery**: Multi-region, backups, failover strategies; test regularly
- **Automation**: Automate everything possible; reduce toil, increase reliability
- **Scalability**: Design for growth; horizontal scaling preferred over vertical

**Core Tenets:**

1. **Zero Trust**: Never trust, always verify. Every request authenticated and authorized
2. **Least Privilege**: Grant minimum permissions necessary; review regularly
3. **Defense in Depth**: Multiple security layers; don't rely on single controls
4. **Fail Securely**: Default deny; explicit allow; fail closed, not open
5. **Immutable Infrastructure**: Replace, don't patch; version everything
6. **Idempotency**: Operations should be safe to repeat; infrastructure as code ensures this

**Applying AWS Philosophy:**

```hcl
# BAD: Trusting network boundaries
resource "aws_security_group" "app" {
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # Trusting all IPs
  }
}

# GOOD: Zero Trust - explicit allowlist
resource "aws_security_group" "app" {
  ingress {
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.lb.id]  # Only from load balancer
  }
}

# BAD: Overly permissive IAM
resource "aws_iam_role_policy" "app" {
  policy = jsonencode({
    Statement = [{
      Effect   = "Allow"
      Action   = "s3:*"  # Too broad
      Resource = "*"
    }]
  })
}

# GOOD: Least privilege
resource "aws_iam_role_policy" "app" {
  policy = jsonencode({
    Statement = [{
      Effect = "Allow"
      Action = [
        "s3:GetObject",
        "s3:ListBucket"
      ]
      Resource = [
        aws_s3_bucket.data.arn,
        "${aws_s3_bucket.data.arn}/*"
      ]
    }]
  })
}
```

---

## Zero Trust Architecture

### Network Segmentation

**Principle:** Never trust, always verify. Every request must be authenticated and authorized.

```hcl
# VPC with private subnets only
resource "aws_vpc" "main" {
  cidr_block           = "10.16.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "zero-trust-vpc"
  }
}

# Private subnets only - no public internet access
resource "aws_subnet" "private" {
  count             = 3
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.16.${count.index + 1}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "private-subnet-${count.index + 1}"
    Type = "Private"
  }
}
```

### Identity and Access Management

**Prefer EKS Pod Identity over IRSA** - Simpler, more secure, AWS-managed solution.

#### EKS Pod Identity (Recommended)

**EKS Pod Identity** is the modern replacement for IRSA. It's simpler, more secure, and AWS-managed:

```hcl
# Enable Pod Identity on EKS cluster
resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  role_arn = aws_iam_role.cluster.arn

  # Enable Pod Identity
  pod_identity_associations {
    service_account = "default"
    namespace       = "default"
  }
}

# Create Pod Identity association
resource "aws_eks_pod_identity_association" "app" {
  cluster_name    = aws_eks_cluster.main.name
  namespace       = "default"
  service_account = "app"
  role_arn        = aws_iam_role.app_pod_identity.arn
}

# IAM Role for Pod Identity (simpler than IRSA)
resource "aws_iam_role" "app_pod_identity" {
  name = "app-pod-identity-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "pods.eks.amazonaws.com"
      }
      Action = "sts:AssumeRole"
      Condition = {
        StringEquals = {
          "eks:cluster-name" = aws_eks_cluster.main.name
        }
      }
    }]
  })

  tags = {
    Name = "app-pod-identity"
  }
}

# Least privilege policy
resource "aws_iam_role_policy" "app_policy" {
  name = "app-policy"
  role = aws_iam_role.app_pod_identity.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "s3:GetObject",
        "s3:ListBucket"
      ]
      Resource = [
        aws_s3_bucket.data.arn,
        "${aws_s3_bucket.data.arn}/*"
      ]
    }]
  })
}
```

**Kubernetes ServiceAccount:**

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app
  namespace: default
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/app-pod-identity-role
```

**Benefits of Pod Identity over IRSA:**

- Simpler setup (no OIDC provider configuration)
- AWS-managed (less operational overhead)
- Better security (AWS handles token management)
- Works with EKS 1.24+
- No need for OIDC provider

#### IRSA (Legacy, Still Supported)

**IRSA** is still valid but more complex. Use when Pod Identity is not available:

```hcl
# OIDC Provider for IRSA
data "tls_certificate" "eks" {
  url = aws_eks_cluster.main.identity[0].oidc[0].issuer
}

resource "aws_iam_openid_connect_provider" "eks" {
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.eks.certificates[0].sha1_fingerprint]
  url             = aws_eks_cluster.main.identity[0].oidc[0].issuer

  tags = {
    Name = "eks-oidc-provider"
  }
}

# EKS Service Account with IRSA
resource "aws_iam_role" "app_role" {
  name = "app-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = aws_iam_openid_connect_provider.eks.arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${replace(aws_iam_openid_connect_provider.eks.url, "https://", "")}:sub" = "system:serviceaccount:default:app"
          "${replace(aws_iam_openid_connect_provider.eks.url, "https://", "")}:aud" = "sts.amazonaws.com"
        }
      }
    }]
  })
}
```

---

## VPC Lattice for Service-to-Service Communication

**VPC Lattice** provides service-to-service networking with built-in authentication, authorization, and traffic management across VPCs, accounts, and on-premises.

**Benefits:**

- Cross-VPC resource access without VPC peering
- Built-in authentication and authorization
- Traffic management and observability
- Works across accounts and regions
- No VPC peering or transit gateway required

### Kubernetes integration (Gateway API controller - pod IP targets)

When using VPC Lattice from Kubernetes via the Gateway API controller, traffic can be routed to **pod IP targets** (pods are registered as targets in Lattice target groups).

Key points:

- **Direct-to-pod routing**: reduces node-level hops compared to node-target patterns
- **Readiness gates**: pods can be gated until registration and target health are established, reducing rollout 5XX

### Service Network Setup

```hcl
# Create VPC Lattice Service Network
resource "aws_vpclattice_service_network" "main" {
  name      = "platform-services"
  auth_type = "AWS_IAM"

  tags = {
    Name        = "platform-services-network"
    Environment = var.environment
  }
}

# Associate VPCs to Service Network
resource "aws_vpclattice_service_network_vpc_association" "vpc1" {
  service_network_identifier = aws_vpclattice_service_network.main.id
  vpc_identifier             = aws_vpc.app1.id

  security_group_ids = [aws_security_group.lattice.id]
}

resource "aws_vpclattice_service_network_vpc_association" "vpc2" {
  service_network_identifier = aws_vpclattice_service_network.main.id
  vpc_identifier             = aws_vpc.app2.id

  security_group_ids = [aws_security_group.lattice.id]
}
```

### Service Definition

```hcl
# Create a Lattice Service (e.g., API Gateway, Lambda, ECS, EKS)
resource "aws_vpclattice_service" "api" {
  name      = "api-service"
  auth_type = "AWS_IAM"

  tags = {
    Name = "api-service"
  }
}

# Associate service to service network
resource "aws_vpclattice_service_network_service_association" "api" {
  service_identifier          = aws_vpclattice_service.api.id
  service_network_identifier  = aws_vpclattice_service_network.main.id
}
```

### Cross-VPC Resource Access Examples

**Example 1: Access RDS in Another VPC**

```hcl
# Target group for RDS in database VPC
resource "aws_vpclattice_target_group" "rds" {
  name            = "rds-target-group"
  type            = "IP"
  protocol        = "TCP"
  port            = 5432
  vpc_identifier  = aws_vpc.database.id

  health_check {
    enabled                        = true
    health_check_interval_seconds  = 30
    healthy_threshold_count        = 2
    unhealthy_threshold_count      = 2
    port                           = 5432
    protocol                       = "TCP"
  }

  tags = {
    Name = "rds-target-group"
  }
}

# Register RDS endpoint as target
resource "aws_vpclattice_target_group_attachment" "rds" {
  target_group_identifier = aws_vpclattice_target_group.rds.id

  target {
    id   = aws_db_instance.main.address
    port = 5432
  }
}

# Create listener for the service
resource "aws_vpclattice_listener" "rds" {
  name               = "rds-listener"
  protocol           = "TCP"
  port               = 5432
  service_identifier = aws_vpclattice_service.rds.id

  default_action {
    forward {
      target_groups {
        target_group_identifier = aws_vpclattice_target_group.rds.id
        weight                   = 100
      }
    }
  }
}
```

**Example 2: Cross-VPC EKS Service Access**

```hcl
# Access EKS service in another VPC/account
resource "aws_vpclattice_target_group" "eks_service" {
  name            = "eks-api-target-group"
  type            = "IP"
  protocol        = "HTTP"
  port            = 80
  vpc_identifier  = aws_vpc.eks.id

  health_check {
    enabled                        = true
    health_check_interval_seconds  = 30
    healthy_threshold_count        = 2
    unhealthy_threshold_count      = 2
    path                          = "/health"
    port                          = 80
    protocol                      = "HTTP"
    matcher                       = "200"
  }

  tags = {
    Name = "eks-api-target-group"
  }
}

# Register EKS service endpoints
resource "aws_vpclattice_target_group_attachment" "eks_service" {
  target_group_identifier = aws_vpclattice_target_group.eks_service.id

  # Multiple targets for high availability
  target {
    id   = "10.1.1.10"  # EKS service IP
    port = 80
  }
  target {
    id   = "10.1.1.11"  # EKS service IP
    port = 80
  }
}
```

**Example 3: Cross-Account Resource Access**

```hcl
# Resource share for cross-account VPC Lattice access
resource "aws_ram_resource_share" "lattice" {
  name                      = "lattice-share"
  allow_external_principals = false

  tags = {
    Name = "lattice-share"
  }
}

resource "aws_ram_resource_association" "lattice" {
  resource_arn       = aws_vpclattice_service_network.main.arn
  resource_share_arn = aws_ram_resource_share.lattice.arn
}

# Share with specific account
resource "aws_ram_principal_association" "lattice" {
  principal          = "123456789012"  # Target account
  resource_share_arn = aws_ram_resource_share.lattice.arn
}

# Access policy for cross-account
resource "aws_vpclattice_service_network" "main" {
  name      = "platform-services"
  auth_type = "AWS_IAM"

  auth_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        AWS = [
          "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/app-role",
          "arn:aws:iam::123456789012:role/cross-account-role"  # Cross-account access
        ]
      }
      Action = "vpc-lattice-svcs:Invoke"
      Resource = "*"
    }]
  })
}
```

### Access Policy (IAM-based)

```hcl
# Service network access policy
resource "aws_vpclattice_service_network" "main" {
  name      = "platform-services"
  auth_type = "AWS_IAM"

  # Access policy for Zero Trust
  auth_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/app-role"
      }
      Action = "vpc-lattice-svcs:Invoke"
      Resource = "*"
      Condition = {
        StringEquals = {
          "vpc-lattice-svcs:ServiceArn" = aws_vpclattice_service.api.arn
        }
      }
    }]
  })
}
```

### VPC Endpoints (For AWS Services)

**Use VPC endpoints for AWS services** (complements VPC Lattice):

```hcl
# VPC Endpoint for S3 (no internet gateway needed)
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = aws_route_table.private[*].id

  tags = {
    Name = "s3-endpoint"
  }
}

# VPC Endpoint for ECR (Docker images)
resource "aws_vpc_endpoint" "ecr_dkr" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.ecr.dkr"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoint.id]

  tags = {
    Name = "ecr-dkr-endpoint"
  }
}
```

---

## EKS Best Practices

### Cluster Configuration

```hcl
resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  role_arn = aws_iam_role.cluster.arn
  version  = "1.28"

  vpc_config {
    subnet_ids              = aws_subnet.private[*].id
    endpoint_private_access = true
    endpoint_public_access  = false  # Private only for Zero Trust
    public_access_cidrs     = []      # No public access
  }

  # Enable Pod Identity (preferred over IRSA)
  pod_identity_associations {
    service_account = "default"
    namespace       = "default"
  }

  # Enable all control plane logs
  enabled_cluster_log_types = [
    "api",
    "audit",
    "authenticator",
    "controllerManager",
    "scheduler"
  ]

  encryption_config {
    provider {
      key_arn = aws_kms_key.eks.arn
    }
    resources = ["secrets"]
  }

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
```

### Node Groups

```hcl
resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "main"
  node_role_arn   = aws_iam_role.node.arn
  subnet_ids      = aws_subnet.private[*].id

  # Use multiple instance types for better availability
  instance_types = ["t3.medium", "t3.large"]

  scaling_config {
    desired_size = 3
    max_size     = 10
    min_size     = 1
  }

  # Update configuration
  update_config {
    max_unavailable = 1
  }

  # Launch template for advanced configuration
  launch_template {
    id      = aws_launch_template.node.id
    version = aws_launch_template.node.latest_version
  }

  labels = {
    Environment = var.environment
    Workload    = "general"
  }

  tags = {
    "k8s.io/cluster-autoscaler/enabled" = "true"
    "k8s.io/cluster-autoscaler/${aws_eks_cluster.main.name}" = "owned"
  }
}
```

### EKS Add-ons

```hcl
# VPC CNI (required)
resource "aws_eks_addon" "vpc_cni" {
  cluster_name = aws_eks_cluster.main.name
  addon_name   = "vpc-cni"
  addon_version = "v1.16.0-eksbuild.1"

  resolve_conflicts_on_update = "OVERWRITE"
}

# CoreDNS
resource "aws_eks_addon" "coredns" {
  cluster_name = aws_eks_cluster.main.name
  addon_name   = "coredns"

  resolve_conflicts_on_update = "OVERWRITE"
}

# kube-proxy
resource "aws_eks_addon" "kube_proxy" {
  cluster_name = aws_eks_cluster.main.name
  addon_name   = "kube-proxy"

  resolve_conflicts_on_update = "OVERWRITE"
}
```

---

## Platform Engineering Patterns

### Infrastructure Modules

**Create reusable modules:**

```hcl
# modules/eks-cluster/main.tf
variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID for the cluster"
  type        = string
}

variable "subnet_ids" {
  description = "Subnet IDs for the cluster"
  type        = list(string)
}

# ... module implementation
```

### Environment Management

```hcl
# environments/production/main.tf
module "eks_cluster" {
  source = "../../modules/eks-cluster"

  cluster_name = "prod-cluster"
  vpc_id       = data.aws_vpc.production.id
  subnet_ids   = data.aws_subnets.private.ids

  node_instance_types = ["m5.large", "m5.xlarge"]
  node_desired_size   = 5
  node_max_size       = 20

  tags = {
    Environment = "production"
    CostCenter  = "platform"
  }
}
```

---

## Security Best Practices

### Encryption

**Encrypt everything:**

```hcl
# KMS Key for EKS
resource "aws_kms_key" "eks" {
  description             = "KMS key for EKS cluster encryption"
  deletion_window_in_days = 30
  enable_key_rotation    = true

  tags = {
    Name = "eks-encryption-key"
  }
}

# Encrypted S3 bucket
resource "aws_s3_bucket" "data" {
  bucket = "my-app-data-${var.environment}"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  bucket = aws_s3_bucket.data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3.arn
    }
  }
}
```

### Secrets Management

**Use AWS Secrets Manager or Parameter Store:**

```hcl
# Secrets Manager
resource "aws_secretsmanager_secret" "db_credentials" {
  name                    = "my-app/db-credentials"
  description             = "Database credentials for my-app"
  recovery_window_in_days = 7

  tags = {
    Environment = var.environment
  }
}

# External Secrets Operator integration
# Use Pod Identity (preferred) or IRSA to allow pods to access secrets
resource "aws_eks_pod_identity_association" "secrets" {
  cluster_name    = aws_eks_cluster.main.name
  namespace       = "default"
  service_account = "external-secrets"
  role_arn        = aws_iam_role.secrets_access.arn
}

resource "aws_iam_role" "secrets_access" {
  name = "secrets-access-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "pods.eks.amazonaws.com"
      }
      Action = "sts:AssumeRole"
      Condition = {
        StringEquals = {
          "eks:cluster-name" = aws_eks_cluster.main.name
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "secrets_access" {
  name = "secrets-access-policy"
  role = aws_iam_role.secrets_access.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ]
      Resource = aws_secretsmanager_secret.db_credentials.arn
    }]
  })
}
```

### Network Security

**Security Groups with least privilege:**

```hcl
# Security group for EKS nodes
resource "aws_security_group" "eks_nodes" {
  name_prefix = "eks-nodes-"
  vpc_id      = aws_vpc.main.id

  # Allow nodes to communicate with each other
  ingress {
    from_port = 0
    to_port   = 65535
    protocol  = "tcp"
    self      = true
  }

  # Allow nodes to communicate with control plane
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.main.cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "eks-nodes-sg"
  }
}
```

---

## Observability

### CloudWatch Logs

```hcl
# CloudWatch Log Group for EKS
resource "aws_cloudwatch_log_group" "eks_cluster" {
  name              = "/aws/eks/${var.cluster_name}/cluster"
  retention_in_days = 30

  kms_key_id = aws_kms_key.logs.arn

  tags = {
    Environment = var.environment
  }
}
```

### CloudWatch Metrics

```hcl
# Custom metric alarm
resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "eks-node-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EKS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Alert when CPU exceeds 80%"

  dimensions = {
    ClusterName = aws_eks_cluster.main.name
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
}
```

---

## Cost Optimization

### Right-Sizing

```hcl
# Use appropriate instance types
resource "aws_eks_node_group" "main" {
  # Use burstable instances for dev/test
  instance_types = var.environment == "production" ?
    ["m5.large", "m5.xlarge"] :
    ["t3.medium", "t3.large"]

  # ... other config
}
```

### Spot Instances

```hcl
# Spot instances for non-critical workloads
resource "aws_eks_node_group" "spot" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "spot"
  capacity_type   = "SPOT"
  instance_types  = ["t3.medium", "t3.large", "t3a.medium"]

  # ... other config

  taints {
    key    = "spot"
    value  = "true"
    effect = "NO_SCHEDULE"
  }
}
```

---

## Disaster Recovery

### Multi-Region

```hcl
# Primary region
module "eks_primary" {
  source = "./modules/eks-cluster"
  providers = {
    aws = aws.us_east_1
  }
  # ... config
}

# Secondary region (DR)
module "eks_secondary" {
  source = "./modules/eks-cluster"
  providers = {
    aws = aws.us_west_2
  }
  # ... config
}
```

### Backups

```hcl
# RDS automated backups
resource "aws_db_instance" "main" {
  # ... config

  backup_retention_period = 7
  backup_window           = "03:00-04:00"
  maintenance_window      = "mon:04:00-mon:05:00"

  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
}
```

---

## Performance Optimization

### Database Optimization

```hcl
# Read replicas for read-heavy workloads
resource "aws_db_instance" "replica" {
  identifier              = "app-db-replica"
  replicate_source_db     = aws_db_instance.main.identifier
  instance_class          = "db.t3.medium"
  publicly_accessible    = false
  vpc_security_group_ids  = [aws_security_group.db.id]
  db_subnet_group_name    = aws_db_subnet_group.db.name

  performance_insights_enabled = true
  performance_insights_retention_period = 7
}

# Connection pooling with RDS Proxy
resource "aws_db_proxy" "main" {
  name                   = "app-db-proxy"
  engine_family          = "POSTGRESQL"
  vpc_subnet_ids         = aws_subnet.private[*].id
  vpc_security_group_ids = [aws_security_group.db_proxy.id]

  auth {
    auth_scheme = "SECRETS"
    secret_arn  = aws_secretsmanager_secret.db_credentials.arn
  }
}
```

### Lambda Optimization

```hcl
# Provisioned concurrency for predictable workloads
resource "aws_lambda_provisioned_concurrency_config" "api" {
  function_name                     = aws_lambda_function.api.function_name
  qualifier                         = aws_lambda_function.api.version
  provisioned_concurrent_executions = 10
}

# Reserved concurrency to prevent overconsumption
resource "aws_lambda_function" "api" {
  function_name = "api-handler"
  runtime       = "python3.14"
  handler       = "index.handler"

  reserved_concurrent_executions = 100  # Limit concurrent executions
}
```

---

## Troubleshooting & Debugging

### EKS Cluster Issues

**Pod Not Starting:**

```bash
# Check pod events
kubectl describe pod <pod-name> -n <namespace>

# Check node capacity
kubectl top nodes

# Check resource quotas
kubectl describe quota -n <namespace>

# Check node group status
aws eks describe-nodegroup \
  --cluster-name <cluster-name> \
  --nodegroup-name <nodegroup-name>
```

**Pod Identity Not Working:**

```bash
# Verify Pod Identity association
aws eks describe-pod-identity-association \
  --cluster-name <cluster-name> \
  --association-id <association-id>

# Check service account
kubectl describe serviceaccount <sa-name> -n <namespace>

# Test credentials in pod
kubectl exec -it <pod-name> -n <namespace> -- \
  aws sts get-caller-identity
```

### VPC Lattice Issues

**Service Not Accessible:**

```bash
# Check service network association
aws vpclattice get-service-network \
  --service-network-identifier <network-id>

# Check service association
aws vpclattice get-service \
  --service-identifier <service-id>

# Check target group health
aws vpclattice get-target-group \
  --target-group-identifier <tg-id>

# Test connectivity
curl -v https://<service-dns-name>
```

---

## Review Checklist

When reviewing AWS infrastructure, check:

- [ ] Zero Trust principles applied (private subnets, VPC endpoints, VPC Lattice)
- [ ] IAM roles use least privilege
- [ ] Encryption enabled (at rest and in transit)
- [ ] Secrets managed securely (Secrets Manager/Parameter Store)
- [ ] Network security groups are restrictive
- [ ] EKS cluster is properly configured
- [ ] **Pod Identity used for pod AWS access** (preferred over IRSA for EKS 1.24+)
- [ ] **VPC Lattice configured** for cross-VPC/service communication (Zero Trust)
- [ ] Observability configured (CloudWatch, logs, metrics)
- [ ] Cost optimization applied (right-sizing, spot instances)
- [ ] Disaster recovery plan in place
- [ ] Infrastructure as Code (Terraform/CloudFormation)
- [ ] Tags applied consistently
- [ ] Cross-VPC access uses VPC Lattice (not VPC peering)
