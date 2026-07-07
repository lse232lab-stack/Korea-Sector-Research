"""Research train/validation/test split utilities."""

from __future__ import annotations

import pandas as pd


DEFAULT_SPLIT_BOUNDARIES = {
    "train_end": "2016-12-31",
    "validation_end": "2021-12-31",
}


def assign_research_split(
    frame: pd.DataFrame,
    *,
    date_col: str = "available_date",
    train_end: str = DEFAULT_SPLIT_BOUNDARIES["train_end"],
    validation_end: str = DEFAULT_SPLIT_BOUNDARIES["validation_end"],
) -> pd.DataFrame:
    """Label rows by the date that information became available to the model."""
    output = frame.copy()
    dates = pd.to_datetime(output[date_col], errors="coerce")
    train_cutoff = pd.Timestamp(train_end)
    validation_cutoff = pd.Timestamp(validation_end)

    output["research_split"] = "test"
    output.loc[dates <= train_cutoff, "research_split"] = "train"
    output.loc[
        (dates > train_cutoff) & (dates <= validation_cutoff),
        "research_split",
    ] = "validation"
    output.loc[dates.isna(), "research_split"] = "unknown"
    return output
