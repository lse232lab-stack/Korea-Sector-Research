"""Generate a client-style investment strategy report."""

from __future__ import annotations

from html import escape
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

KOREAN_FONT = "AppleGothic"
KOREAN_FONT_PATH = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"
REPORT_DATE = "2026-07-04"


def generate_client_strategy_report(
    *,
    markdown_path: str | Path = "outputs/reports/KOSPI200_AI_Quant_Strategy_Client_Report.md",
    pdf_path: str | Path = "outputs/reports/KOSPI200_AI_Quant_Strategy_Client_Report.pdf",
) -> tuple[Path, Path]:
    """Create a sell-side style client report from existing project outputs."""
    tables = _load_report_tables()
    markdown_path = Path(markdown_path)
    pdf_path = Path(pdf_path)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    markdown_path.write_text(_build_markdown(tables), encoding="utf-8")
    _build_pdf(tables, pdf_path)
    return markdown_path, pdf_path


def _load_report_tables() -> dict[str, pd.DataFrame]:
    readers = {
        "price_coverage": ("outputs/tables/long_price_yearly_coverage.csv", {}),
        "research_split": ("outputs/tables/research_split_summary.csv", {}),
        "rank_ic": ("outputs/tables/rank_ic_summary.csv", {}),
        "quintile": ("outputs/tables/quintile_return_summary.csv", {}),
        "split_backtest": ("outputs/tables/ml_vs_factor_split_backtest_summary.csv", {}),
        "ml_metrics": ("outputs/tables/ml_model_metrics.csv", {}),
        "ml_candidates": (
            "outputs/portfolios/latest_ml_prediction_candidates.csv",
            {"dtype": {"ticker": "string"}},
        ),
        "factor_candidates": (
            "outputs/portfolios/latest_recommendation_candidates.csv",
            {"dtype": {"ticker": "string"}},
        ),
    }
    output = {}
    for key, (path, kwargs) in readers.items():
        output[key] = _read_optional_csv(path, **kwargs)
    return output


