"""Phase 2 EV Decision Snapshot Fetcher - ingestion only, no EV/ROI/hit-rate.

Usage:
    python scripts/run_phase2_decision_snapshot_fetch.py            # dry run only
    python scripts/run_phase2_decision_snapshot_fetch.py --execute  # real fetch

Implements docs/PHASE2_EV_METHODOLOGY.md's decision-snapshot scope exactly:
E0 2023-24, decision timestamps T-24h/T-12h/T-6h/T-1h relative to each match's
own (BST-corrected) kickoff, market=h2h, region=eu, every bookmaker present
(not just Pinnacle - which named bookmaker or Avg to use as "the" EV candidate
is an economics decision, deliberately deferred to the separate EV Backtest
Runner PR). Nearest-snapshot-at-or-before rule enforced in code (leakage
guard), a hard budget cap enforced before any real spend, and a coverage
report. Deliberately does NOT compute EV, ROI, hit rate, or anything
profitability-related - see docs/PHASE2_EV_METHODOLOGY.md's "Out of scope"
section; that's the separate EV Backtest Runner PR.
"""

import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from football_odds_lab.analysis.decision_snapshot_extraction import extract_decision_records_for_point
from football_odds_lab.analysis.decision_timestamps import (
    DECISION_OFFSETS_HOURS,
    build_decision_points,
    group_by_unique_timestamp,
)
from football_odds_lab.analysis.line_movement_features import parse_kickoff_datetimes_utc, parse_match_dates
from football_odds_lab.data_sources.the_odds_api import fetch_historical_snapshot

REPO_ROOT = Path(__file__).resolve().parent.parent
SPORT_KEY = "soccer_epl"
CREDITS_PER_REQUEST = 10
HARD_BUDGET_CAP_CREDITS = 15_200  # per docs/PHASE2_EV_METHODOLOGY.md's own estimate ceiling


def load_e0_2324_with_kickoff() -> pd.DataFrame:
    df = pd.read_csv(REPO_ROOT / "data" / "raw" / "E0_2324.csv")
    df["Date"] = parse_match_dates(df["Date"])
    df["Kickoff"] = parse_kickoff_datetimes_utc(df["Date"].dt.strftime("%d/%m/%Y"), df.get("Time"))
    return df


def print_dry_run_summary(groups: dict) -> int:
    estimated_credits = CREDITS_PER_REQUEST * len(groups)
    by_offset: dict[int, set[int]] = defaultdict(set)
    for points in groups.values():
        for p in points:
            by_offset[p.offset_hours].add(p.match_index)

    print("=== DRY RUN (no requests made) ===", file=sys.stderr)
    print(f"Unique decision timestamps to fetch: {len(groups)}", file=sys.stderr)
    print(f"Estimated cost: {estimated_credits} credits ({len(groups)} requests)", file=sys.stderr)
    print(f"Hard budget cap: {HARD_BUDGET_CAP_CREDITS} credits", file=sys.stderr)
    for offset in DECISION_OFFSETS_HOURS:
        print(f"  T-{offset}h: {len(by_offset[offset])} matches planned", file=sys.stderr)
    return estimated_credits


def main() -> None:
    execute = "--execute" in sys.argv

    load_dotenv(REPO_ROOT / ".env")
    football_data_df = load_e0_2324_with_kickoff()

    points = build_decision_points(football_data_df, DECISION_OFFSETS_HOURS)
    groups = group_by_unique_timestamp(points)
    estimated_credits = print_dry_run_summary(groups)

    if estimated_credits > HARD_BUDGET_CAP_CREDITS:
        print(
            f"ABORTING: estimated cost {estimated_credits} exceeds the hard cap "
            f"{HARD_BUDGET_CAP_CREDITS} - reduce scope (fewer offsets, fewer matches) "
            "before proceeding, do not raise this cap without updating "
            "docs/PHASE2_EV_METHODOLOGY.md first.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not execute:
        print("\nDry run only - pass --execute to actually spend the budget above.", file=sys.stderr)
        return

    api_key = os.environ.get("THE_ODDS_API_KEY")
    if not api_key:
        print("THE_ODDS_API_KEY not set in .env - see .env.example", file=sys.stderr)
        sys.exit(1)

    cache_dir = REPO_ROOT / "data" / "raw" / "the_odds_api"
    reports_dir = REPO_ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    all_records = []
    coverage: dict[int, dict[str, int]] = {
        offset: {"covered": 0, "missing": 0, "exactly_at": 0, "strictly_before": 0} for offset in DECISION_OFFSETS_HOURS
    }

    sorted_timestamps = sorted(groups.keys())
    for i, decision_ts in enumerate(sorted_timestamps, start=1):
        snapshot_date_str = decision_ts.isoformat().replace("+00:00", "Z")
        raw = fetch_historical_snapshot(SPORT_KEY, snapshot_date_str, api_key, cache_dir=cache_dir)
        fetched_at = datetime.now(timezone.utc).isoformat()
        snapshot_ts = pd.Timestamp(raw["timestamp"])

        for point in groups[decision_ts]:
            records = extract_decision_records_for_point(
                raw, point.home_team, point.away_team, point.decision_timestamp, point.offset_hours, fetched_at
            )
            if records:
                coverage[point.offset_hours]["covered"] += 1
                if snapshot_ts == point.decision_timestamp:
                    coverage[point.offset_hours]["exactly_at"] += 1
                else:
                    coverage[point.offset_hours]["strictly_before"] += 1
                all_records.extend(records)
            else:
                coverage[point.offset_hours]["missing"] += 1

        if i % 50 == 0 or i == len(sorted_timestamps):
            print(f"Fetched {i}/{len(sorted_timestamps)} unique timestamps...", file=sys.stderr)

    records_df = pd.DataFrame([r.__dict__ for r in all_records])
    records_path = reports_dir / "phase2-decision-snapshots.csv"
    records_df.to_csv(records_path, index=False)

    lines = [
        "# Phase 2 EV Decision Snapshot Fetch Report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Season: E0 2023-24, decision offsets: {DECISION_OFFSETS_HOURS}",
        f"Unique requests made: {len(sorted_timestamps)} ({estimated_credits} credits)",
        f"Total matches in season: {len(football_data_df)}",
        f"Normalized records written: {len(all_records)} rows -> {records_path}",
        "",
        "**No EV, ROI, hit rate, or profitability of any kind computed here** - "
        "this is ingestion and normalization only, per docs/PHASE2_EV_METHODOLOGY.md's "
        "scope. See the separate EV Backtest Runner PR for that.",
        "",
        "## Coverage by decision offset",
        "",
        "| Offset | Covered | Missing | Coverage % | Exactly at decision ts | Strictly before |",
        "|---|---|---|---|---|---|",
    ]
    for offset in DECISION_OFFSETS_HOURS:
        c = coverage[offset]
        total = c["covered"] + c["missing"]
        pct = c["covered"] / total if total else 0.0
        lines.append(
            f"| T-{offset}h | {c['covered']} | {c['missing']} | {pct:.1%} | "
            f"{c['exactly_at']} | {c['strictly_before']} |"
        )

    report_path = reports_dir / "phase2-decision-snapshot-fetch-report.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n".join(lines))
    print(f"\nFull report written to {report_path}")


if __name__ == "__main__":
    main()
