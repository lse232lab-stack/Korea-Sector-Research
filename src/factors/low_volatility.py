"""Low volatility factor calculations."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.factors.common import composite_average, cross_sectional_score


def calculate_low_volatility_factor(prices: pd.DataFrame, benchmark=None) -> pd.DataFrame:
    """Calculate month-end low-volatility factor scores from daily prices."""
    frame = prices.copy().sort_values(["ticker", "date"])
    frame["daily_return"] = frame.groupby("ticker")["adj_close"].pct_change()
    frame["volatility_1y"] = (
        frame.groupby("ticker")["daily_return"]
        .rolling(252, min_periods=126)
        .std()
        .reset_index(level=0, drop=True)
        * np.sqrt(252)
    )
    frame["max_drawdown_1y"] = (
        frame.groupby("ticker")["adj_close"]
        .rolling(252, min_periods=126)
        .apply(_max_drawdown, raw=False)
        .reset_index(level=0, drop=True)
    )

    month_end = (
        frame.groupby(["ticker", frame["date"].dt.to_period("M")], as_index=False)
        .tail(1)
        .copy()
    )
    month_end = month_end.rename(columns={"date": "signal_date"})

    score_columns = []
    for metric in ["volatility_1y", "max_drawdown_1y"]:
        score_col = f"{metric}_low_volatility_z"
        month_end[score_col] = cross_sectional_score(
            month_end,
            group_col="signal_date",
            metric_col=metric,
            higher_is_better=False,
        )
        if month_end[score_col].notna().any():
            score_columns.append(score_col)

    month_end["low_volatility_score"] = composite_average(month_end, score_columns)
    return month_end[
        [
            "ticker",
            "signal_date",
            "volatility_1y",
            "max_drawdown_1y",
            *score_columns,
            "low_volatility_score",
        ]
    ]


def _max_drawdown(series: pd.Series) -> float:
    cumulative_max = series.cummax()
    drawdown = series / cumulative_max - 1
    return float(drawdown.min())
