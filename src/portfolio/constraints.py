"""Portfolio constraints."""

from __future__ import annotations

import pandas as pd


def apply_portfolio_constraints(
    portfolio: pd.DataFrame,
    *,
    weight_col: str = "weight",
    sector_col: str = "sector",
    max_single_name_weight: float = 0.05,
    max_sector_weight: float = 0.25,
    tolerance: float = 1e-10,
    max_iterations: int = 200,
) -> pd.DataFrame:
    """Apply single-name and sector caps by iterative redistribution."""
    constrained = portfolio.copy()
    if constrained.empty:
        constrained["constraint_note"] = ""
        return constrained

    constrained[weight_col] = constrained[weight_col].astype(float)
    constrained[sector_col] = constrained[sector_col].fillna("Unknown")
    constrained[weight_col] = constrained[weight_col] / constrained[weight_col].sum()

    for _ in range(max_iterations):
        before = constrained[weight_col].copy()

        constrained[weight_col] = constrained[weight_col].clip(upper=max_single_name_weight)
        _cap_sectors_in_place(
            constrained,
            weight_col=weight_col,
            sector_col=sector_col,
            max_sector_weight=max_sector_weight,
        )

        deficit = 1.0 - constrained[weight_col].sum()
        if deficit <= tolerance:
            break

        eligible = _eligible_for_redistribution(
            constrained,
            weight_col=weight_col,
            sector_col=sector_col,
            max_single_name_weight=max_single_name_weight,
            max_sector_weight=max_sector_weight,
            tolerance=tolerance,
        )
        if not eligible.any():
            break

        base = constrained.loc[eligible, weight_col].copy()
        if base.sum() <= 0:
            base[:] = 1.0
        additions = deficit * base / base.sum()
        constrained.loc[eligible, weight_col] += additions

        if (constrained[weight_col] - before).abs().sum() <= tolerance:
            break

    total = constrained[weight_col].sum()
    if total > 0:
        constrained[weight_col] = constrained[weight_col] / total
    constrained["constraint_note"] = (
        f"Applied max_single_name_weight={max_single_name_weight:.1%}, "
        f"max_sector_weight={max_sector_weight:.1%}."
    )
    return constrained


def summarize_sector_exposure(
    portfolio: pd.DataFrame,
    *,
    weight_col: str = "weight",
    sector_col: str = "sector",
) -> pd.DataFrame:
    """Summarize sector exposure by weighting method."""
    return (
        portfolio.assign(**{sector_col: portfolio[sector_col].fillna("Unknown")})
        .groupby(["weighting_method", sector_col], as_index=False)
        .agg(weight=(weight_col, "sum"), names=("ticker", "nunique"))
        .sort_values(["weighting_method", "weight"], ascending=[True, False])
    )


def _cap_sectors_in_place(
    frame: pd.DataFrame,
    *,
    weight_col: str,
    sector_col: str,
    max_sector_weight: float,
) -> None:
    sector_sums = frame.groupby(sector_col)[weight_col].transform("sum")
    over = sector_sums > max_sector_weight
    if over.any():
        frame.loc[over, weight_col] *= max_sector_weight / sector_sums[over]


def _eligible_for_redistribution(
    frame: pd.DataFrame,
    *,
    weight_col: str,
    sector_col: str,
    max_single_name_weight: float,
    max_sector_weight: float,
    tolerance: float,
) -> pd.Series:
    sector_sums = frame.groupby(sector_col)[weight_col].transform("sum")
    return (
        (frame[weight_col] < max_single_name_weight - tolerance)
        & (sector_sums < max_sector_weight - tolerance)
    )
