import math

import numpy as np

from football_odds_lab.analysis.classification_metrics import (
    accuracy,
    calibration_summary,
    multiclass_brier_score,
    multiclass_log_loss,
)


def test_accuracy_basic():
    assert accuracy(["H", "D", "A"], ["H", "H", "A"]) == 2 / 3


def test_accuracy_empty_is_nan():
    assert math.isnan(accuracy([], []))


def test_multiclass_log_loss_uniform_prediction_equals_ln3():
    proba = np.array([[1 / 3, 1 / 3, 1 / 3]])  # column order: H, D, A
    loss = multiclass_log_loss(["H"], proba)
    assert math.isclose(loss, math.log(3), abs_tol=1e-6)


def test_multiclass_log_loss_confident_correct_prediction_is_near_zero():
    proba = np.array([[0.98, 0.01, 0.01]])
    loss = multiclass_log_loss(["H"], proba)
    assert loss < 0.05


def test_multiclass_brier_score_perfect_prediction_is_zero():
    proba = np.array([[1.0, 0.0, 0.0]])
    assert multiclass_brier_score(["H"], proba) == 0.0


def test_multiclass_brier_score_uniform_prediction_hand_computed():
    proba = np.array([[1 / 3, 1 / 3, 1 / 3]])
    score = multiclass_brier_score(["H"], proba)
    # one_hot=[1,0,0], diff=[-2/3,1/3,1/3], squared sum = 4/9+1/9+1/9 = 6/9
    assert math.isclose(score, 6 / 9, abs_tol=1e-9)


def test_calibration_summary_well_calibrated_bin():
    # 10 samples all predicted at 0.8 confidence for the favorite; 8/10 correct -
    # observed frequency should match predicted probability closely.
    y_true = ["H"] * 8 + ["D"] * 2
    proba = np.array([[0.8, 0.1, 0.1]] * 10)

    bins = calibration_summary(y_true, proba, n_bins=5)

    matching_bin = next(b for b in bins if b.predicted_range[0] <= 0.8 < b.predicted_range[1] or b.predicted_range[1] == 1.0)
    assert matching_bin.n_samples == 10
    assert math.isclose(matching_bin.mean_predicted_probability, 0.8, abs_tol=1e-9)
    assert math.isclose(matching_bin.observed_frequency, 0.8, abs_tol=1e-9)


def test_calibration_summary_omits_empty_bins():
    y_true = ["H"] * 5
    proba = np.array([[0.9, 0.05, 0.05]] * 5)  # everything falls in the top bin
    bins = calibration_summary(y_true, proba, n_bins=5)
    assert len(bins) == 1
    assert bins[0].n_samples == 5
