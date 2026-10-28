from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tws_belief.models.claim import _freeze_json, thaw_json

from .interventions import InterventionSet

SCHEMA_VERSION = "tws-belief.perturbation-manifest.v0.1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _non_empty(value: object, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


@dataclass(frozen=True, slots=True)
class PerturbationManifest:
    """A versioned, deterministic counterfactual intervention manifest."""

    manifest_id: str
    dataset: str
    reference_id: str
    reference_sha256: str
    intervention_set: InterventionSet
    metadata: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in ("manifest_id", "dataset", "reference_id"):
            _non_empty(getattr(self, name), name)
        if not isinstance(self.reference_sha256, str) or not _SHA256.fullmatch(
            self.reference_sha256
        ):
            raise ValueError("reference_sha256 must be 64 lowercase hexadecimal characters")
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(
                f"schema_version must be {SCHEMA_VERSION!r}, "
                f"got {self.schema_version!r}"
            )
        if not isinstance(self.intervention_set, InterventionSet):
            raise TypeError("intervention_set must be an InterventionSet")
        if not self.intervention_set.interventions:
            raise ValueError("manifest must contain at least one intervention")
        if not isinstance(self.metadata, Mapping):
            raise TypeError("metadata must be an object")
        frozen = _freeze_json(dict(self.metadata), "metadata")
        if not isinstance(frozen, Mapping):
            raise TypeError("metadata must be an object")
        object.__setattr__(self, "metadata", frozen)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> PerturbationManifest:
        if not isinstance(data, Mapping):
            raise TypeError("perturbation manifest must be an object")
        required = {
            "schema_version",
            "manifest_id",
            "dataset",
            "reference_id",
            "reference_sha256",
            "interventions",
        }
        allowed = required | {"metadata"}
        extra = set(data) - allowed
        missing = required - set(data)
        if extra:
            raise ValueError(f"unknown manifest fields: {sorted(extra)}")
        if missing:
            raise ValueError(f"missing manifest fields: {sorted(missing)}")
        metadata = data.get("metadata", {})
        if not isinstance(metadata, Mapping):
            raise TypeError("metadata must be an object")
        return cls(
            schema_version=data["schema_version"],
            manifest_id=data["manifest_id"],
            dataset=data["dataset"],
            reference_id=data["reference_id"],
            reference_sha256=data["reference_sha256"],
            intervention_set=InterventionSet.from_dict(
                {"interventions": data["interventions"]}
            ),
            metadata=metadata,
        )

    @property
    def sha256(self) -> str:
        encoded = json.dumps(
            self.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "manifest_id": self.manifest_id,
            "dataset": self.dataset,
            "reference_id": self.reference_id,
            "reference_sha256": self.reference_sha256,
            "interventions": self.intervention_set.to_dict()["interventions"],
            "metadata": thaw_json(self.metadata),
        }

    def require_reference(
        self,
        *,
        dataset: str,
        reference_id: str,
        reference_sha256: str,
    ) -> None:
        """Fail closed when a manifest is applied to a different baseline."""

        mismatches: list[str] = []
        if dataset != self.dataset:
            mismatches.append(f"dataset={dataset!r}")
        if reference_id != self.reference_id:
            mismatches.append(f"reference_id={reference_id!r}")
        if reference_sha256 != self.reference_sha256:
            mismatches.append(f"reference_sha256={reference_sha256!r}")
        if mismatches:
            raise ValueError(
                "perturbation manifest reference mismatch: " + ", ".join(mismatches)
            )


def load_perturbation_manifest(path: str | Path) -> PerturbationManifest:
    manifest_path = Path(path)
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid JSON in perturbation manifest: {manifest_path}") from error
    return PerturbationManifest.from_dict(data)
