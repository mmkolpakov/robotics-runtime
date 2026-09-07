from __future__ import annotations

import atexit
from contextlib import ExitStack
from functools import cache
from importlib.resources import as_file, files
from pathlib import Path

_resource_contexts = ExitStack()
atexit.register(_resource_contexts.close)


@cache
def schema_directory() -> Path:
    """Keep extracted resources alive for the lifetime of the public Path API."""

    return _resource_contexts.enter_context(
        as_file(files("robotics_runtime_contracts").joinpath("schemas"))
    )
