"""Institutional-style core-satellite strategy with regime risk overlay."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.backtest.engine import run_backtest
from src.backtest.performance import calculate_performance_metrics
from src.factors.composite import calculate_composite_score


SUB_STRATEGY_WEIGHTS = {
    "balanced": {
        "quality_score": 0.25,
        "value_score": 0.25,
        "momentum_score": 0.20,
        "low_volatility_score": 0.20,
        "growth_score": 0.10,
    },
    "value_momentum": {
        "value_score": 0.35,
        "momentum_score": 0.35,
        "quality_score": 0.15,
        "low_volatility_score": 0.15,
    },
    "defensive": {
        "quality_score": 0.45,
        "low_volatility_score": 0.45,
        "value_score": 0.10,
    },
    "aggressive": {
        "momentum_score": 0.60,
        "growth_score": 0.25,
        "quality_score": 0.15,
    },
}

REGIME_BLEND_WEIGHTS = {
    "bull": {
        "balanced_score": 0.25,
        "value_momentum_score": 0.25,
        "aggressive_score": 0.20,
        "ml_score": 0.30,
    },
    "neutral": {
        "balanced_score": 0.40,
        "value_momentum_score": 0.20,
        "defensive_score": 0.20,
        "ml_score": 0.20,
    },
    "bear": {
        "balanced_score": 0.30,
        "defensive_score": 0.45,
        "value_momentum_score": 0.10,
        "ml_score": 0.15,
    },
    "stress": {
        "defensive_score": 0.65,
        "balanced_score": 0.25,
        "value_momentum_score": 0.05,
        "ml_score": 0.05,
    },
}

REGIME_TARGET_EXPOSURE = {
    "bull": 1.00,
    "neutral": 0.80,
    "bear": 0.50,
    "stress": 0.25,
}

SPLITS = [
    ("train_2007_2016", "2007-01-01", "2016-12-31"),
    ("validation_2017_2021", "2017-01-01", "2021-12-31"),
    ("test_2022_2026", "2022-01-01", "2026-12-31"),
    ("full_2007_2026", "2007-01-01", "2026-12-31"),
]


def run_institutional_strategy(
    *,
    price_path: str | Path = "data/raw/price/prices_2007_2026.csv",
    factor_scores_path: str | Path = "data/features/integrated_factor_scores_2007_2026.csv",
    ml_factor_scores_path: str | Path = "data/features/ml_predicted_factor_scores_2007_2026.csv",
    score_output_path: str | Path = "data/features/institutional_core_satellite_scores.csv",
    regime_output_path: str | Path = "outputs/tables/institutional_market_regime.csv",
    backtest_output_dir: str | Path = "outputs/backtest_institutional_core_satellite",
    split_output_path: str | Path = "outputs/tables/institutional_strategy_split_summary.csv",
    report_output_path: str | Path = "outputs/reports/Institutional_Core_Satellite_Strategy.md",
    top_n: int = 30,
    transaction_cost_bps: float = 10.0,
) -> dict[str, pd.DataFrame]:
    """Build, backtest, and document the institutional core-satellite strategy."""
    scores = build_institutional_scores(
        price_path=price_path,
        factor_scores_path=factor_scores_path,
        ml_factor_scores_path=ml_factor_scores_path,
        output_path=score_output_path,
        regime_output_path=regime_output_path,
    )
    result = run_backtest(
        price_path=price_path,
        factor_scores_path=score_output_path,
        output_dir=backtest_output_dir,
        top_n=top_n,
        transaction_cost_bps=transaction_cost_bps,
    )
    split = _split_metrics(result["daily_returns"])
    split_output_path = Path(split_output_path)
    split_output_path.parent.mkdir(parents=True, exist_ok=True)
    split.to_csv(split_output_path, index=False, encoding="utf-8-sig")

    report_output_path = Path(report_output_path)
    report_output_path.parent.mkdir(parents=True, exist_ok=True)
    report_output_path.write_text(
        _build_report(result["summary"], split, scores, regime_output_path),
        encoding="utf-8",
    )
    return {
        "scores": scores,
        "summary": result["summary"],
        "split_summary": split,
        "daily_returns": result["daily_returns"],
        "rebalance_log": result["rebalance_log"],
    }


def build_institutional_scores(
    *,
    price_path: str | Path,
    factor_scores_path: str | Path,
    ml_factor_scores_path: str | Path,
    output_path: str | Path,
    regime_output_path: str | Path,
) -> pd.DataFrame:
    """Create monthly institutional strategy scores compatible with run_backtest."""
    base = pd.read_csv(
        factor_scores_path,
        dtype={"ticker": "string"},
        parse_dates=["signal_date"],
    )
    base["ticker"] = base["ticker"].astype("string").str.zfill(6)
    base = base.dropna(subset=["signal_date"])

    score_parts = base[["ticker", "name", "signal_date"]].copy()
    for label, weights in SUB_STRATEGY_WEIGHTS.items():
        scored = calculate_composite_score(
            base.drop(
                columns=["composite_score", "composite_weight_coverage"],
                errors="ignore",
            ),
            weights=weights,
        )
        raw_col = f"{label}_raw_score"
        z_col = f"{label}_score"
        score_parts[raw_col] = scored["composite_score"]
        score_parts[z_col] = _cross_sectional_zscore(scored, "composite_score")

    ml = _load_ml_scores(ml_factor_scores_path)
    score_parts = _attach_ml_scores_asof(score_parts, ml)

    regimes = build_universe_market_regime(
        price_path=price_path,
        signal_dates=score_parts["signal_date"],
        output_path=regime_output_path,
    )
    score_parts = score_parts.merge(
        regimes[["signal_date", "regime", "target_exposure"]],
        on="signal_date",
        how="left",
    )
    score_parts["regime"] = score_parts["regime"].fillna("neutral")
    score_parts["target_exposure"] = score_parts["target_exposure"].fillna(
        REGIME_TARGET_EXPOSURE["neutral"]
    )
    score_parts["composite_score"] = score_parts.apply(_blend_score, axis=1)
    score_parts["factor_scope"] = "institutional_core_satellite_regime_overlay"
    score_parts = score_parts.dropna(subset=["composite_score"]).sort_values(
        ["signal_date", "composite_score"],
        ascending=[True, False],
    )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    score_parts.to_csv(output_path, index=False, encoding="utf-8-sig")
    return score_parts


def build_universe_market_regime(
    *,
    price_path: str | Path,
    signal_dates: pd.Series,
    output_path: str | Path,
) -> pd.DataFrame:
    """Classify market regimes from the equal-weight universe index."""
    prices = pd.read_csv(price_path, dtype={"ticker": "string"}, parse_dates=["date"])
    prices["ticker"] = prices["ticker"].astype("string").str.zfill(6)
    matrix = (
        prices.pivot_table(index="date", columns="ticker", values="adj_close", aggfunc="last")
        .sort_index()
        .ffill()
    )
    returns = matrix.pct_change(fill_method=None)
    index_return = returns.mean(axis=1, skipna=True).fillna(0.0)
    index_level = (1.0 + index_return).cumprod()

    daily = pd.DataFrame(
        {
            "date": index_level.index,
            "universe_equal_weight_index": index_level.values,
            "market_return": index_return.values,
        }
    ).set_index("date")
    daily["ma_200d"] = daily["universe_equal_weight_index"].rolling(200, min_periods=120).mean()
    daily["ret_60d"] = daily["universe_equal_weight_index"].pct_change(60)
    daily["vol_60d"] = daily["market_return"].rolling(60, min_periods=40).std() * (252 ** 0.5)
    daily["drawdown_120d"] = (
        daily["universe_equal_weight_index"]
        / daily["universe_equal_weight_index"].rolling(120, min_periods=60).max()
        - 1.0
    )

    monthly = daily.groupby(daily.index.to_period("M")).tail(1).reset_index()
    monthly = monthly.rename(columns={"date": "signal_date"})
    monthly["regime"] = monthly.apply(_classify_regime, axis=1)
    monthly["target_exposure"] = monthly["regime"].map(REGIME_TARGET_EXPOSURE)
    wanted = pd.DataFrame({"signal_date": pd.to_datetime(signal_dates.dropna().unique())})
    output = wanted.merge(monthly, on="signal_date", how="left").sort_values("signal_date")
    output["regime"] = output["regime"].ffill().fillna("neutral")
    output["target_exposure"] = output["target_exposure"].fillna(REGIME_TARGET_EXPOSURE["neutral"])

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output


def _load_ml_scores(path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype={"ticker": "string"}, parse_dates=["signal_date"])
    frame["ticker"] = frame["ticker"].astype("string").str.zfill(6)
    score_col = (
        "predicted_excess_forward_1m_return"
        if "predicted_excess_forward_1m_return" in frame
        else "composite_score"
    )
    frame["ml_score"] = _cross_sectional_zscore(frame, score_col)
    return frame


def _attach_ml_scores_asof(scores: pd.DataFrame, ml: pd.DataFrame) -> pd.DataFrame:
    """Attach the latest available ML score per ticker as of each signal date."""
    parts = []
    ml = ml[["ticker", "signal_date", "ml_score"]].dropna(subset=["signal_date", "ml_score"])
    for ticker, group in scores.groupby("ticker", sort=False):
        ml_group = ml[ml["ticker"].eq(ticker)].sort_values("signal_date")
        current = group.sort_values("signal_date")
        if ml_group.empty:
            enriched = current.copy()
            enriched["ml_signal_date"] = pd.NaT
            enriched["ml_score"] = pd.NA
        else:
            enriched = pd.merge_asof(
                current,
                ml_group.rename(columns={"signal_date": "ml_signal_date"}),
                left_on="signal_date",
                right_on="ml_signal_date",
                by="ticker",
                direction="backward",
                tolerance=pd.Timedelta(days=45),
            )
        parts.append(enriched)
    return pd.concat(parts, ignore_index=True)


def _cross_sectional_zscore(frame: pd.DataFrame, column: str) -> pd.Series:
    values = pd.to_numeric(frame[column], errors="coerce")
    grouped = values.groupby(frame["signal_date"])
    mean = grouped.transform("mean")
    std = grouped.transform(lambda series: series.std(ddof=0))
    zscore = (values - mean) / std.replace(0.0, pd.NA)
    return zscore.clip(-3.0, 3.0)


def _blend_score(row: pd.Series) -> float | None:
    weights = REGIME_BLEND_WEIGHTS.get(str(row["regime"]), REGIME_BLEND_WEIGHTS["neutral"])
    weighted_sum = 0.0
    weight_sum = 0.0
    for column, weight in weights.items():
        value = row.get(column)
        if pd.notna(value):
            weighted_sum += float(value) * weight
            weight_sum += weight
    if weight_sum == 0.0:
        return None
    return weighted_sum / weight_sum


def _classify_regime(row: pd.Series) -> str:
    level = row.get("universe_equal_weight_index")
    ma_200d = row.get("ma_200d")
    ret_60d = row.get("ret_60d")
    vol_60d = row.get("vol_60d")
    drawdown = row.get("drawdown_120d")
    if pd.isna(ma_200d) or pd.isna(ret_60d):
        return "neutral"
    if drawdown <= -0.20 or (ret_60d <= -0.12 and vol_60d >= 0.28):
        return "stress"
    if level < ma_200d and ret_60d < -0.03:
        return "bear"
    if level > ma_200d and ret_60d > 0.03:
        return "bull"
    return "neutral"


def _split_metrics(daily_returns: pd.DataFrame) -> pd.DataFrame:
    daily = daily_returns.copy()
    daily["date"] = pd.to_datetime(daily["date"])
    rows = []
    for period, start, end in SPLITS:
        subset = daily[daily["date"].between(pd.Timestamp(start), pd.Timestamp(end))]
        if subset.empty:
            continue
        metrics = calculate_performance_metrics(
            subset["strategy_return"],
            subset["benchmark_return"],
        )
        rows.append(
            {
                "strategy_id": "institutional_core_satellite",
                "strategy_name": "Institutional Core-Satellite",
                "period": period,
                "start_date": subset["date"].min().date(),
                "end_date": subset["date"].max().date(),
                **metrics,
            }
        )
    return pd.DataFrame(rows)


def _build_report(
    summary: pd.DataFrame,
    split: pd.DataFrame,
    scores: pd.DataFrame,
    regime_output_path: str | Path,
) -> str:
    latest = scores[scores["signal_date"].eq(scores["signal_date"].max())].head(10)
    summary_display = _format_metrics(summary.copy())
    split_display = _format_metrics(split.copy())
    latest_display = latest[
        [
            "ticker",
            "name",
            "signal_date",
            "regime",
            "target_exposure",
            "balanced_score",
            "value_momentum_score",
            "defensive_score",
            "ml_score",
            "ml_signal_date",
            "composite_score",
        ]
    ].copy()
    latest_display["signal_date"] = latest_display["signal_date"].dt.strftime("%Y-%m-%d")
    latest_display["ml_signal_date"] = latest_display["ml_signal_date"].dt.strftime("%Y-%m-%d")
    for column in [
        "target_exposure",
        "balanced_score",
        "value_momentum_score",
        "defensive_score",
        "ml_score",
        "composite_score",
    ]:
        latest_display[column] = latest_display[column].map(lambda value: f"{value:.4f}")

    return f"""# Institutional Core-Satellite Quant Strategy

