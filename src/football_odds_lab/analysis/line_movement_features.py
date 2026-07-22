"""Phase 1 baseline feature builder - no model here, features only.

See docs/PHASE1_LINE_MOVEMENT_SIGNAL_METHODOLOGY.md for the full spec. Short
version: every feature here must be computable strictly from information at or
before the opening snapshot, and every rolling/lagged feature must use ONLY
matches with an earlier Date than the match being featurized - never same-day
(kickoff ordering within a day isn't reliably known) and never later.

Implementation choice, deliberate: features are built with a single
chronological pass that maintains running per-team state and computes each
match's features BEFORE updating that state with the match itself. This makes
the no-future-leakage property structural (you cannot see data you haven't
folded into the running state yet), not just something asserted by a vectorized
rolling-window call that could have an off-by-one bug. See
tests/test_line_movement_features.py for the leakage test this is built to pass.
"""

from collections import defaultdict

import pandas as pd

from football_odds_lab.analysis.odds_math import clv_edge, devig_multiplicative, overround

FEATURE_COLUMNS = [
    "season_stage",
    "day_of_week",
    "opening_overround",
    "opening_prob_home",
    "opening_prob_draw",
    "opening_prob_away",
    "home_rest_days",
    "away_rest_days",
    "home_congestion",
    "away_congestion",
    "home_rolling_win_clv_edge",
    "away_rolling_win_clv_edge",
    "home_rolling_market_volatility",
    "away_rolling_market_volatility",
]


def parse_match_dates(date_series: pd.Series) -> pd.Series:
    """football-data.co.uk mixes DD/MM/YY (older seasons, e.g. '18/08/12') and
    DD/MM/YYYY (2018-19 onward) in the same column name across files - verified
    empirically 2026-07-21 against real cached files, not assumed. `format="mixed"`
    handles both without pandas falling back to a slow per-row dateutil parse.
    """
    return pd.to_datetime(date_series, dayfirst=True, format="mixed")


def parse_kickoff_datetimes_utc(date_series: pd.Series, time_series: pd.Series) -> pd.Series:
    """football-data.co.uk's Time column is UK LOCAL time (Europe/London,
    BST-aware), NOT UTC - confirmed empirically 2026-07-21 by comparing a real
    BST-period match's local kickoff (19:30) against The Odds API's UTC
    commence_time for the same match (18:30Z = 19:30 BST). Combining Date+Time
    naively as if it were already UTC would silently misalign every BST-period
    match (roughly late March through late October) by exactly one hour -
    this uses a real Europe/London timezone conversion so the DST transition
    dates (which shift slightly year to year) are handled correctly rather
    than hardcoded.
    """
    naive = pd.to_datetime(
        date_series.astype(str) + " " + time_series.fillna("15:00").astype(str),
        dayfirst=True,
        format="mixed",
    )
    london = naive.dt.tz_localize("Europe/London", ambiguous="NaT", nonexistent="NaT")
    return london.dt.tz_convert("UTC")


def _days_since(previous_date: pd.Timestamp | None, current_date: pd.Timestamp) -> float | None:
    if previous_date is None:
        return None
    return float((current_date - previous_date).days)


def _count_within_window(recent_dates: list[pd.Timestamp], current_date: pd.Timestamp, window_days: int) -> int:
    cutoff = current_date - pd.Timedelta(days=window_days)
    return sum(1 for d in recent_dates if cutoff <= d < current_date)


def _trailing_average(history: list[float]) -> float | None:
    if not history:
        return None
    return sum(history) / len(history)


