"""Phase 1 baseline verdict logic - pure, so it's testable independent of the
runner script's I/O. See docs/PHASE1_BASELINE_MODEL_PLAN.md section 6 and the
main guardrail: logistic regression must beat BOTH baselines, pooled AND across
a real majority of folds, not just one or the other.
"""

from dataclasses import dataclass
from typing import Literal

Verdict = Literal["positive", "weak", "null"]


@dataclass(frozen=True)
class FoldAccuracy:
    majority: float
    favorite: float
    logreg: float


def compute_verdict(fold_accuracies: list[FoldAccuracy], pooled_accuracy: FoldAccuracy) -> Verdict:
    if not fold_accuracies:
        raise ValueError("compute_verdict: no folds - nothing to verdict on")

    n_folds = len(fold_accuracies)
    folds_beat_majority = sum(1 for f in fold_accuracies if f.logreg > f.majority)
    folds_beat_favorite = sum(1 for f in fold_accuracies if f.logreg > f.favorite)

    pooled_beats_majority = pooled_accuracy.logreg > pooled_accuracy.majority
    pooled_beats_favorite = pooled_accuracy.logreg > pooled_accuracy.favorite
    folds_majority_beats_majority = folds_beat_majority > n_folds / 2
    folds_majority_beats_favorite = folds_beat_favorite > n_folds / 2

    if (
        pooled_beats_majority
        and pooled_beats_favorite
        and folds_majority_beats_majority
        and folds_majority_beats_favorite
    ):
        return "positive"
    if not pooled_beats_majority and not pooled_beats_favorite:
        return "null"
    return "weak"
