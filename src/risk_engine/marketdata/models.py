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

    def rate_for_years(self, years: float) -> float:
        """Return an interpolated curve rate for a maturity in years."""

        if not self.points:
            raise ValueError("YieldCurve has no points.")

        ordered = sorted(self.points, key=lambda point: _tenor_to_years(point.tenor))
        target = years
        first_years = _tenor_to_years(ordered[0].tenor)
        last_years = _tenor_to_years(ordered[-1].tenor)

        if target <= first_years:
            return ordered[0].rate
        if target >= last_years:
            return ordered[-1].rate

        for left, right in zip(ordered, ordered[1:], strict=False):
            left_years = _tenor_to_years(left.tenor)
            right_years = _tenor_to_years(right.tenor)
            if left_years <= target <= right_years:
                weight = (target - left_years) / (right_years - left_years)
                return left.rate + weight * (right.rate - left.rate)

        return ordered[-1].rate


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


def _tenor_to_years(tenor: str) -> float:
    """Convert a simple tenor like 6M or 10Y into years."""

    tenor = tenor.strip().upper()
    if tenor.endswith("D"):
        return float(tenor[:-1]) / 365.0
    if tenor.endswith("M"):
        return float(tenor[:-1]) / 12.0
    if tenor.endswith("Y"):
        return float(tenor[:-1])
    raise ValueError(f"Unsupported tenor format: {tenor}")
