"""Rate definitions."""

from dataclasses import dataclass


@dataclass
class Rate:
    """Basic rate placeholder."""

    tenor: str = ""
    value: float = 0.0

