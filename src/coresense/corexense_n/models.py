"""Bounded numeric observations; no raw images, free text, or motor commands."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

SOURCES = {"camera", "joint_state"}


@dataclass(frozen=True)
class Observation:
    source: str
    source_frame: int
    acquired_ms: int
    received_ms: int
    confidence: float
    supports_action: bool
    upstream_id: str

    def __post_init__(self) -> None:
        if self.source not in SOURCES:
            raise ValueError("unknown source")
        for number in (self.source_frame, self.acquired_ms, self.received_ms):
            if type(number) is not int or number < 0:
                raise ValueError("frame and timestamps must be nonnegative integers")
        if not math.isfinite(self.confidence) or not 0 <= self.confidence <= 1:
            raise ValueError("invalid confidence")
        if type(self.supports_action) is not bool or not self.upstream_id:
            raise ValueError("support and upstream identity are required")

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Snapshot:
    now_ms: int
    observations: tuple[Observation, ...]

    def __post_init__(self) -> None:
        if type(self.now_ms) is not int or self.now_ms < 0:
            raise ValueError("invalid clock")
        if len({o.source for o in self.observations}) != len(self.observations):
            raise ValueError("duplicate source in snapshot")


@dataclass(frozen=True)
class Proposal:
    action: str = "press_button"
    target: str = "button_A"


@dataclass(frozen=True)
class Decision:
    action: str
    reason: str


@dataclass(frozen=True)
class Verdict:
    validator: str
    status: str
    request_hash: str
    mode: str
    model: str | None = None
    response_hash: str | None = None
    latency_ms: float | None = None
    diagnostic: str | None = None
    finish_reason: str | None = None
    http_status: int | None = None
    usage: dict | None = None

