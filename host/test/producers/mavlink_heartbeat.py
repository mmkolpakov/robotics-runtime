"""Heartbeat-only discovery fixture using upstream pymavlink."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import signal
import time
from pathlib import Path

from pymavlink import mavutil

parser = argparse.ArgumentParser()
parser.add_argument("--endpoint", required=True)
parser.add_argument("--seconds", type=float, default=15)
parser.add_argument("--report", required=True, type=Path)
args = parser.parse_args()
active = True


def stop(_signal: int, _frame: object) -> None:
    global active
    active = False


signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)
link = mavutil.mavlink_connection(
    args.endpoint, source_system=1, source_component=1, dialect="common"
)
codec = Path(mavutil.mavlink.__file__)
report = {
    "scope": "heartbeat discovery only; no health, control or flight qualification",
    "pymavlink_version": importlib.metadata.version("pymavlink"),
    "codec_source": str(codec),
    "codec_sha256": hashlib.sha256(codec.read_bytes()).hexdigest(),
    "heartbeat_count": 0,
}
deadline = time.monotonic() + args.seconds
try:
    while active and time.monotonic() < deadline:
        link.mav.heartbeat_send(
            mavutil.mavlink.MAV_TYPE_QUADROTOR,
            mavutil.mavlink.MAV_AUTOPILOT_PX4,
            0,
            0,
            mavutil.mavlink.MAV_STATE_STANDBY,
        )
        report["heartbeat_count"] += 1
        time.sleep(0.2)
finally:
    link.close()
    args.report.write_text(json.dumps(report, sort_keys=True) + "\n", encoding="utf-8")
