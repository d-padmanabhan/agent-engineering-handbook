# Elastic Beanstalk Cluster Mode

## Purpose and Boundary

Beanstalk Cluster Mode runs containerized Elastic Beanstalk environments on
service-managed Amazon EKS compute. Customers continue to use Beanstalk
applications, application versions, environments, configuration settings,
health, and lifecycle operations. Beanstalk manages cluster placement and
translates supported environment settings into the Kubernetes resources that
run the application.

Use Cluster Mode when the user wants:

- The Beanstalk application and environment lifecycle on Kubernetes-based
  compute.
- To deploy an existing container image or have Beanstalk build an image from
  application source.
- Beanstalk-managed deployment, health, restart, rollback, load balancing,
  scaling, and termination without operating an EKS cluster directly.

Use direct EKS instead when the user needs `kubectl`, arbitrary Kubernetes
manifests, custom operators or CRDs, cluster-wide policy, direct cluster
administration, or control over Kubernetes versions and upgrades. Do not
choose between Cluster Mode and direct EKS from workload compatibility alone;
route by the required management model.

Before recommending or executing a deployment, verify that Cluster Mode is
available for the target account and Region. Do not substitute traditional
Beanstalk platform settings when Cluster Mode is unavailable.

## Service-Managed Infrastructure

Treat the EKS cluster and generated Kubernetes resources as service-managed.
Use Beanstalk operations and settings instead of directly editing generated
Deployments, Services, Ingresses, node pools, or other resources.

Multiple compatible Cluster Mode environments may share a managed EKS Auto
Mode cluster. This usually does not change application deployment, but it
matters for cluster-compatible networking and placement settings, shared
cluster-scoped capacity or limits, and lifecycle:

- Do not delete the EKS cluster to remove one environment.
- Terminate the target Beanstalk environment through `TerminateEnvironment`.
- Terminating one environment does not imply that the underlying shared
  cluster is deleted.

## API Compatibility

Cluster Mode uses a supported subset of existing Elastic Beanstalk APIs; it
does not introduce a separate Cluster Mode API family.

| Area | Supported operations |
|---|---|
| Application versions | `CreateApplicationVersion`, `UpdateApplicationVersion`, `DeleteApplicationVersion`, `DescribeApplicationVersions` |
| Environment lifecycle | `CreateEnvironment`, `UpdateEnvironment`, `TerminateEnvironment`, `RestartAppServer`, `DescribeEnvironments` |
| Configuration | `DescribeConfigurationOptions`, `DescribeConfigurationSettings` |
| Health and resources | `DescribeEnvironmentHealth`, `DescribeEnvironmentResources` |
| Environment information | `RequestEnvironmentInfo`, `RetrieveEnvironmentInfo` |
| DNS | `SwapEnvironmentCNAMEs` |
| Tags | `UpdateTagsForResource` |

Do not assume that an unlisted Beanstalk operation, request parameter, or
traditional platform option is supported. Use `DescribeConfigurationOptions`
for the Cluster Mode target to discover accepted option names, defaults, and
values before constructing `CreateEnvironment` or `UpdateEnvironment`
requests.

`DescribeEnvironmentResources` represents the EKS-backed environment through
its cluster, load balancers, and scaling triggers. Traditional EC2 resource
fields such as Auto Scaling groups, instances, launch configurations, launch
templates, and queues do not describe Cluster Mode compute.

## Portable Execution

The AWS MCP server is recommended for AWS API discovery and execution, but it
is not required. In clients without the AWS MCP server, use the AWS CLI or an
AWS SDK whose Elastic Beanstalk service model exposes the Cluster Mode
members.

Before using the application-version examples, verify that the installed CLI
model supports `ImageConfiguration`:

```bash
aws elasticbeanstalk create-application-version \
  --generate-cli-skeleton input |
  grep -q '"ImageConfiguration"'
```

If that member is absent, update to a CLI or SDK model that includes the
Cluster Mode launch contract. Do not translate these requests into the legacy
`BuildConfiguration` shape, because it represents a different Beanstalk build
workflow.

## Creating an Environment

Use `CreateEnvironment` with the Beanstalk application name, environment name,
application-version label, Cluster Mode tier, and
`aws:elasticbeanstalk:eks:*` option settings. The launch canaries use this tier
request:

```json
{
  "Tier": {
    "Name": "Kubernetes",
    "Type": "Standard"
  }
}
```

Some launch-enabled service surfaces describe the resulting tier as
`Name=Cluster, Type=EKS`. Treat that response as Cluster Mode; do not infer an
EC2 platform from the display values. Use the SDK model and
`DescribeConfigurationOptions` for the target account and Region rather than
hard-coding a solution stack or platform ARN.

