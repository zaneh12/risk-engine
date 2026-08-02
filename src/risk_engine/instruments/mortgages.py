"""Mortgage pool instrument definitions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class MortgagePool:
    """A simplified fixed-rate mortgage pool for scenario analysis."""

    upb: float
    wac: float
    remaining_term_months: int
    seasoning_months: int = 0
    servicing_fee_bps: float = 25.0

