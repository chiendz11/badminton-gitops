# Production & Local Bootstrap

Infrastructure provisions AWS/EKS (`terraform/bootstrap`, `terraform/domain`, `terraform/platform`, `terraform/argocd`) or local `k3d` (`terraform/local`). Follow [badminton-infras/docs/BOOTSTRAP.md](../../badminton-infras/docs/BOOTSTRAP.md) first.

## Production Order

1. `terraform/platform` writes non-secret infrastructure metadata (EKS cluster, VPC, KMS, IRSA roles including `image-updater`, RDS/Valkey/RabbitMQ endpoints, ECR repository URIs, and Secrets Manager ARNs) to AWS SSM Parameter Store (`/badminton/prod/platform-metadata`).
2. Populate out-of-band AWS Secrets Manager runtime values and `argocd-image-updater-git-creds` (Fine-grained PAT for Image Updater PRs on `chiendz11/badminton-gitops`).
3. Update placeholder values (`UNCONFIGURED_ROLE_ARN`, `UNCONFIGURED_CLUSTER`, `UNCONFIGURED_VPC`, `UNCONFIGURED_ZONE`, ECR repository URIs, endpoints) in `applications/addons/*.yaml`, `applications/image-updater.yaml`, and `environments/production/*/kustomization.yaml` via reviewed PRs on `main`.
4. Enable `enable_gitops_root = true` in `terraform/argocd` so `badminton-root` reconciles [`applications/`](../applications/).

## Local (`k3d` + LocalStack + Image Updater)

1. Run `terraform -chdir=terraform/local apply` in `badminton-infras` (provisions `k3d-badminton-local`, LocalStack, ESO + `ClusterSecretStore/aws-secrets-manager`, `ingress-nginx`, Argo CD + Argo CD Image Updater v1.5.0, and applies `applications/local`).
2. Load the Image Updater PAT into the cluster (`GITHUB_PAT=ghp_xxx make local-image-updater-pat` in `badminton-infras`).
3. Run `make local-migrate` and `make local-status` in `badminton-infras`.
