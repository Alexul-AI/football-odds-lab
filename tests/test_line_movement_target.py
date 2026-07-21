import math

import pandas as pd

from football_odds_lab.analysis.line_movement_target import (
    build_target_magnitudes,
    build_targets,
    compute_movement_magnitude,
    compute_movement_target,
)


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


def test_compute_movement_magnitude_is_the_target_sides_own_edge():
    open_odds = {"H": 2.0, "D": 4.0, "A": 4.0}  # fair: 0.5 / 0.25 / 0.25
    close_odds = {"H": 4.0, "D": 4.0, "A": 2.0}  # fair: 0.25 / 0.25 / 0.5
    # target is "A" (edge +0.25); "H" moved just as far but in the other direction
    assert math.isclose(compute_movement_magnitude(open_odds, close_odds), 0.25, abs_tol=1e-9)


def test_compute_movement_magnitude_is_smaller_for_a_smaller_move():
    open_odds = {"H": 2.5, "D": 3.4, "A": 3.2}
    close_odds = {"H": 2.4, "D": 3.4, "A": 3.3}  # smaller shift than the test above
    magnitude = compute_movement_magnitude(open_odds, close_odds)
    assert 0.0 < magnitude < 0.25


def test_build_target_magnitudes_matches_per_match_computation():
    df = pd.DataFrame([
        {"PSH": 2.0, "PSD": 4.0, "PSA": 4.0, "PSCH": 4.0, "PSCD": 4.0, "PSCA": 2.0},
        {"PSH": 4.0, "PSD": 4.0, "PSA": 2.0, "PSCH": 2.0, "PSCD": 4.0, "PSCA": 4.0},
    ])

    magnitudes = build_target_magnitudes(df)

    assert all(math.isclose(m, 0.25, abs_tol=1e-9) for m in magnitudes)
    assert magnitudes.index.tolist() == df.index.tolist()
