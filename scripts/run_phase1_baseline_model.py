"""Phase 1: run the walk-forward baseline model.

Usage:
    python scripts/run_phase1_baseline_model.py

Implements docs/PHASE1_BASELINE_MODEL_PLAN.md exactly: majority-class / opening-
favorite-heuristic / logistic-regression baselines, expanding walk-forward
validation by season, accuracy/log-loss/Brier metrics per fold and pooled, and an
explicit positive/weak/null verdict - no threshold tuning, no narrative rescue.

Deliberately NOT included (per the plan doc, out of scope for this PR): a
simulated CLV-selection profit report. That's an easy follow-up reusing
clv_hypothesis.py's profit accounting once this PR's classification result is in,
not something to bundle in here.
"""

import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from football_odds_lab.analysis.baseline_verdict import FoldAccuracy, compute_verdict
from football_odds_lab.analysis.classification_metrics import (
    accuracy,
    multiclass_brier_score,
    multiclass_log_loss,
)
from football_odds_lab.analysis.line_movement_baselines import (
    fit_logistic_regression_baseline,
    fit_majority_class_baseline,
    opening_favorite_heuristic_predict,
)
from football_odds_lab.analysis.line_movement_features import build_line_movement_features, parse_match_dates
from football_odds_lab.analysis.line_movement_preprocessing import (
    apply_long_absence_handling,
    drop_cold_start_rows,
    fit_preprocessor,
)
from football_odds_lab.analysis.line_movement_target import TARGET_COLUMN, build_targets
from football_odds_lab.analysis.walk_forward import Fold, generate_expanding_season_folds, split_fold
from football_odds_lab.data_sources.football_data_co_uk import EARLIEST_SEASON_START_YEAR, download_all

REPO_ROOT = Path(__file__).resolve().parent.parent
REQUIRED_COLUMNS = ["PSH", "PSD", "PSA", "PSCH", "PSCD", "PSCA", "FTR"]
CLOSE_ODDS_COLUMNS = ["PSCH", "PSCD", "PSCA"]
MIN_TRAIN_SEASONS = 4


def load_dataset(cache_dir: Path) -> pd.DataFrame:
    df = download_all(cache_dir=cache_dir, start_year=EARLIEST_SEASON_START_YEAR)
    before = len(df)
    df = df.dropna(subset=REQUIRED_COLUMNS).reset_index(drop=True)
    dropped = before - len(df)
    if dropped:
        print(f"Dropped {dropped}/{before} rows missing required odds/result columns.", file=sys.stderr)
    df["Date"] = parse_match_dates(df["Date"])
    return df


def build_dataset_with_target(df: pd.DataFrame) -> pd.DataFrame:
    """Computes the target from close odds, THEN drops the close-odds columns -
    structurally, nothing downstream of this function can ever see them again."""
    targets = build_targets(df)
    featured = build_line_movement_features(df).assign(**{TARGET_COLUMN: targets})
    featured = featured.drop(columns=CLOSE_ODDS_COLUMNS)
    assert not (set(CLOSE_ODDS_COLUMNS) & set(featured.columns)), "close odds leaked past target computation"
    return featured


@dataclass
class FoldResult:
    fold_index: int
    validate_season: int
    n_train: int
    n_validate: int
    majority_accuracy: float
    favorite_accuracy: float
    logreg_accuracy: float
    majority_log_loss: float
    favorite_log_loss: float
    logreg_log_loss: float
    majority_brier: float
    favorite_brier: float
    logreg_brier: float


