"""Fetch OpenDART source data for the LS ELECTRIC analyst report."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data.dart_client import DARTClient, DARTConfig  # noqa: E402

OUT_DIR = ROOT / "data" / "raw" / "dart" / "ls_electric"
SUMMARY_PATH = OUT_DIR / "dart_summary.json"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    client = DARTClient(DARTConfig.from_env(ROOT / ".env"))

    corp_codes = pd.DataFrame(client.corp_codes())
    corp_codes.to_csv(OUT_DIR / "corp_codes.csv", index=False, encoding="utf-8-sig")
    matched = corp_codes.loc[corp_codes["stock_code"].eq("010120")]
    if matched.empty:
        raise RuntimeError("Could not find LS ELECTRIC corp_code from OpenDART corp codes.")
    corp_code = matched.iloc[0]["corp_code"]

    company = client.company(corp_code)
    _write_json(OUT_DIR / "company.json", company)

    filings = []
    for detail_type in ["A001", "A002", "A003"]:
        filings.extend(client.filings(corp_code, "20240101", "20260707", pblntf_detail_ty=detail_type))
    filings = sorted(
        {row["rcept_no"]: row for row in filings}.values(),
        key=lambda row: row.get("rcept_dt", ""),
    )
    filings_frame = pd.DataFrame(filings)
    filings_frame.to_csv(OUT_DIR / "filings.csv", index=False, encoding="utf-8-sig")

    accounts = []
    for year, report_code, report_name in [
        ("2025", "11011", "2025 사업보고서"),
        ("2026", "11013", "2026 1분기보고서"),
        ("2025", "11014", "2025 3분기보고서"),
        ("2025", "11012", "2025 반기보고서"),
    ]:
        try:
            rows = client.single_accounts(corp_code, year, report_code)
        except Exception as exc:  # noqa: BLE001 - persist fetch status for audit.
            rows = [{"bsns_year": year, "reprt_code": report_code, "fetch_error": str(exc)}]
        for row in rows:
            row["requested_report_name"] = report_name
            accounts.append(row)
    accounts_frame = pd.DataFrame(accounts)
    accounts_frame.to_csv(OUT_DIR / "single_accounts.csv", index=False, encoding="utf-8-sig")

    latest_report = _select_latest_periodic_report(filings)
    document_summary = {}
    if latest_report:
        text = client.report_document_text(latest_report["rcept_no"])
        (OUT_DIR / "latest_report_text.txt").write_text(text, encoding="utf-8")
        document_summary = _summarize_document_text(text)
        document_summary["rcept_no"] = latest_report["rcept_no"]
        document_summary["report_nm"] = latest_report["report_nm"]
        document_summary["rcept_dt"] = latest_report["rcept_dt"]
        _write_json(OUT_DIR / "latest_report_summary.json", document_summary)

    summary = {
        "corp_code": corp_code,
        "company": _company_summary(company),
        "latest_periodic_report": document_summary,
        "filing_count": len(filings),
        "account_rows": len(accounts_frame),
        "source_files": {
            "company": str(OUT_DIR / "company.json"),
            "filings": str(OUT_DIR / "filings.csv"),
            "single_accounts": str(OUT_DIR / "single_accounts.csv"),
            "latest_report_text": str(OUT_DIR / "latest_report_text.txt"),
        },
    }
    _write_json(SUMMARY_PATH, summary)
    print(SUMMARY_PATH)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _select_latest_periodic_report(filings: list[dict]) -> dict | None:
    periodic = [
        filing
        for filing in filings
        if any(keyword in filing.get("report_nm", "") for keyword in ["사업보고서", "분기보고서", "반기보고서"])
    ]
    if not periodic:
        return None
    return sorted(periodic, key=lambda row: row.get("rcept_dt", ""))[-1]


def _company_summary(company: dict) -> dict:
    fields = [
        "corp_name",
        "corp_name_eng",
        "stock_name",
        "stock_code",
        "ceo_nm",
        "corp_cls",
        "jurir_no",
        "bizr_no",
        "adres",
        "hm_url",
        "ir_url",
        "phn_no",
        "fax_no",
        "induty_code",
        "est_dt",
        "acc_mt",
    ]
    return {field: company.get(field, "") for field in fields}


def _summarize_document_text(text: str) -> dict:
    compact = re.sub(r"\s+", " ", text)
    keywords = {
        "business": ["전력", "전력기기", "자동화", "스마트", "전력인프라", "배전", "송전"],
        "orders": ["수주", "수주잔고", "계약", "매출"],
        "risk": ["위험", "리스크", "환율", "원재료", "경쟁", "규제"],
        "rd": ["연구개발", "R&D", "개발", "특허"],
        "capex": ["설비", "투자", "증설", "생산능력"],
    }
    snippets = {}
    for label, words in keywords.items():
        snippets[label] = _keyword_snippets(compact, words)
    return {
        "text_length": len(text),
        "keyword_snippets": snippets,
    }


def _keyword_snippets(text: str, words: list[str], limit: int = 4) -> list[str]:
    snippets: list[str] = []
    for word in words:
        for match in re.finditer(re.escape(word), text):
            start = max(match.start() - 90, 0)
            end = min(match.end() + 150, len(text))
            snippet = text[start:end].strip()
            if snippet and all(_similar(snippet, existing) < 0.65 for existing in snippets):
                snippets.append(snippet)
            if len(snippets) >= limit:
                return snippets
    return snippets


def _similar(lhs: str, rhs: str) -> float:
    lhs_set = set(lhs.split())
    rhs_set = set(rhs.split())
    if not lhs_set or not rhs_set:
        return 0.0
    return len(lhs_set & rhs_set) / len(lhs_set | rhs_set)


if __name__ == "__main__":
    main()
