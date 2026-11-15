# Local Development — Pure Declarative GitOps (`k3d` + Argo CD)

Tài liệu này mô tả cấu trúc desired state local trong `badminton-gitops` theo kiến trúc Pure Declarative Kustomize + Argo CD Image Updater v1.5.0.

## 1. Cấu trúc Thư mục Local

| Đường dẫn trong `badminton-gitops` | Trách nhiệm |
|---|---|
| [`bootstrap/local/`](../bootstrap/local/) | Local root `Application` (`badminton-local-root`) trỏ tới `applications/local`. |
| [`applications/local/`](../applications/local/) | `AppProject` (`badminton-local`), 2 child Argo Applications (`badminton-local-platform`, `badminton-local-apps`), và `ImageUpdater` CR (`badminton-local-image-updater`). |
| [`local/platform/`](../local/platform/) & [`environments/local/platform/`](../environments/local/platform/) | PostgreSQL (databases `booking`, `ai`, `identity`), MongoDB, Redis, RabbitMQ, Ingress (`web.badminton.local`, `admin.badminton.local`, `api.badminton.local`), NetworkPolicies. *(Lưu ý: `ClusterSecretStore/aws-secrets-manager` do `badminton-infras` sở hữu.)* |
| [`local/workloads/`](../local/workloads/) & [`environments/local/apps/`](../environments/local/apps/) | 7 microservices hoạt động ở local (`api-gateway`, `identity-service`, `booking-core`, `content-service`, `ai-service`, `web`, `admin`), ExternalSecrets (`LocalStack`), HPA, PDB, và pin tag `sha-<40>` trong [`environments/local/apps/kustomization.yaml`](../environments/local/apps/kustomization.yaml). |

## 2. Quy trình CI & Image Updater Pull Request

1. Khi code trên `badminton_system` (`chiendz11/badminton_system`) merge vào `main`, workflow build đẩy image mới với tag `sha-<40-hex-sha>` lên GHCR (`ghcr.io/chiendz11/badminton-*`).
2. **Argo CD Image Updater** chạy trong namespace `argocd` polling GHCR theo cấu hình [`applications/local/image-updater.yaml`](../applications/local/image-updater.yaml) (`allowTags: regexp:^sha-[0-9a-f]{40}$`, `forceUpdate: true`, `pullRequest.github: {}`).
3. Khi phát hiện tag `sha-*` mới hơn, controller tự động mở **Pull Request** cập nhật `environments/local/apps/kustomization.yaml` vào nhánh `main`.
4. CI [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) chạy `kubectl kustomize` + `kubeconform` + guardrails (zero `Secret`, zero `:latest`).
5. Sau khi PR được merge vào `main`, Argo CD tự sync cụm `k3d-badminton-local`.

## 3. Bảo mật Secrets Local

- Zero plaintext secrets trong ConfigMaps hoặc Git: mọi service (`booking-core`, `ai-service`, `api-gateway`, `identity-service`, `content-service`) đọc secrets từ Kubernetes Secrets được ESO sync từ LocalStack (`ClusterSecretStore/aws-secrets-manager`).
- `argocd-image-updater-git-creds` được nạp vào LocalStack Secrets Manager (`badminton/prod/argocd-image-updater-git-creds`) qua CLI `make local-image-updater-pat` (hoặc tự đọc từ `../PAT.txt` `0600`) trong `badminton-infras`, rồi ESO `ExternalSecret` ([`applications/local/image-updater-git-creds.yaml`](../applications/local/image-updater-git-creds.yaml)) đồng bộ vào Secret `argocd/argocd-image-updater-git-creds` giống hệt Production.
