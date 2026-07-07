"""Market-regime aware factor scoring."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.data.benchmark_loader import load_benchmark
from src.factors.composite import calculate_composite_score


REGIME_WEIGHTS = {
    "bull": {
        "quality_score": 0.25,
        "value_score": 0.20,
        "momentum_score": 0.35,
        "low_volatility_score": 0.20,
    },
    "neutral": {
        "quality_score": 0.30,
        "value_score": 0.25,
        "momentum_score": 0.20,
        "low_volatility_score": 0.25,
    },
    "bear": {
        "quality_score": 0.35,
        "value_score": 0.15,
        "momentum_score": 0.10,
        "low_volatility_score": 0.40,
    },
    "stress": {
        "quality_score": 0.40,
        "value_score": 0.10,
        "momentum_score": 0.05,
        "low_volatility_score": 0.45,
    },
}

REGIME_EXPOSURE = {
    "bull": 1.0,
    "neutral": 0.7,
    "bear": 0.3,
    "stress": 0.1,
}


def build_market_regime_table(
    benchmark_path: str | Path = "data/raw/benchmark/kodex200_prices.csv",
    *,
    output_path: str | Path = "outputs/tables/market_regime_by_signal_date.csv",
) -> pd.DataFrame:
    """Classify monthly market regimes from benchmark trend, volatility, and drawdown."""
    benchmark = load_benchmark(benchmark_path)
    if benchmark.empty:
        raise ValueError(f"Benchmark data is empty: {benchmark_path}")
    benchmark_name = benchmark["benchmark"].iloc[0]
    daily = benchmark[benchmark["benchmark"] == benchmark_name].copy()
    daily = daily.sort_values("date").set_index("date")
    daily["return"] = daily["close"].pct_change(fill_method=None)
    daily["ma_120d"] = daily["close"].rolling(120, min_periods=60).mean()
    daily["ret_60d"] = daily["close"].pct_change(60)
    daily["vol_60d"] = daily["return"].rolling(60, min_periods=40).std() * (252 ** 0.5)
    daily["drawdown_120d"] = daily["close"] / daily["close"].rolling(120, min_periods=60).max() - 1

    monthly = daily.groupby(daily.index.to_period("M")).tail(1).copy()
    monthly = monthly.reset_index().rename(columns={"date": "signal_date"})
    monthly["regime"] = monthly.apply(_classify_regime, axis=1)
    monthly["target_exposure"] = monthly["regime"].map(REGIME_EXPOSURE)
    monthly["benchmark"] = benchmark_name
    output = monthly[
        [
            "signal_date",
            "benchmark",
            "close",
            "ma_120d",
            "ret_60d",
            "vol_60d",
            "drawdown_120d",
            "regime",
            "target_exposure",
        ]
    ].copy()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output


def build_regime_aware_factor_scores(
    factor_scores_path: str | Path = "data/features/integrated_factor_scores.csv",
    benchmark_path: str | Path = "data/raw/benchmark/kodex200_prices.csv",
    *,
    output_path: str | Path = "data/features/regime_aware_factor_scores.csv",
    regime_output_path: str | Path = "outputs/tables/market_regime_by_signal_date.csv",
) -> pd.DataFrame:
    """Apply regime-specific factor weights and target equity exposure."""
    scores = pd.read_csv(
        factor_scores_path,
        dtype={"ticker": "string"},
        parse_dates=["signal_date"],
    )
    regimes = build_market_regime_table(
        benchmark_path,
        output_path=regime_output_path,
    )
    scores["ticker"] = scores["ticker"].astype("string").str.zfill(6)
    scores = scores.merge(
        regimes[["signal_date", "regime", "target_exposure"]],
        on="signal_date",
        how="left",
    )
    scores["regime"] = scores["regime"].fillna("neutral")
    scores["target_exposure"] = scores["target_exposure"].fillna(REGIME_EXPOSURE["neutral"])

    parts = []
    for regime, group in scores.groupby("regime", sort=False):
        weighted = calculate_composite_score(
            group.drop(columns=["composite_score", "composite_weight_coverage"], errors="ignore"),
            weights=REGIME_WEIGHTS.get(regime, REGIME_WEIGHTS["neutral"]),
        )
        parts.append(weighted)
    output = pd.concat(parts, ignore_index=True).sort_values(
        ["signal_date", "composite_score"],
        ascending=[True, False],
    )
    output["factor_scope"] = "regime_aware_value_quality_momentum_low_volatility"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output


def _classify_regime(row: pd.Series) -> str:
    close = row.get("close")
    ma_120d = row.get("ma_120d")
    ret_60d = row.get("ret_60d")
    vol_60d = row.get("vol_60d")
    drawdown = row.get("drawdown_120d")
    if pd.isna(ma_120d) or pd.isna(ret_60d):
        return "neutral"
    if drawdown <= -0.18 or (ret_60d <= -0.12 and vol_60d >= 0.25):
        return "stress"
    if close < ma_120d and ret_60d < -0.03:
        return "bear"
    if close > ma_120d and ret_60d > 0.03:
        return "bull"
    return "neutral"