def _build_markdown(tables: dict[str, pd.DataFrame]) -> str:
    data_summary = _data_summary_rows(tables)
    performance = _performance_table(tables["split_backtest"])
    ic = _ic_table(tables["rank_ic"])
    quintile = _quintile_table(tables["quintile"])
    ml_metrics = _ml_metrics_table(tables["ml_metrics"])
    ml_candidates = _candidate_table(tables["ml_candidates"], limit=10)
    factor_candidates = _candidate_table(tables["factor_candidates"], limit=10)

    return f"""# KOSPI200 AI Quant Strategy

발간일: {REPORT_DATE}

투자전략 의견: 정량모델 기준 KOSPI200 장기 멀티팩터 전략 비중확대. 단, 변동성과 최대낙폭을 감안해 통합 멀티팩터를 코어로, ML 예측 포트폴리오를 위성 전략으로 활용하는 방식을 권고한다.

## Executive Summary

- 본 프로젝트는 KIS API 기반 2007~2026년 KOSPI200 가격 데이터와 TS2000 재무 데이터를 결합해, 고객 배포용 투자전략 리포트 수준의 정량 리서치 프레임워크를 구축했다.
- 데이터셋은 가격 780,050건, 200개 종목, 2007-01-02~2026-06-30 구간을 포함한다. 재무 데이터는 15,756건, 990개 종목, 2007-01~2026-03 회계기간을 포함한다.
- 모델은 Value, Quality, Growth, Momentum, Low Volatility 팩터를 통합한 멀티팩터 전략과, 1개월 후 초과수익률을 예측하는 Ridge 기반 ML 전략을 비교했다.
- 검증 구간을 Train 2007~2016, Validation 2017~2021, Test 2022~2026으로 분리해 데이터 누수를 줄였다.
- Test 구간에서 ML 전략은 CAGR 32.31%, Sharpe 1.14, Information Ratio 1.01, 최대낙폭 -27.61%를 기록했다. 통합 멀티팩터 전략도 CAGR 27.21%, Sharpe 1.09, IR 0.73으로 양호했다.
- 투자전략 관점에서는 통합 멀티팩터를 기본 배분의 70%, ML 예측 전략을 30% 위성 배분으로 두고, 시장 하락 국면에서는 위험노출을 축소하는 국면 대응 룰을 추가하는 방향이 적절하다.

## 프로젝트 구조

1. 데이터 수집: KIS API로 일별 가격 데이터를 수집하고, TS2000 엑셀 재무 데이터를 장기 패널 형태로 표준화했다.
2. 데이터 검증: 종목별 커버리지, 결측, 중복, 연도별 가격 행 수, 재무 데이터 공시 가능일 기준 split을 점검했다.
3. 팩터 생성: Value, Quality, Growth는 재무 데이터에서, Momentum과 Low Volatility는 가격 데이터에서 산출했다.
4. 타깃 생성: 월말 신호일 기준 다음 1개월 종목 수익률에서 동일 유니버스 평균 수익률을 차감해 초과수익률을 정의했다.
5. 학습과 검증: Train에서 모델을 추정하고, Validation Rank IC로 모델을 선택한 뒤, Test 구간은 최종 실전 성과 검증에만 사용했다.
6. 포트폴리오 구성: 매월 상위 30개 종목을 동일가중으로 편입하고, 리밸런싱 회전율에 10bp 거래비용을 적용했다.
7. 성과 평가: CAGR, 변동성, Sharpe, 최대낙폭, 벤치마크 대비 초과수익, Tracking Error, Information Ratio를 비교했다.

## 데이터 커버리지

{_markdown_table(data_summary)}

## 전략별 성과

벤치마크는 보유 가능 종목의 동일가중 포트폴리오다. 공식 KOSPI200 지수가 아니라 모델 유니버스 내부 벤치마크이므로, 향후 공식 지수 또는 KODEX 200 장기 데이터와의 재검증이 필요하다.

{_markdown_table(performance)}

## 팩터 유효성

Composite Score의 평균 Rank IC는 0.0233, 양수 비율은 56.83%다. 월별 예측력이 강한 신호라고 보기는 어렵지만, 장기적으로 양의 방향성을 유지했고 Q5-Q1 월평균 초과수익은 1.04%로 포트폴리오 레벨에서는 활용 가능한 스프레드를 보였다.

{_markdown_table(ic)}

{_markdown_table(quintile)}

## ML 모델 검증

Validation Rank IC 기준 최종 선택 모델은 Ridge Linear다. Test 구간 평균 Rank IC는 0.0393으로 Baseline 대비 개선되었고, 방향성 적중률은 51.89%로 절대적으로 높지는 않지만 횡단면 랭킹 전략에는 의미 있는 개선을 보였다.

{_markdown_table(ml_metrics)}

## 향후 투자전략 제안

### 모델 포트폴리오 후보군

아래 종목은 투자 의견이나 개인화된 매수 추천이 아니라, 2026년 5~6월 신호 기준 정량모델 상위 스크리닝 결과다. 실제 편입 전에는 최신 가격, 유동성, 실적 이벤트, 업종 노출, 리스크 한도를 재확인해야 한다.

ML 예측 전략 상위 후보:

{_markdown_table(ml_candidates)}

통합 멀티팩터 전략 상위 후보:

{_markdown_table(factor_candidates)}

### 권고 운용 프레임

- 코어 전략: 통합 멀티팩터 상위 30종목 동일가중, 월간 리밸런싱, 전략 배분 70%.
- 위성 전략: ML 예측수익률 상위 30종목 동일가중, 전략 배분 30%. 기대수익은 높지만 회전율과 최대낙폭이 커질 수 있다.
- 위험관리: 단일 종목 5%, 업종 25% 한도를 적용하고, 시장 변동성이 과거 80퍼센타일을 상회하거나 지수가 장기 이동평균을 하회할 때 주식 노출을 50%까지 축소한다.
- 리밸런싱: 월말 신호 생성 후 익월 첫 거래일 체결을 가정한다. 실전 적용 시 거래대금 하위 종목은 제외하고 체결비용 민감도 분석을 추가한다.

## 해석과 한계

- ML 전략은 Test 구간 성과가 가장 우수하지만, Full 구간 최대낙폭이 -52.86%로 크다. 단독 주력 전략보다는 위험예산이 제한된 위성 전략으로 활용하는 편이 적절하다.
- 현재 유니버스는 현재 KOSPI200 구성종목 기반이므로 과거 생존편향이 남아 있다. 실무 배포 전에는 point-in-time KOSPI200 편입 이력을 반영해야 한다.
- 재무 데이터는 사용 가능일 기준으로 정렬했지만, 실제 공시 지연과 데이터 벤더 업데이트 시점은 추가 검증이 필요하다.
- 거래비용은 회전율 기반 10bp 단순 가정이다. 대형주는 보수적일 수 있으나, 급등락 구간과 저유동성 종목은 시장충격 비용이 더 클 수 있다.
- 본 자료는 정량 리서치 프로젝트 산출물이며 특정 투자자에게 적합한 투자 자문이 아니다.

## 향후 고도화 과제

1. KOSPI200 point-in-time 유니버스와 공식 지수 벤치마크를 연결한다.
2. 연 1회 또는 반기 1회 walk-forward 재학습으로 모델 안정성을 검증한다.
3. 업종 중립화, 시가총액 중립화, 거래대금 필터를 추가해 실전 운용 가능성을 높인다.
4. 하락장 대응을 위해 추세, 변동성, 신용스프레드, 환율, 금리 변수를 결합한 regime overlay를 구축한다.
5. 포트폴리오 편입 사유를 종목별로 설명하는 Explainable AI 리포트 테이블을 추가한다.
"""


