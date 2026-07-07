"""Practical strategy library experiments for the KOSPI200 project."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.backtest.engine import run_backtest
from src.backtest.performance import calculate_performance_metrics
from src.factors.composite import calculate_composite_score


STRATEGY_DEFINITIONS = [
    {
        "strategy_id": "deep_value",
        "strategy_name": "Deep Value",
        "category": "valuation",
        "description": "저평가 종목군에 집중하는 전통적 가치 전략",
        "weights": {"value_score": 1.0},
    },
    {
        "strategy_id": "quality_compounder",
        "strategy_name": "Quality Compounder",
        "category": "fundamental",
        "description": "수익성, 안정성, 재무 건전성이 우수한 기업 선호",
        "weights": {"quality_score": 1.0},
    },
    {
        "strategy_id": "earnings_growth",
        "strategy_name": "Earnings Growth",
        "category": "fundamental",
        "description": "실적 성장성과 개선 흐름이 강한 종목 선호",
        "weights": {"growth_score": 1.0},
    },
    {
        "strategy_id": "price_momentum",
        "strategy_name": "Price Momentum",
        "category": "price",
        "description": "12개월-1개월 가격 모멘텀이 강한 종목 선호",
        "weights": {"momentum_score": 1.0},
    },
    {
        "strategy_id": "low_volatility",
        "strategy_name": "Low Volatility",
        "category": "defensive",
        "description": "낙폭과 변동성이 낮은 방어적 종목 선호",
        "weights": {"low_volatility_score": 1.0},
    },
    {
        "strategy_id": "balanced_multifactor",
        "strategy_name": "Balanced Multi-Factor",
        "category": "multi_factor",
        "description": "Value, Quality, Growth, Momentum, Low Volatility 균형 결합",
        "weights": {
            "quality_score": 0.25,
            "value_score": 0.25,
            "momentum_score": 0.20,
            "low_volatility_score": 0.20,
            "growth_score": 0.10,
        },
    },
    {
        "strategy_id": "value_momentum_barbell",
        "strategy_name": "Value + Momentum Barbell",
        "category": "multi_factor",
        "description": "저평가와 가격추세를 동시에 요구하는 실무형 조합",
        "weights": {
            "value_score": 0.35,
            "momentum_score": 0.35,
            "quality_score": 0.15,
            "low_volatility_score": 0.15,
        },
    },
    {
        "strategy_id": "quality_low_vol_defensive",
        "strategy_name": "Quality + Low Vol Defensive",
        "category": "defensive",
        "description": "하락장 대응을 의식한 퀄리티와 저변동성 중심 전략",
        "weights": {
            "quality_score": 0.45,
            "low_volatility_score": 0.45,
            "value_score": 0.10,
        },
    },
    {
        "strategy_id": "momentum_growth_aggressive",
        "strategy_name": "Momentum + Growth Aggressive",
        "category": "aggressive",
        "description": "강한 가격추세와 실적 성장성을 결합한 공격형 알파 전략",
        "weights": {
            "momentum_score": 0.60,
            "growth_score": 0.25,
            "quality_score": 0.15,
        },
    },
    {
        "strategy_id": "ml_predicted_return",
        "strategy_name": "ML Predicted Return",
        "category": "machine_learning",
        "description": "Ridge 모델의 1개월 초과수익률 예측치를 랭킹 신호로 사용",
        "source": "ml",
    },
]

SPLITS = [
    ("train_2007_2016", "2007-01-01", "2016-12-31"),
    ("validation_2017_2021", "2017-01-01", "2021-12-31"),
    ("test_2022_2026", "2022-01-01", "2026-12-31"),
    ("full_2007_2026", "2007-01-01", "2026-12-31"),
]


def run_strategy_lab(
    *,
    price_path: str | Path = "data/raw/price/prices_2007_2026.csv",
    factor_scores_path: str | Path = "data/features/integrated_factor_scores_2007_2026.csv",
    ml_factor_scores_path: str | Path = "data/features/ml_predicted_factor_scores_2007_2026.csv",
    strategy_score_dir: str | Path = "data/features/strategy_lab",
    backtest_root: str | Path = "outputs/strategy_lab/backtests",
    summary_output_path: str | Path = "outputs/tables/strategy_lab_summary.csv",
    split_summary_output_path: str | Path = "outputs/tables/strategy_lab_split_summary.csv",
    definition_output_path: str | Path = "outputs/tables/strategy_lab_definitions.csv",
    report_output_path: str | Path = "outputs/reports/Strategy_Lab_Practical_Strategy_Test.md",
    top_n: int = 30,
    transaction_cost_bps: float = 10.0,
) -> dict[str, pd.DataFrame]:
    """Build and backtest a practical strategy library."""
    strategy_score_dir = Path(strategy_score_dir)
    backtest_root = Path(backtest_root)
    strategy_score_dir.mkdir(parents=True, exist_ok=True)
    backtest_root.mkdir(parents=True, exist_ok=True)

    definitions = pd.DataFrame(
        [
            {
                "strategy_id": item["strategy_id"],
                "strategy_name": item["strategy_name"],
                "category": item["category"],
                "description": item["description"],
                "weights": _format_weights(item),
            }
            for item in STRATEGY_DEFINITIONS
        ]
    )
    definition_output_path = Path(definition_output_path)
    definition_output_path.parent.mkdir(parents=True, exist_ok=True)
    definitions.to_csv(definition_output_path, index=False, encoding="utf-8-sig")

    summary_rows = []
    split_rows = []
    for definition in STRATEGY_DEFINITIONS:
        score_path = strategy_score_dir / f"{definition['strategy_id']}.csv"
        score_frame = build_strategy_score_file(
            definition,
            factor_scores_path=factor_scores_path,
            ml_factor_scores_path=ml_factor_scores_path,
            output_path=score_path,
        )
        if score_frame.empty:
            continue

        output_dir = backtest_root / definition["strategy_id"]
        result = run_backtest(
            price_path=price_path,
            factor_scores_path=score_path,
            output_dir=output_dir,
            top_n=top_n,
            transaction_cost_bps=transaction_cost_bps,
        )
        summary = result["summary"].iloc[0].to_dict()
        summary_rows.append(
            {
                "strategy_id": definition["strategy_id"],
                "strategy_name": definition["strategy_name"],
                "category": definition["category"],
                "description": definition["description"],
                **summary,
            }
        )
        split_rows.extend(
            _split_metrics(
                result["daily_returns"],
                definition,
            )
        )

    summary_table = pd.DataFrame(summary_rows)
    split_table = pd.DataFrame(split_rows)
    summary_table = summary_table.sort_values(
        ["information_ratio", "sharpe", "cagr"],
        ascending=False,
    )
    summary_output_path = Path(summary_output_path)
    split_summary_output_path = Path(split_summary_output_path)
    summary_output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_table.to_csv(summary_output_path, index=False, encoding="utf-8-sig")
    split_table.to_csv(split_summary_output_path, index=False, encoding="utf-8-sig")

    report_output_path = Path(report_output_path)
    report_output_path.parent.mkdir(parents=True, exist_ok=True)
    report_output_path.write_text(
        _build_strategy_lab_report(definitions, summary_table, split_table),
        encoding="utf-8",
    )
    return {
        "definitions": definitions,
        "summary": summary_table,
        "split_summary": split_table,
    }


def build_strategy_score_file(
    definition: dict,
    *,
    factor_scores_path: str | Path,
    ml_factor_scores_path: str | Path,
    output_path: str | Path,
) -> pd.DataFrame:
    """Create a score file compatible with the monthly backtest engine."""
    if definition.get("source") == "ml":
        frame = pd.read_csv(
            ml_factor_scores_path,
            dtype={"ticker": "string"},
            parse_dates=["signal_date"],
        )
        frame["ticker"] = frame["ticker"].astype("string").str.zfill(6)
        if "predicted_excess_forward_1m_return" in frame.columns:
            frame["composite_score"] = frame["predicted_excess_forward_1m_return"]
        frame["strategy_id"] = definition["strategy_id"]
        frame["strategy_name"] = definition["strategy_name"]
    else:
        frame = pd.read_csv(
            factor_scores_path,
            dtype={"ticker": "string"},
            parse_dates=["signal_date"],
        )
        frame["ticker"] = frame["ticker"].astype("string").str.zfill(6)
        frame = calculate_composite_score(
            frame.drop(
                columns=["composite_score", "composite_weight_coverage"],
                errors="ignore",
            ),
            weights=definition["weights"],
        )
        frame["strategy_id"] = definition["strategy_id"]
        frame["strategy_name"] = definition["strategy_name"]

    frame = frame.dropna(subset=["signal_date", "composite_score"])
    frame = frame.sort_values(["signal_date", "composite_score"], ascending=[True, False])
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False, encoding="utf-8-sig")
    return frame


def _split_metrics(daily_returns: pd.DataFrame, definition: dict) -> list[dict]:
    daily = daily_returns.copy()
    daily["date"] = pd.to_datetime(daily["date"])
    rows = []
    for split_name, start, end in SPLITS:
        mask = daily["date"].between(pd.Timestamp(start), pd.Timestamp(end))
        subset = daily.loc[mask]
        if subset.empty:
            continue
        metrics = calculate_performance_metrics(
            subset["strategy_return"],
            subset["benchmark_return"],
        )
        rows.append(
            {
                "strategy_id": definition["strategy_id"],
                "strategy_name": definition["strategy_name"],
                "category": definition["category"],
                "period": split_name,
                "start_date": subset["date"].min().date(),
                "end_date": subset["date"].max().date(),
                **metrics,
            }
        )
    return rows


def _build_strategy_lab_report(
    definitions: pd.DataFrame,
    summary: pd.DataFrame,
    split_summary: pd.DataFrame,
) -> str:
    top = summary.head(5).copy()
    test = split_summary[split_summary["period"].eq("test_2022_2026")].copy()
    test = test.sort_values(["information_ratio", "sharpe", "cagr"], ascending=False)
    return (
        "# Practical Quant Strategy Lab\n\n"
        "실무에서 자주 쓰이는 주식 퀀트 전략 10가지를 동일한 데이터, 동일한 월간 리밸런싱, "
        "동일한 Top 30 동일가중 조건으로 비교했다. 이 실험은 특정 전략을 바로 매수 추천하기보다, "
        "어떤 투자 아이디어가 한국 대형주 장기 데이터에서 더 견고했는지 확인하기 위한 연구용이다.\n\n"
        "## Tested Strategies\n\n"
        f"{_markdown_table(definitions)}\n\n"
        "## Full-Period Ranking\n\n"
        f"{_markdown_table(_format_summary(top))}\n\n"
        "## Test-Period Ranking: 2022~2026\n\n"
        f"{_markdown_table(_format_split(test.head(10)))}\n\n"
        "## Interpretation\n\n"
        "- 단일 팩터는 특정 국면에서 강하지만 장기 성과와 낙폭 안정성이 흔들릴 수 있다.\n"
        "- 실무 운용에서는 단일 팩터보다 Value+Momentum, Quality+Low Vol, Balanced Multi-Factor처럼 "
        "서로 다른 성격의 신호를 결합하는 방식이 더 설명 가능하고 관리하기 쉽다.\n"
        "- ML 예측 전략은 알파 잠재력이 크지만 과적합, 회전율, 낙폭 위험을 별도로 통제해야 한다.\n"
        "- 다음 단계에서는 각 전략별 월별 승률, 하락장 성과, 업종 노출, 회전율과 거래비용 민감도를 추가해야 한다.\n"
    )


def _format_summary(frame: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "strategy_name",
        "category",
        "total_return",
        "cagr",
        "annualized_volatility",
        "sharpe",
        "max_drawdown",
        "active_total_return",
        "information_ratio",
        "average_turnover",
    ]
    return _format_metrics(frame[columns].copy())


def _format_split(frame: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "strategy_name",
        "category",
        "period",
        "total_return",
        "cagr",
        "annualized_volatility",
        "sharpe",
        "max_drawdown",
        "active_total_return",
        "information_ratio",
    ]
    return _format_metrics(frame[columns].copy())


def _format_metrics(frame: pd.DataFrame) -> pd.DataFrame:
    percent_columns = [
        "total_return",
        "cagr",
        "annualized_volatility",
        "max_drawdown",
        "active_total_return",
        "average_turnover",
    ]
    for column in percent_columns:
        if column in frame:
            frame[column] = frame[column].map(lambda value: f"{value:.2%}")
    for column in ["sharpe", "information_ratio"]:
        if column in frame:
            frame[column] = frame[column].map(lambda value: f"{value:.2f}")
    return frame


def _format_weights(item: dict) -> str:
    if item.get("source") == "ml":
        return "ml_predicted_excess_forward_1m_return=1.00"
    return ", ".join(f"{key}={value:.2f}" for key, value in item["weights"].items())


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No data available."
    display = frame.copy()
    headers = [str(column) for column in display.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in display.astype(str).values.tolist():
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)
