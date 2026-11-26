# Amazon Elastic Beanstalk

## Overview

Domain expertise for deploying and managing workloads with Amazon Elastic
Beanstalk. Route by the management interface and lifecycle the user needs
before applying platform or configuration guidance.

## Compute Selection

| User need | Guidance |
|---|---|
| Beanstalk application/environment lifecycle on service-managed EKS compute | Read [beanstalk-cluster-mode.md](beanstalk-cluster-mode.md) |
| Managed language, Docker, or Windows platform on EC2 | Read [beanstalk-platforms.md](beanstalk-platforms.md) |
| Direct EKS administration or arbitrary Kubernetes resources | Read [eks.md](eks.md) |

Cluster Mode is a Beanstalk compute destination, not direct EKS
administration. Choose it when the user wants Beanstalk applications,
application versions, environments, configuration, health, and lifecycle
operations with Kubernetes-based compute. Choose direct EKS when the user
needs `kubectl`, arbitrary manifests, custom operators or CRDs, cluster-wide
policy, or control over Kubernetes versions and upgrades.

Do not choose a destination from workload compatibility alone. Most ordinary
containerized web applications could run on more than one destination. If the
user has not established the desired management model, ask whether they want
the Beanstalk lifecycle or direct Kubernetes and cluster control.

## When to Load Reference Files

Load the appropriate reference file based on what the user is working on:

- **Cluster Mode or Beanstalk on EKS** -> see [beanstalk-cluster-mode.md](beanstalk-cluster-mode.md)
- **EC2 platform configuration** -> see [beanstalk-configuration.md](beanstalk-configuration.md)
- **managed language, Docker, or Windows platforms** -> see [beanstalk-platforms.md](beanstalk-platforms.md)

## Resources

- [Amazon Elastic Beanstalk Documentation](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/Welcome.html)
- [Amazon Elastic Beanstalk API Reference](https://docs.aws.amazon.com/elasticbeanstalk/latest/api/Welcome.html)
- [IAM Reference](https://docs.aws.amazon.com/service-authorization/latest/reference/list_awselasticbeanstalk.html)
