"""Generate sector-level analyst reports from the latest quant Top-N universe."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[2]
FONT_PATH = Path("/System/Library/Fonts/Supplemental/AppleGothic.ttf")
FONT_NAME = "AppleGothic"

BRAND = colors.HexColor("#143A5A")
ACCENT = colors.HexColor("#2C7FB8")
GREEN = colors.HexColor("#2D8A57")
GREY = colors.HexColor("#6B7280")
LIGHT = colors.HexColor("#EEF3F7")


@dataclass(frozen=True)
class SectorReportResult:
    output_dir: Path
    index_markdown: Path
    top30_csv: Path
    sector_summary_csv: Path
    pdf_paths: list[Path]
    markdown_paths: list[Path]


@dataclass(frozen=True)
class SectorValuationProfile:
    primary_method: str
    cross_checks: str
    key_drivers: str
    caveat: str
    table_columns: tuple[tuple[str, str], ...]


def generate_sector_reports(
    *,
    score_path: str | Path = "data/features/institutional_core_satellite_scores.csv",
    fundamentals_path: str | Path = "data/raw/ts2000/fundamentals_long.csv",
    price_path: str | Path = "data/raw/price/prices_2007_2026.csv",
    universe_path: str | Path = "data/raw/benchmark/kospi200_constituents.csv",
    sector_master_path: str | Path = "data/raw/sector/sector_master.csv",
    dart_company_path: str | Path = "data/raw/dart/top30/company_profiles.csv",
    dart_accounts_path: str | Path = "data/raw/dart/top30/single_accounts.csv",
    dart_text_kpi_path: str | Path = "data/raw/dart/top30/dart_text_kpis.csv",
    dart_bridge_path: str | Path = "data/raw/dart/top30/dart_bridge_summary.csv",
    output_dir: str | Path = "outputs/reports/sector_top30",
    top_n: int = 30,
) -> SectorReportResult:
    """Create one report per sector for the latest quant Top-N names."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    _register_fonts()

    top = build_top_sector_dataset(
        score_path=score_path,
        fundamentals_path=fundamentals_path,
        price_path=price_path,
        universe_path=universe_path,
        sector_master_path=sector_master_path,
        dart_company_path=dart_company_path,
        dart_accounts_path=dart_accounts_path,
        dart_text_kpi_path=dart_text_kpi_path,
        dart_bridge_path=dart_bridge_path,
        top_n=top_n,
    )
    sector_summary = build_sector_summary(top)

    top30_csv = output_path / "latest_top30_sector_classification.csv"
    sector_summary_csv = output_path / "sector_summary.csv"
    top.to_csv(top30_csv, index=False, encoding="utf-8-sig")
    sector_summary.to_csv(sector_summary_csv, index=False, encoding="utf-8-sig")

    pdf_paths: list[Path] = []
    markdown_paths: list[Path] = []
    for sector, sector_frame in top.groupby("sector_model", sort=False):
        slug = _slugify(sector)
        pdf_path = output_path / f"{slug}_Sector_Report.pdf"
        md_path = output_path / f"{slug}_Sector_Report.md"
        _build_sector_pdf(sector, sector_frame, sector_summary, pdf_path, top_n)
        md_path.write_text(_build_sector_markdown(sector, sector_frame, sector_summary, top_n), encoding="utf-8")
        pdf_paths.append(pdf_path)
        markdown_paths.append(md_path)

    index_markdown = output_path / "Sector_Report_Index.md"
    index_markdown.write_text(
        _build_index_markdown(top, sector_summary, pdf_paths, markdown_paths, top_n),
        encoding="utf-8",
    )
    return SectorReportResult(
        output_dir=output_path,
        index_markdown=index_markdown,
        top30_csv=top30_csv,
        sector_summary_csv=sector_summary_csv,
        pdf_paths=pdf_paths,
        markdown_paths=markdown_paths,
    )


def build_top_sector_dataset(
    *,
    score_path: str | Path,
    fundamentals_path: str | Path,
    price_path: str | Path,
    universe_path: str | Path,
    sector_master_path: str | Path,
    dart_company_path: str | Path,
    dart_accounts_path: str | Path,
    dart_text_kpi_path: str | Path,
    dart_bridge_path: str | Path,
    top_n: int,
) -> pd.DataFrame:
    scores = pd.read_csv(ROOT / score_path, dtype={"ticker": "string"}, parse_dates=["signal_date"])
    scores["ticker"] = scores["ticker"].astype("string").str.zfill(6)
    latest_signal_date = scores["signal_date"].max()
    latest_scores = (
        scores[scores["signal_date"].eq(latest_signal_date)]
        .sort_values("composite_score", ascending=False)
        .head(top_n)
        .copy()
    )
    latest_scores["rank"] = range(1, len(latest_scores) + 1)

    fundamentals = pd.read_csv(ROOT / fundamentals_path, dtype={"ticker": "string"}, parse_dates=["available_date"])
    fundamentals["ticker"] = fundamentals["ticker"].astype("string").str.zfill(6)
    fundamentals = fundamentals[fundamentals["fiscal_period"].astype(str).str.endswith("-12")].copy()
    latest_fundamentals = (
        fundamentals.sort_values("available_date")
        .groupby("ticker", as_index=False)
        .tail(1)[
            [
                "ticker",
                "name",
                "fiscal_period",
                "revenue",
                "operating_income",
                "net_income",
                "equity",
                "shares_outstanding",
                "roe",
                "operating_margin",
                "net_margin",
                "sales_growth",
                "sector",
            ]
        ]
    )

    prices = pd.read_csv(ROOT / price_path, dtype={"ticker": "string"}, parse_dates=["date"])
    prices["ticker"] = prices["ticker"].astype("string").str.zfill(6)
    latest_prices = (
        prices.sort_values("date")
        .groupby("ticker", as_index=False)
        .tail(1)[["ticker", "date", "adj_close", "volume", "trading_value"]]
    )

    top = latest_scores.merge(latest_fundamentals, on="ticker", how="left", suffixes=("", "_fundamental"))
    top["name"] = top["name"].fillna(top["name_fundamental"])
    top = top.merge(latest_prices, on="ticker", how="left")
    top = _merge_sector_master(top, sector_master_path)
    top = _merge_universe_sector(top, universe_path)
    top = _merge_dart_company(top, dart_company_path)
    top = _merge_dart_accounts(top, dart_accounts_path)
    top = _merge_dart_text_kpis(top, dart_text_kpi_path)
    top = _merge_dart_bridge_summary(top, dart_bridge_path)
    top["financial_data_basis"] = top.get("financial_data_basis", pd.Series(index=top.index, dtype="string")).fillna("TS2000 annual")
    top["eps"] = top["net_income"] / top["shares_outstanding"]
    top["bps"] = top["equity"] / top["shares_outstanding"]
    top["current_per"] = top["adj_close"] / top["eps"]
    top["current_pbr"] = top["adj_close"] / top["bps"]
    top["market_cap_proxy"] = top["adj_close"] * top["shares_outstanding"]
    top["enterprise_value_proxy"] = top["market_cap_proxy"] + top["net_debt_proxy"].fillna(0)
    top["current_psr"] = top["market_cap_proxy"] / top["revenue"]
    top["ev_ebitda_proxy"] = top["enterprise_value_proxy"] / top["ebitda_proxy"]
    top["net_debt_to_equity"] = top["net_debt_proxy"] / top["equity"]
    top["earnings_yield"] = top["net_income"] / top["market_cap_proxy"]
    top["op_income_yield"] = top["operating_income"] / top["market_cap_proxy"]
    top["book_discount_proxy"] = 1 - top["current_pbr"]
    top["sector_model"] = top.apply(_classify_sector, axis=1)
    top["sector_source"] = top.apply(_sector_source, axis=1)
    top["sector_rank"] = top.groupby("sector_model")["composite_score"].rank(ascending=False, method="first")
    return top.sort_values(["sector_model", "sector_rank", "rank"]).reset_index(drop=True)


