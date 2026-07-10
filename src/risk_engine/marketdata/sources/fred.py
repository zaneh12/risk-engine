"""FRED market-data adapter.

This module keeps the external data retrieval logic in one place:
- fetch raw JSON from FRED
- convert the payload into small domain objects
- assemble a curve or snapshot for the rest of the app
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date, datetime
from urllib.parse import urlencode
from urllib.request import urlopen

from ..benchmarks import DEFAULT_TREASURY_CURVE_SERIES
from ..models import CurvePoint, MarketSnapshot, YieldCurve

FRED_API_BASE = "https://api.stlouisfed.org/fred"


def _parse_iso_date(value: str) -> date:
    """Convert FRED's YYYY-MM-DD string into a real date."""
    return datetime.strptime(value, "%Y-%m-%d").date()


@dataclass(slots=True)
class FredMarketDataSource:
    """Fetch market data from the Federal Reserve Economic Data API."""

    api_key: str | None = None

    def __post_init__(self) -> None:
        # Keep the API key optional at construction time so `main.py`
        # can load local environment variables first.
        if self.api_key is None:
            self.api_key = os.getenv("FRED_API_KEY")

    def _request_json(self, path: str, params: dict[str, str]) -> dict:
        # FRED returns JSON payloads over HTTPS; we keep this helper private
        # so the rest of the class can work with Python objects only.
        query = urlencode(params)
        url = f"{FRED_API_BASE}/{path}?{query}"
        with urlopen(url) as response:
            return json.loads(response.read().decode("utf-8"))

    def get_series_observations(
        self,
        series_id: str,
        *,
        observation_start: str | None = None,
        observation_end: str | None = None,
        limit: int | None = None,
    ) -> list[tuple[date, float | None]]:
        """Return a dated list of observations for one FRED series."""
        if not self.api_key:
            raise ValueError("FRED_API_KEY is required to fetch live FRED data.")

        # FRED uses string query parameters, so we build the request
        # explicitly instead of trying to hide the shape behind wrappers.
        params: dict[str, str] = {"series_id": series_id, "api_key": self.api_key, "file_type": "json"}
        if observation_start:
            params["observation_start"] = observation_start
        if observation_end:
            params["observation_end"] = observation_end
        if limit is not None:
            params["limit"] = str(limit)
            params["sort_order"] = "desc"

        payload = self._request_json("series/observations", params)
        observations = payload.get("observations", [])
        results: list[tuple[date, float | None]] = []
        for observation in observations:
            # FRED uses "." for missing values, which we normalize to None.
            value = observation.get("value")
            parsed_value = None if value in {None, ".", ""} else float(value)
            results.append((_parse_iso_date(observation["date"]), parsed_value))
        return results

    def treasury_curve(
        self,
        *,
        as_of: date | None = None,
        curve_name: str = "US Treasury",
        series_map: dict[str, str] | None = None,
    ) -> YieldCurve:
        """Build a Treasury curve from the configured FRED Treasury series."""
        series_map = series_map or DEFAULT_TREASURY_CURVE_SERIES
        as_of_value = as_of or date.today()

        points: list[CurvePoint] = []
        for tenor, series_id in series_map.items():
            # We only need the latest observation for the toy curve.
            observations = self.get_series_observations(
                series_id,
                observation_end=as_of_value.isoformat(),
                limit=1,
            )
            if not observations:
                continue
            obs_date, rate = observations[-1]
            if rate is None:
                continue
            points.append(CurvePoint(tenor=tenor, rate=rate, as_of=obs_date))

        # The curve object keeps the market-data result easy to pass around.
        return YieldCurve(name=curve_name, points=points, source="FRED", as_of=as_of_value)

    def snapshot(self, *, as_of: date | None = None) -> MarketSnapshot:
        """Build a small market snapshot around the Treasury curve."""
        curve = self.treasury_curve(as_of=as_of)
        snapshot_date = as_of or curve.as_of or date.today()
        return MarketSnapshot(as_of=snapshot_date, curves={curve.name: curve})
