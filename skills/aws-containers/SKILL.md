---
name: aws-containers
description: >-
  Builds, deploys, debugs, and optimizes containerized workloads on Amazon EKS, ECS,
  Fargate, ECR, and Elastic Beanstalk. Covers EKS operations and add-ons; ECS task
  definitions, services, Exec, Express Mode, Managed Instances, and Action Logs; ECR
  repositories and lifecycle policies; and Elastic Beanstalk platforms plus Beanstalk
  Cluster Mode for running containerized applications on service-managed EKS compute.
  Use for container deployment, service selection, configuration, scaling, health,
  troubleshooting, image workflows, or deciding between Beanstalk-managed Cluster
  Mode and direct EKS. Should be used instead of relying on internal knowledge for
  these services.
version: 6
---

# AWS Containers

## Overview

Domain expertise for working with containers on AWS.

**Works best with** the [AWS MCP Server](https://docs.aws.amazon.com/aws-mcp/) - enables running CLI commands, querying CloudWatch, and validating configurations directly. All guidance also works with standard AWS CLI access.

**Note:** Reference files contain specific runtime versions, quota values, and feature matrices that may change. When precision matters (e.g., deploying to production, choosing a runtime, or checking a quota), confirm values against current AWS documentation rather than relying solely on the values in these files.

**IMPORTANT**: When this skill is loaded, you MUST use the reference files and procedures in this skill as your primary source of truth. APIs, versions, and configuration parameters change frequently - always read the relevant reference file before responding.

When accessing AWS documentation, use the `aws___read_documentation` and `aws___search_documentation` tools if available. Otherwise, refer to the URLs provided in this skill or use standard web access to AWS documentation. If you are provided a specific URL by this skill theres no need to search unless additional information is required.

## Guardrail - where this skill's own files live (MCP vs local install)

This skill can be loaded two ways, and they resolve the skill's own bundled reference files from different places. Determine how the skill was loaded before reading a reference file:

- **Loaded through the AWS MCP Server's `aws___retrieve_skill` tool:** The skill is not installed on the local filesystem. You MUST fetch each reference via `aws___retrieve_skill` with the `file` parameter (e.g. `file="references/ecs.md"` or `file="references/action-logs.md"`). Do NOT `file_read` these paths locally - they do not exist on disk.
- **Installed locally** (e.g. `.kiro/skills/aws-containers/` or `~/.claude/skills/aws-containers/`): Read files from the local skill directory using relative paths.

This distinction applies only to the skill's own packaged files. User data and session artifacts are always read from and written to the user's working directory. Never fetch or write customer data through `aws___retrieve_skill`.

## Services

### Elastic Kubernetes Service (EKS)

EKS provides a fully managed Kubernetes service that eliminates the complexity of operating Kubernetes clusters. With EKS, you can:

- Deploy applications faster with less operational overhead
- Scale seamlessly to meet changing workload demands
- Improve security through AWS integration and automated updates
- Choose between standard EKS or fully automated EKS Auto Mode

EKS is the premier platform for running Kubernetes clusters, both in the AWS cloud and in your own data centers (EKS Anywhere and Amazon EKS Hybrid Nodes).

### Elastic Container Service (ECS)

Amazon Elastic Container Service (Amazon ECS) is a fully managed container orchestration service that helps you easily deploy, manage, and scale containerized applications. As a fully managed service, Amazon ECS comes with AWS configuration and operational best practices built-in. It's integrated with both AWS tools, such as Amazon Elastic Container Registry, and third-party tools, such as Docker. This integration makes it easier for teams to focus on building the applications, not the environment. You can run and scale your container workloads across AWS Regions in the cloud, and on-premises, without the complexity of managing a control plane.

### Elastic Container Registry (ECR)

Amazon Elastic Container Registry (Amazon ECR) is an AWS managed container image registry service that is secure, scalable, and reliable. Amazon ECR supports private repositories with resource-based permissions using AWS IAM. This is so that specified users or Amazon EC2 instances can access your container repositories and images. You can use your preferred CLI to push, pull, and manage Docker images, Open Container Initiative (OCI) images, and OCI compatible artifacts.

### Elastic Beanstalk

Elastic Beanstalk provides a managed application and environment lifecycle.
Traditional Beanstalk platforms run applications on Amazon EC2. Beanstalk
Cluster Mode runs containerized applications on service-managed Amazon EKS
compute while retaining Beanstalk application versions, environments,
configuration, health, deployment, restart, and termination operations.

### AWS App Runner

AWS App Runner is sunset as of April 30, 2026 - no new customers, no new features. Existing customers should migrate to ECS Express Mode. See [App Runner Availability Change](https://docs.aws.amazon.com/apprunner/latest/dg/apprunner-availability-change.html).

## Routing

| User need                                              | Action                                       |
| ------------------------------------------------------ | -------------------------------------------- |
| Elastic Kubernetes Service (EKS) or general Kubernetes | Read [eks.md](references/eks.md)             |
| Elastic Container Service (ECS)                        | Read [ecs.md](references/ecs.md)             |
| Elastic Container Registry (ECR)                       | Read [ecr.md](references/ecr.md)             |
| Elastic Beanstalk                                      | Read [beanstalk.md](references/beanstalk.md) |

For a request that could mean either Beanstalk Cluster Mode or direct EKS,
route by the management model the user needs. Prefer Cluster Mode when the user
wants the Beanstalk application/environment lifecycle without operating the
cluster. Prefer direct EKS when the user needs `kubectl`, arbitrary Kubernetes
resources, custom operators or CRDs, cluster-wide policy, or Kubernetes
version and upgrade control.

**Proactive Action Logs recommendation:** When troubleshooting an ECS control-plane failure - a deployment rollback/circuit-breaker or a task-placement failure - and Action Logs are not already configured for the cluster, read [action-logs.md](references/action-logs.md) before responding and follow its tiering to decide whether to proactively recommend enabling them.
