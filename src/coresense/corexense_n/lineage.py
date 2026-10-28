"""Hash-linked JSONL receipts. Integrity is conditional on a trusted terminal hash."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

GENESIS = "0" * 64


def canonical(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


class Ledger:
    """Single-writer ledger; snapshots payloads to avoid later in-memory mutation."""

    def __init__(self) -> None:
        self._records: list[dict[str, Any]] = []

    @property
    def tip(self) -> str:
        return self._records[-1]["hash"] if self._records else GENESIS

    @property
    def records(self) -> list[dict[str, Any]]:
        return json.loads(canonical(self._records))

    def append(self, kind: str, payload: Any) -> str:
        record = {
            "revision": len(self._records),
            "previous_hash": self.tip,
            "kind": kind,
            "payload": json.loads(canonical(payload)),
        }
        record["hash"] = digest(record)
        self._records.append(record)
        return record["hash"]

    def write(self, path: Path) -> None:
        with path.open("x", encoding="utf-8") as stream:
            for record in self._records:
                stream.write(canonical(record) + "\n")


def verify(records: list[dict[str, Any]], expected_tip: str | None = None) -> str:
    previous = GENESIS
    for revision, record in enumerate(records):
        if set(record) != {"revision", "previous_hash", "kind", "payload", "hash"}:
            raise ValueError(f"invalid record schema at {revision}")
        if type(record["revision"]) is not int or record["revision"] != revision:
            raise ValueError(f"revision mismatch at {revision}")
        if record["previous_hash"] != previous:
            raise ValueError(f"broken chain at {revision}")
        body = {key: value for key, value in record.items() if key != "hash"}
        if record["hash"] != digest(body):
            raise ValueError(f"payload/hash mismatch at {revision}")
        previous = record["hash"]
    if expected_tip is not None and previous != expected_tip:
        raise ValueError("terminal hash mismatch (possible truncation or full rewrite)")
    return previous

