"""Generate an analyst-style LS ELECTRIC company report."""

from __future__ import annotations

import json
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
from reportlab.platypus import (
    Flowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "outputs" / "reports" / "recruiting"
PDF_PATH = OUT_DIR / "Assignment1_LS_ELECTRIC_Analyst_Report.pdf"
MD_PATH = OUT_DIR / "Assignment1_LS_ELECTRIC_Company_Analysis.md"

FONT_PATH = Path("/System/Library/Fonts/Supplemental/AppleGothic.ttf")
FONT_NAME = "AppleGothic"

BRAND = colors.HexColor("#143A5A")
ACCENT = colors.HexColor("#2C7FB8")
GREEN = colors.HexColor("#2D8A57")
RED = colors.HexColor("#C84B31")
GREY = colors.HexColor("#6B7280")
LIGHT = colors.HexColor("#EEF3F7")


def generate_ls_electric_report() -> tuple[Path, Path]:
    """Create Markdown and PDF versions of the LS ELECTRIC report."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _register_fonts()

    fundamentals = _load_fundamentals()
    price = _load_price()
    kodex = _load_kodex()
    factors = _load_factors()
    dart_summary = _load_dart_summary()
    dart_accounts = _load_dart_accounts()
    peers = _load_peer_table()
    metrics = _build_metric_dict(fundamentals, price, factors, dart_accounts)

    MD_PATH.write_text(_build_markdown(metrics, fundamentals, factors, peers, dart_summary), encoding="utf-8")
    _build_pdf(metrics, fundamentals, price, kodex, factors, peers, dart_summary)
    return MD_PATH, PDF_PATH


def _register_fonts() -> None:
    if FONT_PATH.exists():
        pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH)))


def _load_fundamentals() -> pd.DataFrame:
    frame = pd.read_csv(
        ROOT / "data/raw/ts2000/fundamentals_long.csv",
        dtype={"ticker": "string"},
        parse_dates=["available_date"],
    )
    frame["ticker"] = frame["ticker"].astype("string").str.zfill(6)
    frame = frame[frame["ticker"].eq("010120")].sort_values("available_date")
    frame = frame[frame["fiscal_period"].astype(str).str.endswith("-12")].copy()
    return frame.tail(10)


def _load_price() -> pd.DataFrame:
    frame = pd.read_csv(
        ROOT / "data/raw/price/prices_2007_2026.csv",
        dtype={"ticker": "string"},
        parse_dates=["date"],
    )
    frame["ticker"] = frame["ticker"].astype("string").str.zfill(6)
    return frame[frame["ticker"].eq("010120")].sort_values("date").copy()


def _load_kodex() -> pd.DataFrame:
    frame = pd.read_csv(
        ROOT / "data/raw/benchmark/kodex200_prices.csv",
        dtype={"ticker": "string"},
        parse_dates=["date"],
    )
    return frame.sort_values("date").copy()


def _load_factors() -> pd.DataFrame:
    frame = pd.read_csv(
        ROOT / "data/features/institutional_core_satellite_scores.csv",
        dtype={"ticker": "string"},
        parse_dates=["signal_date"],
    )
    frame["ticker"] = frame["ticker"].astype("string").str.zfill(6)
    return frame[frame["ticker"].eq("010120")].sort_values("signal_date").copy()


def _load_dart_summary() -> dict:
    path = ROOT / "data/raw/dart/ls_electric/dart_summary.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _load_dart_accounts() -> pd.DataFrame:
    path = ROOT / "data/raw/dart/ls_electric/single_accounts.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _load_peer_table() -> pd.DataFrame:
    tickers = ["010120", "267260", "298040", "006260"]
    names = {
        "010120": "LS ELECTRIC",
        "267260": "HD현대일렉트릭",
        "298040": "효성중공업",
        "006260": "LS",
    }
    frame = pd.read_csv(
        ROOT / "data/raw/ts2000/fundamentals_long.csv",
        dtype={"ticker": "string"},
        parse_dates=["available_date"],
    )
    frame["ticker"] = frame["ticker"].astype("string").str.zfill(6)
    frame = frame[frame["ticker"].isin(tickers)]
    frame = frame[frame["fiscal_period"].astype(str).str.endswith("-12")].copy()
    latest = frame.sort_values("available_date").groupby("ticker", as_index=False).tail(1)
    latest["peer_name"] = latest["ticker"].map(names)
    prices = pd.read_csv(
        ROOT / "data/raw/price/prices_2007_2026.csv",
        dtype={"ticker": "string"},
        parse_dates=["date"],
    )
    prices["ticker"] = prices["ticker"].astype("string").str.zfill(6)
    latest_prices = prices[prices["ticker"].isin(tickers)].sort_values("date").groupby("ticker", as_index=False).tail(1)
    latest = latest.merge(latest_prices[["ticker", "adj_close"]], on="ticker", how="left")
    latest["eps"] = latest["net_income"] / latest["shares_outstanding"]
    latest["bps"] = latest["equity"] / latest["shares_outstanding"]
    latest["current_per"] = latest["adj_close"] / latest["eps"]
    latest["current_pbr"] = latest["adj_close"] / latest["bps"]
    latest["revenue_tn"] = latest["revenue"] / 1e12
    latest["op_margin_pct"] = latest["operating_margin"] * 100
    latest["roe_pct"] = latest["roe"] * 100
    return latest[
        ["peer_name", "revenue_tn", "op_margin_pct", "roe_pct", "current_per", "current_pbr", "sales_growth"]
    ].sort_values("peer_name")


def _build_metric_dict(
    fundamentals: pd.DataFrame,
    price: pd.DataFrame,
    factors: pd.DataFrame,
    dart_accounts: pd.DataFrame,
) -> dict[str, float | str]:
    latest = fundamentals.iloc[-1]
    prev = fundamentals.iloc[-2]
    price_latest = price.iloc[-1]
    latest_factor = factors.iloc[-1]
    dart = _extract_dart_financials(dart_accounts)
    if dart:
        latest = latest.copy()
        prev = prev.copy()
        latest["revenue"] = dart["revenue"]
        latest["operating_income"] = dart["operating_income"]
        latest["net_income"] = dart["net_income"]
        latest["equity"] = dart["equity"]
        latest["operating_margin"] = dart["operating_income"] / dart["revenue"]
        latest["net_margin"] = dart["net_income"] / dart["revenue"]
        latest["roe"] = dart["net_income"] / dart["equity"]
        prev["revenue"] = dart["prev_revenue"]
    latest_all = pd.read_csv(
        ROOT / "data/features/institutional_core_satellite_scores.csv",
        dtype={"ticker": "string"},
        parse_dates=["signal_date"],
    )
    latest_all["ticker"] = latest_all["ticker"].astype("string").str.zfill(6)
    latest_all = latest_all[latest_all["signal_date"].eq(latest_factor["signal_date"])]
    latest_all["rank"] = latest_all["composite_score"].rank(ascending=False, method="first")
    rank = latest_all[latest_all["ticker"].eq("010120")]["rank"].iloc[0]
    ytd_start = price[price["date"].dt.year.eq(2026)].iloc[0]["adj_close"]
    eps = latest["net_income"] / latest["shares_outstanding"]
    bps = latest["equity"] / latest["shares_outstanding"]
    current_per = price_latest["adj_close"] / eps
    current_pbr = price_latest["adj_close"] / bps
    forecast = _build_forecast(latest)
    forward_eps = forecast.loc[forecast["year"].eq("2026E"), "eps"].iloc[0]
    forward_bps = forecast.loc[forecast["year"].eq("2026E"), "bps"].iloc[0]
    target_per = 27.0
    target_pbr = 4.2
    per_value = forward_eps * target_per
    pbr_value = forward_bps * target_pbr
    dcf_value = _dcf_equity_value_per_share(forecast)
    fair_value = per_value * 0.60 + pbr_value * 0.25 + dcf_value * 0.15
    target_price = round(fair_value / 10_000) * 10_000
    upside = target_price / price_latest["adj_close"] - 1
    rating = "BUY" if upside >= 0.15 else "HOLD"
    return {
        "date": str(price_latest["date"].date()),
        "fiscal_period": str(latest["fiscal_period"]),
        "revenue_tn": latest["revenue"] / 1e12,
        "revenue_growth": latest["revenue"] / prev["revenue"] - 1,
        "op_income_100m": latest["operating_income"] / 1e8,
        "op_margin": latest["operating_margin"],
        "roe": latest["roe"],
        "close": price_latest["adj_close"],
        "ytd_return": price_latest["adj_close"] / ytd_start - 1,
        "factor_rank": rank,
        "factor_score": latest_factor["composite_score"],
        "ml_score": latest_factor["ml_score"],
        "regime": latest_factor["regime"],
        "eps": eps,
        "bps": bps,
        "forward_eps": forward_eps,
        "forward_bps": forward_bps,
        "current_per": current_per,
        "current_pbr": current_pbr,
        "target_per": target_per,
        "target_pbr": target_pbr,
        "per_value": per_value,
        "pbr_value": pbr_value,
        "dcf_value": dcf_value,
        "fair_value": fair_value,
        "target_price": target_price,
        "upside": upside,
        "rating": rating,
        "forecast": forecast,
        "data_basis": "OpenDART 연결" if dart else "TS2000",
        "dart_q1_revenue": dart.get("q1_revenue") if dart else 0,
        "dart_q1_op_income": dart.get("q1_operating_income") if dart else 0,
        "dart_q1_net_income": dart.get("q1_net_income") if dart else 0,
    }


def _extract_dart_financials(dart_accounts: pd.DataFrame) -> dict[str, float]:
    if dart_accounts.empty:
        return {}

    def amount(report: str, account: str, field: str = "thstrm_amount") -> float:
        rows = dart_accounts[
            dart_accounts["requested_report_name"].eq(report)
            & dart_accounts["fs_div"].eq("CFS")
            & dart_accounts["account_nm"].eq(account)
        ]
        if rows.empty:
            return float("nan")
        return _parse_amount(rows.iloc[0][field])

    result = {
        "revenue": amount("2025 사업보고서", "매출액"),
        "operating_income": amount("2025 사업보고서", "영업이익"),
        "net_income": amount("2025 사업보고서", "당기순이익(손실)"),
        "equity": amount("2025 사업보고서", "자본총계"),
        "prev_revenue": amount("2025 사업보고서", "매출액", "frmtrm_amount"),
        "q1_revenue": amount("2026 1분기보고서", "매출액"),
        "q1_operating_income": amount("2026 1분기보고서", "영업이익"),
        "q1_net_income": amount("2026 1분기보고서", "당기순이익(손실)"),
    }
    if any(pd.isna(value) for value in result.values()):
        return {}
    return result


def _parse_amount(value) -> float:
    if pd.isna(value):
        return float("nan")
    return float(str(value).replace(",", ""))


def _build_forecast(latest: pd.Series) -> pd.DataFrame:
    """Build a compact analyst-style forecast from the latest TS2000 base year."""
    assumptions = [
        ("2026E", 0.12, 0.110, 0.086),
        ("2027E", 0.09, 0.113, 0.088),
        ("2028E", 0.06, 0.114, 0.088),
    ]
    rows = []
    revenue = float(latest["revenue"])
    equity = float(latest["equity"])
    shares = float(latest["shares_outstanding"])
    payout = 0.20
    for year, growth, op_margin, net_margin in assumptions:
        revenue *= 1 + growth
        operating_income = revenue * op_margin
        net_income = revenue * net_margin
        equity += net_income * (1 - payout)
        rows.append(
            {
                "year": year,
                "revenue": revenue,
                "growth": growth,
                "op_margin": op_margin,
                "operating_income": operating_income,
                "net_income": net_income,
                "eps": net_income / shares,
                "bps": equity / shares,
                "roe": net_income / equity,
            }
        )
    return pd.DataFrame(rows)


def _dcf_equity_value_per_share(forecast: pd.DataFrame) -> float:
    """FCFE proxy valuation using net income less reinvestment as a simple cross-check."""
    cost_of_equity = 0.095
    terminal_growth = 0.025
    shares = 30_000_000
    fcfe = forecast["net_income"] * 0.82
    discounted = sum(
        cash_flow / ((1 + cost_of_equity) ** index)
        for index, cash_flow in enumerate(fcfe, start=1)
    )
    terminal = fcfe.iloc[-1] * (1 + terminal_growth) / (cost_of_equity - terminal_growth)
    discounted_terminal = terminal / ((1 + cost_of_equity) ** len(fcfe))
    return (discounted + discounted_terminal) / shares


def _build_pdf(
    metrics: dict[str, float | str],
    fundamentals: pd.DataFrame,
    price: pd.DataFrame,
    kodex: pd.DataFrame,
    factors: pd.DataFrame,
    peers: pd.DataFrame,
    dart_summary: dict,
) -> None:
    styles = _styles()
    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )
    story = []
    story.extend(_page_one(styles, metrics, fundamentals))
    story.append(PageBreak())
    story.extend(_page_two(styles, metrics, price, kodex, factors, peers, dart_summary))
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)


def _page_one(styles, metrics, fundamentals) -> list:
    story = [
        _title_block(
            "LS ELECTRIC (010120)",
            "AI 전력 인프라 사이클이 실적으로 확인되는 전력기기 성장주",
            f"투자의견: {metrics['rating']} / 목표주가: {_krw(metrics['target_price'])}",
        ),
        Spacer(1, 6),
        _key_metrics_table(metrics),
        Spacer(1, 8),
        Paragraph("Valuation & Earnings Forecast", styles["Section"]),
        _valuation_table(metrics),
        Spacer(1, 6),
        Paragraph("Investment Summary", styles["Section"]),
        _bullet("OpenDART 분기보고서상 데이터센터업은 전력·자동화 역량의 확장 사업으로 명시됐다.", styles),
        _bullet(f"{metrics['data_basis']} 기준 2025년 매출 {metrics['revenue_tn']:.2f}조원, 영업이익 {metrics['op_income_100m']:.0f}억원으로 외형과 수익성이 개선됐다.", styles),
        _bullet("2025년 데이터센터 관련 매출 약 5,468억원, 북미·Big Tech·HVDC 수주가 실적 가시성을 높인다.", styles),
        _bullet(f"목표주가 {_krw(metrics['target_price'])}는 2026E EPS 기반 PER, PBR, DCF proxy를 가중 평균해 산출했다.", styles),
        Spacer(1, 8),
        _two_column_charts(
            _revenue_profit_chart(fundamentals),
            _margin_roe_chart(fundamentals),
        ),
        Spacer(1, 8),
        Paragraph("Analyst View", styles["Section"]),
        Paragraph(
            f"LS ELECTRIC에 대해 투자의견 {metrics['rating']}와 목표주가 {_krw(metrics['target_price'])}를 제시한다. "
            "목표주가는 2026E EPS에 목표 PER 27배, 2026E BPS에 목표 PBR 4.2배를 적용하고, FCFE proxy DCF를 보조 검증으로 반영해 산출했다. "
            "DART 공시 기준 주요 사업은 전력기기·전력시스템·자동화이며, 데이터센터와 HVDC가 기존 제품 포트폴리오의 고부가 확장으로 연결되고 있다. "
            "따라서 투자 판단의 핵심은 북미 데이터센터·전력망 프로젝트 수주가 매출 인식과 마진으로 전환되는 속도다.",
            styles["Body"],
        ),
    ]
    return story


def _page_two(styles, metrics, price, kodex, factors, peers, dart_summary) -> list:
    story = [
        Paragraph("DART Disclosure Check", styles["Section"]),
        _dart_table(metrics, dart_summary),
        Spacer(1, 6),
        Paragraph("Price & Quant Signal", styles["Section"]),
        _two_column_charts(
            _price_relative_chart(price, kodex),
            _factor_signal_chart(factors),
        ),
        Spacer(1, 8),
        Paragraph("Peer Snapshot", styles["Section"]),
        _peer_table(peers),
        Spacer(1, 8),
        Paragraph("Target Price Sensitivity", styles["Section"]),
        _sensitivity_table(metrics),
        Spacer(1, 8),
        Paragraph("Key Risks", styles["Section"]),
        _bullet("DART상 데이터센터 사업은 품질, 신뢰성, 납기, 설치·시운전·유지보수 역량이 핵심 리스크다.", styles),
        _bullet("전력망 연계 지연, 인허가·규제 변화, 에너지 인프라 부족, 특정 고객·지역 매출 집중 가능성.", styles),
        _bullet("구리 등 원자재 가격, 환율, 대형 프로젝트 납기·검수 시점 변화에 따른 마진 변동성.", styles),
        _bullet(f"Target PER {metrics['target_per']:.1f}배는 peer premium과 2026E 성장 지속을 전제하므로 이익률 하락 시 목표주가 하향 가능.", styles),
        Spacer(1, 8),
        Paragraph("Conclusion", styles["Section"]),
        Paragraph(
            "LS ELECTRIC은 AI 전력 인프라라는 구조적 테마가 재무제표에 반영된 보기 드문 사례다. "
            f"목표주가 {_krw(metrics['target_price'])} 기준 상승여력은 {_pct(metrics['upside'])}로 매수 의견이 가능하다. "
            "다만 전력기기 업종 전반의 프리미엄이 이미 높아져 있어 DART 수주 공시, 분기별 영업이익률, ROE, 퀀트 랭킹 변화를 함께 추적해야 한다. "
            f"최신 KOSPI200 코어-위성 모델 기준 랭킹은 {metrics['factor_rank']:.0f}위로 Top 30 바로 아래이며, "
            "ML 신호는 강하지만 밸류에이션 및 방어 신호는 부담으로 해석된다.",
            styles["Body"],
        ),
        Spacer(1, 6),
        Paragraph(
            "자료: OpenDART 기업개황·정기보고서·단일회사 재무제표, TS2000 재무데이터, KIS API 가격데이터, 자체 KOSPI200 퀀트 모델. 본 자료는 채용 과제용 분석 샘플이며 투자 권유가 아니다.",
            styles["Note"],
        ),
    ]
    return story


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    font = FONT_NAME if FONT_PATH.exists() else "Helvetica"
    return {
        "Title": ParagraphStyle("Title", parent=base["Title"], fontName=font, fontSize=18, leading=23, textColor=BRAND, alignment=TA_LEFT, spaceAfter=3),
        "Subtitle": ParagraphStyle("Subtitle", parent=base["Normal"], fontName=font, fontSize=10.5, leading=14, textColor=colors.black),
        "Tag": ParagraphStyle("Tag", parent=base["Normal"], fontName=font, fontSize=9, leading=12, textColor=colors.white, alignment=TA_CENTER),
        "Section": ParagraphStyle("Section", parent=base["Heading2"], fontName=font, fontSize=12, leading=15, textColor=BRAND, spaceBefore=4, spaceAfter=4),
        "Body": ParagraphStyle("Body", parent=base["BodyText"], fontName=font, fontSize=8.7, leading=13, textColor=colors.HexColor("#222222")),
        "Bullet": ParagraphStyle("Bullet", parent=base["BodyText"], fontName=font, fontSize=8.5, leading=12, leftIndent=8, firstLineIndent=-6),
        "Note": ParagraphStyle("Note", parent=base["BodyText"], fontName=font, fontSize=7.2, leading=10, textColor=GREY),
    }


def _title_block(title: str, subtitle: str, tag: str) -> Table:
    title_style = ParagraphStyle(
        "HeaderTitle",
        fontName=FONT_NAME,
        fontSize=17,
        leading=20,
        textColor=colors.white,
    )
    subtitle_style = ParagraphStyle(
        "HeaderSubtitle",
        fontName=FONT_NAME,
        fontSize=8.4,
        leading=11,
        textColor=colors.white,
    )
    tag_style = ParagraphStyle(
        "HeaderTag",
        fontName=FONT_NAME,
        fontSize=7.2,
        leading=9,
        textColor=colors.white,
        alignment=TA_CENTER,
    )
    table = Table(
        [
            [Paragraph(title, title_style), Paragraph(tag, tag_style)],
            [Paragraph(subtitle, subtitle_style), ""],
        ],
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
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def _key_metrics_table(metrics: dict[str, float | str]) -> Table:
    data = [
        ["투자의견", metrics["rating"], "목표주가", _krw(metrics["target_price"])],
        ["현재주가", _krw(metrics["close"]), "상승여력", _pct(metrics["upside"])],
        ["2025 매출", f"{metrics['revenue_tn']:.2f}조원", "YoY", _pct(metrics["revenue_growth"])],
        ["2025 영업이익", f"{metrics['op_income_100m']:.0f}억원", "OPM", _pct(metrics["op_margin"])],
        ["ROE", _pct(metrics["roe"]), "현 PER/PBR", f"{metrics['current_per']:.1f}x / {metrics['current_pbr']:.2f}x"],
        ["YTD 수익률", _pct(metrics["ytd_return"]), "퀀트 랭킹", f"{metrics['factor_rank']:.0f}위"],
    ]
    table = Table(data, colWidths=[27 * mm, 37 * mm, 25 * mm, 47 * mm])
    table.setStyle(_table_style(header=False))
    return table


def _valuation_table(metrics: dict[str, float | str]) -> Table:
    forecast = metrics["forecast"]
    forecast_2026 = forecast[forecast["year"].eq("2026E")].iloc[0]
    data = [
        ["항목", "주요 가정", "가중치", "주당가치"],
        ["2026E 실적", f"매출 {forecast_2026['revenue'] / 1e12:.2f}조 / OPM {forecast_2026['op_margin'] * 100:.1f}%", "-", f"EPS {_krw(metrics['forward_eps'])}"],
        ["PER", f"2026E EPS × {metrics['target_per']:.1f}x", "60%", _krw(metrics["per_value"])],
        ["PBR", f"2026E BPS × {metrics['target_pbr']:.1f}x", "25%", _krw(metrics["pbr_value"])],
        ["DCF", "COE 9.5%, g 2.5%, FCFE proxy", "15%", _krw(metrics["dcf_value"])],
        ["Target", "반올림 목표주가", "-", _krw(metrics["target_price"])],
    ]
    table = Table(data, colWidths=[27 * mm, 45 * mm, 31 * mm, 42 * mm])
    table.setStyle(_table_style(header=True))
    return table


def _sensitivity_table(metrics: dict[str, float | str]) -> Table:
    eps = metrics["forward_eps"]
    multiples = [23, 25, 27, 29, 31]
    data = [["Target PER", "23x", "25x", "27x", "29x", "31x"]]
    data.append(["TP", *[_krw(round((eps * multiple) / 10_000) * 10_000) for multiple in multiples]])
    table = Table(data, colWidths=[26 * mm, 22 * mm, 22 * mm, 22 * mm, 22 * mm, 22 * mm])
    table.setStyle(_table_style(header=True))
    return table


def _dart_table(metrics: dict[str, float | str], dart_summary: dict) -> Table:
    report = dart_summary.get("latest_periodic_report", {})
    company = dart_summary.get("company", {})
    q1_revenue = metrics["dart_q1_revenue"] / 1e12 if metrics["dart_q1_revenue"] else 0
    q1_op = metrics["dart_q1_op_income"] / 1e8 if metrics["dart_q1_op_income"] else 0
    data = [
        ["항목", "OpenDART 확인 내용"],
        ["최근 공시", f"{report.get('report_nm', 'N/A')} / 접수일 {report.get('rcept_dt', 'N/A')}"],
        ["사업 구조", "전력기기·전력시스템·자동화, HVDC·Smart Grid·ESS·데이터센터 전력 인프라"],
        ["1Q26 실적", f"연결 매출 {q1_revenue:.2f}조원 / 영업이익 {q1_op:.0f}억원"],
        ["성장 근거", "2025년 데이터센터 관련 매출 약 5,468억원, 부산 초고압 변압기 증설 1,008억원"],
        ["수주 근거", "동해안-동서울 HVDC 5,610억원, 북미 신재생 초고압변압기 4,598억원, Big Tech Data Center"],
        ["기업개황", f"대표 {company.get('ceo_nm', 'N/A')} / 결산월 {company.get('acc_mt', '12')}월 / 산업코드 {company.get('induty_code', 'N/A')}"],
    ]
    table = Table(data, colWidths=[29 * mm, 116 * mm])
    table.setStyle(_table_style(header=True))
    return table


def _peer_table(peers: pd.DataFrame) -> Table:
    data = [["기업", "매출(조)", "OPM", "ROE", "현 PER", "현 PBR", "매출성장"]]
    for _, row in peers.iterrows():
        data.append(
            [
                row["peer_name"],
                f"{row['revenue_tn']:.2f}",
                f"{row['op_margin_pct']:.1f}%",
                f"{row['roe_pct']:.1f}%",
                f"{row['current_per']:.1f}x",
                f"{row['current_pbr']:.2f}x",
                _pct(row["sales_growth"]),
            ]
        )
    table = Table(data, colWidths=[31 * mm, 20 * mm, 18 * mm, 18 * mm, 18 * mm, 18 * mm, 22 * mm])
    table.setStyle(_table_style(header=True))
    return table


def _table_style(header: bool) -> TableStyle:
    commands = [
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), 7.2),
        ("LEADING", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D8DEE6")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if header:
        commands += [
            ("BACKGROUND", (0, 0), (-1, 0), BRAND),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ]
    else:
        commands += [
            ("BACKGROUND", (0, 0), (0, -1), LIGHT),
            ("BACKGROUND", (2, 0), (2, -1), LIGHT),
            ("TEXTCOLOR", (0, 0), (0, -1), BRAND),
            ("TEXTCOLOR", (2, 0), (2, -1), BRAND),
        ]
    return TableStyle(commands)


def _two_column_charts(left: Drawing, right: Drawing) -> Table:
    table = Table([[left, right]], colWidths=[88 * mm, 88 * mm])
    table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return table


def _revenue_profit_chart(fundamentals: pd.DataFrame) -> Drawing:
    years = [str(int(year)) for year in fundamentals["fiscal_year"].tail(6)]
    revenue = (fundamentals["revenue"].tail(6) / 1e12).round(2).tolist()
    op = (fundamentals["operating_income"].tail(6) / 1e11).round(2).tolist()
    return _bar_line_chart(
        "매출(조원) & 영업이익(천억원)",
        years,
        revenue,
        op,
        max(max(revenue), max(op)) * 1.25,
    )


def _margin_roe_chart(fundamentals: pd.DataFrame) -> Drawing:
    years = [str(int(year)) for year in fundamentals["fiscal_year"].tail(6)]
    opm = (fundamentals["operating_margin"].tail(6) * 100).round(1).tolist()
    roe = (fundamentals["roe"].tail(6) * 100).round(1).tolist()
    return _two_line_chart("OPM & ROE (%)", years, opm, roe, 0, max(max(opm), max(roe)) * 1.25)


def _price_relative_chart(price: pd.DataFrame, kodex: pd.DataFrame) -> Drawing:
    start = pd.Timestamp("2023-01-02")
    lhs = price[price["date"].ge(start)][["date", "adj_close"]].copy()
    rhs = kodex[kodex["date"].ge(start)][["date", "adj_close"]].copy()
    merged = lhs.merge(rhs, on="date", suffixes=("_ls", "_kodex")).dropna()
    merged["half"] = merged["date"].dt.year.astype(str).str[2:] + "H" + merged["date"].dt.month.map(lambda month: "1" if month <= 6 else "2")
    merged = merged.groupby("half", as_index=False).tail(1)
    ls = (merged["adj_close_ls"] / merged["adj_close_ls"].iloc[0] * 100).round(1).tolist()
    kd = (merged["adj_close_kodex"] / merged["adj_close_kodex"].iloc[0] * 100).round(1).tolist()
    labels = merged["half"].tolist()
    return _two_line_chart("주가 상대성과(2023=100)", labels, ls, kd, min(min(ls), min(kd)) * 0.9, max(max(ls), max(kd)) * 1.1)


def _factor_signal_chart(factors: pd.DataFrame) -> Drawing:
    latest = factors.tail(12).copy()
    labels = [d.strftime("%m") for d in latest["signal_date"]]
    composite = latest["composite_score"].round(2).tolist()
    ml = latest["ml_score"].round(2).tolist()
    low = min(min(composite), min(ml), -1.5)
    high = max(max(composite), max(ml), 2.5)
    return _two_line_chart("퀀트 점수: Composite vs ML", labels, composite, ml, low, high)


def _bar_line_chart(title: str, labels: list[str], bars: list[float], line_values: list[float], high: float) -> Drawing:
    width, height = 82 * mm, 54 * mm
    drawing = Drawing(width, height)
    _chart_frame(drawing, title, width, height)
    chart = VerticalBarChart()
    chart.x = 10 * mm
    chart.y = 9 * mm
    chart.width = 58 * mm
    chart.height = 33 * mm
    chart.data = [bars]
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = high
    chart.valueAxis.valueStep = high / 4
    chart.categoryAxis.categoryNames = labels
    chart.bars[0].fillColor = ACCENT
    chart.categoryAxis.labels.fontName = FONT_NAME
    chart.categoryAxis.labels.fontSize = 6
    chart.valueAxis.labels.fontName = FONT_NAME
    chart.valueAxis.labels.fontSize = 6
    drawing.add(chart)
    _add_polyline(drawing, line_values, 10 * mm, 9 * mm, 58 * mm, 33 * mm, 0, high, GREEN)
    return drawing


def _two_line_chart(
    title: str,
    labels: list[str],
    first: list[float],
    second: list[float],
    low: float,
    high: float,
) -> Drawing:
    width, height = 82 * mm, 54 * mm
    drawing = Drawing(width, height)
    _chart_frame(drawing, title, width, height)
    chart = HorizontalLineChart()
    chart.x = 10 * mm
    chart.y = 9 * mm
    chart.width = 58 * mm
    chart.height = 33 * mm
    chart.data = [first, second]
    chart.valueAxis.valueMin = low
    chart.valueAxis.valueMax = high
    chart.valueAxis.valueStep = (high - low) / 4
    chart.categoryAxis.categoryNames = labels
    chart.lines[0].strokeColor = ACCENT
    chart.lines[1].strokeColor = GREEN
    chart.lines[0].strokeWidth = 1.7
    chart.lines[1].strokeWidth = 1.5
    chart.categoryAxis.labels.fontName = FONT_NAME
    chart.categoryAxis.labels.fontSize = 5.5
    chart.valueAxis.labels.fontName = FONT_NAME
    chart.valueAxis.labels.fontSize = 6
    drawing.add(chart)
    return drawing


def _chart_frame(drawing: Drawing, title: str, width: float, height: float) -> None:
    drawing.add(Rect(0, 0, width, height, strokeColor=colors.HexColor("#D8DEE6"), fillColor=colors.white))
    drawing.add(Rect(0, height - 8 * mm, width, 8 * mm, strokeColor=BRAND, fillColor=BRAND))
    drawing.add(String(4 * mm, height - 5.2 * mm, title, fontName=FONT_NAME, fontSize=7.5, fillColor=colors.white))


def _add_polyline(
    drawing: Drawing,
    values: list[float],
    x: float,
    y: float,
    width: float,
    height: float,
    low: float,
    high: float,
    color,
) -> None:
    if len(values) < 2:
        return
    points = []
    for index, value in enumerate(values):
        px = x + width * index / (len(values) - 1)
        py = y + height * (value - low) / (high - low)
        points.append((px, py))
    for start, end in zip(points[:-1], points[1:]):
        drawing.add(Line(start[0], start[1], end[0], end[1], strokeColor=color, strokeWidth=1.6))


def _bullet(text: str, styles) -> Paragraph:
    return Paragraph(f"- {text}", styles["Bullet"])


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont(FONT_NAME, 7)
    canvas.setFillColor(GREY)
    canvas.drawString(14 * mm, 8 * mm, "Recruiting assignment sample | Data: OpenDART, TS2000, KIS API, internal quant model")
    canvas.drawRightString(196 * mm, 8 * mm, f"{doc.page}")
    canvas.restoreState()


def _build_markdown(metrics, fundamentals, factors, peers, dart_summary) -> str:
    latest = fundamentals.iloc[-1]
    report = dart_summary.get("latest_periodic_report", {})
    return f"""# LS ELECTRIC (010120) 기업분석

투자의견: {metrics['rating']} / 목표주가: {_krw(metrics['target_price'])} / 상승여력: {_pct(metrics['upside'])}

## 투자요약

- AI 데이터센터와 전력망 투자가 전력기기 수요를 구조적으로 자극하고 있다.
- OpenDART 연결 기준 2025년 매출은 {metrics['revenue_tn']:.2f}조원, 영업이익은 {metrics['op_income_100m']:.0f}억원, 영업이익률은 {_pct(metrics['op_margin'])}다.
- 최신 DART 정기공시는 {report.get('report_nm', 'N/A')}이며, 2026년 1분기 연결 매출은 {metrics['dart_q1_revenue'] / 1e12:.2f}조원, 영업이익은 {metrics['dart_q1_op_income'] / 1e8:.0f}억원이다.
- DART 공시상 2025년 데이터센터 관련 매출 약 5,468억원, 동해안-동서울 HVDC 5,610억원, 북미 신재생 초고압변압기 4,598억원, Big Tech Data Center 프로젝트가 확인된다.
- 목표주가는 2026E EPS {_krw(metrics['forward_eps'])}에 목표 PER {metrics['target_per']:.1f}배, 2026E BPS {_krw(metrics['forward_bps'])}에 목표 PBR {metrics['target_pbr']:.1f}배, FCFE proxy DCF를 가중 평균해 산출했다.
- 현 주가 기준 PER은 {metrics['current_per']:.1f}배, PBR은 {metrics['current_pbr']:.2f}배다.
- 자체 KOSPI200 코어-위성 모델 기준 최신 랭킹은 {metrics['factor_rank']:.0f}위로 Top 30 바로 아래다.

## 결론

LS ELECTRIC은 AI 전력 인프라 사이클이 재무제표와 DART 공시 양쪽에서 확인되는 기업이다. 목표주가 기준 상승여력이 {_pct(metrics['upside'])}로 남아 있어 매수 의견을 제시하되, 신규 수주, 영업이익률, ROE, 퀀트 랭킹의 지속 확인이 필요하다.

PDF 리포트: `outputs/reports/recruiting/Assignment1_LS_ELECTRIC_Analyst_Report.pdf`
"""


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _krw(value: float) -> str:
    return f"{value:,.0f}원"


if __name__ == "__main__":
    md_path, pdf_path = generate_ls_electric_report()
    print(f"Saved {md_path}")
    print(f"Saved {pdf_path}")
