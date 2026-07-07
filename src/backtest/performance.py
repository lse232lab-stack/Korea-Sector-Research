"""Performance metrics."""

from __future__ import annotations

import math

import pandas as pd

from src.backtest.risk import calculate_drawdown


def calculate_performance_metrics(
    returns: pd.Series,
    benchmark_returns: pd.Series | None = None,
    *,
    periods_per_year: int = 252,
) -> dict[str, float]:
    """Calculate standard daily-return performance metrics."""
    clean_returns = pd.Series(returns).dropna()
    if clean_returns.empty:
        return {
            "days": 0,
            "total_return": 0.0,
            "cagr": 0.0,
            "annualized_volatility": 0.0,
            "sharpe": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
        }

    total_return = float((1.0 + clean_returns).prod() - 1.0)
    years = len(clean_returns) / periods_per_year
    cagr = (1.0 + total_return) ** (1.0 / years) - 1.0 if years > 0 else 0.0
    volatility = float(clean_returns.std(ddof=0) * math.sqrt(periods_per_year))
    sharpe = float(cagr / volatility) if volatility else 0.0
    max_drawdown = float(calculate_drawdown(clean_returns)["drawdown"].min())
    win_rate = float((clean_returns > 0).mean())

    metrics = {
        "days": int(len(clean_returns)),
        "total_return": total_return,
        "cagr": float(cagr),
        "annualized_volatility": volatility,
        "sharpe": sharpe,
        "max_drawdown": max_drawdown,
        "win_rate": win_rate,
    }

    if benchmark_returns is not None:
        aligned = pd.concat(
            [
                clean_returns.rename("strategy"),
                pd.Series(benchmark_returns).rename("benchmark"),
            ],
            axis=1,
        ).dropna()
        if not aligned.empty:
            active = aligned["strategy"] - aligned["benchmark"]
            tracking_error = float(active.std(ddof=0) * math.sqrt(periods_per_year))
            active_total = float(
                (1.0 + aligned["strategy"]).prod()
                / (1.0 + aligned["benchmark"]).prod()
                - 1.0
            )
            information_ratio = (
                float(active.mean() * periods_per_year / tracking_error)
                if tracking_error
                else 0.0
            )
            metrics.update(
                {
                    "benchmark_total_return": float(
                        (1.0 + aligned["benchmark"]).prod() - 1.0
                    ),
                    "active_total_return": active_total,
                    "tracking_error": tracking_error,
                    "information_ratio": information_ratio,
                }
            )

    return metrics
