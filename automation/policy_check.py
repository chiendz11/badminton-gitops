"""Static policy enforcement for authored and Kustomize-rendered manifests."""
import json
import re
import sys
from pathlib import Path

import yaml

from automation.common import ROOT, SERVICES, read_yaml, validate


def check_documents(documents):
    for document in documents:
        if not isinstance(document, dict):
            continue
        kind = document.get("kind")
        metadata = document.get("metadata", {})
        if kind == "Secret" and (document.get("data") or document.get("stringData")):
            raise ValueError("Plaintext/base64 Kubernetes Secret values are forbidden")
        if kind == "Service" and document.get("spec", {}).get("type") == "LoadBalancer":
            raise ValueError("Application Services must be internal ClusterIP")
        def walk(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key in {"privileged", "allowPrivilegeEscalation", "hostNetwork", "hostPID", "hostIPC"} and item is True:
                        raise ValueError(f"Unsafe setting: {key}")
                    if key == "image":
                        if str(item).endswith(":latest"):
                            raise ValueError("Mutable latest image is forbidden")
                        if str(item).startswith("UNCONFIGURED_IMAGE_REPOSITORY:"):
                            component = metadata.get("labels", {}).get("app") or document["spec"]["template"]["metadata"]["labels"]["app"]
                            app = read_yaml(f"applications/workload-{component}.yaml")
                            if "automated" in app["spec"]["syncPolicy"]:
                                raise ValueError("Unreleased app cannot sync automatically")
                        elif not re.fullmatch(r".+@sha256:[a-f0-9]{64}", str(item)):
                            raise ValueError(f"Workload image is not digest-pinned: {item}")
                    walk(item)
            elif isinstance(value, list):
                for item in value:
                    walk(item)
        walk(document)
        if kind == "Namespace" and metadata["name"] not in {"badminton", "monitoring", "external-secrets", "cert-manager", "external-dns", "argocd"}:
            raise ValueError("Unexpected namespace owner")
        if metadata.get("name") == "ai-service" and kind == "ExternalSecret":
            for item in document["spec"]["data"]:
                if item["secretKey"].startswith("PAYOS_") or item["secretKey"] == "DATABASE_URL":
                    raise ValueError("AI cannot receive Booking DB/PayOS credentials")


def check_repository():
    for path in ROOT.glob("contracts/*.schema.json"):
        from jsonschema import Draft202012Validator
        Draft202012Validator.check_schema(json.loads(path.read_text()))
    platform = json.loads((ROOT / "state/production-platform.json").read_text())
    if platform.get("configured") is not False:
        validate(platform, "platform-contract-v1.schema.json")
    for component in SERVICES:
        kustomization = read_yaml(f"environments/production/{component}/kustomization.yaml")
        application = read_yaml(f"applications/workload-{component}.yaml")
        if "automated" in application["spec"]["syncPolicy"]:
            for image in kustomization["images"]:
                if not re.fullmatch(r"sha256:[a-f0-9]{64}", image.get("digest", "")):
                    raise ValueError("Enabled production workload must have an immutable digest")
                if platform.get("configured") is False or image["newName"] != platform["ecr"][component]:
                    raise ValueError("Enabled workload must use the current approved ECR")
        directory = ROOT / "environments/production" / component
        for path in directory.glob("*.yaml"):
            doc = yaml.safe_load(path.read_text())
            if doc.get("kind") == "Namespace":
                raise ValueError("Namespace must be owned by platform/namespaces")
        if component == "ai-service":
            for entry in kustomization["configMapGenerator"][0]["literals"]:
                if entry.split("=", 1)[0] in {"DATABASE_URL", "PAYOS_API_KEY", "PAYOS_CLIENT_ID", "PAYOS_CHECKSUM_KEY"}:
                    raise ValueError("AI config breaches the read-only Booking boundary")


if __name__ == "__main__":
    check_repository()
    for path in sys.argv[1:]:
        check_documents(list(yaml.safe_load_all(Path(path).read_text())))
