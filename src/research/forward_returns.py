"""Build forward-return targets for factor validation and ranking."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.data.price_loader import load_prices


def build_factor_forward_returns(
    factor_scores_path: str | Path = "data/features/integrated_factor_scores.csv",
    price_path: str | Path = "data/raw/price/prices.csv",
    *,
    output_path: str | Path = "data/features/factor_forward_returns.csv",
    horizons: tuple[int, ...] = (1, 3),
) -> pd.DataFrame:
    """Attach forward monthly returns to each factor signal row."""
    factors = pd.read_csv(
        factor_scores_path,
        dtype={"ticker": "string"},
        parse_dates=["signal_date"],
    )
    prices = load_prices(str(price_path))
    factors["ticker"] = factors["ticker"].astype("string").str.zfill(6)
    prices["ticker"] = prices["ticker"].astype("string").str.zfill(6)
    prices["date"] = pd.to_datetime(prices["date"])

    price_matrix = (
        prices.pivot_table(index="date", columns="ticker", values="adj_close", aggfunc="last")
        .sort_index()
        .ffill()
    )
    signal_dates = sorted(
        date for date in factors["signal_date"].dropna().unique() if date in price_matrix.index
    )
    signal_index = {date: index for index, date in enumerate(signal_dates)}

    output = factors.copy()
    output = output[output["signal_date"].isin(signal_index)].copy()
    output["signal_index"] = output["signal_date"].map(signal_index)

    for horizon in horizons:
        column = f"forward_{horizon}m_return"
        benchmark_column = f"benchmark_forward_{horizon}m_return"
        excess_column = f"excess_forward_{horizon}m_return"
        target_dates = {
            signal_date: signal_dates[index + horizon]
            for signal_date, index in signal_index.items()
            if index + horizon < len(signal_dates)
        }
        output[f"target_{horizon}m_date"] = output["signal_date"].map(target_dates)
        output[column] = output.apply(
            lambda row: _forward_return(
                price_matrix,
                row["ticker"],
                row["signal_date"],
                row[f"target_{horizon}m_date"],
            ),
            axis=1,
        )
        benchmark_returns = {
            signal_date: _equal_weight_forward_return(price_matrix, signal_date, target_date)
            for signal_date, target_date in target_dates.items()
        }
        output[benchmark_column] = output["signal_date"].map(benchmark_returns)
        output[excess_column] = output[column] - output[benchmark_column]

    output = output.drop(columns=["signal_index"])
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output


def _forward_return(
    price_matrix: pd.DataFrame,
    ticker: str,
    signal_date: pd.Timestamp,
    target_date: pd.Timestamp | pd.NaT,
) -> float | None:
    if pd.isna(target_date) or ticker not in price_matrix.columns:
        return None
    start = price_matrix.at[signal_date, ticker]
    end = price_matrix.at[target_date, ticker]
    if pd.isna(start) or pd.isna(end) or start == 0:
        return None
    return float(end / start - 1.0)


def _equal_weight_forward_return(
    price_matrix: pd.DataFrame,
    signal_date: pd.Timestamp,
    target_date: pd.Timestamp,
) -> float | None:
    start = price_matrix.loc[signal_date]
    end = price_matrix.loc[target_date]
    returns = end / start - 1.0
    returns = returns.replace([float("inf"), -float("inf")], pd.NA).dropna()
    if returns.empty:
        return None
    return float(returns.mean())
