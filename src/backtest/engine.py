"""Monthly portfolio backtest engine."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.backtest.performance import calculate_performance_metrics
from src.backtest.risk import calculate_drawdown
from src.data.benchmark_loader import load_benchmark_returns
from src.data.price_loader import load_prices


def run_backtest(
    price_path: str | Path = "data/raw/price/prices.csv",
    factor_scores_path: str | Path = "data/features/price_factor_scores.csv",
    *,
    output_dir: str | Path = "outputs/backtest",
    benchmark_path: str | Path | None = None,
    top_n: int = 30,
    transaction_cost_bps: float = 10.0,
) -> dict[str, pd.DataFrame]:
    """Run a monthly top-N equal-weight backtest from price factor scores."""
    prices = load_prices(str(price_path))
    factors = pd.read_csv(
        factor_scores_path,
        dtype={"ticker": "string"},
        parse_dates=["signal_date"],
    )

    prices["ticker"] = prices["ticker"].astype("string").str.zfill(6)
    prices["date"] = pd.to_datetime(prices["date"])
    factors["ticker"] = factors["ticker"].astype("string").str.zfill(6)
    factors = factors.dropna(subset=["signal_date", "composite_score"])

    price_matrix = (
        prices.pivot_table(
            index="date",
            columns="ticker",
            values="adj_close",
            aggfunc="last",
        )
        .sort_index()
        .ffill()
    )
    daily_returns = price_matrix.pct_change(fill_method=None)
    trading_dates = pd.Index(daily_returns.index)

    signal_dates = [
        signal_date
        for signal_date in sorted(factors["signal_date"].dropna().unique())
        if signal_date < trading_dates.max()
    ]
    portfolio_returns = pd.Series(0.0, index=trading_dates, name="strategy_return")
    if benchmark_path:
        benchmark_returns = load_benchmark_returns(benchmark_path).reindex(trading_dates).ffill()
        benchmark_type = "external_benchmark"
    else:
        benchmark_returns = daily_returns.mean(axis=1, skipna=True)
        benchmark_type = "universe_equal_weight"
    benchmark_returns = benchmark_returns.rename("benchmark_return")
    rebalance_rows = []
    previous_weights: dict[str, float] = {}

    for index, signal_date in enumerate(signal_dates):
        current_scores = factors[factors["signal_date"] == signal_date].copy()
        target_exposure = _target_exposure(current_scores)
        selected = (
            current_scores.sort_values("composite_score", ascending=False)
            .head(top_n)["ticker"]
            .tolist()
        )
        selected = [ticker for ticker in selected if ticker in daily_returns.columns]
        if not selected:
            continue

        weights = {ticker: target_exposure / len(selected) for ticker in selected}
        next_signal_date = (
            signal_dates[index + 1] if index + 1 < len(signal_dates) else trading_dates.max()
        )
        period_dates = trading_dates[(trading_dates > signal_date) & (trading_dates <= next_signal_date)]
        if period_dates.empty:
            continue

        period_returns = daily_returns.loc[period_dates, selected].mul(
            pd.Series(weights),
            axis=1,
        )
        portfolio_returns.loc[period_dates] = period_returns.sum(axis=1, min_count=1).fillna(0.0)

        turnover = _calculate_turnover(previous_weights, weights)
        first_date = period_dates[0]
        portfolio_returns.loc[first_date] -= turnover * transaction_cost_bps / 10_000
        rebalance_rows.append(
            {
                "signal_date": signal_date,
                "first_return_date": first_date,
                "next_signal_date": next_signal_date,
                "holding_days": int(len(period_dates)),
                "selected_tickers": ",".join(selected),
                "selected_count": int(len(selected)),
                "target_exposure": float(target_exposure),
                "cash_weight": float(max(0.0, 1.0 - target_exposure)),
                "regime": _regime_label(current_scores),
                "turnover": float(turnover),
                "transaction_cost_bps": float(transaction_cost_bps),
            }
        )
        previous_weights = weights

    active_mask = portfolio_returns.ne(0.0)
    if active_mask.any():
        first_active_date = portfolio_returns[active_mask].index.min()
        portfolio_returns = portfolio_returns.loc[first_active_date:]
        benchmark_returns = benchmark_returns.loc[first_active_date:]

    metrics = calculate_performance_metrics(portfolio_returns, benchmark_returns)
    rebalance_log = pd.DataFrame(rebalance_rows)
    if not rebalance_log.empty:
        metrics["average_turnover"] = float(rebalance_log["turnover"].mean())
        metrics["rebalance_count"] = int(len(rebalance_log))
    else:
        metrics["average_turnover"] = 0.0
        metrics["rebalance_count"] = 0
    metrics["benchmark_type"] = benchmark_type
    metrics["benchmark_path"] = str(benchmark_path) if benchmark_path else ""

    summary = pd.DataFrame([metrics])
    curve = calculate_drawdown(portfolio_returns)
    curve.index.name = "date"
    curve = curve.reset_index()
    daily = pd.concat(
        [
            portfolio_returns.rename("strategy_return"),
            benchmark_returns.rename("benchmark_return"),
        ],
        axis=1,
    ).reset_index(names="date")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    daily.to_csv(output_dir / "backtest_daily_returns.csv", index=False, encoding="utf-8-sig")
    curve.to_csv(output_dir / "backtest_equity_curve.csv", index=False, encoding="utf-8-sig")
    rebalance_log.to_csv(output_dir / "backtest_rebalance_log.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(output_dir / "backtest_summary.csv", index=False, encoding="utf-8-sig")

    return {
        "daily_returns": daily,
        "equity_curve": curve,
        "rebalance_log": rebalance_log,
        "summary": summary,
    }


def _calculate_turnover(
    previous_weights: dict[str, float],
    current_weights: dict[str, float],
) -> float:
    if not previous_weights:
        return 1.0
    tickers = set(previous_weights) | set(current_weights)
    return 0.5 * sum(
        abs(current_weights.get(ticker, 0.0) - previous_weights.get(ticker, 0.0))
        for ticker in tickers
    )


def _target_exposure(scores: pd.DataFrame) -> float:
    if "target_exposure" not in scores.columns:
        return 1.0
    exposure = pd.to_numeric(scores["target_exposure"], errors="coerce").dropna()
    if exposure.empty:
        return 1.0
    return float(exposure.iloc[0])


def _regime_label(scores: pd.DataFrame) -> str:
    if "regime" not in scores.columns:
        return ""
    labels = scores["regime"].dropna()
    return str(labels.iloc[0]) if not labels.empty else ""
