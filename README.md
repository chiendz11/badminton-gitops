# badminton-gitops

Pure Declarative Kubernetes desired state for **Badminton Manager V2**, refactored along the `MaintAI-gitops` Kustomize + Argo CD Image Updater v1.5.0 PR-based deployment pattern.

Application code and builds: [`chiendz11/badminton_system`](https://github.com/chiendz11/badminton_system).
Infrastructure and Argo CD bootstrap: [`chiendz11/badminton-infras`](https://github.com/chiendz11/badminton-infras).

```text
bootstrap/
├── local/               # Local Root Application -> applications/local
└── production/          # Production Root Application -> applications
applications/
├── addons/              # Production Helm add-ons (ESO, Image Updater v1.5.0, LBC, ExternalDNS, Cert-Manager, Metrics Server, Monitoring)
├── local/               # Local AppProject, platform & apps Applications, ImageUpdater CR (GHCR sha-* -> GitHub PR)
├── project.yaml         # Production AppProject
├── image-updater.yaml   # Production ImageUpdater CR (ECR digest -> GitHub PR)
└── *.yaml               # Production child Argo CD Applications (namespaces, storage, network, secret-store, observability, workloads, edge)
environments/
├── local/               # Local k3d overlays (platform, apps, applications)
└── production/          # AWS EKS workloads (11 services + edge Ingress; default unreleased until ECR & secrets are configured)
local/
├── platform/            # Local PostgreSQL (booking/ai/identity), MongoDB, Redis, RabbitMQ, Ingress, NetworkPolicies
└── workloads/           # Local manifests for active services (api-gateway, identity-service, booking-core, content-service, ai-service, web, admin)
platform/                # Shared prod cluster resources (namespaces, gp3 StorageClass, default-deny NetworkPolicies, ClusterSecretStore, ServiceMonitor)
docs/                    # Architecture, Bootstrap, Local Development, GitHub Actions, Recovery, Security
```

## Ownership Boundary

- **`badminton_system`**: Application source code, Dockerfiles, migrations, and image builds pushed to GHCR / ECR with immutable `sha-<40>` / release tags. Never commits directly into `badminton-gitops`.
- **`badminton-gitops` (this repo)**: Pure Declarative Kubernetes YAML only (zero Python compilers, JSON release state generators, or committed `kind: Secret` objects). Image tag updates are proposed via **Argo CD Image Updater Pull Requests** against `main`.
- **`badminton-infras`**: Terraform 4-root AWS infrastructure (`bootstrap`, `domain`, `platform`, `argocd`), SSM metadata handoff (`/badminton/prod/platform-metadata`), Local `k3d` + LocalStack + `ClusterSecretStore`, and `argocd-image-updater-git-creds` PAT provisioning.

## Quick Links

- Docs Index: [docs/README.md](docs/README.md)
- Repo Boundaries: [AGENTS.md](AGENTS.md)
- Local Development: [docs/LOCAL_DEVELOPMENT.md](docs/LOCAL_DEVELOPMENT.md)
- Production Bootstrap: [docs/BOOTSTRAP.md](docs/BOOTSTRAP.md)
- CI & Validations: [docs/GITHUB_ACTIONS.md](docs/GITHUB_ACTIONS.md)
- Recovery: [docs/RECOVERY.md](docs/RECOVERY.md)
- Security: [docs/SECURITY.md](docs/SECURITY.md)