def run_fold(train_df: pd.DataFrame, validate_df: pd.DataFrame, fold: Fold, fold_index: int) -> tuple[FoldResult, dict]:
    y_train = train_df[TARGET_COLUMN]
    y_validate = validate_df[TARGET_COLUMN].tolist()

    preprocessor = fit_preprocessor(train_df)
    X_train = preprocessor.transform(train_df)
    X_validate = preprocessor.transform(validate_df)

    majority = fit_majority_class_baseline(y_train)
    majority_pred = majority.predict(len(validate_df))
    majority_proba = majority.predict_proba(len(validate_df))

    favorite_pred, favorite_proba = opening_favorite_heuristic_predict(validate_df)

    logreg = fit_logistic_regression_baseline(X_train, y_train)
    logreg_pred = logreg.predict(X_validate)
    logreg_proba = logreg.predict_proba(X_validate)

    result = FoldResult(
        fold_index=fold_index,
        validate_season=fold.validate_season,
        n_train=len(train_df),
        n_validate=len(validate_df),
        majority_accuracy=accuracy(y_validate, majority_pred),
        favorite_accuracy=accuracy(y_validate, favorite_pred),
        logreg_accuracy=accuracy(y_validate, logreg_pred),
        majority_log_loss=multiclass_log_loss(y_validate, majority_proba),
        favorite_log_loss=multiclass_log_loss(y_validate, favorite_proba),
        logreg_log_loss=multiclass_log_loss(y_validate, logreg_proba),
        majority_brier=multiclass_brier_score(y_validate, majority_proba),
        favorite_brier=multiclass_brier_score(y_validate, favorite_proba),
        logreg_brier=multiclass_brier_score(y_validate, logreg_proba),
    )

    pooled = {
        "y_true": y_validate,
        "majority_pred": majority_pred,
        "majority_proba": majority_proba,
        "favorite_pred": favorite_pred,
        "favorite_proba": favorite_proba,
        "logreg_pred": logreg_pred,
        "logreg_proba": logreg_proba,
    }
    return result, pooled


def format_fold_row(r: FoldResult) -> str:
    return (
        f"| {r.fold_index} | {r.validate_season} | {r.n_train} | {r.n_validate} | "
        f"{r.majority_accuracy:.3f} | {r.favorite_accuracy:.3f} | {r.logreg_accuracy:.3f} | "
        f"{r.majority_log_loss:.3f} | {r.favorite_log_loss:.3f} | {r.logreg_log_loss:.3f} | "
        f"{r.majority_brier:.3f} | {r.favorite_brier:.3f} | {r.logreg_brier:.3f} |"
    )


