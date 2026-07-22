"""Extract normalized decision-snapshot records from one raw API response for
one specific match/decision-point - long format, one row per bookmaker.

See docs/PHASE2_EV_METHODOLOGY.md's schema requirement and "Nearest snapshot
rule": the snapshot used for a decision timestamp must be at or before it,
never after (that would be information that didn't exist yet - leakage), and
not staler than a defined tolerance. Pure - no I/O, no network.
"""

from dataclasses import dataclass

import pandas as pd

from football_odds_lab.data_sources.entity_matching import E0_TEAM_NAME_MAP

H2H_MARKET_KEY = "h2h"
DEFAULT_STALENESS_TOLERANCE_HOURS = 48.0


@dataclass(frozen=True)
class DecisionSnapshotRecord:
    source: str
    fetched_at: str
    snapshot_timestamp: str
    decision_timestamp: str
    decision_offset_hours: int
    provider_fixture_id: str
    home_team: str
    away_team: str
    bookmaker: str
    price_home: float
    price_draw: float
    price_away: float


def is_snapshot_valid_for_decision(
    snapshot_timestamp: pd.Timestamp,
    decision_timestamp: pd.Timestamp,
    staleness_tolerance_hours: float = DEFAULT_STALENESS_TOLERANCE_HOURS,
) -> bool:
    """The nearest-snapshot rule's leakage guard. A snapshot strictly AFTER
    the decision timestamp is always rejected, even if it happens to be
    closer in absolute time than an earlier valid one - that's the whole
    point of the rule."""
    if snapshot_timestamp > decision_timestamp:
        return False
    age_hours = (decision_timestamp - snapshot_timestamp).total_seconds() / 3600
    return age_hours <= staleness_tolerance_hours


def find_event_for_match(raw_events: list[dict], home_team_fd: str, away_team_fd: str) -> dict | None:
    """Reverse-lookup: find the raw event whose E0_TEAM_NAME_MAP-mapped team
    names match a football-data.co.uk match's own (already football-data.co.uk
    -style) team names."""
    for event in raw_events:
        mapped_home = E0_TEAM_NAME_MAP.get(event["home_team"])
        mapped_away = E0_TEAM_NAME_MAP.get(event["away_team"])
        if mapped_home == home_team_fd and mapped_away == away_team_fd:
            return event
    return None


def extract_decision_records_for_point(
    raw_snapshot: dict,
    home_team_fd: str,
    away_team_fd: str,
    decision_timestamp: pd.Timestamp,
    decision_offset_hours: int,
    fetched_at: str,
    staleness_tolerance_hours: float = DEFAULT_STALENESS_TOLERANCE_HOURS,
) -> list[DecisionSnapshotRecord]:
    """Returns [] (never raises) if the match isn't found in this snapshot, or
    if the snapshot fails the nearest-at-or-before-decision-timestamp rule -
    callers count an empty result as 'missing' for coverage reporting, not an
    error."""
    snapshot_timestamp = pd.Timestamp(raw_snapshot["timestamp"])
    if not is_snapshot_valid_for_decision(snapshot_timestamp, decision_timestamp, staleness_tolerance_hours):
        return []

    event = find_event_for_match(raw_snapshot["data"], home_team_fd, away_team_fd)
    if event is None:
        return []

    records = []
    for bookmaker in event.get("bookmakers", []):
        for market in bookmaker.get("markets", []):
            if market["key"] != H2H_MARKET_KEY:
                continue
            prices = {o["name"]: o["price"] for o in market["outcomes"]}
            if event["home_team"] not in prices or event["away_team"] not in prices or "Draw" not in prices:
                continue
            records.append(
                DecisionSnapshotRecord(
                    source="the_odds_api",
                    fetched_at=fetched_at,
                    snapshot_timestamp=raw_snapshot["timestamp"],
                    decision_timestamp=str(decision_timestamp),
                    decision_offset_hours=decision_offset_hours,
                    provider_fixture_id=event["id"],
                    home_team=home_team_fd,
                    away_team=away_team_fd,
                    bookmaker=bookmaker["key"],
                    price_home=prices[event["home_team"]],
                    price_draw=prices["Draw"],
                    price_away=prices[event["away_team"]],
                )
            )
    return records
