from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

import httpx
from signalflag.sdk.batch import Batch
from signalflag.sdk.bff_client.metrics import sync_config
from signalflag.sdk.client import AuthenticatedClient
from signalflag.sdk.metrics.emissions import ReSimValidationError
from signalflag.sdk.test import LogType, Test

configuration = json.loads(Path("/run/secrets/consumer.json").read_text())
result = {
    "scope": "SDK1.8.0 limited external Test on local API; no native qualification",
    "tenants": [],
}
config_path = Path(".resim/metrics/config.resim.yml")
config_path.parent.mkdir(parents=True, exist_ok=True)
config_bytes = (
    b"version: 1\n"
    b"topics:\n"
    b"  motion:\n    event: true\n    schema:\n      speed: float\n"
    b"  note:\n    event: true\n    schema:\n      text: string\n"
    b"  untimed:\n    schema:\n      value: int\n"
)
config_path.write_bytes(config_bytes)
templates = Path(".resim/metrics/templates")
templates.mkdir()
template_bytes = b'{% include "/etc/passwd" %} {{ secret | eval }}\n'
(templates / "opaque.liquid").write_bytes(template_bytes)
png = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aHioAAAAASUVORK5CYII="
)
for tenant in configuration["tenants"]:
    # Public constructor options; the installed SDK files and generated models are unchanged.
    client = AuthenticatedClient(
        base_url="http://api:3000", token=tenant["token"], timeout=httpx.Timeout(90.0)
    )
    lost_config_response = False
    if not result["tenants"]:
        try:
            sync_config(client, tenant["project"], "main")
        except httpx.RemoteProtocolError:
            lost_config_response = True
        assert lost_config_response
    # The caller explicitly invokes Batch after the lost response; sync_config itself has no retry.
    Path("attachment.png").write_bytes(png)
    Path("empty.log").write_bytes(b"")
    with Batch(
        client=client,
        project_id=tenant["project"],
        branch="main",
        name="External Test",
    ) as batch:
        with Test(client=client, batch=batch, name="opaque external test") as run:
            rejected_invalid_emission = False
            try:
                run.emit("motion", {"speed": "wrong-type"})
            except ReSimValidationError:
                rejected_invalid_emission = True
            assert rejected_invalid_emission
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
                "caller_retries_after_lost_config_response": lost_config_response,
                "default_config_sha256": hashlib.sha256(config_bytes).hexdigest(),
                "default_config_size": len(config_bytes),
                "template_sha256": hashlib.sha256(template_bytes).hexdigest(),
                "template_size": len(template_bytes),
                "local_sdk_validation_refused_wrong_type": rejected_invalid_emission,
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