def main() -> None:
    cache_dir = REPO_ROOT / "data" / "raw"
    reports_dir = REPO_ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    df = load_dataset(cache_dir)
    dataset = build_dataset_with_target(df)
    dataset = apply_long_absence_handling(dataset)
    dataset = drop_cold_start_rows(dataset)

    available_seasons = sorted(dataset["SeasonStartYear"].unique().tolist())
    folds = generate_expanding_season_folds(available_seasons, min_train_seasons=MIN_TRAIN_SEASONS)

    fold_results: list[FoldResult] = []
    pooled_y_true: list[str] = []
    pooled_preds: dict[str, list[str]] = {"majority": [], "favorite": [], "logreg": []}
    pooled_probas: dict[str, list[np.ndarray]] = {"majority": [], "favorite": [], "logreg": []}

    for i, fold in enumerate(folds, start=1):
        train_df, validate_df = split_fold(dataset, fold)
        result, pooled = run_fold(train_df, validate_df, fold, i)
        fold_results.append(result)

        pooled_y_true.extend(pooled["y_true"])
        pooled_preds["majority"].extend(pooled["majority_pred"])
        pooled_preds["favorite"].extend(pooled["favorite_pred"])
        pooled_preds["logreg"].extend(pooled["logreg_pred"])
        pooled_probas["majority"].append(pooled["majority_proba"])
        pooled_probas["favorite"].append(pooled["favorite_proba"])
        pooled_probas["logreg"].append(pooled["logreg_proba"])

        print(f"Fold {i}/{len(folds)} (validate {fold.validate_season}): "
              f"majority={result.majority_accuracy:.3f} favorite={result.favorite_accuracy:.3f} "
              f"logreg={result.logreg_accuracy:.3f}", file=sys.stderr)

    pooled_accuracy = {name: accuracy(pooled_y_true, preds) for name, preds in pooled_preds.items()}
    pooled_log_loss = {
        name: multiclass_log_loss(pooled_y_true, np.concatenate(probas))
        for name, probas in pooled_probas.items()
    }
    pooled_brier = {
        name: multiclass_brier_score(pooled_y_true, np.concatenate(probas))
        for name, probas in pooled_probas.items()
    }

    fold_accuracies = [
        FoldAccuracy(majority=r.majority_accuracy, favorite=r.favorite_accuracy, logreg=r.logreg_accuracy)
        for r in fold_results
    ]
    pooled_fold_accuracy = FoldAccuracy(
        majority=pooled_accuracy["majority"], favorite=pooled_accuracy["favorite"], logreg=pooled_accuracy["logreg"]
    )
    verdict = compute_verdict(fold_accuracies, pooled_fold_accuracy)

    lines = [
        "# Phase 1 Baseline Model Report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Folds: {len(folds)} (expanding walk-forward, min {MIN_TRAIN_SEASONS} training seasons)",
        f"Rows after feature/target build, long-absence handling, and cold-start drop: {len(dataset)}",
        "",
        "## Verdict",
        "",
        f"**{verdict.upper()}**",
        "",
        {
            "positive": (
                "Logistic regression beat both the majority-class baseline AND the "
                "opening-favorite heuristic, pooled and across a real majority of folds."
            ),
            "weak": (
                "Logistic regression beat at least one baseline but not both, or beat "
                "the pooled numbers without a real majority of individual folds agreeing "
                "- mixed evidence, not a clean result either way."
            ),
            "null": (
                "Logistic regression did not beat the simple baselines out-of-sample. "
                "Reported as-is, per docs/PHASE1_BASELINE_MODEL_PLAN.md's acceptance "
                "criterion: a clean null here is a legitimate, useful Phase 1 outcome, "
                "not a project failure."
            ),
        }[verdict],
        "",
        "## Pooled metrics (all folds' validation predictions combined)",
        "",
        "| Model | Accuracy | Log loss | Brier |",
        "|---|---|---|---|",
        f"| Majority class | {pooled_accuracy['majority']:.3f} | {pooled_log_loss['majority']:.3f} | "
        f"{pooled_brier['majority']:.3f} |",
        f"| Opening favorite | {pooled_accuracy['favorite']:.3f} | {pooled_log_loss['favorite']:.3f} | "
        f"{pooled_brier['favorite']:.3f} |",
        f"| Logistic regression | {pooled_accuracy['logreg']:.3f} | {pooled_log_loss['logreg']:.3f} | "
        f"{pooled_brier['logreg']:.3f} |",
        "",
        "**Opening favorite's log loss/Brier numbers are structurally not comparable "
        "to the other two rows** - it makes hard all-or-nothing predictions (100% on "
        "one outcome, 0% on the other two), so every miss costs it a near-maximal "
        "penalty under either metric. That's expected given it's a one-line rule with "
        "no learned probabilities, not a sign it's a worse model - only its accuracy "
        "column is meaningfully comparable to the other two.",
        "",
        "## Per-fold results",
        "",
        "| Fold | Validate season | N train | N validate | Acc (maj) | Acc (fav) | Acc (logreg) | "
        "LogLoss (maj) | LogLoss (fav) | LogLoss (logreg) | Brier (maj) | Brier (fav) | Brier (logreg) |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    lines.extend(format_fold_row(r) for r in fold_results)

    lines += [
        "",
        "## Read this honestly",
        "",
        "- Accuracy alone isn't the bar - logistic regression must beat the "
        "**opening-favorite heuristic** specifically, not just the weaker "
        "majority-class baseline, per the plan doc's main guardrail. Beating only "
        "majority-class would mean the extra features aren't adding real "
        "information over 'the market already told you the favorite.'",
        "- Per-fold results matter as much as pooled - a model that wins pooled but "
        "loses in most individual folds is not a stable result.",
        "- No threshold tuning, no feature reshuffling happened to produce this "
        "verdict - see docs/PHASE1_BASELINE_MODEL_PLAN.md section 6.",
    ]

    report_path = reports_dir / "phase1-baseline-model-report.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n".join(lines))
    print(f"\nFull report written to {report_path}")


if __name__ == "__main__":
    main()
