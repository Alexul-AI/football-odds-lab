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
    resolved_end_year = end_year if end_year is not None else _latest_available_season_start_year(cache_dir, leagues)

    frames = [
        download_season_csv(league_code, season_start_year, cache_dir)
        for league_code in leagues
        for season_start_year in range(start_year, resolved_end_year + 1)
    ]
    return pd.concat(frames, ignore_index=True)


def _latest_available_season_start_year(cache_dir: Path, league_codes: list[str]) -> int:
    """Probe forward from the current year to find the most recent season with real data."""
    import datetime

    probe_league = league_codes[0]
    candidate_year = datetime.date.today().year
    while candidate_year >= EARLIEST_SEASON_START_YEAR:
        url = BASE_URL.format(season=season_code(candidate_year), league=probe_league)
        response = requests.head(url, timeout=15)
        if response.status_code == 200:
            return candidate_year
        candidate_year -= 1
    raise RuntimeError("Could not find any available season - football-data.co.uk URL scheme may have changed.")
