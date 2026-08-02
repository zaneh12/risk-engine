"""Mortgage-backed securities scenario analytics."""

from __future__ import annotations

import math
from dataclasses import dataclass

from risk_engine.instruments.mortgages import MortgagePool
from risk_engine.marketdata.models import YieldCurve


@dataclass(frozen=True, slots=True)
class MortgageCashflowPeriod:
    """Projected monthly cash flows for a mortgage pool."""

    month: int
    age_months: int
    beginning_balance: float
    interest: float
    scheduled_principal: float
    prepayment_principal: float
    total_principal: float
    total_cashflow: float
    ending_balance: float
    discount_rate: float
    present_value: float


@dataclass(frozen=True, slots=True)
class MortgageScenarioResult:
    """Summary metrics and schedule for a mortgage pool scenario."""

    pool: MortgagePool
    psa: float
    market_rate: float
    discount_spread_bps: float
    refi_slope_cpr: float
    periods: list[MortgageCashflowPeriod]
    pv: float
    wal_years: float
    weighted_avg_coupon: float
    total_interest: float
    total_principal: float
    ending_balance: float


def _monthly_rate(annual_rate_pct: float) -> float:
    return annual_rate_pct / 1200.0


def _monthly_payment(balance: float, annual_rate_pct: float, term_months: int) -> float:
    if term_months <= 0:
        raise ValueError("term_months must be positive.")
    monthly = _monthly_rate(annual_rate_pct)
    if monthly == 0:
        return balance / term_months
    factor = (1.0 + monthly) ** term_months
    return balance * (monthly * factor) / (factor - 1.0)


def _standard_cpr(age_months: int) -> float:
    """Return the standard PSA CPR in percentage points."""

    ramp = 0.2 * min(max(age_months, 0), 30)
    return min(ramp, 6.0)


def _smm_from_cpr(cpr: float) -> float:
    return 1.0 - (1.0 - max(min(cpr, 99.0), 0.0) / 100.0) ** (1.0 / 12.0)


def simulate_mortgage_pool(
    pool: MortgagePool,
    curve: YieldCurve,
    *,
    psa: float = 100.0,
    market_rate: float = 5.0,
    discount_spread_bps: float = 0.0,
    refi_slope_cpr: float = 8.0,
) -> MortgageScenarioResult:
    """Project cash flows for a mortgage pool under a PSA-style scenario."""

    if pool.upb <= 0:
        raise ValueError("MortgagePool.upb must be positive.")
    if pool.wac < 0:
        raise ValueError("MortgagePool.wac must be non-negative.")
    if pool.remaining_term_months <= 0:
        raise ValueError("MortgagePool.remaining_term_months must be positive.")

    balance = pool.upb
    monthly_payment = _monthly_payment(balance, pool.wac, pool.remaining_term_months)
    total_interest = 0.0
    total_principal = 0.0
    total_pv = 0.0
    weighted_months = 0.0
    periods: list[MortgageCashflowPeriod] = []

    for month in range(1, pool.remaining_term_months + 1):
        if balance <= 1e-9:
            break

        age_months = pool.seasoning_months + month
        interest = balance * _monthly_rate(pool.wac)
        scheduled_principal = min(max(monthly_payment - interest, 0.0), balance)
        after_sched = max(balance - scheduled_principal, 0.0)

        psa_cpr = _standard_cpr(age_months) * (psa / 100.0)
        incentive = max(pool.wac - market_rate, 0.0)
        incentive_cpr = min(incentive * refi_slope_cpr, 30.0)
        effective_cpr = min(psa_cpr + incentive_cpr, 60.0)
        smm = _smm_from_cpr(effective_cpr)
        prepayment_principal = min(after_sched * smm, after_sched)
        total_principal_month = scheduled_principal + prepayment_principal
        total_cashflow = interest + total_principal_month
        ending_balance = max(balance - total_principal_month, 0.0)

        discount_years = age_months / 12.0
        discount_rate = curve.rate_for_years(discount_years) + (discount_spread_bps / 100.0)
        present_value = total_cashflow / ((1.0 + discount_rate / 100.0) ** discount_years)

        total_interest += interest
        total_principal += total_principal_month
        total_pv += present_value
        weighted_months += month * total_principal_month

        periods.append(
            MortgageCashflowPeriod(
                month=month,
                age_months=age_months,
                beginning_balance=balance,
                interest=interest,
                scheduled_principal=scheduled_principal,
                prepayment_principal=prepayment_principal,
                total_principal=total_principal_month,
                total_cashflow=total_cashflow,
                ending_balance=ending_balance,
                discount_rate=discount_rate,
                present_value=present_value,
            )
        )

        balance = ending_balance

    wal_years = 0.0 if total_principal <= 0 else (weighted_months / total_principal) / 12.0
    weighted_avg_coupon = pool.wac

    return MortgageScenarioResult(
        pool=pool,
        psa=psa,
        market_rate=market_rate,
        discount_spread_bps=discount_spread_bps,
        refi_slope_cpr=refi_slope_cpr,
        periods=periods,
        pv=total_pv,
        wal_years=wal_years,
        weighted_avg_coupon=weighted_avg_coupon,
        total_interest=total_interest,
        total_principal=total_principal,
        ending_balance=balance,
    )
