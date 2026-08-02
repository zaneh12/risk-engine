"""Simple working entry point for local development.

This file is intentionally the scratchpad for trying market-data ideas
before they grow into reusable services in `src/risk_engine`.
"""

from __future__ import annotations

import os
import sys
from datetime import date
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


def _years_to_maturity(reference, as_of: date | None) -> float:
    """Estimate time to maturity for comparison against the Treasury curve."""

    if reference.maturity_date is not None and as_of is not None:
        return max((reference.maturity_date - as_of).days / 365.25, 0.0)
    return reference.maturity_years


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

    print("Loaded Treasury curve from FRED.")

    bond_identifier = os.getenv("BOND_IDENTIFIER")
    if bond_identifier:
        ref_source = SecBondReferenceSource()
        try:
            bond_references = ref_source.find_recent_offerings(bond_identifier)
        except LookupError as exc:
            print()
            print(f"Could not load a bond reference for {bond_identifier}: {exc}")
            return
        if not bond_references:
            print()
            print(f"No bond references found for {bond_identifier}.")
            return

        bond_reference = min(bond_references, key=ref_source._selection_key)
        bond = bond_reference.to_bond()
        representative_years = _years_to_maturity(bond_reference, curve.as_of)
        treasury_rate = curve.rate_for_years(representative_years)
        coupon_spread = bond_reference.coupon_rate - treasury_rate
        reference_rows = [
            (
                f"{reference.coupon_rate:.3f}%",
                f"{reference.maturity_years:.2f}Y",
                reference.maturity_date.isoformat() if reference.maturity_date is not None else "n/a",
                reference.description,
            )
            for reference in sorted(bond_references, key=lambda ref: ref.maturity_years)
        ]
        print()
        print(f"Loaded {len(bond_references)} bond coupon references from {bond_reference.source}")
        for idx, row in enumerate(reference_rows, start=1):
            coupon, maturity_years, maturity_date, description = row
            print(
                f"  {idx}. coupon {coupon} | {maturity_years} | {maturity_date} | {description}"
            )
        print()
        print("Representative issue")
        print(f"  Issuer: {bond_reference.issuer}")
        print(f"  Coupon: {bond_reference.coupon_rate:.3f}%")
        print(f"  Maturity years: {representative_years:.2f}")
        print(f"  Treasury spot at maturity: {treasury_rate:.3f}%")
        print(f"  Coupon minus Treasury spot: {coupon_spread:.3f}%")
    else:
        bond = Bond(issuer="Example Corp", face_value=100.0, coupon_rate=4.0, maturity_years=10, payment_frequency=2)
        reference_rows = None
        print()
        print("No BOND_IDENTIFIER set, using a sample fixed-rate bond.")
        print(f"Bond: {bond.issuer}, {bond.maturity_years}Y, {bond.coupon_rate:.2f}% coupon, FV {bond.face_value:.2f}")

    bond_price = price_instrument(bond, curve)
    bond_dv01 = dv01(bond, curve)
    print(f"Model price: {bond_price:.4f}")
    print(f"DV01: {bond_dv01:.6f}")

    assets_dir = root / "docs" / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    plot_curve(
        curve,
        reference_rows=reference_rows,
        show=True,
        save_path=assets_dir / "readme-dashboard.png",
    )


if __name__ == "__main__":
    main()
