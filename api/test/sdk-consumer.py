from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

import httpx
from signalflag.sdk.batch import Batch
from signalflag.sdk.client import AuthenticatedClient
from signalflag.sdk.test import LogType, Test

configuration = json.loads(Path("/run/secrets/consumer.json").read_text())
result = {
    "scope": "SDK1.8.0 limited external Test on local API; no native qualification",
    "tenants": [],
}
png = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aHioAAAAASUVORK5CYII="
)
for tenant in configuration["tenants"]:
    # Public constructor options; the installed SDK files and generated models are unchanged.
    client = AuthenticatedClient(
        base_url="http://api:3000", token=tenant["token"], timeout=httpx.Timeout(90.0)
    )
    Path("attachment.png").write_bytes(png)
    Path("empty.log").write_bytes(b"")
    with Batch(
        client=client,
        project_id=tenant["project"],
        branch="main",
        name="External Test",
        metrics_config_path=None,
        templates_path=None,
    ) as batch:
        with Test(client=client, batch=batch, name="opaque external test") as run:
            epoch = 1_791_000_000_000_000_000
            run.emit("motion", {"speed": 1}, timestamp=epoch)
            run.emit_series("motion", {"speed": [2, 3]}, timestamps=[epoch + 1, epoch + 2])
            run.emit_event("motion", {"speed": 4}, timestamp=epoch + 3)
            run.emit_event("note", {"text": "opaque"}, timestamp=epoch + 4)
            run.emit("untimed", {"value": 7})
            run.attach_log("attachment.png", log_type=LogType.OTHER_LOG, wait=True)
            run.attach_log("empty.log", log_type=LogType.OTHER_LOG, wait=True)
            job_id = run.job_id
        path = Path(f"emissions_{job_id}.resim.jsonl")
        raw = path.read_bytes()
        result["tenants"].append(
            {
                "project": tenant["project"],
                "batch": batch.id,
                "job": job_id,
                "emissions_sha256": hashlib.sha256(raw).hexdigest(),
                "emissions_size": len(raw),
                "png_sha256": hashlib.sha256(png).hexdigest(),
                "empty_sha256": hashlib.sha256(b"").hexdigest(),
            }
        )
Path("/work/sdk-report.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"passed": True, "tenants": len(result["tenants"])}))
