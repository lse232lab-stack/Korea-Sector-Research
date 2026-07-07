"""KIS paper-trading order planner for the institutional quant strategy."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from src.data.kis_client import KISAPIError, KISClient, KISConfig, polite_sleep


@dataclass(frozen=True)
class PaperTradingResult:
    target_portfolio: pd.DataFrame
    order_plan: pd.DataFrame
    account_snapshot: pd.DataFrame
    report_path: Path


def run_kis_paper_trading(
    *,
    score_path: str | Path = "data/features/institutional_core_satellite_scores.csv",
    price_path: str | Path = "data/raw/price/prices_2007_2026.csv",
    env_file: str | None = ".env",
    output_dir: str | Path = "outputs/paper_trading",
    report_output_path: str | Path = "outputs/reports/KIS_Paper_Trading_Run_Report.md",
    top_n: int = 30,
    initial_cash: float = 100_000_000,
    use_kis_quotes: bool = True,
    use_kis_balance: bool = True,
    submit_orders: bool = False,
    request_sleep_seconds: float = 0.2,
) -> PaperTradingResult:
    """Build a target portfolio, create order tickets, and optionally submit paper orders."""
    config = KISConfig.from_env(env_file)
    client = KISClient(config)
    scores = _load_latest_scores(score_path, top_n=top_n)
    prices = _load_latest_local_prices(price_path)
    targets = scores.merge(prices, on="ticker", how="left", suffixes=("", "_local"))

    quote_status = "not_requested"
    if use_kis_quotes:
        targets, quote_status = _attach_kis_quotes(
            client,
            targets,
            request_sleep_seconds=request_sleep_seconds,
        )
    if "kis_price" not in targets.columns:
        targets["kis_price"] = pd.NA

    holdings, account_status = _load_account_snapshot(
        client,
        use_kis_balance=use_kis_balance,
        fallback_cash=initial_cash,
    )
    portfolio_value = _portfolio_value(holdings, prices, fallback_cash=initial_cash)
    target_exposure = float(targets["target_exposure"].dropna().iloc[0]) if "target_exposure" in targets else 1.0
    cash_weight = max(0.0, 1.0 - target_exposure)
    investable_value = portfolio_value * target_exposure

    targets = targets.sort_values("composite_score", ascending=False).copy()
    targets["target_weight"] = target_exposure / len(targets)
    targets["target_value"] = investable_value / len(targets)
    quote_price = pd.to_numeric(targets["kis_price"], errors="coerce")
    local_price = pd.to_numeric(targets["adj_close"], errors="coerce")
    targets["execution_price"] = quote_price.fillna(local_price)
    targets["target_quantity"] = (
        targets["target_value"] / targets["execution_price"]
    ).fillna(0).astype(int)
    targets["target_order_value"] = targets["target_quantity"] * targets["execution_price"]

    order_plan = _build_order_plan(targets, holdings)
    submission_status = "dry_run"
    if submit_orders:
        if not config.is_paper:
            raise ValueError("Order submission is allowed only when KIS_IS_PAPER=true.")
        order_plan, submission_status = _submit_orders(
            client,
            order_plan,
            request_sleep_seconds=request_sleep_seconds,
        )

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    targets.to_csv(output_dir / "latest_target_portfolio.csv", index=False, encoding="utf-8-sig")
    order_plan.to_csv(output_dir / "latest_order_plan.csv", index=False, encoding="utf-8-sig")
    holdings.to_csv(output_dir / "latest_account_snapshot.csv", index=False, encoding="utf-8-sig")

    report_path = Path(report_output_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        _build_report(
            targets=targets,
            order_plan=order_plan,
            holdings=holdings,
            config=config,
            portfolio_value=portfolio_value,
            cash_weight=cash_weight,
            quote_status=quote_status,
            account_status=account_status,
            submission_status=submission_status,
        ),
        encoding="utf-8",
    )
    return PaperTradingResult(targets, order_plan, holdings, report_path)


def _load_latest_scores(path: str | Path, *, top_n: int) -> pd.DataFrame:
    scores = pd.read_csv(path, dtype={"ticker": "string"}, parse_dates=["signal_date"])
    scores["ticker"] = scores["ticker"].astype("string").str.zfill(6)
    scores = scores.dropna(subset=["signal_date", "composite_score"])
    latest_signal = scores["signal_date"].max()
    return (
        scores[scores["signal_date"].eq(latest_signal)]
        .sort_values("composite_score", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )


def _load_latest_local_prices(path: str | Path) -> pd.DataFrame:
    prices = pd.read_csv(path, dtype={"ticker": "string"}, parse_dates=["date"])
    prices["ticker"] = prices["ticker"].astype("string").str.zfill(6)
    prices = prices.dropna(subset=["date", "adj_close"])
    latest = prices.sort_values("date").groupby("ticker", as_index=False).tail(1)
    return latest[["ticker", "date", "adj_close", "close", "volume", "trading_value"]]


def _attach_kis_quotes(
    client: KISClient,
    targets: pd.DataFrame,
    *,
    request_sleep_seconds: float,
) -> tuple[pd.DataFrame, str]:
    rows: list[dict[str, Any]] = []
    failures = 0
    for ticker in targets["ticker"].astype(str):
        try:
            quote = client.get_domestic_current_price(ticker)
            rows.append(
                {
                    "ticker": ticker,
                    "kis_price": _to_float(quote.get("stck_prpr")),
                    "kis_change_rate": _to_float(quote.get("prdy_ctrt")),
                    "kis_accum_volume": _to_float(quote.get("acml_vol")),
                }
            )
        except (KISAPIError, OSError, ValueError) as exc:
            failures += 1
            rows.append({"ticker": ticker, "kis_quote_error": str(exc)})
        polite_sleep(request_sleep_seconds)
    quote_frame = pd.DataFrame(rows)
    enriched = targets.merge(quote_frame, on="ticker", how="left")
    if failures == 0:
        return enriched, "kis_quotes_ok"
    return enriched, f"kis_quotes_partial_failure_{failures}"


def _load_account_snapshot(
    client: KISClient,
    *,
    use_kis_balance: bool,
    fallback_cash: float,
) -> tuple[pd.DataFrame, str]:
    fallback = pd.DataFrame(
        [{"ticker": "CASH", "name": "Fallback cash", "quantity": 0, "cash": fallback_cash}]
    )
    if not use_kis_balance:
        return fallback, "fallback_cash_by_option"
    try:
        raw = client.get_domestic_balance()
    except (KISAPIError, OSError, ValueError) as exc:
        fallback["account_error"] = str(exc)
        return fallback, "fallback_cash_after_balance_error"

    positions = []
    for row in raw.get("output1", []) or []:
        quantity = int(float(row.get("hldg_qty", 0) or 0))
        if quantity <= 0:
            continue
        positions.append(
            {
                "ticker": str(row.get("pdno", "")).zfill(6),
                "name": row.get("prdt_name", ""),
                "quantity": quantity,
                "avg_price": _to_float(row.get("pchs_avg_pric")),
                "market_value": _to_float(row.get("evlu_amt")),
                "cash": 0.0,
            }
        )
    output2 = raw.get("output2", []) or []
    cash = fallback_cash
    if output2:
        summary = output2[0]
        cash = _first_positive(
            summary.get("dnca_tot_amt"),
            summary.get("nass_amt"),
            summary.get("tot_evlu_amt"),
            default=fallback_cash,
        )
    positions.append({"ticker": "CASH", "name": "KIS paper cash", "quantity": 0, "cash": cash})
    return pd.DataFrame(positions), "kis_balance_ok"


def _portfolio_value(holdings: pd.DataFrame, prices: pd.DataFrame, *, fallback_cash: float) -> float:
    if holdings.empty:
        return fallback_cash
    cash = pd.to_numeric(holdings.get("cash", 0), errors="coerce").fillna(0).sum()
    positions = holdings[holdings["ticker"].ne("CASH")].copy()
    if positions.empty:
        return float(cash or fallback_cash)
    positions = positions.merge(prices[["ticker", "adj_close"]], on="ticker", how="left")
    value = (
        pd.to_numeric(positions["quantity"], errors="coerce").fillna(0)
        * pd.to_numeric(positions["adj_close"], errors="coerce").fillna(0)
    ).sum()
    return float(cash + value)


def _build_order_plan(targets: pd.DataFrame, holdings: pd.DataFrame) -> pd.DataFrame:
    current = holdings[holdings["ticker"].ne("CASH")][["ticker", "quantity"]].copy()
    current["quantity"] = pd.to_numeric(current["quantity"], errors="coerce").fillna(0).astype(int)
    plan = targets.merge(current, on="ticker", how="left", suffixes=("", "_current"))
    plan["current_quantity"] = plan["quantity"].fillna(0).astype(int)
    plan["order_quantity_signed"] = plan["target_quantity"] - plan["current_quantity"]
    plan["side"] = plan["order_quantity_signed"].map(lambda value: "BUY" if value > 0 else "SELL")
    plan["order_quantity"] = plan["order_quantity_signed"].abs().astype(int)
    plan["order_type"] = "market"
    plan["dry_run"] = True
    cols = [
        "signal_date",
        "ticker",
        "name",
        "regime",
        "target_exposure",
        "composite_score",
        "target_weight",
        "execution_price",
        "current_quantity",
        "target_quantity",
        "side",
        "order_quantity",
        "order_type",
        "dry_run",
    ]
    return plan.loc[plan["order_quantity"].gt(0), [col for col in cols if col in plan.columns]]


def _submit_orders(
    client: KISClient,
    order_plan: pd.DataFrame,
    *,
    request_sleep_seconds: float,
) -> tuple[pd.DataFrame, str]:
    results = []
    for _, row in order_plan.iterrows():
        try:
            response = client.place_domestic_cash_order(
                ticker=row["ticker"],
                side=str(row["side"]).lower(),
                quantity=int(row["order_quantity"]),
                price=0,
                order_type="01",
            )
            results.append(response.get("msg1", "submitted"))
        except (KISAPIError, OSError, ValueError) as exc:
            results.append(f"failed: {exc}")
        polite_sleep(request_sleep_seconds)
    submitted = order_plan.copy()
    submitted["dry_run"] = False
    submitted["submission_result"] = results
    return submitted, "submitted_to_kis_paper"


def _build_report(
    *,
    targets: pd.DataFrame,
    order_plan: pd.DataFrame,
    holdings: pd.DataFrame,
    config: KISConfig,
    portfolio_value: float,
    cash_weight: float,
    quote_status: str,
    account_status: str,
    submission_status: str,
) -> str:
    latest_signal = targets["signal_date"].max().date()
    buys = int(order_plan["side"].eq("BUY").sum()) if not order_plan.empty else 0
    sells = int(order_plan["side"].eq("SELL").sum()) if not order_plan.empty else 0
    top_table = _markdown_table(
        targets[
            ["ticker", "name", "composite_score", "target_weight", "execution_price", "target_quantity"]
        ].head(10)
    )
    order_table = _markdown_table(
        order_plan[["ticker", "name", "side", "order_quantity", "execution_price"]].head(15)
    )
    submission_table = "No submission results."
    if "submission_result" in order_plan.columns:
        submission_summary = (
            order_plan["submission_result"]
            .fillna("")
            .value_counts()
            .rename_axis("submission_result")
            .reset_index(name="count")
        )
        submission_table = _markdown_table(submission_summary)
    mode = "paper-trading" if config.is_paper else "live-quotes-dry-run"
    return f"""# KIS 모의투자 시스템 트레이딩 실행 보고서

