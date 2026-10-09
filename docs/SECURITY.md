# Network and credential boundaries

`platform/policies` starts the badminton namespace with default-deny ingress and egress. Each component declares its permitted graph. EKS VPC CNI NetworkPolicy support is enabled by infrastructure.

| Component | Internal ingress | Egress |
| --- | --- | --- |
| booking-core | gateway, AI, social, monitoring | own RDS /32, cache /32, broker /32, PayOS/public HTTPS |
| identity-service | gateway, monitoring | own RDS /32, cache /32, broker /32, OAuth/public HTTPS |
| commerce-service | gateway, monitoring | own RDS /32, broker /32, public HTTPS |
| social-service | ALB/private VPC, gateway, monitoring | Mongo allow-list, Redis /32, Booking API, public HTTPS |
| notification-service | gateway, monitoring | Mongo allow-list, broker /32, delivery-provider HTTPS |
| storage/content | gateway, monitoring | Mongo allow-list, public provider HTTPS |
| ai-service | gateway, monitoring | **own AI RDS /32**, Booking API, Redis /32, hosted LLM HTTPS |
| api-gateway | ALB/private VPC, web/admin, monitoring | internal service HTTP origins |
| web/admin | ALB/private VPC, monitoring | gateway HTTP origin |

All Pods may query kube-dns on TCP/UDP 53. Public HTTPS egress excludes RFC1918 and link-local ranges; it is a network-port policy, not an LLM/provider domain allow-list. Provider-specific domain restrictions require an additional FQDN-aware egress solution. Mongo destination ranges are operator metadata and never a broad `0.0.0.0/0:27017` rule.

Public-backend ingress permits the platform VPC CIDR for ALB target traffic. This is not an ALB identity proof; AWS security groups and API auth remain relevant. Standard NetworkPolicy cannot express read-only HTTP methods/tools, separate Mongo DB authorization or payment permissions. AI's network rule reaches Booking HTTP but its code must enforce read-only tool access. Its own database egress is not permission to use Booking RDS, and no Booking DB or PayOS secret is mounted into it.

Runtime Deployments use non-root UIDs, RuntimeDefault seccomp, no privilege escalation, dropped capabilities, read-only roots, writable tmp volumes, CPU/memory requests/limits, readiness/startup/liveness probes and rolling updates. Frontend nginx uses UID 101, port 8080, writable cache/pid mounts and an explicit config, bypassing the image's Docker-only nginx template.

Migration Jobs use the component's network identity but have a writable root for Prisma/Alembic tooling. Services, Deployment selectors and PDBs select the `runtime` component label, so migration Job Pods cannot become HTTP backends or inflate the disruption budget.

Each backend gets a separate ExternalSecret and metrics bearer token. RDS master credentials are not read by ESO or mounted into app Pods. Service accounts do not automount API tokens; ordinary workloads receive no IRSA role. Secret values are operator-owned in AWS and refresh through ESO. Refer to the infrastructure secret table for exact property names.

The structural policy program rejects authored plaintext Kubernetes Secrets, latest/unpinned active images, privilege escalation/host namespace settings, public LoadBalancer app Services and AI Booking/PayOS credentials. It permits initial image markers only for disabled Applications. Its checks supplement review and do not replace a live security assessment.
