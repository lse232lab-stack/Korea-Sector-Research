"""Quintile return analysis."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def calculate_quintile_returns(
    factor_targets: pd.DataFrame,
    *,
    score_column: str = "composite_score",
    target_column: str = "excess_forward_1m_return",
    quantiles: int = 5,
) -> pd.DataFrame:
    """Calculate monthly forward returns by score quantile."""
    rows = []
    for signal_date, group in factor_targets.groupby("signal_date"):
        sample = group[[score_column, target_column]].dropna().copy()
        if len(sample) < quantiles * 10:
            continue
        ranked = sample[score_column].rank(method="first")
        sample["quantile"] = pd.qcut(ranked, q=quantiles, labels=False) + 1
        for quantile, quantile_group in sample.groupby("quantile"):
            rows.append(
                {
                    "signal_date": signal_date,
                    "score": score_column,
                    "target": target_column,
                    "quantile": int(quantile),
                    "mean_forward_return": float(quantile_group[target_column].mean()),
                    "median_forward_return": float(quantile_group[target_column].median()),
                    "n": int(len(quantile_group)),
                }
            )
    return pd.DataFrame(rows).sort_values(["signal_date", "quantile"]).reset_index(drop=True)


def write_quintile_outputs(
    factor_targets_path: str | Path = "data/features/factor_forward_returns.csv",
    *,
    output_path: str | Path = "outputs/tables/quintile_returns_by_month.csv",
    summary_output_path: str | Path = "outputs/tables/quintile_return_summary.csv",
    score_column: str = "composite_score",
    target_column: str = "excess_forward_1m_return",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Write monthly quintile returns and top-minus-bottom spread summary."""
    factor_targets = pd.read_csv(
        factor_targets_path,
        dtype={"ticker": "string"},
        parse_dates=["signal_date"],
    )
    monthly = calculate_quintile_returns(
        factor_targets,
        score_column=score_column,
        target_column=target_column,
    )
    summary = (
        monthly.groupby(["score", "target", "quantile"], as_index=False)
        .agg(
            months=("mean_forward_return", "size"),
            mean_forward_return=("mean_forward_return", "mean"),
            median_forward_return=("median_forward_return", "median"),
            mean_n=("n", "mean"),
        )
        .sort_values("quantile")
    )
    spread = _top_minus_bottom_spread(monthly)
    output_path = Path(output_path)
    summary_output_path = Path(summary_output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    monthly.to_csv(output_path, index=False, encoding="utf-8-sig")
    final_summary = (
        pd.concat([summary, spread], ignore_index=True)
        if not spread.empty
        else summary
    )
    final_summary.to_csv(
        summary_output_path,
        index=False,
        encoding="utf-8-sig",
    )
    return monthly, final_summary


def _top_minus_bottom_spread(monthly: pd.DataFrame) -> pd.DataFrame:
    if monthly.empty:
        return pd.DataFrame()
    pivot = monthly.pivot_table(
        index="signal_date",
        columns="quantile",
        values="mean_forward_return",
        aggfunc="first",
    )
    if 1 not in pivot.columns or 5 not in pivot.columns:
        return pd.DataFrame()
    spread = pivot[5] - pivot[1]
    return pd.DataFrame(
        [
            {
                "score": monthly["score"].iloc[0],
                "target": monthly["target"].iloc[0],
                "quantile": "Q5-Q1",
                "months": int(spread.dropna().size),
                "mean_forward_return": float(spread.mean()),
                "median_forward_return": float(spread.median()),
                "mean_n": 0.0,
            }
        ]
    )