def build_line_movement_features(df: pd.DataFrame, congestion_window_days: int = 14) -> pd.DataFrame:
    """Adds FEATURE_COLUMNS to a copy of df. Requires Date (parsed, see
    parse_match_dates), HomeTeam, AwayTeam, League, SeasonStartYear, PSH, PSD, PSA,
    PSCH, PSCD, PSCA. Row order in, row order out is preserved.
    """
    if not pd.api.types.is_datetime64_any_dtype(df["Date"]):
        raise ValueError("df['Date'] must already be parsed - call parse_match_dates first")

    working = df.reset_index(drop=True)
    chronological_order = working["Date"].argsort(kind="stable")

    season_totals = working.groupby(["League", "SeasonStartYear"]).size()
    season_running_count: dict[tuple[str, int], int] = defaultdict(int)

    team_last_match_date: dict[str, pd.Timestamp] = {}
    team_recent_match_dates: dict[str, list[pd.Timestamp]] = defaultdict(list)
    team_win_clv_history: dict[str, list[float]] = defaultdict(list)
    team_volatility_history: dict[str, list[float]] = defaultdict(list)

    features_by_original_index: dict[int, dict] = {}

    for original_index in chronological_order:
        row = working.loc[original_index]
        season_key = (row["League"], row["SeasonStartYear"])
        season_running_count[season_key] += 1
        season_stage = season_running_count[season_key] / season_totals[season_key]

        home_rest_days = _days_since(team_last_match_date.get(row["HomeTeam"]), row["Date"])
        away_rest_days = _days_since(team_last_match_date.get(row["AwayTeam"]), row["Date"])

        home_congestion = _count_within_window(
            team_recent_match_dates[row["HomeTeam"]], row["Date"], congestion_window_days
        )
        away_congestion = _count_within_window(
            team_recent_match_dates[row["AwayTeam"]], row["Date"], congestion_window_days
        )

        home_rolling_win_clv = _trailing_average(team_win_clv_history[row["HomeTeam"]])
        away_rolling_win_clv = _trailing_average(team_win_clv_history[row["AwayTeam"]])
        home_rolling_volatility = _trailing_average(team_volatility_history[row["HomeTeam"]])
        away_rolling_volatility = _trailing_average(team_volatility_history[row["AwayTeam"]])

        open_probs = devig_multiplicative([row["PSH"], row["PSD"], row["PSA"]])

        features_by_original_index[original_index] = {
            "season_stage": season_stage,
            "day_of_week": int(row["Date"].dayofweek),
            "opening_overround": overround([row["PSH"], row["PSD"], row["PSA"]]),
            "opening_prob_home": open_probs[0],
            "opening_prob_draw": open_probs[1],
            "opening_prob_away": open_probs[2],
            "home_rest_days": home_rest_days,
            "away_rest_days": away_rest_days,
            "home_congestion": home_congestion,
            "away_congestion": away_congestion,
            "home_rolling_win_clv_edge": home_rolling_win_clv,
            "away_rolling_win_clv_edge": away_rolling_win_clv,
            "home_rolling_market_volatility": home_rolling_volatility,
            "away_rolling_market_volatility": away_rolling_volatility,
        }

        # Update running state AFTER computing this row's features - this ordering
        # is what makes the no-future-leakage guarantee structural, not incidental.
        close_probs = devig_multiplicative([row["PSCH"], row["PSCD"], row["PSCA"]])
        home_win_edge = clv_edge(open_probs[0], close_probs[0])
        away_win_edge = clv_edge(open_probs[2], close_probs[2])
        match_volatility = sum(abs(clv_edge(o, c)) for o, c in zip(open_probs, close_probs)) / 3

        team_last_match_date[row["HomeTeam"]] = row["Date"]
        team_last_match_date[row["AwayTeam"]] = row["Date"]
        team_recent_match_dates[row["HomeTeam"]].append(row["Date"])
        team_recent_match_dates[row["AwayTeam"]].append(row["Date"])
        team_win_clv_history[row["HomeTeam"]].append(home_win_edge)
        team_win_clv_history[row["AwayTeam"]].append(away_win_edge)
        team_volatility_history[row["HomeTeam"]].append(match_volatility)
        team_volatility_history[row["AwayTeam"]].append(match_volatility)

    features_df = pd.DataFrame.from_dict(features_by_original_index, orient="index")[FEATURE_COLUMNS]
    return pd.concat([working, features_df], axis=1)
