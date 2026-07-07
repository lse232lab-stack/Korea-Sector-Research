"""Load benchmark index data."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_benchmark(path: str | Path) -> pd.DataFrame:
    """Load benchmark CSV and normalize it to date/benchmark/close/return."""
    frame = pd.read_csv(path, dtype={"ticker": "string", "benchmark": "string"})
    if frame.empty:
        return pd.DataFrame(columns=["date", "benchmark", "close", "return"])

    frame = frame.copy()
    frame["date"] = pd.to_datetime(frame["date"])

    if "benchmark" not in frame.columns:
        if "ticker" in frame.columns:
            frame["benchmark"] = frame["ticker"].astype("string").str.zfill(6)
        else:
            frame["benchmark"] = "BENCHMARK"

    if "close" not in frame.columns:
        if "adj_close" in frame.columns:
            frame["close"] = frame["adj_close"]
        else:
            raise ValueError("Benchmark CSV must include close or adj_close.")

    output = frame[["date", "benchmark", "close"]].copy()
    output["close"] = pd.to_numeric(output["close"], errors="coerce")
    output = output.dropna(subset=["date", "close"]).sort_values(["benchmark", "date"])
    output["return"] = output.groupby("benchmark")["close"].pct_change(fill_method=None)
    return output.reset_index(drop=True)


def load_benchmark_returns(path: str | Path) -> pd.Series:
    """Load the first benchmark return series from a normalized benchmark CSV."""
    benchmark = load_benchmark(path)
    if benchmark.empty:
        return pd.Series(dtype=float, name="benchmark_return")
    benchmark_name = str(benchmark["benchmark"].dropna().iloc[0])
    series = (
        benchmark[benchmark["benchmark"] == benchmark_name]
        .set_index("date")["return"]
        .sort_index()
        .rename("benchmark_return")
    )
    return series
