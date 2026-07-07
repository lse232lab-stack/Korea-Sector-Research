"""Load the long-horizon TS2000 wide fundamentals workbooks."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from src.data.cleaner import standardize_ticker
from src.research.dataset_split import assign_research_split


DEFAULT_LONG_HORIZON_SOURCES = [
    "/Users/leesangeui/Downloads/kospi07-11.xlsx",
    "/Users/leesangeui/Downloads/kospi12-16.xlsx",
    "/Users/leesangeui/Downloads/kospi 17-21.xlsx",
    "/Users/leesangeui/Downloads/kospi22-26.xlsx",
]

WIDE_TS2000_COLUMN_MAP = {
    "회사명": "name",
    "거래소코드": "ticker",
    "회계년도": "fiscal_period",
    "[A100000000][공통]자산(*)(IFRS)(천원)": "assets_krw_thousand",
    "[A600000000][공통]자본(*)(IFRS)(천원)": "equity_krw_thousand",
    "[A800000000][공통]부채(*)(IFRS)(천원)": "liabilities_krw_thousand",
    "[A600010200][공통]* 발행한 주식총수(*)(IFRS)(주)": "shares_outstanding",
    "[A600010300][공통]   보통주(IFRS)(주)": "common_shares",
    "[A600010400][공통]   우선주(IFRS)(주)": "preferred_shares",
    "[B430000000][공통]* (정상)영업손익(계산수치)(IFRS)(천원)": "operating_income_krw_thousand",
    "[B840000000][공통]당기순이익(손실)(IFRS)(천원)": "net_income_krw_thousand",
    "[D100000000][공통]영업활동으로 인한 현금흐름(간접법)(*)(IFRS)(천원)": "operating_cash_flow_krw_thousand",
    "[공통]종가(원)": "close",
    "[공통]거래량(주)": "volume",
    "[공통]거래대금(백원)": "trading_value_100krw",
    "[공통]PER(최고)(IFRS)": "per_high",
    "[공통]PER(최저)(IFRS)": "per_low",
    "[공통]PBR(최고)(IFRS)": "pbr_high",
    "[공통]PBR(최저)(IFRS)": "pbr_low",
    "[공통]PCR(최고)(IFRS)": "pcr_high",
    "[공통]PCR(최저)(IFRS)": "pcr_low",
    "[공통]PSR(최고)(IFRS)": "psr_high",
    "[공통]PSR(최저)(IFRS)": "psr_low",
    "[공통]자기자본순이익률(IFRS)": "roe_percent",
    "[공통]총자본순이익률(IFRS)": "roa_percent",
    "[공통]매출액정상영업이익률(IFRS)": "operating_margin_percent",
    "[공통]매출액순이익률(IFRS)": "net_margin_percent",
    "[공통]부채비율(IFRS)": "debt_ratio_percent",
    "[공통]매출액증가율(IFRS)": "sales_growth_percent",
    "[공통]총자본증가율(IFRS)": "asset_growth_percent",
    "[공통]1주당매출액(IFRS)(원)": "sales_per_share",
}

STANDARD_OUTPUT_COLUMNS = [
    "ticker",
    "name",
    "fiscal_period",
    "fiscal_year",
    "fiscal_quarter",
    "report_date",
    "available_date",
    "research_split",
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
    "volume",
    "trading_value",
    "market_cap",
    "per",
    "pbr",
    "psr",
    "pcr",
    "ev_ebitda",
    "roe",
    "roa",
    "operating_margin",
    "net_margin",
    "debt_ratio",
    "sales_growth",
    "asset_growth",
    "operating_cash_flow_to_net_income",
    "sector",
    "source_row_count",
    "source_note",
]


def prepare_long_horizon_fundamentals(
    source_paths: list[str | Path] | None = None,
    *,
    output_path: str | Path = "data/raw/ts2000/fundamentals_long.csv",
    dictionary_output_path: str | Path = "outputs/tables/ts2000_wide_column_dictionary.csv",
    split_summary_output_path: str | Path = "outputs/tables/research_split_summary.csv",
    disclosure_lag_months: int = 3,
) -> pd.DataFrame:
    """Combine the 2007-2026 TS2000 workbooks into the project schema."""
    paths = [Path(path) for path in (source_paths or DEFAULT_LONG_HORIZON_SOURCES)]
    _write_column_dictionary(paths, dictionary_output_path)

    usecols = list(WIDE_TS2000_COLUMN_MAP)
    frames = []
    for path in paths:
        raw = pd.read_excel(path, usecols=usecols)
        raw["source_file"] = path.name
        frames.append(raw)

    combined = pd.concat(frames, ignore_index=True)
    standardized = _standardize_wide_ts2000_frame(
        combined,
        disclosure_lag_months=disclosure_lag_months,
    )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    standardized.to_csv(output_path, index=False, encoding="utf-8-sig")

    split_summary_path = Path(split_summary_output_path)
    split_summary_path.parent.mkdir(parents=True, exist_ok=True)
    _build_split_summary(standardized).to_csv(
        split_summary_path,
        index=False,
        encoding="utf-8-sig",
    )
    return standardized


def _standardize_wide_ts2000_frame(
    raw: pd.DataFrame,
    *,
    disclosure_lag_months: int,
) -> pd.DataFrame:
    missing = [column for column in WIDE_TS2000_COLUMN_MAP if column not in raw.columns]
    if missing:
        raise ValueError("Missing wide TS2000 columns: " + ", ".join(missing))

    renamed = raw.rename(columns=WIDE_TS2000_COLUMN_MAP)
    renamed["ticker"] = renamed["ticker"].map(standardize_ticker)
    renamed["fiscal_period"] = renamed["fiscal_period"].astype(str).str.replace("/", "-")
    renamed["fiscal_period_date"] = pd.to_datetime(
        renamed["fiscal_period"] + "-01",
        errors="coerce",
    )

    for column in [
        "assets_krw_thousand",
        "equity_krw_thousand",
        "liabilities_krw_thousand",
        "operating_income_krw_thousand",
        "net_income_krw_thousand",
        "operating_cash_flow_krw_thousand",
        "shares_outstanding",
        "common_shares",
        "preferred_shares",
        "close",
        "volume",
        "trading_value_100krw",
        "per_high",
        "per_low",
        "pbr_high",
        "pbr_low",
        "pcr_high",
        "pcr_low",
        "psr_high",
        "psr_low",
        "roe_percent",
        "roa_percent",
        "operating_margin_percent",
        "net_margin_percent",
        "debt_ratio_percent",
        "sales_growth_percent",
        "asset_growth_percent",
        "sales_per_share",
    ]:
        renamed[column] = pd.to_numeric(renamed[column], errors="coerce")

    for source_column, target_column in {
        "assets_krw_thousand": "assets",
        "equity_krw_thousand": "equity",
        "liabilities_krw_thousand": "liabilities",
        "operating_income_krw_thousand": "operating_income",
        "net_income_krw_thousand": "net_income",
        "operating_cash_flow_krw_thousand": "operating_cash_flow",
    }.items():
        renamed[target_column] = renamed[source_column] * 1_000

    renamed["trading_value"] = renamed["trading_value_100krw"] * 100
    renamed["revenue"] = renamed["sales_per_share"] * renamed["shares_outstanding"]

    group_columns = ["ticker", "fiscal_period"]
    agg_map = {
        "name": "first",
        "fiscal_period_date": "first",
        "assets": "first",
        "equity": "first",
        "liabilities": "first",
        "revenue": "first",
        "operating_income": "first",
        "net_income": "first",
        "operating_cash_flow": "first",
        "shares_outstanding": "first",
        "preferred_shares": "first",
        "close": "last",
        "volume": "sum",
        "trading_value": "sum",
        "per_high": "mean",
        "per_low": "mean",
        "pbr_high": "mean",
        "pbr_low": "mean",
        "pcr_high": "mean",
        "pcr_low": "mean",
        "psr_high": "mean",
        "psr_low": "mean",
        "roe_percent": "first",
        "roa_percent": "first",
        "operating_margin_percent": "first",
        "net_margin_percent": "first",
        "debt_ratio_percent": "first",
        "sales_growth_percent": "first",
        "asset_growth_percent": "first",
        "source_file": lambda series: ",".join(sorted(set(series.dropna().astype(str)))),
    }
    collapsed = (
        renamed.sort_values(group_columns)
        .groupby(group_columns, as_index=False)
        .agg(**{column: (column, method) for column, method in agg_map.items()})
    )
    source_counts = (
        renamed.groupby(group_columns).size().rename("source_row_count").reset_index()
    )
    collapsed = collapsed.merge(source_counts, on=group_columns, how="left")

    period = collapsed["fiscal_period_date"]
    collapsed["fiscal_year"] = period.dt.year.astype("Int64")
    collapsed["fiscal_quarter"] = period.dt.quarter.astype("Int64")
    report_date = period + pd.offsets.MonthEnd(0)
    available_date = report_date + pd.DateOffset(months=disclosure_lag_months)
    collapsed["report_date"] = report_date.dt.date
    collapsed["available_date"] = (available_date + pd.offsets.MonthEnd(0)).dt.date
    collapsed = assign_research_split(collapsed, date_col="available_date")

    collapsed["market_cap"] = collapsed["close"] * collapsed["shares_outstanding"]
    collapsed["per"] = _prefer_statement_ratio(
        _safe_divide_positive_denominator(collapsed["market_cap"], collapsed["net_income"]),
        collapsed["per_high"],
        collapsed["per_low"],
    )
    collapsed["pbr"] = _prefer_statement_ratio(
        _safe_divide_positive_denominator(collapsed["market_cap"], collapsed["equity"]),
        collapsed["pbr_high"],
        collapsed["pbr_low"],
    )
    collapsed["psr"] = _prefer_statement_ratio(
        _safe_divide_positive_denominator(collapsed["market_cap"], collapsed["revenue"]),
        collapsed["psr_high"],
        collapsed["psr_low"],
    )
    collapsed["pcr"] = _prefer_statement_ratio(
        _safe_divide_positive_denominator(
            collapsed["market_cap"],
            collapsed["operating_cash_flow"],
        ),
        collapsed["pcr_high"],
        collapsed["pcr_low"],
    )
    collapsed["ev_ebitda"] = pd.NA
    collapsed["roe"] = collapsed["roe_percent"] / 100
    collapsed["roa"] = collapsed["roa_percent"] / 100
    collapsed["operating_margin"] = collapsed["operating_margin_percent"] / 100
    collapsed["net_margin"] = collapsed["net_margin_percent"] / 100
    collapsed["debt_ratio"] = collapsed["debt_ratio_percent"] / 100
    collapsed["sales_growth"] = collapsed["sales_growth_percent"] / 100
    collapsed["asset_growth"] = collapsed["asset_growth_percent"] / 100
    collapsed["operating_cash_flow_to_net_income"] = _safe_divide(
        collapsed["operating_cash_flow"],
        collapsed["net_income"],
    )
    collapsed["sector"] = pd.NA
    collapsed["source_note"] = (
        "TS2000 long-horizon wide workbooks; accounting amounts converted from "
        "thousand KRW to KRW. available_date assumes fiscal period end plus "
        f"{disclosure_lag_months} months. research_split is based on available_date."
    )

    return collapsed[STANDARD_OUTPUT_COLUMNS].sort_values(["ticker", "fiscal_period"])


def _write_column_dictionary(
    paths: list[Path],
    output_path: str | Path,
) -> pd.DataFrame:
    rows = []
    seen_columns: set[str] = set()
    for path in paths:
        columns = [str(column).strip() for column in pd.read_excel(path, nrows=0).columns]
        for position, column in enumerate(columns, start=1):
            if column in seen_columns:
                continue
            seen_columns.add(column)
            rows.append(
                {
                    "source_column": column,
                    "canonical_name": WIDE_TS2000_COLUMN_MAP.get(column, ""),
                    "position": position,
                    "statement_block": _infer_statement_block(column),
                    "unit": _infer_unit(column),
                    "include_in_standard_schema": column in WIDE_TS2000_COLUMN_MAP,
                }
            )
    dictionary = pd.DataFrame(rows)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dictionary.to_csv(output_path, index=False, encoding="utf-8-sig")
    return dictionary


def _build_split_summary(frame: pd.DataFrame) -> pd.DataFrame:
    return (
        frame.groupby("research_split", as_index=False)
        .agg(
            rows=("ticker", "size"),
            tickers=("ticker", "nunique"),
            min_available_date=("available_date", "min"),
            max_available_date=("available_date", "max"),
            min_fiscal_period=("fiscal_period", "min"),
            max_fiscal_period=("fiscal_period", "max"),
        )
        .sort_values("min_available_date")
    )


def _prefer_statement_ratio(
    direct_ratio: pd.Series,
    high_ratio: pd.Series,
    low_ratio: pd.Series,
) -> pd.Series:
    average_ratio = pd.concat([high_ratio, low_ratio], axis=1).mean(axis=1)
    return direct_ratio.where(direct_ratio.notna(), average_ratio)


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    return numerator / denominator.mask(denominator == 0)


def _safe_divide_positive_denominator(
    numerator: pd.Series,
    denominator: pd.Series,
) -> pd.Series:
    return numerator / denominator.where(denominator > 0)


def _infer_statement_block(column: str) -> str:
    match = re.match(r"\[([A-Z])", column)
    if not match:
        return "market_or_ratio"
    return {
        "A": "balance_sheet",
        "B": "income_statement",
        "C": "equity_statement",
        "D": "cash_flow_statement",
        "E": "appropriation_statement",
    }.get(match.group(1), "other_statement")


def _infer_unit(column: str) -> str:
    if "(천원)" in column:
        return "thousand_krw"
    if "(백원)" in column:
        return "hundred_krw"
    if "(원)" in column:
        return "krw"
    if "(주)" in column:
        return "shares"
    if "율" in column or "PER" in column or "PBR" in column or "PCR" in column or "PSR" in column:
        return "ratio_or_percent"
    return ""
