"""Argument parsing and dispatch for the bounded document producer commands."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping
from pathlib import Path

from robotics_runtime_contracts import load_mapping
from robotics_runtime_contracts.recordings import recording_summary_from_mcap
from robotics_runtime_contracts.statements import write_qualification_statement
from robotics_runtime_contracts.writers import (
    add_evidence_artifact,
    create_artifact_receipt,
    create_evidence_index,
    create_runtime_manifest,
    evidence_sources,
    finalize_evidence_index,
    protect_inputs,
    write_document,
    write_evidence_draft,
)


def _template_command(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--template", required=True, metavar="PATH")
    parser.add_argument("--output", required=True, metavar="PATH")


def add_writer_commands[ParserT: argparse.ArgumentParser](
    subparsers: argparse._SubParsersAction[ParserT],
    add_extensions: Callable[[argparse.ArgumentParser], None],
) -> None:
    runtime = subparsers.add_parser("runtime-manifest", help="produce an explicit runtime manifest")
    init = runtime.add_subparsers(dest="operation", required=True).add_parser("init")
    _template_command(init)
    add_extensions(init)
    init.set_defaults(writer_operation="runtime")

    evidence = subparsers.add_parser("evidence-index", help="build and finalize an evidence index")
    operations = evidence.add_subparsers(dest="operation", required=True)
    init = operations.add_parser("init", help="create writer state, not a finalized public index")
    _template_command(init)
    add_extensions(init)
    init.set_defaults(writer_operation="evidence_init")
    _add_evidence_operations(operations, add_extensions)
    _add_receipt_command(subparsers, add_extensions)

    recording = subparsers.add_parser("recording-summary", help="extract observed MCAP statistics")
    mcap = recording.add_subparsers(dest="operation", required=True).add_parser("from-mcap")
    mcap.add_argument("source", metavar="MCAP")
    mcap.add_argument("--output", required=True, metavar="PATH")
    add_extensions(mcap)
    mcap.set_defaults(writer_operation="recording")

    qualification = subparsers.add_parser(
        "qualification", help="produce a validated qualification bundle"
    )
    statement = qualification.add_subparsers(dest="operation", required=True).add_parser(
        "statement"
    )
    statement.add_argument(
        "--artifact", action="append", required=True, metavar="KIND:SUBJECT=PATH"
    )
    statement.add_argument("--output", required=True, metavar="PATH")
    add_extensions(statement)
    statement.set_defaults(writer_operation="qualification_statement")


def _add_receipt_command[ParserT: argparse.ArgumentParser](
    subparsers: argparse._SubParsersAction[ParserT],
    add_extensions: Callable[[argparse.ArgumentParser], None],
) -> None:
    receipt = subparsers.add_parser(
        "artifact-receipt", help="bind a receipt to source bytes and external verification"
    )
    create = receipt.add_subparsers(dest="operation", required=True).add_parser("create")
    _template_command(create)
    create.add_argument("--source", required=True, metavar="PATH")
    create.add_argument("--verification", required=True, metavar="PATH")
    create.add_argument("--dependency", action="append", required=True, metavar="PATH")
    add_extensions(create)
    create.set_defaults(writer_operation="artifact_receipt")


def _add_evidence_operations[ParserT: argparse.ArgumentParser](
    operations: argparse._SubParsersAction[ParserT],
    add_extensions: Callable[[argparse.ArgumentParser], None],
) -> None:
    add = operations.add_parser("add-artifact")
    add.add_argument("draft", metavar="DRAFT")
    add.add_argument("--source", required=True, metavar="PATH")
    add.add_argument("--metadata", required=True, metavar="PATH")
    add.add_argument("--recording-summary", metavar="PATH")
    add.add_argument("--output", metavar="PATH", help="defaults to atomic replacement of DRAFT")
    add_extensions(add)
    add.set_defaults(writer_operation="evidence_add")
    finalize = operations.add_parser("finalize")
    finalize.add_argument("draft", metavar="DRAFT")
    finalize.add_argument("--output", required=True, metavar="PATH")
    add_extensions(finalize)
    finalize.set_defaults(writer_operation="evidence_finalize")


def _runtime(arguments: argparse.Namespace, extensions: Mapping[str, bytes]) -> Path:
    protect_inputs(arguments.output, (arguments.template,))
    document = create_runtime_manifest(
        load_mapping(arguments.template), extension_schemas=extensions
    )
    return write_document(document, arguments.output, extension_schemas=extensions)


def _evidence_init(arguments: argparse.Namespace, extensions: Mapping[str, bytes]) -> Path:
    protect_inputs(arguments.output, (arguments.template,))
    draft = create_evidence_index(load_mapping(arguments.template), extension_schemas=extensions)
    return write_evidence_draft(draft, arguments.output, extension_schemas=extensions)


def _evidence_add(arguments: argparse.Namespace, extensions: Mapping[str, bytes]) -> Path:
    output = arguments.output or arguments.draft
    protect_inputs(output, (arguments.metadata, arguments.source))
    draft = add_evidence_artifact(
        load_mapping(arguments.draft),
        arguments.source,
        load_mapping(arguments.metadata),
        recording_summary=arguments.recording_summary,
        extension_schemas=extensions,
    )
    return write_evidence_draft(draft, output, extension_schemas=extensions)


def _evidence_finalize(arguments: argparse.Namespace, extensions: Mapping[str, bytes]) -> Path:
    document = finalize_evidence_index(load_mapping(arguments.draft), extension_schemas=extensions)
    protect_inputs(arguments.output, evidence_sources(document))
    return write_document(document, arguments.output, extension_schemas=extensions)


def _recording(arguments: argparse.Namespace, _extensions: Mapping[str, bytes]) -> Path:
    protect_inputs(arguments.output, (arguments.source,))
    return write_document(recording_summary_from_mcap(arguments.source), arguments.output)


def _artifact_receipt(arguments: argparse.Namespace, _extensions: Mapping[str, bytes]) -> Path:
    protect_inputs(
        arguments.output,
        [arguments.template, arguments.source, arguments.verification, *arguments.dependency],
    )
    document = create_artifact_receipt(
        load_mapping(arguments.template),
        arguments.source,
        arguments.verification,
        arguments.dependency,
    )
    return write_document(document, arguments.output)


def _qualification_statement(
    arguments: argparse.Namespace, extensions: Mapping[str, bytes]
) -> Path:
    return write_qualification_statement(
        arguments.artifact, arguments.output, extension_schemas=extensions
    )


def run_writer(arguments: argparse.Namespace, extensions: Mapping[str, bytes]) -> Path:
    output = arguments.output
    if arguments.writer_operation == "evidence_add" and not output:
        output = arguments.draft
    protect_inputs(output, [item.partition("=")[2] for item in arguments.extension_schema])
    operations = {
        "runtime": _runtime,
        "evidence_init": _evidence_init,
        "evidence_add": _evidence_add,
        "evidence_finalize": _evidence_finalize,
        "recording": _recording,
        "artifact_receipt": _artifact_receipt,
        "qualification_statement": _qualification_statement,
    }
    return operations[arguments.writer_operation](arguments, extensions)
