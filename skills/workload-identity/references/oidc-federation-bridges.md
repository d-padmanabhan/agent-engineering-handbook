# OIDC Federation Bridges - SPIRE to Cloud IAM

How to trade a JWT-SVID for cloud credentials, with no static cloud keys.

---

## The pattern

```
Workload --> Workload API --> JWT-SVID
              |
              v
SPIRE OIDC Discovery Provider (.well-known/openid-configuration)
              |
              v
Cloud STS / federation endpoint
              |
              v
Short-lived cloud credential
```

The cloud trusts the SPIRE issuer; the trust policy pins the `sub` claim to a specific SPIFFE ID. No long-lived key on the cloud side, no long-lived key on the workload side.

---

## SPIRE OIDC Discovery Provider

Deploy `spire-oidc-discovery-provider` as a Deployment with an HTTPS-fronted endpoint at a stable URL (e.g., `https://spiffe-oidc.example.com`).

Required endpoints:

- `/.well-known/openid-configuration`
- `/keys` (JWKS)

URL stability matters more than perfection - changing it is a coordinated change across every cloud trust policy.

---

## AWS

### Register the OIDC provider

```hcl
resource "aws_iam_openid_connect_provider" "spire" {
  url             = "https://spiffe-oidc.example.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.spire.certificates[0].sha1_fingerprint]
}
```

### Trust policy on the target role

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::ACCOUNT:oidc-provider/spiffe-oidc.example.com"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "spiffe-oidc.example.com:sub": "spiffe://prod.example.com/ns/payments/sa/checkout",
        "spiffe-oidc.example.com:aud": "sts.amazonaws.com"
      }
    }
  }]
}
```

### Workload code

```python
import jwt
from spiffe import WorkloadApiClient
import boto3

with WorkloadApiClient() as client:
    jwt_svid = client.fetch_jwt_svid(audience="sts.amazonaws.com")
    sts = boto3.client("sts")
    creds = sts.assume_role_with_web_identity(
        RoleArn="arn:aws:iam::ACCOUNT:role/payments-checkout",
        RoleSessionName="checkout-session",
        WebIdentityToken=jwt_svid.token,
    )
```

### Hardening

- Always pin `sub` to a specific SPIFFE ID (or a tight prefix). Never trust the issuer alone.
- Pin `aud` to `sts.amazonaws.com` (or the audience your role expects).
- Region-pin where possible.
- Use IAM Access Analyzer to flag overly permissive trust policies.

---

## GCP

### Workload Identity Pool + Provider

```hcl
resource "google_iam_workload_identity_pool" "spire" {
  workload_identity_pool_id = "spire-prod"
  display_name             = "SPIRE prod trust domain"
}

resource "google_iam_workload_identity_pool_provider" "spire" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.spire.workload_identity_pool_id
  workload_identity_pool_provider_id = "spiffe"
  display_name                       = "SPIFFE OIDC"
  oidc {
    issuer_uri = "https://spiffe-oidc.example.com"
  }
  attribute_mapping = {
    "google.subject" = "assertion.sub"
  }
  attribute_condition = "assertion.sub == 'spiffe://prod.example.com/ns/payments/sa/checkout'"
}
```

### Bind to a service account

```hcl
resource "google_service_account_iam_binding" "spire_sa" {
  service_account_id = google_service_account.checkout.name
  role               = "roles/iam.workloadIdentityUser"
  members = [
    "principal://iam.googleapis.com/projects/PROJECT/locations/global/workloadIdentityPools/spire-prod/subject/spiffe://prod.example.com/ns/payments/sa/checkout"
  ]
}
```

### Workload code

```python
from spiffe import WorkloadApiClient
from google.auth.external_account import Credentials

with WorkloadApiClient() as client:
    jwt_svid = client.fetch_jwt_svid(
        audience="//iam.googleapis.com/projects/PROJECT/locations/global/workloadIdentityPools/spire-prod/providers/spiffe"
    )
    # Exchange via the GCP STS endpoint, then impersonate the SA
```

---

## Azure

### Federated credential on a User-Assigned Managed Identity

```hcl
resource "azurerm_federated_identity_credential" "spire" {
  name                = "spire-checkout"
  resource_group_name = azurerm_resource_group.example.name
  parent_id           = azurerm_user_assigned_identity.checkout.id
  audience            = ["api://AzureADTokenExchange"]
  issuer              = "https://spiffe-oidc.example.com"
  subject             = "spiffe://prod.example.com/ns/payments/sa/checkout"
}
```

### Workload code

```python
from spiffe import WorkloadApiClient
from azure.identity import ClientAssertionCredential

with WorkloadApiClient() as client:
    jwt_svid = client.fetch_jwt_svid(audience="api://AzureADTokenExchange")
    cred = ClientAssertionCredential(
        tenant_id="...",
        client_id="<UAMI client id>",
        func=lambda: jwt_svid.token,
    )
```

---

## HashiCorp Vault

### `auth/jwt` config

```bash
vault auth enable jwt
vault write auth/jwt/config \
  oidc_discovery_url=https://spiffe-oidc.example.com

vault write auth/jwt/role/checkout \
  role_type=jwt \
  bound_audiences=vault \
  user_claim=sub \
  bound_subject="spiffe://prod.example.com/ns/payments/sa/checkout" \
  policies=checkout
```

### Workload code

```python
from spiffe import WorkloadApiClient
import hvac

with WorkloadApiClient() as client:
    jwt_svid = client.fetch_jwt_svid(audience="vault")
    vault = hvac.Client(url="https://vault.example.com")
    vault.auth.jwt.jwt_login(role="checkout", jwt=jwt_svid.token)
```

---

## Common cross-cloud anti-patterns

- **Trust the issuer without binding `sub`.** Anyone with a SPIRE-issued JWT for any workload can assume the role.
- **Wildcard `sub`.** Same problem, larger blast radius.
- **Long JWT-SVID TTLs.** Defeats the rotation property; keep TTL in minutes.
- **Single audience for all clouds.** Use distinct audiences per cloud / per role; the audience is part of the trust contract.
- **Stable JWKS thumbprint hardcoded into IAM trust policies.** When rotating SPIRE keys, also rotate cloud trust thumbprints. Plan for this.
- **No audit on the cloud side.** CloudTrail / Cloud Audit Logs / Azure Activity Log records every `AssumeRoleWithWebIdentity` / federation - make sure it ships to SIEM.

---

## Related

- Rule: `318-workload-identity.mdc`
- Rule: `412-aws-iam.mdc` (AWS-specific IAM)
- Reference: [spire-on-eks.md](spire-on-eks.md)
- Reference: [spiffe-vs-cloud-iam.md](spiffe-vs-cloud-iam.md)
