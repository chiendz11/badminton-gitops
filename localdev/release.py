"""Prepare local GitOps desired state from receipts."""

import argparse
import json
from pathlib import Path

import yaml

from .common import ROOT


def update_apps(receipts_file):
    receipts = json.loads(Path(receipts_file).read_text())
    apps_dir = ROOT / "environments/local/apps"
    
    image_overrides = []
    for component, receipt in receipts.items():
        if "image" not in receipt:
            continue
        repo, tag = receipt["image"].rsplit(":", 1)
        image_overrides.append({
            "name": f"registry.invalid/badminton-local/{component}",
            "newName": repo,
            "newTag": tag
        })
    
    kustomize = {
        "apiVersion": "kustomize.config.k8s.io/v1beta1",
        "kind": "Kustomization",
        "namespace": "badminton",
        "resources": [
            "../../../local/workloads/booking-core",
            "../../../local/workloads/ai-service",
            "../../../local/workloads/api-gateway",
            "../../../local/workloads/web",
            "../../../local/workloads/admin"
        ],
        "images": image_overrides
    }
    
    (apps_dir / "kustomization.yaml").write_text(yaml.safe_dump(kustomize, sort_keys=False))
    print(f"Updated {apps_dir / 'kustomization.yaml'} with {len(image_overrides)} image overrides.")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Update local GitOps desired state")
    parser.add_argument("--receipts", required=True, help="Path to receipts JSON")
    args = parser.parse_args(argv)
    update_apps(args.receipts)


if __name__ == "__main__":
    main()

