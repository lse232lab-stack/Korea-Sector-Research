"""Extract guidance table candidates from locally collected IR PDFs."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
GUIDANCE_KEYWORDS = ["guidance", "가이던스", "전망", "목표", "매출", "영업이익", "EBITDA", "수주", "CAPEX", "투자"]


@dataclass(frozen=True)
class IRGuidanceResult:
    guidance_table_path: Path
    coverage_path: Path


def extract_ir_guidance_tables(
    *,
    ir_dir: str | Path = "data/raw/ir",
    output_dir: str | Path = "data/raw/ir",
) -> IRGuidanceResult:
    """Scan local IR PDFs and extract guidance table/text candidates."""
    import pdfplumber

    source = ROOT / ir_dir
    out = ROOT / output_dir
    out.mkdir(parents=True, exist_ok=True)
    table_rows: list[dict] = []
    coverage_rows: list[dict] = []
    pdfs = sorted(source.glob("**/*.pdf")) if source.exists() else []
    for pdf_path in pdfs:
        ticker = _ticker_from_path(pdf_path)
        pages = 0
        matched_pages = 0
        table_count = 0
        with pdfplumber.open(pdf_path) as pdf:
            pages = len(pdf.pages)
            for page_number, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                page_tables = page.extract_tables() or []
                page_has_keyword = _has_guidance_keyword(text)
                if page_has_keyword:
                    matched_pages += 1
                for table_index, table in enumerate(page_tables):
                    flattened = _flatten_table(table)
                    if not _has_guidance_keyword(flattened) and not page_has_keyword:
                        continue
                    table_count += 1
                    table_rows.append(
                        {
                            "ticker": ticker,
                            "source_file": str(pdf_path.relative_to(ROOT)),
                            "page": page_number,
                            "table_index": table_index,
                            "matched_keywords": ",".join(_matched_keywords(f"{text} {flattened}")),
                            "row_count": len(table),
                            "preview": flattened[:700],
                        }
                    )
        coverage_rows.append(
            {
                "ticker": ticker,
                "source_file": str(pdf_path.relative_to(ROOT)),
                "pages": pages,
                "matched_pages": matched_pages,
                "guidance_tables": table_count,
            }
        )
    if not coverage_rows:
        coverage_rows.append(
            {
                "ticker": "",
                "source_file": "",
                "pages": 0,
                "matched_pages": 0,
                "guidance_tables": 0,
                "note": "No local IR PDF files found under data/raw/ir.",
            }
        )
    guidance_table_path = out / "ir_guidance_tables.csv"
    coverage_path = out / "ir_guidance_coverage.csv"
    pd.DataFrame(table_rows).to_csv(guidance_table_path, index=False, encoding="utf-8-sig")
    pd.DataFrame(coverage_rows).to_csv(coverage_path, index=False, encoding="utf-8-sig")
    return IRGuidanceResult(guidance_table_path=guidance_table_path, coverage_path=coverage_path)


def _ticker_from_path(path: Path) -> str:
    match = re.search(r"(\d{6})", path.name)
    return match.group(1) if match else ""


def _flatten_table(table: list[list[object]]) -> str:
    return re.sub(r"\s+", " ", " ".join("" if cell is None else str(cell) for row in table for cell in row)).strip()


def _has_guidance_keyword(text: str) -> bool:
    return bool(_matched_keywords(text))


def _matched_keywords(text: str) -> list[str]:
    return [keyword for keyword in GUIDANCE_KEYWORDS if re.search(re.escape(keyword), text, flags=re.IGNORECASE)]
