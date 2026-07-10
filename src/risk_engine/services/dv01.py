"""DV01 service entry points."""

from __future__ import annotations

from risk_engine.instruments.bonds import Bond
from risk_engine.marketdata.models import YieldCurve
from risk_engine.services.price import price_bond


def dv01_bond(bond: Bond, curve: YieldCurve, *, bump_bps: float = 1.0) -> float:
    """Return the bond's DV01 using a parallel curve bump."""

    if bump_bps <= 0:
        raise ValueError("bump_bps must be positive.")

    price_up = price_bond(bond, curve.bumped_parallel(bump_bps))
    price_down = price_bond(bond, curve.bumped_parallel(-bump_bps))
    return (price_down - price_up) / (2.0 * bump_bps)


def dv01(instrument, market_data):
    """Calculate DV01 for a supported instrument."""

    if isinstance(instrument, Bond):
        if not isinstance(market_data, YieldCurve):
            raise TypeError("Bond DV01 expects a YieldCurve market_data input.")
        return dv01_bond(instrument, market_data)

    raise TypeError(f"Unsupported instrument type: {type(instrument).__name__}")
