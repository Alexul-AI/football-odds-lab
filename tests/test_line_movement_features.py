import datetime
import math

import pandas as pd
import pytest

from football_odds_lab.analysis.line_movement_features import (
    build_line_movement_features,
    parse_kickoff_datetimes_utc,
    parse_match_dates,
)


def _synthetic_matches_df() -> pd.DataFrame:
    """4 matches, 3 teams, hand-computable features - see the PR description for
    the worked-out expected values this is designed against.

    M1 2020-08-01 TeamA(H) vs TeamB(A): open fair (2.0/4.0/4.0), close fair (4.0/4.0/2.0)
    M2 2020-08-08 TeamC(H) vs TeamA(A): open == close (2.0/4.0/4.0), no movement
    M3 2020-08-15 TeamA(H) vs TeamC(A): open fair (4.0/4.0/2.0), close fair (2.0/4.0/4.0)
    M4 2020-08-18 TeamB(H) vs TeamA(A): open == close (2.0/4.0/4.0), no movement
    """
    rows = [
        {
            "Date": "01/08/2020",
            "League": "E0",
            "SeasonStartYear": 2020,
            "HomeTeam": "TeamA",
            "AwayTeam": "TeamB",
            "PSH": 2.0, "PSD": 4.0, "PSA": 4.0,
            "PSCH": 4.0, "PSCD": 4.0, "PSCA": 2.0,
            "FTR": "H",
        },
        {
            "Date": "08/08/2020",
            "League": "E0",
            "SeasonStartYear": 2020,
            "HomeTeam": "TeamC",
            "AwayTeam": "TeamA",
            "PSH": 2.0, "PSD": 4.0, "PSA": 4.0,
            "PSCH": 2.0, "PSCD": 4.0, "PSCA": 4.0,
            "FTR": "H",
        },
        {
            "Date": "15/08/2020",
            "League": "E0",
            "SeasonStartYear": 2020,
            "HomeTeam": "TeamA",
            "AwayTeam": "TeamC",
            "PSH": 4.0, "PSD": 4.0, "PSA": 2.0,
            "PSCH": 2.0, "PSCD": 4.0, "PSCA": 4.0,
            "FTR": "H",
        },
        {
            "Date": "18/08/2020",
            "League": "E0",
            "SeasonStartYear": 2020,
            "HomeTeam": "TeamB",
            "AwayTeam": "TeamA",
            "PSH": 2.0, "PSD": 4.0, "PSA": 4.0,
            "PSCH": 2.0, "PSCD": 4.0, "PSCA": 4.0,
            "FTR": "H",
        },
    ]
    df = pd.DataFrame(rows)
    df["Date"] = parse_match_dates(df["Date"])
    return df


def _isclose_or_both_nan(a, b) -> bool:
    if a is None and b is None:
        return True
    a_nan = a is None or (isinstance(a, float) and math.isnan(a))
    b_nan = b is None or (isinstance(b, float) and math.isnan(b))
    if a_nan or b_nan:
        return a_nan and b_nan
    return math.isclose(a, b, abs_tol=1e-9)


def test_parse_match_dates_handles_two_and_four_digit_years():
    # football-data.co.uk mixes '18/08/12' (older seasons) and '10/08/2018' -
    # verified against real files, see the module docstring.
    parsed = parse_match_dates(pd.Series(["18/08/12", "10/08/2018"]))
    assert parsed.dt.year.tolist() == [2012, 2018]


def test_parse_kickoff_datetimes_utc_converts_bst_period_correctly():
    # Real match, real verification 2026-07-21: football-data.co.uk shows
    # 02/04/2024 19:30 (BST, UTC+1); The Odds API's real commence_time for
    # this exact match was 2024-04-02T18:30:00Z.
    result = parse_kickoff_datetimes_utc(pd.Series(["02/04/2024"]), pd.Series(["19:30"]))
    assert result.iloc[0] == pd.Timestamp("2024-04-02T18:30:00Z")


def test_parse_kickoff_datetimes_utc_no_shift_during_gmt_period():
    # Real match: football-data.co.uk 02/03/2024 15:00 (GMT, before BST starts
    # for 2024) matched The Odds API's 2024-03-02T15:00:00Z exactly - no offset.
    result = parse_kickoff_datetimes_utc(pd.Series(["02/03/2024"]), pd.Series(["15:00"]))
    assert result.iloc[0] == pd.Timestamp("2024-03-02T15:00:00Z")


def test_parse_kickoff_datetimes_utc_handles_missing_time():
    result = parse_kickoff_datetimes_utc(pd.Series(["02/03/2024"]), pd.Series([None]))
    assert result.iloc[0] == pd.Timestamp("2024-03-02T15:00:00Z")  # defaults to 15:00 local


def test_preserves_input_row_order():
    df = _synthetic_matches_df()
    # Shuffle the input so it's NOT already chronological, to actually exercise
    # the reordering logic rather than trivially matching by coincidence.
    shuffled = df.iloc[[2, 0, 3, 1]].reset_index(drop=True)

    result = build_line_movement_features(shuffled)

    assert result["HomeTeam"].tolist() == shuffled["HomeTeam"].tolist()
    assert result["Date"].tolist() == shuffled["Date"].tolist()


