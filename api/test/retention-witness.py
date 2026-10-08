#!/usr/bin/env python3
"""Count fixed CLI custody calls in the owned integration fixture only."""

import hashlib
import json
import os
import sys
import uuid
from pathlib import Path

original = "/usr/local/libexec/retained-artifact"
expected = "398bf5e45b215d50e67433071ef218f4dff58fca44ab056114fdd6f180c2098c"
if hashlib.sha256(Path(original).read_bytes()).hexdigest() != expected:
    raise RuntimeError("original retention executable changed")
if len(sys.argv) > 1 and sys.argv[1] in ("predicate", "verify"):
    registration = json.loads(Path(sys.argv[sys.argv.index("--registration") + 1]).read_bytes())
    upload = registration["uri"].split("/")[-2]
    if str(uuid.UUID(upload)) != upload:
        raise RuntimeError("fixture upload identity is not canonical")
    target = Path("/fixture/cli-attempts.jsonl")
    if target.exists() and target.stat().st_size > 65536:
        raise RuntimeError("fixture custody witness exceeds its bound")
    event = (
        json.dumps({"upload": upload, "operation": sys.argv[1]}, separators=(",", ":")) + "\n"
    ).encode()
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.write(descriptor, event)
    finally:
        os.close(descriptor)
os.execv(original, [original, *sys.argv[1:]])
