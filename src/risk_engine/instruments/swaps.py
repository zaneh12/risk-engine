"""Interest rate swap instrument definitions."""

from dataclasses import dataclass


@dataclass
class Swap:
    """Basic interest rate swap placeholder."""

    notional: float = 0.0
    fixed_rate: float = 0.0
    maturity_years: float = 0.0

