"""Open local evidence beneath its trusted directory before reading any bytes."""

from __future__ import annotations

import os
import stat
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO


class EvidenceReadError(ValueError):
    """The opened evidence file cannot be bound to the allowed directory."""

    def __init__(self, message: str, *, field: str | None = None) -> None:
        self.field = field
        super().__init__(message)


def _windows_final_path(descriptor: int) -> Path:
    if sys.platform != "win32":
        raise EvidenceReadError("Windows handle inspection is unavailable on this platform")
    import ctypes
    import msvcrt
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    final_path = kernel.GetFinalPathNameByHandleW
    final_path.argtypes = (wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD)
    final_path.restype = wintypes.DWORD
    handle = msvcrt.get_osfhandle(descriptor)
    buffer = ctypes.create_unicode_buffer(32768)
    length = final_path(handle, buffer, len(buffer), 0)
    if length == 0:
        raise ctypes.WinError(ctypes.get_last_error())
    if length >= len(buffer):
        raise EvidenceReadError("opened evidence path exceeds the supported Windows path length")
    value = buffer.value
    if value.startswith("\\\\?\\UNC\\"):
        value = "\\\\" + value[8:]
    elif value.startswith("\\\\?\\"):
        value = value[4:]
    return Path(value)


def _posix_descriptor(root: Path, relative: Path) -> int:
    if sys.platform == "win32":
        raise EvidenceReadError("directory-relative POSIX opens are unavailable on Windows")
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


def _descriptor(path: Path, root: Path, relative: Path) -> int:
    if sys.platform != "win32":
        return _posix_descriptor(root, relative)
    descriptor = os.open(path, os.O_RDONLY | os.O_BINARY)
    try:
        if not _windows_final_path(descriptor).is_relative_to(root):
            raise EvidenceReadError("opened file is outside the evidence directory")
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


@contextmanager
def open_evidence(path: Path, root: Path) -> Iterator[BinaryIO]:
    """Yield one regular-file descriptor whose path is contained by the index directory.

    POSIX walks directory descriptors without following links. Windows checks the
    final path of the opened handle, including junction resolution, before reading.
    Missing platform containment support fails instead of falling back to path checks.
    """
    root = root.expanduser().resolve(strict=True)
    path = path.expanduser().absolute()
    try:
        relative = path.relative_to(root)
    except ValueError as error:
        raise EvidenceReadError("file is outside the evidence directory") from error
    if not relative.parts or ".." in relative.parts:
        raise EvidenceReadError("evidence must identify a file below the evidence directory")
    descriptor = _descriptor(path, root, relative)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise EvidenceReadError("evidence must be a regular file")
        stream = os.fdopen(descriptor, "rb")
    except BaseException:
        os.close(descriptor)
        raise
    with stream:
        yield stream
