import pytest

from football_odds_lab.analysis.baseline_verdict import FoldAccuracy, compute_verdict


def test_verdict_positive_when_logreg_clearly_beats_both_baselines():
    folds = [FoldAccuracy(majority=0.40, favorite=0.44, logreg=0.48) for _ in range(10)]
    pooled = FoldAccuracy(majority=0.40, favorite=0.44, logreg=0.48)
    assert compute_verdict(folds, pooled) == "positive"


def test_verdict_null_when_logreg_beats_neither_baseline_pooled():
    folds = [FoldAccuracy(majority=0.44, favorite=0.44, logreg=0.40) for _ in range(10)]
    pooled = FoldAccuracy(majority=0.44, favorite=0.44, logreg=0.40)
    assert compute_verdict(folds, pooled) == "null"


def test_verdict_weak_when_logreg_beats_majority_but_not_favorite():
    # Mirrors the real first run: logreg > majority pooled, but < favorite pooled.
    folds = [FoldAccuracy(majority=0.39, favorite=0.45, logreg=0.44) for _ in range(10)]
    pooled = FoldAccuracy(majority=0.39, favorite=0.45, logreg=0.44)
    assert compute_verdict(folds, pooled) == "weak"


def test_verdict_weak_when_pooled_wins_but_fold_majority_disagrees():
    # Pooled says logreg beats both, but only wins in 3/10 individual folds -
    # a model that only looks good pooled isn't a stable result.
    winning_fold = FoldAccuracy(majority=0.30, favorite=0.30, logreg=0.90)
    losing_fold = FoldAccuracy(majority=0.50, favorite=0.50, logreg=0.45)
    folds = [winning_fold] * 3 + [losing_fold] * 7
    pooled = FoldAccuracy(majority=0.40, favorite=0.40, logreg=0.60)  # still numerically "wins" pooled
    assert compute_verdict(folds, pooled) == "weak"


def test_verdict_requires_strict_majority_of_folds_not_just_half():
    # Exactly half the folds (5/10) favor logreg over the favorite heuristic -
    # not a real majority, so this should not qualify as "positive" even though
    # pooled numbers look clean.
    folds = [FoldAccuracy(majority=0.40, favorite=0.40, logreg=0.50)] * 5 + [
        FoldAccuracy(majority=0.40, favorite=0.60, logreg=0.45)
    ] * 5
    pooled = FoldAccuracy(majority=0.40, favorite=0.50, logreg=0.475)
    assert compute_verdict(folds, pooled) != "positive"


def test_compute_verdict_raises_on_empty_folds():
    with pytest.raises(ValueError, match="no folds"):
        compute_verdict([], FoldAccuracy(majority=0.4, favorite=0.4, logreg=0.4))
