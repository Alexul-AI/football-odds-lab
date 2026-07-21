"""The Odds API historical odds snapshot fetcher - Phase 2 source spike only.

See docs/PHASE2_SOURCE_SPIKE_PLAN.md - read-only, audit-scoped (E0, a small
date range). The 200-request budget cap from that plan is enforced by the
caller (scripts/run_phase2_source_spike.py counts requests itself), not by
this module - this module just knows how to make one request and parse one
response.

Caching interpretation: docs/PHASE2_DATA_SOURCE_SELECTION.md already checked
The Odds API's redistribution clause (internal research use, not reselling
data as a standalone product, is fine under standard terms). Local caching to
a gitignored directory for this project's own repeat analysis - never shared,
never redistributed - is treated as consistent with that, same as this
project's existing football-data.co.uk CSV caching. Revisit if this project
ever moves beyond pure local research use.
"""

import json
from dataclasses import dataclass
from pathlib import Path

import requests

BASE_URL = "https://api.the-odds-api.com/v4/historical/sports/{sport_key}/odds"
PINNACLE_BOOKMAKER_KEY = "pinnacle"
H2H_MARKET_KEY = "h2h"


@dataclass(frozen=True)
class PinnacleSnapshotRecord:
    """One event's Pinnacle H/D/A prices at one snapshot moment - preserves
    exactly the fields docs/PHASE2_SOURCE_SPIKE_PLAN.md's QA gates require
    (source, fetched_at, event_timestamp, provider_fixture_id)."""

    source: str
    fetched_at: str
    snapshot_timestamp: str
    event_timestamp: str
    provider_fixture_id: str
    home_team: str
    away_team: str
    price_home: float | None
    price_draw: float | None
    price_away: float | None


def fetch_historical_snapshot(
    sport_key: str,
    snapshot_datetime: str,
    api_key: str,
    cache_dir: Path | None = None,
    regions: str = "eu",
    markets: str = "h2h",
) -> dict:
    """Fetches one historical snapshot (costs credits - 10 per region per
    market, confirmed against the live API 2026-07-21). Caches the raw JSON
    response to cache_dir if given, so a repeated run doesn't re-spend budget -
    never writes the api_key itself to the cache file, only the response body.
    """
    cache_path = None
    if cache_dir is not None:
        cache_key = f"{sport_key}_{snapshot_datetime}_{regions}_{markets}".replace(":", "-")
        cache_path = cache_dir / f"{cache_key}.json"
        if cache_path.exists():
            return json.loads(cache_path.read_text(encoding="utf-8"))

    url = BASE_URL.format(sport_key=sport_key)
    response = requests.get(
        url,
        params={"apiKey": api_key, "regions": regions, "markets": markets, "date": snapshot_datetime},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()

    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(payload), encoding="utf-8")

    return payload


def extract_pinnacle_records(raw_snapshot: dict, fetched_at: str) -> list[PinnacleSnapshotRecord]:
    """Pure - no I/O. Flattens one snapshot response into per-event Pinnacle
    price records. price_home/draw/away are None if Pinnacle had no price for
    that event at this snapshot (not every bookmaker covers every event at
    every moment) - callers must handle that, not assume it's always present.
    """
    snapshot_timestamp = raw_snapshot["timestamp"]
    records = []
    for event in raw_snapshot["data"]:
        prices = _pinnacle_h2h_prices(event)
        records.append(
            PinnacleSnapshotRecord(
                source="the_odds_api",
                fetched_at=fetched_at,
                snapshot_timestamp=snapshot_timestamp,
                event_timestamp=event["commence_time"],
                provider_fixture_id=event["id"],
                home_team=event["home_team"],
                away_team=event["away_team"],
                price_home=prices.get(event["home_team"]) if prices else None,
                price_draw=prices.get("Draw") if prices else None,
                price_away=prices.get(event["away_team"]) if prices else None,
            )
        )
    return records


def _pinnacle_h2h_prices(event: dict) -> dict[str, float] | None:
    for bookmaker in event.get("bookmakers", []):
        if bookmaker["key"] != PINNACLE_BOOKMAKER_KEY:
            continue
        for market in bookmaker.get("markets", []):
            if market["key"] != H2H_MARKET_KEY:
                continue
            return {outcome["name"]: outcome["price"] for outcome in market["outcomes"]}
    return None
