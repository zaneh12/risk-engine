"""SEC-based bond reference discovery.

This is a practical first pass at real bond reference data without hardcoding
securities. It looks up a company in SEC data, finds recent debt-offering
filings, and extracts note terms from the filing text.
"""

from __future__ import annotations

import json
import gzip
import re
import os
import zlib
from dataclasses import dataclass
from datetime import date, datetime
from functools import lru_cache
from urllib.request import Request, urlopen

from .models import BondReference

SEC_BASE = "https://www.sec.gov"
SEC_DATA_BASE = "https://data.sec.gov"
DEFAULT_USER_AGENT = os.getenv(
    "SEC_USER_AGENT",
    "risk-engine/0.1 (contact: set SEC_USER_AGENT)",
)

FILING_FORMS = {"8-K", "424B2", "424B5", "S-3", "S-3ASR", "424B3"}
MONTH_PATTERN = (
    r"(?:January|February|March|April|May|June|July|August|September|"
    r"October|November|December)"
)
DEBT_EXACT_DATE_PATTERN = re.compile(
    rf"(?P<coupon>\d+(?:\.\d+)?)%\s+(?P<title>.+?)\s+due\s+(?:on\s+)?"
    rf"(?P<month>{MONTH_PATTERN})\s+(?P<day>\d{{1,2}}),\s+(?P<year>20\d{{2}})",
    re.IGNORECASE | re.DOTALL,
)
DEBT_YEAR_ONLY_PATTERN = re.compile(
    r"(?P<coupon>\d+(?:\.\d+)?)%\s+(?P<title>.+?)\s+due\s+(?P<year>20\d{2})",
    re.IGNORECASE | re.DOTALL,
)


def _request_json(url: str, user_agent: str) -> dict:
    request = Request(url, headers={"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"})
    with urlopen(request) as response:
        body = response.read()
        encoding = response.headers.get("Content-Encoding", "").lower()
        if encoding == "gzip":
            body = gzip.decompress(body)
        elif encoding == "deflate":
            body = zlib.decompress(body)
        return json.loads(body.decode("utf-8"))


def _request_text(url: str, user_agent: str) -> str:
    request = Request(url, headers={"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"})
    with urlopen(request) as response:
        body = response.read()
        encoding = response.headers.get("Content-Encoding", "").lower()
        if encoding == "gzip":
            body = gzip.decompress(body)
        elif encoding == "deflate":
            body = zlib.decompress(body)
        return body.decode("utf-8", errors="replace")


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _parse_maturity_date(match: re.Match[str]) -> date | None:
    month = match.groupdict().get("month")
    day = match.groupdict().get("day")
    year = match.groupdict().get("year")
    if not (month and day and year):
        return None
    return datetime.strptime(f"{month} {day}, {year}", "%B %d, %Y").date()


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
        refs: list[BondReference] = []

        for pattern in (DEBT_EXACT_DATE_PATTERN, DEBT_YEAR_ONLY_PATTERN):
            for match in pattern.finditer(text):
                coupon = float(match.group("coupon"))
                description = match.group("title").strip()
                maturity_date = _parse_maturity_date(match)
                if maturity_date is not None:
                    maturity_years = (maturity_date - filing_date).days / 365.25
                    if maturity_years <= 0:
                        continue
                else:
                    maturity_year = int(match.group("year"))
                    # SEC filing text usually gives only the maturity year, so we
                    # estimate a midpoint maturity rather than collapsing same-year
                    # notes to zero years.
                    maturity_years = max(float(maturity_year - filing_date.year) + 0.5, 0.5)

                refs.append(
                    BondReference(
                        issuer=issuer,
                        coupon_rate=coupon,
                        maturity_years=maturity_years,
                        maturity_date=maturity_date,
                        payment_frequency=2,
                        face_value=100.0,
                        description=description,
                        source="SEC EDGAR",
                        source_url=source_url,
                        as_of=filing_date,
                    )
                )

        return refs
