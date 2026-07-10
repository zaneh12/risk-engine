"""Treasury instrument definitions."""

from dataclasses import dataclass


@dataclass
class Treasury:
    """Basic treasury placeholder."""

    maturity_years: float = 0.0
    face_value: float = 0.0

