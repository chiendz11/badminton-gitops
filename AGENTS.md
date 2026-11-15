# badminton-gitops — Repository Rules & Boundaries

Read [README.md](README.md), [docs/README.md](docs/README.md), and [docs/BOOTSTRAP.md](docs/BOOTSTRAP.md) before modifying manifests.

## Core Principles

1. **Pure Declarative Kustomize Only**: This repository holds only Kubernetes/Kustomize YAML, Argo CD `Application` / `AppProject` / `ImageUpdater` manifests, and documentation. Do not reintroduce Python compilers, JSON release-state generators, or shell deployment scripts.
2. **Never Commit Sensitive Material**: Never commit `kind: Secret` YAML manifests, passwords, PATs, TLS keys, or API keys.
   - `argocd-image-updater-git-creds` (Fine-grained PAT for Image Updater PR creation) is synced into the `argocd` namespace via External Secrets Operator (`ExternalSecret` reading `badminton/prod/argocd-image-updater-git-creds` via `ClusterSecretStore/aws-secrets-manager-argocd` from LocalStack in local dev or AWS Secrets Manager in production; seeded out-of-band via `badminton-infras` CLI `python3 -m localdev image-updater-pat`).
   - All runtime credentials flow through External Secrets Operator (`ExternalSecret` -> `ClusterSecretStore/aws-secrets-manager`).
3. **Pull Request Discipline for Image Updates**:
   - Application CI pushes immutable images (`sha-<40>` / semver tags) to GHCR / ECR and does not commit directly to `badminton-gitops`.
   - Argo CD Image Updater (`ImageUpdater` CRs under `applications/image-updater.yaml` and `applications/local/image-updater.yaml`) proposes image updates as GitHub Pull Requests against `main` (`writeBackTarget: kustomization`).
4. **No Mutable `:latest` Tags or Duplicate Namespace/SecretStore Ownership**:
   - Local manifests (`local/`, `environments/local/`) must never reference `:latest` tags on application images.
   - `kind: Namespace` belongs only in `platform/namespaces/`.
   - Local `ClusterSecretStore/aws-secrets-manager` is owned by `badminton-infras/local/manifests/cluster-secret-store.yaml`; do not duplicate it here.

## Verification Scope

Running [`.github/workflows/ci.yml`](.github/workflows/ci.yml) (`kubectl kustomize` + `kubeconform` + YAML safety checks) validates manifest syntax and policy offline. Live Argo CD reconciliation requires a cluster provisioned via `badminton-infras`.
