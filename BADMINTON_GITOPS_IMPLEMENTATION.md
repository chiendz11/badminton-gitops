# Badminton Manager V2 — GitOps Implementation Guide

> Thiết kế dựa trên structure và ownership pattern của `chiendz11/iris-gitops`, nhưng chuyển từ MLOps sang hệ thống web/service của Badminton Manager V2.
>
> `badminton-gitops` là **source of truth cho Kubernetes desired state**. App repo build/publish image; infrastructure repo tạo AWS/EKS/ArgoCD; GitOps repo quyết định cluster đang chạy image/config nào.

## 1. Ownership

```text
badminton_system
  -> source code
  -> tests
  -> Dockerfile
  -> image publish

badminton-infrastructure
  -> AWS
  -> EKS
  -> RDS / Redis / RabbitMQ managed resources
  -> ECR
  -> IAM/IRSA
  -> Route53/ACM
  -> Argo CD bootstrap

badminton-gitops
  -> Deployment
  -> Service
  -> Ingress
  -> ConfigMap
  -> ExternalSecret
  -> HPA
  -> PDB
  -> NetworkPolicy
  -> ServiceMonitor
  -> PrometheusRule
```

App CI không chạy `kubectl apply` production. Argo CD là actor reconcile cluster.

## 2. Những gì không copy từ Iris

Bỏ:

```text
Argo Workflows
Argo Events
Knative
KServe
MLflow
training WorkflowTemplate
model canary lifecycle
model registry workload
S3 dataset event
```

Giữ:

```text
AppProject
App-of-Apps
sync waves
External Secrets
AWS Load Balancer Controller
ExternalDNS
cert-manager nếu dùng
metrics-server
kube-prometheus-stack
ServiceMonitor / PrometheusRule
NetworkPolicy
Kustomize
workload release PR
platform reconcile contract
```

## 3. Repository tree

```text
badminton-gitops/
├── .github/
│   └── workflows/
│       ├── validate.yml
│       ├── workload-release.yml
│       ├── platform-reconcile.yml
│       └── recovery.yml
├── applications/
│   ├── kustomization.yaml
│   ├── project.yaml
│   ├── platform-namespaces.yaml
│   ├── platform-external-secrets.yaml
│   ├── platform-external-secrets-config.yaml
│   ├── platform-monitoring.yaml
│   ├── platform-metrics-server.yaml
│   ├── platform-aws-load-balancer-controller.yaml
│   ├── platform-external-dns.yaml
│   ├── platform-cert-manager.yaml
│   ├── workload-edge.yaml
│   ├── workload-web.yaml
│   ├── workload-admin.yaml
│   ├── workload-api-gateway.yaml
│   ├── workload-identity.yaml
│   ├── workload-booking-core.yaml
│   ├── workload-commerce.yaml
│   ├── workload-social.yaml
│   ├── workload-content.yaml
│   ├── workload-notification.yaml
│   ├── workload-storage.yaml
│   └── workload-ai.yaml
├── platform/
│   ├── namespaces/
│   ├── external-secrets-config/
│   ├── argocd-monitoring/
│   └── policies/
├── environments/
│   └── production/
│       ├── edge/
│       ├── web/
│       ├── admin/
│       ├── api-gateway/
│       ├── identity-service/
│       ├── booking-core/
│       ├── commerce-service/
│       ├── social-service/
│       ├── content-service/
│       ├── notification-service/
│       ├── storage-service/
│       └── ai-service/
├── contracts/
│   ├── platform-contract-v1.schema.json
│   └── workload-release-v1.schema.json
├── automation/
│   ├── platform_reconcile/
│   └── workload_release/
└── state/
    └── production-platform.json
```

Nếu chỉ có production thì không tạo staging/base-overlay giả. Có staging thật mới thêm `environments/staging`.

## 4. Namespace strategy

Khuyến nghị:

```text
badminton
monitoring
external-secrets
cert-manager
external-dns
argocd
```

Nếu self-host stateful dependencies có thể thêm namespace `data`.

`platform/namespaces` là owner duy nhất của Namespace:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: badminton
  annotations:
    argocd.argoproj.io/sync-options: Prune=false
