"""Phase 1 preprocessing policy - resolves the two open items from issue #7.

See docs/PHASE1_BASELINE_MODEL_PLAN.md section 2. Two hard rules this module
exists to enforce structurally, not just by convention:

1. Fitting (scaler mean/std, league categories) must use ONLY the train fold -
   never the validation fold, never the full dataset. See
   tests/test_line_movement_preprocessing.py's leakage test.
2. PSCH/PSCD/PSCA must never reach the output feature matrix, even if a caller
   passes them in by mistake - the transform step only ever selects an explicit,
   audited column list, never a blanket pass-through.
"""

from dataclasses import dataclass

import pandas as pd
from sklearn.preprocessing import StandardScaler

from football_odds_lab.analysis.line_movement_features import FEATURE_COLUMNS

# Generously above any normal close-season gap (English/European top-flight
# close seasons run roughly 60-100 days) - only genuine multi-season absences
# from this dataset (promotion/relegation cycles, see PR #6's Sunderland finding)
# should trip this.
LONG_ABSENCE_THRESHOLD_DAYS = 200.0
REST_DAYS_CAP = 200.0

LAGGED_COLUMNS_REQUIRING_WARMUP = [
    "home_rest_days",
    "away_rest_days",
    "home_rolling_win_clv_edge",
    "away_rolling_win_clv_edge",
    "home_rolling_market_volatility",
    "away_rolling_market_volatility",
]

LEAGUE_COLUMN = "League"

# issue #7, item 1: both a capped numeric value AND an explicit indicator - the
# cap keeps the numeric feature from distorting scaling, the indicator preserves
# the "this was an unusual gap" information the cap alone would throw away.
MODEL_FEATURE_COLUMNS = [*FEATURE_COLUMNS, "home_long_absence", "away_long_absence"]


def apply_long_absence_handling(df: pd.DataFrame) -> pd.DataFrame:
    """Threshold is a fixed constant, not fit from data - safe to apply to the
    full dataset before any train/validation split, no leakage risk."""
    result = df.copy()
    result["home_long_absence"] = (result["home_rest_days"] > LONG_ABSENCE_THRESHOLD_DAYS).astype(float)
    result["away_long_absence"] = (result["away_rest_days"] > LONG_ABSENCE_THRESHOLD_DAYS).astype(float)
    result["home_rest_days"] = result["home_rest_days"].clip(upper=REST_DAYS_CAP)
    result["away_rest_days"] = result["away_rest_days"].clip(upper=REST_DAYS_CAP)
    return result


def drop_cold_start_rows(df: pd.DataFrame) -> pd.DataFrame:
    """issue #7, item 2: exclude rows with no rolling history yet rather than
    impute a fake value - matches line_movement_features.py's own documented
    warm-up limitation (a rolling stat over 0-1 prior matches isn't meaningfully
    different from missing)."""
    return df.dropna(subset=LAGGED_COLUMNS_REQUIRING_WARMUP).reset_index(drop=True)


@dataclass
class FoldPreprocessor:
    """Fit once on a train fold; reused (never refit) to transform both that same
    train fold and its validation fold."""

    scaler: StandardScaler
    league_categories: list[str]
    feature_columns: list[str]

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        league_dummy_columns = [f"League_{c}" for c in self.league_categories]
        league_dummies = pd.get_dummies(df[LEAGUE_COLUMN], prefix="League").reindex(
            columns=league_dummy_columns, fill_value=0
        )
        numeric = df[self.feature_columns].astype(float)
        scaled = pd.DataFrame(
            self.scaler.transform(numeric),
            columns=self.feature_columns,
            index=df.index,
        )
        return pd.concat([scaled, league_dummies.astype(float)], axis=1)


def fit_preprocessor(train_df: pd.DataFrame) -> FoldPreprocessor:
    """Fits scaler mean/std and the set of League categories using ONLY train_df.
    Callers must never pass validation-fold or full-dataset rows here."""
    league_categories = sorted(train_df[LEAGUE_COLUMN].unique().tolist())
    scaler = StandardScaler()
    scaler.fit(train_df[MODEL_FEATURE_COLUMNS].astype(float))
    return FoldPreprocessor(scaler=scaler, league_categories=league_categories, feature_columns=MODEL_FEATURE_COLUMNS)