Portable CLI shape:

```bash
aws elasticbeanstalk create-environment --cli-input-json '{
  "ApplicationName": "orders",
  "EnvironmentName": "orders-cluster",
  "VersionLabel": "v12",
  "Tier": {"Name": "Kubernetes", "Type": "Standard"},
  "OptionSettings": [
    {
      "Namespace": "aws:elasticbeanstalk:eks:environment",
      "OptionName": "service-port",
      "Value": "8080"
    }
  ]
}'
```

## Application Versions

Every Cluster Mode environment deploys a compatible Beanstalk application
version. There are two mutually exclusive ways to create one.

### Existing container image

With a CLI model that exposes `ImageConfiguration`, use:

```bash
aws elasticbeanstalk create-application-version --cli-input-json '{
  "ApplicationName": "orders",
  "VersionLabel": "v12",
  "ImageConfiguration": {
    "Source": {
      "Uri": "123456789012.dkr.ecr.us-east-1.amazonaws.com/orders:v12"
    }
  }
}'
```

For this path:

- Set `ImageConfiguration.Source.Uri` to the container image URI.
- Do not also set `SourceBundle`.
- Do not also set `ImageConfiguration.Build`.
- Ensure the image can run on the environment architecture.

Deploy the resulting version by supplying its `VersionLabel` to
`CreateEnvironment` or `UpdateEnvironment`.

### Build an image from source

Use `CreateApplicationVersion` with `SourceBundle` and
`ImageConfiguration.Build` together. Do not set `ImageConfiguration.Source`.

`ImageConfiguration.Build` requires:

- `CodeBuildServiceRole`.
- `Type` set to `docker` or `buildpack`.

Use a dedicated CodeBuild service role scoped to the required source object,
build logs, output image repository, and any KMS keys used by those resources.
Do not attach broad `FullAccess` policies or service-wide wildcard
permissions.

For a Docker build, set `DockerfileLocation` when the Dockerfile is not at the
expected root location. For a buildpack build, set a non-empty `Buildpack`.
Set `Architecture` to `amd64` or `arm64` as needed; it defaults to `amd64`.
Set `Process` to true to start the processing and image-build workflow.

With a CLI model that exposes `ImageConfiguration`, use:

```bash
aws elasticbeanstalk create-application-version --cli-input-json '{
  "ApplicationName": "orders",
  "VersionLabel": "v13",
  "SourceBundle": {
    "S3Bucket": "my-source-bucket",
    "S3Key": "orders/v13.zip"
  },
  "ImageConfiguration": {
    "Build": {
      "Type": "docker",
      "CodeBuildServiceRole": "arn:aws:iam::123456789012:role/BeanstalkImageBuild",
      "DockerfileLocation": "deploy/Dockerfile",
      "Architecture": "amd64"
    }
  },
  "Process": true
}'
```

Wait for application-version processing to complete successfully before
deploying it.

### Architecture compatibility

The environment architecture is configured by
`aws:elasticbeanstalk:eks:environment / arch` and defaults to `amd64`.
For source-built versions, the application-version image architecture must
match the environment architecture. If an `arm64` version is rejected by an
environment using the default:

- Set the environment architecture to `arm64` and use compatible Graviton
  capacity, or
- Rebuild the application version for `amd64`.

## Environment Configuration

Cluster Mode option namespaces begin with `aws:elasticbeanstalk:eks`. Do not
reuse traditional EC2-based Beanstalk namespaces or `.ebextensions` behavior
unless Cluster Mode documentation explicitly supports them.

Important customer-facing groups include:

| Namespace | Purpose and representative options |
|---|---|
| `aws:elasticbeanstalk:eks:environment` | `cpu`, `cpu-limit`, `memory`, `memory-limit`, `service-port`, `load-balancer-type`, `env-variables`, `secrets`, `arch`, `instance-category`, `node-pool`, ingress groups and allowlists |
| `aws:elasticbeanstalk:eks:environment:deployment` | deployment `strategy` |
| `aws:elasticbeanstalk:eks:environment:deployment:strategy:rolling` | `max-surge`, `max-unavailable` |
| `aws:elasticbeanstalk:eks:environment:readiness-probe` | enablement, HTTP path and port, timing, thresholds, headers |
| `aws:elasticbeanstalk:eks:environment:liveness-probe` | enablement, HTTP path and port, timing, thresholds, headers |
| `aws:elasticbeanstalk:eks:environment:startup-probe` | enablement, HTTP path and port, timing, thresholds, headers |
| `aws:elasticbeanstalk:eks:environment:autoscaling` | `min-replica`, `max-replica`, polling interval, cooldown |
| `aws:elasticbeanstalk:eks:environment:autoscaling:trigger` | CPU, memory, cron, or metrics-API trigger settings |
| `aws:elasticbeanstalk:eks:environment:autoscaling:behavior` | scale-up and scale-down policy settings |
| `aws:elasticbeanstalk:eks:alb` | ALB selection, scheme, subnets, security groups, listeners, TLS, health checks, attributes, and tags |
| `aws:elasticbeanstalk:eks:observability` | metrics, logs, and traces backends and endpoints |

