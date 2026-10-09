"""One approved component, one immutable digest; no caller-controlled paths."""
import argparse
import json
from pathlib import Path

from automation.common import SERVICES, application_name, enable_application, read_yaml, state, validate, write_yaml


def render(payload):
    validate(payload, "workload-release-v1.schema.json")
    component = payload["component"]
    platform = state()
    image = payload["image"]
    if image["repository"] != platform["ecr"][component]:
        raise ValueError("Image repository does not match the platform ECR allow-list")
    if image["digest"] == "sha256:" + "0" * 64:
        raise ValueError("A placeholder digest is not a release")
    if component in {"identity-service", "booking-core", "commerce-service"}:
        if not image.get("migration_digest") or image["migration_digest"] == "sha256:" + "0" * 64:
            raise ValueError("Prisma services require a separate signed migration image digest")
    if component in {"social-service", "content-service", "notification-service", "storage-service"} and not platform.get("mongodb_allowed_cidrs"):
        raise ValueError("Configure explicit MongoDB network CIDRs before releasing this workload")
    path = f"environments/production/{component}/kustomization.yaml"
    doc = read_yaml(path)
    doc["images"] = [{"name": f"badminton-{component}", "newName": image["repository"], "digest": image["digest"]}]
    if component in {"identity-service", "booking-core", "commerce-service"}:
        doc["images"].append({"name": f"badminton-{component}-migrations", "newName": image["repository"], "digest": image["migration_digest"]})
    write_yaml(path, doc)
    enable_application(application_name(component))
    # Expose edge only after all ALB backend services have an image release.
    if all("digest" in read_yaml(f"environments/production/{s}/kustomization.yaml")["images"][0]
           for s in ("web", "admin", "api-gateway", "social-service")):
        enable_application("workload-edge")
    write_yaml(f"state/{component}-release.yaml", payload)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("payload", type=Path)
    args = parser.parse_args()
    render(json.loads(args.payload.read_text()))
