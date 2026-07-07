"""Extract analyst-style KPI hints from OpenDART report text."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.data.dart_client import DARTAPIError, DARTClient, DARTConfig


ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class DARTTextKPIResult:
    kpi_path: Path
    snippet_path: Path
    document_dir: Path


KEYWORDS = {
    "backlog": ["수주잔고", "계약잔액", "미청구", "공사잔액", "잔고"],
    "new_orders": ["신규수주", "수주", "계약", "프로젝트"],
    "segment_sales": ["사업부문", "부문별", "제품별", "매출 비중", "주요 제품"],
    "net_debt": ["순차입금", "차입금", "사채", "현금및현금성자산", "유동성장기부채"],
    "ebitda": ["EBITDA", "감가상각", "상각비"],
    "nav": ["관계기업", "종속기업", "지분", "공정가치", "투자주식"],
    "guidance": ["전망", "가이던스", "목표", "계획", "CAPEX", "투자계획"],
    "margin_risk": ["원가율", "마진", "손실", "충당부채", "공사손실", "환율"],
}


def build_dart_text_kpis(
    *,
    filings_path: str | Path = "data/raw/dart/top30/filings.csv",
    output_dir: str | Path = "data/raw/dart/top30",
    env_file: str | Path = ".env",
    fetch_documents: bool = False,
    max_documents: int | None = None,
) -> DARTTextKPIResult:
    """Build keyword evidence tables from latest periodic DART reports."""
    out = ROOT / output_dir
    document_dir = out / "documents"
    document_dir.mkdir(parents=True, exist_ok=True)
    filings = pd.read_csv(ROOT / filings_path, dtype={"ticker": "string", "corp_code": "string", "rcept_no": "string"})
    filings["ticker"] = filings["ticker"].astype("string").str.zfill(6)
    latest = _latest_periodic_filings(filings)

    client = DARTClient(DARTConfig.from_env(ROOT / env_file)) if fetch_documents else None
    kpi_rows: list[dict] = []
    snippet_rows: list[dict] = []
    for index, row in latest.iterrows():
        if max_documents is not None and index >= max_documents:
            break
        ticker = row["ticker"]
        rcept_no = row["rcept_no"]
        text_path = document_dir / f"{ticker}_{rcept_no}.txt"
        fetch_error = ""
        if fetch_documents and client is not None and not text_path.exists():
            try:
                text_path.write_text(client.report_document_text(rcept_no), encoding="utf-8")
            except DARTAPIError as exc:
                fetch_error = str(exc)
        text = text_path.read_text(encoding="utf-8", errors="ignore") if text_path.exists() else ""
        stats, snippets = _extract_text_stats(text)
        kpi_rows.append(
            {
                "ticker": ticker,
                "corp_code": row.get("corp_code", ""),
                "rcept_no": rcept_no,
                "report_nm": row.get("report_nm", ""),
                "rcept_dt": row.get("rcept_dt", ""),
                "document_path": str(text_path.relative_to(ROOT)) if text_path.exists() else "",
                "text_length": len(text),
                "fetch_error": fetch_error,
                **stats,
            }
        )
        for category, rows in snippets.items():
            for snippet in rows:
                snippet_rows.append(
                    {
                        "ticker": ticker,
                        "rcept_no": rcept_no,
                        "category": category,
                        "snippet": snippet,
                    }
                )
    kpi_path = out / "dart_text_kpis.csv"
    snippet_path = out / "dart_text_snippets.csv"
    pd.DataFrame(kpi_rows).to_csv(kpi_path, index=False, encoding="utf-8-sig")
    pd.DataFrame(snippet_rows).to_csv(snippet_path, index=False, encoding="utf-8-sig")
    return DARTTextKPIResult(kpi_path=kpi_path, snippet_path=snippet_path, document_dir=document_dir)


def _latest_periodic_filings(filings: pd.DataFrame) -> pd.DataFrame:
    periodic = filings[filings["report_nm"].astype(str).str.contains("사업보고서|분기보고서|반기보고서", regex=True, na=False)].copy()
    if periodic.empty:
        return periodic
    periodic = periodic.sort_values(["ticker", "rcept_dt", "rcept_no"])
    return periodic.groupby("ticker", as_index=False).tail(1).reset_index(drop=True)


def _extract_text_stats(text: str) -> tuple[dict[str, int | float], dict[str, list[str]]]:
    compact = re.sub(r"\s+", " ", text)
    stats: dict[str, int | float] = {}
    snippets: dict[str, list[str]] = {}
    for category, words in KEYWORDS.items():
        found = _keyword_snippets(compact, words)
        snippets[category] = found
        stats[f"{category}_mentions"] = sum(len(re.findall(re.escape(word), compact, flags=re.IGNORECASE)) for word in words)
        stats[f"{category}_evidence"] = len(found)
    stats["analyst_note_readiness"] = _readiness_score(stats)
    return stats, snippets


def _keyword_snippets(text: str, words: list[str], limit: int = 3) -> list[str]:
    snippets: list[str] = []
    for word in words:
        for match in re.finditer(re.escape(word), text, flags=re.IGNORECASE):
            start = max(match.start() - 100, 0)
            end = min(match.end() + 180, len(text))
            snippet = text[start:end].strip()
            if snippet and all(_similar(snippet, existing) < 0.65 for existing in snippets):
                snippets.append(snippet)
            if len(snippets) >= limit:
                return snippets
    return snippets


def _readiness_score(stats: dict[str, int | float]) -> float:
    categories = ["backlog", "segment_sales", "net_debt", "ebitda", "nav", "guidance", "margin_risk"]
    covered = sum(1 for category in categories if stats.get(f"{category}_evidence", 0) > 0)
    return round(covered / len(categories), 3)


def _similar(lhs: str, rhs: str) -> float:
    lhs_set = set(lhs.split())
    rhs_set = set(rhs.split())
    if not lhs_set or not rhs_set:
        return 0.0
    return len(lhs_set & rhs_set) / len(lhs_set | rhs_set)
