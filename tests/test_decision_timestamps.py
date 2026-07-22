import pandas as pd

from football_odds_lab.analysis.decision_timestamps import (
    DECISION_OFFSETS_HOURS,
    build_decision_points,
    group_by_unique_timestamp,
)


def _football_data_df() -> pd.DataFrame:
    # Two matches sharing the exact same Saturday 15:00 kickoff, one a full
    # week away (far enough that none of ITS 4 decision timestamps coincide
    # with either of the shared-kickoff match's 4, even by coincidence) -
    # mirrors the real E0 2023-24 pattern (many matches per shared kickoff
    # slot) without confounding the test with an accidental cross-offset
    # collision between unrelated matches.
    df = pd.DataFrame([
        {"HomeTeam": "Arsenal", "AwayTeam": "Chelsea", "Kickoff": pd.Timestamp("2024-03-02T15:00:00Z")},
        {"HomeTeam": "Everton", "AwayTeam": "Fulham", "Kickoff": pd.Timestamp("2024-03-02T15:00:00Z")},
        {"HomeTeam": "Liverpool", "AwayTeam": "Burnley", "Kickoff": pd.Timestamp("2024-03-10T14:00:00Z")},
    ])
    return df


def test_build_decision_points_one_per_match_per_offset():
    points = build_decision_points(_football_data_df())
    assert len(points) == 3 * len(DECISION_OFFSETS_HOURS)


def test_build_decision_points_computes_correct_timestamp():
    df = _football_data_df().iloc[[0]]
    points = build_decision_points(df, offsets_hours=(24,))
    assert points[0].decision_timestamp == pd.Timestamp("2024-03-01T15:00:00Z")


def test_group_by_unique_timestamp_dedups_shared_kickoffs():
    points = build_decision_points(_football_data_df())
    groups = group_by_unique_timestamp(points)

    # 2 unique kickoffs x 4 offsets = 8 unique decision timestamps, not 12
    # (3 matches x 4 offsets) - the two Saturday-15:00 matches collapse together.
    assert len(groups) == 2 * len(DECISION_OFFSETS_HOURS)


def test_group_by_unique_timestamp_serves_both_matches_from_one_fetch():
    points = build_decision_points(_football_data_df(), offsets_hours=(6,))
    groups = group_by_unique_timestamp(points)

    shared_decision_ts = pd.Timestamp("2024-03-02T15:00:00Z") - pd.Timedelta(hours=6)
    matches_served = groups[shared_decision_ts]
    assert len(matches_served) == 2
    assert {p.home_team for p in matches_served} == {"Arsenal", "Everton"}


def test_dry_run_cost_estimate_matches_group_count():
    points = build_decision_points(_football_data_df())
    groups = group_by_unique_timestamp(points)
    estimated_credits = 10 * len(groups)
    assert estimated_credits == 80  # 8 unique timestamps x 10 credits
