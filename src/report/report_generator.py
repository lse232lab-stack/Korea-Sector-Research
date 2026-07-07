"""Generate project reports from available outputs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.report.charts import save_price_chart

KOREAN_FONT = "AppleGothic"
KOREAN_FONT_PATH = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"


def generate_initial_report(
    *,
    price_summary_path: str | Path = "outputs/tables/price_data_summary.csv",
    price_issues_path: str | Path = "outputs/tables/price_data_issues.csv",
    fundamentals_summary_path: str | Path = "outputs/tables/fundamentals_data_summary.csv",
    fundamentals_coverage_path: str | Path = "outputs/tables/fundamentals_yearly_coverage.csv",
    fundamentals_issues_path: str | Path = "outputs/tables/fundamentals_data_issues.csv",
    factor_coverage_path: str | Path = "outputs/tables/factor_score_coverage.csv",
    portfolio_preview_path: str | Path = "outputs/portfolios/current_model_portfolio_preview.csv",
    price_factor_path: str | Path = "data/features/price_factor_scores.csv",
    price_factor_coverage_path: str | Path = "outputs/tables/price_factor_score_coverage.csv",
    kospi200_portfolio_path: str | Path = "outputs/portfolios/kospi200_model_portfolio_preview.csv",
    kospi200_sector_exposure_path: str | Path = "outputs/tables/kospi200_portfolio_sector_exposure.csv",
    backtest_summary_path: str | Path = "outputs/backtest/backtest_summary.csv",
    backtest_rebalance_log_path: str | Path = "outputs/backtest/backtest_rebalance_log.csv",
    integrated_backtest_summary_path: str | Path = "outputs/backtest_integrated/backtest_summary.csv",
    integrated_backtest_rebalance_log_path: str | Path = "outputs/backtest_integrated/backtest_rebalance_log.csv",
    kodex200_price_backtest_summary_path: str | Path = "outputs/backtest_kodex200/backtest_summary.csv",
    kodex200_integrated_backtest_summary_path: str | Path = "outputs/backtest_integrated_kodex200/backtest_summary.csv",
    kodex200_regime_backtest_summary_path: str | Path = "outputs/backtest_regime_kodex200/backtest_summary.csv",
    markdown_path: str | Path = "outputs/reports/KOSPI200_Factor_Model_Initial_Report.md",
    pdf_path: str | Path = "outputs/reports/KOSPI200_Factor_Model_Initial_Report.pdf",
) -> tuple[Path, Path]:
    """Generate an initial data-ingestion report from current outputs."""
    price_summary = pd.read_csv(price_summary_path, dtype={"ticker": "string"})
    price_issues = pd.read_csv(price_issues_path)
    fundamentals_summary = pd.read_csv(fundamentals_summary_path)
    fundamentals_coverage = pd.read_csv(fundamentals_coverage_path)
    fundamentals_issues = pd.read_csv(fundamentals_issues_path)
    factor_coverage = _read_optional_csv(factor_coverage_path)
    portfolio_preview = _read_optional_csv(
        portfolio_preview_path,
        dtype={"ticker": "string"},
    )
    price_factor_scores = _read_optional_csv(
        price_factor_path,
        dtype={"ticker": "string"},
    )
    price_factor_coverage = _read_optional_csv(price_factor_coverage_path)
    kospi200_portfolio = _read_optional_csv(
        kospi200_portfolio_path,
        dtype={"ticker": "string"},
    )
    kospi200_sector_exposure = _read_optional_csv(kospi200_sector_exposure_path)
    backtest_summary = _read_optional_csv(backtest_summary_path)
    backtest_rebalance_log = _read_optional_csv(backtest_rebalance_log_path)
    integrated_backtest_summary = _read_optional_csv(integrated_backtest_summary_path)
    integrated_backtest_rebalance_log = _read_optional_csv(integrated_backtest_rebalance_log_path)
    kodex200_price_backtest_summary = _read_optional_csv(kodex200_price_backtest_summary_path)
    kodex200_integrated_backtest_summary = _read_optional_csv(
        kodex200_integrated_backtest_summary_path
    )
    kodex200_regime_backtest_summary = _read_optional_csv(kodex200_regime_backtest_summary_path)
    name_master = _build_name_master()
    price_summary = _attach_names(price_summary, name_master)
    price_factor_scores = _attach_names(price_factor_scores, name_master)
    chart_path = save_price_chart()

    markdown_path = Path(markdown_path)
    pdf_path = Path(pdf_path)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    markdown_path.write_text(
        _build_markdown(
            price_summary,
            price_issues,
            fundamentals_summary,
            fundamentals_coverage,
            fundamentals_issues,
            factor_coverage,
            portfolio_preview,
            price_factor_scores,
            price_factor_coverage,
            kospi200_portfolio,
            kospi200_sector_exposure,
            backtest_summary,
            backtest_rebalance_log,
            integrated_backtest_summary,
            integrated_backtest_rebalance_log,
            kodex200_price_backtest_summary,
            kodex200_integrated_backtest_summary,
            kodex200_regime_backtest_summary,
            chart_path,
        ),
        encoding="utf-8",
    )
    _build_pdf(
        price_summary,
        price_issues,
        fundamentals_summary,
        fundamentals_coverage,
        fundamentals_issues,
        factor_coverage,
        portfolio_preview,
        price_factor_scores,
        price_factor_coverage,
        kospi200_portfolio,
        kospi200_sector_exposure,
        backtest_summary,
        backtest_rebalance_log,
        integrated_backtest_summary,
        integrated_backtest_rebalance_log,
        kodex200_price_backtest_summary,
        kodex200_integrated_backtest_summary,
        kodex200_regime_backtest_summary,
        chart_path,
        pdf_path,
    )
    return markdown_path, pdf_path


def generate_pdf_report():
    """Compatibility wrapper for the report pipeline step."""
    return generate_initial_report()


def _build_markdown(
    price_summary: pd.DataFrame,
    price_issues: pd.DataFrame,
    fundamentals_summary: pd.DataFrame,
    fundamentals_coverage: pd.DataFrame,
    fundamentals_issues: pd.DataFrame,
    factor_coverage: pd.DataFrame,
    portfolio_preview: pd.DataFrame,
    price_factor_scores: pd.DataFrame,
    price_factor_coverage: pd.DataFrame,
    kospi200_portfolio: pd.DataFrame,
    kospi200_sector_exposure: pd.DataFrame,
    backtest_summary: pd.DataFrame,
    backtest_rebalance_log: pd.DataFrame,
    integrated_backtest_summary: pd.DataFrame,
    integrated_backtest_rebalance_log: pd.DataFrame,
    kodex200_price_backtest_summary: pd.DataFrame,
    kodex200_integrated_backtest_summary: pd.DataFrame,
    kodex200_regime_backtest_summary: pd.DataFrame,
    chart_path: Path,
) -> str:
    price_issue_text = (
        "No price data issues detected."
        if price_issues.empty
        else _dataframe_to_markdown(price_issues)
    )
    fundamentals_issue_text = (
        "No fundamentals data issues detected."
        if fundamentals_issues.empty
        else _dataframe_to_markdown(fundamentals_issues)
    )
    price_ticker_count = (
        int(price_summary["ticker"].nunique()) if "ticker" in price_summary.columns else 0
    )
    price_start_date = (
        str(price_summary["start_date"].min()) if "start_date" in price_summary.columns else ""
    )
    price_end_date = (
        str(price_summary["end_date"].max()) if "end_date" in price_summary.columns else ""
    )
    price_description = (
        f"현재 가격 데이터는 {price_ticker_count}개 종목의 {price_start_date}~{price_end_date} 일별 데이터입니다."
        if price_ticker_count
        else "현재 가격 데이터 커버리지를 확인할 수 없습니다."
    )
    factor_section = ""
    if not factor_coverage.empty and not portfolio_preview.empty:
        preview_cols = [
            "ticker",
            "name",
            "available_date",
            "fiscal_period",
            "value_score",
            "quality_score",
            "composite_score",
        ]
        factor_section = (
            "## Fundamental Factor Scores\n\n"
            "Value/Quality MVP 팩터 점수를 생성했습니다. Composite score는 아직 Momentum과 "
            "Low Volatility가 빠진 부분 점수이며, 사용 가능한 Value/Quality 가중치만 재정규화했습니다.\n\n"
            "### Factor Coverage\n\n"
            f"{_dataframe_to_markdown(factor_coverage.tail(15))}\n\n"
            "### Current Model Portfolio Preview Top 10\n\n"
            f"{_dataframe_to_markdown(portfolio_preview[preview_cols].head(10))}\n\n"
        )

    kospi200_portfolio_section = ""
    if not kospi200_portfolio.empty:
        equal_weight = kospi200_portfolio[
            kospi200_portfolio["weighting_method"] == "equal_weight"
        ].copy()
        preview_cols = [
            "ticker",
            "name",
            "sector",
            "available_date",
            "value_score",
            "quality_score",
            "composite_score",
            "weight",
        ]
        exposure_text = (
            _dataframe_to_markdown(kospi200_sector_exposure)
            if not kospi200_sector_exposure.empty
            else "No sector exposure table is available."
        )
        kospi200_portfolio_section = (
            "## KOSPI200 Portfolio Preview\n\n"
            "현재 KOSPI200 구성종목 fallback universe를 적용해 Value/Quality MVP Top 30 포트폴리오를 만들었습니다. "
            "동일가중과 스코어가중 모두 단일 종목 5%, 섹터 25% cap을 적용했습니다. "
            "아직 Momentum/Low Volatility, 유동성 필터, 거래비용, 백테스트는 적용 전입니다.\n\n"
            "### Equal-Weight Top 10\n\n"
            f"{_dataframe_to_markdown(equal_weight[preview_cols].head(10))}\n\n"
            "### Sector Exposure\n\n"
            f"{exposure_text}\n\n"
        )

    price_factor_section = ""
    if not price_factor_scores.empty and not price_factor_coverage.empty:
        price_factor_scores["signal_date"] = pd.to_datetime(
            price_factor_scores["signal_date"]
        )
        latest_signal_date = price_factor_scores["signal_date"].max()
        latest_price_factors = price_factor_scores[
            price_factor_scores["signal_date"] == latest_signal_date
        ].sort_values("composite_score", ascending=False)
        latest_ticker_count = int(latest_price_factors["ticker"].nunique())
        latest_price_factors["signal_date"] = latest_price_factors[
            "signal_date"
        ].dt.strftime("%Y-%m-%d")
        price_cols = [
            "ticker",
            "name",
            "signal_date",
            "return_6m",
            "volatility_1y",
            "max_drawdown_1y",
            "momentum_score",
            "low_volatility_score",
            "composite_score",
        ]
        price_factor_section = (
            "## Price Factor Scores\n\n"
            f"Momentum/Low Volatility 가격 팩터를 현재 가격 데이터 {latest_ticker_count}개 종목 기준으로 계산했습니다. "
            "12개월-1개월 모멘텀과 1년 저변동성 팩터를 월말 신호 기준으로 산출했습니다. "
            "더 긴 장기 데이터를 확보하면 IC 검증과 국면별 성과 안정성을 추가 점검합니다.\n\n"
            "### Price Factor Coverage\n\n"
            f"{_dataframe_to_markdown(price_factor_coverage)}\n\n"
            "### Latest Price Factor Snapshot Top 20\n\n"
            f"{_dataframe_to_markdown(latest_price_factors[price_cols].head(20))}\n\n"
        )

    backtest_section = ""
    if not backtest_summary.empty:
        formatted_summary = backtest_summary.copy()
        percent_columns = [
            "total_return",
            "cagr",
            "annualized_volatility",
            "max_drawdown",
            "win_rate",
            "benchmark_total_return",
            "active_total_return",
            "tracking_error",
            "average_turnover",
        ]
        for column in percent_columns:
            if column in formatted_summary.columns:
                formatted_summary[column] = formatted_summary[column].map(
                    lambda value: f"{value:.2%}"
                )
        for column in ["sharpe", "information_ratio"]:
            if column in formatted_summary.columns:
                formatted_summary[column] = formatted_summary[column].map(
                    lambda value: f"{value:.2f}"
                )
        rebalance_text = (
            _dataframe_to_markdown(backtest_rebalance_log.tail(10))
            if not backtest_rebalance_log.empty
            else "No rebalance log is available."
        )
        backtest_section = (
            "## Price Factor Backtest\n\n"
            "월말 Momentum/Low Volatility composite score 상위 30종목을 동일가중으로 보유하고, "
            "다음 월말 리밸런싱 전까지 일별 수익률을 추적했습니다. 거래비용은 리밸런싱 회전율에 "
            "10bp를 적용했습니다. 벤치마크는 보유 가능 종목의 일별 동일가중 수익률입니다.\n\n"
            "### Backtest Summary\n\n"
            f"{_dataframe_to_markdown(formatted_summary)}\n\n"
            "### Recent Rebalance Log\n\n"
            f"{rebalance_text}\n\n"
        )

    integrated_backtest_section = ""
    if not integrated_backtest_summary.empty:
        formatted_integrated = _format_backtest_summary(integrated_backtest_summary)
        integrated_rebalance_text = (
            _dataframe_to_markdown(integrated_backtest_rebalance_log.tail(10))
            if not integrated_backtest_rebalance_log.empty
            else "No rebalance log is available."
        )
        integrated_backtest_section = (
            "## Integrated Multi-Factor Backtest\n\n"
            "Value/Quality 재무 팩터를 각 월말 가격 신호일 기준 최신 사용가능 데이터로 결합하고, "
            "Momentum/Low Volatility와 함께 고정 가중 composite score를 계산했습니다. "
            "동일하게 상위 30종목 동일가중, 월말 리밸런싱, 회전율 기반 10bp 거래비용을 적용했습니다.\n\n"
            "### Integrated Backtest Summary\n\n"
            f"{_dataframe_to_markdown(formatted_integrated)}\n\n"
            "### Recent Integrated Rebalance Log\n\n"
            f"{integrated_rebalance_text}\n\n"
        )

    external_benchmark_section = ""
    external_rows = []
    if not kodex200_price_backtest_summary.empty:
        external_rows.append(
            kodex200_price_backtest_summary.assign(
                strategy="Price Momentum/Low Volatility",
                benchmark="KODEX 200 ETF (069500)",
            )
        )
    if not kodex200_integrated_backtest_summary.empty:
        external_rows.append(
            kodex200_integrated_backtest_summary.assign(
                strategy="Integrated Value/Quality/Momentum/Low Volatility",
                benchmark="KODEX 200 ETF (069500)",
            )
        )
    if not kodex200_regime_backtest_summary.empty:
        external_rows.append(
            kodex200_regime_backtest_summary.assign(
                strategy="Regime-Aware Defensive Multi-Factor",
                benchmark="KODEX 200 ETF (069500)",
            )
        )
    if external_rows:
        external_summary = pd.concat(external_rows, ignore_index=True)
        columns = [
            "strategy",
            "benchmark",
            "days",
            "total_return",
            "cagr",
            "annualized_volatility",
            "sharpe",
            "max_drawdown",
            "benchmark_total_return",
            "active_total_return",
            "tracking_error",
            "information_ratio",
            "average_turnover",
            "rebalance_count",
        ]
        external_benchmark_section = (
            "## External Benchmark Comparison\n\n"
            "KODEX 200 ETF(069500)를 KOSPI200 대용 벤치마크로 사용해 동일한 백테스트를 재계산했습니다. "
            "ETF는 추적오차와 비용이 있어 지수 자체와 완전히 같지는 않지만, 현재 단계에서는 시장 대비 "
            "초과성과를 설명하기 위한 실무적인 비교 기준입니다.\n\n"
            f"{_dataframe_to_markdown(_format_backtest_summary(external_summary[columns]))}\n\n"
        )

    return (
        "# KOSPI200 Fundamental Factor Model Portfolio - Initial Report\n\n"
        "## Executive Summary\n\n"
        "KIS API 가격 데이터 수집 파이프라인과 TS2000 재무데이터 표준화 파이프라인을 실행했습니다. "
        f"{price_description} "
        "재무데이터는 TS2000 원천 엑셀을 표준 `fundamentals.csv`로 변환한 결과입니다. "
        "이번 리포트는 데이터 검증, 팩터 산출, 1차 가격 팩터 백테스트 결과를 함께 요약합니다.\n\n"
        "## Price Data Coverage\n\n"
        f"{_dataframe_to_markdown(price_summary)}\n\n"
        "## Fundamentals Data Coverage\n\n"
        f"{_dataframe_to_markdown(fundamentals_summary)}\n\n"
        "## Fundamentals Yearly Coverage\n\n"
        f"{_dataframe_to_markdown(fundamentals_coverage.tail(15))}\n\n"
        "## Validation Issues\n\n"
        "### Price\n\n"
        f"{price_issue_text}\n\n"
        "### Fundamentals\n\n"
        f"{fundamentals_issue_text}\n\n"
        f"{factor_section}"
        f"{kospi200_portfolio_section}"
        f"{price_factor_section}"
        f"{backtest_section}"
        f"{integrated_backtest_section}"
        f"{external_benchmark_section}"
        "## Chart\n\n"
        f"![Normalized Price Index]({chart_path})\n\n"
        "## Next Steps\n\n"
        "1. 2015년 이후 가격 이력을 추가 수집해 장기 백테스트로 확장합니다.\n"
        "2. 실제 KOSPI200 지수 또는 ETF 벤치마크 수익률을 추가합니다.\n"
        "3. Value/Quality와 Momentum/Low Volatility를 결합한 통합 랭킹을 백테스트합니다.\n"
        "4. 거래대금 필터, 섹터/종목 cap, 거래비용 민감도 분석을 추가합니다.\n"
        "5. 월별 성과, 낙폭 구간, 팩터 IC/분위 포트폴리오 검증을 리포트화합니다.\n"
    )


def _build_pdf(
    price_summary: pd.DataFrame,
    price_issues: pd.DataFrame,
    fundamentals_summary: pd.DataFrame,
    fundamentals_coverage: pd.DataFrame,
    fundamentals_issues: pd.DataFrame,
    factor_coverage: pd.DataFrame,
    portfolio_preview: pd.DataFrame,
    price_factor_scores: pd.DataFrame,
    price_factor_coverage: pd.DataFrame,
    kospi200_portfolio: pd.DataFrame,
    kospi200_sector_exposure: pd.DataFrame,
    backtest_summary: pd.DataFrame,
    backtest_rebalance_log: pd.DataFrame,
    integrated_backtest_summary: pd.DataFrame,
    integrated_backtest_rebalance_log: pd.DataFrame,
    kodex200_price_backtest_summary: pd.DataFrame,
    kodex200_integrated_backtest_summary: pd.DataFrame,
    kodex200_regime_backtest_summary: pd.DataFrame,
    chart_path: Path,
    pdf_path: Path,
) -> None:
    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4)
    styles = getSampleStyleSheet()
    _setup_korean_styles(styles)
    price_ticker_count = (
        int(price_summary["ticker"].nunique()) if "ticker" in price_summary.columns else 0
    )
    story = [
        Paragraph("KOSPI200 Fundamental Factor Model Portfolio", styles["Title"]),
        Spacer(1, 0.15 * inch),
        Paragraph("Factor Modeling and Backtest Report", styles["Heading2"]),
        Paragraph(
            "This report summarizes the current KIS API price-data ingestion run "
            "and TS2000 fundamentals standardization run, then reports factor scores "
            "and monthly-rebalanced backtest results. "
            f"The current price dataset covers {price_ticker_count} ticker(s). ",
            styles["BodyText"],
        ),
        Spacer(1, 0.2 * inch),
        Paragraph("Price Data Coverage", styles["Heading2"]),
        _price_summary_table(price_summary),
        Spacer(1, 0.25 * inch),
        Paragraph("Fundamentals Data Coverage", styles["Heading2"]),
        _generic_table(fundamentals_summary),
        Spacer(1, 0.25 * inch),
        Paragraph("Fundamentals Yearly Coverage", styles["Heading2"]),
        _generic_table(fundamentals_coverage.tail(13)),
        Spacer(1, 0.25 * inch),
    ]
    if not factor_coverage.empty and not portfolio_preview.empty:
        story.extend(
            [
                Paragraph("Fundamental Factor Scores", styles["Heading2"]),
                Paragraph(
                    "Value/Quality MVP factor scores were generated. Composite score "
                    "renormalizes available Value and Quality weights only.",
                    styles["BodyText"],
                ),
                Spacer(1, 0.12 * inch),
                Paragraph("Current Portfolio Preview Top 10", styles["Heading3"]),
                _generic_table(
                    portfolio_preview[
                        [
                            "ticker",
                            "name",
                            "available_date",
                            "value_score",
                            "quality_score",
                            "composite_score",
                        ]
                    ].head(10)
                ),
                Spacer(1, 0.25 * inch),
            ]
        )
    if not kospi200_portfolio.empty:
        equal_weight = kospi200_portfolio[
            kospi200_portfolio["weighting_method"] == "equal_weight"
        ].copy()
        story.extend(
            [
                Paragraph("KOSPI200 Portfolio Preview", styles["Heading2"]),
                Paragraph(
                    "Current-universe KOSPI200 Value/Quality MVP portfolio preview. "
                    "Single-name 5% and sector 25% caps are applied.",
                    styles["BodyText"],
                ),
                Spacer(1, 0.12 * inch),
                _generic_table(
                    equal_weight[
                        [
                            "ticker",
                            "name",
                            "sector",
                            "value_score",
                            "quality_score",
                            "composite_score",
                            "weight",
                        ]
                    ].head(10)
                ),
                Spacer(1, 0.12 * inch),
            ]
        )
        if not kospi200_sector_exposure.empty:
            story.extend(
                [
                    Paragraph("KOSPI200 Sector Exposure", styles["Heading3"]),
                    _generic_table(kospi200_sector_exposure.head(12)),
                    Spacer(1, 0.25 * inch),
                ]
            )
    if not price_factor_scores.empty:
        price_factor_scores["signal_date"] = pd.to_datetime(
            price_factor_scores["signal_date"]
        )
        latest = price_factor_scores[
            price_factor_scores["signal_date"] == price_factor_scores["signal_date"].max()
        ].sort_values("composite_score", ascending=False)
        latest["signal_date"] = latest["signal_date"].dt.strftime("%Y-%m-%d")
        story.extend(
            [
                Paragraph("Price Factor Scores", styles["Heading2"]),
                Paragraph(
                    "Momentum and Low Volatility factors were generated for the "
                    "current price dataset. Longer history is still required for "
                    "full IC validation and backtesting.",
                    styles["BodyText"],
                ),
                Spacer(1, 0.12 * inch),
                _generic_table(
                    latest[
                        [
                            "ticker",
                            "name",
                            "signal_date",
                            "return_6m",
                            "volatility_1y",
                            "momentum_score",
                            "low_volatility_score",
                            "composite_score",
                        ]
                    ].head(20)
                ),
                Spacer(1, 0.25 * inch),
            ]
        )
    if not backtest_summary.empty:
        story.extend(
            [
                Paragraph("Price Factor Backtest", styles["Heading2"]),
                Paragraph(
                    "Monthly top-30 equal-weight Momentum/Low Volatility backtest "
                    "with 10bp turnover-based transaction cost.",
                    styles["BodyText"],
                ),
                Spacer(1, 0.12 * inch),
                _generic_table(backtest_summary),
                Spacer(1, 0.12 * inch),
            ]
        )
    if not integrated_backtest_summary.empty:
        story.extend(
            [
                Paragraph("Integrated Multi-Factor Backtest", styles["Heading2"]),
                Paragraph(
                    "Value, Quality, Momentum, and Low Volatility are combined "
                    "using latest available fundamentals as of each price signal date.",
                    styles["BodyText"],
                ),
                Spacer(1, 0.12 * inch),
                _generic_table(integrated_backtest_summary),
                Spacer(1, 0.12 * inch),
            ]
        )
        if not integrated_backtest_rebalance_log.empty:
            story.extend(
                [
                    Paragraph("Recent Integrated Rebalance Log", styles["Heading3"]),
                    _generic_table(integrated_backtest_rebalance_log.tail(5)),
                    Spacer(1, 0.25 * inch),
                ]
            )
    external_rows = []
    if not kodex200_price_backtest_summary.empty:
        external_rows.append(
            kodex200_price_backtest_summary.assign(strategy="Price", benchmark="KODEX200")
        )
    if not kodex200_integrated_backtest_summary.empty:
        external_rows.append(
            kodex200_integrated_backtest_summary.assign(strategy="Integrated", benchmark="KODEX200")
        )
    if not kodex200_regime_backtest_summary.empty:
        external_rows.append(
            kodex200_regime_backtest_summary.assign(strategy="Regime", benchmark="KODEX200")
        )
    if external_rows:
        external_summary = pd.concat(external_rows, ignore_index=True)
        story.extend(
            [
                Paragraph("External Benchmark Comparison", styles["Heading2"]),
                Paragraph(
                    "KODEX 200 ETF is used as a practical KOSPI200 proxy benchmark.",
                    styles["BodyText"],
                ),
                Spacer(1, 0.12 * inch),
                _generic_table(
                    external_summary[
                        [
                            "strategy",
                            "benchmark",
                            "total_return",
                            "cagr",
                            "sharpe",
                            "max_drawdown",
                            "benchmark_total_return",
                            "active_total_return",
                            "information_ratio",
                        ]
                    ]
                ),
                Spacer(1, 0.25 * inch),
            ]
        )
        if not backtest_rebalance_log.empty:
            story.extend(
                [
                    Paragraph("Recent Rebalance Log", styles["Heading3"]),
                    _generic_table(backtest_rebalance_log.tail(5)),
                    Spacer(1, 0.25 * inch),
                ]
            )
    story.extend(
        [
        Paragraph("Validation Issues", styles["Heading2"]),
        Paragraph(
            _issue_text("Price", price_issues)
            + "<br/>"
            + _issue_text("Fundamentals", fundamentals_issues),
            styles["BodyText"],
        ),
        Spacer(1, 0.25 * inch),
        Paragraph("Normalized Price Index", styles["Heading2"]),
        Paragraph(f"Chart saved separately: {chart_path}", styles["BodyText"]),
        Spacer(1, 0.2 * inch),
        Paragraph("Next Steps", styles["Heading2"]),
        Paragraph(
            "Extend price history to 2015 or earlier, replace current-universe fallback "
            "with point-in-time KOSPI200 membership, and add Rank IC, quintile spread, "
            "sector-neutral portfolios, and transaction-cost sensitivity analysis.",
            styles["BodyText"],
        ),
        ]
    )
    doc.build(story)


def _price_summary_table(summary: pd.DataFrame) -> Table:
    columns = [
        "ticker",
        "name",
        "rows",
        "start_date",
        "end_date",
        "first_adj_close",
        "last_adj_close",
        "simple_return",
    ]
    table_data = [columns]
    for _, row in summary[columns].iterrows():
        table_data.append(
            [
                row["ticker"],
                row.get("name", ""),
                int(row["rows"]),
                row["start_date"],
                row["end_date"],
                f"{row['first_adj_close']:,.0f}",
                f"{row['last_adj_close']:,.0f}",
                f"{row['simple_return']:.1%}",
            ]
        )

    table = Table(table_data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTNAME", (0, 0), (-1, -1), KOREAN_FONT),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            ]
        )
    )
    return table


def _generic_table(frame: pd.DataFrame) -> Table:
    styles = getSampleStyleSheet()
    _setup_korean_styles(styles)
    cell_style = styles["BodyText"]
    cell_style.fontSize = 6.5
    cell_style.leading = 8
    table_data = [[Paragraph(str(column), cell_style) for column in frame.columns]]
    for _, row in frame.iterrows():
        values = []
        for value in row.tolist():
            if pd.isna(value):
                values.append(Paragraph("", cell_style))
            elif isinstance(value, float):
                values.append(Paragraph(f"{value:,.2f}", cell_style))
            else:
                values.append(Paragraph(str(value), cell_style))
        table_data.append(values)

    table = Table(table_data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTNAME", (0, 0), (-1, -1), KOREAN_FONT),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
            ]
        )
    )
    return table


def _issue_text(label: str, issues: pd.DataFrame) -> str:
    if issues.empty:
        return f"{label}: no issues detected."
    return f"{label}: {len(issues)} informational issue row(s). See Markdown report for details."


def _read_optional_csv(path: str | Path, **kwargs) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, **kwargs)


def _setup_korean_styles(styles) -> None:
    try:
        pdfmetrics.registerFont(TTFont(KOREAN_FONT, KOREAN_FONT_PATH))
    except Exception:
        pass
    for style_name in styles.byName:
        style = styles[style_name]
        style.fontName = KOREAN_FONT
        style.wordWrap = "CJK"


def _build_name_master() -> pd.DataFrame:
    sources = []
    fundamentals_path = Path("data/raw/ts2000/fundamentals.csv")
    if fundamentals_path.exists():
        fundamentals = pd.read_csv(
            fundamentals_path,
            dtype={"ticker": "string"},
            usecols=["ticker", "name", "available_date"],
            parse_dates=["available_date"],
        )
        fundamentals = fundamentals.dropna(subset=["ticker", "name"])
        latest = (
            fundamentals.sort_values("available_date")
            .groupby("ticker", as_index=False)
            .tail(1)[["ticker", "name"]]
        )
        sources.append(latest)
    universe_path = Path("data/raw/benchmark/kospi200_constituents.csv")
    if universe_path.exists():
        universe = pd.read_csv(universe_path, dtype={"ticker": "string"}, usecols=["ticker", "name"])
        sources.append(universe.dropna(subset=["ticker", "name"]))
    if not sources:
        return pd.DataFrame(columns=["ticker", "name"])
    master = pd.concat(sources, ignore_index=True)
    master["ticker"] = master["ticker"].astype("string").str.zfill(6)
    master = master.drop_duplicates("ticker", keep="first")
    overrides = {
        "298040": "효성중공업(주)",
    }
    for ticker, name in overrides.items():
        mask = master["ticker"].eq(ticker)
        if mask.any():
            master.loc[mask, "name"] = name
        else:
            master = pd.concat(
                [master, pd.DataFrame([{"ticker": ticker, "name": name}])],
                ignore_index=True,
            )
    master.to_csv("outputs/tables/ticker_name_master.csv", index=False, encoding="utf-8-sig")
    return master


def _attach_names(frame: pd.DataFrame, name_master: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or "ticker" not in frame.columns or name_master.empty:
        return frame
    output = frame.copy()
    output["ticker"] = output["ticker"].astype("string").str.zfill(6)
    if "name" in output.columns:
        output = output.drop(columns=["name"])
    return output.merge(name_master, on="ticker", how="left")


def _format_backtest_summary(summary: pd.DataFrame) -> pd.DataFrame:
    formatted = summary.copy()
    percent_columns = [
        "total_return",
        "cagr",
        "annualized_volatility",
        "max_drawdown",
        "win_rate",
        "benchmark_total_return",
        "active_total_return",
        "tracking_error",
        "average_turnover",
    ]
    for column in percent_columns:
        if column in formatted.columns:
            formatted[column] = formatted[column].map(lambda value: f"{value:.2%}")
    for column in ["sharpe", "information_ratio"]:
        if column in formatted.columns:
            formatted[column] = formatted[column].map(lambda value: f"{value:.2f}")
    return formatted


def _dataframe_to_markdown(frame: pd.DataFrame) -> str:
    display = frame.copy()
    for column in display.columns:
        if pd.api.types.is_float_dtype(display[column]):
            display[column] = display[column].map(
                lambda value: "" if pd.isna(value) else f"{value:.4f}"
            )
        else:
            display[column] = display[column].map(
                lambda value: "" if pd.isna(value) else str(value)
            )
    headers = [str(column) for column in display.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in display.values.tolist():
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(lines)
