"""Shared factor preprocessing utilities."""

from __future__ import annotations

import pandas as pd


def cross_sectional_score(
    frame: pd.DataFrame,
    *,
    group_col: str,
    metric_col: str,
    higher_is_better: bool,
    lower_quantile: float = 0.01,
    upper_quantile: float = 0.99,
) -> pd.Series:
    """Winsorize, median-fill, z-score, and align metric direction by group."""
    return frame.groupby(group_col, group_keys=False)[metric_col].apply(
        lambda series: _score_series(
            series,
            higher_is_better=higher_is_better,
            lower_quantile=lower_quantile,
            upper_quantile=upper_quantile,
        )
    )


def composite_average(frame: pd.DataFrame, columns: list[str]) -> pd.Series:
    """Average available z-score columns row-wise."""
    return frame[columns].mean(axis=1, skipna=True)


def _score_series(
    series: pd.Series,
    *,
    higher_is_better: bool,
    lower_quantile: float,
    upper_quantile: float,
) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().sum() < 3:
        return pd.Series(pd.NA, index=series.index, dtype="Float64")

    lower = numeric.quantile(lower_quantile)
    upper = numeric.quantile(upper_quantile)
    clipped = numeric.clip(lower=lower, upper=upper)
    filled = clipped.fillna(clipped.median())
    std = filled.std(ddof=0)
    if std == 0 or pd.isna(std):
        return pd.Series(0.0, index=series.index)

    zscore = (filled - filled.mean()) / std
    if not higher_is_better:
        zscore = -zscore
    return zscore
