# GitHub Actions & PR Governance

`badminton-gitops` uses Pure Declarative CI without custom release compilers or repository dispatch writers.

## CI Workflow (`.github/workflows/ci.yml`)

Triggered on `pull_request` and pushes to `main`:

1. **Pinned tools**: downloads checksum-verified `kubectl` `v1.35.5` and `kubeconform` `v0.8.0`.
2. **Kustomize render & schema validation**: renders all 14 Kustomize roots (`bootstrap/*`, `applications`, `applications/local`, `environments/local/*`, `environments/production/*`, `platform/*`) and validates every output + standalone `applications/addons/*.yaml` with `kubeconform -strict -ignore-missing-schemas -kubernetes-version 1.35.0`.
3. **Static safety guards**:
   - Rejects any committed `kind: Secret` YAML manifest.
   - Rejects duplicate `kind: Namespace` manifests outside `platform/namespaces/`.
   - Rejects mutable `:latest` tags across `local/` and `environments/local/`.
   - Validates all relative markdown links across `README.md`, `AGENTS.md`, and `docs/*.md`.

## Automated Image Updates

- Image updates arrive as automated GitHub Pull Requests opened by **Argo CD Image Updater** (`applications/local/image-updater.yaml` for local GHCR `sha-<40>`, `applications/image-updater.yaml` for production ECR digests).
- Configure branch protection on `main` requiring `CI / required` and manual review approval before merging image or platform PRs.
