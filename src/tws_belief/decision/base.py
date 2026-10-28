from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from tws_belief.models import BeliefState, PropositionKey


@dataclass(frozen=True, slots=True)
class Decision:
    """Minimal deterministic decision output used for replay evaluation."""

    action: str
    proposition: PropositionKey
    selected_claim_id: str | None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "action": self.action,
            "proposition": str(self.proposition),
            "selected_claim_id": self.selected_claim_id,
        }


class DecisionPolicy(Protocol):
    @property
    def policy_id(self) -> str: ...

    def decide(self, belief_state: BeliefState) -> Decision: ...
