"""Simple working entry point for local development.

This file is intentionally the scratchpad for trying market-data ideas
before they grow into reusable services in `src/risk_engine`.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def load_dotenv(path: str | Path | None = None) -> None:
    """Load a local .env file into the current process."""

    env_path = Path(path) if path is not None else Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def main() -> None:
    """Run a small market-data smoke test."""

    root = Path(__file__).resolve().parent
    # Add `src/` so we can import the package while still keeping a src layout.
    sys.path.insert(0, str(root / "src"))

    load_dotenv()

    from risk_engine.instruments import Bond
    from risk_engine.marketdata import FredMarketDataSource, DEFAULT_TREASURY_CURVE_SERIES
    from risk_engine.frontend import plot_curve
    from risk_engine.services import dv01, price_instrument
    from risk_engine.reference import SecBondReferenceSource

    source = FredMarketDataSource()
    curve = source.treasury_curve(series_map=DEFAULT_TREASURY_CURVE_SERIES)

    if not curve.points:
        print("No curve points were returned. Check your FRED_API_KEY and try again.")
        return

    print(f"As of: {curve.as_of}")
    print(f"{curve.name} ({curve.source})")
    for point in curve.points:
        print(f"  {point.tenor}: {point.rate}")

    short = next((point for point in curve.points if point.tenor == "2Y"), None)
    long = next((point for point in curve.points if point.tenor == "10Y"), None)
    if short is not None and long is not None:
        spread = long.rate - short.rate
        print(f"  10Y minus 2Y spread: {spread}")

    bond_identifier = os.getenv("BOND_IDENTIFIER")
    if bond_identifier:
        ref_source = SecBondReferenceSource()
        try:
            bond_reference = ref_source.lookup(bond_identifier)
        except LookupError as exc:
            print()
            print(f"Could not load a bond reference for {bond_identifier}: {exc}")
            return
        bond = bond_reference.to_bond()
        print()
        print(f"Loaded bond reference from {bond_reference.source}")
        print(f"Issuer: {bond_reference.issuer}")
        print(f"Description: {bond_reference.description}")
        print(f"Coupon: {bond_reference.coupon_rate:.3f}%")
        print(f"Maturity years: {bond_reference.maturity_years:.2f}")
    else:
        bond = Bond(issuer="Example Corp", face_value=100.0, coupon_rate=4.0, maturity_years=10, payment_frequency=2)
        print()
        print("No BOND_IDENTIFIER set, using a sample fixed-rate bond.")
        print(f"Bond: {bond.issuer}, {bond.maturity_years}Y, {bond.coupon_rate:.2f}% coupon, FV {bond.face_value:.2f}")

    bond_price = price_instrument(bond, curve)
    bond_dv01 = dv01(bond, curve)
    print(f"Model price: {bond_price:.4f}")
    print(f"DV01: {bond_dv01:.6f}")

    plot_curve(curve, show=True)


if __name__ == "__main__":
    main()
