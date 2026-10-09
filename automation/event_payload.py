"""Read workflow input as data; never interpolate JSON into a shell script."""
import json
import os
from pathlib import Path

event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
if os.environ["GITHUB_EVENT_NAME"] == "repository_dispatch":
    payload = event["client_payload"]["contract"]
else:
    payload = json.loads(event["inputs"]["contract"])
Path("payload.json").write_text(json.dumps(payload, indent=2) + "\n")
