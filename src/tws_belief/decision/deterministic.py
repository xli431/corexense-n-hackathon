from __future__ import annotations

import json

from tws_belief.models import BeliefState, PropositionKey
from tws_belief.models.claim import thaw_json

from .base import Decision


class SelectedValueDecisionPolicy:
    """Map one selected proposition value to a deterministic symbolic action."""

    def __init__(self, proposition: PropositionKey, *, action_prefix: str = "select") -> None:
        if not action_prefix.strip():
            raise ValueError("action_prefix must be non-empty")
        self.proposition = proposition
        self.action_prefix = action_prefix

    @property
    def policy_id(self) -> str:
        return f"selected-value-v0.1:{self.proposition}:{self.action_prefix}"

    def action_for_value(self, value: object) -> str:
        encoded = json.dumps(
            thaw_json(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        return f"{self.action_prefix}:{encoded}"

    def decide(self, belief_state: BeliefState) -> Decision:
        belief = belief_state.get(self.proposition)
        if belief is None:
            return Decision(
                action=f"{self.action_prefix}:<no-belief>",
                proposition=self.proposition,
                selected_claim_id=None,
            )
        return Decision(
            action=self.action_for_value(belief.value),
            proposition=self.proposition,
            selected_claim_id=belief.selected_claim.claim_id,
        )
