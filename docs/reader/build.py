"""Stage tracked public documents, resolve repository links, and run Sphinx."""

from __future__ import annotations

import json
import os
import posixpath
import shutil
import subprocess
import sys
from functools import partial
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit, urlunsplit
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from packaging.requirements import Requirement
from packaging.version import Version

REPOSITORY = "https://github.com/mmkolpakov/robotics-runtime"
PUBLIC_ROOTS = (
    "docs/",
    "packages/contracts/docs/",
    "packages/contracts/consumer-examples/",
    "packages/harness/docs/",
)
PUBLIC_FILES = {"README.md", "host/README.md", "mcp/README.md", "quality/README.md"}
PACKAGE_ROOTS = {"packages/contracts", "packages/harness"}
CONSUMER_ROOT = "packages/contracts/consumer-examples/published-cli"
CONSUMER_INPUTS = frozenset(
    f"{CONSUMER_ROOT}/{name}"
    for name in ("README.md", "produce.py", "scenario-input.json", "runtime-template.json")
)
DIAGRAM_SOURCES = frozenset(
    {
        "docs/architecture/workspace.dsl",
        "docs/architecture/run-sequence.mmd",
        "docs/architecture/run-state.mmd",
    }
)


def git(root: Path, *arguments: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *arguments], text=True).strip()


def public_document(name: str) -> bool:
    path = Path(name)
    return (
        path.name != "AGENTS.md"
        and not any(part.startswith(".") for part in path.parts)
        and (path.suffix in {".md", ".svg"} or name in DIAGRAM_SOURCES)
        and (
            name in PUBLIC_FILES
            or path.parent.as_posix() in PACKAGE_ROOTS
            or any(name.startswith(prefix) for prefix in PUBLIC_ROOTS)
        )
    )


def reader_path(name: str) -> str:
    return "index.md" if name == "README.md" else name


def repository_references(app, doctree, *, manifest, tracked):
    """Map MyST-parsed repository references without parsing Markdown syntax."""
    from docutils import nodes
    from sphinx import addnodes

    docname = app.env.docname
    original = "README.md" if docname == "index" else docname + ".md"
    for node in list(doctree.findall(addnodes.pending_xref)):
        if node.get("reftype") != "myst" or node.get("refdomain") == "doc":
            continue
        parts = urlsplit(node["reftarget"])
        if parts.scheme or parts.netloc or not parts.path:
            continue
        name = posixpath.normpath(posixpath.join(posixpath.dirname(original), unquote(parts.path)))
        if name == "README.md":
            node["refdomain"] = "doc"
            node["reftarget"] = "index"
            node["reftargetid"] = parts.fragment or None
        elif name not in manifest["files"]:
            directory = any(item.startswith(name.rstrip("/") + "/") for item in tracked)
            if name not in tracked and not directory:
                continue
            kind = "tree" if directory else "blob"
            url = f"{manifest['repository']}/{kind}/{manifest['revision']}/{quote(name, safe='/')}"
            uri = urlunsplit((*urlsplit(url)[:3], parts.query, parts.fragment))
            node.replace_self(nodes.reference("", "", *node.children, refuri=uri, internal=False))


def setup_references(app):
    manifest = json.loads((Path(app.srcdir) / "source-manifest.json").read_text())
    root = Path(__file__).resolve().parents[2]
    tracked = set(git(root, "ls-files", "-z").split("\0"))
    app.connect("doctree-read", partial(repository_references, manifest=manifest, tracked=tracked))


def navigation(name: str, documents: set[str]) -> str:
    entries = []
    for item in sorted(documents):
        if item == name or not item.endswith(".md"):
            continue
        parent = Path(item).parent
        if item.endswith("README.md"):
            parent = parent.parent
        while parent.as_posix() != "." and f"{parent}/README.md" not in documents:
            parent = parent.parent
        owner = f"{parent}/README.md" if parent.as_posix() != "." else "README.md"
        if owner == name:
            relative = posixpath.relpath(
                reader_path(item), posixpath.dirname(reader_path(name)) or "."
            )
            entries.append(relative.removesuffix(".md"))
    if not entries:
        return ""
    return "\n\n```{toctree}\n:maxdepth: 2\n\n" + "\n".join(entries) + "\n```\n"


def verify_toolchain(root: Path) -> None:
    for line in (root / "docs/reader/requirements.in").read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        requirement = Requirement(line)
        pins = list(requirement.specifier)
        if (
            len(pins) != 1
            or pins[0].operator != "=="
            or requirement.url
            or requirement.marker is not None
            or requirement.extras
        ):
            raise ValueError(f"Documentation dependency must have one exact pin: {requirement}")
        pinned = Version(pins[0].version)
        if Version(version(requirement.name)) != pinned:
            raise ValueError(f"Installed documentation toolchain disagrees with {requirement}")