## 1. 목적

이 전략은 논문 또는 S&T/운용 부서의 내부 투자전략 검토 문서에서 방어 가능한 수준을 목표로 설계했다. 단일 팩터의 과최적화 위험을 줄이기 위해 여러 검증된 알파 신호를 앙상블하고, 시장 국면에 따라 팩터 가중치와 주식 노출을 조정한다.

## 2. 이론적 근거

- Value: Fama and French의 다요인 모형은 장부가치 대비 저평가된 주식의 수익률 차이를 체계적 요인으로 해석한다.
- Momentum: Jegadeesh and Titman의 3~12개월 승자-패자 모멘텀 연구는 가격 추세 신호가 단기 이후 수익률을 설명할 수 있음을 보였다.
- Quality/Profitability: profitability 계열 신호는 단순 저평가 함정을 줄이고 기업의 지속 가능한 이익 창출력을 반영한다.
- Low Risk/Low Volatility: Frazzini and Pedersen의 Betting Against Beta 계열 연구는 레버리지 제약이 낮은 위험 자산의 상대적 프리미엄으로 이어질 수 있음을 설명한다.
- Machine Learning: ML은 비선형 조합과 조건부 예측력을 포착할 수 있지만, 과적합 위험 때문에 단독 전략이 아니라 위성 신호로 제한한다.

