"""Team-name mapping and match-level entity resolution: The Odds API <-> football-data.co.uk.

E0 only, per docs/PHASE2_SOURCE_SPIKE_PLAN.md's scope. The map below was built
by directly comparing real team names from both sources (The Odds API's
soccer_epl historical snapshot, 2024-03-02; football-data.co.uk's E0 2023-24
CSV) on 2026-07-21 - not fuzzy string matching, not guessed. Per the plan's QA
gate: entity matching must produce a match-rate report and an explicit
unmatched-case list, never a silent "looks fine."

If a future season uses a team-name spelling not in this map (promoted/
relegated clubs, or The Odds API changing a name), that shows up as an
unmatched case with a clear reason - exactly what the reporting is for, rather
than trying to guess every possible spelling upfront.
"""

from dataclasses import dataclass

import pandas as pd

E0_TEAM_NAME_MAP: dict[str, str] = {
    "Arsenal": "Arsenal",
    "Aston Villa": "Aston Villa",
    "Bournemouth": "Bournemouth",
    "Brentford": "Brentford",
    "Brighton and Hove Albion": "Brighton",
    "Burnley": "Burnley",
    "Chelsea": "Chelsea",
    "Crystal Palace": "Crystal Palace",
    "Everton": "Everton",
    "Fulham": "Fulham",
    "Liverpool": "Liverpool",
    "Luton": "Luton",
    "Manchester City": "Man City",
    "Manchester United": "Man United",
    "Newcastle United": "Newcastle",
    "Nottingham Forest": "Nott'm Forest",
    "Sheffield United": "Sheffield United",
    "Tottenham Hotspur": "Tottenham",
    "West Ham United": "West Ham",
    "Wolverhampton Wanderers": "Wolves",
}


@dataclass(frozen=True)
class MatchResult:
    matched: bool
    the_odds_api_home: str
    the_odds_api_away: str
    the_odds_api_date: str
    football_data_home: str | None
    football_data_away: str | None
    reason: str | None


def match_event_to_football_data(
    home_team: str,
    away_team: str,
    commence_time: pd.Timestamp,
    football_data_df: pd.DataFrame,
) -> MatchResult:
    """football_data_df must have HomeTeam/AwayTeam/Date columns, Date already
    parsed to datetime. Matches on mapped team names + same calendar date -
    kickoff times can differ by source (UTC vs local reporting conventions),
    so date-level matching is the reliable join key here, not exact timestamp.
    """
    mapped_home = E0_TEAM_NAME_MAP.get(home_team)
    mapped_away = E0_TEAM_NAME_MAP.get(away_team)
    event_date = str(commence_time.date())

    if mapped_home is None or mapped_away is None:
        unmapped = [t for t in (home_team, away_team) if E0_TEAM_NAME_MAP.get(t) is None]
        return MatchResult(
            matched=False,
            the_odds_api_home=home_team,
            the_odds_api_away=away_team,
            the_odds_api_date=event_date,
            football_data_home=mapped_home,
            football_data_away=mapped_away,
            reason=f"no name mapping for: {', '.join(unmapped)}",
        )

    candidates = football_data_df[
        (football_data_df["HomeTeam"] == mapped_home)
        & (football_data_df["AwayTeam"] == mapped_away)
        & (football_data_df["Date"].dt.date == commence_time.date())
    ]

    if len(candidates) == 0:
        return MatchResult(
            matched=False,
            the_odds_api_home=home_team,
            the_odds_api_away=away_team,
            the_odds_api_date=event_date,
            football_data_home=mapped_home,
            football_data_away=mapped_away,
            reason="no football-data.co.uk row for this team pair on this date",
        )

    return MatchResult(
        matched=True,
        the_odds_api_home=home_team,
        the_odds_api_away=away_team,
        the_odds_api_date=event_date,
        football_data_home=mapped_home,
        football_data_away=mapped_away,
        reason=None,
    )
