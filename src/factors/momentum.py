"""Momentum factor calculations."""

from __future__ import annotations

import pandas as pd

from src.factors.common import composite_average, cross_sectional_score


def calculate_momentum_factor(prices: pd.DataFrame, benchmark=None) -> pd.DataFrame:
    """Calculate month-end momentum factor scores from daily prices."""
    frame = prices.copy().sort_values(["ticker", "date"])
    frame["return_6m"] = frame.groupby("ticker")["adj_close"].pct_change(126)
    frame["return_12m_ex_1m"] = (
        frame.groupby("ticker")["adj_close"].shift(21)
        / frame.groupby("ticker")["adj_close"].shift(252)
        - 1
    )

    month_end = (
        frame.groupby(["ticker", frame["date"].dt.to_period("M")], as_index=False)
        .tail(1)
        .copy()
    )
    month_end = month_end.rename(columns={"date": "signal_date"})

    score_columns = []
    for metric in ["return_6m", "return_12m_ex_1m"]:
        score_col = f"{metric}_momentum_z"
        month_end[score_col] = cross_sectional_score(
            month_end,
            group_col="signal_date",
            metric_col=metric,
            higher_is_better=True,
        )
        if month_end[score_col].notna().any():
            score_columns.append(score_col)

    month_end["momentum_score"] = composite_average(month_end, score_columns)
    return month_end[
        [
            "ticker",
            "signal_date",
            "return_6m",
            "return_12m_ex_1m",
            *score_columns,
            "momentum_score",
        ]
    ]
