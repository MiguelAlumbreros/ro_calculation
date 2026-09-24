"""Command line entry point: ``python -m ro_calculation q3_26 --asof 2026-07-24``."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from .pipeline import run


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="ro_calculation", description=__doc__)
    parser.add_argument("target_quarter", help="Delivery quarter being remunerated, e.g. q3_26")
    parser.add_argument(
        "--asof",
        type=date.fromisoformat,
        default=date.today(),
        help="Date to stand on (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument("--csv", type=Path, default=None, help="Price CSV (default: data/futures.csv)")
    parser.add_argument("--out-dir", type=Path, default=None, help="Where to write the workbook")
    parser.add_argument(
        "--use-pfc",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Source the floating (still-open) portion of each leg from the hourly PFC "
             "instead of a futures close held flat (default: on; --no-use-pfc to turn off)",
    )
    parser.add_argument(
        "--pfc-csv", type=Path, default=None, help="PFC CSV (default: config.pfc_path()); implies --use-pfc"
    )
    args = parser.parse_args(argv)

    result = run(
        target_quarter=args.target_quarter,
        asof=args.asof,
        csv_path=args.csv,
        out_dir=args.out_dir,
        use_pfc=args.use_pfc or args.pfc_csv is not None,
        pfc_csv_path=args.pfc_csv,
    )
    print(f"Target quarter: {args.target_quarter}")
    print(f"As-of:          {args.asof}")
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
