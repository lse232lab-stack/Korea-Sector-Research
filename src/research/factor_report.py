"""Combine factor validation outputs into research tables."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.research.forward_returns import build_factor_forward_returns
from src.research.ic_analysis import write_rank_ic_outputs
from src.research.quintile_analysis import write_quintile_outputs
from src.research.recommendation import build_latest_recommendation_candidates


def build_factor_validation_report(
    factor_scores_path: str | Path = "data/features/integrated_factor_scores.csv",
    price_path: str | Path = "data/raw/price/prices.csv",
    *,
    target_output_path: str | Path = "data/features/factor_forward_returns.csv",
    report_output_path: str | Path = "outputs/reports/factor_validation_summary.md",
) -> dict[str, pd.DataFrame]:
    """Build target, Rank IC, quintile, and latest candidate outputs."""
    targets = build_factor_forward_returns(
        factor_scores_path=factor_scores_path,
        price_path=price_path,
        output_path=target_output_path,
    )
    rank_ic, rank_ic_summary = write_rank_ic_outputs(target_output_path)
    quintile, quintile_summary = write_quintile_outputs(target_output_path)
    candidates = build_latest_recommendation_candidates(factor_scores_path)

    report_output_path = Path(report_output_path)
    report_output_path.parent.mkdir(parents=True, exist_ok=True)
    report_output_path.write_text(
        _build_markdown_summary(targets, rank_ic_summary, quintile_summary, candidates),
        encoding="utf-8",
    )
    return {
        "targets": targets,
        "rank_ic": rank_ic,
        "rank_ic_summary": rank_ic_summary,
        "quintile": quintile,
        "quintile_summary": quintile_summary,
        "candidates": candidates,
    }


def _build_markdown_summary(
    targets: pd.DataFrame,
    rank_ic_summary: pd.DataFrame,
    quintile_summary: pd.DataFrame,
    candidates: pd.DataFrame,
) -> str:
    dated_targets = targets.dropna(subset=["excess_forward_1m_return"])
    return (
        "# Factor Validation and Recommendation Candidate Summary\n\n"
        "## Target Coverage\n\n"
        f"- Rows with forward 1M excess return: {len(dated_targets):,}\n"
        f"- Signal dates: {dated_targets['signal_date'].nunique():,}\n"
        f"- Tickers: {dated_targets['ticker'].nunique():,}\n\n"
        "## Rank IC Summary\n\n"
        f"{_dataframe_to_markdown(_round(rank_ic_summary))}\n\n"
        "## Quintile Return Summary\n\n"
        f"{_dataframe_to_markdown(_round(quintile_summary))}\n\n"
        "## Latest Model Portfolio Candidates Top 30\n\n"
        f"{_dataframe_to_markdown(_round(candidates))}\n\n"
        "Note: This is a quantitative screening result, not investment advice. "
        "Use it as model portfolio candidate output for research and interview discussion.\n"
    )


def _round(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    for column in output.columns:
        if pd.api.types.is_datetime64_any_dtype(output[column]):
            output[column] = output[column].dt.strftime("%Y-%m-%d")
        elif pd.api.types.is_float_dtype(output[column]):
            output[column] = output[column].map(lambda value: "" if pd.isna(value) else f"{value:.4f}")
    return output


def _dataframe_to_markdown(frame: pd.DataFrame) -> str:
    headers = [str(column) for column in frame.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in frame.values.tolist():
        lines.append("| " + " | ".join("" if pd.isna(value) else str(value) for value in row) + " |")
    return "\n".join(lines)
