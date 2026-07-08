"""Generate sector-aware individual company analyst notes for quant Top-N names."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from src.report.sector_report_model import (
    build_sector_summary,
    build_top_sector_dataset,
    _sector_valuation_profile,
)


ROOT = Path(__file__).resolve().parents[2]
FONT_PATH = Path("/System/Library/Fonts/Supplemental/AppleGothic.ttf")
FONT_NAME = "AppleGothic"

BRAND = colors.HexColor("#143A5A")
ACCENT = colors.HexColor("#2C7FB8")
GREEN = colors.HexColor("#2D8A57")
RED = colors.HexColor("#C84B31")
GREY = colors.HexColor("#6B7280")
LIGHT = colors.HexColor("#EEF3F7")


@dataclass(frozen=True)
class CompanyReportResult:
    output_dir: Path
    index_markdown: Path
    valuation_csv: Path
    pdf_paths: list[Path]
    markdown_paths: list[Path]


def generate_company_reports(
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
    output_dir: str | Path = "outputs/reports/company_top30",
    top_n: int = 30,
) -> CompanyReportResult:
    """Create one analyst-style company report per latest quant Top-N name."""
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
    valuations = _build_company_valuations(top)
    price_history = _load_price_history(price_path, valuations["ticker"].tolist())

    valuation_csv = output_path / "latest_top30_company_valuations.csv"
    valuations.to_csv(valuation_csv, index=False, encoding="utf-8-sig")

    pdf_paths: list[Path] = []
    markdown_paths: list[Path] = []
    for _, row in valuations.sort_values("rank").iterrows():
        slug = _slugify(f"{row['ticker']}_{row['name']}")
        pdf_path = output_path / f"{slug}_Company_Report.pdf"
        md_path = output_path / f"{slug}_Company_Report.md"
        sector_frame = valuations[valuations["sector_model"].eq(row["sector_model"])].copy()
        ticker_price = price_history[price_history["ticker"].eq(row["ticker"])].copy()
        _build_company_pdf(row, sector_frame, sector_summary, ticker_price, pdf_path, top_n)
        md_path.write_text(_build_company_markdown(row, sector_frame, top_n), encoding="utf-8")
        pdf_paths.append(pdf_path)
        markdown_paths.append(md_path)

    index_markdown = output_path / "Company_Report_Index.md"
    index_markdown.write_text(
        _build_index_markdown(valuations, pdf_paths, markdown_paths, top_n),
        encoding="utf-8",
    )
    return CompanyReportResult(
        output_dir=output_path,
        index_markdown=index_markdown,
        valuation_csv=valuation_csv,
        pdf_paths=pdf_paths,
        markdown_paths=markdown_paths,
    )


def _build_company_valuations(top: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for sector, frame in top.groupby("sector_model", sort=False):
        peer_stats = _peer_stats(frame)
        for _, row in frame.iterrows():
            rows.append(_value_company(row, peer_stats))
    valuations = pd.DataFrame(rows)
    keep = [
        "rank",
        "ticker",
        "name",
        "sector_model",
        "sector_source",
        "signal_date",
        "date",
        "rating",
        "current_price",
        "target_price",
        "upside",
        "fair_value_per_share",
        "primary_method",
        "valuation_basis",
        "target_multiple",
        "confidence",
        "composite_score",
        "ml_score",
        "current_per",
        "current_pbr",
        "current_psr",
        "ev_ebitda_proxy",
        "roe",
        "operating_margin",
        "sales_growth",
        "revenue",
        "operating_income",
        "net_income",
        "equity",
        "market_cap_proxy",
        "enterprise_value_proxy",
        "net_debt_proxy",
        "ebitda_proxy",
        "eps",
        "bps",
        "analyst_note_readiness",
        "dart_table_bridge_count",
        "revenue_segment_bridge_count",
        "ebitda_bridge_count",
        "backlog_bridge_count",
        "nav_bridge_count",
        "financial_data_basis",
        "investment_thesis",
        "key_risks",
    ]
    return valuations[keep].sort_values("rank").reset_index(drop=True)


def _peer_stats(frame: pd.DataFrame) -> dict[str, float]:
    positive_per = _positive(frame["current_per"])
    positive_ev_ebitda = _positive(frame["ev_ebitda_proxy"])
    return {
        "median_per": _bounded_median(positive_per, fallback=10.0),
        "median_pbr": _bounded_median(_positive(frame["current_pbr"]), fallback=1.0),
        "median_psr": _bounded_median(_positive(frame["current_psr"]), fallback=0.8),
        "median_ev_ebitda": _bounded_median(positive_ev_ebitda, fallback=7.0),
        "median_roe": _bounded_median(frame["roe"].dropna(), fallback=0.08),
        "median_opm": _bounded_median(frame["operating_margin"].dropna(), fallback=0.07),
        "median_score": _bounded_median(frame["composite_score"].dropna(), fallback=0.0),
    }


def _value_company(row: pd.Series, peer_stats: dict[str, float]) -> dict[str, object]:
    sector = str(row["sector_model"])
    profile = _sector_valuation_profile(sector)
    current_price = _num(row.get("adj_close"))
    eps = _num(row.get("eps"))
    bps = _num(row.get("bps"))
    ebitda = _num(row.get("ebitda_proxy"))
    net_debt = _num(row.get("net_debt_proxy"))
    shares = max(_num(row.get("shares_outstanding")), 1.0)
    score_adj = _score_adjustment(_num(row.get("composite_score")), peer_stats["median_score"])
    quality_adj = _quality_adjustment(row, peer_stats)

    method = profile.primary_method
    target_multiple = math.nan
    fair_value = math.nan
    basis = ""

    if sector == "Financials":
        target_multiple = _clamp(peer_stats["median_pbr"] * (1 + 0.55 * quality_adj + 0.20 * score_adj), 0.25, 1.8)
        fair_value = bps * target_multiple
        basis = f"BPS {_krw_plain(bps)} x target PBR {target_multiple:.2f}x"
    elif sector in {"Energy & Chemicals", "Industrials", "Logistics"}:
        target_multiple = _clamp(peer_stats["median_ev_ebitda"] * (1 + 0.35 * quality_adj + 0.20 * score_adj), 4.0, 14.0)
        fair_value = ((ebitda * target_multiple) - net_debt) / shares if ebitda > 0 else _fallback_per_value(row, peer_stats)
        basis = f"EBITDA {_krw_plain(ebitda)} x target EV/EBITDA {target_multiple:.1f}x - net debt"
    elif sector == "Holdings & Investment":
        nav_evidence = _num(row.get("nav_bridge_count")) + _num(row.get("nav_evidence"))
        discount_relief = min(nav_evidence / 10, 0.20)
        target_multiple = _clamp(peer_stats["median_pbr"] * (1 + 0.30 * quality_adj + 0.20 * score_adj + discount_relief), 0.25, 1.3)
        fair_value = bps * target_multiple
        method = "NAV discount proxy"
        basis = f"BPS {_krw_plain(bps)} x target PBR/NAV proxy {target_multiple:.2f}x"
    elif sector == "Construction & Infrastructure":
        backlog_support = min((_num(row.get("backlog_bridge_count")) + _num(row.get("backlog_evidence"))) / 20, 0.15)
        target_multiple = _clamp(peer_stats["median_pbr"] * (1 + 0.25 * quality_adj + 0.15 * score_adj + backlog_support), 0.25, 1.4)
        fair_value = bps * target_multiple
        method = "PBR plus backlog/margin cycle"
        basis = f"BPS {_krw_plain(bps)} x target PBR {target_multiple:.2f}x with backlog evidence"
    else:
        target_multiple = _clamp(peer_stats["median_per"] * (1 + 0.30 * quality_adj + 0.25 * score_adj), 5.0, 32.0)
        fair_value = eps * target_multiple if eps > 0 else _fallback_pbr_value(row, peer_stats)
        basis = f"EPS {_krw_plain(eps)} x target PER {target_multiple:.1f}x"

    if not _is_finite(fair_value) or fair_value <= 0:
        fair_value = _fallback_pbr_value(row, peer_stats)
        basis = f"Fallback BPS {_krw_plain(bps)} x peer PBR {peer_stats['median_pbr']:.2f}x"

    target_price = _round_target_price(fair_value)
    upside = target_price / current_price - 1 if current_price > 0 else math.nan
    confidence = _confidence(row, method)
    rating = _rating(upside, confidence)

    result = row.to_dict()
    result.update(
        {
            "rating": rating,
            "current_price": current_price,
            "target_price": target_price,
            "upside": upside,
            "fair_value_per_share": fair_value,
            "primary_method": method,
            "valuation_basis": basis,
            "target_multiple": target_multiple,
            "confidence": confidence,
            "investment_thesis": _investment_thesis(row, method, upside),
            "key_risks": _key_risks(row),
        }
    )
    return result


def _load_price_history(price_path: str | Path, tickers: list[str]) -> pd.DataFrame:
    path = ROOT / price_path
    frame = pd.read_csv(path, dtype={"ticker": "string"}, parse_dates=["date"])
    frame["ticker"] = frame["ticker"].astype("string").str.zfill(6)
    frame = frame[frame["ticker"].isin(tickers)].sort_values(["ticker", "date"])
    cutoff = frame["date"].max() - pd.DateOffset(months=18)
    return frame[frame["date"].ge(cutoff)].copy()


def _build_company_pdf(
    row: pd.Series,
    sector_frame: pd.DataFrame,
    sector_summary: pd.DataFrame,
    price: pd.DataFrame,
    pdf_path: Path,
    top_n: int,
) -> None:
    styles = _styles()
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )
    summary = sector_summary[sector_summary["sector_model"].eq(row["sector_model"])].iloc[0]
    story = [
        _title_block(
            f"{row['name']} ({row['ticker']})",
            f"{row['sector_model']} | Quant Top{top_n} rank {int(row['rank'])} | signal {pd.Timestamp(row['signal_date']).date()}",
            f"{row['rating']} / TP {_krw(row['target_price'])}",
        ),
        Spacer(1, 6),
        _key_metrics_table(row),
        Spacer(1, 7),
        Paragraph("Valuation", styles["Section"]),
        _valuation_table(row, sector_frame),
        Spacer(1, 7),
        Paragraph("Investment Summary", styles["Section"]),
        *_bullets(
            [
                row["investment_thesis"],
                f"섹터 primary method는 {row['primary_method']}이며, 목표가는 {row['valuation_basis']} 방식으로 산출했다.",
                f"DART 기반 재무/원문/표 evidence를 반영한 note readiness는 {_pct(row['analyst_note_readiness'])}, table bridge 후보는 {int(_num(row['dart_table_bridge_count']))}건이다.",
            ],
            styles,
        ),
        Spacer(1, 7),
        _two_column_charts(
            _price_chart(price, row),
            _peer_chart(sector_frame, row),
        ),
        Spacer(1, 7),
        Paragraph("Disclosure & Sector Evidence", styles["Section"]),
        _evidence_table(row, summary),
        Spacer(1, 7),
        Paragraph("Key Risks", styles["Section"]),
        *_bullets(row["key_risks"].split(" | "), styles),
        Spacer(1, 7),
        Paragraph("Analyst View", styles["Section"]),
        Paragraph(_analyst_view(row), styles["Body"]),
        Spacer(1, 5),
        Paragraph(
            "자료: 자체 KOSPI200 코어-위성 퀀트 모델, TS2000/OpenDART 재무데이터, KIS API 가격데이터. 본 자료는 자동 생성된 채용 과제용 리서치 초안이며 투자 권유가 아니다.",
            styles["Note"],
        ),
    ]
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)


def _build_company_markdown(row: pd.Series, sector_frame: pd.DataFrame, top_n: int) -> str:
    peer_rows = []
    for _, peer in sector_frame.sort_values("composite_score", ascending=False).iterrows():
        peer_rows.append(
            f"| {int(peer['rank'])} | {peer['ticker']} | {peer['name']} | {peer['rating']} | {_krw(peer['target_price'])} | {_pct(peer['upside'])} | {_per(peer['current_per'])} | {_multiple(peer['current_pbr'])} | {_pct(peer['roe'])} |"
        )
    return f"""# {row['name']} ({row['ticker']}) Company Report