```

Child Application không lặp Namespace.

## 5. AppProject

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: badminton-production
  namespace: argocd
  annotations:
    argocd.argoproj.io/sync-wave: "-100"
    argocd.argoproj.io/sync-options: Prune=false
spec:
  description: Badminton Manager production

  sourceRepos:
    - https://github.com/chiendz11/badminton-gitops.git
    - https://prometheus-community.github.io/helm-charts
    - https://charts.external-secrets.io
    - https://aws.github.io/eks-charts
    - https://kubernetes-sigs.github.io/external-dns/
    - https://kubernetes-sigs.github.io/metrics-server/
    - https://charts.jetstack.io

  destinations:
    - namespace: "*"
      server: https://kubernetes.default.svc

  clusterResourceWhitelist:
    - group: "*"
      kind: "*"

  namespaceResourceWhitelist:
    - group: "*"
      kind: "*"

  orphanedResources:
    warn: true
```

Không thêm chart repository của KServe/Knative/Argo Workflows.

## 6. App-of-Apps

`applications/kustomization.yaml`:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - project.yaml
  - platform-namespaces.yaml
  - platform-external-secrets.yaml
  - platform-external-secrets-config.yaml
  - platform-monitoring.yaml
  - platform-metrics-server.yaml
  - platform-aws-load-balancer-controller.yaml
  - platform-external-dns.yaml
  - platform-cert-manager.yaml
  - workload-edge.yaml
  - workload-web.yaml
  - workload-admin.yaml
  - workload-api-gateway.yaml
  - workload-identity.yaml
  - workload-booking-core.yaml
  - workload-commerce.yaml
  - workload-social.yaml
  - workload-content.yaml
  - workload-notification.yaml
  - workload-storage.yaml
  - workload-ai.yaml
```

## 7. Sync waves

Gợi ý:

```text
-100 AppProject
 -90 namespaces
 -50 External Secrets
 -49 External Secrets config
 -45 metrics-server
 -40 monitoring
 -38 AWS LB Controller
 -37 ExternalDNS
 -36 cert-manager
   0 shared policy/config
  10 backend workloads
  20 api-gateway
  25 web/admin
  30 ingress/edge
```

Không dùng sync-wave để thay retry/readiness của service.

## 8. Platform monitoring

Giữ kube-prometheus-stack giống Iris:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: platform-monitoring
  namespace: argocd
  annotations:
    argocd.argoproj.io/sync-wave: "-40"
spec:
  project: badminton-production

  source:
    repoURL: https://prometheus-community.github.io/helm-charts
    chart: kube-prometheus-stack
    targetRevision: <PINNED_VERSION>
    helm:
      releaseName: monitoring
      valuesObject:
        grafana:
          sidecar:
            dashboards:
              enabled: true
              searchNamespace: ALL

        prometheus:
          prometheusSpec:
            serviceMonitorSelectorNilUsesHelmValues: false
            podMonitorSelectorNilUsesHelmValues: false
            ruleSelectorNilUsesHelmValues: false

  destination:
    server: https://kubernetes.default.svc
    namespace: monitoring

  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - ServerSideApply=true
```

Prometheus/Grafana thuộc platform; app-specific `ServiceMonitor`/`PrometheusRule` nằm cạnh app.

## 9. External Secrets

`ClusterSecretStore`:

```yaml
apiVersion: external-secrets.io/v1
kind: ClusterSecretStore
metadata:
  name: aws-secrets-manager
spec:
  provider:
    aws:
      service: SecretsManager
      region: ap-southeast-1
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets
            namespace: external-secrets
```

IRSA role ARN lấy từ platform reconcile.

## 10. AWS Load Balancer Controller và ExternalDNS

Giữ pattern Helm Application của Iris. Các giá trị:

```text
clusterName
vpcId
region
roleArn
zoneId
domain
```

đến từ `state/production-platform.json`, không hard-code thủ công lâu dài.

## 11. Workload Application

Ví dụ `applications/workload-booking-core.yaml`:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: workload-booking-core
  namespace: argocd
  annotations:
    argocd.argoproj.io/sync-wave: "10"
spec:
  project: badminton-production

  source:
    repoURL: https://github.com/chiendz11/badminton-gitops.git
    targetRevision: main
    path: environments/production/booking-core

  destination:
    server: https://kubernetes.default.svc
    namespace: badminton

  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - ServerSideApply=true
    retry:
      limit: 10
