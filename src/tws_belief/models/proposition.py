from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, order=True, slots=True)
class PropositionKey:
    """Stable identity for a proposition about an entity."""

    entity_id: str
    predicate: str

    def __post_init__(self) -> None:
        if not self.entity_id.strip():
            raise ValueError("entity_id must be non-empty")
        if not self.predicate.strip():
            raise ValueError("predicate must be non-empty")

    def __str__(self) -> str:
        return f"{self.entity_id}.{self.predicate}"
