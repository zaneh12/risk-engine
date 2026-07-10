"""Core market-data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True, slots=True)
class CurvePoint:
    """A single point on a curve."""

    tenor: str
    rate: float
    as_of: date | None = None


@dataclass(slots=True)
class YieldCurve:
    """A named yield curve with one or more points."""

    name: str
    points: list[CurvePoint] = field(default_factory=list)
    source: str = "unknown"
    as_of: date | None = None


@dataclass(slots=True)
class MarketSnapshot:
    """A point-in-time collection of market data."""

    as_of: date
    curves: dict[str, YieldCurve] = field(default_factory=dict)
    rates: dict[str, float] = field(default_factory=dict)

    def curve(self, name: str) -> YieldCurve:
        """Return a curve by name."""
        return self.curves[name]

    def rate(self, name: str) -> float:
        """Return a rate by name."""
        return self.rates[name]
