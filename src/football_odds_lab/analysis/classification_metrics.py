"""Generic multiclass classification metrics - not football-specific, reusable
anywhere a (y_true, predicted-probability-matrix) pair needs scoring.

See docs/PHASE1_BASELINE_MODEL_PLAN.md section 5.
"""

from dataclasses import dataclass

import numpy as np
from sklearn.metrics import log_loss as sklearn_log_loss

from football_odds_lab.analysis.odds_math import OUTCOMES


def accuracy(y_true: list[str], y_pred: list[str]) -> float:
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must be the same length")
    if not y_true:
        return float("nan")
    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    return correct / len(y_true)


def multiclass_log_loss(y_true: list[str], proba: np.ndarray) -> float:
    """proba's columns must be in OUTCOMES=(H,D,A) order, same convention as every
    other function in this module and in line_movement_baselines.py.

    sklearn.metrics.log_loss silently assumes probability columns are in
    alphabetical label order regardless of what's passed via `labels=` (confirmed
    via its own runtime warning, not assumed) - so this reorders columns to
    alphabetical (A, D, H) before calling it. Getting this wrong doesn't raise an
    error, it just silently scores every prediction against the wrong class -
    exactly the kind of bug a hand-computed test in
    tests/test_classification_metrics.py exists to catch.
    """
    alphabetical_labels = sorted(OUTCOMES)
    reorder = [OUTCOMES.index(label) for label in alphabetical_labels]
    reordered_proba = proba[:, reorder]
    return float(sklearn_log_loss(y_true, reordered_proba, labels=alphabetical_labels))


def multiclass_brier_score(y_true: list[str], proba: np.ndarray) -> float:
    """One-vs-rest average: mean squared error between the one-hot true label and
    the predicted probability vector, averaged over samples. sklearn's own
    brier_score_loss is binary-only, so this is a small manual multiclass version -
    0.0 is perfect, higher is worse."""
    one_hot = np.array([[1.0 if outcome == label else 0.0 for outcome in OUTCOMES] for label in y_true])
    return float(np.mean(np.sum((proba - one_hot) ** 2, axis=1)))


def expected_weighted_random_accuracy(
    reference_class_frequencies: dict[str, float], evaluation_class_frequencies: dict[str, float]
) -> float:
    """Closed-form expected accuracy of a baseline that guesses each match's class
    by random draw from `reference_class_frequencies` (e.g. the train fold's class
    mix), scored against matches whose true labels occur at
    `evaluation_class_frequencies` (e.g. the validation fold's actual mix).

    P(a given match is guessed correctly) = sum_c P(true=c) * P(guess=c), since the
    guess and the true label are independent draws - this is that sum, computed
    analytically rather than by actually sampling, so the report this feeds into
    doesn't need a random seed to be reproducible. Always <= the majority-class
    baseline's expected accuracy for the same distributions (guessing the mode
    every time beats guessing randomly in proportion) - included for context on
    how much of any baseline's edge is "there's structure at all" vs specific to
    that baseline's rule.
    """
    return sum(
        reference_class_frequencies.get(c, 0.0) * evaluation_class_frequencies.get(c, 0.0) for c in OUTCOMES
    )


@dataclass(frozen=True)
class CalibrationBin:
    predicted_range: tuple[float, float]
    n_samples: int
    mean_predicted_probability: float
    observed_frequency: float


def calibration_summary(y_true: list[str], proba: np.ndarray, n_bins: int = 5) -> list[CalibrationBin]:
    """Calibration check for the predicted (highest-probability) outcome only -
    not a full per-class reliability diagram, sufficient for a first baseline pass.
    Empty bins are omitted rather than reported as zero/NaN."""
    predicted_class_index = proba.argmax(axis=1)
    predicted_probability = proba[np.arange(len(proba)), predicted_class_index]
    predicted_outcome = [OUTCOMES[i] for i in predicted_class_index]
    was_correct = np.array([t == p for t, p in zip(y_true, predicted_outcome)], dtype=float)

    bin_edges = np.linspace(0, 1, n_bins + 1)
    bins = []
    for low, high in zip(bin_edges[:-1], bin_edges[1:]):
        is_last_bin = high >= 1.0
        mask = (predicted_probability >= low) & (
            predicted_probability <= high if is_last_bin else predicted_probability < high
        )
        n = int(mask.sum())
        if n == 0:
            continue
        bins.append(
            CalibrationBin(
                predicted_range=(float(low), float(high)),
                n_samples=n,
                mean_predicted_probability=float(predicted_probability[mask].mean()),
                observed_frequency=float(was_correct[mask].mean()),
            )
        )
    return bins
