# Badminton GitOps Local Development

Tài liệu này mô tả cấu trúc và cách quản lý Desired State cho môi trường **k3d Local Demo** (`badminton-local`) theo mô hình MaintAI.

---

## 1. Cấu trúc thư mục Local Desired State

```text
badminton-gitops/
├── environments/
│   ├── production/               # AWS EKS Production (không sửa đổi khi chạy local)
│   └── local/                    # Khai báo Argo CD Applications local
│       ├── platform/             # Kustomization cho CSDL PostgreSQL local
│       └── apps/                 # Kustomization cho các ứng dụng (Booking, AI, Gateway, Web, Admin)
├── local/
│   ├── platform/                 # Manifests PostgreSQL (StatefulSet, Service, PVC, script init)
│   └── workloads/                # Manifests cho từng microservice / frontend
│       ├── booking-core/
│       ├── ai-service/
│       ├── api-gateway/
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

Hoặc render chi tiết:
```bash
make render-platform
make render-apps
```

