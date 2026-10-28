from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from tws_belief.models import Claim, EvidenceRecord


class ArmbenchEvidenceAdapter:
    """Validate derived ARMBench metadata and convert it into core claims.

    This adapter intentionally consumes the repository's normalized evidence
    schema. It does not infer Amazon robot beliefs or parse undocumented native
    dataset internals.
    """

    DATASET_NAME = "ARMBench"

    def adapt(self, data: Mapping[str, Any]) -> EvidenceRecord:
        record = EvidenceRecord.from_dict(data)
        if record.dataset != self.DATASET_NAME:
            raise ValueError(
                f"dataset must be {self.DATASET_NAME!r}, got {record.dataset!r}"
            )
        return record

    def claims_from_records(
        self,
        records: Iterable[EvidenceRecord],
    ) -> tuple[Claim, ...]:
        ordered = sorted(records, key=lambda record: record.evidence_id)
        invalid = sorted(
            record.evidence_id
            for record in ordered
            if record.dataset != self.DATASET_NAME
        )
        if invalid:
            raise ValueError(
                f"all records must use dataset {self.DATASET_NAME!r}; "
                f"invalid evidence: {invalid}"
            )
        identifiers = [record.evidence_id for record in ordered]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("evidence_id values must be unique")
        return tuple(claim for record in ordered for claim in record.to_claims())


def load_armbench_evidence_jsonl(path: str | Path) -> tuple[EvidenceRecord, ...]:
    """Load normalized, metadata-only ARMBench evidence from UTF-8 JSON Lines."""

    adapter = ArmbenchEvidenceAdapter()
    records: list[EvidenceRecord] = []
    with Path(path).open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"invalid JSON on line {line_number}") from error
            if not isinstance(data, Mapping):
                raise TypeError(f"line {line_number} must contain a JSON object")
            try:
                records.append(adapter.adapt(data))
            except (TypeError, ValueError) as error:
                raise type(error)(f"line {line_number}: {error}") from error
    adapter.claims_from_records(records)
    return tuple(sorted(records, key=lambda record: record.evidence_id))
