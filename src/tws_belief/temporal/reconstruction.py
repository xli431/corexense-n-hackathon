from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime

from tws_belief.models import (
    BeliefState,
    Claim,
    ClaimConflict,
    PropositionKey,
    detect_conflicts,
)
from tws_belief.resolution import BeliefResolver, DeterministicBeliefResolver


class ClaimStore:
    """In-memory immutable-claim collection for deterministic reconstruction."""

    def __init__(self, claims: Iterable[Claim] = ()) -> None:
        self._claims: dict[str, Claim] = {}
        for claim in claims:
            self.add(claim)

    def add(self, claim: Claim) -> None:
        if claim.claim_id in self._claims:
            raise ValueError(f"duplicate claim_id: {claim.claim_id}")
        self._claims[claim.claim_id] = claim

    def all_claims(self) -> tuple[Claim, ...]:
        return tuple(self._claims[key] for key in sorted(self._claims))

    def for_proposition(self, proposition: PropositionKey) -> tuple[Claim, ...]:
        return tuple(
            claim for claim in self.all_claims() if claim.proposition == proposition
        )

    def known_by(self, knowledge_time: datetime) -> tuple[Claim, ...]:
        return tuple(
            claim for claim in self.all_claims() if claim.known_by(knowledge_time)
        )

    def valid_at(self, event_time: datetime) -> tuple[Claim, ...]:
        return tuple(claim for claim in self.all_claims() if claim.valid_at(event_time))

    def competing_claims(
        self,
        proposition: PropositionKey,
        *,
        knowledge_time: datetime,
        event_time: datetime | None = None,
    ) -> tuple[Claim, ...]:
        query_event_time = event_time or knowledge_time
        return tuple(
            claim
            for claim in self.for_proposition(proposition)
            if claim.known_by(knowledge_time) and claim.valid_at(query_event_time)
        )

    def conflicts(
        self,
        *,
        knowledge_time: datetime,
        event_time: datetime | None = None,
    ) -> tuple[ClaimConflict, ...]:
        query_event_time = event_time or knowledge_time
        eligible = [
            claim
            for claim in self.known_by(knowledge_time)
            if claim.valid_at(query_event_time)
        ]
        return detect_conflicts(eligible)

    def grouped(self) -> dict[PropositionKey, tuple[Claim, ...]]:
        groups: dict[PropositionKey, list[Claim]] = defaultdict(list)
        for claim in self.all_claims():
            groups[claim.proposition].append(claim)
        return {
            proposition: tuple(groups[proposition]) for proposition in sorted(groups)
        }


class HistoricalReconstructor:
    """Reconstruct only from claims known at the requested knowledge time."""

    def __init__(
        self,
        store: ClaimStore,
        resolver: BeliefResolver | None = None,
    ) -> None:
        self.store = store
        self.resolver = resolver or DeterministicBeliefResolver()

    def reconstruct(
        self,
        knowledge_time: datetime,
        *,
        event_time: datetime | None = None,
    ) -> BeliefState:
        return self.resolver.resolve(
            self.store.all_claims(),
            knowledge_time,
            event_time=event_time,
        )
