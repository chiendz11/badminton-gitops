# GitOps Recovery & Rollback

Because all cluster state is Pure Declarative Kustomize under `main`, recovery uses standard Git revert/PR workflows rather than custom state compilers:

1. Identify the last known-good commit SHA in `git log main` affecting [`environments/local/apps/kustomization.yaml`](../environments/local/apps/kustomization.yaml) or [`environments/production/`](../environments/production/).
2. Open a revert Pull Request reverting the problematic `newTag` / digest / manifest commit back to the known-good immutable tag or digest (`git revert <bad-sha>`).
3. Wait for `CI / required` ([`.github/workflows/ci.yml`](../.github/workflows/ci.yml)) to validate `kubectl kustomize` and `kubeconform`.
4. Review and merge into `main`; Argo CD reconciles the previous desired state cleanly (`selfHeal: true`).
5. Never force-apply unreviewed local patches or `:latest` tags in `main`.
