"""Composite score calculation."""

from __future__ import annotations

import pandas as pd


def calculate_composite_score(
    factor_scores: pd.DataFrame,
    weights: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Calculate available-factor weighted composite score.

    Missing factor families are ignored and remaining weights are renormalized.
    This allows the MVP to produce a transparent Value/Quality partial score
    before Momentum and Low Volatility are implemented.
    """
    weights = weights or {
        "quality_score": 0.25,
        "value_score": 0.25,
        "momentum_score": 0.20,
        "low_volatility_score": 0.20,
        "growth_score": 0.10,
    }
    frame = factor_scores.copy()
    available = [column for column in weights if column in frame.columns]
    if not available:
        frame["composite_score"] = pd.NA
        frame["composite_weight_coverage"] = 0.0
        return frame

    weighted_sum = pd.Series(0.0, index=frame.index)
    row_weight_sum = pd.Series(0.0, index=frame.index)
    for column in available:
        valid = frame[column].notna()
        weighted_sum = weighted_sum.add(frame[column].fillna(0.0) * weights[column])
        row_weight_sum = row_weight_sum.add(valid.astype(float) * weights[column])
    frame["composite_score"] = weighted_sum / row_weight_sum.replace(0.0, pd.NA)
    frame["composite_weight_coverage"] = row_weight_sum
    return frame
