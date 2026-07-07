"""Factor build pipeline."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.data.price_loader import load_prices
from src.data.ts2000_loader import load_fundamentals
from src.factors.composite import calculate_composite_score
from src.factors.growth import calculate_growth_factor
from src.factors.low_volatility import calculate_low_volatility_factor
from src.factors.momentum import calculate_momentum_factor
from src.factors.quality import calculate_quality_factor
from src.factors.value import calculate_value_factor


def build_fundamental_factor_scores(
    fundamentals_path: str | Path = "data/raw/ts2000/fundamentals.csv",
    *,
    output_path: str | Path = "data/features/factor_scores.csv",
    tables_dir: str | Path = "outputs/tables",
    portfolios_dir: str | Path = "outputs/portfolios",
    minimum_tickers_for_preview: int = 100,
) -> pd.DataFrame:
    """Build Value/Quality factor scores from standardized fundamentals."""
    fundamentals = load_fundamentals(str(fundamentals_path))
    base_columns = [
        "ticker",
        "name",
        "available_date",
        "fiscal_period",
        "pbr",
        "per",
        "roe",
        "roa",
        "debt_ratio",
        "operating_cash_flow_to_net_income",
        "sales_growth",
        "asset_growth",
    ]
    base = fundamentals[[column for column in base_columns if column in fundamentals.columns]].copy()

    value = calculate_value_factor(fundamentals)
    quality = calculate_quality_factor(fundamentals)
    growth = calculate_growth_factor(fundamentals)
    scores = (
        base.merge(value, on=["ticker", "available_date", "fiscal_period"], how="left")
        .merge(quality, on=["ticker", "available_date", "fiscal_period"], how="left")
        .merge(growth, on=["ticker", "available_date", "fiscal_period"], how="left")
    )
    scores = calculate_composite_score(scores)
    scores["factor_scope"] = "fundamental_value_quality_growth"
    scores = scores.sort_values(["available_date", "composite_score"], ascending=[True, False])

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    scores.to_csv(output_path, index=False, encoding="utf-8-sig")

    tables_dir = Path(tables_dir)
    portfolios_dir = Path(portfolios_dir)
    tables_dir.mkdir(parents=True, exist_ok=True)
    portfolios_dir.mkdir(parents=True, exist_ok=True)
    _write_factor_outputs(
        scores,
        tables_dir=tables_dir,
        portfolios_dir=portfolios_dir,
        minimum_tickers_for_preview=minimum_tickers_for_preview,
    )
    return scores


def build_price_factor_scores(
    price_path: str | Path = "data/raw/price/prices.csv",
    *,
    output_path: str | Path = "data/features/price_factor_scores.csv",
    tables_dir: str | Path = "outputs/tables",
) -> pd.DataFrame:
    """Build Momentum/Low Volatility factor scores from available prices."""
    prices = load_prices(str(price_path))
    momentum = calculate_momentum_factor(prices)
    low_volatility = calculate_low_volatility_factor(prices)
    scores = momentum.merge(
        low_volatility,
        on=["ticker", "signal_date"],
        how="outer",
    )
    scores = calculate_composite_score(scores)
    scores["factor_scope"] = "price_momentum_low_volatility_sample"
    scores = scores.sort_values(["signal_date", "composite_score"], ascending=[True, False])

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    scores.to_csv(output_path, index=False, encoding="utf-8-sig")

    tables_dir = Path(tables_dir)
    tables_dir.mkdir(parents=True, exist_ok=True)
    coverage = (
        scores.groupby("signal_date", as_index=False)
        .agg(
            rows=("ticker", "size"),
            tickers=("ticker", "nunique"),
            momentum_score_missing=("momentum_score", lambda series: int(series.isna().sum())),
            low_volatility_score_missing=(
                "low_volatility_score",
                lambda series: int(series.isna().sum()),
            ),
            composite_score_missing=(
                "composite_score",
                lambda series: int(series.isna().sum()),
            ),
        )
        .sort_values("signal_date")
    )
    coverage.to_csv(
        tables_dir / "price_factor_score_coverage.csv",
        index=False,
        encoding="utf-8-sig",
    )
    return scores


def _write_factor_outputs(
    scores: pd.DataFrame,
    *,
    tables_dir: Path,
    portfolios_dir: Path,
    minimum_tickers_for_preview: int,
) -> None:
    coverage = (
        scores.groupby("available_date", as_index=False)
        .agg(
            rows=("ticker", "size"),
            tickers=("ticker", "nunique"),
            value_score_missing=("value_score", lambda series: int(series.isna().sum())),
            quality_score_missing=("quality_score", lambda series: int(series.isna().sum())),
            growth_score_missing=("growth_score", lambda series: int(series.isna().sum())),
            composite_score_missing=(
                "composite_score",
                lambda series: int(series.isna().sum()),
            ),
        )
        .sort_values("available_date")
    )
    coverage.to_csv(
        tables_dir / "factor_score_coverage.csv",
        index=False,
        encoding="utf-8-sig",
    )

    broad_dates = coverage.loc[
        coverage["tickers"] >= minimum_tickers_for_preview,
        "available_date",
    ]
    if broad_dates.empty:
        preview_date = scores["available_date"].max()
    else:
        preview_date = broad_dates.max()

    preview = (
        scores[scores["available_date"] == preview_date]
        .sort_values("composite_score", ascending=False)
        .head(30)
        .copy()
    )
    preview["preview_note"] = (
        "Fundamental Value/Quality MVP preview. "
        "Momentum, Low Volatility, KOSPI200 membership, liquidity, and sector constraints "
        "are not applied yet."
    )
    preview.to_csv(
        portfolios_dir / "current_model_portfolio_preview.csv",
        index=False,
        encoding="utf-8-sig",
    )
