from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from tws_belief.models import BeliefState, Claim, ResolutionScore
from tws_belief.sources import SourceRegistry


@dataclass(frozen=True, slots=True)
class ResolutionContext:
    knowledge_time: datetime
    event_time: datetime
    sources: SourceRegistry


class ResolutionPolicy(Protocol):
    @property
    def policy_id(self) -> str: ...

    def score(self, claim: Claim, context: ResolutionContext) -> ResolutionScore: ...


class BeliefResolver(Protocol):
    def resolve(
        self,
        claims: Iterable[Claim],
        knowledge_time: datetime,
        *,
        event_time: datetime | None = None,
    ) -> BeliefState: ...
