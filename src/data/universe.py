"""Manage KOSPI200 universe membership and exclusions."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd

from src.data.cleaner import standardize_ticker


KOSPI200_WIKIPEDIA_URL = "https://en.wikipedia.org/wiki/KOSPI_200"


def load_universe(path: str):
    """Load KOSPI200 constituent CSV."""
    return pd.read_csv(path, dtype={"ticker": "string"}, parse_dates=["effective_date"])


def fetch_kospi200_constituents_from_wikipedia(
    *,
    output_path: str | Path = "data/raw/benchmark/kospi200_constituents.csv",
    effective_date: str | None = None,
) -> pd.DataFrame:
    """Fetch current KOSPI200 components from Wikipedia as an MVP fallback.

    This is not a point-in-time KRX constituent history. It is suitable for
    current-universe MVP development only, and the resulting survivorship bias
    must be disclosed in research reports.
    """
    effective_date = effective_date or date.today().isoformat()
    request = Request(
        KOSPI200_WIKIPEDIA_URL,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    html = urlopen(request, timeout=30).read()
    tables = pd.read_html(html)
    components = _find_components_table(tables)

    output = pd.DataFrame(
        {
            "effective_date": effective_date,
            "ticker": components["Symbol"].map(standardize_ticker),
            "name": components["Company"].astype(str),
            "sector": components["GICS Sector"].astype(str),
            "is_preferred_share": False,
            "is_spac": False,
            "is_suspended": pd.NA,
            "is_administrative": pd.NA,
            "source": KOSPI200_WIKIPEDIA_URL,
            "source_note": (
                "Current KOSPI200 components from Wikipedia; use only as MVP "
                "fallback when point-in-time KRX constituent history is unavailable."
            ),
        }
    ).drop_duplicates("ticker")

    if len(output) != 200:
        raise ValueError(f"Expected 200 KOSPI200 constituents, found {len(output)}.")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output


def _find_components_table(tables: list[pd.DataFrame]) -> pd.DataFrame:
    for table in tables:
        columns = set(str(column) for column in table.columns)
        if {"Company", "Symbol", "GICS Sector"}.issubset(columns) and len(table) == 200:
            return table.copy()
    raise ValueError("Could not find KOSPI200 components table.")
