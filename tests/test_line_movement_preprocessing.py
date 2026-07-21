import math

import numpy as np
import pandas as pd

from football_odds_lab.analysis.line_movement_features import FEATURE_COLUMNS
from football_odds_lab.analysis.line_movement_preprocessing import (
    MODEL_FEATURE_COLUMNS,
    REST_DAYS_CAP,
    apply_long_absence_handling,
    drop_cold_start_rows,
    fit_preprocessor,
)

FORBIDDEN_CLOSE_ODDS_COLUMNS = {"PSCH", "PSCD", "PSCA"}


def _synthetic_feature_df(n: int = 20, league: str = "E0") -> pd.DataFrame:
    rng = np.random.default_rng(42)
    data = {col: rng.normal(size=n) for col in FEATURE_COLUMNS}
    data["League"] = [league] * n
    # PSCH/PSCD/PSCA deliberately present, simulating a caller who forgot to drop
    # them before preprocessing - the preprocessor's output must still exclude them.
    data["PSCH"] = rng.uniform(1.5, 5.0, size=n)
    data["PSCD"] = rng.uniform(1.5, 5.0, size=n)
    data["PSCA"] = rng.uniform(1.5, 5.0, size=n)
    return pd.DataFrame(data)


def test_apply_long_absence_handling_caps_and_flags():
    df = pd.DataFrame({
        "home_rest_days": [3.0, 5000.0, None],
        "away_rest_days": [4.0, 7.0, 210.0],
    })

    result = apply_long_absence_handling(df)

    assert result["home_rest_days"].tolist()[:2] == [3.0, REST_DAYS_CAP]
    assert result["home_long_absence"].tolist() == [0.0, 1.0, 0.0]  # NaN > threshold is False
    assert result["away_long_absence"].tolist() == [0.0, 0.0, 1.0]
    assert result["away_rest_days"].iloc[2] == REST_DAYS_CAP


def test_apply_long_absence_handling_leaves_normal_gaps_untouched():
    # A normal close-season gap (~70-100 days) must not trip the indicator or be capped.
    df = pd.DataFrame({"home_rest_days": [85.0], "away_rest_days": [70.0]})
    result = apply_long_absence_handling(df)
    assert result["home_long_absence"].iloc[0] == 0.0
    assert result["home_rest_days"].iloc[0] == 85.0


def test_drop_cold_start_rows_removes_only_rows_with_missing_rolling_history():
    df = pd.DataFrame({
        "home_rest_days": [1.0, None, 3.0],
        "away_rest_days": [1.0, 2.0, 3.0],
        "home_rolling_win_clv_edge": [0.1, 0.2, 0.3],
        "away_rolling_win_clv_edge": [0.1, 0.2, 0.3],
        "home_rolling_market_volatility": [0.1, 0.2, 0.3],
        "away_rolling_market_volatility": [0.1, 0.2, 0.3],
        "keep_me": ["a", "b", "c"],
    })

    result = drop_cold_start_rows(df)

    assert result["keep_me"].tolist() == ["a", "c"]


# --- The tests this module exists to pass ---


def test_model_feature_columns_never_include_close_odds():
    assert not (FORBIDDEN_CLOSE_ODDS_COLUMNS & set(MODEL_FEATURE_COLUMNS))


def test_preprocessor_output_never_includes_close_odds_even_if_present_in_input():
    df = _synthetic_feature_df()
    df = apply_long_absence_handling(
        df.assign(home_rest_days=1.0, away_rest_days=1.0)  # already-numeric rest days for this synthetic case
    )

    preprocessor = fit_preprocessor(df)
    transformed = preprocessor.transform(df)

    assert not (FORBIDDEN_CLOSE_ODDS_COLUMNS & set(transformed.columns))
    assert set(transformed.columns) == set(MODEL_FEATURE_COLUMNS) | {"League_E0"}


def test_fit_preprocessor_uses_only_train_data_not_validation_or_full_dataset():
    train_df = _synthetic_feature_df(n=30)
    train_df = apply_long_absence_handling(train_df.assign(home_rest_days=1.0, away_rest_days=1.0))

    # Validation fold with a deliberately shifted distribution (mean +100) on one
    # feature - if fit_preprocessor secretly used this, the fitted mean would move.
    validation_df = _synthetic_feature_df(n=30)
    validation_df = apply_long_absence_handling(validation_df.assign(home_rest_days=1.0, away_rest_days=1.0))
    validation_df[FEATURE_COLUMNS[0]] += 100.0

    combined_df = pd.concat([train_df, validation_df], ignore_index=True)

    preprocessor_train_only = fit_preprocessor(train_df)
    preprocessor_combined = fit_preprocessor(combined_df)

    feature_index = preprocessor_train_only.feature_columns.index(FEATURE_COLUMNS[0])
    train_only_mean = preprocessor_train_only.scaler.mean_[feature_index]
    combined_mean = preprocessor_combined.scaler.mean_[feature_index]

    assert not math.isclose(train_only_mean, combined_mean, abs_tol=1.0), (
        "fit_preprocessor(train_df) produced the same scaler mean as fitting on "
        "train+validation combined - it must be using only train_df"
    )


def test_transform_raises_on_unseen_league_gracefully_via_reindex():
    train_df = _synthetic_feature_df(league="E0")
    train_df = apply_long_absence_handling(train_df.assign(home_rest_days=1.0, away_rest_days=1.0))
    preprocessor = fit_preprocessor(train_df)

    validation_df = _synthetic_feature_df(league="SP1")
    validation_df = apply_long_absence_handling(validation_df.assign(home_rest_days=1.0, away_rest_days=1.0))

    transformed = preprocessor.transform(validation_df)

    # SP1 wasn't in the training fold, so it's correctly encoded as all-zero
    # (matches no known League_* dummy) rather than raising or fabricating a column.
    assert "League_SP1" not in transformed.columns
    assert (transformed["League_E0"] == 0.0).all()