def build_sector_summary(top: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for sector, frame in top.groupby("sector_model", sort=False):
        profile = _sector_valuation_profile(sector)
        positive_per = frame["current_per"].where(frame["current_per"] > 0)
        rows.append(
            {
                "sector_model": sector,
                "primary_method": profile.primary_method,
                "count": len(frame),
                "top_ticker": frame.sort_values("composite_score", ascending=False).iloc[0]["ticker"],
                "top_name": frame.sort_values("composite_score", ascending=False).iloc[0]["name"],
                "avg_composite_score": frame["composite_score"].mean(),
                "avg_ml_score": frame["ml_score"].mean(),
                "median_per_positive": positive_per.median(),
                "median_pbr": frame["current_pbr"].median(),
                "median_psr": frame["current_psr"].median(),
                "median_ev_ebitda_proxy": frame["ev_ebitda_proxy"].where(frame["ev_ebitda_proxy"] > 0).median(),
                "median_net_debt_to_equity": frame["net_debt_to_equity"].median(),
                "median_earnings_yield": frame["earnings_yield"].median(),
                "median_op_income_yield": frame["op_income_yield"].median(),
                "avg_roe": frame["roe"].mean(),
                "avg_op_margin": frame["operating_margin"].mean(),
                "avg_sales_growth": frame["sales_growth"].mean(),
                "total_market_cap_proxy": frame["market_cap_proxy"].sum(),
                "dart_coverage": frame["financial_data_basis"].astype(str).str.contains("OpenDART", na=False).mean(),
                "dart_text_kpi_coverage": frame["analyst_note_readiness"].notna().mean(),
                "dart_table_bridge_coverage": frame["dart_table_bridge_count"].fillna(0).gt(0).mean(),
                "avg_analyst_note_readiness": frame["analyst_note_readiness"].mean(),
                "primary_sector_source": frame["sector_source"].mode().iloc[0] if not frame["sector_source"].mode().empty else "fallback",
            }
        )
    return pd.DataFrame(rows).sort_values(["count", "avg_composite_score"], ascending=[False, False])


def _merge_sector_master(top: pd.DataFrame, sector_master_path: str | Path) -> pd.DataFrame:
    path = ROOT / sector_master_path
    if not path.exists():
        top["analyst_sector"] = pd.NA
        top["sector_master_source"] = pd.NA
        top["valuation_family"] = pd.NA
        return top
    master = pd.read_csv(path, dtype={"ticker": "string"})
    master["ticker"] = master["ticker"].astype("string").str.zfill(6)
    keep = [
        col
        for col in ["ticker", "analyst_sector", "sector_source", "valuation_family", "confidence"]
        if col in master.columns
    ]
    master = master[keep].rename(columns={"sector_source": "sector_master_source", "confidence": "sector_master_confidence"})
    return top.merge(master, on="ticker", how="left")


def _merge_universe_sector(top: pd.DataFrame, universe_path: str | Path) -> pd.DataFrame:
    path = ROOT / universe_path
    if not path.exists():
        top["universe_sector"] = pd.NA
        return top
    universe = pd.read_csv(path, dtype={"ticker": "string"})
    universe["ticker"] = universe["ticker"].astype("string").str.zfill(6)
    universe = universe.sort_values("effective_date").groupby("ticker", as_index=False).tail(1)
    universe = universe[["ticker", "sector"]].rename(columns={"sector": "universe_sector"})
    return top.merge(universe, on="ticker", how="left")


def _merge_dart_company(top: pd.DataFrame, dart_company_path: str | Path) -> pd.DataFrame:
    path = ROOT / dart_company_path
    if not path.exists():
        top["dart_industry_code"] = pd.NA
        top["dart_sector"] = pd.NA
        return top
    company = pd.read_csv(path, dtype={"ticker": "string", "stock_code": "string", "induty_code": "string"})
    ticker_col = "ticker" if "ticker" in company.columns else "stock_code"
    company["ticker"] = company[ticker_col].astype("string").str.zfill(6)
    keep = [col for col in ["ticker", "corp_code", "corp_name", "stock_name", "induty_code", "hm_url", "ir_url"] if col in company.columns]
    company = company[keep].rename(columns={"induty_code": "dart_industry_code"})
    company["dart_sector"] = company["dart_industry_code"].map(_dart_industry_to_sector)
    return top.merge(company, on="ticker", how="left", suffixes=("", "_dart"))


def _merge_dart_accounts(top: pd.DataFrame, dart_accounts_path: str | Path) -> pd.DataFrame:
    path = ROOT / dart_accounts_path
    if not path.exists():
        top["financial_data_basis"] = "TS2000 annual"
        top["ebitda_proxy"] = pd.NA
        top["net_debt_proxy"] = pd.NA
        return top
    accounts = pd.read_csv(path, dtype={"ticker": "string", "stock_code": "string", "fs_div": "string", "account_nm": "string"})
    if accounts.empty or "account_nm" not in accounts.columns:
        top["financial_data_basis"] = "TS2000 annual"
        top["ebitda_proxy"] = pd.NA
        top["net_debt_proxy"] = pd.NA
        return top
    ticker_col = "ticker" if "ticker" in accounts.columns else "stock_code"
    accounts["ticker"] = accounts[ticker_col].astype("string").str.zfill(6)
    fs_div = accounts["fs_div"] if "fs_div" in accounts.columns else pd.Series("CFS", index=accounts.index)
    accounts = accounts[fs_div.astype(str).eq("CFS")].copy()
    accounts["amount"] = accounts.get("thstrm_amount", pd.Series(dtype="object")).map(_parse_amount)
    report_code = accounts["reprt_code"] if "reprt_code" in accounts.columns else pd.Series("", index=accounts.index)
    accounts["report_priority"] = report_code.astype(str).map({"11011": 4, "11014": 3, "11012": 2, "11013": 1}).fillna(0)
    accounts = accounts.sort_values(["ticker", "bsns_year", "report_priority"])

    rows = []
    for ticker, frame in accounts.groupby("ticker"):
        report_code = frame["reprt_code"] if "reprt_code" in frame.columns else pd.Series("", index=frame.index)
        annual = frame[report_code.astype(str).eq("11011")]
        source = annual if not annual.empty else frame
        metrics = _extract_dart_financial_metrics(source)
        if metrics:
            metrics["ticker"] = ticker
            metrics["financial_data_basis"] = "OpenDART CFS annual" if not annual.empty else "OpenDART CFS interim"
            metrics["dart_report_year"] = str(source.get("bsns_year", pd.Series([""])).iloc[-1])
            rows.append(metrics)
    if not rows:
        top["financial_data_basis"] = "TS2000 annual"
        top["ebitda_proxy"] = pd.NA
        top["net_debt_proxy"] = pd.NA
        return top
    dart_metrics = pd.DataFrame(rows)
    merged = top.merge(dart_metrics, on="ticker", how="left", suffixes=("", "_dart"))
    for column in ["revenue", "operating_income", "net_income", "equity"]:
        dart_col = f"{column}_dart"
        if dart_col in merged.columns:
            merged[column] = merged[dart_col].combine_first(merged[column])
            merged = merged.drop(columns=[dart_col])
    merged["financial_data_basis"] = merged["financial_data_basis"].fillna("TS2000 annual")
    for column in ["ebitda_proxy", "net_debt_proxy", "total_assets", "total_liabilities", "interest_expense", "interest_income"]:
        if column not in merged.columns:
            merged[column] = pd.NA
    return merged


def _extract_dart_financial_metrics(frame: pd.DataFrame) -> dict[str, float]:
    account_map = {
        "revenue": ["매출액", "수익(매출액)", "영업수익", "매출"],
        "operating_income": ["영업이익", "영업손실"],
        "net_income": ["당기순이익", "당기순손실", "분기순이익", "반기순이익"],
        "equity": ["자본총계", "자본"],
        "total_assets": ["자산총계"],
        "total_liabilities": ["부채총계"],
        "current_liabilities": ["유동부채"],
        "noncurrent_liabilities": ["비유동부채"],
        "cash_and_equivalents": ["현금및현금성자산", "현금 및 현금성자산", "현금성자산"],
        "borrowings": ["차입금", "차입부채", "사채"],
        "interest_expense": ["이자비용"],
        "interest_income": ["이자수익"],
        "depreciation_amortization": ["감가상각비", "감가상각", "상각비"],
    }
    metrics: dict[str, float] = {}
    for metric, names in account_map.items():
        match = frame[frame["account_nm"].astype(str).isin(names)]
        if match.empty:
            pattern = "|".join(re.escape(name) for name in names)
            match = frame[frame["account_nm"].astype(str).str.contains(pattern, regex=True, na=False)]
        if not match.empty:
            metrics[metric] = match.dropna(subset=["amount"]).iloc[-1]["amount"]
    op = metrics.get("operating_income")
    da = metrics.get("depreciation_amortization")
    if op is not None:
        metrics["ebitda_proxy"] = op + (da if da is not None else 0)
    borrowings = metrics.get("borrowings")
    cash = metrics.get("cash_and_equivalents")
    if borrowings is not None:
        metrics["net_debt_proxy"] = borrowings - (cash if cash is not None else 0)
    elif metrics.get("total_liabilities") is not None and metrics.get("current_liabilities") is not None:
        # Fallback when detailed debt lines are unavailable in OpenDART's single-account API.
        metrics["net_debt_proxy"] = metrics["total_liabilities"] - metrics["current_liabilities"]
    return metrics


def _merge_dart_text_kpis(top: pd.DataFrame, dart_text_kpi_path: str | Path) -> pd.DataFrame:
    path = ROOT / dart_text_kpi_path
    kpi_columns = [
        "analyst_note_readiness",
        "backlog_evidence",
        "segment_sales_evidence",
        "net_debt_evidence",
        "ebitda_evidence",
        "nav_evidence",
        "guidance_evidence",
        "margin_risk_evidence",
    ]
    if not path.exists():
        for column in kpi_columns:
            top[column] = pd.NA
        return top
    kpis = pd.read_csv(path, dtype={"ticker": "string"})
    if kpis.empty:
        for column in kpi_columns:
            top[column] = pd.NA
        return top
    kpis["ticker"] = kpis["ticker"].astype("string").str.zfill(6)
    keep = ["ticker", *[col for col in kpi_columns if col in kpis.columns]]
    return top.merge(kpis[keep], on="ticker", how="left")


def _merge_dart_bridge_summary(top: pd.DataFrame, dart_bridge_path: str | Path) -> pd.DataFrame:
    path = ROOT / dart_bridge_path
    bridge_columns = [
        "dart_table_bridge_count",
        "revenue_segment_bridge_count",
        "ebitda_bridge_count",
        "backlog_bridge_count",
        "nav_bridge_count",
    ]
    if not path.exists():
        for column in bridge_columns:
            top[column] = 0
        return top
    try:
        bridges = pd.read_csv(path, dtype={"ticker": "string"})
    except pd.errors.EmptyDataError:
        for column in bridge_columns:
            top[column] = 0
        return top
    if bridges.empty or "bridge_type" not in bridges.columns:
        for column in bridge_columns:
            top[column] = 0
        return top
    bridges["ticker"] = bridges["ticker"].astype("string").str.zfill(6)
    counts = bridges.groupby(["ticker", "bridge_type"]).size().unstack(fill_value=0).reset_index()
    counts["dart_table_bridge_count"] = counts.drop(columns=["ticker"]).sum(axis=1)
    rename = {
        "revenue_segment": "revenue_segment_bridge_count",
        "ebitda_bridge": "ebitda_bridge_count",
        "backlog_bridge": "backlog_bridge_count",
        "nav_bridge": "nav_bridge_count",
    }
    counts = counts.rename(columns=rename)
    for column in bridge_columns:
        if column not in counts.columns:
            counts[column] = 0
    return top.merge(counts[["ticker", *bridge_columns]], on="ticker", how="left").fillna({column: 0 for column in bridge_columns})


def _parse_amount(value: object) -> float | None:
    if pd.isna(value):
        return None
    text = str(value).replace(",", "").strip()
    if not text or text == "-":
        return None
    if text.startswith("(") and text.endswith(")"):
        text = f"-{text[1:-1]}"
    try:
        return float(text)
    except ValueError:
        return None


def _classify_sector(row: pd.Series) -> str:
    ticker = str(row.get("ticker", ""))
    name = str(row.get("name", ""))
    analyst_sector = _normalize_sector(row.get("analyst_sector"))
    if analyst_sector:
        return analyst_sector
    universe_sector = _normalize_sector(row.get("universe_sector"))
    if universe_sector:
        return universe_sector
    dart_sector = _normalize_sector(row.get("dart_sector"))
    if dart_sector:
        return dart_sector
    raw_sector = row.get("sector")
    if isinstance(raw_sector, str) and raw_sector.strip() and raw_sector.lower() != "nan":
        return raw_sector.strip()

    explicit = {
        "000660": "Semiconductors",
        "005930": "Semiconductors",
        "000990": "Semiconductors",
        "011070": "IT Hardware & Components",
        "009150": "IT Hardware & Components",
        "066570": "Consumer Electronics",
        "047040": "Construction & Infrastructure",
        "028050": "Construction & Infrastructure",
        "138930": "Financials",
        "071050": "Financials",
        "175330": "Financials",
        "139130": "Financials",
        "316140": "Financials",
        "096770": "Energy & Chemicals",
        "004000": "Energy & Chemicals",
        "268280": "Energy & Chemicals",
        "456040": "Energy & Chemicals",
        "005380": "Auto & Mobility",
        "073240": "Auto & Mobility",
        "000120": "Logistics",
        "259960": "Gaming & Internet",
        "161890": "Consumer & Healthcare",
        "004170": "Consumer & Retail",
        "035250": "Leisure",
        "014820": "Packaging & Materials",
        "081660": "Holdings & Investment",
        "402340": "Holdings & Investment",
        "034730": "Holdings & Investment",
        "000210": "Holdings & Investment",
        "006260": "Holdings & Investment",
    }
    if ticker in explicit:
        return explicit[ticker]
    if any(keyword in name for keyword in ["금융", "은행", "증권"]):
        return "Financials"
    if any(keyword in name for keyword in ["하이닉스", "삼성전자", "반도체", "디비하이텍"]):
        return "Semiconductors"
    if any(keyword in name for keyword in ["전자", "전기", "이노텍"]):
        return "IT Hardware & Components"
    if any(keyword in name for keyword in ["건설", "이앤에이"]):
        return "Construction & Infrastructure"
    if any(keyword in name for keyword in ["화학", "OCI", "이노베이션"]):
        return "Energy & Chemicals"
    if any(keyword in name for keyword in ["지주", "홀딩스"]):
        return "Holdings & Investment"
    return "Unclassified"


def _sector_source(row: pd.Series) -> str:
    if _normalize_sector(row.get("analyst_sector")):
        source = row.get("sector_master_source")
        short = {
            "kospi200_constituent": "KOSPI200",
            "manual_override": "manual",
            "opendart_industry": "OpenDART",
            "ts2000_sector": "TS2000",
        }.get(source, source)
        return f"master/{short}" if isinstance(short, str) and short else "sector master"
    if _normalize_sector(row.get("universe_sector")):
        return "KOSPI200 constituent sector"
    if _normalize_sector(row.get("dart_sector")):
        return "OpenDART industry code"
    raw_sector = row.get("sector")
    if isinstance(raw_sector, str) and raw_sector.strip() and raw_sector.lower() != "nan":
        return "TS2000 sector"
    return "ticker/name fallback rule"


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
        "Industrials": "Industrials",
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


def _sector_valuation_profile(sector: str) -> SectorValuationProfile:
    profiles = {
        "Financials": SectorValuationProfile(
            primary_method="PBR/ROE",
            cross_checks="PER, earnings yield, shareholder-return capacity",
            key_drivers="ROE sustainability, CET1/capital buffer proxy, dividend/buyback policy, credit cost cycle",
            caveat="금융업은 매출/OPM보다 자기자본 대비 수익성과 자본정책이 valuation의 중심이다.",
            table_columns=(
                ("PBR", "current_pbr"),
                ("ROE", "roe"),
                ("PER", "current_per"),
                ("Earnings Yield", "earnings_yield"),
            ),
        ),
        "Semiconductors": SectorValuationProfile(
            primary_method="Cycle-normalized PER",
            cross_checks="PBR vs ROE, memory cycle momentum, earnings revision",
            key_drivers="AI 수요, ASP/bit growth, 재고 사이클, capex discipline, 영업레버리지",
            caveat="반도체는 trough/peak 이익 왜곡이 커서 단년 PER은 cycle-normalized 관점으로 해석한다.",
            table_columns=(
                ("PER", "current_per"),
                ("PBR", "current_pbr"),
                ("ROE", "roe"),
                ("Sales Growth", "sales_growth"),
            ),
        ),
        "IT Hardware & Components": SectorValuationProfile(
            primary_method="Forward PER",
            cross_checks="PBR/ROE, margin cycle, customer/product concentration",
            key_drivers="스마트폰/AI 서버/전장 부품 수요, 고객사 물량, 믹스 개선, 가동률",
            caveat="부품주는 고객사 수요와 제품 믹스에 따라 이익 변동성이 커서 PER과 마진 추세를 함께 본다.",
            table_columns=(
                ("PER", "current_per"),
                ("PBR", "current_pbr"),
                ("OPM", "operating_margin"),
                ("ROE", "roe"),
            ),
        ),
        "Holdings & Investment": SectorValuationProfile(
            primary_method="NAV discount",
            cross_checks="PBR, listed subsidiary value, dividend income, capital allocation",
            key_drivers="상장 자회사 지분가치, 비상장 자산 재평가, 배당/자사주, 지배구조 이벤트",
            caveat="DART 원문에서 관계기업·종속기업·투자주식 evidence를 추출하고, 아직 미상장 자산별 fair value는 수작업 검증한다.",
            table_columns=(
                ("PBR", "current_pbr"),
                ("Book Discount Proxy", "book_discount_proxy"),
                ("NAV Evidence", "nav_evidence"),
                ("PER", "current_per"),
            ),
        ),
        "Energy & Chemicals": SectorValuationProfile(
            primary_method="EV/EBITDA or replacement value",
            cross_checks="PBR, operating-income yield, spread/margin cycle",
            key_drivers="제품 스프레드, 원재료 가격, 정제/화학 cycle, 재무구조, capex",
            caveat="OpenDART 단일회사 주요계정에서 순차입금·EBITDA proxy를 계산하되, 정확한 현금/리스/비지배지분 조정은 후속 모델에서 검증한다.",
            table_columns=(
                ("EV/EBITDA", "ev_ebitda_proxy"),
                ("PBR", "current_pbr"),
                ("Net Debt/Eq", "net_debt_to_equity"),
                ("OPM", "operating_margin"),
            ),
        ),
        "Construction & Infrastructure": SectorValuationProfile(
            primary_method="PBR plus order/margin cycle",
            cross_checks="PER, OPM, backlog quality, overseas project risk",
            key_drivers="수주잔고, 원가율, 해외 프로젝트 손실 가능성, 주택/플랜트 cycle, 현금흐름",
            caveat="DART 원문에서 수주잔고·원가율·공사손실 evidence를 추출하고, 정량 수주잔고 table은 원문 표 구조화 단계에서 확장한다.",
            table_columns=(
                ("PBR", "current_pbr"),
                ("PER", "current_per"),
                ("Backlog Evidence", "backlog_evidence"),
                ("OPM", "operating_margin"),
            ),
        ),
        "Industrials": SectorValuationProfile(
            primary_method="EV/EBITDA plus order cycle",
            cross_checks="PBR/ROE, order backlog evidence, margin quality",
            key_drivers="수주, 납기, 원재료, 방산/전력/기계 cycle, 운전자본",
            caveat="OpenDART 계정으로 EV/EBITDA proxy를 계산하고 원문에서 order/guidance evidence를 추출한다.",
            table_columns=(
                ("EV/EBITDA", "ev_ebitda_proxy"),
                ("PBR", "current_pbr"),
                ("Guidance Ev.", "guidance_evidence"),
                ("OPM", "operating_margin"),
            ),
        ),
        "Auto & Mobility": SectorValuationProfile(
            primary_method="PER with volume/mix cycle",
            cross_checks="PBR/ROE, margin, FX sensitivity, shareholder return",
            key_drivers="판매대수, ASP/mix, 환율, 인센티브, 전동화 투자, 주주환원",
            caveat="완성차/부품은 경기와 환율 민감도가 커서 단순 저PER만으로 판단하지 않는다.",
            table_columns=(
                ("PER", "current_per"),
                ("PBR", "current_pbr"),
                ("ROE", "roe"),
                ("OPM", "operating_margin"),
            ),
        ),
        "Gaming & Internet": SectorValuationProfile(
            primary_method="PER plus pipeline valuation",
            cross_checks="PSR, operating margin, cash generation, new title pipeline",
            key_drivers="신작 출시, MAU/ARPU, 글로벌 흥행 지속성, 플랫폼 수수료, 인건비",
            caveat="신작 pipeline 가치는 정성 가정 비중이 커서 자동화 초안에서는 PSR/OPM을 보조지표로 쓴다.",
            table_columns=(
                ("PER", "current_per"),
                ("PSR", "current_psr"),
                ("OPM", "operating_margin"),
                ("ROE", "roe"),
            ),
        ),
    }
    default = SectorValuationProfile(
        primary_method="PER with PBR cross-check",
        cross_checks="PBR/ROE, sales growth, operating margin",
        key_drivers="실적 성장률, 마진 안정성, 브랜드/가격결정력, 재무건전성",
        caveat="섹터별 세부 KPI가 없는 경우 공통 상장사 valuation pack으로 1차 스크리닝한다.",
        table_columns=(
            ("PER", "current_per"),
            ("PBR", "current_pbr"),
            ("Sales Growth", "sales_growth"),
            ("OPM", "operating_margin"),
        ),
    )
    return profiles.get(sector, default)


def _register_fonts() -> None:
    if FONT_PATH.exists():
        pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH)))


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    font = FONT_NAME if FONT_PATH.exists() else "Helvetica"
    return {
        "Title": ParagraphStyle("Title", parent=base["Title"], fontName=font, fontSize=17, leading=22, textColor=BRAND, alignment=TA_LEFT),
        "Section": ParagraphStyle("Section", parent=base["Heading2"], fontName=font, fontSize=12, leading=15, textColor=BRAND, spaceBefore=5, spaceAfter=4),
        "Body": ParagraphStyle("Body", parent=base["BodyText"], fontName=font, fontSize=8.5, leading=12.5, textColor=colors.HexColor("#222222")),
        "Bullet": ParagraphStyle("Bullet", parent=base["BodyText"], fontName=font, fontSize=8.2, leading=11.5, leftIndent=8, firstLineIndent=-6),
        "Note": ParagraphStyle("Note", parent=base["BodyText"], fontName=font, fontSize=7.2, leading=10, textColor=GREY),
    }