- Signal date: {pd.Timestamp(row['signal_date']).date()}
- Universe: Latest KOSPI200 quant Top{top_n}
- Sector: {row['sector_model']}
- Rating: {row['rating']}
- Current price: {_krw(row['current_price'])}
- Target price: {_krw(row['target_price'])}
- Upside: {_pct(row['upside'])}
- Primary valuation: {row['primary_method']}
- Valuation basis: {row['valuation_basis']}
- Confidence: {_pct(row['confidence'])}

## Investment Summary

- {row['investment_thesis']}
- 섹터별 valuation anchor를 적용해 목표가를 계산했다.
- DART table bridge 후보 {int(_num(row['dart_table_bridge_count']))}건, revenue segment {int(_num(row['revenue_segment_bridge_count']))}건, EBITDA {int(_num(row['ebitda_bridge_count']))}건, backlog {int(_num(row['backlog_bridge_count']))}건, NAV {int(_num(row['nav_bridge_count']))}건을 검수 대상으로 남겼다.

## Valuation Snapshot

| Metric | Value |
|---|---:|
| PER | {_per(row['current_per'])} |
| PBR | {_multiple(row['current_pbr'])} |
| PSR | {_multiple(row['current_psr'])} |
| EV/EBITDA proxy | {_per(row['ev_ebitda_proxy'])} |
| ROE | {_pct(row['roe'])} |
| OPM | {_pct(row['operating_margin'])} |
| Sales growth | {_pct(row['sales_growth'])} |

