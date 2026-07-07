"""Load, fetch, and standardize daily stock price data."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable

import pandas as pd

from src.data.cleaner import standardize_ticker
from src.data.kis_client import KISAPIError, KISClient, polite_sleep


PRICE_COLUMNS = [
    "date",
    "ticker",
    "name",
    "open",
    "high",
    "low",
    "close",
    "adj_close",
    "volume",
    "trading_value",
    "market_cap",
    "sector",
    "is_suspended",
    "is_administrative",
]


def load_prices(path: str):
    """Load standardized price CSV."""
    return pd.read_csv(path, dtype={"ticker": "string"}, parse_dates=["date"])


def normalize_kis_daily_prices(
    rows: list[dict],
    ticker: str,
    *,
    name: str | None = None,
) -> pd.DataFrame:
    """Normalize KIS daily chart rows into the project price schema."""
    ticker = standardize_ticker(ticker)
    records = []
    for row in rows:
        date_value = row.get("stck_bsop_date")
        if not date_value:
            continue

        records.append(
            {
                "date": pd.to_datetime(date_value, format="%Y%m%d"),
                "ticker": ticker,
                "name": name,
                "open": _to_number(row.get("stck_oprc")),
                "high": _to_number(row.get("stck_hgpr")),
                "low": _to_number(row.get("stck_lwpr")),
                "close": _to_number(row.get("stck_clpr")),
                "adj_close": _to_number(row.get("stck_clpr")),
                "volume": _to_number(row.get("acml_vol")),
                "trading_value": _to_number(row.get("acml_tr_pbmn")),
                "market_cap": None,
                "sector": None,
                "is_suspended": None,
                "is_administrative": None,
            }
        )

    frame = pd.DataFrame.from_records(records, columns=PRICE_COLUMNS)
    if frame.empty:
        return frame
    return frame.sort_values(["ticker", "date"]).reset_index(drop=True)


def fetch_prices_from_kis(
    client: KISClient,
    tickers: Iterable[str],
    start_date: str,
    end_date: str,
    *,
    output_path: str | Path = "data/raw/price/prices.csv",
    request_sleep_seconds: float = 0.25,
    max_retries: int = 5,
    retry_sleep_seconds: float = 5.0,
    resume: bool = False,
) -> pd.DataFrame:
    """Fetch daily prices from KIS and save a standardized CSV."""
    output_path = Path(output_path)
    existing = _load_existing_prices(output_path) if resume else pd.DataFrame(columns=PRICE_COLUMNS)
    existing = _prepare_existing_prices(existing)

    result = existing.copy()
    for ticker in tickers:
        clean_ticker = standardize_ticker(ticker)

        ticker_frames = []
        for chunk_start, chunk_end in _date_chunks(start_date, end_date):
            if resume and _existing_has_chunk(result, clean_ticker, chunk_start, chunk_end):
                continue
            rows = _fetch_daily_item_chart_price_with_retry(
                client,
                ticker=clean_ticker,
                start_date=chunk_start,
                end_date=chunk_end,
                max_retries=max_retries,
                retry_sleep_seconds=retry_sleep_seconds,
            )
            ticker_frames.append(normalize_kis_daily_prices(rows, clean_ticker))
            polite_sleep(request_sleep_seconds)

        if ticker_frames:
            non_empty_frames = [frame for frame in ticker_frames if not frame.empty]
            if non_empty_frames:
                ticker_data = pd.concat(non_empty_frames, ignore_index=True)
                result = _combine_price_frames(result, ticker_data)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                result.to_csv(output_path, index=False, encoding="utf-8-sig")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False, encoding="utf-8-sig")
    return result


def fetch_long_horizon_prices_from_kis(
    client: KISClient,
    tickers: Iterable[str],
    *,
    start_year: int,
    end_year: int,
    yearly_output_dir: str | Path = "data/raw/price/yearly",
    combined_output_path: str | Path = "data/raw/price/prices_2007_2026.csv",
    final_end_date: str | None = None,
    request_sleep_seconds: float = 1.0,
    max_retries: int = 5,
    retry_sleep_seconds: float = 5.0,
    resume: bool = True,
    summary_output_path: str | Path = "outputs/tables/long_price_fetch_summary.csv",
) -> pd.DataFrame:
    """Fetch long-horizon KIS prices year by year and combine the files."""
    if start_year > end_year:
        raise ValueError("start_year must be earlier than or equal to end_year.")

    yearly_output_dir = Path(yearly_output_dir)
    yearly_output_dir.mkdir(parents=True, exist_ok=True)
    tickers = [standardize_ticker(ticker) for ticker in tickers]
    summary_rows = []

    for year in range(start_year, end_year + 1):
        year_start = f"{year}0101"
        year_end = _year_end_for_fetch(year, end_year, final_end_date)
        output_path = yearly_output_dir / f"prices_{year}.csv"
        print(
            f"Fetching {year}: {len(tickers):,} ticker(s), "
            f"{year_start} to {year_end}, output={output_path}",
            flush=True,
        )
        frame = fetch_prices_from_kis(
            client,
            tickers=tickers,
            start_date=year_start,
            end_date=year_end,
            output_path=output_path,
            request_sleep_seconds=request_sleep_seconds,
            max_retries=max_retries,
            retry_sleep_seconds=retry_sleep_seconds,
            resume=resume,
        )
        summary_rows.append(
            {
                "year": year,
                "start_date": year_start,
                "end_date": year_end,
                "output_path": str(output_path),
                "rows": len(frame),
                "tickers": frame["ticker"].nunique() if "ticker" in frame else 0,
                "min_date": frame["date"].min() if not frame.empty else pd.NaT,
                "max_date": frame["date"].max() if not frame.empty else pd.NaT,
            }
        )

    summary = pd.DataFrame(summary_rows)
    summary_output_path = Path(summary_output_path)
    summary_output_path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(summary_output_path, index=False, encoding="utf-8-sig")

    combined = combine_yearly_price_files(
        yearly_output_dir,
        output_path=combined_output_path,
        start_year=start_year,
        end_year=end_year,
    )
    return combined


def combine_yearly_price_files(
    yearly_output_dir: str | Path = "data/raw/price/yearly",
    *,
    output_path: str | Path = "data/raw/price/prices_2007_2026.csv",
    start_year: int | None = None,
    end_year: int | None = None,
    coverage_output_path: str | Path = "outputs/tables/long_price_yearly_coverage.csv",
) -> pd.DataFrame:
    """Combine yearly price CSVs into one de-duplicated long-horizon file."""
    yearly_output_dir = Path(yearly_output_dir)
    paths = sorted(yearly_output_dir.glob("prices_*.csv"))
    if start_year is not None:
        paths = [path for path in paths if _year_from_price_path(path) >= start_year]
    if end_year is not None:
        paths = [path for path in paths if _year_from_price_path(path) <= end_year]
    if not paths:
        raise FileNotFoundError(f"No yearly price files found in {yearly_output_dir}")

    frames = [load_prices(str(path)) for path in paths]
    combined = pd.concat(frames, ignore_index=True)
    combined = _combine_price_frames(pd.DataFrame(columns=PRICE_COLUMNS), combined)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(output_path, index=False, encoding="utf-8-sig")
    _build_yearly_price_coverage(combined).to_csv(
        coverage_output_path,
        index=False,
        encoding="utf-8-sig",
    )
    return combined


def load_tickers_from_csv(path: str | Path, *, limit: int | None = None) -> list[str]:
    """Load tickers from a CSV with a `ticker` column."""
    frame = pd.read_csv(path, dtype={"ticker": "string"})
    if "ticker" not in frame.columns:
        raise ValueError(f"Ticker file must include a ticker column: {path}")
    tickers = frame["ticker"].dropna().map(standardize_ticker).drop_duplicates().tolist()
    return tickers[:limit] if limit else tickers


def _fetch_daily_item_chart_price_with_retry(
    client: KISClient,
    *,
    ticker: str,
    start_date: str,
    end_date: str,
    max_retries: int,
    retry_sleep_seconds: float,
) -> list[dict]:
    for attempt in range(max_retries + 1):
        try:
            return client.get_daily_item_chart_price(
                ticker,
                start_date=start_date,
                end_date=end_date,
                adjusted_price=True,
            )
        except KISAPIError as exc:
            if attempt >= max_retries:
                raise
            wait_seconds = retry_sleep_seconds * (attempt + 1)
            print(
                "KIS request retry "
                f"{attempt + 1}/{max_retries}: ticker={ticker}, "
                f"{start_date}-{end_date}, wait={wait_seconds:.1f}s, error={exc}",
                flush=True,
            )
            polite_sleep(wait_seconds)
    return []


def _build_yearly_price_coverage(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    output["year"] = pd.to_datetime(output["date"]).dt.year
    return (
        output.groupby("year", as_index=False)
        .agg(
            rows=("ticker", "size"),
            tickers=("ticker", "nunique"),
            min_date=("date", "min"),
            max_date=("date", "max"),
            duplicate_ticker_dates=(
                "ticker",
                lambda series: int(output.loc[series.index].duplicated(["ticker", "date"]).sum()),
            ),
        )
        .sort_values("year")
    )


def _year_end_for_fetch(
    year: int,
    end_year: int,
    final_end_date: str | None,
) -> str:
    if year == end_year and final_end_date:
        return final_end_date
    if year == date.today().year:
        yesterday = date.today() - timedelta(days=1)
        return yesterday.strftime("%Y%m%d")
    return f"{year}1231"


def _year_from_price_path(path: Path) -> int:
    stem = path.stem
    try:
        return int(stem.rsplit("_", 1)[1])
    except (IndexError, ValueError) as exc:
        raise ValueError(f"Could not infer year from price file name: {path}") from exc


def _date_chunks(
    start_date: str,
    end_date: str,
    *,
    chunk_days: int = 90,
) -> list[tuple[str, str]]:
    """Split YYYYMMDD date range into API-friendly chunks."""
    start = datetime.strptime(start_date, "%Y%m%d").date()
    end = datetime.strptime(end_date, "%Y%m%d").date()
    if start > end:
        raise ValueError("start_date must be earlier than or equal to end_date.")

    chunks = []
    cursor = start
    while cursor <= end:
        chunk_end = min(cursor + timedelta(days=chunk_days - 1), end)
        chunks.append((cursor.strftime("%Y%m%d"), chunk_end.strftime("%Y%m%d")))
        cursor = chunk_end + timedelta(days=1)
    return chunks


def _load_existing_prices(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=PRICE_COLUMNS)
    return load_prices(str(path))


def _prepare_existing_prices(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=PRICE_COLUMNS)
    prepared = frame.copy()
    prepared["ticker"] = prepared["ticker"].astype("string").str.zfill(6)
    prepared["date"] = pd.to_datetime(prepared["date"])
    return prepared


def _existing_has_chunk(
    frame: pd.DataFrame,
    ticker: str,
    chunk_start: str,
    chunk_end: str,
    *,
    min_rows: int = 20,
) -> bool:
    if frame.empty:
        return False
    start = pd.to_datetime(chunk_start, format="%Y%m%d")
    end = pd.to_datetime(chunk_end, format="%Y%m%d")
    mask = (
        (frame["ticker"].astype("string").str.zfill(6) == ticker)
        & (frame["date"] >= start)
        & (frame["date"] <= end)
    )
    return int(mask.sum()) >= min_rows


def _combine_price_frames(existing: pd.DataFrame, new_data: pd.DataFrame) -> pd.DataFrame:
    result = pd.concat(
        [
            frame
            for frame in [existing, new_data]
            if not frame.empty and not frame.dropna(axis=1, how="all").empty
        ],
        ignore_index=True,
    )
    if result.empty:
        return pd.DataFrame(columns=PRICE_COLUMNS)
    return (
        result.drop_duplicates(["ticker", "date"])
        .sort_values(["ticker", "date"])
        .reset_index(drop=True)
    )


def _to_number(value: object) -> float | None:
    if value is None or value == "":
        return None
    return pd.to_numeric(str(value).replace(",", ""), errors="coerce")
