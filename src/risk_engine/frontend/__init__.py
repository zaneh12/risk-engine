"""Frontend layer for GUI or dashboards."""

from .gui import launch
from .mbs_dashboard import render_mbs_dashboard_html, render_mbs_preview_svg, write_mbs_dashboard_assets
from .plotting import plot_curve

__all__ = [
    "launch",
    "plot_curve",
    "render_mbs_dashboard_html",
    "render_mbs_preview_svg",
    "write_mbs_dashboard_assets",
]