def _build_sector_pdf(sector: str, frame: pd.DataFrame, sector_summary: pd.DataFrame, pdf_path: Path, top_n: int) -> None:
    styles = _styles()
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )
    summary = sector_summary[sector_summary["sector_model"].eq(sector)].iloc[0]
    profile = _sector_valuation_profile(sector)
    story = [
        _title_block(f"{sector} Sector Report", f"Quant Top{top_n} sector basket | signal date {frame['signal_date'].iloc[0].date()}"),
        Spacer(1, 8),
        _sector_kpi_table(summary, frame, profile),
        Spacer(1, 8),
        Paragraph("Valuation Framework", styles["Section"]),
        _valuation_framework_table(profile, frame),
        Spacer(1, 8),
        Paragraph("Sector Thesis", styles["Section"]),
        Paragraph(_sector_thesis(sector, frame, profile), styles["Body"]),
        Spacer(1, 8),
        Paragraph("Top Quant Picks", styles["Section"]),
        _top_picks_table(frame, profile),
        Spacer(1, 8),
        _two_column(_score_chart(frame), _fundamental_chart(frame)),
        Spacer(1, 8),
        Paragraph("Model Interpretation", styles["Section"]),
        *_sector_bullets(sector, frame, profile, styles),
        Spacer(1, 6),
        Paragraph(
            "자료: 자체 KOSPI200 코어-위성 퀀트 모델, TS2000/OpenDART 재무데이터, KIS API 가격데이터. 본 자료는 자동 생성된 리서치 초안이며 투자 권유가 아니다.",
            styles["Note"],
        ),
    ]
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)


