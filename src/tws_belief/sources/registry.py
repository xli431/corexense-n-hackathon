from __future__ import annotations

from collections.abc import Mapping


class SourceRegistry:
    """Configurable source reliability lookup with an explicit unknown default."""

    def __init__(
        self,
        reliabilities: Mapping[str, float] | None = None,
        *,
        default_reliability: float = 0.5,
    ) -> None:
        self._validate(default_reliability)
        self._default = float(default_reliability)
        self._reliabilities: dict[str, float] = {}
        for source_id, reliability in (reliabilities or {}).items():
            self.register(source_id, reliability)

    @staticmethod
    def _validate(value: float) -> None:
        if isinstance(value, bool) or not 0.0 <= value <= 1.0:
            raise ValueError("source reliability must be between 0 and 1 inclusive")

    def register(self, source_id: str, reliability: float) -> None:
        if not source_id.strip():
            raise ValueError("source_id must be non-empty")
        self._validate(reliability)
        self._reliabilities[source_id] = float(reliability)

    def reliability(self, source_id: str) -> float:
        return self._reliabilities.get(source_id, self._default)

    @property
    def default_reliability(self) -> float:
        return self._default

    def copy(self) -> SourceRegistry:
        return SourceRegistry(
            self._reliabilities,
            default_reliability=self._default,
        )

    def with_reliability(self, source_id: str, reliability: float) -> SourceRegistry:
        copied = self.copy()
        copied.register(source_id, reliability)
        return copied

    def to_dict(self) -> dict[str, float]:
        return dict(sorted(self._reliabilities.items()))