def _build_pdf(tables: dict[str, pd.DataFrame], pdf_path: Path) -> None:
    styles = getSampleStyleSheet()
    _setup_korean_styles(styles)
    for style_name in ["Title", "Heading1", "Heading2", "Heading3"]:
        styles[style_name].textColor = colors.HexColor("#14213d")
        styles[style_name].spaceAfter = 8
    styles["BodyText"].fontSize = 9
    styles["BodyText"].leading = 13

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=0.45 * inch,
        leftMargin=0.45 * inch,
        topMargin=0.45 * inch,
        bottomMargin=0.45 * inch,
    )
    story = [
        Paragraph("KOSPI200 AI Quant Strategy", styles["Title"]),
        Paragraph("장기 멀티팩터와 ML 예측수익률 기반 투자전략 리포트", styles["Heading2"]),
        Paragraph(f"발간일: {REPORT_DATE}", styles["BodyText"]),
        Spacer(1, 0.15 * inch),
        _callout(
            "투자전략 의견: 정량모델 기준 KOSPI200 장기 멀티팩터 전략 비중확대. "
            "통합 멀티팩터를 코어로, ML 예측 포트폴리오를 위성 전략으로 활용하는 접근을 권고한다.",
            styles,
        ),
        Spacer(1, 0.15 * inch),
        Paragraph("Executive Summary", styles["Heading2"]),
        *_bullets(
            [
                "KIS API 가격 780,050건과 TS2000 재무 15,756건을 결합한 2007~2026 장기 정량 리서치 프레임워크를 구축했다.",
                "Train 2007~2016, Validation 2017~2021, Test 2022~2026으로 분리해 데이터 누수를 줄였다.",
                "Test 구간 ML 전략은 CAGR 32.31%, Sharpe 1.14, IR 1.01, 최대낙폭 -27.61%를 기록했다.",
                "통합 멀티팩터는 더 설명 가능하고 안정적인 코어 전략, ML 전략은 공격적 알파를 추구하는 위성 전략으로 해석한다.",
            ],
            styles,
        ),
        Spacer(1, 0.15 * inch),
        Paragraph("프로젝트 구조", styles["Heading2"]),
        *_bullets(
            [
                "데이터 수집: KIS API 일별 가격, TS2000 재무 데이터 표준화.",
                "팩터 생성: Value, Quality, Growth, Momentum, Low Volatility 산출.",
                "학습 목표: 월말 기준 다음 1개월 초과수익률 예측.",
                "검증 방식: Validation Rank IC로 모델 선택, Test 성과는 최종 검증에만 사용.",
                "포트폴리오: 월간 리밸런싱, 상위 30종목 동일가중, 10bp 거래비용.",
            ],
            styles,
        ),
        Spacer(1, 0.12 * inch),
        Paragraph("데이터 커버리지", styles["Heading2"]),
        _pdf_table(_data_summary_rows(tables), styles, [1.6 * inch, 1.3 * inch, 1.1 * inch, 2.0 * inch, 1.7 * inch]),
        PageBreak(),
        Paragraph("전략별 성과", styles["Heading2"]),
        Paragraph(
            "벤치마크는 보유 가능 종목의 동일가중 포트폴리오다. 공식 KOSPI200 지수와의 추가 검증이 필요하다.",
            styles["BodyText"],
        ),
        _pdf_table(_performance_table(tables["split_backtest"]), styles),
        Spacer(1, 0.18 * inch),
        Paragraph("팩터 유효성", styles["Heading2"]),
        Paragraph(
            "Composite Score는 평균 Rank IC 0.0233과 양수 비율 56.83%를 기록했다. Q5-Q1 월평균 스프레드는 1.04%다.",
            styles["BodyText"],
        ),
        _pdf_table(_ic_table(tables["rank_ic"]), styles),
        Spacer(1, 0.12 * inch),
        _pdf_table(_quintile_table(tables["quintile"]), styles),
        PageBreak(),
        Paragraph("ML 모델 검증", styles["Heading2"]),
        Paragraph(
            "Validation Rank IC 기준 최종 선택 모델은 Ridge Linear다. Test 구간 Rank IC와 전략 성과 모두 Baseline 대비 개선되었다.",
            styles["BodyText"],
        ),
        _pdf_table(_ml_metrics_table(tables["ml_metrics"]), styles),
        Spacer(1, 0.18 * inch),
        Paragraph("모델 포트폴리오 후보군", styles["Heading2"]),
        Paragraph(
            "아래 표는 투자 의견이 아니라 정량모델 상위 스크리닝 결과다. 실제 편입 전 최신 가격, 유동성, 실적 이벤트, 업종 한도를 재확인해야 한다.",
            styles["BodyText"],
        ),
        Paragraph("ML 예측 전략 상위 후보", styles["Heading3"]),
        _pdf_table(_candidate_table(tables["ml_candidates"], limit=10), styles),
        Spacer(1, 0.12 * inch),
        Paragraph("통합 멀티팩터 전략 상위 후보", styles["Heading3"]),
        _pdf_table(_candidate_table(tables["factor_candidates"], limit=10), styles),
        PageBreak(),
        Paragraph("향후 투자전략 제안", styles["Heading2"]),
        *_bullets(
            [
                "코어 전략: 통합 멀티팩터 상위 30종목 동일가중, 월간 리밸런싱, 전략 배분 70%.",
                "위성 전략: ML 예측수익률 상위 30종목 동일가중, 전략 배분 30%.",
                "위험관리: 단일 종목 5%, 업종 25% 한도. 시장 변동성 급등 또는 장기 추세 하회 시 주식 노출을 50%까지 축소.",
                "실전 적용: 거래대금 하위 종목 제외, 체결비용 민감도 분석, 업종 중립화와 point-in-time 유니버스 반영.",
            ],
            styles,
        ),
        Spacer(1, 0.15 * inch),
        Paragraph("해석과 한계", styles["Heading2"]),
        *_bullets(
            [
                "ML 전략은 기대수익이 높지만 Full 구간 최대낙폭이 -52.86%로 커 단독 주력 전략보다는 위성 전략이 적절하다.",
                "현재 KOSPI200 구성종목 기반이라 과거 생존편향이 남아 있다.",
                "거래비용은 10bp 단순 가정이며, 실제 시장충격과 유동성 제약은 추가 반영해야 한다.",
                "본 자료는 정량 리서치 프로젝트 산출물이며 특정 투자자에게 적합한 투자 자문이 아니다.",
            ],
            styles,
        ),
    ]
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)


