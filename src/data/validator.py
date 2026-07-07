"""Data validation utilities for raw project inputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.data.price_loader import PRICE_COLUMNS, load_prices
from src.data.ts2000_loader import FUNDAMENTALS_COLUMNS, load_fundamentals


@dataclass(frozen=True)
class PriceValidationResult:
    summary: pd.DataFrame
    issues: pd.DataFrame


@dataclass(frozen=True)
class FundamentalsValidationResult:
    summary: pd.DataFrame
    coverage: pd.DataFrame
    issues: pd.DataFrame


def validate_price_data(path: str | Path) -> PriceValidationResult:
    """Validate standardized price data and return summary/issue tables."""
    path = Path(path)
    issues = []
    if not path.exists():
        return PriceValidationResult(
            summary=pd.DataFrame(),
            issues=pd.DataFrame(
                [{"severity": "error", "check": "file_exists", "detail": str(path)}]
            ),
        )

    frame = load_prices(str(path))
    missing_columns = [column for column in PRICE_COLUMNS if column not in frame.columns]
    if missing_columns:
        issues.append(
            {
                "severity": "error",
                "check": "required_columns",
                "detail": ",".join(missing_columns),
            }
        )

    if frame.empty:
        issues.append({"severity": "error", "check": "non_empty", "detail": str(path)})
        return PriceValidationResult(
            summary=pd.DataFrame(),
            issues=pd.DataFrame(issues),
        )

    frame["ticker"] = frame["ticker"].astype("string").str.zfill(6)
    duplicate_count = int(frame.duplicated(["ticker", "date"]).sum())
    missing_adj_close = int(frame["adj_close"].isna().sum())
    missing_volume = int(frame["volume"].isna().sum())
    nonpositive_adj_close = int((frame["adj_close"] <= 0).sum())
    nonpositive_volume = int((frame["volume"] < 0).sum())

    for check, count in {
        "duplicate_ticker_date": duplicate_count,
        "missing_adj_close": missing_adj_close,
        "missing_volume": missing_volume,
        "nonpositive_adj_close": nonpositive_adj_close,
        "negative_volume": nonpositive_volume,
    }.items():
        if count:
            issues.append({"severity": "warning", "check": check, "detail": count})

    summary = (
        frame.groupby("ticker", as_index=False)
        .agg(
            rows=("date", "size"),
            start_date=("date", "min"),
            end_date=("date", "max"),
            first_adj_close=("adj_close", "first"),
            last_adj_close=("adj_close", "last"),
            total_volume=("volume", "sum"),
            total_trading_value=("trading_value", "sum"),
        )
        .sort_values("ticker")
    )
    summary["simple_return"] = (
        summary["last_adj_close"] / summary["first_adj_close"] - 1
    )
    summary["start_date"] = summary["start_date"].dt.strftime("%Y-%m-%d")
    summary["end_date"] = summary["end_date"].dt.strftime("%Y-%m-%d")

    return PriceValidationResult(
        summary=summary,
        issues=pd.DataFrame(issues, columns=["severity", "check", "detail"]),
    )


def validate_fundamentals_data(path: str | Path) -> FundamentalsValidationResult:
    """Validate standardized fundamentals data and return summary tables."""
    path = Path(path)
    issues = []
    if not path.exists():
        return FundamentalsValidationResult(
            summary=pd.DataFrame(),
            coverage=pd.DataFrame(),
            issues=pd.DataFrame(
                [{"severity": "warning", "check": "file_exists", "detail": str(path)}]
            ),
        )

    frame = load_fundamentals(str(path))
    missing_columns = [
        column for column in FUNDAMENTALS_COLUMNS if column not in frame.columns
    ]
    if missing_columns:
        issues.append(
            {
                "severity": "error",
                "check": "fundamentals_required_columns",
                "detail": ",".join(missing_columns),
            }
        )

    if frame.empty:
        issues.append(
            {"severity": "error", "check": "fundamentals_non_empty", "detail": str(path)}
        )
        return FundamentalsValidationResult(
            summary=pd.DataFrame(),
            coverage=pd.DataFrame(),
            issues=pd.DataFrame(issues),
        )

    frame["ticker"] = frame["ticker"].astype("string").str.zfill(6)
    duplicate_count = int(frame.duplicated(["ticker", "fiscal_period"]).sum())
    invalid_available_dates = int(
        (frame["available_date"] < frame["report_date"]).sum()
    )
    missing_core = {
        column: int(frame[column].isna().sum())
        for column in [
            "assets",
            "equity",
            "net_income",
            "operating_cash_flow",
            "market_cap",
            "pbr",
            "roe",
            "roa",
            "debt_ratio",
        ]
    }

    if duplicate_count:
        issues.append(
            {
                "severity": "warning",
                "check": "duplicate_ticker_fiscal_period",
                "detail": duplicate_count,
            }
        )
    if invalid_available_dates:
        issues.append(
            {
                "severity": "error",
                "check": "available_date_before_report_date",
                "detail": invalid_available_dates,
            }
        )
    for column, count in missing_core.items():
        if count:
            issues.append(
                {
                    "severity": "info",
                    "check": f"missing_{column}",
                    "detail": count,
                }
            )

    summary = pd.DataFrame(
        [
            {
                "rows": len(frame),
                "tickers": frame["ticker"].nunique(),
                "start_period": frame["fiscal_period"].min(),
                "end_period": frame["fiscal_period"].max(),
                "duplicate_ticker_period": duplicate_count,
                "median_source_rows": frame["source_row_count"].median(),
            }
        ]
    )
    coverage = (
        frame.groupby("fiscal_year", as_index=False)
        .agg(rows=("ticker", "size"), tickers=("ticker", "nunique"))
        .sort_values("fiscal_year")
    )

    return FundamentalsValidationResult(
        summary=summary,
        coverage=coverage,
        issues=pd.DataFrame(issues, columns=["severity", "check", "detail"]),
    )


def write_price_validation_outputs(
    price_path: str | Path,
    *,
    tables_dir: str | Path = "outputs/tables",
    reports_dir: str | Path = "outputs/reports",
) -> PriceValidationResult:
    """Validate price data and write CSV/Markdown outputs."""
    result = validate_price_data(price_path)
    tables_dir = Path(tables_dir)
    reports_dir = Path(reports_dir)
    tables_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    result.summary.to_csv(
        tables_dir / "price_data_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )
    result.issues.to_csv(
        tables_dir / "price_data_issues.csv",
        index=False,
        encoding="utf-8-sig",
    )
    (reports_dir / "data_validation_report.md").write_text(
        build_price_validation_markdown(result),
        encoding="utf-8",
    )
    return result


def write_data_validation_outputs(
    price_path: str | Path,
    fundamentals_path: str | Path,
    *,
    tables_dir: str | Path = "outputs/tables",
    reports_dir: str | Path = "outputs/reports",
) -> tuple[PriceValidationResult, FundamentalsValidationResult]:
    """Validate available raw inputs and write CSV/Markdown outputs."""
    price_result = validate_price_data(price_path)
    fundamentals_result = validate_fundamentals_data(fundamentals_path)
    tables_dir = Path(tables_dir)
    reports_dir = Path(reports_dir)
    tables_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    price_result.summary.to_csv(
        tables_dir / "price_data_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )
    price_result.issues.to_csv(
        tables_dir / "price_data_issues.csv",
        index=False,
        encoding="utf-8-sig",
    )
    fundamentals_result.summary.to_csv(
        tables_dir / "fundamentals_data_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )
    fundamentals_result.coverage.to_csv(
        tables_dir / "fundamentals_yearly_coverage.csv",
        index=False,
        encoding="utf-8-sig",
    )
    fundamentals_result.issues.to_csv(
        tables_dir / "fundamentals_data_issues.csv",
        index=False,
        encoding="utf-8-sig",
    )
    (reports_dir / "data_validation_report.md").write_text(
        build_data_validation_markdown(price_result, fundamentals_result),
        encoding="utf-8",
    )
    return price_result, fundamentals_result


def build_price_validation_markdown(result: PriceValidationResult) -> str:
    """Build a concise Markdown validation report."""
    lines = [
        "# Data Validation Report",
        "",
        "## Price Data",
        "",
    ]
    if result.summary.empty:
        lines.append("No valid price data summary is available.")
    else:
        lines.append(_dataframe_to_markdown(result.summary))

    lines.extend(["", "## Issues", ""])
    if result.issues.empty:
        lines.append("No price data issues detected.")
    else:
        lines.append(_dataframe_to_markdown(result.issues))

    lines.extend(
        [
            "",
            "## Next Checks",
            "",
            "- Add TS2000 fundamentals and validate `available_date` lag assumptions.",
            "- Add benchmark data for KOSPI200 relative return and tracking error.",
            "- Expand price fetch from the test ticker set to the KOSPI200 universe.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_data_validation_markdown(
    price_result: PriceValidationResult,
    fundamentals_result: FundamentalsValidationResult,
) -> str:
    """Build a Markdown validation report for all available data."""
    lines = [
        "# Data Validation Report",
        "",
        "## Price Data",
        "",
        _dataframe_to_markdown(price_result.summary)
        if not price_result.summary.empty
        else "No valid price data summary is available.",
        "",
        "## Fundamentals Data",
        "",
        _dataframe_to_markdown(fundamentals_result.summary)
        if not fundamentals_result.summary.empty
        else "No valid fundamentals data summary is available.",
        "",
        "## Fundamentals Yearly Coverage",
        "",
        _dataframe_to_markdown(fundamentals_result.coverage.tail(15))
        if not fundamentals_result.coverage.empty
        else "No fundamentals coverage table is available.",
        "",
        "## Issues",
        "",
        "### Price",
        "",
        _dataframe_to_markdown(price_result.issues)
        if not price_result.issues.empty
        else "No price data issues detected.",
        "",
        "### Fundamentals",
        "",
        _dataframe_to_markdown(fundamentals_result.issues)
        if not fundamentals_result.issues.empty
        else "No fundamentals data issues detected.",
        "",
        "## Next Checks",
        "",
        "- Add benchmark data for KOSPI200 relative return and tracking error.",
        "- Expand price fetch from the test ticker set to the KOSPI200 universe.",
        "- Implement Value and Quality factors from standardized fundamentals.",
    ]
    return "\n".join(lines) + "\n"


def _dataframe_to_markdown(frame: pd.DataFrame) -> str:
    """Render a small DataFrame as a Markdown table without optional packages."""
    if frame.empty:
        return ""

    display = frame.copy()
    for column in display.columns:
        if pd.api.types.is_float_dtype(display[column]):
            display[column] = display[column].map(
                lambda value: "" if pd.isna(value) else f"{value:.4f}"
            )
        else:
            display[column] = display[column].map(
                lambda value: "" if pd.isna(value) else str(value)
            )

    headers = [str(column) for column in display.columns]
    rows = display.values.tolist()
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(lines)
