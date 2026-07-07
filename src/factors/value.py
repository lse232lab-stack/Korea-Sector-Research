"""Value factor calculations."""

from __future__ import annotations

import pandas as pd

from src.factors.common import composite_average, cross_sectional_score


VALUE_METRICS = {
    "per": False,
    "pbr": False,
    "psr": False,
    "ev_ebitda": False,
}


def calculate_value_factor(fundamentals: pd.DataFrame) -> pd.DataFrame:
    """Calculate cross-sectional value factor scores."""
    frame = fundamentals.copy()
    available_metrics = [metric for metric in VALUE_METRICS if metric in frame.columns]

    score_columns = []
    for metric in available_metrics:
        score_col = f"{metric}_value_z"
        frame[score_col] = cross_sectional_score(
            frame,
            group_col="available_date",
            metric_col=metric,
            higher_is_better=VALUE_METRICS[metric],
        )
        if frame[score_col].notna().any():
            score_columns.append(score_col)

    frame["value_score"] = composite_average(frame, score_columns)
    return frame[["ticker", "available_date", "fiscal_period", *score_columns, "value_score"]]
