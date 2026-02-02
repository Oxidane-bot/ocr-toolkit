"""
Lightweight profiling utilities.

Used to implement the `--profile` CLI flag with minimal overhead and without
adding external dependencies.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from time import perf_counter


@dataclass
class _ProfileStat:
    total_s: float = 0.0
    count: int = 0

    @property
    def avg_s(self) -> float:
        return (self.total_s / self.count) if self.count else 0.0


@dataclass
class Profiler:
    """
    Simple accumulator-based profiler.

    Records total time and counts for named sections.
    """

    _stats: dict[str, _ProfileStat] = field(default_factory=dict)

    @contextmanager
    def track(self, name: str, *, count: int = 1):
        start = perf_counter()
        try:
            yield
        finally:
            duration = perf_counter() - start
            stat = self._stats.setdefault(name, _ProfileStat())
            stat.total_s += duration
            stat.count += max(int(count), 0)

    def to_dict(self) -> dict[str, dict[str, float | int]]:
        return {
            name: {"total_s": stat.total_s, "count": stat.count, "avg_s": stat.avg_s}
            for name, stat in self._stats.items()
        }
