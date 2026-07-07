"""Risk analysis utilities."""

from __future__ import annotations

import pandas as pd


def calculate_drawdown(returns: pd.Series) -> pd.DataFrame:
    """Calculate cumulative wealth, running peak, and drawdown series."""
    clean_returns = pd.Series(returns).fillna(0.0)
    wealth = (1.0 + clean_returns).cumprod()
    peak = wealth.cummax()
    drawdown = wealth / peak - 1.0
    return pd.DataFrame(
        {
            "equity_curve": wealth,
            "running_peak": peak,
            "drawdown": drawdown,
        }
    )
