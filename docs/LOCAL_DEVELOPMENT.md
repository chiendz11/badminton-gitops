# Badminton GitOps Local Development

Tài liệu này mô tả cấu trúc và cách quản lý Desired State cho môi trường **k3d Local Demo** (`badminton-local`) theo chuẩn GitOps tự động kéo image từ GitHub Container Registry (`ghcr.io/chiendz11`).

---

## 1. Cấu trúc thư mục Local Desired State

```text
badminton-gitops/
├── environments/
│   ├── production/               # AWS EKS Production (không sửa đổi khi chạy local)
│   └── local/                    # Khai báo Argo CD Applications local
│       ├── platform/             # Kustomization cho CSDL PostgreSQL local
│       └── apps/                 # Kustomization ánh xạ images sang ghcr.io/chiendz11/...:latest
├── local/
│   ├── platform/                 # Manifests PostgreSQL (StatefulSet, Service, PVC, script init)
│   └── workloads/                # Manifests cho từng microservice / frontend
│       ├── booking-core/
│       ├── ai-service/
│       ├── api-gateway/
│       ├── content-service/
│       ├── web/
│       └── admin/
├── contracts/
│   └── local-platform-contract-v1.json  # Platform contract khớp với badminton-infras
└── config/local/
    └── runtime-catalog.json             # Danh mục runtime của các components
```

---

## 2. Kiểm tra tính hợp lệ của Manifests (Dry-run Render)

Bạn có thể render và kiểm tra cú pháp toàn bộ manifests local bằng lệnh:

```bash
cd /home/chienqt/Dev/newBTL/badminton-gitops
make validate-local
```

Hoặc render chi tiết các workloads để kiểm tra image tags GHCR:
```bash
make render-apps
```

Toàn bộ các workloads (`booking-core`, `ai-service`, `api-gateway`, `content-service`, `web`, `admin`) được Kustomize tự động ánh xạ từ `registry.invalid/badminton-local/<component>` sang image phát hành chính thức `ghcr.io/chiendz11/badminton-<component>:latest` để cụm k3d tự động kéo về chạy.
