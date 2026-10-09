# Bootstrap and ownership

Infrastructure prepares state/OIDC, domain, private cloud/data resources, EKS and Argo CD. Follow `badminton-infras/docs/AWS_DEPLOYMENT.md` before adopting this repository.

1. Merge the implementation into this repository's main branch after review and configure GitHub workflow credentials/protections.
2. Obtain a real, validated platform v1 contract from Terraform output. Populate runtime Secrets Manager values and app database users separately; none are passed through the contract.
3. Invoke `platform-reconcile.yml` with contract JSON or an authorized repository_dispatch event. Review/merge the generated PR. This configures IRSA, chart values, secret ARN references, ingress metadata and managed endpoint-specific policies. It leaves image selections unchanged.
4. Enable the Terraform root Application only after that platform PR is merged. The root reads `applications` on main.
5. Publish/sign initial application runtime and, where required, Prisma migration images. Submit one release contract per service. Review/merge each PR. The receiver enables automatic sync for that service only.
6. Migrations run after the service's PreSync ExternalSecret reports ready and before its Deployment update. Migration failure stops that Application's rollout.
7. Edge becomes automated once web, admin, gateway and social have approved image releases. Readiness and service health still determine whether ALB can route traffic; an image release alone does not assert application health.

| Wave | Resource group |
| --- | --- |
| -100 | AppProject |
| -90 | namespaces |
| -50 / -49 | External Secrets / store configuration |
| -45 / -44 | metrics-server / gp3 storage |
| -40 / -39 | monitoring / Argo metrics |
| -38 / -37 / -36 | AWS LB Controller / ExternalDNS / cert-manager |
| 0 | shared default-deny policy |
| 10 | backend Applications |
| 20 | gateway |
| 25 | web/admin |
| 30 | edge |

Within a database Application, hook waves are -20 for the ExternalSecret and -10 for migration. The Argo Helm values in infrastructure include the `ExternalSecret Ready=True` health check. The hooks assume the cluster-wide ESO platform already exists. Disable automatic sync until prerequisites are reviewed. Sync waves do not replace application retries/readiness.

Only `platform/namespaces` declares app/platform Namespace manifests; child roots do not duplicate them. `argocd` is initially created by the infrastructure Helm install and then retained under GitOps namespace desired state. The existing EKS `kube-system` namespace is not recreated by this repository.

Infrastructure owns EKS/EBS CSI/IAM/managed endpoints/ACM. GitOps owns StorageClass/PVC, chart add-ons, workload images/config, policies and alerts. Application code owns runtime correctness and build/publish logic.
