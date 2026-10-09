"""Verify commit provenance, CI completion and keyless ECR image signatures."""
import json
import os
import subprocess
import sys
from pathlib import Path

from automation.common import APP_REPOSITORY, state, validate


def run(*args):
    return subprocess.check_output(args, text=True)


def verify(payload):
    validate(payload, "workload-release-v1.schema.json")
    platform = state()
    component = payload["component"]
    if payload["image"]["repository"] != platform["ecr"][component]:
        raise ValueError("Unapproved image repository")
    commit = payload["source"]["commit"]
    # Source must be on the application's main branch, including historical releases.
    comparison = json.loads(run("gh", "api", f"repos/{APP_REPOSITORY}/compare/{commit}...main"))
    if comparison["status"] not in {"ahead", "identical"}:
        raise ValueError("Source commit is not an ancestor of app main")
    workflow = os.environ.get("APP_CI_WORKFLOW", "ci.yml")
    runs = json.loads(run("gh", "api", f"repos/{APP_REPOSITORY}/actions/workflows/{workflow}/runs?head_sha={commit}&status=completed&per_page=100"))["workflow_runs"]
    if not any(item["conclusion"] == "success" and item["event"] == "push" and item["head_branch"] == "main" for item in runs):
        raise ValueError("Source commit has no successful main CI run")
    certificate_identity = os.environ["IMAGE_SIGNER_IDENTITY"]
    digests = [payload["image"]["digest"]]
    if payload["image"].get("migration_digest"):
        digests.append(payload["image"]["migration_digest"])
    for digest in digests:
        reference = payload["image"]["repository"] + "@" + digest
        verification = json.loads(run("cosign", "verify", "--certificate-identity", certificate_identity,
                                      "--certificate-oidc-issuer", "https://token.actions.githubusercontent.com", reference))
        if not verification:
            raise ValueError("No valid keyless image signatures")
        for signature in verification:
            critical = signature["critical"]
            if critical["image"]["docker-manifest-digest"] != digest:
                raise ValueError("Signature digest mismatch")
            if signature.get("optional", {}).get("source_commit") != commit:
                raise ValueError("Signer must bind the source_commit annotation to the release commit")


if __name__ == "__main__":
    verify(json.loads(Path(sys.argv[1]).read_text()))
