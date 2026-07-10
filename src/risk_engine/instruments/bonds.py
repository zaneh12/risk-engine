"""Bond instrument definitions."""

from dataclasses import dataclass


@dataclass
class Bond:
    """Basic bond placeholder."""

    issuer: str = ""
    face_value: float = 0.0
    coupon_rate: float = 0.0
    maturity_years: float = 0.0

