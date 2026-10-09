# GitHub workflow configuration

Configure required reviews and the stable `validate` check on main after the first actual CI run. Create `production-automation`, restrict it to main and configure the protections appropriate for PR automation. Workflows require trusted main code; manual executions from feature branches fail the main-reference condition.

## Variables and secret

| Variable | Purpose |
| --- | --- |
| AUTOMATION_APP_ID | Installed GitHub App used for scoped PR and source-read tokens |
| DISPATCH_SENDER | Exact authorized repository_dispatch sender login, usually the App's `[bot]` login |
| AWS_REGION | ECR region, matching the platform |
| RELEASE_VERIFIER_ROLE_ARN | Infrastructure output `gitops_release_verifier_role_arn` |
| APP_CI_WORKFLOW | App workflow file, default ci.yml |
| IMAGE_SIGNER_IDENTITY | Exact keyless signing certificate identity, e.g. `https://github.com/chiendz11/badminton_system/.github/workflows/image-publish.yml@refs/heads/main` once that publisher exists |

Store `AUTOMATION_APP_PRIVATE_KEY` as an environment secret. Install the App on GitOps with Contents write and Pull requests write to create review PRs; install it on the app repository with Actions read/Contents read capability for provenance queries. Workflow tokens request only their needed repository/permissions. PR writes use an App token so the resulting PR can trigger CI rather than GitHub's recursively suppressed GITHUB_TOKEN.

The AWS verifier role trusts `repo:chiendz11/badminton-gitops:environment:production-automation`; it can inspect/download only the project ECR images, with no ECR push, EKS or Secrets Manager access. Platform reconciliation itself needs no AWS credential and does not read secret values. Its endpoint DNS resolution must work from the selected runner; use a VPC runner if your managed endpoint DNS is private-only.

## Workflows

- `validate.yml`: authored YAML lint; every Kustomize root build; kubeconform strict validation for standard Kubernetes resources; repository/schema/image/namespace/credential policies. Unknown CRD kinds are skipped by kubeconform because their cluster-installed chart schemas are not vendored; contract/policy checks do not prove full CRD API compatibility.
- `platform-reconcile.yml`: authorized contract dispatch/manual input or scheduled current-contract DNS refresh; updates platform metadata and opens/updates `platform/reconcile` PR. The scheduled path is dormant while state is unconfigured.
- `workload-release.yml`: validates source CI and signed images; updates only approved component state; opens/updates `release/<component>` PR.
- `recovery.yml`: takes component, a full historical **GitOps** commit and reason; verifies a known historical source/image release and opens a recovery PR.

All writers share `production-gitops-writer` concurrency without cancellation. Workflows do not merge PRs, execute production kubectl, force-sync Argo CD or apply Terraform. Existing automation branches are updated by the PR action; branch protection/reviews still control main adoption. Required-check rules and environments are operational prerequisites, not created by this coding task.

No unit/integration/E2E tests or validation workflows were run during implementation. There is intentionally no test suite in these new repositories. Structural policy/contract programs are production workflow code and can be exercised later during deployment preparation.
