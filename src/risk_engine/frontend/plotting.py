"""Plotting helpers for market data and analytics.

This stays in the frontend layer because it turns domain objects into visuals.
The market-data layer should keep focusing on fetching and shaping data.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Mapping, Sequence

import matplotlib.pyplot as plt
from matplotlib import gridspec

from risk_engine.marketdata.models import YieldCurve


def _tenor_to_order(tenor: str) -> int:
    """Turn a tenor like 2Y or 6M into a sortable integer bucket."""

    tenor = tenor.strip().upper()
    if tenor.endswith("D"):
        return int(float(tenor[:-1]))
    if tenor.endswith("M"):
        return int(float(tenor[:-1]))
    if tenor.endswith("Y"):
        return int(float(tenor[:-1]) * 12)
    return 10**9


def _tenor_to_years(tenor: str) -> float:
    """Convert a tenor like 6M or 10Y into a floating-point year value."""

    tenor = tenor.strip().upper()
    if tenor.endswith("D"):
        return float(tenor[:-1]) / 365.25
    if tenor.endswith("M"):
        return float(tenor[:-1]) / 12.0
    if tenor.endswith("Y"):
        return float(tenor[:-1])
    raise ValueError(f"Unsupported tenor format: {tenor}")


def _sorted_points(curve: YieldCurve):
    """Return curve points sorted in tenor order."""

    return sorted(curve.points, key=lambda point: _tenor_to_order(point.tenor))


def _point_lookup(curve: YieldCurve) -> dict[str, float]:
    return {point.tenor: point.rate for point in curve.points}


def _format_rate(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}%"


def plot_curve(
    curve: YieldCurve,
    *,
    overlays: Mapping[str, YieldCurve] | None = None,
    reference_rows: Sequence[tuple[str, str, str, str]] | None = None,
    show: bool = True,
    save_path: str | Path | None = None,
):
    """Plot a yield curve with optional overlays and a summary panel."""

    overlays = overlays or {}
    primary_points = _sorted_points(curve)
    primary_x = [_tenor_to_years(point.tenor) for point in primary_points]
    primary_labels = [point.tenor for point in primary_points]
    primary_rates = [point.rate for point in primary_points]
    overlay_rates = [point.rate for overlay_curve in overlays.values() for point in overlay_curve.points]

    plt.style.use("seaborn-v0_8-darkgrid")
    fig = plt.figure(figsize=(13, 7), constrained_layout=True)
    gs = gridspec.GridSpec(1, 2, figure=fig, width_ratios=[3.4, 1.2])
    ax = fig.add_subplot(gs[0, 0])
    info_ax = fig.add_subplot(gs[0, 1])
    info_ax.axis("off")

    # Main curve
    ax.plot(
        primary_x,
        primary_rates,
        marker="o",
        linewidth=2.8,
        color="#1f4e79",
        label=curve.name,
        zorder=3,
    )
    ax.scatter(primary_x, primary_rates, color="#1f4e79", s=45, zorder=4)

    # Overlay points, if any, stay visually subordinate to the main curve.
    overlay_palette = ["#8a8a8a", "#b45f06", "#6a329f", "#2f7d32"]
    for idx, (label, overlay_curve) in enumerate(overlays.items()):
        overlay_points = _sorted_points(overlay_curve)
        if not overlay_points:
            continue
        overlay_x = [_tenor_to_years(point.tenor) for point in overlay_points]
        overlay_y = [point.rate for point in overlay_points]
        ax.scatter(
            overlay_x,
            overlay_y,
            s=32,
            alpha=0.85,
            color=overlay_palette[idx % len(overlay_palette)],
            label=label,
            zorder=2,
        )

    all_rates = primary_rates + overlay_rates
    if all_rates:
        y_min = min(all_rates)
        y_max = max(all_rates)
        y_pad = max((y_max - y_min) * 0.15, 0.15)
        ax.set_ylim(y_min - y_pad, y_max + y_pad)

    ax.set_title(f"{curve.name} Curve", loc="left", fontsize=16, fontweight="bold")
    ax.set_xlabel("Maturity (years)")
    ax.set_ylabel("Rate (%)")
    ax.legend(loc="upper left", frameon=True)

    # Put value labels on the main curve only to keep the chart readable.
    for x_value, tenor, rate in zip(primary_x, primary_labels, primary_rates, strict=False):
        ax.annotate(
            f"{rate:.3f}%",
            xy=(x_value, rate),
            xytext=(0, 8),
            textcoords="offset points",
            ha="center",
            fontsize=9,
            color="#1f1f1f",
        )

    if primary_x:
        step = max(1, math.ceil(len(primary_x) / 6))
        tick_positions = primary_x[::step]
        tick_labels = primary_labels[::step]
        if tick_positions[-1] != primary_x[-1]:
            tick_positions.append(primary_x[-1])
            tick_labels.append(primary_labels[-1])
        ax.set_xticks(tick_positions)
        ax.set_xticklabels(tick_labels, rotation=0)

    primary_lookup = _point_lookup(curve)
    two_year = primary_lookup.get("2Y")
    ten_year = primary_lookup.get("10Y")
    spread = None if two_year is None or ten_year is None else ten_year - two_year

    overlay_lines = []
    if overlays:
        overlay_lines.append("Overlays:")
        for label, overlay_curve in overlays.items():
            overlay_lines.append(f"- {label}: {len(overlay_curve.points)} points")

    reference_lines = []
    if reference_rows:
        reference_lines.append("")
        reference_lines.append("Bond references:")
        reference_lines.append("coupon | maturity | date | description")
        for coupon, maturity_years, maturity_date, description in reference_rows:
            reference_lines.append(f"{coupon} | {maturity_years} | {maturity_date} | {description}")

    summary_lines = [
        f"As of: {curve.as_of or 'n/a'}",
        f"Source: {curve.source}",
        f"Points: {len(curve.points)}",
        f"2Y: {_format_rate(two_year)}",
        f"10Y: {_format_rate(ten_year)}",
        f"10Y-2Y spread: {_format_rate(spread)}",
    ]
    summary_lines.extend(overlay_lines)
    summary_lines.extend(reference_lines)

    info_ax.text(
        0.0,
        1.0,
        "\n".join(summary_lines),
        va="top",
        ha="left",
        fontsize=11,
        family="monospace",
        bbox=dict(boxstyle="round,pad=0.6", facecolor="#f7f7f7", edgecolor="#d0d0d0"),
    )

    fig.suptitle("Fixed Income Curve Dashboard", x=0.02, ha="left", fontsize=18, fontweight="bold")

    if save_path is not None:
        fig.savefig(save_path, bbox_inches="tight")

    if show:
        plt.show()

    return fig, ax
