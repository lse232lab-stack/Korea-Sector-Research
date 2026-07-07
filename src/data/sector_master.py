"""Build a reusable sector master for analyst report automation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class SectorMasterResult:
    output_path: Path
    coverage_path: Path


def build_sector_master(
    *,
    universe_path: str | Path = "data/raw/benchmark/kospi200_constituents.csv",
    dart_company_path: str | Path = "data/raw/dart/top30/company_profiles.csv",
    fundamentals_path: str | Path = "data/raw/ts2000/fundamentals_long.csv",
    overrides_path: str | Path = "config/sector_overrides.csv",
    output_path: str | Path = "data/raw/sector/sector_master.csv",
    coverage_path: str | Path = "outputs/tables/sector_master_coverage.csv",
) -> SectorMasterResult:
    """Create an analyst-controlled sector master with explicit source hierarchy."""
    universe = _load_universe(universe_path)
    dart = _load_dart_company(dart_company_path)
    ts2000 = _load_ts2000_sector(fundamentals_path)
    master = universe.merge(dart, on="ticker", how="outer", suffixes=("_universe", "_dart")).merge(ts2000, on="ticker", how="outer")
    master["name"] = _coalesce_columns(master, ["name_universe", "name_dart", "corp_name", "ts2000_name"])
    master = _apply_overrides(master, overrides_path)
    master["dart_sector"] = master["dart_industry_code"].map(_dart_industry_to_sector)
    master["analyst_sector"] = master.apply(_choose_analyst_sector, axis=1)
    master["sector_source"] = master.apply(_sector_source, axis=1)
    master["valuation_family"] = master["analyst_sector"].map(_valuation_family).fillna("common_equity")
    master["confidence"] = master["sector_source"].map(
        {
            "manual_override": 1.00,
            "kospi200_constituent": 0.85,
            "opendart_industry": 0.75,
            "ts2000_sector": 0.60,
        }
    ).fillna(0.40)
    columns = [
        "ticker",
        "name",
        "analyst_sector",
        "valuation_family",
        "sector_source",
        "confidence",
        "kospi200_sector",
        "dart_sector",
        "dart_industry_code",
        "ts2000_sector",
        "override_sector",
        "override_note",
    ]
    master = master[[col for col in columns if col in master.columns]].sort_values(["analyst_sector", "ticker"])

    out = ROOT / output_path
    cov = ROOT / coverage_path
    out.parent.mkdir(parents=True, exist_ok=True)
    cov.parent.mkdir(parents=True, exist_ok=True)
    master.to_csv(out, index=False, encoding="utf-8-sig")
    coverage = (
        master.groupby(["analyst_sector", "sector_source"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["analyst_sector", "sector_source"])
    )
    coverage.to_csv(cov, index=False, encoding="utf-8-sig")
    return SectorMasterResult(output_path=out, coverage_path=cov)


def _coalesce_columns(frame: pd.DataFrame, columns: list[str]) -> pd.Series:
    result = pd.Series(pd.NA, index=frame.index, dtype="object")
    for column in columns:
        if column in frame.columns:
            result = result.combine_first(frame[column])
    return result


def _load_universe(path: str | Path) -> pd.DataFrame:
    full = ROOT / path
    if not full.exists():
        return pd.DataFrame(columns=["ticker", "name", "kospi200_sector"])
    frame = pd.read_csv(full, dtype={"ticker": "string"})
    frame["ticker"] = frame["ticker"].astype("string").str.zfill(6)
    frame = frame.sort_values("effective_date").groupby("ticker", as_index=False).tail(1)
    return frame[["ticker", "name", "sector"]].rename(columns={"sector": "kospi200_sector"})


def _load_dart_company(path: str | Path) -> pd.DataFrame:
    full = ROOT / path
    if not full.exists():
        return pd.DataFrame(columns=["ticker", "corp_name", "dart_industry_code"])
    frame = pd.read_csv(full, dtype={"ticker": "string", "stock_code": "string", "induty_code": "string"})
    ticker_col = "ticker" if "ticker" in frame.columns else "stock_code"
    frame["ticker"] = frame[ticker_col].astype("string").str.zfill(6)
    keep = [col for col in ["ticker", "corp_name", "stock_name", "induty_code"] if col in frame.columns]
    return frame[keep].rename(columns={"stock_name": "name", "induty_code": "dart_industry_code"})


def _load_ts2000_sector(path: str | Path) -> pd.DataFrame:
    full = ROOT / path
    if not full.exists():
        return pd.DataFrame(columns=["ticker", "ts2000_name", "ts2000_sector"])
    frame = pd.read_csv(full, dtype={"ticker": "string"})
    frame["ticker"] = frame["ticker"].astype("string").str.zfill(6)
    if "available_date" in frame.columns:
        frame = frame.sort_values("available_date").groupby("ticker", as_index=False).tail(1)
    return frame[["ticker", "name", "sector"]].rename(columns={"name": "ts2000_name", "sector": "ts2000_sector"})


def _apply_overrides(master: pd.DataFrame, overrides_path: str | Path) -> pd.DataFrame:
    full = ROOT / overrides_path
    if not full.exists():
        master["override_sector"] = pd.NA
        master["override_note"] = pd.NA
        return master
    overrides = pd.read_csv(full, dtype={"ticker": "string"})
    overrides["ticker"] = overrides["ticker"].astype("string").str.zfill(6)
    return master.merge(overrides[["ticker", "override_sector", "override_note"]], on="ticker", how="left")


def _choose_analyst_sector(row: pd.Series) -> str:
    for column in ["override_sector", "kospi200_sector", "dart_sector", "ts2000_sector"]:
        value = _normalize_sector(row.get(column))
        if value:
            return value
    return "Unclassified"


def _sector_source(row: pd.Series) -> str:
    if _normalize_sector(row.get("override_sector")):
        return "manual_override"
    if _normalize_sector(row.get("kospi200_sector")):
        return "kospi200_constituent"
    if _normalize_sector(row.get("dart_sector")):
        return "opendart_industry"
    if _normalize_sector(row.get("ts2000_sector")):
        return "ts2000_sector"
    return "fallback"


def _normalize_sector(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip() or value.lower() == "nan":
        return None
    mapping = {
        "IT": "IT Hardware & Components",
        "Constructions": "Construction & Infrastructure",
        "Consumer Discretionary": "Consumer & Retail",
        "Consumer Staples": "Consumer & Retail",
        "Health Care": "Consumer & Healthcare",
        "Communication Services": "Gaming & Internet",
        "Heavy Industries": "Industrials",
        "Steels & Materials": "Packaging & Materials",
    }
    return mapping.get(value.strip(), value.strip())


def _dart_industry_to_sector(code: object) -> str | None:
    if pd.isna(code):
        return None
    text = str(code).strip()
    if not text:
        return None
    prefix2 = text[:2]
    if prefix2 in {"64", "65", "66"}:
        return "Financials"
    if prefix2 in {"41", "42"}:
        return "Construction & Infrastructure"
    if prefix2 in {"19", "20", "21", "22"}:
        return "Energy & Chemicals"
    if prefix2 == "26":
        return "IT Hardware & Components"
    if prefix2 in {"28", "29", "30", "31", "33"}:
        return "Industrials"
    if prefix2 in {"46", "47", "55", "56"}:
        return "Consumer & Retail"
    if prefix2 in {"49", "50", "51", "52"}:
        return "Logistics"
    if prefix2 in {"58", "59", "60", "61", "62", "63"}:
        return "Gaming & Internet"
    return None


def _valuation_family(sector: str) -> str:
    mapping = {
        "Financials": "pbr_roe_capital_return",
        "Energy & Chemicals": "ev_ebitda_spread_cycle",
        "Construction & Infrastructure": "pbr_backlog_margin",
        "IT Hardware & Components": "forward_per_margin_cycle",
        "Semiconductors": "cycle_normalized_per",
        "Gaming & Internet": "per_pipeline_psr",
        "Holdings & Investment": "nav_discount",
        "Consumer & Retail": "per_pbr_margin",
        "Consumer & Healthcare": "per_growth_pipeline",
        "Industrials": "ev_ebitda_order_cycle",
        "Packaging & Materials": "per_pbr_spread",
        "Logistics": "ev_ebitda_volume_yield",
    }
    return mapping.get(sector, "common_equity")
