"""SEC-based bond reference discovery.

This is a practical first pass at real bond reference data without hardcoding
securities. It looks up a company in SEC data, finds recent debt-offering
filings, and extracts note terms from the filing text.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from functools import lru_cache
from urllib.request import Request, urlopen

from .models import BondReference

SEC_BASE = "https://www.sec.gov"
SEC_DATA_BASE = "https://data.sec.gov"
DEFAULT_USER_AGENT = "risk-engine/0.1 (contact: local-development)"

FILING_FORMS = {"8-K", "424B2", "424B5", "S-3", "S-3ASR", "424B3"}
DEBT_TITLE_PATTERN = re.compile(
    r"(?P<coupon>\d+(?:\.\d+)?)%\s+(?P<title>.+?)\s+due\s+(?P<year>20\d{2})",
    re.IGNORECASE,
)


def _request_json(url: str, user_agent: str) -> dict:
    request = Request(url, headers={"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"})
    with urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def _request_text(url: str, user_agent: str) -> str:
    request = Request(url, headers={"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"})
    with urlopen(request) as response:
        return response.read().decode("utf-8", errors="replace")


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


@lru_cache(maxsize=1)
def _company_ticker_map() -> dict[str, int]:
    payload = _request_json(f"{SEC_BASE}/files/company_tickers.json", DEFAULT_USER_AGENT)
    return {
        entry["ticker"].upper(): int(entry["cik_str"])
        for entry in payload.values()
    }


@dataclass(slots=True)
class SecBondReferenceSource:
    """Find bond reference data from SEC company filings."""

    user_agent: str = DEFAULT_USER_AGENT

    def lookup(self, identifier: str) -> BondReference:
        offerings = self.find_recent_offerings(identifier)
        if not offerings:
            raise LookupError(f"No bond references found for {identifier}.")
        return offerings[0]

    def find_recent_offerings(self, identifier: str, *, max_filings: int = 12) -> list[BondReference]:
        """Return bond references from recent debt-offering filings."""

        cik = self._resolve_cik(identifier)
        submissions = _request_json(f"{SEC_DATA_BASE}/submissions/CIK{cik:010d}.json", self.user_agent)
        recent = submissions.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        accession_numbers = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])
        filing_dates = recent.get("filingDate", [])
        company_name = submissions.get("name", identifier)

        results: list[BondReference] = []
        for form, accession, primary_doc, filing_date in zip(forms, accession_numbers, primary_docs, filing_dates, strict=False):
            if form not in FILING_FORMS:
                continue
            filing_url = f"{SEC_BASE}/Archives/edgar/data/{cik}/{accession.replace('-', '')}/{primary_doc}"
            text = _request_text(filing_url, self.user_agent)
            refs = self._extract_references(
                text=text,
                issuer=company_name,
                source_url=filing_url,
                filing_date=_parse_date(filing_date),
            )
            results.extend(refs)
            if len(results) >= max_filings:
                break

        return results[:max_filings]

    def _resolve_cik(self, identifier: str) -> int:
        normalized = identifier.strip().upper()
        if normalized.isdigit():
            return int(normalized)

        ticker_map = _company_ticker_map()
        if normalized in ticker_map:
            return ticker_map[normalized]

        raise LookupError(f"Unable to resolve SEC CIK for {identifier}.")

    def _extract_references(self, *, text: str, issuer: str, source_url: str, filing_date: date) -> list[BondReference]:
        matches = list(DEBT_TITLE_PATTERN.finditer(text))
        refs: list[BondReference] = []

        for match in matches:
            coupon = float(match.group("coupon"))
            maturity_year = int(match.group("year"))
            maturity_years = max(float(maturity_year - filing_date.year), 0.0)
            description = match.group("title").strip()
            refs.append(
                BondReference(
                    issuer=issuer,
                    coupon_rate=coupon,
                    maturity_years=maturity_years,
                    payment_frequency=2,
                    face_value=100.0,
                    description=description,
                    source="SEC EDGAR",
                    source_url=source_url,
                    as_of=filing_date,
                )
            )

        return refs