def test_season_stage_is_chronological_rank_over_season_total():
    result = build_line_movement_features(_synthetic_matches_df())
    assert result["season_stage"].tolist() == [0.25, 0.5, 0.75, 1.0]


def test_day_of_week_matches_python_stdlib():
    result = build_line_movement_features(_synthetic_matches_df())
    expected = [datetime.date(2020, 8, 1).weekday(), datetime.date(2020, 8, 8).weekday()]
    assert result["day_of_week"].tolist()[:2] == expected


def test_opening_probabilities_and_overround_for_fair_odds():
    result = build_line_movement_features(_synthetic_matches_df())
    m1 = result.iloc[0]
    assert math.isclose(m1["opening_prob_home"], 0.5, abs_tol=1e-9)
    assert math.isclose(m1["opening_prob_draw"], 0.25, abs_tol=1e-9)
    assert math.isclose(m1["opening_prob_away"], 0.25, abs_tol=1e-9)
    assert math.isclose(m1["opening_overround"], 0.0, abs_tol=1e-9)


def test_first_appearance_has_cold_start_nones():
    result = build_line_movement_features(_synthetic_matches_df())
    m1 = result.iloc[0]  # TeamA and TeamB's first-ever match in this data
    for col in [
        "home_rest_days", "away_rest_days",
        "home_rolling_win_clv_edge", "away_rolling_win_clv_edge",
        "home_rolling_market_volatility", "away_rolling_market_volatility",
    ]:
        assert m1[col] is None or (isinstance(m1[col], float) and math.isnan(m1[col])), col
    assert m1["home_congestion"] == 0
    assert m1["away_congestion"] == 0


def test_rest_days_and_congestion_hand_computed():
    result = build_line_movement_features(_synthetic_matches_df())
    m4 = result.iloc[3]  # TeamB(H) vs TeamA(A), 2020-08-18

    assert m4["home_rest_days"] == 17.0  # TeamB: 08-01 -> 08-18
    assert m4["away_rest_days"] == 3.0   # TeamA: 08-15 -> 08-18
    assert m4["home_congestion"] == 0    # TeamB's only prior match (08-01) is outside the 14-day window
    assert m4["away_congestion"] == 2    # TeamA played on 08-08 and 08-15, both within 14 days of 08-18


def test_rolling_clv_and_volatility_hand_computed():
    result = build_line_movement_features(_synthetic_matches_df())
    m4 = result.iloc[3]  # TeamB(H) vs TeamA(A)

    assert math.isclose(m4["home_rolling_win_clv_edge"], 0.25, abs_tol=1e-9)  # TeamB's only prior edge
    assert math.isclose(m4["away_rolling_win_clv_edge"], 0.0, abs_tol=1e-9)  # TeamA: (-0.25 + 0 + 0.25) / 3
    assert math.isclose(m4["home_rolling_market_volatility"], 1 / 6, abs_tol=1e-9)
    assert math.isclose(m4["away_rolling_market_volatility"], (1 / 6 + 0 + 1 / 6) / 3, abs_tol=1e-9)


def test_missing_date_column_type_raises():
    df = _synthetic_matches_df()
    df["Date"] = df["Date"].astype(str)  # un-parse it back to plain strings
    with pytest.raises(ValueError, match="parse_match_dates"):
        build_line_movement_features(df)


# --- Leakage tests: the property the whole module exists to guarantee ---

LAGGED_FEATURE_COLUMNS = [
    "home_rest_days", "away_rest_days",
    "home_congestion", "away_congestion",
    "home_rolling_win_clv_edge", "away_rolling_win_clv_edge",
    "home_rolling_market_volatility", "away_rolling_market_volatility",
]


def test_removing_future_matches_does_not_change_past_features():
    full_df = _synthetic_matches_df()
    truncated_df = full_df.iloc[:3].reset_index(drop=True)  # drop M4, the future match

    full_result = build_line_movement_features(full_df)
    truncated_result = build_line_movement_features(truncated_df)

    for i in range(3):  # M1, M2, M3 must be identical whether or not M4 exists
        for col in LAGGED_FEATURE_COLUMNS:
            assert _isclose_or_both_nan(full_result.iloc[i][col], truncated_result.iloc[i][col]), (
                f"row {i}, column {col}: M4's presence changed an earlier match's feature - leakage"
            )


def test_mutating_a_future_match_does_not_change_past_features():
    full_df = _synthetic_matches_df()
    baseline_result = build_line_movement_features(full_df)

    mutated_df = full_df.copy()
    mutated_df.loc[3, ["PSH", "PSD", "PSA", "PSCH", "PSCD", "PSCA"]] = [1.5, 5.0, 6.0, 1.2, 6.0, 9.0]
    mutated_result = build_line_movement_features(mutated_df)

    for i in range(3):
        for col in LAGGED_FEATURE_COLUMNS:
            assert _isclose_or_both_nan(baseline_result.iloc[i][col], mutated_result.iloc[i][col]), (
                f"row {i}, column {col}: mutating M4's odds changed an earlier match's feature - leakage"
            )
