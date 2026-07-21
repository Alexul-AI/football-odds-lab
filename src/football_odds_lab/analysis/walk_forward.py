"""Expanding-window walk-forward folds by season - no random splits.

See docs/PHASE1_BASELINE_MODEL_PLAN.md section 4. Each fold trains on every
season strictly before the validation season, expanding by one season per fold -
the same causal-ordering discipline as line_movement_features.py's leakage tests,
just applied at the fold level instead of the per-feature level.
"""

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class Fold:
    train_seasons: tuple[int, ...]
    validate_season: int


def generate_expanding_season_folds(available_seasons: list[int], min_train_seasons: int = 4) -> list[Fold]:
    """available_seasons: every SeasonStartYear present in the dataset, any order.
    min_train_seasons: minimum number of seasons before the first fold is emitted -
    gives rolling features (line_movement_features.py) real history to build on
    before the first validation fold, not just whatever's technically available.
    """
    ordered = sorted(set(available_seasons))
    folds = []
    for i in range(min_train_seasons, len(ordered)):
        train_seasons = tuple(ordered[:i])
        validate_season = ordered[i]
        folds.append(Fold(train_seasons=train_seasons, validate_season=validate_season))
    return folds


def split_fold(df: pd.DataFrame, fold: Fold, season_column: str = "SeasonStartYear") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (train_df, validate_df). Train is every row whose season is in
    fold.train_seasons; validate is every row whose season == fold.validate_season.
    Rows from any other season (later than the validation season) are excluded
    from both - a fold only ever sees its own past and its own validation season."""
    train_df = df[df[season_column].isin(fold.train_seasons)]
    validate_df = df[df[season_column] == fold.validate_season]
    return train_df, validate_df
