"""Open local evidence beneath its trusted directory before reading any bytes."""

from __future__ import annotations

import os
import stat
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO


class EvidenceReadError(ValueError):
    """The opened evidence file cannot be bound to the allowed directory."""

    def __init__(self, message: str, *, field: str | None = None) -> None:
        self.field = field
        super().__init__(message)


def _descriptor(root: Path, relative: Path) -> int:
    if not all(hasattr(os, flag) for flag in ("O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK")):
        raise EvidenceReadError("evidence containment requires POSIX directory descriptors")
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    directory = os.open(root, directory_flags)
    try:
        for component in relative.parts[:-1]:
            nested = os.open(component, directory_flags, dir_fd=directory)
            os.close(directory)
            directory = nested
        return os.open(
            relative.name,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=directory,
        )
    finally:
        os.close(directory)


@contextmanager
def open_evidence(path: Path, root: Path) -> Iterator[BinaryIO]:
    """Yield one regular-file descriptor whose path is contained by the index directory.

    Directory descriptors are walked without following links, and the final file is
    opened without blocking on a FIFO. Platforms without directory-relative opens
    fail instead of falling back to path checks.
    """
    root = root.expanduser().resolve(strict=True)
    path = path.expanduser().absolute()
    try:
        relative = path.relative_to(root)
    except ValueError as error:
        raise EvidenceReadError("file is outside the evidence directory") from error
    if not relative.parts or ".." in relative.parts:
        raise EvidenceReadError("evidence must identify a file below the evidence directory")
    descriptor = _descriptor(root, relative)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise EvidenceReadError("evidence must be a regular file")
        stream = os.fdopen(descriptor, "rb")
    except BaseException:
        os.close(descriptor)
        raise
    with stream:
        yield stream
