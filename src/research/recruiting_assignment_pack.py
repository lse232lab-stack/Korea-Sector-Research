"""Recruiting assignment style analyses for quant research applications."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.backtest.engine import run_backtest
from src.backtest.performance import calculate_performance_metrics


def run_recruiting_assignment_pack(
    *,
    price_path: str | Path = "data/raw/price/prices_2007_2026.csv",
    factor_scores_path: str | Path = "data/features/integrated_factor_scores_2007_2026.csv",
    output_table_dir: str | Path = "outputs/tables/recruiting_assignment_pack",
    output_report_path: str | Path = "outputs/reports/Quant_Research_Recruiting_Assignment_Pack.md",
) -> dict[str, pd.DataFrame]:
    """Run a practical assignment pack using the user's KOSPI200 dataset."""
    table_dir = Path(output_table_dir)
    table_dir.mkdir(parents=True, exist_ok=True)
    prices = _load_prices(price_path)
    factors = _load_factors(factor_scores_path)
    returns = prices.pct_change(fill_method=None)

    skill_map = _build_skill_map()
    minvar_weights, minvar_roll = _minimum_variance_outputs(returns)
    pca_summary = _pca_outputs(prices)
    low_vol_bootstrap = _low_vol_bootstrap(factors, returns)
    momentum_compare = _momentum_skip_month_comparison(prices, returns)
    cost_sensitivity = _transaction_cost_sensitivity(price_path, factor_scores_path)
    weighting_compare = _weighting_comparison(factors, returns)
    fat_tail = _fat_tail_summary(returns)
    corr_breakdown = _correlation_breakdown(returns)

    outputs = {
        "skill_map": skill_map,
        "q50_min_variance_latest_weights": minvar_weights,
        "q50_rolling_min_variance_summary": minvar_roll,
        "q52_pca_summary": pca_summary,
        "q54_low_vol_bootstrap": low_vol_bootstrap,
        "q56_momentum_skip_month_comparison": momentum_compare,
        "q57_transaction_cost_sensitivity": cost_sensitivity,
        "q58_weighting_comparison": weighting_compare,
        "q59_fat_tail_summary": fat_tail,
        "q60_correlation_breakdown": corr_breakdown,
    }
    for name, frame in outputs.items():
        frame.to_csv(table_dir / f"{name}.csv", index=False, encoding="utf-8-sig")

    output_report_path = Path(output_report_path)
    output_report_path.parent.mkdir(parents=True, exist_ok=True)
    output_report_path.write_text(_build_report(outputs), encoding="utf-8")
    return outputs


def _load_prices(path: str | Path) -> pd.DataFrame:
    raw = pd.read_csv(path, dtype={"ticker": "string"}, parse_dates=["date"])
    raw["ticker"] = raw["ticker"].astype("string").str.zfill(6)
    return (
        raw.pivot_table(index="date", columns="ticker", values="adj_close", aggfunc="last")
        .sort_index()
        .ffill()
    )


def _load_factors(path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype={"ticker": "string"}, parse_dates=["signal_date"])
    frame["ticker"] = frame["ticker"].astype("string").str.zfill(6)
    return frame.dropna(subset=["signal_date"])


def _build_skill_map() -> pd.DataFrame:
    rows = [
        ("Q50", "Covariance Matrix / Minimum Variance Portfolio", "공분산 행렬, 최적화, rolling window", "q50_min_variance_latest_weights.csv"),
        ("Q52", "PCA on monthly returns", "차원축소, 시장 공통요인 해석", "q52_pca_summary.csv"),
        ("Q54", "Low-volatility strategy bootstrap", "전략 성과 검정, bootstrap CI", "q54_low_vol_bootstrap.csv"),
        ("Q56", "Momentum skip-month test", "모멘텀 정의 비교, 반전효과 점검", "q56_momentum_skip_month_comparison.csv"),
        ("Q57", "Transaction-cost sensitivity", "실무 거래비용 가정과 성과 민감도", "q57_transaction_cost_sensitivity.csv"),
        ("Q58", "Equal / volatility / risk-parity weighting", "포트폴리오 가중 방식 비교", "q58_weighting_comparison.csv"),
        ("Q59", "Fat-tail diagnostics", "왜도, 첨도, tail risk", "q59_fat_tail_summary.csv"),
        ("Q60", "Correlation breakdown in stress periods", "상관 상승과 분산효과 붕괴", "q60_correlation_breakdown.csv"),
        ("Q76", "Lagging rule / look-ahead bias", "재무정보 사용 가능일 통제", "existing integrated factor pipeline"),
        ("Q99", "End-to-end pipeline", "수집-정제-팩터-검증-리포트 자동화", "main.py pipeline steps"),
    ]
    return pd.DataFrame(rows, columns=["question", "assignment_theme", "demonstrated_skill", "project_artifact"])


