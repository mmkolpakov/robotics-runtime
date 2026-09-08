"""Observed MCAP facts, with data definitions authoritative over summary copies."""

from collections import Counter
from dataclasses import dataclass, field

from mcap.records import Attachment, Channel, DataEnd, McapRecord, Message, Metadata, Schema

from robotics_runtime_contracts.writers import WriterError


def _invalid(message: str) -> WriterError:
    return WriterError(message, error_id="writer.invalid_mcap")


def _definition[RecordT: (Schema, Channel)](
    definitions: dict[int, RecordT], record: RecordT, in_summary: bool
) -> None:
    previous = definitions.get(record.id)
    if previous is not None:
        if record != previous:
            raise _invalid(f"conflicting MCAP {type(record).__name__} ID {record.id}")
    elif in_summary:
        raise _invalid(f"MCAP summary {type(record).__name__} lacks a data definition")
    else:
        definitions[record.id] = record


@dataclass
class Observations:
    schemas: dict[int, Schema] = field(default_factory=dict)
    channels: dict[int, Channel] = field(default_factory=dict)
    messages: Counter[int] = field(default_factory=Counter)
    attachments: int = 0
    metadata: int = 0
    start: int | None = None
    end: int = 0
    in_summary: bool = False

    def definition(self, record: Schema | Channel) -> None:
        if isinstance(record, Schema):
            if record.id == 0:
                raise _invalid("MCAP schema ID must be nonzero")
            _definition(self.schemas, record, self.in_summary)
        else:
            if record.schema_id == 0:
                raise _invalid("recording-summary.v1 requires a named schema for every channel")
            if record.schema_id not in self.schemas:
                raise _invalid(f"MCAP channel refers to undefined schema {record.schema_id}")
            _definition(self.channels, record, self.in_summary)

    def message(self, record: Message) -> None:
        if self.in_summary:
            raise _invalid("MCAP message occurs after DataEnd")
        if record.channel_id not in self.channels:
            raise _invalid(f"MCAP message refers to undefined channel {record.channel_id}")
        self.messages[record.channel_id] += 1
        self.start = record.log_time if self.start is None else min(self.start, record.log_time)
        self.end = max(self.end, record.log_time)

    def auxiliary(self, record: Attachment | Metadata) -> None:
        if self.in_summary:
            raise _invalid("MCAP attachment/metadata occurs after DataEnd")
        if isinstance(record, Attachment):
            self.attachments += 1
        else:
            self.metadata += 1

    def observe(self, record: McapRecord) -> None:
        if isinstance(record, DataEnd):
            if self.in_summary:
                raise _invalid("duplicate MCAP DataEnd")
            self.in_summary = True
        elif isinstance(record, (Schema, Channel)):
            self.definition(record)
        elif isinstance(record, Message):
            self.message(record)
        elif isinstance(record, (Attachment, Metadata)):
            self.auxiliary(record)

    def statistics(self) -> dict[str, int]:
        if not self.in_summary:
            raise _invalid("MCAP requires DataEnd before its summary")
        return {
            "message_count": sum(self.messages.values()),
            "schema_count": len(self.schemas),
            "channel_count": len(self.channels),
            "attachment_count": self.attachments,
            "metadata_count": self.metadata,
            "message_start_time_ns": 0 if self.start is None else self.start,
            "message_end_time_ns": self.end,
        }
