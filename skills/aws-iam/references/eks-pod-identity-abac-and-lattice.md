# EKS Pod Identity ABAC tags + VPC Lattice auth policies (namespace scoping)

EKS Pod Identity attaches a predefined set of **session tags** to the temporary credentials it vends to pods.
Those tags can be used as **principal tags** for authorization decisions (ABAC).

This is a useful pattern for multi-tenant clusters where you want **namespace-level** authorization boundaries without giving teams a way to broaden access by editing network policies.

> [!IMPORTANT]
> This is **authorization** control (IAM). It does not replace network-level controls for reachability or egress restriction.

## What EKS Pod Identity tags you get

EKS Pod Identity session tags (examples):

- `kubernetes-namespace`
- `kubernetes-service-account`
- `eks-cluster-name`

Docs: `https://docs.aws.amazon.com/eks/latest/userguide/pod-id-abac.html`

## Trust policy: restrict which pods can assume the role

EKS Pod Identity uses:

- `Principal`: `pods.eks.amazonaws.com`
- `Action`: `sts:AssumeRole` and `sts:TagSession`

Docs: `https://docs.aws.amazon.com/eks/latest/userguide/pod-id-role.html`

Example trust policy condition (namespace + service account):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowEksAuthToAssumeRoleForPodIdentity",
      "Effect": "Allow",
      "Principal": { "Service": "pods.eks.amazonaws.com" },
      "Action": ["sts:AssumeRole", "sts:TagSession"],
      "Condition": {
        "StringEquals": {
          "aws:RequestTag/kubernetes-namespace": ["my-namespace"],
          "aws:RequestTag/kubernetes-service-account": ["my-service-account"]
        }
      }
    }
  ]
}
```

## VPC Lattice auth policy: restrict access based on principal tags

VPC Lattice auth policies support **principal tags** (including session tags) via `aws:PrincipalTag/...`.

Docs: `https://docs.aws.amazon.com/vpc-lattice/latest/ug/auth-policies.html`

### Correct invoke action name

VPC Lattice service invocation uses:

- `Action`: `vpc-lattice-svcs:Invoke`

AWS managed policy reference: `https://docs.aws.amazon.com/aws-managed-policy/latest/reference/VPCLatticeServicesInvokeAccess.html`

### Example policy: allow invoke only from a specific namespace

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowNamespace",
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::ACCOUNT:role/multi-tenant-lattice-role" },
      "Action": "vpc-lattice-svcs:Invoke",
      "Resource": "arn:aws:vpc-lattice:REGION:ACCOUNT:service/svc-0123456789abcdef0/*",
      "Condition": {
        "StringEquals": {
          "aws:PrincipalTag/kubernetes-namespace": "my-namespace"
        }
      }
    }
  ]
}
```

## Operational gotchas

- **AuthZ requires both sides**: for a request to succeed, the caller identity permissions and the Lattice auth policy must both allow access (resource policy + identity policy model).
- **SigV4**: if the service or service network auth type is `AWS_IAM`, requests must be signed (see the Lattice docs section on SigV4).
- **Policy formatting**: the Lattice docs note that the policy JSON must not contain newlines or blank lines. If you hit validation errors, try minifying:

```bash
jq -c . policy.json > policy.min.json
```

## IMDS hardening for the underlying nodes

EKS Pod Identity and IRSA replace IMDS for app-side credentials, but the worker nodes still run EC2 and the IMDS endpoint is still reachable from inside containers if you let it be. Treat IMDS at the node level as a separate hardening concern from credential delivery at the app level.

Required on every EKS node group launch template:

```hcl
metadata_options {
  http_endpoint               = "enabled"
  http_tokens                 = "required"   # IMDSv2 only - never optional
  http_put_response_hop_limit = 2            # 2 hops to traverse the container bridge; never default 64
  instance_metadata_tags      = "enabled"
}
```

Why `hop_limit = 2`:

- A pod requesting IMDS traverses one hop into the CNI / kubelet, one hop to the node IMDS endpoint - 2 hops total.
- The AWS default of 64 hops means any process inside any container (or any sidecar, or any process that escapes the container boundary) can reach IMDS. That defeats the entire reason Pod Identity / IRSA exist.
- A hop limit of 1 silently breaks pod-to-IMDS resolution if any app does fall through to IMDS; debugging this is unpleasant. Pick 2 for EKS nodes, document the reasoning in the Terraform comment.

Discipline:

- **Apps should never read IMDS directly on EKS.** Use Pod Identity (preferred) or IRSA. The hop limit is the floor; the right mechanism is the OIDC-vended credential.
- **Block IMDS from pod networking entirely** for hardest-tier workloads via a NetworkPolicy or eBPF rule denying `169.254.169.254/32`. Catches the case where an app library has IMDS fallback you didn't know about.
- **Audit nightly** for nodes that drift to `http_tokens = "optional"`:

  ```bash
  aws ec2 describe-instances \
    --filters "Name=metadata-options.http-tokens,Values=optional" \
              "Name=tag:eks:cluster-name,Values=*" \
    --query "Reservations[].Instances[].[InstanceId,Tags[?Key=='eks:cluster-name'].Value|[0]]" \
    --output table
  ```

See `rules/410-aws.mdc` "Non-negotiable: IMDSv2 only" for the cross-cutting AWS rule, account-wide SCP / AWS Config enforcement, and the migration recipe for legacy instances.