```

Mỗi deployable có Application riêng để health/history/rollback rõ.

## 12. Layout một workload

```text
environments/production/booking-core/
├── kustomization.yaml
├── service-account.yaml
├── external-secret.yaml
├── migration-job.yaml
├── deployment.yaml
├── service.yaml
├── hpa.yaml
├── pdb.yaml
├── network-policy.yaml
├── servicemonitor.yaml
└── prometheusrule.yaml
```

Không phải service nào cũng cần HPA/PDB ngay.

## 13. Kustomization pattern

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - service-account.yaml
  - external-secret.yaml
  - deployment.yaml
  - service.yaml
  - hpa.yaml
  - pdb.yaml
  - network-policy.yaml
  - servicemonitor.yaml
  - prometheusrule.yaml

configMapGenerator:
  - name: booking-core-config
    namespace: badminton
    literals:
      - PORT=3000
      - REDIS_TLS=true
      - RABBITMQ_VHOST=/badminton
      - LOG_LEVEL=info

generatorOptions:
  disableNameSuffixHash: false

images:
  - name: badminton-booking-core
    newName: <ECR_BOOKING_CORE>
    digest: sha256:<IMMUTABLE_DIGEST>
```

Không dùng `latest`.

## 14. Deployment chuẩn

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: booking-core
  namespace: badminton
  labels:
    app: booking-core
spec:
  replicas: 2

  selector:
    matchLabels:
      app: booking-core

  template:
    metadata:
      labels:
        app: booking-core

    spec:
      serviceAccountName: booking-core

      securityContext:
        runAsNonRoot: true
        seccompProfile:
          type: RuntimeDefault

      containers:
        - name: booking-core
          image: badminton-booking-core
          imagePullPolicy: IfNotPresent

          envFrom:
            - configMapRef:
                name: booking-core-config
            - secretRef:
                name: booking-core-secrets

          ports:
            - name: http
              containerPort: 3000

          startupProbe:
            httpGet:
              path: /health
              port: http
            periodSeconds: 5
            failureThreshold: 30

          readinessProbe:
            httpGet:
              path: /ready
              port: http
            periodSeconds: 10
            timeoutSeconds: 2

          livenessProbe:
            httpGet:
              path: /health
              port: http
            periodSeconds: 10
            timeoutSeconds: 2

          resources:
            requests:
              cpu: 250m
              memory: 256Mi
            limits:
              cpu: "1"
              memory: 1Gi

          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: [ALL]
            readOnlyRootFilesystem: true
```

Resource values phải benchmark rồi chốt.

## 15. Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: booking-core
  namespace: badminton
  labels:
    app: booking-core
spec:
  selector:
    app: booking-core
  ports:
    - name: http
      port: 3000
      targetPort: http
```

Backend internal dùng ClusterIP, không tạo LoadBalancer riêng.

## 16. Public ingress

Một ALB Ingress:

```text
/          -> web
/admin     -> admin
/api       -> api-gateway
/socket.io -> social-service
```

Ví dụ:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: badminton-public
  namespace: badminton
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'
spec:
  rules:
    - host: badminton.example.com
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: api-gateway
                port:
                  name: http
          - path: /socket.io
            pathType: Prefix
            backend:
              service:
                name: social-service
                port:
                  name: http
          - path: /
            pathType: Prefix
            backend:
              service:
                name: web
                port:
                  name: http
