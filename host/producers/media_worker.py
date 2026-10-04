"""Finite GStreamer/GI lifecycle worker. Frames stay in the configured native pipeline."""

from __future__ import annotations

import argparse
import json
import signal
import time
from pathlib import Path

import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402 - GI version is selected before namespace import


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--deadline-ms", required=True, type=int)
    parser.add_argument("--ready-marker", type=Path)
    args = parser.parse_args()
    if not 0 < args.deadline_ms <= 2147483647:
        raise ValueError("deadline-ms must be a positive bounded integer")
    # Exclusive output admission precedes native execution; retained inputs cannot be overwritten.
    output = args.report.open("x", encoding="utf-8")
    ready_output = args.ready_marker.open("x", encoding="utf-8") if args.ready_marker else None
    config = json.loads(args.config.read_bytes())
    Gst.init(None)
    canceled = False

    def cancel(_signal: int, _frame: object) -> None:
        nonlocal canceled
        canceled = True

    signal.signal(signal.SIGTERM, cancel)
    signal.signal(signal.SIGINT, cancel)
    report = {
        "status": "error",
        "gstreamer": Gst.version_string(),
        "events": [],
        "playing": False,
        "cleanup": {"observed": None, "succeeded": False},
    }
    pipeline = None
    try:
        pipeline = Gst.parse_launch(config["pipeline"])
        change = pipeline.set_state(Gst.State.PLAYING)
        state = pipeline.get_state(min(args.deadline_ms, 5000) * Gst.MSECOND)
        report["state"] = {
            "requested": "playing",
            "return": change.value_nick,
            "observed": state[1].value_nick,
            "pending": state[2].value_nick,
        }
        report["playing"] = state[1] == Gst.State.PLAYING
        if ready_output is not None:
            ready_output.write(
                json.dumps({"playing": report["playing"], "observed": state[1].value_nick}) + "\n"
            )
            ready_output.flush()
        deadline = time.monotonic() + args.deadline_ms / 1000
        bus = pipeline.get_bus()
        while time.monotonic() < deadline and not canceled:
            message = bus.timed_pop_filtered(
                100 * Gst.MSECOND, Gst.MessageType.EOS | Gst.MessageType.ERROR
            )
            if message is None:
                continue
            if message.type == Gst.MessageType.ERROR:
                error, debug = message.parse_error()
                report["events"].append({"type": "error", "message": str(error), "debug": debug})
                break
            report["events"].append({"type": "eos"})
            report["status"] = "eos"
            break
        else:
            report["status"] = "canceled" if canceled else "timeout"
        ok, position = pipeline.query_position(Gst.Format.TIME)
        report["position"] = {
            "available": bool(ok),
            "native_unit": "nanoseconds",
            "native_representation": "int64",
            "value": str(position) if ok else None,
        }
    except Exception as error:
        report["events"].append({"type": "error", "message": str(error)})
    finally:
        if pipeline is not None:
            change = pipeline.set_state(Gst.State.NULL)
            state = pipeline.get_state(5000 * Gst.MSECOND)
            report["cleanup"] = {
                "requested": "null",
                "return": change.value_nick,
                "observed": state[1].value_nick,
                "succeeded": state[1] == Gst.State.NULL,
            }
        output.write(json.dumps(report, allow_nan=False, sort_keys=True) + "\n")
        output.close()
        if ready_output is not None:
            ready_output.close()
    print(json.dumps({"status": report["status"], "report": str(args.report)}, sort_keys=True))
    return (
        0
        if report["status"] == "eos" and report["playing"] and report["cleanup"]["succeeded"]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
