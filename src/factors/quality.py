"""Quality factor calculations."""

from __future__ import annotations

import pandas as pd

from src.factors.common import composite_average, cross_sectional_score


QUALITY_METRICS = {
    "roe": True,
    "roa": True,
    "operating_margin": True,
    "debt_ratio": False,
    "operating_cash_flow_to_net_income": True,
}


def calculate_quality_factor(fundamentals: pd.DataFrame) -> pd.DataFrame:
    """Calculate cross-sectional quality factor scores."""
    frame = fundamentals.copy()
    available_metrics = [metric for metric in QUALITY_METRICS if metric in frame.columns]

    score_columns = []
    for metric in available_metrics:
        score_col = f"{metric}_quality_z"
        frame[score_col] = cross_sectional_score(
            frame,
            group_col="available_date",
            metric_col=metric,
            higher_is_better=QUALITY_METRICS[metric],
        )
        if frame[score_col].notna().any():
            score_columns.append(score_col)

    frame["quality_score"] = composite_average(frame, score_columns)
    return frame[
        ["ticker", "available_date", "fiscal_period", *score_columns, "quality_score"]
    ]
