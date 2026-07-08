"""Parse OpenDART report HTML/XML tables into analyst bridge candidates."""

from __future__ import annotations

import re
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from xml.etree import ElementTree

import pandas as pd

from src.data.dart_client import DARTAPIError, DARTClient, DARTConfig


ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class DARTTableParseResult:
    table_inventory_path: Path
    bridge_summary_path: Path
    revenue_bridge_path: Path
    ebitda_bridge_path: Path
    backlog_bridge_path: Path
    nav_bridge_path: Path
    raw_document_dir: Path


TABLE_CATEGORIES = {
    "revenue_segment": ["매출", "사업부문", "부문", "제품", "서비스", "고객"],
    "ebitda_bridge": ["영업이익", "EBITDA", "감가상각", "상각", "이자", "법인세"],
    "backlog_bridge": ["수주", "수주잔고", "계약잔액", "미청구", "공사", "원가"],
    "nav_bridge": ["종속기업", "관계기업", "공정가치", "지분", "투자주식", "비지배"],
}


def build_dart_table_bridges(
    *,
    filings_path: str | Path = "data/raw/dart/top30/filings.csv",
    output_dir: str | Path = "data/raw/dart/top30",
    env_file: str | Path = ".env",
    fetch_raw_documents: bool = False,
    max_documents: int | None = None,
) -> DARTTableParseResult:
    """Extract bridge candidates from DART report tables."""
    out = ROOT / output_dir
    raw_dir = out / "raw_documents"
    raw_dir.mkdir(parents=True, exist_ok=True)
    filings = pd.read_csv(ROOT / filings_path, dtype={"ticker": "string", "corp_code": "string", "rcept_no": "string"})
    filings["ticker"] = filings["ticker"].astype("string").str.zfill(6)
    latest = _latest_periodic_filings(filings)
    client = DARTClient(DARTConfig.from_env(ROOT / env_file)) if fetch_raw_documents else None

    inventory_rows: list[dict] = []
    bridge_rows: list[dict] = []
    for index, filing in latest.iterrows():
        if max_documents is not None and index >= max_documents:
            break
        ticker = filing["ticker"]
        rcept_no = filing["rcept_no"]
        raw_files = _load_or_fetch_raw_files(raw_dir, ticker, rcept_no, client)
        for raw_name, html in raw_files.items():
            tables = _read_html_tables(html)
            for table_index, table in enumerate(tables):
                normalized = _normalize_table(table)
                table_text = _table_text(normalized)
                categories = _matched_categories(table_text)
                numeric_values = _numeric_values(normalized)
                row = {
                    "ticker": ticker,
                    "corp_code": filing.get("corp_code", ""),
                    "rcept_no": rcept_no,
                    "report_nm": filing.get("report_nm", ""),
                    "rcept_dt": filing.get("rcept_dt", ""),
                    "raw_file": raw_name,
                    "table_index": table_index,
                    "row_count": len(normalized),
                    "column_count": len(normalized.columns),
                    "numeric_count": len(numeric_values),
                    "numeric_abs_sum": sum(abs(value) for value in numeric_values),
                    "categories": ",".join(categories),
                    "preview": table_text[:500],
                }
                inventory_rows.append(row)
                for category in categories:
                    bridge_rows.append(
                        {
                            **row,
                            "bridge_type": category,
                            "matched_keywords": ",".join(_matched_keywords(table_text, TABLE_CATEGORIES[category])),
                            "amount_candidates": _top_amounts(numeric_values),
                        }
                    )

    inventory = pd.DataFrame(inventory_rows)
    bridges = pd.DataFrame(bridge_rows)
    table_inventory_path = out / "dart_table_inventory.csv"
    bridge_summary_path = out / "dart_bridge_summary.csv"
    revenue_bridge_path = out / "revenue_segment_bridge.csv"
    ebitda_bridge_path = out / "ebitda_bridge.csv"
    backlog_bridge_path = out / "backlog_bridge.csv"
    nav_bridge_path = out / "nav_bridge.csv"
    inventory.to_csv(table_inventory_path, index=False, encoding="utf-8-sig")
    bridges.to_csv(bridge_summary_path, index=False, encoding="utf-8-sig")
    _write_bridge(bridges, "revenue_segment", revenue_bridge_path)
    _write_bridge(bridges, "ebitda_bridge", ebitda_bridge_path)
    _write_bridge(bridges, "backlog_bridge", backlog_bridge_path)
    _write_bridge(bridges, "nav_bridge", nav_bridge_path)
    return DARTTableParseResult(
        table_inventory_path=table_inventory_path,
        bridge_summary_path=bridge_summary_path,
        revenue_bridge_path=revenue_bridge_path,
        ebitda_bridge_path=ebitda_bridge_path,
        backlog_bridge_path=backlog_bridge_path,
        nav_bridge_path=nav_bridge_path,
        raw_document_dir=raw_dir,
    )


def _load_or_fetch_raw_files(raw_dir: Path, ticker: str, rcept_no: str, client: DARTClient | None) -> dict[str, str]:
    existing = sorted(raw_dir.glob(f"{ticker}_{rcept_no}_*.xml"))
    if existing:
        return {path.name: path.read_text(encoding="utf-8", errors="ignore") for path in existing}
    if client is None:
        return {}
    try:
        files = client.report_document_files(rcept_no)
    except DARTAPIError:
        return {}
    output: dict[str, str] = {}
    for index, (name, text) in enumerate(files.items()):
        safe_name = re.sub(r"[^0-9A-Za-z_.-]+", "_", name)
        path = raw_dir / f"{ticker}_{rcept_no}_{index}_{safe_name}"
        if not path.suffix:
            path = path.with_suffix(".xml")
        path.write_text(text, encoding="utf-8")
        output[path.name] = text
    return output