## 3. 전략 구조

월말마다 모든 종목의 하위 신호를 cross-sectional z-score로 표준화한 뒤, 시장 국면별 가중치로 최종 점수를 계산한다.

### 3.1 하위 신호

| 신호 | 구성 |
| --- | --- |
| Balanced | Quality 25%, Value 25%, Momentum 20%, Low Volatility 20%, Growth 10% |
| Value Momentum | Value 35%, Momentum 35%, Quality 15%, Low Volatility 15% |
| Defensive | Quality 45%, Low Volatility 45%, Value 10% |
| Aggressive | Momentum 60%, Growth 25%, Quality 15% |
| ML | Ridge 모델의 다음 1개월 초과수익률 예측치 |

### 3.2 국면별 최종 점수

| 국면 | 최종 점수 가중치 | 목표 주식 노출 |
| --- | --- | --- |
| Bull | Balanced 25%, Value Momentum 25%, Aggressive 20%, ML 30% | 100% |
| Neutral | Balanced 40%, Value Momentum 20%, Defensive 20%, ML 20% | 80% |
| Bear | Balanced 30%, Defensive 45%, Value Momentum 10%, ML 15% | 50% |
| Stress | Defensive 65%, Balanced 25%, Value Momentum 5%, ML 5% | 25% |

