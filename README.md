# badminton-gitops

Kubernetes desired state for Badminton Manager V2. Argo CD reconciles reviewed `main`; app CI publishes images and infrastructure supplies non-secret platform metadata. Neither producer deploys production using kubectl.

## Delivered

- AppProject and App-of-Apps with ordered platform/workload sync waves.
- Namespace ownership, External Secrets/ClusterSecretStore, monitoring, metrics-server, AWS LB Controller, ExternalDNS, cert-manager, gp3 StorageClass, default-deny policies and Argo monitoring.
- Production manifests for web, admin, API gateway, identity, booking, commerce, social, content, notification, storage and AI, plus one public ALB Ingress.
- Per-workload Deployment, ServiceAccount, internal Service, generated ConfigMap, HPA/PDB and NetworkPolicy. Backends have their own ExternalSecret, ServiceMonitor and alert rules; database services have ordered PreSync migration Jobs.
- Strict platform and release contracts; deterministic metadata/image renderers; CI/signature provenance verification; release/reconcile/recovery PR workflows; structural CI policies.

## Initial state

`state/production-platform.json` starts with `configured: false`. Add-ons requiring real AWS metadata and all workload Applications start without automated sync. Initial `unreleased` image markers are allowed only while their Application is disabled; they are not fabricated production digests.

First merge a real platform reconcile PR, which enables the platform Applications. Then merge signed image-release PRs per service, which pin immutable digests and enable that service. Edge is automatically enabled when web/admin/gateway/social all have reviewed image releases. Disabled child Applications are deliberately treated as healthy by the Terraform-installed Argo health customization so they do not block unrelated platform phases.

Do not manually sync an unconfigured/unreleased Application. No tests, Kustomize build, kubeconform, cluster deployment or workflow runs were executed during implementation, per the user's request. CI definitions are available for later PRs; they are not execution evidence.

## Documentation

- [Bootstrap and ownership](docs/BOOTSTRAP.md)
- [Platform and release contracts](docs/CONTRACTS.md)
- [Release producer integration](docs/RELEASE_INTEGRATION.md)
- [GitHub workflow configuration](docs/GITHUB_ACTIONS.md)
- [Network and secret boundaries](docs/SECURITY.md)
- [Recovery](docs/RECOVERY.md)
- [Detailed implementation report](docs/IMPLEMENTATION_DETAILS.md)
- [Original GitOps guide](BADMINTON_GITOPS_IMPLEMENTATION.md)

The existing app implements web/admin/gateway/booking/AI. The other six Applications are deployment contracts for future app services and remain disabled until they have real images. App-level idempotency, Redis adapters, route handlers, read-only Booking tools and metrics instrumentation belong to the app repository.
