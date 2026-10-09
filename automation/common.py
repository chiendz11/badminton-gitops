"""Shared contract validation and deterministic file I/O."""
import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SERVICES = (
    "web", "admin", "api-gateway", "identity-service", "booking-core",
    "commerce-service", "social-service", "content-service",
    "notification-service", "storage-service", "ai-service",
)
APP_REPOSITORY = "chiendz11/badminton_system"


def validate(payload, schema):
    definition = json.loads((ROOT / "contracts" / schema).read_text())
    Draft202012Validator(definition).validate(payload)
    return payload


def read_yaml(path):
    return yaml.safe_load((ROOT / path).read_text())


def write_yaml(path, value):
    (ROOT / path).write_text(yaml.safe_dump(value, sort_keys=False, width=110))


def state():
    value = json.loads((ROOT / "state/production-platform.json").read_text())
    if value.get("configured") is False:
        raise ValueError("Merge a verified platform contract before releasing workloads")
    return validate(value, "platform-contract-v1.schema.json")


def enable_application(name):
    path = f"applications/{name}.yaml"
    application = read_yaml(path)
    application["spec"]["syncPolicy"]["automated"] = {"prune": True, "selfHeal": True}
    write_yaml(path, application)


def application_name(component):
    if component not in SERVICES:
        raise ValueError("Component is not allow-listed")
    return f"workload-{component}"