def _title_block(title: str, subtitle: str) -> Table:
    title_style = ParagraphStyle("HeaderTitle", fontName=FONT_NAME, fontSize=16, leading=20, textColor=colors.white)
    subtitle_style = ParagraphStyle("HeaderSubtitle", fontName=FONT_NAME, fontSize=8.5, leading=11, textColor=colors.white)
    table = Table([[Paragraph(title, title_style)], [Paragraph(subtitle, subtitle_style)]], colWidths=[176 * mm], rowHeights=[12 * mm, 8 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BRAND),
                ("BOX", (0, 0), (-1, -1), 0, BRAND),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _sector_kpi_table(summary: pd.Series, frame: pd.DataFrame, profile: SectorValuationProfile) -> Table:
    data = [
        ["종목 수", f"{int(summary['count'])}", "Top Pick", f"{summary['top_name']} ({summary['top_ticker']})"],
        ["주 valuation", profile.primary_method, "보조 지표", profile.cross_checks],
        ["섹터 원천", summary["primary_sector_source"], "DART 재무 커버리지", _pct(summary["dart_coverage"])],
        ["DART 원문 커버리지", _pct(summary["dart_text_kpi_coverage"]), "Note readiness", _pct(summary["avg_analyst_note_readiness"])],
        ["DART 표 bridge", _pct(summary["dart_table_bridge_coverage"]), "EV/EBITDA", _multiple(summary["median_ev_ebitda_proxy"])],
        ["평균 퀀트점수", f"{summary['avg_composite_score']:.2f}", "평균 ML", f"{summary['avg_ml_score']:.2f}"],
        ["중위 PER", _per_multiple(summary["median_per_positive"]), "중위 PBR", _multiple(summary["median_pbr"])],
        ["순부채 지표", _multiple(summary["median_net_debt_to_equity"]), "평균 OPM", _pct(summary["avg_op_margin"])],
        ["평균 ROE", _pct(summary["avg_roe"]), "매출 성장률", _pct(summary["avg_sales_growth"])],
    ]
    table = Table(data, colWidths=[28 * mm, 50 * mm, 28 * mm, 70 * mm])
    table.setStyle(_table_style(header=False))
    return table


def _valuation_framework_table(profile: SectorValuationProfile, frame: pd.DataFrame) -> Table:
    data = [
        ["구분", "내용"],
        ["Primary", profile.primary_method],
        ["Cross-check", profile.cross_checks],
        ["핵심 드라이버", profile.key_drivers],
        ["자동화 한계", profile.caveat],
    ]
    table = Table(data, colWidths=[29 * mm, 147 * mm])
    table.setStyle(_table_style(header=True))
    return table


def _top_picks_table(frame: pd.DataFrame, profile: SectorValuationProfile) -> Table:
    dynamic_headers = [label for label, _ in profile.table_columns]
    data = [["Rank", "종목", "Score", "ML", *dynamic_headers]]
    for _, row in frame.sort_values("composite_score", ascending=False).head(8).iterrows():
        data.append(
            [
                f"{int(row['rank'])}",
                f"{row['name']} ({row['ticker']})",
                f"{row['composite_score']:.2f}",
                f"{row['ml_score']:.2f}",
                *[_format_metric(column, row[column]) for _, column in profile.table_columns],
            ]
        )
    table = Table(data, colWidths=[13 * mm, 48 * mm, 16 * mm, 14 * mm, 21 * mm, 21 * mm, 21 * mm, 21 * mm])
    table.setStyle(_table_style(header=True))
    return table


def _score_chart(frame: pd.DataFrame) -> Drawing:
    chart_frame = frame.sort_values("composite_score", ascending=False).head(6).copy()
    labels = [_short_name(name) for name in chart_frame["name"]]
    values = chart_frame["composite_score"].round(2).tolist()
    return _bar_chart("Composite Score", labels, values, min(0, min(values) * 0.9), max(values) * 1.2)


def _fundamental_chart(frame: pd.DataFrame) -> Drawing:
    chart_frame = frame.sort_values("roe", ascending=False).head(6).copy()
    labels = [_short_name(name) for name in chart_frame["name"]]
    values = (chart_frame["roe"] * 100).round(1).tolist()
    return _bar_chart("ROE (%)", labels, values, min(0, min(values) * 1.2), max(values) * 1.2)


def _bar_chart(title: str, labels: list[str], values: list[float], low: float, high: float) -> Drawing:
    width, height = 82 * mm, 54 * mm
    drawing = Drawing(width, height)
    drawing.add(Rect(0, 0, width, height, strokeColor=colors.HexColor("#D8DEE6"), fillColor=colors.white))
    drawing.add(Rect(0, height - 8 * mm, width, 8 * mm, strokeColor=BRAND, fillColor=BRAND))
    drawing.add(String(4 * mm, height - 5.2 * mm, title, fontName=FONT_NAME, fontSize=7.5, fillColor=colors.white))
    chart = VerticalBarChart()
    chart.x = 8 * mm
    chart.y = 10 * mm
    chart.width = 64 * mm
    chart.height = 31 * mm
    chart.data = [values]
    chart.valueAxis.valueMin = low
    chart.valueAxis.valueMax = high if high != low else high + 1
    chart.valueAxis.valueStep = (chart.valueAxis.valueMax - chart.valueAxis.valueMin) / 4
    chart.categoryAxis.categoryNames = labels
    chart.bars[0].fillColor = ACCENT
    chart.categoryAxis.labels.fontName = FONT_NAME
    chart.categoryAxis.labels.fontSize = 4.8
    chart.categoryAxis.labels.angle = 25
    chart.valueAxis.labels.fontName = FONT_NAME
    chart.valueAxis.labels.fontSize = 6
    drawing.add(chart)
    return drawing


def _two_column(left: Drawing, right: Drawing) -> Table:
    table = Table([[left, right]], colWidths=[88 * mm, 88 * mm])
    table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return table


def _sector_thesis(sector: str, frame: pd.DataFrame, profile: SectorValuationProfile) -> str:
    top_names = ", ".join(frame.sort_values("composite_score", ascending=False)["name"].head(3).tolist())
    templates = {
        "Semiconductors": "AI 메모리와 고성능 컴퓨팅 사이클이 이익 모멘텀의 중심이다.",
        "Financials": "고ROE와 주주환원 기대가 퀀트 점수 상단을 지지한다.",
        "Holdings & Investment": "자회사 가치와 순자산가치 할인 축소가 핵심 관찰 포인트다.",
        "Energy & Chemicals": "원재료/스프레드 변동성이 크지만 턴어라운드와 밸류에이션 매력이 공존한다.",
        "Construction & Infrastructure": "수주잔고, 해외 프로젝트 마진, 원가율 안정화가 섹터 판단의 핵심이다.",
    }
    base = templates.get(sector, "상위 종목의 퀀트 점수와 재무 모멘텀을 함께 점검해야 하는 섹터다.")
    return (
        f"{base} 최신 Top{len(frame)} 구성종목 중 대표 종목은 {top_names}이며, "
        f"섹터 평균 composite score는 {frame['composite_score'].mean():.2f}다. "
        f"이 섹터의 자동 valuation anchor는 {profile.primary_method}이며, {profile.cross_checks}로 검증한다."
    )


def _sector_bullets(
    sector: str,
    frame: pd.DataFrame,
    profile: SectorValuationProfile,
    styles: dict[str, ParagraphStyle],
) -> list[Paragraph]:
    leader = frame.sort_values("composite_score", ascending=False).iloc[0]
    positive_per = frame["current_per"].where(frame["current_per"] > 0).median()
    return [
        Paragraph(f"- 모델상 최상위 종목은 {leader['name']}이며 composite score {leader['composite_score']:.2f}, ML score {leader['ml_score']:.2f}다.", styles["Bullet"]),
        Paragraph(f"- 실무형 anchor는 {profile.primary_method}이며, 현재 proxy 기준 중위 PER은 {_per_multiple(positive_per)}, 중위 PBR은 {_multiple(frame['current_pbr'].median())}다.", styles["Bullet"]),
        Paragraph(f"- 핵심 드라이버는 {profile.key_drivers}이며, 자동화 초안의 한계는 '{profile.caveat}'로 명시한다.", styles["Bullet"]),
        Paragraph("- 자동화 모델은 정량 랭킹과 섹터별 valuation pack을 먼저 제시하고, 애널리스트가 DART 공시·수주·산업 이슈를 추가 검증하는 workflow를 전제한다.", styles["Bullet"]),
    ]


def _build_sector_markdown(sector: str, frame: pd.DataFrame, sector_summary: pd.DataFrame, top_n: int) -> str:
    summary = sector_summary[sector_summary["sector_model"].eq(sector)].iloc[0]
    profile = _sector_valuation_profile(sector)
    metric_headers = [label for label, _ in profile.table_columns]
    rows = []
    for _, row in frame.sort_values("composite_score", ascending=False).iterrows():
        rows.append(
            f"| {int(row['rank'])} | {row['ticker']} | {row['name']} | {row['composite_score']:.2f} | {row['ml_score']:.2f} | "
            + " | ".join(_format_metric(column, row[column]) for _, column in profile.table_columns)
            + " |"
        )
    return f"""# {sector} Sector Report

Signal date: {frame['signal_date'].iloc[0].date()}  
Universe: Latest KOSPI200 quant Top{top_n}

## Summary

- 종목 수: {int(summary['count'])}
- Top Pick: {summary['top_name']} ({summary['top_ticker']})
- 평균 composite score: {summary['avg_composite_score']:.2f}
- Primary valuation: {profile.primary_method}
- Cross-check: {profile.cross_checks}
- 핵심 드라이버: {profile.key_drivers}
- 섹터 분류 원천: {summary['primary_sector_source']}
- DART 재무 커버리지: {_pct(summary['dart_coverage'])}
- DART 원문 KPI 커버리지: {_pct(summary['dart_text_kpi_coverage'])}
- DART 표 bridge 커버리지: {_pct(summary['dart_table_bridge_coverage'])}
- 평균 analyst note readiness: {_pct(summary['avg_analyst_note_readiness'])}

## Thesis

{_sector_thesis(sector, frame, profile)}

## Constituents

| Rank | Ticker | Name | Composite | ML | {' | '.join(metric_headers)} |
|---:|---|---|---:|---:|{'|'.join(['---:' for _ in metric_headers])}|
{chr(10).join(rows)}

자료: 자체 KOSPI200 코어-위성 퀀트 모델, TS2000/OpenDART 재무데이터, KIS API 가격데이터.
"""


def _build_index_markdown(top: pd.DataFrame, sector_summary: pd.DataFrame, pdf_paths: list[Path], markdown_paths: list[Path], top_n: int) -> str:
    pdf_map = {path.stem.replace("_Sector_Report", ""): path for path in pdf_paths}
    md_map = {path.stem.replace("_Sector_Report", ""): path for path in markdown_paths}
    lines = [
        f"# Quant Top{top_n} Sector Report Index",
        "",
        f"- Signal date: {top['signal_date'].iloc[0].date()}",
        f"- Generated sectors: {len(sector_summary)}",
        f"- Top{top_n} CSV: `latest_top30_sector_classification.csv`",
        "",
        "| Sector | Method | Count | DART Fin. | DART Text | DART Table | Sector Source | Top Pick | Avg Score | PDF | Markdown |",
        "|---|---|---:|---:|---:|---:|---|---|---:|---|---|",
    ]
    for _, row in sector_summary.iterrows():
        slug = _slugify(row["sector_model"])
        pdf = pdf_map.get(slug)
        md = md_map.get(slug)
        lines.append(
            f"| {row['sector_model']} | {row['primary_method']} | {int(row['count'])} | {_pct(row['dart_coverage'])} | {_pct(row['dart_text_kpi_coverage'])} | {_pct(row['dart_table_bridge_coverage'])} | {row['primary_sector_source']} | {row['top_name']} | {row['avg_composite_score']:.2f} | `{pdf.name if pdf else ''}` | `{md.name if md else ''}` |"
        )
    return "\n".join(lines) + "\n"


def _table_style(header: bool) -> TableStyle:
    commands = [
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), 7.1),
        ("LEADING", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D8DEE6")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if header:
        commands += [("BACKGROUND", (0, 0), (-1, 0), BRAND), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white)]
    else:
        commands += [
            ("BACKGROUND", (0, 0), (0, -1), LIGHT),
            ("BACKGROUND", (2, 0), (2, -1), LIGHT),
            ("TEXTCOLOR", (0, 0), (0, -1), BRAND),
            ("TEXTCOLOR", (2, 0), (2, -1), BRAND),
        ]
    return TableStyle(commands)


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont(FONT_NAME, 7)
    canvas.setFillColor(GREY)
    canvas.drawString(14 * mm, 8 * mm, "Automated sector report model | Data: TS2000/OpenDART, KIS API, internal quant model")
    canvas.drawRightString(196 * mm, 8 * mm, f"{doc.page}")
    canvas.restoreState()


