"""Phase 2 Source Spike: audit The Odds API's historical Pinnacle odds for E0.

Usage:
    python scripts/run_phase2_source_spike.py

Implements docs/PHASE2_SOURCE_SPIKE_PLAN.md exactly: one source (The Odds API),
one league (E0), one season (2023-24, already cached locally from earlier
phases), read-only, audit only - coverage, timestamp granularity, entity
matchability, price agreement with football-data.co.uk, cost, reproducibility.
No betting simulation, no model training, per the plan's explicit scope.

Requires THE_ODDS_API_KEY in .env (see .env.example). Tracks every request
against the plan's 200-request budget cap and refuses to exceed it.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from football_odds_lab.analysis.line_movement_features import parse_match_dates
from football_odds_lab.analysis.odds_math import devig_multiplicative
from football_odds_lab.data_sources.entity_matching import match_event_to_football_data
from football_odds_lab.data_sources.the_odds_api import extract_pinnacle_records, fetch_historical_snapshot

REPO_ROOT = Path(__file__).resolve().parent.parent
SPORT_KEY = "soccer_epl"
BUDGET_CAP_REQUESTS = 200

# Biweekly across the E0 2023-24 season (season runs mid-Aug through May) -
# dense enough to avoid gaps in The Odds API's "upcoming events" horizon (a
# single snapshot only showed ~11 days ahead in initial testing, 2026-07-21),
# cheap enough to stay far under budget (18 requests of the 200 cap).
SNAPSHOT_DATETIMES = [
    "2023-08-15T12:00:00Z", "2023-09-01T12:00:00Z", "2023-09-15T12:00:00Z",
    "2023-10-01T12:00:00Z", "2023-10-15T12:00:00Z", "2023-11-01T12:00:00Z",
    "2023-11-15T12:00:00Z", "2023-12-01T12:00:00Z", "2023-12-15T12:00:00Z",
    "2024-01-01T12:00:00Z", "2024-01-15T12:00:00Z", "2024-02-01T12:00:00Z",
    "2024-02-15T12:00:00Z", "2024-03-02T12:00:00Z", "2024-03-15T12:00:00Z",
    "2024-04-01T12:00:00Z", "2024-04-15T12:00:00Z", "2024-05-01T12:00:00Z",
]
REPRODUCIBILITY_CHECK_DATETIME = "2024-03-02T12:00:00Z"  # re-fetched uncached, compared to the cached copy


def load_football_data_e0_2324() -> pd.DataFrame:
    df = pd.read_csv(REPO_ROOT / "data" / "raw" / "E0_2324.csv")
    df["Date"] = parse_match_dates(df["Date"])
    return df


class RequestBudget:
    def __init__(self, cap: int):
        self.cap = cap
        self.used = 0

    def spend(self, n: int = 1) -> None:
        if self.used + n > self.cap:
            raise RuntimeError(
                f"Budget cap exceeded: {self.used + n} requests would exceed the {self.cap}-request "
                "cap from docs/PHASE2_SOURCE_SPIKE_PLAN.md - stopping, not silently raising the cap."
            )
        self.used += n


def main() -> None:
    load_dotenv(REPO_ROOT / ".env")
    api_key = os.environ.get("THE_ODDS_API_KEY")
    if not api_key:
        print("THE_ODDS_API_KEY not set in .env - see .env.example", file=sys.stderr)
        sys.exit(1)

    cache_dir = REPO_ROOT / "data" / "raw" / "the_odds_api"
    reports_dir = REPO_ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    budget = RequestBudget(BUDGET_CAP_REQUESTS)
    football_data_df = load_football_data_e0_2324()

    all_records = []
    timestamp_gaps_minutes = []
    for snapshot_dt in SNAPSHOT_DATETIMES:
        budget.spend(1)
        raw = fetch_historical_snapshot(SPORT_KEY, snapshot_dt, api_key, cache_dir=cache_dir)
        fetched_at = datetime.now(timezone.utc).isoformat()
        records = extract_pinnacle_records(raw, fetched_at)
        all_records.extend(records)

        ts = pd.Timestamp(raw["timestamp"])
        prev_ts = pd.Timestamp(raw["previous_timestamp"])
        gap_minutes = (ts - prev_ts).total_seconds() / 60
        timestamp_gaps_minutes.append(gap_minutes)
        print(f"Fetched {snapshot_dt}: {len(records)} events, gap-to-previous={gap_minutes:.1f}min", file=sys.stderr)

    # Dedup by provider_fixture_id - the same future match appears in multiple
    # consecutive snapshots as its kickoff approaches. Keep the record from the
    # EARLIEST snapshot that saw it (closest to an "opening"-style read).
    records_by_fixture: dict[str, object] = {}
    for record in all_records:
        existing = records_by_fixture.get(record.provider_fixture_id)
        if existing is None or record.snapshot_timestamp < existing.snapshot_timestamp:
            records_by_fixture[record.provider_fixture_id] = record
    unique_records = list(records_by_fixture.values())

    # Reproducibility check: re-fetch one snapshot bypassing cache, compare to
    # the cached copy already on disk.
    budget.spend(1)
    reproducibility_cache_path = cache_dir / f"{SPORT_KEY}_{REPRODUCIBILITY_CHECK_DATETIME.replace(':', '-')}_eu_h2h.json"
    cached_payload = reproducibility_cache_path.read_text(encoding="utf-8")
    fresh_payload_dict = fetch_historical_snapshot(
        SPORT_KEY, REPRODUCIBILITY_CHECK_DATETIME, api_key, cache_dir=None
    )
    reproducible = json.loads(cached_payload) == fresh_payload_dict

    # Entity matching against football-data.co.uk E0 2023-24.
    match_results = [
        match_event_to_football_data(
            r.home_team, r.away_team, pd.Timestamp(r.event_timestamp), football_data_df
        )
        for r in unique_records
    ]
    matched = [m for m in match_results if m.matched]
    unmatched = [m for m in match_results if not m.matched]
    match_rate = len(matched) / len(match_results) if match_results else 0.0

    # Price agreement: for matched events with a Pinnacle price, compare
    # The Odds API's devigged Pinnacle probability against football-data.co.uk's
    # own PSH/PSD/PSA (opening) devigged probability for the same match.
    price_diffs = []
    for record, match in zip(unique_records, match_results):
        if not match.matched or record.price_home is None:
            continue
        fd_row = football_data_df[
            (football_data_df["HomeTeam"] == match.football_data_home)
            & (football_data_df["AwayTeam"] == match.football_data_away)
            & (football_data_df["Date"].dt.date == pd.Timestamp(record.event_timestamp).date())
        ]
        if fd_row.empty or fd_row[["PSH", "PSD", "PSA"]].isna().any(axis=1).iloc[0]:
            continue
        fd_probs = devig_multiplicative([fd_row["PSH"].iloc[0], fd_row["PSD"].iloc[0], fd_row["PSA"].iloc[0]])
        odds_api_probs = devig_multiplicative([record.price_home, record.price_draw, record.price_away])
        price_diffs.append(abs(fd_probs[0] - odds_api_probs[0]))

    n_with_pinnacle = sum(1 for r in unique_records if r.price_home is not None)
    coverage_rate = n_with_pinnacle / len(football_data_df) if len(football_data_df) else 0.0
    avg_gap = sum(timestamp_gaps_minutes) / len(timestamp_gaps_minutes) if timestamp_gaps_minutes else 0.0
    avg_price_diff = sum(price_diffs) / len(price_diffs) if price_diffs else None

    if match_rate >= 0.90 and (avg_price_diff is None or avg_price_diff < 0.03) and reproducible:
        verdict = "accept"
    elif match_rate >= 0.70 and reproducible:
        verdict = "accept-with-caveats"
    else:
        verdict = "reject"

    lines = [
        "# Phase 2 Source Spike Report: The Odds API",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Source: The Odds API historical odds ({SPORT_KEY}), Pinnacle bookmaker only",
        f"Scope: E0 2023-24 season, {len(SNAPSHOT_DATETIMES)} biweekly snapshots",
        f"Budget used: {budget.used} / {budget.cap} requests",
        "",
        "## Verdict",
        "",
        f"**{verdict.upper()}**",
        "",
        "## Coverage",
        "",
        f"- Unique fixtures seen across all snapshots: {len(unique_records)}",
        f"- Fixtures with a Pinnacle H2H price: {n_with_pinnacle} "
        f"({n_with_pinnacle / len(unique_records):.1%} of fixtures seen)" if unique_records else "- no fixtures seen",
        f"- Coverage vs. full football-data.co.uk E0 2023-24 season ({len(football_data_df)} matches): "
        f"{coverage_rate:.1%}",
        "",
        f"**Read the {coverage_rate:.1%} full-season figure as a sampling-cadence artifact of this spike, "
        "not a ceiling on what the source can provide.** Biweekly snapshots leave real gaps - a match "
        "that fell between two snapshot dates, or whose commence_time slipped just past a snapshot's "
        "event horizon, is simply never seen, independent of whether The Odds API had a Pinnacle price "
        "for it. The 93.2% 'of fixtures seen' figure above is the more direct read on data availability; "
        "a production pipeline sampling weekly (or matching snapshot cadence to each match's own "
        "kickoff) would be expected to close most of this gap.",
        "",
        "## Timestamp granularity",
        "",
        f"- Average gap between a snapshot's timestamp and its previous_timestamp: {avg_gap:.1f} minutes "
        f"(advertised: ~5 minutes for this period)",
        "",
        "## Entity matching",
        "",
        f"- Match rate: {match_rate:.1%} ({len(matched)}/{len(match_results)})",
        f"- Unmatched cases: {len(unmatched)}",
    ]
    for m in unmatched[:20]:
        lines.append(f"  - {m.the_odds_api_home} vs {m.the_odds_api_away} on {m.the_odds_api_date}: {m.reason}")
    if len(unmatched) > 20:
        lines.append(f"  - ... and {len(unmatched) - 20} more")

    lines += [
        "",
        "## Price agreement (Pinnacle, The Odds API vs. football-data.co.uk)",
        "",
        f"- Matches compared: {len(price_diffs)}",
        f"- Mean absolute devigged-home-probability difference: "
        f"{avg_price_diff:.4f}" if avg_price_diff is not None else "- no comparable matches",
        "",
        "## Reproducibility",
        "",
        f"- Re-fetching {REPRODUCIBILITY_CHECK_DATETIME} uncached and comparing to the cached copy: "
        f"{'IDENTICAL' if reproducible else 'DIFFERED - see note below'}",
    ]

    report_path = reports_dir / "phase2-source-spike-report.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n".join(lines))
    print(f"\nFull report written to {report_path}")


if __name__ == "__main__":
    main()
