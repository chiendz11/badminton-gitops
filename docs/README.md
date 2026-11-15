# badminton-gitops Documentation Index

Pure Declarative Kubernetes Desired State for **Badminton Manager V2** (`local` `k3d` + `production` EKS).

## Documents

- [BOOTSTRAP.md](BOOTSTRAP.md) — Production & local bootstrap flow from `badminton-infras` to Argo CD root adoption.
- [LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md) — Pure Declarative local `k3d` overlays, ExternalSecrets, CoreDNS service discovery, and Image Updater `sha-<40>` PR loop.
- [GITHUB_ACTIONS.md](GITHUB_ACTIONS.md) — Offline CI (`kubectl kustomize`, `kubeconform`, secret/namespace/`:latest`/link guards) and PR-based rollout governance.
- [RECOVERY.md](RECOVERY.md) — GitOps commit rollback and Argo CD image recovery procedures.
- [RELEASE_INTEGRATION.md](RELEASE_INTEGRATION.md) — Image build -> GHCR/ECR -> Argo CD Image Updater PR -> Argo CD sync integration flow.
- [SECURITY.md](SECURITY.md) — NetworkPolicies, ExternalSecrets, non-root Pod security context, and PAT isolation.
- [APPLICATION_MONITORING.md](APPLICATION_MONITORING.md) — Prometheus ServiceMonitor / PrometheusRule layout across production services.
- [IMPLEMENTATION_DETAILS.md](IMPLEMENTATION_DETAILS.md) — Notes on Kustomize layout and Pure GitOps transition.

Related repositories:
- [README.md](../README.md) & [AGENTS.md](../AGENTS.md)
- Infrastructure repo: `../badminton-infras`
- Application repo: `../badminton-system`
