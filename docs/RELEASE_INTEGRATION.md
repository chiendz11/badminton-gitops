# Application CI -> GitOps Release Integration

Badminton Manager V2 decouples container publishing from Kubernetes reconciliation:

1. **Application CI (`badminton_system`)**:
   - Builds service container images and pushes immutable tags (`sha-<40>` on `main` to GHCR for local staging; release tags/digests to ECR for production).
   - Never pushes commits directly into `badminton-gitops` or runs `kubectl` / `helm` against clusters.
2. **Argo CD Image Updater (`badminton-gitops`)**:
   - Helm addon [`applications/addons/argocd-image-updater.yaml`](../applications/addons/argocd-image-updater.yaml) (`v1.5.0`) + controller installed in local `badminton-infras`.
   - [`applications/local/image-updater.yaml`](../applications/local/image-updater.yaml) watches GHCR tags matching `^sha-[0-9a-f]{40}$` and opens GitHub Pull Requests updating `environments/local/apps/kustomization.yaml`.
   - [`applications/image-updater.yaml`](../applications/image-updater.yaml) watches ECR repositories and opens GitHub Pull Requests updating `environments/production/workloads/kustomization.yaml` (by digest).
3. **Human Review & Argo CD Sync**:
   - `.github/workflows/ci.yml` validates every PR offline; after review & merge to `main`, Argo CD reconciles the updated Kustomization.