## Sector Peer Snapshot

| Rank | Ticker | Name | Rating | Target | Upside | PER | PBR | ROE |
|---:|---|---|---|---:|---:|---:|---:|---:|
{chr(10).join(peer_rows)}

## Key Risks

{chr(10).join(f'- {risk}' for risk in row['key_risks'].split(' | '))}

자료: 자체 KOSPI200 코어-위성 퀀트 모델, TS2000/OpenDART 재무데이터, KIS API 가격데이터.
"""


def _build_index_markdown(valuations: pd.DataFrame, pdf_paths: list[Path], markdown_paths: list[Path], top_n: int) -> str:
    pdf_map = {path.stem.replace("_Company_Report", ""): path.name for path in pdf_paths}
    md_map = {path.stem.replace("_Company_Report", ""): path.name for path in markdown_paths}
    lines = [
        f"# Quant Top{top_n} Company Report Index",
        "",
        f"- Signal date: {pd.Timestamp(valuations['signal_date'].iloc[0]).date()}",
        f"- Generated company reports: {len(valuations)}",
        "- CSV: `latest_top30_company_valuations.csv`",
        "",
        "| Rank | Ticker | Name | Sector | Rating | Target | Upside | Method | Confidence | PDF | Markdown |",
        "|---:|---|---|---|---|---:|---:|---|---:|---|---|",
    ]
    for _, row in valuations.sort_values("rank").iterrows():
        slug = _slugify(f"{row['ticker']}_{row['name']}")
        lines.append(
            f"| {int(row['rank'])} | {row['ticker']} | {row['name']} | {row['sector_model']} | {row['rating']} | {_krw(row['target_price'])} | {_pct(row['upside'])} | {row['primary_method']} | {_pct(row['confidence'])} | `{pdf_map.get(slug, '')}` | `{md_map.get(slug, '')}` |"
        )
    return "\n".join(lines) + "\n"


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    font = FONT_NAME if FONT_PATH.exists() else "Helvetica"
    return {
        "Section": ParagraphStyle("Section", parent=base["Heading2"], fontName=font, fontSize=12, leading=15, textColor=BRAND, spaceBefore=4, spaceAfter=4),
        "Body": ParagraphStyle("Body", parent=base["BodyText"], fontName=font, fontSize=8.5, leading=12.5, textColor=colors.HexColor("#222222")),
        "Bullet": ParagraphStyle("Bullet", parent=base["BodyText"], fontName=font, fontSize=8.2, leading=11.5, leftIndent=8, firstLineIndent=-6),
        "Note": ParagraphStyle("Note", parent=base["BodyText"], fontName=font, fontSize=7.1, leading=9.5, textColor=GREY),
    }


def _title_block(title: str, subtitle: str, tag: str) -> Table:
    title_style = ParagraphStyle("HeaderTitle", fontName=FONT_NAME, fontSize=15.5, leading=19, textColor=colors.white)
    subtitle_style = ParagraphStyle("HeaderSubtitle", fontName=FONT_NAME, fontSize=8.1, leading=10.5, textColor=colors.white)
    tag_style = ParagraphStyle("HeaderTag", fontName=FONT_NAME, fontSize=8, leading=10, textColor=colors.white, alignment=TA_CENTER)
    table = Table(
        [[Paragraph(title, title_style), Paragraph(tag, tag_style)], [Paragraph(subtitle, subtitle_style), ""]],
        colWidths=[124 * mm, 52 * mm],
        rowHeights=[13 * mm, 9 * mm],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BRAND),
                ("BACKGROUND", (1, 0), (1, 0), ACCENT),
                ("SPAN", (1, 0), (1, 1)),
                ("BOX", (0, 0), (-1, -1), 0, BRAND),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _key_metrics_table(row: pd.Series) -> Table:
    data = [
        ["투자의견", row["rating"], "목표주가", _krw(row["target_price"])],
        ["현재주가", _krw(row["current_price"]), "상승여력", _pct(row["upside"])],
        ["Valuation", row["primary_method"], "Target multiple", _multiple(row["target_multiple"])],
        ["PER/PBR", f"{_per(row['current_per'])} / {_multiple(row['current_pbr'])}", "EV/EBITDA", _per(row["ev_ebitda_proxy"])],
        ["ROE/OPM", f"{_pct(row['roe'])} / {_pct(row['operating_margin'])}", "Sales growth", _pct(row["sales_growth"])],
        ["Quant rank", f"{int(row['rank'])}위", "Composite/ML", f"{row['composite_score']:.2f} / {row['ml_score']:.2f}"],
    ]
    table = Table(data, colWidths=[27 * mm, 50 * mm, 27 * mm, 72 * mm])
    table.setStyle(_table_style(header=False, font_size=7.0))
    return table


def _valuation_table(row: pd.Series, sector_frame: pd.DataFrame) -> Table:
    sector_median_per = _positive(sector_frame["current_per"]).median()
    sector_median_pbr = _positive(sector_frame["current_pbr"]).median()
    sector_median_ev = _positive(sector_frame["ev_ebitda_proxy"]).median()
    data = [
        ["구분", "자동 산출값", "Peer median", "해석"],
        ["목표가", _krw(row["target_price"]), "-", row["valuation_basis"]],
        ["상승여력", _pct(row["upside"]), "-", _rating_comment(row["rating"])],
        ["PER", _per(row["current_per"]), _per(sector_median_per), "이익가치 cross-check"],
        ["PBR", _multiple(row["current_pbr"]), _multiple(sector_median_pbr), "자산가치/ROE cross-check"],
        ["EV/EBITDA", _per(row["ev_ebitda_proxy"]), _per(sector_median_ev), "순차입금 조정 기업가치 proxy"],
    ]
    table = Table(data, colWidths=[24 * mm, 35 * mm, 33 * mm, 84 * mm])
    table.setStyle(_table_style(header=True, font_size=6.8))
    return table


def _evidence_table(row: pd.Series, summary: pd.Series) -> Table:
    data = [
        ["항목", "기업", "섹터 평균/원천"],
        ["재무 데이터", row["financial_data_basis"], f"DART coverage {_pct(summary['dart_coverage'])}"],
        ["DART note readiness", _pct(row["analyst_note_readiness"]), f"Sector avg {_pct(summary['avg_analyst_note_readiness'])}"],
        ["Revenue segment bridge", f"{int(_num(row['revenue_segment_bridge_count']))}건", "사업부문 매출 표 후보"],
        ["EBITDA bridge", f"{int(_num(row['ebitda_bridge_count']))}건", "상각/영업이익 bridge 후보"],
        ["Backlog bridge", f"{int(_num(row['backlog_bridge_count']))}건", "수주잔고/계약잔액 후보"],
        ["NAV bridge", f"{int(_num(row['nav_bridge_count']))}건", "투자주식/관계기업 후보"],
    ]
    table = Table(data, colWidths=[42 * mm, 49 * mm, 85 * mm])
    table.setStyle(_table_style(header=True, font_size=6.8))
    return table


def _price_chart(price: pd.DataFrame, row: pd.Series) -> Drawing:
    width, height = 84 * mm, 52 * mm
    drawing = Drawing(width, height)
    drawing.add(Rect(0, 0, width, height, strokeColor=colors.HexColor("#D8DEE6"), fillColor=colors.white))
    drawing.add(String(4 * mm, height - 6 * mm, "Price trend", fontName=FONT_NAME, fontSize=7.2, fillColor=BRAND))
    if price.empty:
        drawing.add(String(8 * mm, 24 * mm, "No price history", fontName=FONT_NAME, fontSize=7, fillColor=GREY))
        return drawing
    sample = price.tail(90).copy()
    values = sample["adj_close"].astype(float).tolist()
    chart = HorizontalLineChart()
    chart.x = 8 * mm
    chart.y = 10 * mm
    chart.width = 66 * mm
    chart.height = 30 * mm
    chart.data = [values]
    low = min(values) * 0.94
    high = max(values) * 1.06
    chart.valueAxis.valueMin = low
    chart.valueAxis.valueMax = high if high > low else low + 1
    chart.valueAxis.valueStep = (chart.valueAxis.valueMax - chart.valueAxis.valueMin) / 4
    chart.lines[0].strokeColor = ACCENT
    chart.lines[0].strokeWidth = 1.5
    chart.categoryAxis.visibleLabels = 0
    chart.categoryAxis.visibleTicks = 0
    chart.categoryAxis.strokeColor = colors.HexColor("#D8DEE6")
    chart.valueAxis.labels.fontName = FONT_NAME
    chart.valueAxis.labels.fontSize = 5.5
    drawing.add(chart)
    target_y = 10 * mm + 30 * mm * (_num(row["target_price"]) - low) / (chart.valueAxis.valueMax - low)
    if 10 * mm <= target_y <= 40 * mm:
        drawing.add(Line(8 * mm, target_y, 74 * mm, target_y, strokeColor=GREEN, strokeWidth=0.5))
        drawing.add(String(55 * mm, target_y + 1.5 * mm, "TP", fontName=FONT_NAME, fontSize=6, fillColor=GREEN))
    return drawing


def _peer_chart(sector_frame: pd.DataFrame, row: pd.Series) -> Drawing:
    chart_frame = sector_frame.sort_values("composite_score", ascending=False).head(6).copy()
    labels = [_short_name(name) for name in chart_frame["name"]]
    values = (chart_frame["upside"] * 100).round(1).tolist()
    width, height = 84 * mm, 52 * mm
    drawing = Drawing(width, height)
    drawing.add(Rect(0, 0, width, height, strokeColor=colors.HexColor("#D8DEE6"), fillColor=colors.white))
    drawing.add(String(4 * mm, height - 6 * mm, "Upside by sector peer (%)", fontName=FONT_NAME, fontSize=7.2, fillColor=BRAND))
    chart = VerticalBarChart()
    chart.x = 8 * mm
    chart.y = 10 * mm
    chart.width = 66 * mm
    chart.height = 30 * mm
    chart.data = [values]
    low = min(0, min(values) * 1.2)
    high = max(10, max(values) * 1.2)
    chart.valueAxis.valueMin = low
    chart.valueAxis.valueMax = high if high > low else low + 1
    chart.valueAxis.valueStep = (chart.valueAxis.valueMax - chart.valueAxis.valueMin) / 4
    chart.categoryAxis.categoryNames = labels
    chart.categoryAxis.labels.fontName = FONT_NAME
    chart.categoryAxis.labels.fontSize = 4.8
    chart.categoryAxis.labels.angle = 25
    chart.valueAxis.labels.fontName = FONT_NAME
    chart.valueAxis.labels.fontSize = 5.5
    chart.bars[0].fillColor = GREEN if row["rating"] == "BUY" else ACCENT
    drawing.add(chart)
    return drawing


def _two_column_charts(left: Drawing, right: Drawing) -> Table:
    table = Table([[left, right]], colWidths=[88 * mm, 88 * mm])
    table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return table


def _analyst_view(row: pd.Series) -> str:
    return (
        f"{row['name']}에 대해 자동 산출 투자의견 {row['rating']}, 목표주가 {_krw(row['target_price'])}를 제시한다. "
        f"핵심 valuation은 {row['primary_method']}이며, {row['valuation_basis']}를 기준으로 주당 적정가치 {_krw(row['fair_value_per_share'])}를 계산했다. "
        f"현재가 대비 상승여력은 {_pct(row['upside'])}이다. "
        f"다만 목표가는 DART 단일계정과 표 후보를 활용한 proxy이므로, 실제 발간 전에는 원문 주석의 세부 계정, IR guidance, peer multiple을 analyst가 최종 검수해야 한다."
    )


def _investment_thesis(row: pd.Series, method: str, upside: float) -> str:
    name = row["name"]
    sector = row["sector_model"]
    common = f"{name}은 {sector} 내 quant rank {int(row['sector_rank'])}위, composite score {row['composite_score']:.2f}로 선별됐다."
    if sector == "Financials":
        return f"{common} ROE {_pct(row['roe'])}와 PBR {_multiple(row['current_pbr'])}의 균형을 PBR/ROE 방식으로 점검할 필요가 있다."
    if sector in {"Energy & Chemicals", "Industrials", "Logistics"}:
        return f"{common} EBITDA와 순차입금을 반영한 EV/EBITDA 관점에서 {_pct(upside)}의 재평가 여지를 계산했다."
    if sector == "Construction & Infrastructure":
        return f"{common} 수주잔고 evidence와 마진 안정성을 PBR cycle에 결합해 목표가를 산출했다."
    if sector == "Holdings & Investment":
        return f"{common} DART NAV 관련 표 후보와 book discount를 함께 반영해 NAV discount 축소 가능성을 점검했다."
    return f"{common} {method} 중심으로 이익가치와 PBR/ROE cross-check를 함께 적용했다."


def _key_risks(row: pd.Series) -> str:
    sector = row["sector_model"]
    base = ["퀀트 점수는 후행 재무와 가격 데이터를 포함하므로 급격한 업황 변화를 즉시 반영하지 못할 수 있다"]
    sector_risks = {
        "Financials": ["충당금·금리·자본규제 변화", "주주환원 정책 후퇴"],
        "Energy & Chemicals": ["스프레드와 원재료 가격 변동", "순차입금·capex 확대"],
        "Construction & Infrastructure": ["원가율 상승과 해외 프로젝트 손실", "수주잔고의 매출 전환 지연"],
        "Industrials": ["수주 취소와 납기 지연", "원재료·환율에 따른 마진 변동"],
        "Holdings & Investment": ["자회사 가치 하락", "NAV discount 장기화"],
        "Semiconductors": ["메모리 가격 하락", "capex cycle과 재고 부담"],
        "Gaming & Internet": ["신작 흥행 실패", "인건비와 플랫폼 수수료 부담"],
    }
    base.extend(sector_risks.get(sector, ["수요 둔화와 마진 하락", "peer multiple 하향"]))
    return " | ".join(base)


def _table_style(header: bool, font_size: float = 7.0) -> TableStyle:
    commands = [
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("LEADING", (0, 0), (-1, -1), font_size + 2),
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


def _bullets(items: list[str], styles: dict[str, ParagraphStyle]) -> list[Paragraph]:
    return [Paragraph(f"- {item}", styles["Bullet"]) for item in items]


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont(FONT_NAME, 7)
    canvas.setFillColor(GREY)
    canvas.drawString(14 * mm, 8 * mm, "Automated company analyst note | Data: TS2000/OpenDART, KIS API, internal quant model")
    canvas.drawRightString(196 * mm, 8 * mm, f"{doc.page}")
    canvas.restoreState()


def _register_fonts() -> None:
    if FONT_PATH.exists():
        pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH)))


def _score_adjustment(score: float, median_score: float) -> float:
    return _clamp((score - median_score) / 2.0, -0.35, 0.35)


def _quality_adjustment(row: pd.Series, peer_stats: dict[str, float]) -> float:
    roe_gap = _num(row.get("roe")) - peer_stats["median_roe"]
    opm_gap = _num(row.get("operating_margin")) - peer_stats["median_opm"]
    growth = _num(row.get("sales_growth"))
    return _clamp((roe_gap * 1.6) + (opm_gap * 0.9) + (growth * 0.15), -0.45, 0.45)


def _confidence(row: pd.Series, method: str) -> float:
    score = 0.45
    score += 0.20 if "OpenDART" in str(row.get("financial_data_basis", "")) else 0.05
    score += min(_num(row.get("analyst_note_readiness")), 1.0) * 0.15
    score += min(_num(row.get("dart_table_bridge_count")) / 80, 0.15)
    if "EV/EBITDA" in method:
        score += 0.05 if _num(row.get("ebitda_bridge_count")) > 0 or _num(row.get("ebitda_proxy")) > 0 else -0.05
    if "NAV" in method:
        score += 0.05 if _num(row.get("nav_bridge_count")) > 0 else -0.05
    if "backlog" in method.lower():
        score += 0.05 if _num(row.get("backlog_bridge_count")) > 0 else -0.05
    return _clamp(score, 0.2, 0.95)


def _rating(upside: float, confidence: float) -> str:
    if not _is_finite(upside):
        return "NOT RATED"
    hurdle = 0.15 if confidence >= 0.55 else 0.20
    if upside >= hurdle:
        return "BUY"
    if upside <= -0.10:
        return "REDUCE"
    return "HOLD"


def _rating_comment(rating: str) -> str:
    return {
        "BUY": "15% 이상 상승여력 또는 높은 신뢰도 구간",
        "HOLD": "목표가와 현재가가 균형권",
        "REDUCE": "목표가가 현재가를 의미 있게 하회",
    }.get(rating, "데이터 보완 필요")


def _fallback_per_value(row: pd.Series, peer_stats: dict[str, float]) -> float:
    eps = _num(row.get("eps"))
    if eps > 0:
        return eps * peer_stats["median_per"]
    return _fallback_pbr_value(row, peer_stats)


def _fallback_pbr_value(row: pd.Series, peer_stats: dict[str, float]) -> float:
    bps = _num(row.get("bps"))
    if bps > 0:
        return bps * _clamp(peer_stats["median_pbr"], 0.3, 1.8)
    return _num(row.get("adj_close"))


def _round_target_price(value: float) -> float:
    if not _is_finite(value) or value <= 0:
        return math.nan
    if value >= 100_000:
        unit = 5_000
    elif value >= 20_000:
        unit = 1_000
    elif value >= 5_000:
        unit = 500
    else:
        unit = 100
    return round(value / unit) * unit


def _positive(series: pd.Series) -> pd.Series:
    return series.dropna().where(series > 0).dropna()


def _bounded_median(series: pd.Series, fallback: float) -> float:
    if series.empty:
        return fallback
    value = float(series.median())
    return value if _is_finite(value) and value > 0 else fallback


def _num(value: object) -> float:
    if pd.isna(value):
        return 0.0
    try:
        result = float(value)
    except (TypeError, ValueError):
        return 0.0
    return result if _is_finite(result) else 0.0


def _is_finite(value: float) -> bool:
    return not pd.isna(value) and math.isfinite(float(value))


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _krw(value: object) -> str:
    number = _num(value)
    if number == 0 and pd.isna(value):
        return "-"
    return f"{number:,.0f}원"


def _krw_plain(value: object) -> str:
    number = _num(value)
    if abs(number) >= 1e12:
        return f"{number / 1e12:.2f}조원"
    if abs(number) >= 1e8:
        return f"{number / 1e8:.0f}억원"
    return _krw(number)


def _pct(value: object) -> str:
    if pd.isna(value):
        return "-"
    return f"{_num(value) * 100:.1f}%"


def _multiple(value: object) -> str:
    if pd.isna(value):
        return "-"
    return f"{_num(value):.2f}x"


def _per(value: object) -> str:
    number = _num(value)
    if number <= 0:
        return "N/M"
    return f"{number:.1f}x"


def _short_name(name: str) -> str:
    return (
        str(name)
        .replace("(주)", "")
        .replace("주식회사", "")
        .replace("에스케이", "SK")
        .replace("삼성", "삼성")
    )[:9]


def _slugify(value: str) -> str:
    text = re.sub(r"[^0-9A-Za-z가-힣_]+", "_", str(value))
    text = re.sub(r"_+", "_", text).strip("_")
    return text[:80]