def _short_name(name: str) -> str:
    return (
        str(name)
        .replace("(주)", "")
        .replace("주식회사", "")
        .replace("에스케이", "SK")
        .replace("엘지", "LG")
        .replace("삼성", "삼성")
    )[:9]


def _format_metric(column: str, value: float) -> str:
    if column == "current_per":
        return _per_multiple(value)
    if column == "ev_ebitda_proxy":
        return _per_multiple(value)
    if column in {"current_pbr", "current_psr", "ev_ebitda_proxy", "net_debt_to_equity"}:
        return _multiple(value)
    if column in {
        "roe",
        "operating_margin",
        "sales_growth",
        "earnings_yield",
        "op_income_yield",
        "book_discount_proxy",
    }:
        return _pct(value)
    if pd.isna(value):
        return "-"
    if column.endswith("_evidence"):
        return f"{int(value)}"
    return f"{value:.2f}"


def _pct(value: float) -> str:
    if pd.isna(value):
        return "-"
    return f"{value * 100:.1f}%"


def _multiple(value: float) -> str:
    if pd.isna(value):
        return "-"
    return f"{value:.1f}x"


def _per_multiple(value: float) -> str:
    if pd.isna(value) or value <= 0:
        return "N/M"
    return f"{value:.1f}x"


def _slugify(value: str) -> str:
    return (
        value.lower()
        .replace("&", "and")
        .replace("/", "_")
        .replace(" ", "_")
        .replace("-", "_")
    )