```

## 17. API Gateway routes

```text
/api/auth/*          -> identity-service
/api/users/*         -> identity-service
/api/centers/*       -> booking-core
/api/courts/*        -> booking-core
/api/bookings/*      -> booking-core
/api/pass-posts/*    -> booking-core
/api/commerce/*      -> commerce-service
/api/social/*        -> social-service
/api/content/*       -> content-service
/api/notifications/* -> notification-service
/api/storage/*       -> storage-service
/api/ai/*            -> ai-service
```

Trong cùng namespace có thể dùng DNS:

```text
http://booking-core:3000
http://ai-service:8000
```

## 18. Booking Core boundary

Một Deployment duy nhất:

```text
booking-core
```

Dù code chứa:

```text
Center
Court
Pricing
Availability
Reservation
Booking
Payment
Pass Marketplace
```

Không tạo Deployment riêng cho từng module vì đó là modular monolith.

Dependencies:

```text
Booking PostgreSQL
Redis
RabbitMQ
PayOS
```

## 19. Identity

Secrets:

```text
DATABASE_URL
JWT signing material
OAuth credentials
```

Có migration Job cho Prisma.

## 20. Commerce

Một deployment chứa product/inventory/stock/sale/invoice/reporting. Dùng Commerce PostgreSQL.

## 21. Social

Social là service riêng vì WebSocket.

```text
Social Pods
  -> MongoDB
  -> Redis adapter
  -> Booking Core chat-context read API
```

Khi >1 replica phải dùng Socket.IO Redis Adapter.

NetworkPolicy phải cho:

```text
Ingress/ALB -> Social
Social -> Redis
Social -> MongoDB
Social -> Booking Core internal endpoint
```

Social không query Booking DB.

## 22. Notification

```text
RabbitMQ -> notification-service -> MongoDB
```

Consumer phải idempotent. Theo dõi queue depth/DLQ/consumer lag.

## 23. Storage

Secrets Cloudinary qua ExternalSecret. Metadata ở MongoDB.

## 24. AI service không dùng Argo Workflow/KServe

Runtime:

```text
FastAPI
  -> LangGraph
      -> LangChain structured output
      -> LLM provider
      -> read-only Booking tools
```

Directory:

```text
environments/production/ai-service/
├── kustomization.yaml
├── deployment.yaml
├── service.yaml
├── external-secret.yaml
├── hpa.yaml
├── pdb.yaml
├── network-policy.yaml
├── servicemonitor.yaml
└── prometheusrule.yaml
```

## 25. AI Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-service
  namespace: badminton
spec:
  replicas: 2
  selector:
    matchLabels:
      app: ai-service
  template:
    metadata:
      labels:
        app: ai-service
    spec:
      containers:
        - name: ai
          image: badminton-ai-service
          ports:
            - name: http
              containerPort: 8000

          envFrom:
            - configMapRef:
                name: ai-service-config
            - secretRef:
                name: ai-service-secrets

          startupProbe:
            httpGet:
              path: /health
              port: http
            periodSeconds: 5
            failureThreshold: 30

          readinessProbe:
            httpGet:
              path: /ready
              port: http
            periodSeconds: 10

          livenessProbe:
            httpGet:
              path: /health
              port: http
            periodSeconds: 10

          resources:
            requests:
              cpu: 250m
              memory: 512Mi
            limits:
              cpu: "1"
              memory: 1Gi
```

Hosted LLM thì không cần GPU.

## 26. AI ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ai-service-config
  namespace: badminton
data:
  BOOKING_CORE_BASE_URL: "http://booking-core:3000"
  MODEL_PROVIDER: "groq"
  MODEL_NAME: "<reviewed-model-name>"
  LANGGRAPH_CHECKPOINT_BACKEND: "redis"
  REDIS_HOST: "<rendered-platform-value>"
```

Không đặt LLM API key trong ConfigMap.

## 27. AI ExternalSecret

```yaml
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: ai-service
  namespace: badminton
spec:
  refreshInterval: 1h

  secretStoreRef:
    kind: ClusterSecretStore
    name: aws-secrets-manager

  target:
    name: ai-service-secrets

  data:
    - secretKey: LLM_API_KEY
      remoteRef:
        key: badminton/prod/llm
        property: api_key
```

## 28. AI security boundary

```text
ai-service
  -> LLM provider HTTPS
  -> booking-core read-only tool API
  -> Redis checkpoint backend

ai-service
  X Booking PostgreSQL
  X PayOS write credentials
```

NetworkPolicy chỉ bảo vệ network-level; API allow-list vẫn phải enforce ở code.

## 29. ServiceMonitor

Ví dụ AI:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: ai-service
  namespace: badminton
  labels:
    release: monitoring
spec:
  selector:
    matchLabels:
      app: ai-service
  endpoints:
    - port: http
      path: /metrics
      interval: 15s
```

## 30. PrometheusRule

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: ai-service
  namespace: badminton
  labels:
    release: monitoring
spec:
  groups:
    - name: ai-service
      rules:
        - alert: AIServiceUnavailable
          expr: up{job=~".*ai-service.*"} == 0
          for: 2m
          labels:
            severity: critical

        - alert: AIServiceHighErrorRate
          expr: |
            sum(rate(ai_http_requests_total{status=~"5.."}[5m]))
            /
            clamp_min(sum(rate(ai_http_requests_total[5m])), 0.001)
            > 0.05
          for: 5m
          labels:
            severity: warning

        - alert: AIServiceToolFailures
          expr: |
            sum(rate(ai_tool_calls_total{outcome!="success"}[5m])) > 0.1
          for: 5m
          labels:
            severity: warning
```

## 31. Booking monitoring

App code expose:

```text
booking_core_http_requests_total
booking_core_http_duration_seconds
booking_core_database_up
booking_conflict_total
payment_webhook_failure_total
pass_transfer_total
```

GitOps chứa:

```text
ServiceMonitor
PrometheusRule:
  BookingCoreUnavailable
  BookingCoreHighErrorRate
  BookingCoreHighLatency
```

## 32. Không dùng static Prometheus target production

Không dùng:

```yaml
scrape_configs:
  - job_name: booking-core
    static_configs:
      - targets: ["api:3000"]
```

Dùng:

```text
ServiceMonitor
  -> label selector
  -> Kubernetes Service
  -> Pods
```

PrometheusRule thay `rule_files`.

## 33. HPA

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: booking-core
  namespace: badminton
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: booking-core
  minReplicas: 2
  maxReplicas: 6
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

AI ban đầu có thể CPU HPA; custom request concurrency/queue metric thêm sau khi đo ổn định.

## 34. PDB

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: booking-core
  namespace: badminton
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: booking-core
```

Chỉ meaningful khi replicas >1.

## 35. NetworkPolicy map

Booking:

```text
IN:
api-gateway -> booking-core
ai-service -> Booking read API
social-service -> chat-context API

OUT:
booking-core -> Booking PostgreSQL
booking-core -> Redis
booking-core -> RabbitMQ
booking-core -> PayOS
```

Identity:

```text
api-gateway -> identity
identity -> Identity PostgreSQL
identity -> Redis
identity -> RabbitMQ
```

Commerce:

```text
api-gateway -> commerce
commerce -> Commerce PostgreSQL
commerce -> RabbitMQ
```

Nên bắt đầu `default deny`, rồi allow theo dataflow.

## 36. Secret per workload

Ví dụ Booking:

```text
booking-core-secrets
├── DATABASE_URL
├── PAYOS_CLIENT_ID
├── PAYOS_API_KEY
├── PAYOS_CHECKSUM_KEY
└── internal auth material
```

Không tạo một `badminton-all-secrets` cho mọi Pod.

## 37. Database migration bằng Argo CD hook

Không cần Argo Workflow.

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: booking-core-migrate
  namespace: badminton
  annotations:
    argocd.argoproj.io/hook: PreSync
    argocd.argoproj.io/hook-delete-policy: BeforeHookCreation,HookSucceeded
spec:
  backoffLimit: 2
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: migrate
          image: badminton-booking-core
          command: ["npm", "run", "prisma:migrate:deploy"]
          envFrom:
            - secretRef:
                name: booking-core-secrets
```

Flow:

```text
GitOps PR merged
  -> Argo CD sync
  -> PreSync migration
  -> fail => stop rollout
  -> pass => Deployment rollout
```

Migration phải backward-compatible với rolling update.

## 38. Workload release flow

Giữ tư tưởng của Iris nhưng đơn giản hơn:

```text
badminton_system
  -> CI green
  -> build/sign/push ECR
  -> immutable digest
  -> dispatch workload-release intent
  -> badminton-gitops receiver
  -> protected PR
  -> review
  -> merge
  -> Argo CD sync
```

Producer không có kubeconfig.

## 39. Workload release contract

```json
{
  "schema_version": "v1",
  "environment": "production",
  "component": "booking-core",
  "image": {
    "repository": "123.dkr.ecr.ap-southeast-1.amazonaws.com/badminton-prod/booking-core",
    "digest": "sha256:..."
  },
  "source": {
    "repository": "chiendz11/badminton_system",
    "commit": "..."
  }
}
```

Renderer chỉ sửa component đã allow-list. Producer không được truyền arbitrary manifest path/namespace/ECR repo.

## 40. Monorepo release

CI detect deployable thay đổi:

```text
booking_core/src/modules/pricing/*
  -> booking-core image

ai_service/*
  -> ai-service image

apps/web/*
  -> web image
```

Module `pricing` không có image riêng vì thuộc booking-core.

## 41. Image pinning và rollback

```yaml
images:
  - name: badminton-booking-core
    newName: 123.dkr.ecr.ap-southeast-1.amazonaws.com/badminton-prod/booking-core
    digest: sha256:abc...
```

Rollback image = Git revert/PR về digest cũ.

## 42. Config release

Không phải config change nào cũng rebuild image.

Có thể sửa GitOps ConfigMap cho:

```text
LOG_LEVEL
LLM_MODEL_NAME
BOOKING_TOOL_TIMEOUT_MS
feature flags
```

Secret value vẫn nằm Secrets Manager.

## 43. Platform reconcile

```text
badminton-infrastructure
  -> platform-contract-v1
  -> platform-reconcile.yml
  -> renderer
  -> GitOps PR
```

Renderer cập nhật:

```text
clusterName
VPC ID
IRSA ARN
ECR allow-list
RDS hosts
Redis endpoint
RabbitMQ endpoint
domain
certificate ARN
secret ARN references
```

Không cập nhật application image digest.

## 44. Stable platform state

`state/production-platform.json`:

```json
{
  "environment": "production",
  "aws_region": "ap-southeast-1",
  "cluster_name": "badminton-prod",
  "vpc_id": "vpc-...",
  "ecr": {
    "booking-core": "...",
    "ai-service": "..."
  },
  "domain": "badminton.example.com"
}
```

Không ghi password/API key/transient run ID.

## 45. GitOps CI

`validate.yml`:

```text
yamllint
kustomize build every root
kubeconform
policy tests
schema validation
renderer unit tests
forbid plaintext secrets
forbid :latest
forbid unpinned production images
validate namespace ownership
```

Required check ổn định: `validate`.

## 46. Policy checks nên có

Fail production manifest nếu:

```text
plaintext Secret value
image :latest
privileged: true
allowPrivilegeEscalation: true
hostNetwork: true
LoadBalancer Service cho internal backend
```

AI config cũng fail nếu vô tình nhận Booking DB URL hoặc PayOS write credential.

## 47. Recovery

`recovery.yml` nhận:

```text
component
historical digest/commit
reason
```

Nó chỉ mở recovery PR:

```text
verify target
  -> open PR
  -> review
  -> merge
  -> Argo CD
```

Không force-sync bằng CI.

## 48. Rollback theo loại lỗi

```text
Image regression -> revert digest
Config regression -> revert ConfigMap
Infrastructure -> fix/revert badminton-infrastructure
DB destructive migration -> run migration recovery plan, không chỉ đổi image
```

DB migration nên theo expand -> deploy -> contract.

## 49. Readiness semantics

`/health` = process alive.

`/ready` = service có thể nhận traffic.

Booking có thể check DB/config thiết yếu.

AI readiness:

```text
FastAPI started
LangGraph initialized
required model/provider config loaded
checkpoint backend ready nếu bắt buộc
```

Không nên làm AI permanently NotReady chỉ vì hosted LLM provider tạm timeout; có thể trả fallback có kiểm soát.

## 50. Monitoring ownership

```text
App code
  -> instrumentation

GitOps app directory
  -> ServiceMonitor
  -> PrometheusRule
  -> app dashboard

GitOps platform
  -> Prometheus
  -> Grafana
  -> Alertmanager
```

## 51. Alerts gợi ý

Booking:

```text
BookingCoreUnavailable
BookingCoreHighErrorRate
BookingCoreHighLatency
BookingConflictSpike
PaymentWebhookFailures
```

Social:

```text
SocialUnavailable
SocketConnectionSpike
UnauthorizedRoomAttempts
MessageLatencyHigh
```

AI:

```text
AIUnavailable
AIHighErrorRate
AIHighLatency
AIToolFailureRate
AIFallbackRateHigh
```

RabbitMQ:

```text
QueueDepthHigh
DLQNotEmpty
ConsumerLagHigh
```

## 52. Secrets lifecycle

```text
operator
  -> AWS Secrets Manager
  -> External Secrets
  -> Kubernetes Secret
  -> Pod
```

Rotate secret ở AWS. Restart workload nếu app không hot-reload.

Ví dụ:

```text
badminton/prod/llm
badminton/prod/payos
badminton/prod/cloudinary
```

Không mount PayOS secret vào AI Pod.

## 53. Redis/RabbitMQ/Mongo placement

Nếu managed:

```text
Terraform creates infrastructure
GitOps consumes endpoint + secret refs
```

Nếu demo in-cluster:

```text
GitOps platform/data owns StatefulSet/Helm/PVC
```

Không nhét Redis/Mongo/RabbitMQ sidecar vào từng app Pod.

## 54. Progressive delivery

MVP dùng RollingUpdate.

Booking:

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxUnavailable: 0
    maxSurge: 1
```

Chỉ thêm Argo Rollouts khi thật sự cần canary. Không copy KServe canary của Iris sang app thường.

## 55. AI rollout

AI tương đối stateless nếu checkpoint ở Redis.

Rolling update cần chú ý compatibility của:

```text
prompt version
structured-output schema
LangGraph state/checkpoint schema
tool schema
```

Nếu checkpoint schema breaking, phải version state/session.

## 56. Bootstrap order

1. Infrastructure bootstrap remote state + OIDC.
2. Apply domain.
3. Apply platform: VPC/EKS/data/ECR/IAM/Secrets/ArgoCD.
4. Root Application đọc `badminton-gitops/applications`.
5. GitOps tạo namespaces.
6. GitOps cài External Secrets.
7. GitOps cài monitoring/metrics/LB controller/ExternalDNS.
8. Platform reconcile cập nhật endpoint/ARN/ECR allow-list.
9. App CI publish first image digests.
10. Workload-release PR pin digests.
11. Argo CD deploy workloads.
12. Verify probes/metrics/alerts/ingress/E2E.

## 57. Deployment validation

```text
GET /
-> web

POST /api/auth/login
-> identity

GET /api/centers
-> booking-core

booking transaction
-> no double booking

PayOS webhook
-> idempotent

/socket.io
-> WebSocket upgrade

2 social replicas
-> Redis adapter

RabbitMQ event
-> notification

/api/ai/v1/chat
-> structured intent/constraints
-> read-only Booking tool
-> no direct Booking DB/write
```

## 58. Failure isolation

```text
AI down
-> booking/search/payment/social still work

Social down
-> booking still works

Notification slow
-> booking commits, RabbitMQ buffers event

Booking DB down
-> booking readiness fails
-> AI tool returns controlled fallback
-> AI must not hallucinate availability
```

## 59. Phase đầu nên tạo gì

Tạo trước:

```text
applications/
  project.yaml
  kustomization.yaml
  platform-namespaces.yaml
  platform-external-secrets.yaml
  platform-external-secrets-config.yaml
  platform-monitoring.yaml
  platform-metrics-server.yaml
  platform-aws-load-balancer-controller.yaml

platform/
  namespaces/
  external-secrets-config/

environments/production/
  api-gateway/
  identity-service/
  booking-core/
  social-service/
  ai-service/
```

Sau đó thêm commerce/content/notification/storage/web/admin/edge.

## 60. Migration không big-bang

Trong thời gian refactor có thể giữ:

```text
legacy service
new service
```

song song.

Gateway route/feature flag cutover:

```text
new writes
-> new service

shadow reads
-> compare

cutover reads
-> legacy read-only
-> decommission
```

## 61. Final flow

```text
badminton_system
  -> image digest
                                    v
        badminton-gitops
             ^
            /
           /
badminton-infrastructure
  -> platform contract

badminton-gitops
  -> protected PR
  -> Argo CD
  -> EKS
  -> web/admin/gateway/identity/booking/commerce/social/content/notification/storage/ai
```

Quy tắc cuối:

> **Application repo quyết định cách build phần mềm. Infrastructure repo quyết định cloud/platform nào tồn tại. GitOps repo quyết định Kubernetes đang chạy phiên bản và cấu hình nào.**