def _latest_periodic_filings(filings: pd.DataFrame) -> pd.DataFrame:
    periodic = filings[filings["report_nm"].astype(str).str.contains("사업보고서|분기보고서|반기보고서", regex=True, na=False)].copy()
    if periodic.empty:
        return periodic
    periodic = periodic.sort_values(["ticker", "rcept_dt", "rcept_no"])
    return periodic.groupby("ticker", as_index=False).tail(1).reset_index(drop=True)


def _read_html_tables(html: str) -> list[pd.DataFrame]:
    if "<table" not in html.lower():
        return []
    try:
        tables = pd.read_html(StringIO(html))
    except (ValueError, ImportError):
        tables = []
    if tables:
        return tables
    return _read_dart_xml_tables(html)


def _read_dart_xml_tables(xml_text: str) -> list[pd.DataFrame]:
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        return _read_dart_table_blocks(xml_text)
    return _tables_from_root(root)


def _read_dart_table_blocks(xml_text: str) -> list[pd.DataFrame]:
    tables: list[pd.DataFrame] = []
    for match in re.finditer(r"<TABLE\b.*?</TABLE>", xml_text, flags=re.IGNORECASE | re.DOTALL):
        block = match.group(0)
        try:
            root = ElementTree.fromstring(block)
        except ElementTree.ParseError:
            continue
        tables.extend(_tables_from_root(root))
    return tables


def _tables_from_root(root: ElementTree.Element) -> list[pd.DataFrame]:
    tables: list[pd.DataFrame] = []
    for table in root.iter():
        if _tag_name(table.tag) != "TABLE":
            continue
        rows: list[list[str]] = []
        for tr in table.iter():
            if _tag_name(tr.tag) != "TR":
                continue
            cells = [
                _cell_text(cell)
                for cell in list(tr)
                if _tag_name(cell.tag) in {"TD", "TH", "TU"}
            ]
            if cells:
                rows.append(cells)
        if not rows:
            continue
        width = max(len(row) for row in rows)
        padded = [row + [""] * (width - len(row)) for row in rows]
        header = padded[0]
        body = padded[1:] if len(padded) > 1 else padded
        if len(set(header)) != len(header) or all(not value for value in header):
            header = [f"col_{index + 1}" for index in range(width)]
            body = padded
        tables.append(pd.DataFrame(body, columns=header))
    return tables


def _tag_name(tag: str) -> str:
    return str(tag).split("}", 1)[-1].upper()


def _cell_text(cell: ElementTree.Element) -> str:
    text = " ".join(part.strip() for part in cell.itertext() if part and part.strip())
    return re.sub(r"\s+", " ", text).strip()


def _normalize_table(table: pd.DataFrame) -> pd.DataFrame:
    normalized = table.copy()
    normalized.columns = [" ".join(str(part) for part in column if str(part) != "nan") if isinstance(column, tuple) else str(column) for column in normalized.columns]
    normalized = normalized.dropna(how="all").dropna(axis=1, how="all")
    return normalized.fillna("")


def _table_text(table: pd.DataFrame) -> str:
    chunks = [" ".join(map(str, table.columns))]
    for _, row in table.head(40).iterrows():
        chunks.append(" ".join(str(value) for value in row.tolist()))
    return re.sub(r"\s+", " ", " ".join(chunks)).strip()


def _matched_categories(text: str) -> list[str]:
    return [category for category, words in TABLE_CATEGORIES.items() if _matched_keywords(text, words)]


def _matched_keywords(text: str, words: list[str]) -> list[str]:
    return [word for word in words if re.search(re.escape(word), text, flags=re.IGNORECASE)]


def _numeric_values(table: pd.DataFrame) -> list[float]:
    values: list[float] = []
    for value in table.to_numpy().ravel():
        parsed = _parse_number(value)
        if parsed is not None:
            values.append(parsed)
    return values


def _parse_number(value: object) -> float | None:
    text = str(value).replace(",", "").strip()
    if not text or text in {"-", "nan"}:
        return None
    if text.startswith("(") and text.endswith(")"):
        text = f"-{text[1:-1]}"
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group())
    except ValueError:
        return None


def _top_amounts(values: list[float], limit: int = 5) -> str:
    ordered = sorted(values, key=lambda value: abs(value), reverse=True)[:limit]
    return ";".join(f"{value:.0f}" for value in ordered)


def _write_bridge(bridges: pd.DataFrame, bridge_type: str, path: Path) -> None:
    if bridges.empty or "bridge_type" not in bridges.columns:
        pd.DataFrame().to_csv(path, index=False, encoding="utf-8-sig")
        return
    frame = bridges[bridges["bridge_type"].eq(bridge_type)].copy()
    if not frame.empty:
        frame = frame.sort_values(["ticker", "numeric_count", "numeric_abs_sum"], ascending=[True, False, False])
    frame.to_csv(path, index=False, encoding="utf-8-sig")
