"""Construct model portfolios from composite scores."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.data.universe import load_universe
from src.portfolio.constraints import apply_portfolio_constraints, summarize_sector_exposure


def build_top_n_portfolio(
    composite_scores: pd.DataFrame,
    top_n: int = 30,
    method: str = "equal_weight",
) -> pd.DataFrame:
    """Build a top-N portfolio from one signal-date score table."""
    selected = composite_scores.sort_values("composite_score", ascending=False).head(top_n)
    selected = selected.copy()
    if selected.empty:
        selected["weight"] = pd.Series(dtype=float)
        return selected

    if method == "equal_weight":
        selected["weight"] = 1 / len(selected)
    elif method == "score_weight":
        positive = selected["composite_score"].clip(lower=0)
        if positive.sum() == 0:
            selected["weight"] = 1 / len(selected)
        else:
            selected["weight"] = positive / positive.sum()
    else:
        raise ValueError(f"Unsupported weighting method: {method}")

    selected["weighting_method"] = method
    return selected


def build_kospi200_model_portfolio_preview(
    factor_scores_path: str | Path = "data/features/factor_scores.csv",
    universe_path: str | Path = "data/raw/benchmark/kospi200_constituents.csv",
    *,
    output_path: str | Path = "outputs/portfolios/kospi200_model_portfolio_preview.csv",
    sector_exposure_output_path: str | Path = "outputs/tables/kospi200_portfolio_sector_exposure.csv",
    top_n: int = 30,
    minimum_tickers_for_signal_date: int = 100,
    max_single_name_weight: float = 0.05,
    max_sector_weight: float = 0.25,
) -> pd.DataFrame:
    """Build a KOSPI200-filtered Value/Quality MVP portfolio preview."""
    scores = pd.read_csv(
        factor_scores_path,
        dtype={"ticker": "string"},
        parse_dates=["available_date"],
    )
    universe = load_universe(str(universe_path))
    universe_tickers = set(universe["ticker"].astype("string").str.zfill(6))

    coverage = (
        scores.groupby("available_date", as_index=False)
        .agg(tickers=("ticker", "nunique"))
        .sort_values("available_date")
    )
    broad_dates = coverage.loc[
        coverage["tickers"] >= minimum_tickers_for_signal_date,
        "available_date",
    ]
    signal_date = broad_dates.max() if not broad_dates.empty else scores["available_date"].max()

    signal_scores = scores[
        (scores["available_date"] == signal_date)
        & (scores["ticker"].astype("string").str.zfill(6).isin(universe_tickers))
    ].copy()
    signal_scores = signal_scores.merge(
        universe[["ticker", "sector"]],
        on="ticker",
        how="left",
        suffixes=("", "_universe"),
    )
    if "sector_universe" in signal_scores.columns:
        signal_scores["sector"] = signal_scores["sector_universe"]
        signal_scores = signal_scores.drop(columns=["sector_universe"])

    equal_weight = apply_portfolio_constraints(
        build_top_n_portfolio(signal_scores, top_n=top_n, method="equal_weight"),
        max_single_name_weight=max_single_name_weight,
        max_sector_weight=max_sector_weight,
    )
    score_weight = apply_portfolio_constraints(
        build_top_n_portfolio(signal_scores, top_n=top_n, method="score_weight"),
        max_single_name_weight=max_single_name_weight,
        max_sector_weight=max_sector_weight,
    )
    portfolio = pd.concat([equal_weight, score_weight], ignore_index=True)
    portfolio["portfolio_note"] = (
        "KOSPI200 current-universe Value/Quality MVP preview. Momentum, Low Volatility, "
        "liquidity and transaction costs are not applied yet."
    )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    portfolio.to_csv(output_path, index=False, encoding="utf-8-sig")

    sector_exposure_output_path = Path(sector_exposure_output_path)
    sector_exposure_output_path.parent.mkdir(parents=True, exist_ok=True)
    summarize_sector_exposure(portfolio).to_csv(
        sector_exposure_output_path,
        index=False,
        encoding="utf-8-sig",
    )
    return portfolio