def main() -> None:
    root = Path(git(Path.cwd(), "rev-parse", "--show-toplevel"))
    verify_toolchain(root)
    if os.environ.get("GITHUB_ACTIONS") == "true" and git(
        root, "status", "--porcelain", "--untracked-files=no"
    ):
        raise ValueError("CI documentation must be built from clean committed source")
    output = root / "build" / "docs"
    if output.exists():
        shutil.rmtree(output)
    source = output / "source"
    source.mkdir(parents=True)
    revision = git(root, "rev-parse", "HEAD")
    tracked = set(git(root, "ls-files", "-z").split("\0"))
    documents = {name for name in tracked if public_document(name)}
    hashes = {}
    raw_files = {}
    for name in sorted(documents):
        path = root / name
        if path.is_symlink():
            raise ValueError(f"Documentation source must be a regular tracked file: {name}")
        raw = path.read_bytes()
        raw_files[name] = raw
        hashes[name] = sha256(raw).hexdigest()
        destination = source / reader_path(name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if name.endswith(".md"):
            text = raw.decode()
            if name.endswith("README.md"):
                text += navigation(name, documents)
            if name == "README.md":
                notice = (
                    "\n```{note}\nThis reader follows development source. "
                    "Installable packages are on [contracts PyPI]"
                    "(https://pypi.org/project/robotics-runtime-contracts/) "
                    "and [harness PyPI](https://pypi.org/project/robotics-acceptance-harness/). "
                    "Frozen examples retain their own release and commit pins.\n```\n\n"
                    "[Infra documentation]"
                    "(https://github.com/mmkolpakov/robotics-runtime-infra) · "
                    "[Releases](https://github.com/mmkolpakov/robotics-runtime/releases) · "
                    '<a href="documentation-sources.zip">Markdown, SVG and diagram source</a> · '
                    '<a href="index.txt">Plain text</a> · '
                    '<a href="llms.txt">LLM index</a> · '
                    '<a href="llms-full.txt">Full LLM text</a>\n'
                )
                title, rest = text.split("\n", 1)
                text = title + "\n" + notice + rest
            if name == "docs/first-result.md":
                title, rest = text.split("\n", 1)
                text = (
                    title + "\n\n"
                    '<a href="../consumer-inputs.zip">Download consumer inputs</a> · '
                    '<a href="../source-manifest.json">Documentation source manifest</a>\n'
                    + rest
                )
            destination.write_text(text)
        else:
            destination.write_bytes(raw)
    for name in sorted(CONSUMER_INPUTS):
        path = root / name
        if name not in tracked or path.is_symlink() or not path.is_file():
            raise ValueError(f"Consumer input must be a regular tracked file: {name}")
        raw_files[name] = path.read_bytes()
        hashes[name] = sha256(raw_files[name]).hexdigest()
    manifest = {
        "repository": REPOSITORY,
        "revision": revision,
        "working_copy": bool(git(root, "diff", "--name-only", "HEAD", "--", *sorted(raw_files))),
        "files": hashes,
    }
    (source / "source-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    with ZipFile(source / "documentation-sources.zip", "w", compression=ZIP_DEFLATED) as archive:
        for name in sorted(raw_files):
            entry = ZipInfo(name)
            entry.compress_type = ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, raw_files[name])
    consumer_manifest = {
        "repository": REPOSITORY,
        "revision": revision,
        "working_copy": manifest["working_copy"],
        "files": {Path(name).name: hashes[name] for name in sorted(CONSUMER_INPUTS)},
    }
    with ZipFile(source / "consumer-inputs.zip", "w", compression=ZIP_DEFLATED) as archive:
        for name in sorted(CONSUMER_INPUTS):
            entry = ZipInfo(Path(name).name)
            entry.compress_type = ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, raw_files[name])
        entry = ZipInfo("manifest.json")
        entry.compress_type = ZIP_DEFLATED
        entry.external_attr = 0o100644 << 16
        archive.writestr(entry, json.dumps(consumer_manifest, indent=2) + "\n")
    (source / "text").mkdir()
    configuration = root / "docs" / "reader"
    for builder, destination in (("text", output / "text"), ("html", output / "html")):
        if builder == "html":
            shutil.copytree(output / "text", source / "text", dirs_exist_ok=True)
        subprocess.run(
            [
                sys.executable,
                "-m",
                "sphinx",
                "-b",
                builder,
                "-W",
                "--keep-going",
                "-c",
                str(configuration),
                "-d",
                str(output / "doctrees" / builder),
                str(source),
                str(destination),
            ],
            check=True,
        )
    for name in documents:
        if name.endswith(".svg"):
            destination = output / "html" / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw_files[name])
    for name in (
        "index.html",
        "search.html",
        "searchindex.js",
        "index.txt",
        "llms.txt",
        "llms-full.txt",
        "_sources/index.md",
        "documentation-sources.zip",
        "consumer-inputs.zip",
    ):
        path = output / "html" / name
        if not path.is_file() or not path.stat().st_size:
            raise ValueError(f"Documentation output is missing or empty: {name}")
    full_text = (output / "html" / "llms-full.txt").read_text()
    with ZipFile(output / "html" / "consumer-inputs.zip") as archive:
        exported_manifest = json.loads(archive.read("manifest.json"))
        if set(archive.namelist()) != {"manifest.json", *exported_manifest["files"]}:
            raise ValueError("Consumer archive contains an unexpected file set")
        for name, digest in exported_manifest["files"].items():
            if sha256(archive.read(name)).hexdigest() != digest:
                raise ValueError(f"Consumer archive digest disagrees with its manifest: {name}")
    for name in DIAGRAM_SOURCES:
        body = "\n".join(
            f"   {line}" if line.strip() else "" for line in raw_files[name].decode().splitlines()
        )
        exported = f"\n{name}\n{'=' * len(name)}\n\n.. code-block:: text\n\n{body}"
        if full_text.count(exported) != 1:
            raise ValueError(
                f"Canonical diagram source must appear exactly once in LLM export: {name}"
            )
    print(
        json.dumps({"documents": len(documents), "revision": revision, "output": "build/docs/html"})
    )


if __name__ == "__main__":
    main()
