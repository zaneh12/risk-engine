"""Bond instrument definitions."""

from dataclasses import dataclass


@dataclass
class Bond:
    """Plain fixed-rate bond."""

    issuer: str = ""
    face_value: float = 100.0
    coupon_rate: float = 0.0
    maturity_years: float = 0.0
    payment_frequency: int = 2
