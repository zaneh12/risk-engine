"""Pricing service entry points."""

from __future__ import annotations

from risk_engine.instruments.bonds import Bond
from risk_engine.marketdata.models import YieldCurve


def _discount_factor(rate: float, years: float) -> float:
    """Convert a spot rate into a simple annual-compounded discount factor."""

    return 1.0 / ((1.0 + rate / 100.0) ** years)


def price_bond(bond: Bond, curve: YieldCurve) -> float:
    """Price a plain fixed-rate bond off a spot curve."""

    if bond.maturity_years <= 0:
        raise ValueError("Bond maturity_years must be positive.")
    if bond.payment_frequency <= 0:
        raise ValueError("Bond payment_frequency must be positive.")

    coupon_per_period = bond.face_value * (bond.coupon_rate / 100.0) / bond.payment_frequency
    periods = int(bond.maturity_years * bond.payment_frequency)
    price = 0.0

    for period in range(1, periods + 1):
        years = period / bond.payment_frequency
        spot_rate = curve.rate_for_years(years)
        cashflow = coupon_per_period
        if period == periods:
            cashflow += bond.face_value
        price += cashflow * _discount_factor(spot_rate, years)

    return price


def price_instrument(instrument, market_data):
    """Price a supported instrument using supplied market data."""

    if isinstance(instrument, Bond):
        if not isinstance(market_data, YieldCurve):
            raise TypeError("Bond pricing expects a YieldCurve market_data input.")
        return price_bond(instrument, market_data)

    raise TypeError(f"Unsupported instrument type: {type(instrument).__name__}")