def _data_summary_rows(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    price = tables["price_coverage"]
    research = tables["research_split"]
    price_rows = int(price["rows"].sum()) if "rows" in price else 780050
    max_tickers = int(price["tickers"].max()) if "tickers" in price else 200
    return pd.DataFrame(
        [
            {
                "구분": "가격 데이터",
                "행 수": f"{price_rows:,}",
                "종목 수": f"{max_tickers:,}",
                "기간": "2007-01-02~2026-06-30",
                "용도": "수익률, 모멘텀, 변동성",
            },
            {
                "구분": "재무 데이터",
                "행 수": "15,756",
                "종목 수": "990",
                "기간": "2007-01~2026-03",
                "용도": "Value, Quality, Growth",
            },
            {
                "구분": "Train",
                "행 수": _split_value(research, "train", "rows"),
                "종목 수": _split_value(research, "train", "tickers"),
                "기간": "2007~2016",
                "용도": "모델 학습",
            },
            {
                "구분": "Validation",
                "행 수": _split_value(research, "validation", "rows"),
                "종목 수": _split_value(research, "validation", "tickers"),
                "기간": "2017~2021",
                "용도": "모델 선택",
            },
            {
                "구분": "Test",
                "행 수": _split_value(research, "test", "rows"),
                "종목 수": _split_value(research, "test", "tickers"),
                "기간": "2022~2026",
                "용도": "최종 검증",
            },
        ]
    )


def _performance_table(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    output = frame.copy()
    if "split" in output:
        split_series = output["split"].astype(str)
    else:
        split_series = output["period"].astype(str).str.split("_").str[0]
    output["구간"] = split_series.str.lower().map(
        {
            "train": "Train",
            "validation": "Validation",
            "test": "Test",
            "full": "Full",
        }
    ).fillna(split_series)
    output = output[output["구간"].isin(["Train", "Validation", "Test", "Full"])]
    output["전략"] = output["strategy"].map(
        {
            "Integrated": "통합 멀티팩터",
            "ML Predicted Return": "ML 예측",
            "integrated_multifactor": "통합 멀티팩터",
            "ml_predicted_return": "ML 예측",
        }
    ).fillna(output["strategy"])
    cols = {
        "total_return": "누적수익률",
        "cagr": "CAGR",
        "annualized_volatility": "변동성",
        "sharpe": "Sharpe",
        "max_drawdown": "MDD",
        "active_total_return": "초과수익",
        "information_ratio": "IR",
    }
    keep = ["전략", "구간", *cols.values()]
    for source, target in cols.items():
        if source in output:
            if source in {"sharpe", "information_ratio"}:
                output[target] = output[source].map(lambda value: f"{value:.2f}")
            else:
                output[target] = output[source].map(lambda value: f"{value:.2%}")
    return output[keep]


def _ic_table(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    names = {
        "composite_score": "Composite",
        "quality_score": "Quality",
        "value_score": "Value",
        "low_volatility_score": "Low Vol",
        "momentum_score": "Momentum",
    }
    output = frame.copy()
    output["팩터"] = output["factor"].map(names).fillna(output["factor"])
    positive_col = "positive_ic_rate" if "positive_ic_rate" in output else "positive_rate"
    return pd.DataFrame(
        {
            "팩터": output["팩터"],
            "월 수": output["months"].map(lambda value: f"{int(value):,}"),
            "평균 Rank IC": output["mean_rank_ic"].map(lambda value: f"{value:.4f}"),
            "중앙값 IC": output["median_rank_ic"].map(lambda value: f"{value:.4f}"),
            "양수 비율": output[positive_col].map(lambda value: f"{value:.2%}"),
        }
    )


def _quintile_table(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    output = frame.copy()
    mean_col = "mean_forward_return" if "mean_forward_return" in output else "mean_excess_return"
    median_col = (
        "median_forward_return"
        if "median_forward_return" in output
        else "median_excess_return"
    )
    return pd.DataFrame(
        {
            "분위": output["quantile"].astype(str),
            "월 수": output["months"].map(lambda value: f"{int(value):,}"),
            "월평균 초과수익": output[mean_col].map(lambda value: f"{value:.2%}"),
            "월중앙 초과수익": output[median_col].map(lambda value: f"{value:.2%}"),
        }
    )


def _ml_metrics_table(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    output = frame.copy()
    model_col = "model_name" if "model_name" in output else "model"
    split_col = "research_split" if "research_split" in output else "split"
    direction_col = (
        "direction_hit_rate"
        if "direction_hit_rate" in output
        else "directional_hit_rate"
    )
    output = output[output[model_col].isin(["ridge_linear", "composite_baseline"])]
    return pd.DataFrame(
        {
            "모델": output[model_col].map(
                {"ridge_linear": "Ridge Linear", "composite_baseline": "Composite Baseline"}
            ),
            "구간": output[split_col],
            "평균 Rank IC": output["mean_rank_ic"].map(lambda value: f"{value:.4f}"),
            "IC 양수 비율": output["positive_rank_ic_rate"].map(lambda value: f"{value:.2%}"),
            "방향성 적중률": output[direction_col].map(lambda value: f"{value:.2%}"),
            "RMSE": output["rmse"].map(lambda value: f"{value:.4f}"),
        }
    )


def _candidate_table(frame: pd.DataFrame, *, limit: int) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    output = frame.copy().head(limit)
    if "predicted_excess_forward_1m_return" in output.columns:
        score_col = "predicted_excess_forward_1m_return"
    elif "prediction" in output.columns:
        score_col = "prediction"
    else:
        score_col = "composite_score"
    if score_col not in output:
        score_col = output.select_dtypes("number").columns[-1]
    return pd.DataFrame(
        {
            "순위": range(1, len(output) + 1),
            "종목코드": output["ticker"].astype("string").str.zfill(6),
            "종목명": output["name"].astype(str),
            "신호일": output.get("signal_date", "").astype(str),
            "모델점수": output[score_col].map(lambda value: f"{value:.4f}"),
        }
    )


def _split_value(frame: pd.DataFrame, split: str, column: str) -> str:
    if frame.empty or column not in frame:
        return ""
    if "research_split" in frame:
        split_col = "research_split"
    elif "split" in frame:
        split_col = "split"
    else:
        split_col = "dataset"
    if split_col not in frame:
        return ""
    row = frame[frame[split_col].astype(str).str.lower().eq(split)]
    if row.empty:
        return ""
    return f"{int(row.iloc[0][column]):,}"


def _read_optional_csv(path: str | Path, **kwargs) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, **kwargs)


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No data available."
    headers = [str(column) for column in frame.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in frame.astype(str).values.tolist():
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _setup_korean_styles(styles) -> None:
    try:
        pdfmetrics.registerFont(TTFont(KOREAN_FONT, KOREAN_FONT_PATH))
    except Exception:
        pass
    for style_name in styles.byName:
        style = styles[style_name]
        style.fontName = KOREAN_FONT
        style.wordWrap = "CJK"


def _pdf_table(frame: pd.DataFrame, styles, col_widths=None) -> Table:
    cell_style = styles["BodyText"].clone("TableCell")
    cell_style.fontSize = 6.4
    cell_style.leading = 8
    cell_style.wordWrap = "CJK"
    data = [[Paragraph(escape(str(col)), cell_style) for col in frame.columns]]
    for _, row in frame.iterrows():
        data.append([Paragraph(escape(str(value)), cell_style) for value in row.tolist()])
    if col_widths is None:
        available = A4[0] - 0.9 * inch
        col_widths = [available / max(len(frame.columns), 1)] * len(frame.columns)
    table = Table(data, repeatRows=1, colWidths=col_widths)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#14213d")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
                ("FONTNAME", (0, 0), (-1, -1), KOREAN_FONT),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _bullets(items: list[str], styles) -> list:
    story = []
    for item in items:
        story.append(Paragraph("- " + escape(item), styles["BodyText"]))
        story.append(Spacer(1, 0.04 * inch))
    return story


def _callout(text: str, styles) -> Table:
    cell = Paragraph(escape(text), styles["BodyText"])
    table = Table([[cell]], colWidths=[A4[0] - 0.9 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eef2ff")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#14213d")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def _footer(canvas, doc) -> None:
    canvas.saveState()
    try:
        canvas.setFont(KOREAN_FONT, 7)
    except Exception:
        canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#6b7280"))
    canvas.drawString(0.45 * inch, 0.25 * inch, "KOSPI200 AI Quant Strategy - Research project output")
    canvas.drawRightString(A4[0] - 0.45 * inch, 0.25 * inch, f"{doc.page}")
    canvas.restoreState()
