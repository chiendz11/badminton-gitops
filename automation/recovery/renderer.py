"""Recovery restores a known historical digest through a normal review PR."""
import json
import os
import re
import subprocess
from pathlib import Path

from automation.common import SERVICES, read_yaml, state
from automation.verify_release import verify
from automation.workload_release.renderer import render


def recover(component, revision, reason):
    if component not in SERVICES or not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError("Recovery needs an allowed component and full GitOps historical commit SHA")
    if not reason.strip():
        raise ValueError("Recovery reason is required")
    subprocess.run(["git", "merge-base", "--is-ancestor", revision, "origin/main"], check=True)
    text = subprocess.check_output(["git", "show", f"{revision}:state/{component}-release.yaml"], text=True)
    import yaml
    payload = yaml.safe_load(text)
    if payload["component"] != component:
        raise ValueError("Historical release does not match requested component")
    verify(payload)
    render(payload)
    Path("state/last-recovery.json").write_text(json.dumps({
        "component": component, "historical_commit": revision, "reason": reason,
        "image_digest": payload["image"]["digest"],
    }, indent=2) + "\n")


if __name__ == "__main__":
    recover(os.environ["RECOVERY_COMPONENT"], os.environ["RECOVERY_COMMIT"], os.environ["RECOVERY_REASON"])