### 3.3 시장 국면 판정

KOSPI200 구성 종목의 동일가중 지수를 내부 시장 proxy로 만들고, 200일 이동평균, 60일 수익률, 60일 변동성, 120일 낙폭으로 국면을 판정한다. 공식 지수 대신 내부 universe를 쓰는 이유는 현 단계에서 모든 종목의 긴 가격 이력이 이미 확보되어 있고, 전략의 투자 가능 universe와 벤치마크 proxy를 일치시키기 위해서다.

## 4. 포트폴리오 구성

- 매월 말 신호 생성.
- 최종 점수 상위 30개 종목 동일가중.
- 국면별 target_exposure만큼 주식 보유, 잔여 비중은 현금 가정.
- 리밸런싱 회전율 기준 10bp 거래비용 차감.
- 벤치마크는 동일 universe의 일별 동일가중 수익률.

## 5. 백테스트 결과

{_markdown_table(summary_display)}

## 6. 구간별 검증

{_markdown_table(split_display)}

## 7. 최신 모델 후보군

아래는 투자 의견이 아니라, 최종 점수 기준 최신 상위 스크리닝 결과다.

{_markdown_table(latest_display)}

## 8. 실무 적용 전 필수 보완

1. Point-in-time KOSPI200 구성종목 이력으로 생존편향을 제거한다.
2. 공식 KOSPI200 지수 또는 KODEX 200 장기 데이터로 외부 벤치마크를 재검증한다.
3. 거래대금 필터, 단일 종목 5%, 업종 25%, ADV 대비 주문비율 한도를 추가한다.
4. 거래비용을 5bp, 10bp, 20bp, 50bp로 민감도 분석한다.
5. 리밸런싱 다음날 체결, 가격제한폭, 거래정지, 실적 발표 직후 gap risk를 반영한다.
6. ML 신호는 walk-forward 재학습과 feature drift 모니터링 없이는 실전 비중을 제한한다.

## 9. 참고 문헌 및 근거 자료

- Fama, E. F. and French, K. R. (1993), Common risk factors in the returns on stocks and bonds.
- Jegadeesh, N. and Titman, S. (1993), Returns to Buying Winners and Selling Losers.
- Frazzini, A. and Pedersen, L. H. (2014), Betting Against Beta.
- Novy-Marx, R. (2013), The Other Side of Value: The Gross Profitability Premium.

Regime table: `{regime_output_path}`
"""


def _format_metrics(frame: pd.DataFrame) -> pd.DataFrame:
    percent_columns = [
        "total_return",
        "cagr",
        "annualized_volatility",
        "max_drawdown",
        "win_rate",
        "benchmark_total_return",
        "active_total_return",
        "tracking_error",
    ]
    for column in percent_columns:
        if column in frame:
            frame[column] = frame[column].map(lambda value: f"{value:.2%}")
    for column in ["sharpe", "information_ratio"]:
        if column in frame:
            frame[column] = frame[column].map(lambda value: f"{value:.2f}")
    return frame


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No data available."
    headers = [str(column) for column in frame.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in frame.astype(str).values.tolist():
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)
