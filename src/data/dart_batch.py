"""Batch OpenDART collection for quant-ranked companies."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.data.dart_client import DARTAPIError, DARTClient, DARTConfig


ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class DARTBatchResult:
    output_dir: Path
    company_profiles_path: Path
    filings_path: Path
    single_accounts_path: Path
    fetch_summary_path: Path


def fetch_top30_dart_data(
    *,
    score_path: str | Path = "data/features/institutional_core_satellite_scores.csv",
    output_dir: str | Path = "data/raw/dart/top30",
    env_file: str | Path = ".env",
    top_n: int = 30,
    end_date: str = "20260707",
) -> DARTBatchResult:
    """Fetch company profiles, filings, and financial statement lines for latest Top-N."""
    out = ROOT / output_dir
    out.mkdir(parents=True, exist_ok=True)
    client = DARTClient(DARTConfig.from_env(ROOT / env_file))
    top = _latest_top_names(score_path, top_n)

    corp_codes = pd.DataFrame(client.corp_codes())
    corp_codes["stock_code"] = corp_codes["stock_code"].astype("string").str.zfill(6)
    matched = top.merge(corp_codes, left_on="ticker", right_on="stock_code", how="left")

    company_rows: list[dict] = []
    filing_rows: list[dict] = []
    account_rows: list[dict] = []
    summary_rows: list[dict] = []
    for _, row in matched.iterrows():
        ticker = row["ticker"]
        corp_code = row.get("corp_code", "")
        summary = {
            "rank": row["rank"],
            "ticker": ticker,
            "name": row["name"],
            "corp_code": corp_code,
            "company_ok": False,
            "filings_count": 0,
            "accounts_count": 0,
            "error": "",
        }
        if not isinstance(corp_code, str) or not corp_code:
            summary["error"] = "corp_code_not_found"
            summary_rows.append(summary)
            continue

        try:
            company = client.company(corp_code)
            company.update({"ticker": ticker, "rank": row["rank"]})
            company_rows.append(company)
            summary["company_ok"] = True
        except DARTAPIError as exc:
            summary["error"] = _append_error(summary["error"], f"company:{exc}")

        try:
            filings = _fetch_periodic_filings(client, corp_code, end_date)
            for filing in filings:
                filing.update({"ticker": ticker, "rank": row["rank"], "corp_code": corp_code})
                filing_rows.append(filing)
            summary["filings_count"] = len(filings)
        except DARTAPIError as exc:
            summary["error"] = _append_error(summary["error"], f"filings:{exc}")

        for year, report_code, report_name in [
            ("2025", "11011", "2025 business report"),
            ("2026", "11013", "2026 1Q report"),
            ("2025", "11014", "2025 3Q report"),
            ("2025", "11012", "2025 half-year report"),
        ]:
            try:
                accounts = client.single_accounts(corp_code, year, report_code)
            except DARTAPIError as exc:
                accounts = [{"fetch_error": str(exc)}]
            for account in accounts:
                account.update(
                    {
                        "ticker": ticker,
                        "rank": row["rank"],
                        "corp_code": corp_code,
                        "requested_report_name": report_name,
                        "requested_bsns_year": year,
                        "requested_reprt_code": report_code,
                    }
                )
                account_rows.append(account)
        summary["accounts_count"] = sum(1 for account in account_rows if account.get("ticker") == ticker)
        summary_rows.append(summary)

    company_profiles_path = out / "company_profiles.csv"
    filings_path = out / "filings.csv"
    single_accounts_path = out / "single_accounts.csv"
    fetch_summary_path = out / "fetch_summary.csv"
    pd.DataFrame(company_rows).to_csv(company_profiles_path, index=False, encoding="utf-8-sig")
    pd.DataFrame(filing_rows).to_csv(filings_path, index=False, encoding="utf-8-sig")
    pd.DataFrame(account_rows).to_csv(single_accounts_path, index=False, encoding="utf-8-sig")
    pd.DataFrame(summary_rows).to_csv(fetch_summary_path, index=False, encoding="utf-8-sig")
    return DARTBatchResult(
        output_dir=out,
        company_profiles_path=company_profiles_path,
        filings_path=filings_path,
        single_accounts_path=single_accounts_path,
        fetch_summary_path=fetch_summary_path,
    )


def _latest_top_names(score_path: str | Path, top_n: int) -> pd.DataFrame:
    scores = pd.read_csv(ROOT / score_path, dtype={"ticker": "string"}, parse_dates=["signal_date"])
    scores["ticker"] = scores["ticker"].astype("string").str.zfill(6)
    latest = scores["signal_date"].max()
    top = scores[scores["signal_date"].eq(latest)].sort_values("composite_score", ascending=False).head(top_n).copy()
    top["rank"] = range(1, len(top) + 1)
    return top[["rank", "ticker", "name", "composite_score", "ml_score"]]


def _fetch_periodic_filings(client: DARTClient, corp_code: str, end_date: str) -> list[dict]:
    filings: list[dict] = []
    for detail_type in ["A001", "A002", "A003"]:
        filings.extend(client.filings(corp_code, "20240101", end_date, pblntf_detail_ty=detail_type))
    return sorted({row["rcept_no"]: row for row in filings}.values(), key=lambda row: row.get("rcept_dt", ""))


def _append_error(current: str, new: str) -> str:
    return new if not current else f"{current} | {new}"
