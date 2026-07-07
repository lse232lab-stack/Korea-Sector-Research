"""Integrated multi-factor score construction."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.factors.composite import calculate_composite_score


def build_integrated_factor_scores(
    fundamental_factor_path: str | Path = "data/features/factor_scores.csv",
    price_factor_path: str | Path = "data/features/price_factor_scores.csv",
    *,
    output_path: str | Path = "data/features/integrated_factor_scores.csv",
    coverage_output_path: str | Path = "outputs/tables/integrated_factor_score_coverage.csv",
) -> pd.DataFrame:
    """Join latest available fundamental factors to each monthly price signal."""
    fundamentals = pd.read_csv(
        fundamental_factor_path,
        dtype={"ticker": "string"},
        parse_dates=["available_date"],
    )
    prices = pd.read_csv(
        price_factor_path,
        dtype={"ticker": "string"},
        parse_dates=["signal_date"],
    )

    fundamentals["ticker"] = fundamentals["ticker"].astype("string").str.zfill(6)
    prices["ticker"] = prices["ticker"].astype("string").str.zfill(6)
    fundamentals = fundamentals.sort_values(["ticker", "available_date"])
    prices = prices.sort_values(["ticker", "signal_date"])

    joined_parts = []
    fundamental_columns = [
        "ticker",
        "name",
        "available_date",
        "fiscal_period",
        "value_score",
        "quality_score",
        "growth_score",
    ]
    price_columns = [
        "ticker",
        "signal_date",
        "return_6m",
        "return_12m_ex_1m",
        "momentum_score",
        "volatility_1y",
        "max_drawdown_1y",
        "low_volatility_score",
    ]

    for ticker, price_group in prices[price_columns].groupby("ticker", sort=False):
        fundamental_group = fundamentals.loc[
            fundamentals["ticker"] == ticker,
            fundamental_columns,
        ]
        if fundamental_group.empty:
            enriched = price_group.copy()
            enriched["name"] = pd.NA
            enriched["available_date"] = pd.NaT
            enriched["fiscal_period"] = pd.NA
            enriched["value_score"] = pd.NA
            enriched["quality_score"] = pd.NA
            enriched["growth_score"] = pd.NA
        else:
            enriched = pd.merge_asof(
                price_group.sort_values("signal_date"),
                fundamental_group.sort_values("available_date"),
                left_on="signal_date",
                right_on="available_date",
                by="ticker",
                direction="backward",
            )
        joined_parts.append(enriched)

    if joined_parts:
        scores = pd.concat(joined_parts, ignore_index=True)
    else:
        scores = pd.DataFrame(columns=price_columns + fundamental_columns)

    scores = calculate_composite_score(scores)
    scores["factor_scope"] = "integrated_value_quality_growth_momentum_low_volatility"
    scores = scores.sort_values(["signal_date", "composite_score"], ascending=[True, False])

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    scores.to_csv(output_path, index=False, encoding="utf-8-sig")

    coverage = (
        scores.groupby("signal_date", as_index=False)
        .agg(
            rows=("ticker", "size"),
            tickers=("ticker", "nunique"),
            value_score_missing=("value_score", lambda series: int(series.isna().sum())),
            quality_score_missing=("quality_score", lambda series: int(series.isna().sum())),
            growth_score_missing=("growth_score", lambda series: int(series.isna().sum())),
            momentum_score_missing=("momentum_score", lambda series: int(series.isna().sum())),
            low_volatility_score_missing=(
                "low_volatility_score",
                lambda series: int(series.isna().sum()),
            ),
            composite_score_missing=("composite_score", lambda series: int(series.isna().sum())),
            average_weight_coverage=("composite_weight_coverage", "mean"),
        )
        .sort_values("signal_date")
    )
    coverage_output_path = Path(coverage_output_path)
    coverage_output_path.parent.mkdir(parents=True, exist_ok=True)
    coverage.to_csv(coverage_output_path, index=False, encoding="utf-8-sig")
    return scores
