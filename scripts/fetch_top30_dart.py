"""CLI wrapper for Top-N OpenDART batch collection."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data.dart_batch import fetch_top30_dart_data  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch OpenDART data for latest quant Top-N companies.")
    parser.add_argument("--top-n", type=int, default=30)
    parser.add_argument("--score-path", default="data/features/institutional_core_satellite_scores.csv")
    parser.add_argument("--output-dir", default="data/raw/dart/top30")
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--end-date", default="20260707")
    args = parser.parse_args()

    result = fetch_top30_dart_data(
        score_path=args.score_path,
        output_dir=args.output_dir,
        env_file=args.env_file,
        top_n=args.top_n,
        end_date=args.end_date,
    )
    print(f"Saved {result.company_profiles_path}")
    print(f"Saved {result.filings_path}")
    print(f"Saved {result.single_accounts_path}")
    print(f"Saved {result.fetch_summary_path}")


if __name__ == "__main__":
    main()
