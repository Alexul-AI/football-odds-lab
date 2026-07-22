"""Phase 3 Injury Spike: audit API-Football's injuries data for EPL 2023-24.

Usage:
    python scripts/run_phase3_injury_spike.py

Implements docs/PHASE3_INJURY_SPIKE_PLAN.md exactly: one source
(API-Football, free tier only), one league (EPL), one season (2023-24),
read-only, audit only. Answers the plan's three ordered stop/go questions -
historical coverage, usable publication/update timestamp, entity resolution
- and ends in exactly one of three verdicts: accept-for-retrospective-
backtest / reject-for-backtest-but-viable-for-paper-journal / reject-source.
No betting simulation, no model training, no "useful injury features" - per
the plan's explicit scope.

Requires API_FOOTBALL_KEY in .env (see .env.example). Tracks every request
against the plan's 20-request budget cap and refuses to exceed it.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from football_odds_lab.data_sources.api_football import (
    PREMIER_LEAGUE_ID,
    fetch_fixtures_for_league_season,
    fetch_injuries_for_fixture,
    fetch_injuries_for_league_season,
    fetch_league_seasons,
    find_season_coverage,
    flatten_keys,
    has_api_errors,
)
from football_odds_lab.data_sources.entity_matching import E0_TEAM_NAME_MAP

REPO_ROOT = Path(__file__).resolve().parent.parent
TARGET_SEASON = 2023  # API-Football's season param is the year a season started: 2023-24 -> 2023
BUDGET_CAP_REQUESTS = 20
N_FIXTURE_SAMPLE = 5  # only used if the broad league+season injuries query returns nothing


class RequestBudget:
    def __init__(self, cap: int):
        self.cap = cap
        self.used = 0

    def spend(self, n: int = 1) -> None:
        if self.used + n > self.cap:
            raise RuntimeError(
                f"Budget cap exceeded: {self.used + n} requests would exceed the {self.cap}-request "
                "cap from docs/PHASE3_INJURY_SPIKE_PLAN.md - stopping, not silently raising the cap."
            )
        self.used += n


def _sample_fixture_ids(fixtures_response: dict, n: int) -> list[int]:
    fixtures = fixtures_response.get("response", [])
    if not fixtures:
        return []
    step = max(1, len(fixtures) // n)
    sampled = fixtures[::step][:n]
    return [f["fixture"]["id"] for f in sampled if "fixture" in f and "id" in f["fixture"]]


def main() -> None:
    load_dotenv(REPO_ROOT / ".env")
    api_key = os.environ.get("API_FOOTBALL_KEY")
    if not api_key:
        print("API_FOOTBALL_KEY not set in .env - see .env.example", file=sys.stderr)
        sys.exit(1)

    cache_dir = REPO_ROOT / "data" / "raw" / "api_football"
    reports_dir = REPO_ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    budget = RequestBudget(BUDGET_CAP_REQUESTS)
    section_lines: list[str] = []
    verdict = "reject-source"
    verdict_reason = "Spike did not reach a conclusive state (see sections above for where it stopped)."

    # --- Question 1: historical EPL 2023-24 injuries coverage on the free tier ---
    budget.spend(1)
    leagues_payload = fetch_league_seasons(PREMIER_LEAGUE_ID, api_key, cache_dir=cache_dir)
    print(f"[req {budget.used}] /leagues?id={PREMIER_LEAGUE_ID} -> errors={leagues_payload.get('errors')}", file=sys.stderr)

    if has_api_errors(leagues_payload):
        verdict_reason = f"/leagues call returned API errors: {leagues_payload.get('errors')}"
        section_lines += ["## Question 1: historical coverage", "", f"API error: {leagues_payload.get('errors')}", ""]
    else:
        target_coverage = find_season_coverage(leagues_payload, TARGET_SEASON)
        all_years = sorted(
            {
                s.get("year")
                for entry in leagues_payload.get("response", [])
                for s in entry.get("seasons", [])
                if s.get("year") is not None
            }
        )
        most_recent_year = max(all_years) if all_years else None
        current_coverage = (
            find_season_coverage(leagues_payload, most_recent_year) if most_recent_year is not None else None
        )

        q1_historical_pass = bool(target_coverage and target_coverage.get("injuries"))
        q1_current_pass = bool(current_coverage and current_coverage.get("injuries"))

        section_lines += [
            "## Question 1: is EPL 2023-24 injuries coverage available on the free tier?",
            "",
            f"- All seasons this league is tracked for: {all_years}",
            f"- Season {TARGET_SEASON} present: {target_coverage is not None}",
            f"- `coverage.injuries` for season {TARGET_SEASON}: "
            f"{target_coverage.get('injuries') if target_coverage else 'N/A (season not returned)'}",
            f"- Most recent tracked season: {most_recent_year}",
            f"- `coverage.injuries` for the most recent tracked season: "
            f"{current_coverage.get('injuries') if current_coverage else 'N/A'}",
            "",
        ]

        if not q1_historical_pass:
            if q1_current_pass:
                verdict = "reject-for-backtest-but-viable-for-paper-journal"
                verdict_reason = (
                    f"Season {TARGET_SEASON}'s coverage.injuries is False (or the season isn't tracked "
                    f"at all) on the free tier, but the most recent tracked season ({most_recent_year}) "
                    "has coverage.injuries=True - not usable for a 2023-24 retrospective backtest, but "
                    "looks viable for Phase 4's prospective paper journal (collect going forward)."
                )
            else:
                verdict = "reject-source"
                verdict_reason = (
                    f"Neither season {TARGET_SEASON} nor the most recent tracked season "
                    f"({most_recent_year}) has coverage.injuries=True on the free tier - no viable "
                    "path for this source under the current plan."
                )
        else:
            # --- Question 2: is there a usable publication/update timestamp? ---
            budget.spend(1)
            injuries_payload = fetch_injuries_for_league_season(
                PREMIER_LEAGUE_ID, TARGET_SEASON, api_key, cache_dir=cache_dir
            )
            print(
                f"[req {budget.used}] /injuries?league={PREMIER_LEAGUE_ID}&season={TARGET_SEASON} -> "
                f"errors={injuries_payload.get('errors')}, results={injuries_payload.get('results')}",
                file=sys.stderr,
            )

            records = injuries_payload.get("response", []) if not has_api_errors(injuries_payload) else []
            used_fallback = False

            if not records:
                used_fallback = True
                budget.spend(1)
                fixtures_payload = fetch_fixtures_for_league_season(
                    PREMIER_LEAGUE_ID, TARGET_SEASON, api_key, cache_dir=cache_dir
                )
                print(
                    f"[req {budget.used}] /fixtures?league={PREMIER_LEAGUE_ID}&season={TARGET_SEASON} -> "
                    f"errors={fixtures_payload.get('errors')}, results={fixtures_payload.get('results')}",
                    file=sys.stderr,
                )
                sampled_fixture_ids = (
                    _sample_fixture_ids(fixtures_payload, N_FIXTURE_SAMPLE)
                    if not has_api_errors(fixtures_payload)
                    else []
                )
                for fixture_id in sampled_fixture_ids:
                    if budget.used >= budget.cap:
                        break
                    budget.spend(1)
                    per_fixture_payload = fetch_injuries_for_fixture(fixture_id, api_key, cache_dir=cache_dir)
                    print(
                        f"[req {budget.used}] /injuries?fixture={fixture_id} -> "
                        f"errors={per_fixture_payload.get('errors')}, results={per_fixture_payload.get('results')}",
                        file=sys.stderr,
                    )
                    if not has_api_errors(per_fixture_payload):
                        records.extend(per_fixture_payload.get("response", []))

            fields_seen: set[str] = set()
            for record in records:
                fields_seen |= flatten_keys(record)

            section_lines += [
                "## Question 2: does any field function as a real publication/update timestamp?",
                "",
                f"- Query path used: {'per-fixture fallback sample' if used_fallback else 'broad league+season query'}",
                f"- Total injury records retrieved: {len(records)}",
                f"- All distinct (flattened) field paths seen across records: "
                f"{sorted(fields_seen) if fields_seen else '(none - no records retrieved)'}",
                "",
                "This question requires a human read of the actual field names/values above - a field "
                "existing is not proof of what it represents. See the Verdict section for the actual "
                "call made after reading the real data below.",
                "",
            ]

            if records:
                section_lines.append("### Minimal example record(s)")
                section_lines.append("")
                for record in records[:2]:
                    section_lines.append("```json")
                    section_lines.append(json.dumps(record, indent=2, ensure_ascii=False))
                    section_lines.append("```")
                    section_lines.append("")

            if not records:
                verdict = "reject-source"
                verdict_reason = (
                    "coverage.injuries reported True for this season, but no injury records were "
                    "actually returned by either the broad league+season query or the per-fixture "
                    "fallback sample - the coverage flag does not appear to reflect retrievable data "
                    "for this league/season on the free tier."
                )
            else:
                # --- Question 3: entity resolution + coverage, only reached if 1 and 2 passed ---
                team_names_seen = {
                    r.get("team", {}).get("name") for r in records if r.get("team", {}).get("name")
                }
                known_names = set(E0_TEAM_NAME_MAP.values())
                matched_names = team_names_seen & known_names
                unmatched_names = team_names_seen - known_names

                section_lines += [
                    "## Question 3: entity resolution against the existing E0 dataset",
                    "",
                    f"- Distinct team names seen in injury records: {sorted(team_names_seen)}",
                    f"- Matched against the existing 20-team E0 name set: {sorted(matched_names)}",
                    f"- Unmatched: {sorted(unmatched_names) if unmatched_names else 'none'}",
                    "",
                ]

                # Placeholder pending the manual timestamp read below - defaults conservative.
                verdict = "reject-for-backtest-but-viable-for-paper-journal"
                verdict_reason = (
                    "Historical coverage and real injury records both confirmed - see Question 2's "
                    "example record(s) above for the actual field names. This script does NOT "
                    "auto-classify whether a real timestamp field exists (a field name alone doesn't "
                    "prove what it represents) - that judgment must be made by reading the printed "
                    "example record(s) above and is recorded in this report's final Verdict section "
                    "by whoever reviews the real output, not computed here."
                )

    # --- Assemble the report ---
    lines = [
        "# Phase 3 Injury Spike Report: API-Football",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Source: API-Football (direct, free tier), league={PREMIER_LEAGUE_ID} (Premier League), "
        f"target season={TARGET_SEASON} (2023-24)",
        f"Budget used: {budget.used} / {budget.cap} requests",
        "",
    ]
    lines += section_lines
    lines += [
        "## Verdict",
        "",
        f"**{verdict}**",
        "",
        verdict_reason,
    ]

    report_path = reports_dir / "phase3-injury-spike-report.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n".join(lines))
    print(f"\nFull report written to {report_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
