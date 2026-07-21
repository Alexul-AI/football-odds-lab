import pandas as pd

from football_odds_lab.analysis.line_movement_target import build_targets, compute_movement_target


def test_compute_movement_target_picks_side_that_moved_most():
    open_odds = {"H": 2.0, "D": 4.0, "A": 4.0}  # fair: 0.5 / 0.25 / 0.25
    close_odds = {"H": 4.0, "D": 4.0, "A": 2.0}  # fair: 0.25 / 0.25 / 0.5
    assert compute_movement_target(open_odds, close_odds) == "A"


def test_compute_movement_target_home():
    open_odds = {"H": 4.0, "D": 4.0, "A": 2.0}
    close_odds = {"H": 2.0, "D": 4.0, "A": 4.0}
    assert compute_movement_target(open_odds, close_odds) == "H"


def test_build_targets_matches_per_match_computation():
    df = pd.DataFrame([
        {"PSH": 2.0, "PSD": 4.0, "PSA": 4.0, "PSCH": 4.0, "PSCD": 4.0, "PSCA": 2.0},
        {"PSH": 4.0, "PSD": 4.0, "PSA": 2.0, "PSCH": 2.0, "PSCD": 4.0, "PSCA": 4.0},
    ])

    targets = build_targets(df)

    assert targets.tolist() == ["A", "H"]
    assert targets.index.tolist() == df.index.tolist()
