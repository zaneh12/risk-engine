"""Bond instrument definitions."""

from datetime import date
from dataclasses import dataclass


@dataclass
class Bond:
    """Plain fixed-rate bond."""

    issuer: str = ""
    face_value: float = 100.0
    coupon_rate: float = 0.0
    maturity_years: float = 0.0
    maturity_date: date | None = None
    payment_frequency: int = 2