def _minimum_variance_outputs(returns: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    recent = returns.tail(30).dropna(axis=1, thresh=20)
    weights = _long_only_minvar(recent)
    latest_weights = (
        weights.sort_values(ascending=False)
        .head(30)
        .reset_index()
        .rename(columns={"index": "ticker", 0: "weight"})
    )
    latest_weights["weight"] = latest_weights["weight"].astype(float)

    rows = []
    previous = None
    for end in range(max(10, len(returns) - 120), len(returns) + 1, 10):
        window = returns.iloc[max(0, end - 30):end].dropna(axis=1, thresh=20)
        if window.shape[1] < 5:
            continue
        w = _long_only_minvar(window)
        top = w.sort_values(ascending=False).head(30)
        turnover = np.nan
        if previous is not None:
            all_names = sorted(set(previous.index) | set(top.index))
            turnover = 0.5 * sum(abs(float(top.get(t, 0.0)) - float(previous.get(t, 0.0))) for t in all_names)
        rows.append(
            {
                "window_end_date": returns.index[end - 1].date(),
                "asset_count": int(window.shape[1]),
                "effective_weight_count": float(1.0 / np.sum(np.square(top.values))),
                "top_weight": float(top.max()),
                "top5_weight_sum": float(top.head(5).sum()),
                "turnover_vs_prev_window": turnover,
            }
        )
        previous = top
    return latest_weights, pd.DataFrame(rows)


def _long_only_minvar(window_returns: pd.DataFrame) -> pd.Series:
    clean = window_returns.dropna(axis=1, thresh=max(5, int(len(window_returns) * 0.7))).fillna(0.0)
    cov = clean.cov().to_numpy(dtype=float)
    if cov.size == 0:
        return pd.Series(dtype=float)
    ridge = np.eye(cov.shape[0]) * max(1e-6, float(np.nanmean(np.diag(cov))) * 0.05)
    inv = np.linalg.pinv(cov + ridge)
    ones = np.ones(cov.shape[0])
    raw = inv @ ones
    raw = raw / max(float(ones @ raw), 1e-12)
    raw = np.clip(raw, 0.0, None)
    if raw.sum() == 0:
        raw = np.ones_like(raw) / len(raw)
    else:
        raw = raw / raw.sum()
    return pd.Series(raw, index=clean.columns, name="weight")


def _pca_outputs(prices: pd.DataFrame) -> pd.DataFrame:
    monthly_prices = prices.resample("ME").last()
    monthly_returns = monthly_prices.pct_change(fill_method=None)
    periods = [
        ("full_2007_2026", "2007-01-01", "2026-06-30"),
        ("covid_crash_2020", "2020-02-01", "2020-05-31"),
        ("rate_hike_2022", "2022-01-01", "2022-12-31"),
        ("recent_2024_2026", "2024-01-01", "2026-06-30"),
    ]
    rows = []
    for label, start, end in periods:
        subset = monthly_returns.loc[start:end].dropna(axis=1, thresh=6).dropna(how="all")
        if subset.shape[0] < 3 or subset.shape[1] < 5:
            continue
        corr = subset.fillna(0.0).corr().fillna(0.0).to_numpy(dtype=float)
        eigenvalues = np.linalg.eigvalsh(corr)
        eigenvalues = np.sort(np.clip(eigenvalues, 0.0, None))[::-1]
        total = eigenvalues.sum() if eigenvalues.sum() else 1.0
        rows.append(
            {
                "period": label,
                "months": int(subset.shape[0]),
                "tickers": int(subset.shape[1]),
                "pc1_var_ratio": float(eigenvalues[0] / total),
                "pc2_var_ratio": float(eigenvalues[1] / total),
                "pc3_var_ratio": float(eigenvalues[2] / total),
                "pc1_to_pc3_cumulative": float(eigenvalues[:3].sum() / total),
            }
        )
    return pd.DataFrame(rows)


def _low_vol_bootstrap(factors: pd.DataFrame, returns: pd.DataFrame) -> pd.DataFrame:
    monthly = returns.resample("ME").apply(lambda x: (1.0 + x).prod() - 1.0)
    rows = []
    spreads = []
    for signal_date, group in factors.dropna(subset=["low_volatility_score"]).groupby("signal_date"):
        if signal_date not in monthly.index:
            continue
        next_dates = monthly.index[monthly.index > signal_date]
        if len(next_dates) == 0:
            continue
        ret_date = next_dates[0]
        selected = group.sort_values("low_volatility_score", ascending=False).head(30)["ticker"]
        available = [t for t in selected if t in monthly.columns]
        universe = [t for t in group["ticker"].unique() if t in monthly.columns]
        if len(available) < 5 or len(universe) < 30:
            continue
        strategy_ret = float(monthly.loc[ret_date, available].mean())
        universe_ret = float(monthly.loc[ret_date, universe].mean())
        spreads.append(strategy_ret - universe_ret)
    spreads = np.array(spreads, dtype=float)
    if len(spreads) == 0:
        return pd.DataFrame()
    rng = np.random.default_rng(42)
    boot_means = np.array([rng.choice(spreads, len(spreads), replace=True).mean() for _ in range(2000)])
    rows.append(
        {
            "months": int(len(spreads)),
            "mean_monthly_excess_return": float(spreads.mean()),
            "median_monthly_excess_return": float(np.median(spreads)),
            "bootstrap_ci_2_5": float(np.quantile(boot_means, 0.025)),
            "bootstrap_ci_97_5": float(np.quantile(boot_means, 0.975)),
            "positive_month_rate": float((spreads > 0).mean()),
        }
    )
    return pd.DataFrame(rows)


def _momentum_skip_month_comparison(prices: pd.DataFrame, returns: pd.DataFrame) -> pd.DataFrame:
    monthly_prices = prices.resample("ME").last()
    monthly_returns = monthly_prices.pct_change(fill_method=None)
    trailing_12_including = monthly_prices.pct_change(12)
    trailing_12_ex_1 = monthly_prices.shift(1) / monthly_prices.shift(12) - 1.0
    rows = []
    for label, signal in [("include_recent_1m", trailing_12_including), ("exclude_recent_1m", trailing_12_ex_1)]:
        monthly_spreads = []
        for signal_date in signal.index[:-1]:
            scores = signal.loc[signal_date].dropna().sort_values(ascending=False)
            if len(scores) < 50:
                continue
            next_ret = monthly_returns.loc[monthly_returns.index[monthly_returns.index > signal_date][0]]
            top = [t for t in scores.head(30).index if t in next_ret.index]
            universe = [t for t in scores.index if t in next_ret.index]
            monthly_spreads.append(float(next_ret[top].mean() - next_ret[universe].mean()))
        spread = pd.Series(monthly_spreads).dropna()
        rows.append(
            {
                "momentum_definition": label,
                "months": int(len(spread)),
                "mean_monthly_excess_return": float(spread.mean()),
                "annualized_excess_return": float((1.0 + spread.mean()) ** 12 - 1.0),
                "volatility_of_monthly_excess": float(spread.std(ddof=0)),
                "positive_month_rate": float((spread > 0).mean()),
            }
        )
    return pd.DataFrame(rows)


def _transaction_cost_sensitivity(price_path: str | Path, factor_scores_path: str | Path) -> pd.DataFrame:
    rows = []
    for bps in [0.0, 10.0, 30.0]:
        output_dir = f"outputs/recruiting_assignment_pack/backtest_cost_{int(bps)}bps"
        result = run_backtest(
            price_path=price_path,
            factor_scores_path=factor_scores_path,
            output_dir=output_dir,
            transaction_cost_bps=bps,
        )
        row = result["summary"].iloc[0].to_dict()
        row["transaction_cost_bps"] = bps
        rows.append(row)
    return pd.DataFrame(rows)


def _weighting_comparison(factors: pd.DataFrame, returns: pd.DataFrame) -> pd.DataFrame:
    daily_returns = returns.copy()
    trading_dates = pd.Index(daily_returns.index)
    signal_dates = [d for d in sorted(factors["signal_date"].dropna().unique()) if d < trading_dates.max()]
    benchmark = daily_returns.mean(axis=1, skipna=True)
    rows = []
    for method in ["equal_weight", "inverse_volatility", "score_weight"]:
        portfolio = pd.Series(0.0, index=trading_dates)
        for idx, signal_date in enumerate(signal_dates):
            group = factors[factors["signal_date"].eq(signal_date)].dropna(subset=["composite_score"])
            selected = group.sort_values("composite_score", ascending=False).head(30)
            tickers = [t for t in selected["ticker"] if t in daily_returns.columns]
            if not tickers:
                continue
            period_end = signal_dates[idx + 1] if idx + 1 < len(signal_dates) else trading_dates.max()
            period_dates = trading_dates[(trading_dates > signal_date) & (trading_dates <= period_end)]
            weights = _weights_for_method(method, selected.set_index("ticker"), daily_returns, signal_date, tickers)
            portfolio.loc[period_dates] = daily_returns.loc[period_dates, tickers].mul(weights, axis=1).sum(axis=1).fillna(0.0)
        active = portfolio.ne(0)
        metrics = calculate_performance_metrics(portfolio.loc[active], benchmark.loc[active])
        metrics["weighting_method"] = method
        rows.append(metrics)
    return pd.DataFrame(rows)


def _weights_for_method(
    method: str,
    selected: pd.DataFrame,
    returns: pd.DataFrame,
    signal_date: pd.Timestamp,
    tickers: list[str],
) -> pd.Series:
    if method == "equal_weight":
        return pd.Series(1.0 / len(tickers), index=tickers)
    if method == "inverse_volatility":
        vol = returns.loc[returns.index <= signal_date, tickers].tail(252).std(ddof=0).replace(0, np.nan)
        raw = 1.0 / vol
    else:
        score = selected.loc[tickers, "composite_score"].clip(lower=0.0)
        raw = score if score.sum() > 0 else pd.Series(1.0, index=tickers)
    raw = raw.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    if raw.sum() <= 0:
        return pd.Series(1.0 / len(tickers), index=tickers)
    return raw / raw.sum()


def _fat_tail_summary(returns: pd.DataFrame) -> pd.DataFrame:
    universe_return = returns.mean(axis=1, skipna=True).dropna()
    centered = universe_return - universe_return.mean()
    std = universe_return.std(ddof=0)
    skew = float((centered ** 3).mean() / (std ** 3)) if std else 0.0
    kurt = float((centered ** 4).mean() / (std ** 4)) if std else 0.0
    q01 = float(universe_return.quantile(0.01))
    q05 = float(universe_return.quantile(0.05))
    normal_q01 = float(universe_return.mean() - 2.326 * std)
    normal_q05 = float(universe_return.mean() - 1.645 * std)
    return pd.DataFrame(
        [
            {
                "series": "universe_equal_weight_daily_return",
                "observations": int(len(universe_return)),
                "mean": float(universe_return.mean()),
                "volatility_daily": float(std),
                "annualized_volatility": float(std * np.sqrt(252)),
                "skewness": skew,
                "kurtosis": kurt,
                "excess_kurtosis": kurt - 3.0,
                "empirical_1pct": q01,
                "normal_implied_1pct": normal_q01,
                "empirical_5pct": q05,
                "normal_implied_5pct": normal_q05,
            }
        ]
    )


def _correlation_breakdown(returns: pd.DataFrame) -> pd.DataFrame:
    periods = [
        ("normal_2019", "2019-01-01", "2019-12-31"),
        ("covid_crash_2020_03", "2020-03-01", "2020-03-31"),
        ("rate_hike_2022", "2022-01-01", "2022-12-31"),
        ("recent_2026_h1", "2026-01-01", "2026-06-30"),
    ]
    rows = []
    for label, start, end in periods:
        subset = returns.loc[start:end].dropna(axis=1, thresh=10)
        corr = subset.corr().to_numpy(dtype=float)
        upper = corr[np.triu_indices_from(corr, k=1)]
        upper = upper[~np.isnan(upper)]
        if len(upper) == 0:
            continue
        rows.append(
            {
                "period": label,
                "start": start,
                "end": end,
                "days": int(subset.shape[0]),
                "tickers": int(subset.shape[1]),
                "average_pairwise_correlation": float(np.mean(upper)),
                "median_pairwise_correlation": float(np.median(upper)),
                "corr_90th_percentile": float(np.quantile(upper, 0.90)),
            }
        )
    return pd.DataFrame(rows)


def _build_report(outputs: dict[str, pd.DataFrame]) -> str:
    return f"""# Quant Research Recruiting Assignment Pack

## 목적

증권사 퀀트리서치 사전과제는 단순한 코딩 테스트가 아니라, 데이터 수집, 정제, 통계검정, 포트폴리오 구성, 백테스트, 해석 능력을 함께 확인한다. 이 문서는 사용자가 보유한 KOSPI200 장기 가격/팩터 데이터를 바탕으로 사전과제형 문항을 실제 프로젝트 산출물로 연결한 결과다.

## 사전과제 요구 역량과 프로젝트 산출물

{_markdown_table(outputs["skill_map"])}

## Q50. 최근 30일 공분산 기반 Minimum Variance Portfolio

최근 30거래일 수익률 공분산 행렬에 ridge 안정화를 적용하고, 음수 비중을 0으로 절단한 long-only minimum variance proxy를 계산했다.

{_markdown_table(outputs["q50_min_variance_latest_weights"].head(10))}

Rolling 10일 단위 포트폴리오 변화:

{_markdown_table(outputs["q50_rolling_min_variance_summary"].tail(10))}

## Q52. 월간 수익률 PCA

첫 번째 주성분은 시장 공통요인에 가까우며, 위기 구간에서 PC1 설명력이 상승하면 분산효과가 약해졌다고 해석할 수 있다.

{_markdown_table(outputs["q52_pca_summary"])}

## Q54. Low Volatility Bootstrap

Low Volatility 상위 30종목의 다음 월 초과수익률에 대해 bootstrap 평균 신뢰구간을 계산했다.

{_markdown_table(outputs["q54_low_vol_bootstrap"])}

## Q56. Momentum Skip-Month 비교

최근 1개월을 포함한 12개월 모멘텀과 최근 1개월을 제외한 12개월-1개월 모멘텀을 비교했다.

{_markdown_table(outputs["q56_momentum_skip_month_comparison"])}

## Q57. 거래비용 민감도

같은 멀티팩터 전략에 대해 0bp, 10bp, 30bp 거래비용을 적용했다.

{_markdown_table(_format_metrics(outputs["q57_transaction_cost_sensitivity"]))}

## Q58. 가중 방식 비교

Equal-weight, inverse-volatility, score-weight 방식의 성과를 비교했다.

{_markdown_table(_format_metrics(outputs["q58_weighting_comparison"]))}

## Q59. Fat-tail 진단

KOSPI200 동일가중 일간 수익률의 왜도, 첨도, empirical tail을 계산했다.

{_markdown_table(outputs["q59_fat_tail_summary"])}

## Q60. 위기 국면 상관구조 변화

일반 구간과 위기 구간의 평균 pairwise correlation을 비교했다.

{_markdown_table(outputs["q60_correlation_breakdown"])}

## 서류/면접 어필 포인트

1. 단순 백테스트가 아니라 사전과제형 문제를 프로젝트 모듈로 확장했다.
2. 공분산, PCA, bootstrap, fat-tail, 거래비용 민감도, 가중 방식 비교를 모두 같은 데이터셋에서 재현 가능하게 구현했다.
3. 금융 시계열에서 중요한 look-ahead bias, survivorship bias, transaction cost 문제를 보고서 한계와 향후 연구에 명시했다.
4. 결과가 좋지 않은 전략도 숨기지 않고 해석했다. 이는 리서치센터에서 중요한 검증 태도다.
"""


def _format_metrics(frame: pd.DataFrame) -> pd.DataFrame:
    display = frame.copy()
    percent_cols = [
        "total_return",
        "cagr",
        "annualized_volatility",
        "max_drawdown",
        "win_rate",
        "benchmark_total_return",
        "active_total_return",
        "tracking_error",
        "average_turnover",
    ]
    for col in percent_cols:
        if col in display:
            display[col] = display[col].map(lambda x: f"{x:.2%}")
    for col in ["sharpe", "information_ratio"]:
        if col in display:
            display[col] = display[col].map(lambda x: f"{x:.2f}")
    return display


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No data._"
    display = frame.copy()
    for col in display.columns:
        if pd.api.types.is_float_dtype(display[col]):
            display[col] = display[col].map(lambda x: "" if pd.isna(x) else f"{x:.6f}")
    headers = [str(c) for c in display.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in display.astype(str).values.tolist():
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)
