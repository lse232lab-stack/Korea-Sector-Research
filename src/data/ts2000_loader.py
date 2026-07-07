"""Load and standardize TS2000 fundamentals data."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.data.cleaner import standardize_ticker


TS2000_COLUMN_MAP = {
    "회사명": "name",
    "거래소코드": "ticker",
    "회계년도": "fiscal_period",
    "[공통]자산(*)(IFRS)(천원)": "assets_krw_thousand",
    "[공통]자본(*)(IFRS)(천원)": "equity_krw_thousand",
    "[공통]* 발행한 주식총수(*)(IFRS)(주)": "shares_outstanding",
    "[공통]   보통주(IFRS)(주)": "common_shares",
    "[공통]   우선주(IFRS)(주)": "preferred_shares",
    "[공통]부채(*)(IFRS)(천원)": "liabilities_krw_thousand",
    "[공통]* (정상)영업손익(계산수치)(IFRS)(천원)": "operating_income_krw_thousand",
    "[공통]당기순이익(손실)(IFRS)(천원)": "net_income_krw_thousand",
    "[공통]영업활동으로 인한 현금흐름(간접법)(*)(IFRS)(천원)": "operating_cash_flow_krw_thousand",
    "[공통]거래년도(*)": "trading_year",
    "[공통]거래량(주)": "volume",
    "[공통]종가(원)": "close",
    "[공통]자기자본순이익률(IFRS)": "roe_percent",
}

ACCOUNTING_COLUMNS_THOUSAND_KRW = [
    "assets",
    "equity",
    "liabilities",
    "operating_income",
    "net_income",
    "operating_cash_flow",
]

FUNDAMENTALS_COLUMNS = [
    "ticker",
    "name",
    "fiscal_period",
    "fiscal_year",
    "fiscal_quarter",
    "report_date",
    "available_date",
    "assets",
    "equity",
    "liabilities",
    "revenue",
    "operating_income",
    "net_income",
    "operating_cash_flow",
    "shares_outstanding",
    "preferred_shares",
    "close",
    "market_cap",
    "per",
    "pbr",
    "psr",
    "ev_ebitda",
    "roe",
    "roa",
    "operating_margin",
    "debt_ratio",
    "operating_cash_flow_to_net_income",
    "sector",
    "source_row_count",
    "source_note",
]


def load_fundamentals(path: str):
    """Load standardized fundamentals CSV."""
    return pd.read_csv(
        path,
        dtype={"ticker": "string"},
        parse_dates=["report_date", "available_date"],
    )


def standardize_ts2000_excel(
    source_path: str | Path,
    *,
    output_path: str | Path = "data/raw/ts2000/fundamentals.csv",
    disclosure_lag_months: int = 3,
) -> pd.DataFrame:
    """Convert the raw TS2000 workbook into the project fundamentals schema."""
    source_path = Path(source_path)
    raw = pd.read_excel(source_path)
    renamed = raw.rename(columns=TS2000_COLUMN_MAP)

    missing = [
        original for original in TS2000_COLUMN_MAP if original not in raw.columns
    ]
    if missing:
        raise ValueError("Missing TS2000 columns: " + ", ".join(missing))

    renamed["ticker"] = renamed["ticker"].map(standardize_ticker)
    renamed["fiscal_period"] = renamed["fiscal_period"].astype(str).str.replace("/", "-")
    renamed["fiscal_period_date"] = pd.to_datetime(
        renamed["fiscal_period"] + "-01",
        errors="coerce",
    )

    for source_column, target_column in {
        "assets_krw_thousand": "assets",
        "equity_krw_thousand": "equity",
        "liabilities_krw_thousand": "liabilities",
        "operating_income_krw_thousand": "operating_income",
        "net_income_krw_thousand": "net_income",
        "operating_cash_flow_krw_thousand": "operating_cash_flow",
    }.items():
        renamed[target_column] = pd.to_numeric(
            renamed[source_column],
            errors="coerce",
        ) * 1_000

    numeric_columns = [
        "shares_outstanding",
        "common_shares",
        "preferred_shares",
        "volume",
        "close",
        "roe_percent",
    ]
    for column in numeric_columns:
        renamed[column] = pd.to_numeric(renamed[column], errors="coerce")

    group_columns = ["ticker", "fiscal_period"]
    agg_map = {
        "name": "first",
        "fiscal_period_date": "first",
        "assets": "first",
        "equity": "first",
        "liabilities": "first",
        "operating_income": "first",
        "net_income": "first",
        "operating_cash_flow": "first",
        "shares_outstanding": "first",
        "preferred_shares": "first",
        "close": "last",
        "volume": "sum",
        "roe_percent": "first",
    }
    collapsed = (
        renamed.sort_values(group_columns)
        .groupby(group_columns, as_index=False)
        .agg(**{column: (column, method) for column, method in agg_map.items()})
    )
    source_counts = (
        renamed.groupby(group_columns)
        .size()
        .rename("source_row_count")
        .reset_index()
    )
    collapsed = collapsed.merge(source_counts, on=group_columns, how="left")

    period = collapsed["fiscal_period_date"]
    collapsed["fiscal_year"] = period.dt.year.astype("Int64")
    collapsed["fiscal_quarter"] = period.dt.quarter.astype("Int64")
    report_date = period + pd.offsets.MonthEnd(0)
    available_date = report_date + pd.DateOffset(months=disclosure_lag_months)
    collapsed["report_date"] = report_date.dt.date
    collapsed["available_date"] = (available_date + pd.offsets.MonthEnd(0)).dt.date

    collapsed["market_cap"] = collapsed["close"] * collapsed["shares_outstanding"]
    collapsed["per"] = _safe_divide_positive_denominator(
        collapsed["market_cap"],
        collapsed["net_income"],
    )
    collapsed["pbr"] = _safe_divide_positive_denominator(
        collapsed["market_cap"],
        collapsed["equity"],
    )
    collapsed["psr"] = pd.NA
    collapsed["ev_ebitda"] = pd.NA
    collapsed["roe"] = collapsed["roe_percent"] / 100
    collapsed["roa"] = _safe_divide(collapsed["net_income"], collapsed["assets"])
    collapsed["operating_margin"] = pd.NA
    collapsed["debt_ratio"] = _safe_divide(collapsed["liabilities"], collapsed["equity"])
    collapsed["operating_cash_flow_to_net_income"] = _safe_divide(
        collapsed["operating_cash_flow"],
        collapsed["net_income"],
    )
    collapsed["revenue"] = pd.NA
    collapsed["sector"] = pd.NA
    collapsed["source_note"] = (
        "TS2000 raw workbook; accounting amounts converted from thousand KRW to KRW. "
        f"available_date assumes fiscal period end plus {disclosure_lag_months} months."
    )

    output = collapsed[FUNDAMENTALS_COLUMNS].sort_values(
        ["ticker", "fiscal_period"]
    )
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    denominator = denominator.mask(denominator == 0)
    return numerator / denominator


def _safe_divide_positive_denominator(
    numerator: pd.Series,
    denominator: pd.Series,
) -> pd.Series:
    return numerator / denominator.where(denominator > 0)
