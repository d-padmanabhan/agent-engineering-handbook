# Kubernetes Patterns

## ConfigMap and Secret

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  LOG_LEVEL: "INFO"
  API_URL: "https://api.acme.com"
---
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
type: Opaque
stringData:
  DB_PASSWORD: "secret-value"
---
# Using in Deployment
containers:
  - name: app
    envFrom:
      - configMapRef:
          name: app-config
      - secretRef:
          name: app-secrets
    env:
      - name: SPECIFIC_VAR
        valueFrom:
          configMapKeyRef:
            name: app-config
            key: LOG_LEVEL
```

## Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: app
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

## Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - app.acme.com
      secretName: app-tls
  rules:
    - host: app.acme.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: app
                port:
                  number: 80
```

## Kustomize (bases + overlays)

Use Kustomize when you want environment overlays without templating.

**Common commands:**

```bash
# Preview rendered YAML
kubectl kustomize overlays/dev

# Diff before apply
kubectl diff -k overlays/dev

# Apply an overlay
kubectl apply -k overlays/dev
```

**Minimal file layout:**

```text
kustomize/
  base/
    kustomization.yaml
    deployment.yaml
    service.yaml
  overlays/
    dev/
      kustomization.yaml
    prod/
      kustomization.yaml
```

> [!IMPORTANT]
> Do not generate or commit Secrets via Kustomize generators. Keep secrets in a secret manager or external secret mechanism.

## RBAC

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-sa
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: app-role
rules:
  - apiGroups: [""]
    resources: ["configmaps", "secrets"]
    verbs: ["get", "list"]
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: app-rolebinding
subjects:
  - kind: ServiceAccount
    name: app-sa
roleRef:
  kind: Role
  name: app-role
  apiGroup: rbac.authorization.k8s.io
```

## Network Policy

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: app-network-policy
spec:
  podSelector:
    matchLabels:
      app: my-app
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 8080
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: database
      ports:
        - protocol: TCP
          port: 5432
```

## Pod Disruption Budget

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: my-app
```

## Pod Placement and Scheduling

Choose placement controls from the scheduling outcome:

- **Taints repel Pods.** A matching toleration permits a Pod onto a tainted
  node, but does not require or prefer that node.
- **Node affinity selects nodes.** Combine it with taints and tolerations when
  a workload must run only on a dedicated node pool.
- **Pod affinity and anti-affinity** co-locate or separate Pods relative to
  other Pods.
- **Topology spread constraints** balance matching replicas across zones,
  nodes, or other labeled failure domains.

`requiredDuringSchedulingIgnoredDuringExecution` and `DoNotSchedule` are hard
constraints. Use them only when every supported cluster shape has enough
matching capacity. `preferredDuringSchedulingIgnoredDuringExecution` and
`ScheduleAnyway` are soft constraints that preserve scheduling when the ideal
placement is unavailable.

### Dedicated Node Pool

Use both a taint and trusted node affinity for exclusive placement:

```yaml
spec:
  template:
    metadata:
      labels:
        app: payments-api
    spec:
      tolerations:
        - key: dedicated
          operator: Equal
          value: payments
          effect: NoSchedule
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
              - matchExpressions:
                  - key: acme.com.node-restriction.kubernetes.io/workload
                    operator: In
                    values:
                      - payments
```

The matching node configuration is:

```text
taint:
  dedicated=payments:NoSchedule

label:
  acme.com.node-restriction.kubernetes.io/workload=payments
```

Use the Node authorizer and `NodeRestriction` admission plugin for
security-sensitive placement labels. A compromised kubelet must not be able to
label itself into a privileged workload pool.

Taint effects have different lifecycle behavior:

- `NoSchedule`: blocks new non-tolerating Pods but does not evict existing
  Pods.
- `PreferNoSchedule`: soft repulsion.
- `NoExecute`: blocks new Pods and evicts existing non-tolerating Pods.
- `tolerationSeconds`: temporarily tolerates a matching `NoExecute` taint
  before eviction.

### Replica Distribution

Use topology spread when the goal is an even replica count across failure
domains:

```yaml
spec:
  template:
    metadata:
      labels:
        app: payments-api
    spec:
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: payments-api
        - maxSkew: 1
          topologyKey: kubernetes.io/hostname
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels:
              app: payments-api
```

`topologyKey` names the node label whose distinct values define scheduling
domains. `labelSelector` identifies the Pods counted in the skew calculation
and must match the intended pod-template labels. With `DoNotSchedule`,
`maxSkew` is a hard scheduling threshold across eligible domains. With
`ScheduleAnyway`, the scheduler uses skew to score nodes but may place a Pod
even when the resulting skew exceeds `maxSkew`.

The zone constraint is hard; the hostname preference is soft. Validate that
the cluster has enough labeled, eligible zones before using `DoNotSchedule`.
Missing topology labels or insufficient capacity can leave Pods Pending.

Use pod anti-affinity when placement depends on the presence of another
workload rather than an even count:

```yaml
spec:
  template:
    metadata:
      labels:
        app: payments-api
    spec:
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                topologyKey: kubernetes.io/hostname
                labelSelector:
                  matchLabels:
                    app: payments-api
```

Prefer soft pod anti-affinity for ordinary replica separation. Hard
inter-pod affinity and anti-affinity can be expensive in large clusters and
can deadlock rollouts when topology, capacity, or labels do not satisfy every
term.

Placement controls complement, but do not replace, resource requests,
PodDisruptionBudgets, autoscaling, and capacity planning. Test scheduling
against minimum, degraded, and upgrade cluster shapes.

Authoritative references:

- [Assigning Pods to Nodes](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/)
- [Taints and Tolerations](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/)
- [Pod Topology Spread Constraints](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/)

## Jobs and CronJobs

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: backup
spec:
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: backup
              image: backup:1.0.0
              args: ["--bucket", "my-backup-bucket"]
          restartPolicy: OnFailure
```

## Init Containers

```yaml
spec:
  initContainers:
    - name: wait-for-db
      image: busybox:1.36
      command: ['sh', '-c', 'until nc -z db 5432; do sleep 2; done']
    - name: migrate
      image: myapp:1.0.0
      command: ['./migrate']
  containers:
    - name: app
      image: myapp:1.0.0
```