Use the exact `Namespace`, `OptionName`, and string `Value` returned by
`DescribeConfigurationOptions`. Do not expose service-managed role or
placement settings merely because they appear in a configuration response.

For sensitive configuration:

- Put credentials and other secret values in AWS Secrets Manager. Set the
  `secrets` option to a JSON mapping of container variable names to Secrets
  Manager ARNs; do not place secret values in `env-variables`.
- Scope the application role to `secretsmanager:GetSecretValue` on only the
  referenced secret ARNs, plus `kms:Decrypt` on the applicable KMS keys when
  customer-managed encryption keys are used.
- Do not echo resolved secrets in responses, diagnostic output, application
  logs, or configuration examples.

For an internet-facing ALB, prefer an HTTPS listener with an ACM certificate,
a supported TLS policy, and HTTP-to-HTTPS redirect. Restrict inbound access
with security-group references or the narrowest practical CIDRs instead of
`0.0.0.0/0`. Consider AWS WAF for public applications and apply
authentication, rate limiting, and security headers at the appropriate
application or edge layer.

Common defaults include:

- CPU request: `250m`.
- Memory request: `512Mi`; memory limit: `1Gi`.
- Service port: `8080`; the port is injected into the container as `PORT`.
- Load balancer type: `ALB`; use `none` when no load balancer is wanted.
- Architecture: `amd64`.
- Deployment strategy: `RollingUpdate`, with max surge `1` and max
  unavailable `0`.
- Readiness, liveness, and startup probes disabled until enabled.
- Autoscaling minimum `1` and maximum `10`.

Treat these values as discoverable defaults, not a substitute for querying the
target's configuration options.

## Operations and Diagnostics

For creation or updates:

1. Create or select a compatible application version.
2. Query Cluster Mode configuration options.
3. Create or update the Beanstalk environment with the version label and
   Cluster Mode option settings.
4. Observe environment status and enhanced health until the operation
   completes or rolls back.

Portable CLI operations include:

```bash
aws elasticbeanstalk describe-environments \
  --application-name orders \
  --environment-names orders-cluster

aws elasticbeanstalk update-environment \
  --environment-name orders-cluster \
  --version-label v13

aws elasticbeanstalk restart-app-server \
  --environment-name orders-cluster
```

For a degraded environment, begin with:

- `DescribeEnvironments` for status and deployed version.
- `DescribeEnvironmentHealth` for health state and causes.
- `RequestEnvironmentInfo` and `RetrieveEnvironmentInfo` for supported
  diagnostic information.
- `DescribeConfigurationSettings` to inspect effective settings.
- `DescribeApplicationVersions` to check processing status.
- `DescribeEnvironmentResources` for the managed cluster, load balancers, and
  scaling triggers.

`RestartAppServer` restarts the environment's managed Kubernetes workload.
Do not begin by editing generated Kubernetes resources directly.

For termination, use `TerminateEnvironment` and let Beanstalk clean up the
environment's managed workload and supporting resources according to the
termination request. Confirm destructive intent before executing the
operation.

After confirmation, the portable CLI form is:

```bash
aws elasticbeanstalk terminate-environment \
  --environment-name orders-cluster
```

## Security Considerations

- Encrypt application source, container images, secrets, logs, and telemetry
  at rest. Use customer-managed KMS keys when organizational policy requires
  control beyond service-managed encryption.
- Use TLS for ALB listeners and custom observability endpoints. Store ACM
  certificate ARNs in supported settings; never embed private keys or
  credentials in configuration.
- Use narrowly scoped IAM roles for image builds, application pods, and
  observability components. Prefer role-based temporary credentials and avoid
  IAM users or long-lived access keys.
- Enable and retain the logging needed to investigate deployments and access,
  including CloudTrail management events, application logs, and appropriate
  ALB access logs and CloudWatch alarms. Encrypt destinations that can contain
  customer or sensitive data.
- Treat configuration responses, environment information, diagnostic bundles,
  and logs as potentially sensitive. Redact secrets and limit access and
  retention according to the application's data classification.
