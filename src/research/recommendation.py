"""Latest factor-based recommendation candidate report."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.report.report_generator import _attach_names, _build_name_master


def build_latest_recommendation_candidates(
    factor_scores_path: str | Path = "data/features/integrated_factor_scores.csv",
    *,
    output_path: str | Path = "outputs/portfolios/latest_recommendation_candidates.csv",
    top_n: int = 30,
) -> pd.DataFrame:
    """Build latest top-ranked model portfolio candidate table."""
    scores = pd.read_csv(
        factor_scores_path,
        dtype={"ticker": "string"},
        parse_dates=["signal_date"],
    )
    latest_date = scores["signal_date"].max()
    latest = scores[scores["signal_date"] == latest_date].copy()
    latest = _attach_names(latest, _build_name_master())
    latest = latest.sort_values("composite_score", ascending=False).head(top_n)
    latest["rank"] = range(1, len(latest) + 1)
    latest["candidate_label"] = "factor_based_model_portfolio_candidate"
    latest["recommendation_note"] = latest.apply(_recommendation_note, axis=1)

    columns = [
        "rank",
        "ticker",
        "name",
        "signal_date",
        "composite_score",
        "value_score",
        "quality_score",
        "growth_score",
        "momentum_score",
        "low_volatility_score",
        "return_6m",
        "return_12m_ex_1m",
        "volatility_1y",
        "max_drawdown_1y",
        "candidate_label",
        "recommendation_note",
    ]
    existing_columns = [column for column in columns if column in latest.columns]
    output = latest[existing_columns].copy()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output


def _recommendation_note(row: pd.Series) -> str:
    notes = []
    if pd.notna(row.get("momentum_score")) and row["momentum_score"] > 1.0:
        notes.append("모멘텀 상위")
    if pd.notna(row.get("quality_score")) and row["quality_score"] > 0.5:
        notes.append("퀄리티 양호")
    if pd.notna(row.get("value_score")) and row["value_score"] > 0.0:
        notes.append("밸류에이션 우호")
    if pd.notna(row.get("growth_score")) and row["growth_score"] > 0.5:
        notes.append("성장성 양호")
    if pd.notna(row.get("low_volatility_score")) and row["low_volatility_score"] > 0.0:
        notes.append("저변동성 우호")
    if not notes:
        notes.append("통합 팩터 점수 상위")
    return ", ".join(notes)
