"""API-Football client - Phase 3 injury spike only.

See docs/PHASE3_INJURY_SPIKE_PLAN.md - read-only, audit-scoped (EPL, one
season). The 20-request budget cap from that plan is enforced by the caller
(scripts/run_phase3_injury_spike.py counts requests itself), not by this
module - this module just knows how to make one request and parse one
response, same convention as data_sources/the_odds_api.py.

Auth: API-Football's direct (non-RapidAPI) dashboard issues a key used via
the `x-apisports-key` HTTP header, not a query parameter - confirmed against
the provider's own documentation, 2026-07-22.
"""

import json
from pathlib import Path

import requests

BASE_URL = "https://v3.football.api-sports.io"
PREMIER_LEAGUE_ID = 39  # stable across seasons - confirmed 2026-07-22


def _get(endpoint: str, params: dict, api_key: str, cache_dir: Path | None, cache_key: str) -> dict:
    cache_path = None
    if cache_dir is not None:
        cache_path = cache_dir / f"{cache_key}.json"
        if cache_path.exists():
            return json.loads(cache_path.read_text(encoding="utf-8"))

    response = requests.get(
        f"{BASE_URL}/{endpoint}",
        headers={"x-apisports-key": api_key},
        params=params,
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()

    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(payload), encoding="utf-8")

    return payload


def fetch_league_seasons(league_id: int, api_key: str, cache_dir: Path | None = None) -> dict:
    """`/leagues?id=X` - no season filter, so the response's `seasons` array
    covers every season this league is tracked for, each with its own
    `coverage` object (including `coverage.injuries: bool`). One call answers
    both halves of docs/PHASE3_INJURY_SPIKE_PLAN.md's question 1 (the target
    2023-24 season, and the most recent tracked season for the prospective-
    fallback check) instead of two.
    """
    return _get("leagues", {"id": league_id}, api_key, cache_dir, f"leagues_{league_id}")


def fetch_injuries_for_league_season(
    league_id: int, season: int, api_key: str, cache_dir: Path | None = None
) -> dict:
    """`/injuries?league=X&season=Y` - the documented broad-query form of this
    endpoint; cheapest way to sample real injury records for a whole season
    if the provider actually returns data for it."""
    return _get(
        "injuries",
        {"league": league_id, "season": season},
        api_key,
        cache_dir,
        f"injuries_league{league_id}_season{season}",
    )


def fetch_injuries_for_fixture(fixture_id: int, api_key: str, cache_dir: Path | None = None) -> dict:
    """`/injuries?fixture=X` - fallback if the broad league+season query
    returns nothing; per-fixture is the documented alternative query shape
    for this endpoint."""
    return _get("injuries", {"fixture": fixture_id}, api_key, cache_dir, f"injuries_fixture{fixture_id}")


def fetch_fixtures_for_league_season(
    league_id: int, season: int, api_key: str, cache_dir: Path | None = None
) -> dict:
    """`/fixtures?league=X&season=Y` - used only to sample real fixture IDs
    for the per-fixture injuries fallback above."""
    return _get(
        "fixtures",
        {"league": league_id, "season": season},
        api_key,
        cache_dir,
        f"fixtures_league{league_id}_season{season}",
    )


def find_season_coverage(leagues_response: dict, season: int) -> dict | None:
    """Pure - no I/O. `leagues_response` is the raw `/leagues` payload;
    returns the `coverage` dict for the given season year, or None if that
    season isn't present in the response at all."""
    for league_entry in leagues_response.get("response", []):
        for season_entry in league_entry.get("seasons", []):
            if season_entry.get("year") == season:
                return season_entry.get("coverage")
    return None


def has_api_errors(payload: dict) -> bool:
    """Pure - no I/O. API-Football's `errors` field is `[]`/`{}` when clean,
    a non-empty list or dict when something (bad params, rate limit, auth)
    went wrong - handle both shapes, never assume one."""
    errors = payload.get("errors")
    if isinstance(errors, (list, dict)):
        return len(errors) > 0
    return False


def flatten_keys(record: dict, prefix: str = "") -> set[str]:
    """Pure - no I/O. Every dotted field path present in a nested dict record
    - used to inspect a real injury record's full schema for docs/
    PHASE3_INJURY_SPIKE_PLAN.md's question 2 (does any field function as a
    real publication/update timestamp), without assuming field names ahead
    of a real response."""
    keys: set[str] = set()
    for key, value in record.items():
        full_key = f"{prefix}.{key}" if prefix else key
        keys.add(full_key)
        if isinstance(value, dict):
            keys |= flatten_keys(value, full_key)
    return keys
