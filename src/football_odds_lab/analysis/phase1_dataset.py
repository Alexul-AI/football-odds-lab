"""Shared Phase 1 dataset assembly: features + target(+magnitude), close odds excluded.

Extracted from scripts/run_phase1_baseline_model.py (PR #9) so both that runner
and the diagnostic script build the exact same dataset the exact same way,
instead of two scripts quietly drifting apart. Pure given an already-loaded,
already-date-parsed DataFrame - no I/O here.
"""

import pandas as pd

from football_odds_lab.analysis.line_movement_features import build_line_movement_features
from football_odds_lab.analysis.line_movement_target import (
    TARGET_COLUMN,
    TARGET_MAGNITUDE_COLUMN,
    build_target_magnitudes,
    build_targets,
)

REQUIRED_COLUMNS = ["PSH", "PSD", "PSA", "PSCH", "PSCD", "PSCA", "FTR"]
CLOSE_ODDS_COLUMNS = ["PSCH", "PSCD", "PSCA"]


def _build_dataset_with_target_and_magnitude(df: pd.DataFrame) -> pd.DataFrame:
    targets = build_targets(df)
    magnitudes = build_target_magnitudes(df)
    featured = build_line_movement_features(df).assign(
        **{TARGET_COLUMN: targets, TARGET_MAGNITUDE_COLUMN: magnitudes}
    )
    featured = featured.drop(columns=CLOSE_ODDS_COLUMNS)
    assert not (set(CLOSE_ODDS_COLUMNS) & set(featured.columns)), "close odds leaked past target computation"
    return featured


def build_dataset_with_target(df: pd.DataFrame) -> pd.DataFrame:
    """df must have Date already parsed (line_movement_features.parse_match_dates)
    and REQUIRED_COLUMNS present with no nulls. Computes the target from close
    odds, THEN drops the close-odds columns - structurally, nothing downstream of
    this function can ever see them again. Model-training path: excludes
    movement_magnitude too (diagnostic-only, see build_diagnostic_dataset)."""
    return _build_dataset_with_target_and_magnitude(df).drop(columns=[TARGET_MAGNITUDE_COLUMN])


def build_diagnostic_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Same as build_dataset_with_target, plus movement_magnitude - diagnostic use
    only (see the Phase 1 opening-favorite-effect diagnostic). Never used by the
    baseline model's training/scoring path; MODEL_FEATURE_COLUMNS in
    line_movement_preprocessing.py doesn't include this column, so it can't reach
    the model even if this function's output were passed there by mistake."""
    return _build_dataset_with_target_and_magnitude(df)
