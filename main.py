"""Command line entry point for the KOSPI200 factor model project."""

from __future__ import annotations

import argparse

from src.backtest.engine import run_backtest
from src.data.kis_client import KISClient, KISConfig
from src.data.price_loader import (
    combine_yearly_price_files,
    fetch_long_horizon_prices_from_kis,
    fetch_prices_from_kis,
    load_tickers_from_csv,
)
from src.data.ts2000_loader import standardize_ts2000_excel
from src.data.ts2000_wide_loader import prepare_long_horizon_fundamentals
from src.data.universe import fetch_kospi200_constituents_from_wikipedia
from src.data.validator import write_data_validation_outputs
from src.data.dart_batch import fetch_top30_dart_data
from src.data.dart_text_kpi import build_dart_text_kpis
from src.data.sector_master import build_sector_master
from src.factors.integrated import build_integrated_factor_scores
from src.factors.pipeline import build_fundamental_factor_scores, build_price_factor_scores
from src.portfolio.construction import build_kospi200_model_portfolio_preview
from src.report.client_strategy_report import generate_client_strategy_report
from src.report.interview_manual import generate_interview_manual
from src.report.report_generator import generate_initial_report
from src.report.research_paper import generate_research_paper
from src.report.sector_report_model import generate_sector_reports
from src.research.factor_report import build_factor_validation_report
from src.research.recruiting_assignment_pack import run_recruiting_assignment_pack
from src.ml.return_model import run_ml_return_experiment
from src.strategy.regime import build_regime_aware_factor_scores
from src.strategy.institutional_strategy import run_institutional_strategy
from src.strategy.strategy_lab import run_strategy_lab
from src.trading.kis_paper_trading import run_kis_paper_trading


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="KOSPI200 Fundamental Factor Model Portfolio"
    )
    parser.add_argument(
        "--step",
        default="validate-data",
        choices=[
            "validate-data",
            "fetch-prices",
            "fetch-long-prices",
            "combine-yearly-prices",
            "fetch-top30-dart",
            "extract-dart-kpis",
            "fetch-universe",
            "build-sector-master",
            "prepare-fundamentals",
            "prepare-long-fundamentals",
            "build-factors",
            "build-integrated-factors",
            "build-regime-strategy",
            "run-institutional-strategy",
            "run-strategy-lab",
            "run-ml-experiment",
            "run-ml-801010",
            "run-recruiting-assignment-pack",
            "validate-factors",
            "build-recommendations",
            "construct-portfolio",
            "run-backtest",
            "generate-report",
            "generate-client-report",
            "generate-research-paper",
            "generate-manual",
            "generate-sector-reports",
            "run-paper-trading",
        ],
        help="Pipeline step to run. Only placeholders exist in the initial scaffold.",
    )
    parser.add_argument(
        "--tickers",
        nargs="*",
        default=None,
        help="Tickers to fetch for --step fetch-prices, e.g. 005930 000660.",
    )
    parser.add_argument(
        "--tickers-file",
        default=None,
        help="CSV file with ticker column for --step fetch-prices.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit tickers loaded from --tickers-file.",
    )
    parser.add_argument("--start", default=None, help="Start date as YYYYMMDD.")
    parser.add_argument("--end", default=None, help="End date as YYYYMMDD.")
    parser.add_argument(
        "--start-year",
        type=int,
        default=None,
        help="Start year for --step fetch-long-prices or combine-yearly-prices.",
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=None,
        help="End year for --step fetch-long-prices or combine-yearly-prices.",
    )
    parser.add_argument(
        "--output",
        default="data/raw/price/prices.csv",
        help="Output CSV path for fetched price data.",
    )
    parser.add_argument(
        "--yearly-output-dir",
        default="data/raw/price/yearly",
        help="Directory for yearly price CSVs used by long-horizon price steps.",
    )
    parser.add_argument(
        "--price-path",
        default="data/raw/price/prices.csv",
        help="Input price CSV path for --step validate-data.",
    )
    parser.add_argument(
        "--fundamentals-source",
        default="/Users/leesangeui/Downloads/kospi재무정보.xlsx",
        help="Raw TS2000 Excel file for --step prepare-fundamentals.",
    )
    parser.add_argument(
        "--fundamentals-sources",
        nargs="*",
        default=None,
        help="Raw long-horizon TS2000 Excel files for --step prepare-long-fundamentals.",
    )
    parser.add_argument(
        "--fundamentals-output",
        default="data/raw/ts2000/fundamentals.csv",
        help="Output CSV path for standardized fundamentals.",
    )
    parser.add_argument(
        "--fundamentals-path",
        default="data/raw/ts2000/fundamentals.csv",
        help="Input fundamentals CSV path for --step validate-data.",
    )
    parser.add_argument(
        "--factor-output",
        default="data/features/factor_scores.csv",
        help="Output factor score CSV path for --step build-factors.",
    )
    parser.add_argument(
        "--universe-output",
        default="data/raw/benchmark/kospi200_constituents.csv",
        help="Output universe CSV path for --step fetch-universe.",
    )
    parser.add_argument(
        "--universe-path",
        default="data/raw/benchmark/kospi200_constituents.csv",
        help="Input universe CSV path for --step construct-portfolio.",
    )
    parser.add_argument(
        "--price-factor-output",
        default="data/features/price_factor_scores.csv",
        help="Output price factor score CSV path for --step build-factors.",
    )
    parser.add_argument(
        "--integrated-factor-output",
        default="data/features/integrated_factor_scores.csv",
        help="Output integrated factor score CSV path for --step build-integrated-factors.",
    )
    parser.add_argument(
        "--backtest-factor-path",
        default="data/features/price_factor_scores.csv",
        help="Factor score CSV path for --step run-backtest.",
    )
    parser.add_argument(
        "--backtest-output-dir",
        default="outputs/backtest",
        help="Output directory for --step run-backtest.",
    )
    parser.add_argument(
        "--ml-target-output",
        default="data/features/ml_forward_return_dataset.csv",
        help="Output target dataset path for --step run-ml-experiment.",
    )
    parser.add_argument(
        "--ml-prediction-output",
        default="outputs/ml/ml_return_predictions.csv",
        help="Output prediction CSV path for --step run-ml-experiment.",
    )
    parser.add_argument(
        "--ml-factor-output",
        default="data/features/ml_predicted_factor_scores_2007_2026.csv",
        help="Output ML predicted factor score path for --step run-ml-experiment.",
    )
    parser.add_argument(
        "--benchmark-path",
        default=None,
        help="Optional benchmark CSV path for --step run-backtest.",
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to .env file containing KIS credentials.",
    )
    parser.add_argument(
        "--request-sleep",
        type=float,
        default=1.0,
        help="Seconds to sleep between KIS API requests.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=5,
        help="Maximum retries per KIS price request.",
    )
    parser.add_argument(
        "--retry-sleep",
        type=float,
        default=5.0,
        help="Base seconds for KIS retry backoff.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip tickers already present in the output price CSV.",
    )
    parser.add_argument(
        "--paper-trading-output-dir",
        default="outputs/paper_trading",
        help="Output directory for --step run-paper-trading.",
    )
    parser.add_argument(
        "--sector-report-output-dir",
        default="outputs/reports/sector_top30",
        help="Output directory for --step generate-sector-reports.",
    )
    parser.add_argument(
        "--sector-report-top-n",
        type=int,
        default=30,
        help="Number of latest quant-ranked names to include in sector reports.",
    )
    parser.add_argument(
        "--sector-master-path",
        default="data/raw/sector/sector_master.csv",
        help="Analyst sector master path for --step generate-sector-reports.",
    )
    parser.add_argument(
        "--dart-output-dir",
        default="data/raw/dart/top30",
        help="Output directory for --step fetch-top30-dart.",
    )
    parser.add_argument(
        "--dart-end-date",
        default="20260707",
        help="End date as YYYYMMDD for --step fetch-top30-dart filing lookup.",
    )
    parser.add_argument(
        "--fetch-dart-documents",
        action="store_true",
        help="Download latest OpenDART report documents for --step extract-dart-kpis.",
    )
    parser.add_argument(
        "--max-dart-documents",
        type=int,
        default=None,
        help="Optional max document count for --step extract-dart-kpis.",
    )
    parser.add_argument(
        "--initial-cash",
        type=float,
        default=100_000_000,
        help="Fallback cash used when KIS paper balance is unavailable.",
    )
    parser.add_argument(
        "--no-kis-quotes",
        action="store_true",
        help="Use latest local prices instead of KIS current quotes for order sizing.",
    )
    parser.add_argument(
        "--no-kis-balance",
        action="store_true",
        help="Use fallback cash instead of KIS paper account balance.",
    )
    parser.add_argument(
        "--submit-paper-orders",
        action="store_true",
        help="Submit generated orders to the configured KIS paper account.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.step == "fetch-prices":
        tickers = args.tickers
        if args.tickers_file:
            tickers = load_tickers_from_csv(args.tickers_file, limit=args.limit)
        if not tickers:
            raise ValueError("--tickers or --tickers-file is required for --step fetch-prices.")
        if not args.start or not args.end:
            raise ValueError("--start and --end are required as YYYYMMDD.")

        config = KISConfig.from_env(args.env_file)
        client = KISClient(config)
        frame = fetch_prices_from_kis(
            client,
            tickers=tickers,
            start_date=args.start,
            end_date=args.end,
            output_path=args.output,
            request_sleep_seconds=args.request_sleep,
            max_retries=args.max_retries,
            retry_sleep_seconds=args.retry_sleep,
            resume=args.resume,
        )
        print(f"Saved {len(frame):,} price rows to {args.output}")
        print(f"Tickers in output: {frame['ticker'].nunique():,}")
        return

    if args.step == "fetch-long-prices":
        if not args.tickers_file:
            raise ValueError("--tickers-file is required for --step fetch-long-prices.")
        if args.start_year is None or args.end_year is None:
            raise ValueError("--start-year and --end-year are required.")
        tickers = load_tickers_from_csv(args.tickers_file, limit=args.limit)
        if not tickers:
            raise ValueError("--tickers-file did not provide any ticker.")

        config = KISConfig.from_env(args.env_file)
        client = KISClient(config)
        frame = fetch_long_horizon_prices_from_kis(
            client,
            tickers=tickers,
            start_year=args.start_year,
            end_year=args.end_year,
            yearly_output_dir=args.yearly_output_dir,
            combined_output_path=args.output,
            final_end_date=args.end,
            request_sleep_seconds=args.request_sleep,
            max_retries=args.max_retries,
            retry_sleep_seconds=args.retry_sleep,
            resume=args.resume,
        )
        print(f"Saved combined long-horizon prices to {args.output}")
        print(
            f"Rows: {len(frame):,}, tickers: {frame['ticker'].nunique():,}, "
            f"date range: {frame['date'].min().date()} to {frame['date'].max().date()}"
        )
        print("Saved outputs/tables/long_price_fetch_summary.csv")
        return

    if args.step == "combine-yearly-prices":
        frame = combine_yearly_price_files(
            args.yearly_output_dir,
            output_path=args.output,
            start_year=args.start_year,
            end_year=args.end_year,
        )
        print(f"Saved combined yearly prices to {args.output}")
        print(
            f"Rows: {len(frame):,}, tickers: {frame['ticker'].nunique():,}, "
            f"date range: {frame['date'].min().date()} to {frame['date'].max().date()}"
        )
        print("Saved outputs/tables/long_price_yearly_coverage.csv")
        return

    if args.step == "fetch-universe":
        frame = fetch_kospi200_constituents_from_wikipedia(
            output_path=args.universe_output,
        )
        print(f"Saved {len(frame):,} KOSPI200 constituents to {args.universe_output}")
        print(
            f"Source: Wikipedia current components fallback. "
            f"Effective date: {frame['effective_date'].iloc[0]}"
        )
        return

    if args.step == "fetch-top30-dart":
        result = fetch_top30_dart_data(
            score_path="data/features/institutional_core_satellite_scores.csv",
            output_dir=args.dart_output_dir,
            env_file=args.env_file,
            top_n=args.sector_report_top_n,
            end_date=args.dart_end_date,
        )
        print(f"Saved {result.company_profiles_path}")
        print(f"Saved {result.filings_path}")
        print(f"Saved {result.single_accounts_path}")
        print(f"Saved {result.fetch_summary_path}")
        return

    if args.step == "extract-dart-kpis":
        result = build_dart_text_kpis(
            filings_path=f"{args.dart_output_dir}/filings.csv",
            output_dir=args.dart_output_dir,
            env_file=args.env_file,
            fetch_documents=args.fetch_dart_documents,
            max_documents=args.max_dart_documents,
        )
        print(f"Saved {result.kpi_path}")
        print(f"Saved {result.snippet_path}")
        print(f"Documents: {result.document_dir}")
        return

    if args.step == "build-sector-master":
        sector_fundamentals_path = (
            "data/raw/ts2000/fundamentals_long.csv"
            if args.fundamentals_path == "data/raw/ts2000/fundamentals.csv"
            else args.fundamentals_path
        )
        result = build_sector_master(
            universe_path=args.universe_path,
            dart_company_path=f"{args.dart_output_dir}/company_profiles.csv",
            fundamentals_path=sector_fundamentals_path,
        )
        print(f"Saved {result.output_path}")
        print(f"Saved {result.coverage_path}")
        return

    if args.step == "prepare-fundamentals":
        frame = standardize_ts2000_excel(
            args.fundamentals_source,
            output_path=args.fundamentals_output,
        )
        print(
            f"Saved {len(frame):,} standardized fundamentals rows "
            f"to {args.fundamentals_output}"
        )
        print(
            f"Coverage: {frame['ticker'].nunique():,} ticker(s), "
            f"{frame['fiscal_period'].min()} to {frame['fiscal_period'].max()}"
        )
        return

    if args.step == "prepare-long-fundamentals":
        frame = prepare_long_horizon_fundamentals(
            args.fundamentals_sources,
            output_path=args.fundamentals_output,
        )
        print(
            f"Saved {len(frame):,} long-horizon fundamentals rows "
            f"to {args.fundamentals_output}"
        )
        print(
            f"Coverage: {frame['ticker'].nunique():,} ticker(s), "
            f"{frame['fiscal_period'].min()} to {frame['fiscal_period'].max()}"
        )
        print("Saved outputs/tables/ts2000_wide_column_dictionary.csv")
        print("Saved outputs/tables/research_split_summary.csv")
        return

    if args.step == "validate-data":
        price_result, fundamentals_result = write_data_validation_outputs(
            args.price_path,
            args.fundamentals_path,
        )
        issue_count = len(price_result.issues) + len(fundamentals_result.issues)
        print(
            "Validated data: "
            f"{len(price_result.summary):,} price ticker summary row(s), "
            f"{len(fundamentals_result.summary):,} fundamentals summary row(s), "
            f"{issue_count:,} issue(s)."
        )
        print("Saved outputs/tables/price_data_summary.csv")
        print("Saved outputs/tables/price_data_issues.csv")
        print("Saved outputs/tables/fundamentals_data_summary.csv")
        print("Saved outputs/tables/fundamentals_yearly_coverage.csv")
        print("Saved outputs/tables/fundamentals_data_issues.csv")
        print("Saved outputs/reports/data_validation_report.md")
        return

    if args.step == "build-factors":
        frame = build_fundamental_factor_scores(
            args.fundamentals_path,
            output_path=args.factor_output,
        )
        print(f"Saved {len(frame):,} factor score rows to {args.factor_output}")
        print(
            f"Coverage: {frame['ticker'].nunique():,} ticker(s), "
            f"{frame['available_date'].min().date()} to {frame['available_date'].max().date()}"
        )
        price_frame = build_price_factor_scores(
            args.price_path,
            output_path=args.price_factor_output,
        )
        print(f"Saved {len(price_frame):,} price factor score rows to {args.price_factor_output}")
        print(
            f"Price factor coverage: {price_frame['ticker'].nunique():,} ticker(s), "
            f"{price_frame['signal_date'].min().date()} to {price_frame['signal_date'].max().date()}"
        )
        return

    if args.step == "build-integrated-factors":
        frame = build_integrated_factor_scores(
            fundamental_factor_path=args.factor_output,
            price_factor_path=args.price_factor_output,
            output_path=args.integrated_factor_output,
        )
        print(
            f"Saved {len(frame):,} integrated factor score rows "
            f"to {args.integrated_factor_output}"
        )
        print(
            f"Integrated factor coverage: {frame['ticker'].nunique():,} ticker(s), "
            f"{frame['signal_date'].min().date()} to {frame['signal_date'].max().date()}"
        )
        return

    if args.step == "build-regime-strategy":
        frame = build_regime_aware_factor_scores(
            factor_scores_path=args.integrated_factor_output,
            benchmark_path=args.benchmark_path or "data/raw/benchmark/kodex200_prices.csv",
        )
        print(
            f"Saved {len(frame):,} regime-aware factor score rows "
            "to data/features/regime_aware_factor_scores.csv"
        )
        print("Saved outputs/tables/market_regime_by_signal_date.csv")
        print(
            "Regime counts: "
            + ", ".join(
                f"{regime}={count}"
                for regime, count in frame[["signal_date", "regime"]]
                .drop_duplicates()["regime"]
                .value_counts()
                .items()
            )
        )
        return

    if args.step == "run-strategy-lab":
        result = run_strategy_lab(
            price_path=args.price_path,
            factor_scores_path=args.integrated_factor_output,
            ml_factor_scores_path=args.ml_factor_output,
        )
        summary = result["summary"]
        print("Saved data/features/strategy_lab/*.csv")
        print("Saved outputs/strategy_lab/backtests/*")
        print("Saved outputs/tables/strategy_lab_definitions.csv")
        print("Saved outputs/tables/strategy_lab_summary.csv")
        print("Saved outputs/tables/strategy_lab_split_summary.csv")
        print("Saved outputs/reports/Strategy_Lab_Practical_Strategy_Test.md")
        print(summary[["strategy_name", "cagr", "sharpe", "max_drawdown", "information_ratio"]].head(10).to_string(index=False))
        return

    if args.step == "run-institutional-strategy":
        result = run_institutional_strategy(
            price_path=args.price_path,
            factor_scores_path=args.integrated_factor_output,
            ml_factor_scores_path=args.ml_factor_output,
        )
        summary = result["summary"].iloc[0]
        print("Saved data/features/institutional_core_satellite_scores.csv")
        print("Saved outputs/tables/institutional_market_regime.csv")
        print("Saved outputs/backtest_institutional_core_satellite/*")
        print("Saved outputs/tables/institutional_strategy_split_summary.csv")
        print("Saved outputs/reports/Institutional_Core_Satellite_Strategy.md")
        print(
            "Institutional strategy summary: "
            f"total_return={summary['total_return']:.2%}, "
            f"CAGR={summary['cagr']:.2%}, "
            f"vol={summary['annualized_volatility']:.2%}, "
            f"Sharpe={summary['sharpe']:.2f}, "
            f"MDD={summary['max_drawdown']:.2%}, "
            f"IR={summary['information_ratio']:.2f}"
        )
        return

    if args.step == "run-ml-experiment":
        result = run_ml_return_experiment(
            factor_scores_path=args.integrated_factor_output,
            price_path=args.price_path,
            target_output_path=args.ml_target_output,
            prediction_output_path=args.ml_prediction_output,
            selected_factor_output_path=args.ml_factor_output,
        )
        metrics = result["metrics"]
        selected_model_name = result["selected_model_name"]
        print("Saved data/features/ml_forward_return_dataset.csv")
        print("Saved outputs/ml/ml_return_predictions.csv")
        print("Saved data/features/ml_predicted_factor_scores_2007_2026.csv")
        print("Saved outputs/tables/ml_model_metrics.csv")
        print("Saved outputs/tables/ml_dataset_split_summary.csv")
        print("Saved outputs/reports/ML_Return_Prediction_Experiment.md")
        print(f"Selected ML model: {selected_model_name}")
        print(metrics.to_string(index=False))
        return

    if args.step == "run-ml-801010":
        result = run_ml_return_experiment(
            factor_scores_path=args.integrated_factor_output,
            price_path=args.price_path,
            target_output_path="data/features/ml_forward_return_dataset_801010.csv",
            prediction_output_path="outputs/ml/ml_return_predictions_801010.csv",
            selected_factor_output_path="data/features/ml_predicted_factor_scores_801010.csv",
            metrics_output_path="outputs/tables/ml_model_metrics_801010.csv",
            split_summary_output_path="outputs/tables/ml_dataset_split_summary_801010.csv",
            report_output_path="outputs/reports/ML_Return_Prediction_Experiment_801010.md",
            split_scheme="chronological_801010",
        )
        metrics = result["metrics"]
        selected_model_name = result["selected_model_name"]
        print("Saved data/features/ml_forward_return_dataset_801010.csv")
        print("Saved outputs/ml/ml_return_predictions_801010.csv")
        print("Saved data/features/ml_predicted_factor_scores_801010.csv")
        print("Saved outputs/tables/ml_model_metrics_801010.csv")
        print("Saved outputs/tables/ml_dataset_split_summary_801010.csv")
        print("Saved outputs/reports/ML_Return_Prediction_Experiment_801010.md")
        print(f"Selected ML model: {selected_model_name}")
        print(metrics.to_string(index=False))
        return

    if args.step == "run-recruiting-assignment-pack":
        result = run_recruiting_assignment_pack(
            price_path=args.price_path,
            factor_scores_path=args.integrated_factor_output,
        )
        print("Saved outputs/tables/recruiting_assignment_pack/*.csv")
        print("Saved outputs/reports/Quant_Research_Recruiting_Assignment_Pack.md")
        print(
            "Generated assignment modules: "
            + ", ".join(key for key in result if key != "skill_map")
        )
        return

    if args.step in {"validate-factors", "build-recommendations"}:
        result = build_factor_validation_report(
            factor_scores_path=args.integrated_factor_output,
            price_path=args.price_path,
        )
        print("Saved data/features/factor_forward_returns.csv")
        print("Saved outputs/tables/rank_ic_by_month.csv")
        print("Saved outputs/tables/rank_ic_summary.csv")
        print("Saved outputs/tables/quintile_returns_by_month.csv")
        print("Saved outputs/tables/quintile_return_summary.csv")
        print("Saved outputs/portfolios/latest_recommendation_candidates.csv")
        print("Saved outputs/reports/factor_validation_summary.md")
        print(
            "Validation summary: "
            f"targets={len(result['targets']):,}, "
            f"candidates={len(result['candidates']):,}"
        )
        return

    if args.step == "construct-portfolio":
        portfolio = build_kospi200_model_portfolio_preview(
            factor_scores_path=args.factor_output,
            universe_path=args.universe_path,
        )
        print(
            "Saved KOSPI200 portfolio preview to "
            "outputs/portfolios/kospi200_model_portfolio_preview.csv"
        )
        print(
            f"Rows: {len(portfolio):,}, tickers: {portfolio['ticker'].nunique():,}, "
            f"signal date: {portfolio['available_date'].max().date()}"
        )
        return

    if args.step == "run-backtest":
        result = run_backtest(
            price_path=args.price_path,
            factor_scores_path=args.backtest_factor_path,
            output_dir=args.backtest_output_dir,
            benchmark_path=args.benchmark_path,
        )
        summary = result["summary"].iloc[0]
        print(f"Saved {args.backtest_output_dir}/backtest_daily_returns.csv")
        print(f"Saved {args.backtest_output_dir}/backtest_equity_curve.csv")
        print(f"Saved {args.backtest_output_dir}/backtest_rebalance_log.csv")
        print(f"Saved {args.backtest_output_dir}/backtest_summary.csv")
        print(
            "Backtest summary: "
            f"total_return={summary['total_return']:.2%}, "
            f"CAGR={summary['cagr']:.2%}, "
            f"vol={summary['annualized_volatility']:.2%}, "
            f"Sharpe={summary['sharpe']:.2f}, "
            f"MDD={summary['max_drawdown']:.2%}"
        )
        return

    if args.step == "generate-report":
        markdown_path, pdf_path = generate_initial_report()
        print(f"Saved {markdown_path}")
        print(f"Saved {pdf_path}")
        return

    if args.step == "generate-client-report":
        markdown_path, pdf_path = generate_client_strategy_report()
        print(f"Saved {markdown_path}")
        print(f"Saved {pdf_path}")
        return

    if args.step == "generate-research-paper":
        paper_path = generate_research_paper()
        print(f"Saved {paper_path}")
        return

    if args.step == "generate-manual":
        markdown_path, pdf_path = generate_interview_manual()
        print(f"Saved {markdown_path}")
        print(f"Saved {pdf_path}")
        return

    if args.step == "generate-sector-reports":
        sector_fundamentals_path = (
            "data/raw/ts2000/fundamentals_long.csv"
            if args.fundamentals_path == "data/raw/ts2000/fundamentals.csv"
            else args.fundamentals_path
        )
        sector_price_path = (
            "data/raw/price/prices_2007_2026.csv"
            if args.price_path == "data/raw/price/prices.csv"
            else args.price_path
        )
        result = generate_sector_reports(
            score_path="data/features/institutional_core_satellite_scores.csv",
            fundamentals_path=sector_fundamentals_path,
            price_path=sector_price_path,
            universe_path=args.universe_path,
            sector_master_path=args.sector_master_path,
            dart_company_path=f"{args.dart_output_dir}/company_profiles.csv",
            dart_accounts_path=f"{args.dart_output_dir}/single_accounts.csv",
            dart_text_kpi_path=f"{args.dart_output_dir}/dart_text_kpis.csv",
            output_dir=args.sector_report_output_dir,
            top_n=args.sector_report_top_n,
        )
        print(f"Saved {result.top30_csv}")
        print(f"Saved {result.sector_summary_csv}")
        print(f"Saved {result.index_markdown}")
        print(f"Generated {len(result.pdf_paths):,} sector PDF report(s)")
        for path in result.pdf_paths:
            print(f"Saved {path}")
        return

    if args.step == "run-paper-trading":
        result = run_kis_paper_trading(
            score_path=args.integrated_factor_output
            if args.integrated_factor_output.endswith("institutional_core_satellite_scores.csv")
            else "data/features/institutional_core_satellite_scores.csv",
            price_path=args.price_path,
            env_file=args.env_file,
            output_dir=args.paper_trading_output_dir,
            initial_cash=args.initial_cash,
            use_kis_quotes=not args.no_kis_quotes,
            use_kis_balance=not args.no_kis_balance,
            submit_orders=args.submit_paper_orders,
            request_sleep_seconds=args.request_sleep,
        )
        print(f"Saved {args.paper_trading_output_dir}/latest_target_portfolio.csv")
        print(f"Saved {args.paper_trading_output_dir}/latest_order_plan.csv")
        print(f"Saved {args.paper_trading_output_dir}/latest_account_snapshot.csv")
        print(f"Saved {result.report_path}")
        print(
            "Paper trading dry-run: "
            f"targets={len(result.target_portfolio):,}, orders={len(result.order_plan):,}"
        )
        return

    raise NotImplementedError(
        f"Pipeline step '{args.step}' is a placeholder. "
        "Implement data loaders and schema validation before running results."
    )


if __name__ == "__main__":
    main()
