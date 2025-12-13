from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from . import config, data_prep


def cmd_prepare_data(args: argparse.Namespace) -> None:
    df = data_prep.load_processed()
    print(f"Prepared processed dataset with {len(df)} rows.")
    print("Columns:")
    print(", ".join(df.columns))


def _select_row(df, index: Optional[int], title: Optional[str]):
    if title:
        # substring match (case-insensitive), take first match
        mask = df[config.COL_JOB_TITLE].str.contains(title, case=False, na=False)
        if not mask.any():
            raise ValueError(f"No job title matched: {title}")
        return df[mask].iloc[0]

    if index is None:
        raise ValueError("Provide --index or --title")
    if index < 0 or index >= len(df):
        raise IndexError(f"Index out of range: {index}")
    return df.iloc[index]


def cmd_show_job(args: argparse.Namespace) -> None:
    df = data_prep.load_processed()
    row = _select_row(df, args.index, args.title)

    print("Job:")
    for c in [config.COL_JOB_TITLE, config.COL_RISK_CATEGORY, config.COL_EDU_LEVEL]:
        if c in row.index:
            print(f"- {c}: {row[c]}")

    print("\nCore signals:")
    for c in [config.COL_AI_EXPOSURE, config.COL_AUTOMATION_PROB, config.COL_TECH_GROWTH, config.COL_AVG_SALARY]:
        if c in row.index:
            print(f"- {c}: {row[c]}")

    print("\nForces:")
    for c in [
        config.COL_FORCE_AUTOMATION,
        config.COL_FORCE_ADAPTABILITY,
        config.COL_FORCE_TRANSFERABILITY,
        config.COL_FORCE_DEMAND,
        config.COL_FORCE_AUGMENTATION,
    ]:
        if c in row.index:
            print(f"- {c}: {row[c]:+.3f}")

    print("\nEquilibrium:")
    for c in [config.COL_EQ_SHIFT, config.COL_EQ_CENTER, config.COL_EQ_LOWER, config.COL_EQ_UPPER, config.COL_TENSION]:
        if c in row.index:
            print(f"- {c}: {row[c]:.4f}")


def cmd_export_snapshot(args: argparse.Namespace) -> None:
    df = data_prep.load_processed()
    out_path: Path = args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"Saved snapshot to: {out_path}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Workforce Disruption Equilibrium Engine CLI")
    sp = p.add_subparsers(dest="command", required=True)

    p1 = sp.add_parser("prepare-data", help="Prepare processed parquet with forces & equilibrium.")
    p1.set_defaults(func=cmd_prepare_data)

    p2 = sp.add_parser("show-job", help="Show equilibrium details for one job.")
    p2.add_argument("--index", type=int, default=None, help="Row index in processed dataset")
    p2.add_argument("--title", type=str, default=None, help="Substring match for Job_Title")
    p2.set_defaults(func=cmd_show_job)

    p3 = sp.add_parser("export-snapshot", help="Export full dataset with forces & equilibrium to CSV.")
    p3.add_argument("--out", type=Path, default=config.REPORTS_METRICS_DIR / "workforce_equilibrium_snapshot.csv")
    p3.set_defaults(func=cmd_export_snapshot)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
