import math

import pandas as pd

from football_odds_lab.analysis.line_movement_baselines import (
    fit_logistic_regression_baseline,
    fit_majority_class_baseline,
    opening_favorite_heuristic_predict,
)
from football_odds_lab.analysis.odds_math import OUTCOMES


def test_majority_class_baseline_learns_train_distribution():
    train_targets = pd.Series(["H", "H", "H", "D", "A"])
    baseline = fit_majority_class_baseline(train_targets)

    assert math.isclose(baseline.class_probabilities["H"], 0.6, abs_tol=1e-9)
    assert math.isclose(baseline.class_probabilities["D"], 0.2, abs_tol=1e-9)
    assert math.isclose(baseline.class_probabilities["A"], 0.2, abs_tol=1e-9)
    assert baseline.predict(3) == ["H", "H", "H"]


def test_majority_class_baseline_proba_shape_and_column_order():
    train_targets = pd.Series(["H", "D", "D", "A"])
    baseline = fit_majority_class_baseline(train_targets)

    proba = baseline.predict_proba(5)

    assert proba.shape == (5, 3)  # 5 rows, len(OUTCOMES) columns
    # Every row is identical (constant prediction) and matches OUTCOMES=(H,D,A) order.
    expected_row = [baseline.class_probabilities[o] for o in OUTCOMES]
    for row in proba:
        assert list(row) == expected_row


def test_majority_class_baseline_handles_missing_class_in_train():
    # No draws at all in this training fold - D must still get 0.0, not KeyError.
    train_targets = pd.Series(["H", "A", "H"])
    baseline = fit_majority_class_baseline(train_targets)
    assert baseline.class_probabilities["D"] == 0.0


def test_opening_favorite_heuristic_picks_highest_opening_probability():
    df = pd.DataFrame({
        "opening_prob_home": [0.6, 0.2, 0.33],
        "opening_prob_draw": [0.25, 0.3, 0.34],
        "opening_prob_away": [0.15, 0.5, 0.33],
    })

    predictions, soft = opening_favorite_heuristic_predict(df)

    assert predictions == ["H", "A", "D"]
    assert soft.shape == (3, 3)
    assert soft[0].tolist() == [1.0, 0.0, 0.0]
    assert soft[1].tolist() == [0.0, 0.0, 1.0]
    assert soft[2].tolist() == [0.0, 1.0, 0.0]


def test_logistic_regression_baseline_recovers_a_clean_linear_signal():
    # Synthetic, deliberately easy: a single feature perfectly separates the 3
    # classes - this just proves the fit/predict/reordering wiring is correct,
    # not that the real feature set has any signal.
    X_train = pd.DataFrame({"x": [-10, -9, -8, 0, 0.5, -0.5, 10, 9, 8]})
    y_train = pd.Series(["A", "A", "A", "D", "D", "D", "H", "H", "H"])

    baseline = fit_logistic_regression_baseline(X_train, y_train)

    X_test = pd.DataFrame({"x": [-9.5, 0.2, 9.5]})
    predictions = baseline.predict(X_test)
    proba = baseline.predict_proba(X_test)

    assert predictions == ["A", "D", "H"]
    assert proba.shape == (3, 3)
    # Each row's probabilities must sum to 1 and follow OUTCOMES=(H,D,A) column order.
    for row in proba:
        assert math.isclose(sum(row), 1.0, abs_tol=1e-6)
    assert proba[0][2] > proba[0][0]  # row 0 (true "A"): P(A) column (index 2) should dominate
    assert proba[2][0] > proba[2][2]  # row 2 (true "H"): P(H) column (index 0) should dominate
