"""Bond reference data models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from risk_engine.instruments.bonds import Bond


@dataclass(frozen=True, slots=True)
class BondReference:
    """Reference data for a single bond issue."""

    issuer: str
    coupon_rate: float
    maturity_years: float
    payment_frequency: int = 2
    face_value: float = 100.0
    identifier: str | None = None
    description: str = ""
    source: str = "unknown"
    source_url: str | None = None
    as_of: date | None = None

    def to_bond(self) -> Bond:
        """Convert reference data into the pricer's bond model."""

        return Bond(
            issuer=self.issuer,
            face_value=self.face_value,
            coupon_rate=self.coupon_rate,
            maturity_years=self.maturity_years,
            payment_frequency=self.payment_frequency,
        )


class BondReferenceSource(Protocol):
    """Protocol for anything that can return bond reference data."""

    def lookup(self, identifier: str) -> BondReference:
        """Return a bond reference for the supplied identifier."""
        raise NotImplementedError

