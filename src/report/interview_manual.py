"""Generate an interview-ready project explanation manual."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from src.report.report_generator import _attach_names, _build_name_master

KOREAN_FONT = "AppleGothic"
KOREAN_FONT_PATH = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"


def generate_interview_manual(
    *,
    markdown_path: str | Path = "outputs/reports/KOSPI200_Quant_Project_Interview_Manual.md",
    pdf_path: str | Path = "outputs/reports/KOSPI200_Quant_Project_Interview_Manual.pdf",
) -> tuple[Path, Path]:
    """Create a Korean project manual suitable for quant research interviews."""
    data = _load_manual_data()
    markdown = _build_markdown(data)

    markdown_path = Path(markdown_path)
    pdf_path = Path(pdf_path)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(markdown, encoding="utf-8")
    _build_pdf(data, pdf_path)
    return markdown_path, pdf_path


def _load_manual_data() -> dict[str, pd.DataFrame]:
    name_master = _build_name_master()
    price_summary = pd.read_csv("outputs/tables/price_data_summary.csv", dtype={"ticker": "string"})
    comparison = pd.read_csv("outputs/tables/backtest_strategy_comparison.csv")
    integrated_scores = pd.read_csv(
        "data/features/integrated_factor_scores.csv",
        dtype={"ticker": "string"},
        parse_dates=["signal_date"],
    )
    price_scores = pd.read_csv(
        "data/features/price_factor_scores.csv",
        dtype={"ticker": "string"},
        parse_dates=["signal_date"],
    )
    coverage = pd.read_csv("outputs/tables/integrated_factor_score_coverage.csv")
    rank_ic_summary = _read_optional("outputs/tables/rank_ic_summary.csv")
    quintile_summary = _read_optional("outputs/tables/quintile_return_summary.csv")
    candidates = _read_optional("outputs/portfolios/latest_recommendation_candidates.csv")

    latest_integrated = integrated_scores[
        integrated_scores["signal_date"] == integrated_scores["signal_date"].max()
    ].sort_values("composite_score", ascending=False)
    latest_price = price_scores[
        price_scores["signal_date"] == price_scores["signal_date"].max()
    ].sort_values("composite_score", ascending=False)

    return {
        "name_master": name_master,
        "price_summary": _attach_names(price_summary, name_master),
        "comparison": comparison,
        "latest_integrated": _attach_names(latest_integrated, name_master),
        "latest_price": _attach_names(latest_price, name_master),
        "coverage": coverage,
        "rank_ic_summary": rank_ic_summary,
        "quintile_summary": quintile_summary,
        "candidates": candidates,
    }


def _build_markdown(data: dict[str, pd.DataFrame]) -> str:
    price_summary = data["price_summary"]
    comparison = data["comparison"]
    latest_integrated = data["latest_integrated"]
    latest_price = data["latest_price"]
    coverage = data["coverage"]
    rank_ic_summary = data["rank_ic_summary"]
    quintile_summary = data["quintile_summary"]
    candidates = data["candidates"]

    price_range = f"{price_summary['start_date'].min()}~{price_summary['end_date'].max()}"
    ticker_count = int(price_summary["ticker"].nunique())
    row_count = int(price_summary["rows"].sum())

    kodex = comparison[comparison["benchmark"].eq("kodex200_etf_069500")].copy()
    strategy_cols = [
        "strategy",
        "benchmark",
        "total_return",
        "cagr",
        "annualized_volatility",
        "sharpe",
        "max_drawdown",
        "benchmark_total_return",
        "active_total_return",
        "information_ratio",
    ]
    top_cols = [
        "ticker",
        "name",
        "signal_date",
        "value_score",
        "quality_score",
        "momentum_score",
        "low_volatility_score",
        "composite_score",
    ]
    price_cols = [
        "ticker",
        "name",
        "signal_date",
        "momentum_score",
        "low_volatility_score",
        "composite_score",
    ]

    return (
        "# KOSPI200 Quant Factor Model Project - Interview Manual\n\n"
        "## 1. 프로젝트 한 줄 요약\n\n"
        "KOSPI200 유니버스에서 Value, Quality, Momentum, Low Volatility 팩터를 계산하고, "
        "월말 리밸런싱 Top 30 동일가중 전략으로 백테스트한 뒤 KODEX 200 ETF 대비 성과를 검증한 프로젝트입니다.\n\n"
        "## 2. 리서치 질문\n\n"
        "- 한국 대형주 시장에서 전통 팩터가 향후 수익률과 위험 조정 성과를 설명하는가?\n"
        "- 단순하고 설명 가능한 composite score만으로 시장 대비 초과성과를 만들 수 있는가?\n"
        "- 팩터 전략의 장점과 한계가 거래비용, 회전율, MDD 관점에서 어떻게 드러나는가?\n\n"
        "## 3. 데이터와 커버리지\n\n"
        f"- 가격 데이터: KIS API, {ticker_count}개 종목, {price_range}, {row_count:,} rows\n"
        "- 재무 데이터: TS2000 원천 엑셀 표준화, 2013-03~2025-06 회계기간\n"
        "- 벤치마크: KODEX 200 ETF(069500), KOSPI200 대용 시장 비교 기준\n"
        "- 유니버스: 현재 KOSPI200 구성종목 fallback. 구성종목 이력이 아니므로 survivorship bias를 명시해야 합니다.\n\n"
        "## 4. 프로젝트 구조\n\n"
        "- `src/data`: KIS 가격 수집, TS2000 표준화, 유니버스/벤치마크 로더\n"
        "- `src/factors`: Value, Quality, Momentum, Low Volatility, 통합 composite score\n"
        "- `src/backtest`: 월말 리밸런싱 엔진, 성과지표, drawdown 계산\n"
        "- `src/portfolio`: Top N 포트폴리오와 제약조건\n"
        "- `src/report`: 리포트와 면접용 설명서 생성\n"
        "- `outputs`: 백테스트 결과, 비교표, PDF/Markdown 리포트\n\n"
        "## 5. 절차\n\n"
        "1. KIS API로 종목별 일별 OHLCV를 수집하고 표준 가격 스키마로 저장했습니다.\n"
        "2. TS2000 재무 엑셀을 ticker, fiscal_period, available_date, PBR/PER/ROE/ROA 등으로 표준화했습니다.\n"
        "3. 재무 팩터는 available_date 기준으로만 사용해 look-ahead bias를 줄였습니다.\n"
        "4. 가격 팩터는 월말 가격으로 6개월 모멘텀, 12개월-1개월 모멘텀, 1년 변동성, 1년 MDD를 계산했습니다.\n"
        "5. 각 월말 signal_date에서 최신 재무 팩터를 as-of join으로 붙여 통합 멀티팩터 점수를 만들었습니다.\n"
        "6. composite score 상위 30종목을 동일가중으로 보유하고 다음 월말까지 일별 수익률을 추적했습니다.\n"
        "7. 리밸런싱 회전율에 10bp 거래비용을 차감했습니다.\n"
        "8. 내부 동일가중 벤치마크와 KODEX 200 ETF 벤치마크를 모두 계산했습니다.\n\n"
        "## 6. 팩터 정의와 해석\n\n"
        "- Value: PER/PBR이 낮을수록 높게 점수화했습니다. 저평가 프리미엄을 포착하려는 목적입니다.\n"
        "- Quality: ROE/ROA가 높고 부채비율이 낮으며 현금흐름 질이 좋은 기업을 선호합니다.\n"
        "- Momentum: 최근 상승 추세가 유지되는 종목을 선호하되, 단기 반전 영향을 줄이기 위해 12개월 수익률에서 최근 1개월을 제외합니다.\n"
        "- Low Volatility: 변동성과 최근 1년 MDD가 낮은 종목을 선호해 포트폴리오 방어력을 높입니다.\n"
        "- Composite: Quality 30%, Value 25%, Momentum 25%, Low Volatility 20% 고정 가중입니다. 결측 팩터는 해당 row에서 제외하고 가중치를 재정규화합니다.\n\n"
        "## 7. 성과 해석\n\n"
        f"{_dataframe_to_markdown(_format_strategy_table(kodex[strategy_cols]))}\n\n"
        "해석 포인트:\n\n"
        "- 가격 팩터 전략은 KODEX 200 대비 초과 총수익률이 더 크게 나타났습니다. 2023~2025년의 추세장 성격에서 Momentum과 Low Volatility 조합이 유효했을 가능성이 있습니다.\n"
        "- 통합 멀티팩터 전략은 MDD와 변동성이 낮아 방어력이 개선됐지만, KODEX 200 대비 초과성과는 더 작았습니다. 재무 팩터가 고성장/모멘텀 장세에서 성과를 일부 희석했을 수 있습니다.\n"
        "- 국면 대응 방어형 전략은 하락장과 스트레스장에서 주식 노출도를 낮추고 Quality/Low Volatility 비중을 높였습니다. 총수익률은 낮아졌지만 연변동성이 가장 낮아져 위험관리형 전략으로 해석할 수 있습니다.\n"
        "- 이 결과는 전략이 완성됐다는 뜻이 아니라, 팩터별 기여도와 시장 국면별 성과를 추가 검증할 출발점입니다.\n\n"
        "## 8. 최신 통합 팩터 Top 10\n\n"
        f"{_dataframe_to_markdown(_round_table(latest_integrated[top_cols].head(10)))}\n\n"
        "## 9. 최신 가격 팩터 Top 10\n\n"
        f"{_dataframe_to_markdown(_round_table(latest_price[price_cols].head(10)))}\n\n"
        "## 10. 데이터 품질과 한계\n\n"
        f"{_dataframe_to_markdown(_round_table(coverage.tail(5)))}\n\n"
        "## 11. 추천 후보와 검증 근거\n\n"
        "최신 시점 기준 Top 30은 직접적인 매수 추천이 아니라, 팩터 기반 model portfolio candidate입니다. "
        "따라서 추천 리스트는 반드시 Rank IC와 quintile spread 같은 검증 결과와 함께 해석해야 합니다.\n\n"
        "### Rank IC Summary\n\n"
        f"{_dataframe_to_markdown(_round_table(rank_ic_summary))}\n\n"
        "### Quintile Return Summary\n\n"
        f"{_dataframe_to_markdown(_round_table(quintile_summary))}\n\n"
        "### Latest Candidate Top 10\n\n"
        f"{_dataframe_to_markdown(_round_table(_candidate_display(candidates).head(10)))}\n\n"
        "- 현재 KOSPI200 구성종목을 과거 전체 기간에 적용했기 때문에 survivorship bias가 있습니다.\n"
        "- TS2000 공시일이 없어서 결산월 이후 3개월 available_date 가정을 사용했습니다.\n"
        "- KODEX 200 ETF는 지수 자체가 아니라 ETF이므로 보수, 추적오차, 분배금 처리 차이가 있습니다.\n"
        "- 백테스트는 Top 30 동일가중 중심이며, 실제 운용에서는 유동성, 세금, 호가충격, 섹터 cap, 종목 cap을 더 엄격히 반영해야 합니다.\n\n"
        "## 12. 면접에서 강조할 포인트\n\n"
        "- 모델 복잡도를 높이기보다 데이터 누수 방지, 재현 가능한 파이프라인, 설명 가능한 팩터 정의에 집중했습니다.\n"
        "- 재무 팩터와 가격 팩터의 시점 정합성을 맞추기 위해 as-of join을 사용했습니다.\n"
        "- 단순 총수익률보다 MDD, 회전율, IR, 벤치마크 대비 초과성과를 함께 보았습니다.\n"
        "- 결과가 좋은 부분뿐 아니라 survivorship bias, 벤치마크 한계, 기간 한계를 명시했습니다.\n\n"
        "## 13. 다음 개선 계획\n\n"
        "1. KRX/KOSCOM 기반 KOSPI200 구성종목 이력을 확보해 point-in-time universe로 교체합니다.\n"
        "2. 2015년 이후 가격 데이터를 확장해 장기 국면별 검증을 수행합니다.\n"
        "3. 월별 IC, Rank IC, quintile spread를 추가해 팩터 자체의 예측력을 검증합니다.\n"
        "4. 거래대금 필터, 섹터/종목 cap, 리밸런싱 비용 민감도를 백테스트 엔진에 반영합니다.\n"
        "5. 팩터 가중치를 고정값에서 rolling IC 또는 regime-aware 방식으로 개선합니다.\n"
    )


def _build_pdf(data: dict[str, pd.DataFrame], pdf_path: Path) -> None:
    pdfmetrics.registerFont(TTFont(KOREAN_FONT, KOREAN_FONT_PATH))
    styles = getSampleStyleSheet()
    for style in styles.byName.values():
        style.fontName = KOREAN_FONT
        style.wordWrap = "CJK"
    styles["Title"].fontSize = 18
    styles["Heading2"].fontSize = 13
    styles["BodyText"].fontSize = 9
    styles["BodyText"].leading = 13

    story = [
        Paragraph("KOSPI200 Quant Factor Model Project", styles["Title"]),
        Spacer(1, 0.08 * inch),
        Paragraph("퀀트리서치 면접용 프로젝트 설명서", styles["Heading2"]),
        Spacer(1, 0.18 * inch),
    ]

    sections = _manual_sections(data)
    for index, (title, body, table) in enumerate(sections, start=1):
        if index in {5, 9}:
            story.append(PageBreak())
        story.append(Paragraph(title, styles["Heading2"]))
        for paragraph in body:
            story.append(Paragraph(paragraph, styles["BodyText"]))
            story.append(Spacer(1, 0.06 * inch))
        if table is not None:
            story.append(_pdf_table(table))
            story.append(Spacer(1, 0.12 * inch))
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=0.45 * inch,
        leftMargin=0.45 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )
    doc.build(story)


def _manual_sections(data: dict[str, pd.DataFrame]) -> list[tuple[str, list[str], pd.DataFrame | None]]:
    price_summary = data["price_summary"]
    comparison = data["comparison"]
    latest_integrated = data["latest_integrated"]
    latest_price = data["latest_price"]
    coverage = data["coverage"]
    rank_ic_summary = data["rank_ic_summary"]
    quintile_summary = data["quintile_summary"]
    candidates = data["candidates"]
    price_range = f"{price_summary['start_date'].min()}~{price_summary['end_date'].max()}"
    row_count = int(price_summary["rows"].sum())
    kodex = comparison[comparison["benchmark"].eq("kodex200_etf_069500")].copy()

    strategy_cols = [
        "strategy",
        "total_return",
        "cagr",
        "sharpe",
        "max_drawdown",
        "benchmark_total_return",
        "active_total_return",
        "information_ratio",
    ]
    top_cols = [
        "ticker",
        "name",
        "value_score",
        "quality_score",
        "momentum_score",
        "low_volatility_score",
        "composite_score",
    ]
    price_cols = ["ticker", "name", "momentum_score", "low_volatility_score", "composite_score"]

    return [
        (
            "1. 프로젝트 목적",
            [
                "KOSPI200 대형주를 대상으로 Value, Quality, Momentum, Low Volatility 팩터가 시장 대비 초과성과를 만들 수 있는지 검증했습니다.",
                "면접에서 강조할 핵심은 복잡한 모델보다 데이터 누수 방지, 재현 가능한 파이프라인, 설명 가능한 투자 가설입니다.",
            ],
            None,
        ),
        (
            "2. 데이터와 커버리지",
            [
                f"KIS API 가격 데이터는 200개 종목, {price_range}, 총 {row_count:,} rows입니다.",
                "재무 데이터는 TS2000 원천 엑셀을 표준 스키마로 변환했고, 공시일 대용으로 결산월 이후 3개월 available_date를 적용했습니다.",
                "시장 비교 기준은 KODEX 200 ETF(069500)입니다. 지수 자체가 아닌 ETF이므로 추적오차와 비용 차이는 한계로 명시합니다.",
            ],
            None,
        ),
        (
            "3. 파이프라인 구조",
            [
                "src/data는 KIS 가격 수집, TS2000 표준화, 벤치마크 로더를 담당합니다.",
                "src/factors는 재무 팩터와 가격 팩터, integrated composite score를 계산합니다.",
                "src/backtest는 월말 리밸런싱, 거래비용, 성과지표, drawdown을 계산합니다.",
                "src/report는 제출용 리포트와 이 면접용 설명서를 생성합니다.",
            ],
            None,
        ),
        (
            "4. 모델링 절차",
            [
                "월말 signal_date를 기준으로 가격 팩터를 계산하고, 해당 시점에 이미 사용 가능했던 최신 재무 팩터만 as-of join했습니다.",
                "Composite score는 Quality 30%, Value 25%, Momentum 25%, Low Volatility 20%이며, 결측 팩터는 row별로 가중치를 재정규화합니다.",
                "상위 30종목을 동일가중으로 보유하고 다음 월말까지 일별 수익률을 추적했습니다. 리밸런싱 회전율에 10bp 거래비용을 차감했습니다.",
            ],
            None,
        ),
        (
            "5. KODEX 200 기준 성과",
            [
                "가격 팩터 전략은 Momentum/Low Volatility 중심이라 추세장 구간에서 초과성과가 뚜렷했습니다.",
                "통합 멀티팩터 전략은 재무 안정성을 반영해 MDD와 변동성이 완화됐지만, KODEX 200 대비 초과성과는 더 작았습니다.",
                "국면 대응 방어형 전략은 bull/neutral/bear/stress 국면에 따라 팩터 가중치와 주식 노출도를 조정했습니다.",
            ],
            _format_strategy_table(kodex[strategy_cols]),
        ),
        (
            "6. 최신 통합 팩터 Top 10",
            [
                "아래 표는 최신 signal_date 기준 integrated composite score 상위 종목입니다. 종목명은 TS2000 한국어 회사명 master를 우선 사용했습니다.",
            ],
            _round_table(latest_integrated[top_cols].head(10)),
        ),
        (
            "7. 최신 가격 팩터 Top 10",
            [
                "가격 팩터만 보면 최근 수익률과 변동성 방어력이 함께 좋은 종목이 상위에 배치됩니다.",
            ],
            _round_table(latest_price[price_cols].head(10)),
        ),
        (
            "8. 데이터 품질 체크",
            [
                "최근 월말 기준 integrated composite score 결측은 0건입니다. 일부 신규 상장 또는 데이터가 짧은 종목은 재무 팩터 결측이 남을 수 있습니다.",
            ],
            _round_table(coverage.tail(5)),
        ),
        (
            "9. 추천 후보와 검증 근거",
            [
                "최신 Top 30은 직접적인 매수 추천이 아니라 factor-based model portfolio candidate입니다.",
                "Rank IC는 팩터 점수와 다음 1개월 초과수익률의 월별 순위상관입니다. Quintile spread는 상위 점수 그룹이 하위 점수 그룹보다 얼마나 나았는지를 보여줍니다.",
            ],
            _round_table(rank_ic_summary),
        ),
        (
            "10. Quintile Spread",
            [
                "Composite score 기준 상위 quintile과 하위 quintile의 다음 1개월 초과수익률 차이를 확인합니다.",
            ],
            _round_table(quintile_summary),
        ),
        (
            "11. 최신 추천 후보 Top 10",
            [
                "아래 목록은 최신 signal_date 기준 정량 스크리닝 결과입니다. 실제 투자 판단에는 추가 리스크 점검과 포트폴리오 제약조건이 필요합니다.",
            ],
            _round_table(_candidate_display(candidates).head(10)),
        ),
        (
            "12. 결과 해석",
            [
                "이 결과는 특정 기간에서 전통 팩터 조합이 시장 대비 의미 있는 성과를 냈다는 초기 증거입니다.",
                "다만 2023~2025년이라는 짧은 기간, 현재 구성종목 기반 유니버스, ETF 벤치마크의 한계를 함께 제시해야 리서치 신뢰도가 높아집니다.",
                "면접에서는 좋은 성과 숫자보다 왜 이런 결과가 나왔는지, 어떤 편향을 통제했고 무엇을 다음에 개선할지 설명하는 것이 중요합니다.",
            ],
            None,
        ),
        (
            "13. 다음 개선 계획",
            [
                "Point-in-time KOSPI200 구성종목 이력을 확보해 survivorship bias를 줄입니다.",
                "2015년 이후 장기 가격 데이터를 추가해 국면별 성과와 팩터 안정성을 확인합니다.",
                "Rank IC, quintile spread, 섹터중립 포트폴리오, 거래비용 민감도 분석을 추가합니다.",
                "고정 가중 composite에서 rolling IC 기반 동적 가중 또는 regime-aware weighting으로 확장할 수 있습니다.",
            ],
            None,
        ),
    ]


def _pdf_table(frame: pd.DataFrame) -> Table:
    styles = getSampleStyleSheet()
    for style in styles.byName.values():
        style.fontName = KOREAN_FONT
        style.wordWrap = "CJK"
    cell_style = styles["BodyText"]
    cell_style.fontSize = 6.5
    cell_style.leading = 8
    table_data = [[Paragraph(str(column), cell_style) for column in frame.columns]]
    for _, row in frame.iterrows():
        table_data.append([Paragraph("" if pd.isna(value) else str(value), cell_style) for value in row])
    table = Table(table_data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#263238")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#b0bec5")),
                ("FONTNAME", (0, 0), (-1, -1), KOREAN_FONT),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def _format_strategy_table(frame: pd.DataFrame) -> pd.DataFrame:
    formatted = frame.copy()
    strategy_names = {
        "price_momentum_low_volatility": "가격 팩터",
        "integrated_value_quality_momentum_low_volatility": "통합 멀티팩터",
        "regime_aware_defensive_multifactor": "국면 대응 방어형",
    }
    if "strategy" in formatted.columns:
        formatted["strategy"] = formatted["strategy"].map(strategy_names).fillna(formatted["strategy"])
    for column in [
        "total_return",
        "cagr",
        "annualized_volatility",
        "max_drawdown",
        "benchmark_total_return",
        "active_total_return",
    ]:
        if column in formatted.columns:
            formatted[column] = formatted[column].map(lambda value: f"{value:.2%}")
    for column in ["sharpe", "information_ratio"]:
        if column in formatted.columns:
            formatted[column] = formatted[column].map(lambda value: f"{value:.2f}")
    return formatted.rename(
        columns={
            "strategy": "전략",
            "benchmark": "벤치마크",
            "days": "일수",
            "total_return": "총수익률",
            "cagr": "CAGR",
            "annualized_volatility": "연변동성",
            "sharpe": "Sharpe",
            "max_drawdown": "MDD",
            "benchmark_total_return": "벤치마크수익률",
            "active_total_return": "초과수익률",
            "information_ratio": "IR",
        }
    )


def _round_table(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    rounded = frame.copy()
    for column in rounded.columns:
        if pd.api.types.is_datetime64_any_dtype(rounded[column]):
            rounded[column] = rounded[column].dt.strftime("%Y-%m-%d")
        elif pd.api.types.is_float_dtype(rounded[column]):
            rounded[column] = rounded[column].map(lambda value: "" if pd.isna(value) else f"{value:.4f}")
    return rounded.rename(
        columns={
            "ticker": "종목코드",
            "name": "종목명",
            "signal_date": "신호일",
            "value_score": "Value",
            "quality_score": "Quality",
            "momentum_score": "Momentum",
            "low_volatility_score": "LowVol",
            "composite_score": "Composite",
            "rows": "행수",
            "tickers": "종목수",
            "value_score_missing": "Value결측",
            "quality_score_missing": "Quality결측",
            "momentum_score_missing": "Momentum결측",
            "low_volatility_score_missing": "LowVol결측",
            "composite_score_missing": "Composite결측",
            "average_weight_coverage": "평균가중커버리지",
            "factor": "팩터",
            "target": "타깃",
            "months": "월수",
            "mean_rank_ic": "평균RankIC",
            "median_rank_ic": "중앙RankIC",
            "positive_ic_rate": "IC양수비율",
            "mean_n": "평균표본수",
            "score": "점수",
            "quantile": "분위",
            "mean_forward_return": "평균선행수익률",
            "median_forward_return": "중앙선행수익률",
            "rank": "순위",
            "candidate_label": "후보유형",
            "recommendation_note": "선정근거",
        }
    )


def _candidate_display(candidates: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "rank",
        "ticker",
        "name",
        "signal_date",
        "composite_score",
        "recommendation_note",
    ]
    existing = [column for column in columns if column in candidates.columns]
    return candidates[existing].copy()


def _read_optional(path: str) -> pd.DataFrame:
    file_path = Path(path)
    if not file_path.exists():
        return pd.DataFrame()
    return pd.read_csv(file_path)


def _dataframe_to_markdown(frame: pd.DataFrame) -> str:
    display = frame.copy()
    headers = [str(column) for column in display.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in display.values.tolist():
        lines.append("| " + " | ".join("" if pd.isna(value) else str(value) for value in row) + " |")
    return "\n".join(lines)
