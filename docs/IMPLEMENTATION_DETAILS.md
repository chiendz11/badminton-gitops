# Detailed implementation report

## Platform

The AppProject allow-lists only GitOps and the selected Helm repositories, with explicit known destination namespaces. App-of-Apps includes all add-ons, shared policy/storage/monitoring roots, 11 workload Applications and edge. Namespaces are centrally retained with `Prune=false`.

ESO uses AWS IRSA and a ClusterSecretStore scoped to badminton. Monitoring includes kube-prometheus-stack, Grafana dashboard discovery, ServiceMonitor/PodMonitor/rule discovery and a retained gp3 Prometheus volume. Metrics-server supports HPA. LB Controller consumes reconciled cluster/region/VPC/IRSA; ExternalDNS reads Ingress sources, uses a TXT owner and hosted-zone filter, and defaults to upsert-only. Cert-manager is installed as an optional general certificate facility; the ALB certificate is ACM-owned, so no fabricated cert-manager Issuer is introduced.

## Workloads

| Workload | Port | Secrets/data | Migration |
| --- | --- | --- | --- |
| web | 8080 | non-secret SPA config | no |
| admin | 8080 | non-secret SPA config, separate hostname | no |
| api-gateway | 8081 | JWT, metrics, internal auth; service origins | no |
| identity-service | 3000 | own PostgreSQL, Redis, RabbitMQ, OAuth | signed Prisma migration image |
| booking-core | 3000 | own PostgreSQL, Redis, RabbitMQ, PayOS | signed Prisma migration image |
| commerce-service | 3000 | own PostgreSQL, RabbitMQ | signed Prisma migration image |
| social-service | 3000 | own MongoDB, Redis adapter config, Booking context origin | no |
| content-service | 3000 | own MongoDB | no |
| notification-service | 3000 | own MongoDB, RabbitMQ | no |
| storage-service | 3000 | own MongoDB metadata, Cloudinary | no |
| ai-service | 8000 | own PostgreSQL, Redis metadata, hosted LLM, Booking read origin | Alembic/app migration in runtime image |

Every workload has a ServiceAccount, Deployment, ClusterIP Service, CPU HPA, PDB and NetworkPolicy. All backends add a separate ExternalSecret, authenticated ServiceMonitor and PrometheusRule. ConfigMaps use Kustomize's generated hash so config adoption triggers a rollout. HPA defaults to 2–6 replicas at 70% CPU; requests/limits are provisional values, not benchmark results. Argo ignores HPA-owned replica fields with `RespectIgnoreDifferences=true`.

Migration images are independently pinned for Node DB services. PreSync hooks require ready secret material, stop rollout on failure, delete successful Jobs and retain runtime secrets during hook recreation. HTTP Services select runtime Pods only. Startup probes provide an initial initialization window; readiness and liveness match current Booking/Gateway/AI paths.

One ALB Ingress routes `/api`, `/graphql`, `/socket.io` and the public SPA. `/admin` redirects to the separate root-path admin host. It uses HTTPS/ACM, redirect from HTTP, IP targets, per-backend health overrides, ExternalDNS annotations and a 120-second idle timeout for websocket requests. Kubernetes ingress alone does not implement a Socket.IO Redis adapter or authentication routes.

## Monitoring

Booking/Gateway/AI use the metric prefixes in current app code. Booking alerts include availability, errors, latency, database connectivity and conflicts. AI includes errors, latency and tool failures. Social authorization and notification queue/DLQ/lag alerts are included as future instrumentation contracts. There is no static production scrape target. Some guide-specific payment/fallback/queue series require future app/exporter work, documented in release integration; their presence as alert rules does not imply those series currently exist.

## Delivery automation

The strict platform schema is shared with infrastructure; the workload schema fixes environment/source and allowed components, immutable digests and optional migration digest metadata. Schema extensions reject arbitrary extra properties.

Platform reconcile renders deterministic reviewed cloud metadata, secret references and endpoint-specific policies without changing workload digests. Release verifies registered ECR URL, source main ancestry, successful CI and keyless Cosign identity plus commit annotation, then changes only the approved component and its release history. Recovery selects a known historical GitOps release and reuses the verifier. All changes go through proposal PRs, main protections and Argo reconciliation.

The structural policy program checks secrets/images/namespace ownership and common Pod/Service risks. The stable `validate` workflow builds every root and checks standard resources with kubeconform; chart CRD schemas are not vendored. No renderer test suite or test execution was added because the user requested code first without tests.

## Limits of this delivery

No real AWS account/domain values or secrets were fabricated. No cloud resources, cluster deployments, automated main merges, branch protection rules or GitHub environments were created. Code is delivered on a new feature branch. Main bootstrap contains only repository scaffolding until the implementation branch is reviewed/merged.

Actual deployability requires the configuration/secrets/producer steps in these docs, app implementations for the six future services, reviewed sizing/HA/plans, and later validation. Managed endpoint /32 rules need reviewed DNS-refresh adoption on failover. The current AI requires its own PostgreSQL and the frontend uses a separate admin host, both explicitly adapted from actual app code instead of copying mismatching example snippets.
