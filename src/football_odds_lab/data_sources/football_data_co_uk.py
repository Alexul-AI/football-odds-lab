"""Downloader for football-data.co.uk historical odds CSVs.

Schema verified empirically against real files on 2026-07-20 (see
docs/PHASE0_METHODOLOGY.md) rather than assumed from memory:

- PSH/PSD/PSA = Pinnacle odds (Home/Draw/Away) at the snapshot football-data.co.uk
  takes before kickoff week; PSCH/PSCD/PSCA = Pinnacle odds at closing (their own
  "C" suffix convention, applied to every bookmaker column, e.g. B365H -> B365CH).
- Confirmed present for all five top-5 leagues (E0/SP1/D1/I1/F1) from the 2012-13
  season onward. Seasons before 2012-13 use different (non-Pinnacle) bookmaker
  columns with no opening/closing distinction at all - not usable for a CLV test.
"""

import io
from pathlib import Path

import pandas as pd
import requests

LEAGUES = {
    "E0": "Premier League (England)",
    "SP1": "La Liga (Spain)",
    "D1": "Bundesliga (Germany)",
    "I1": "Serie A (Italy)",
    "F1": "Ligue 1 (France)",
}

EARLIEST_SEASON_START_YEAR = 2012

BASE_URL = "https://www.football-data.co.uk/mmz4281/{season}/{league}.csv"

# Smallest modern top-5-league season is Bundesliga/Ligue 1 at 18 teams = 306 matches;
# a season file exists (HTTP 200) as soon as it starts, well before it's actually
# played out, so "the file exists" alone isn't enough to call a season complete.
MIN_MATCHES_FOR_COMPLETE_SEASON = 300


def season_code(start_year: int) -> str:
    """2012 -> '1213' (the 2012-13 season)."""
    return f"{start_year % 100:02d}{(start_year + 1) % 100:02d}"


def download_season_csv(league_code: str, season_start_year: int, cache_dir: Path) -> pd.DataFrame:
    """Fetch one league/season CSV, caching it to disk so re-runs don't re-hit the network."""
    season = season_code(season_start_year)
    cache_path = cache_dir / f"{league_code}_{season}.csv"

    if not cache_path.exists():
        url = BASE_URL.format(season=season, league=league_code)
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(response.content)

    df = pd.read_csv(cache_path)
    return df.assign(League=league_code, SeasonStartYear=season_start_year)


def download_all(
    cache_dir: Path,
    start_year: int = EARLIEST_SEASON_START_YEAR,
    end_year: int | None = None,
    league_codes: list[str] | None = None,
) -> pd.DataFrame:
    """Fetch every league/season combination in range and concatenate into one DataFrame.

    end_year is inclusive and defaults to the most recent completed season available.
    """
    leagues = league_codes if league_codes is not None else list(LEAGUES)
    resolved_end_year = end_year if end_year is not None else _latest_completed_season_start_year(leagues)

    frames = [
        download_season_csv(league_code, season_start_year, cache_dir)
        for league_code in leagues
        for season_start_year in range(start_year, resolved_end_year + 1)
    ]
    return pd.concat(frames, ignore_index=True)


def _season_row_count(league_code: str, season_start_year: int) -> int | None:
    """Row count for a season CSV, without touching the on-disk cache. None if it 404s.

    Deliberately bypasses download_season_csv's cache: this is only used to test
    whether a season is complete, and caching a partial in-progress season under its
    final filename would make it "stick" as stale even after the real season finishes
    (download_season_csv never re-fetches once a cache file exists).
    """
    url = BASE_URL.format(season=season_code(season_start_year), league=league_code)
    response = requests.get(url, timeout=30)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return len(pd.read_csv(io.BytesIO(response.content)))


def _latest_completed_season_start_year(league_codes: list[str]) -> int:
    """Walk back from the current year to the most recent season that's actually finished.

    A season's file exists on football-data.co.uk as soon as it starts, long before
    it's played out - checking for HTTP 200 alone would silently accept a fresh,
    barely-started season as "the latest complete one." Row count catches that: a
    season with only a few matchweeks played is nowhere near
    MIN_MATCHES_FOR_COMPLETE_SEASON, so it's skipped in favor of the prior season.
    """
    import datetime

    probe_league = league_codes[0]
    candidate_year = datetime.date.today().year
    while candidate_year >= EARLIEST_SEASON_START_YEAR:
        row_count = _season_row_count(probe_league, candidate_year)
        if row_count is not None and row_count >= MIN_MATCHES_FOR_COMPLETE_SEASON:
            return candidate_year
        candidate_year -= 1
    raise RuntimeError("Could not find any completed season - football-data.co.uk URL scheme may have changed.")
