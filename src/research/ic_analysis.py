"""Rank IC analysis."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


DEFAULT_FACTOR_COLUMNS = [
    "value_score",
    "quality_score",
    "momentum_score",
    "low_volatility_score",
    "composite_score",
]


def calculate_rank_ic(
    factor_targets: pd.DataFrame,
    *,
    factor_columns: list[str] | None = None,
    target_column: str = "excess_forward_1m_return",
) -> pd.DataFrame:
    """Calculate monthly Spearman rank IC by factor."""
    factor_columns = factor_columns or DEFAULT_FACTOR_COLUMNS
    rows = []
    for signal_date, group in factor_targets.groupby("signal_date"):
        for factor in factor_columns:
            if factor not in group.columns or target_column not in group.columns:
                continue
            sample = group[[factor, target_column]].dropna()
            if len(sample) < 20:
                continue
            rows.append(
                {
                    "signal_date": signal_date,
                    "factor": factor,
                    "target": target_column,
                    "rank_ic": _spearman_without_scipy(sample[factor], sample[target_column]),
                    "n": int(len(sample)),
                }
            )
    return pd.DataFrame(rows).sort_values(["factor", "signal_date"]).reset_index(drop=True)


def _spearman_without_scipy(left: pd.Series, right: pd.Series) -> float:
    left_rank = left.rank(method="average")
    right_rank = right.rank(method="average")
    return float(left_rank.corr(right_rank, method="pearson"))


def write_rank_ic_outputs(
    factor_targets_path: str | Path = "data/features/factor_forward_returns.csv",
    *,
    output_path: str | Path = "outputs/tables/rank_ic_by_month.csv",
    summary_output_path: str | Path = "outputs/tables/rank_ic_summary.csv",
    target_column: str = "excess_forward_1m_return",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Write monthly Rank IC and factor-level summary tables."""
    factor_targets = pd.read_csv(
        factor_targets_path,
        dtype={"ticker": "string"},
        parse_dates=["signal_date"],
    )
    rank_ic = calculate_rank_ic(factor_targets, target_column=target_column)
    summary = (
        rank_ic.groupby(["factor", "target"], as_index=False)
        .agg(
            months=("rank_ic", "size"),
            mean_rank_ic=("rank_ic", "mean"),
            median_rank_ic=("rank_ic", "median"),
            positive_ic_rate=("rank_ic", lambda series: float((series > 0).mean())),
            mean_n=("n", "mean"),
        )
        .sort_values("mean_rank_ic", ascending=False)
    )
    output_path = Path(output_path)
    summary_output_path = Path(summary_output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rank_ic.to_csv(output_path, index=False, encoding="utf-8-sig")
    summary.to_csv(summary_output_path, index=False, encoding="utf-8-sig")
    return rank_ic, summary