## 실행 요약

- 전략: KOSPI200 Institutional Core-Satellite Quant Strategy
- 신호일: {latest_signal}
- KIS 환경: {mode}
- 주문 상태: {submission_status}
- 현재가 조회 상태: {quote_status}
- 잔고 조회 상태: {account_status}
- 추정 포트폴리오 가치: {portfolio_value:,.0f}원
- 목표 주식 비중: {(1.0 - cash_weight):.1%}
- 목표 현금 비중: {cash_weight:.1%}
- 생성 주문: 매수 {buys}건, 매도 {sells}건

## 상위 목표 포트폴리오

{top_table}

## 주문 전표 미리보기

{order_table}

## 주문 전송 결과

{submission_table}

## 운용 해석

이 실행은 TS2000 재무 팩터, KIS 가격 데이터, Ridge ML 예측 신호를 결합한 월간 리밸런싱 전략을 KIS 모의투자 계좌 주문 전표로 변환한 결과다. 기본값은 dry-run으로 두어 실제 주문 전송 전에 목표 비중, 주문 수량, 현금 비중을 검토할 수 있게 했다.

## 리스크 통제

- 단일 신호에 과도하게 의존하지 않도록 Value, Quality, Momentum, Low Volatility, Growth, ML 신호를 혼합했다.
- 시장 국면이 neutral로 판정될 경우 목표 주식 노출을 80%로 제한하고 잔여 20%는 현금으로 둔다.
- 실제 주문 전송은 `--submit-paper-orders` 옵션을 명시적으로 켠 경우에만 수행한다.
"""


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No rows."
    output = frame.copy()
    for col in output.select_dtypes(include=["float"]).columns:
        output[col] = output[col].map(lambda value: f"{value:.4f}" if abs(value) < 10 else f"{value:,.0f}")
    output = output.fillna("")
    headers = [str(col) for col in output.columns]
    rows = [[str(value) for value in row] for row in output.to_numpy().tolist()]
    widths = [
        max(len(header), *(len(row[index]) for row in rows)) if rows else len(header)
        for index, header in enumerate(headers)
    ]
    header_line = "| " + " | ".join(
        header.ljust(widths[index]) for index, header in enumerate(headers)
    ) + " |"
    separator = "| " + " | ".join("-" * width for width in widths) + " |"
    body = [
        "| " + " | ".join(row[index].ljust(widths[index]) for index in range(len(headers))) + " |"
        for row in rows
    ]
    return "\n".join([header_line, separator, *body])


def _to_float(value: Any) -> float:
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return float("nan")


def _first_positive(*values: Any, default: float) -> float:
    for value in values:
        number = _to_float(value)
        if pd.notna(number) and number > 0:
            return float(number)
    return float(default)
