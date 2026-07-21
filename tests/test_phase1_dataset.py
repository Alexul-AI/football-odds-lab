import math

import pandas as pd

from football_odds_lab.analysis.line_movement_features import parse_match_dates
from football_odds_lab.analysis.line_movement_preprocessing import MODEL_FEATURE_COLUMNS
from football_odds_lab.analysis.line_movement_target import TARGET_COLUMN, TARGET_MAGNITUDE_COLUMN
from football_odds_lab.analysis.phase1_dataset import (
    CLOSE_ODDS_COLUMNS,
    build_dataset_with_target,
    build_diagnostic_dataset,
)


def _synthetic_df() -> pd.DataFrame:
    rows = [
        {
            "Date": "01/08/2020", "League": "E0", "SeasonStartYear": 2020,
            "HomeTeam": "TeamA", "AwayTeam": "TeamB",
            "PSH": 2.0, "PSD": 4.0, "PSA": 4.0,
            "PSCH": 4.0, "PSCD": 4.0, "PSCA": 2.0,
            "FTR": "H",
        },
        {
            "Date": "08/08/2020", "League": "E0", "SeasonStartYear": 2020,
            "HomeTeam": "TeamC", "AwayTeam": "TeamA",
            "PSH": 4.0, "PSD": 4.0, "PSA": 2.0,
            "PSCH": 2.0, "PSCD": 4.0, "PSCA": 4.0,
            "FTR": "A",
        },
    ]
    df = pd.DataFrame(rows)
    df["Date"] = parse_match_dates(df["Date"])
    return df


def test_build_dataset_with_target_computes_labels_and_drops_close_odds():
    result = build_dataset_with_target(_synthetic_df())

    assert TARGET_COLUMN in result.columns
    assert result[TARGET_COLUMN].tolist() == ["A", "H"]
    assert not (set(CLOSE_ODDS_COLUMNS) & set(result.columns))


def test_build_dataset_with_target_preserves_row_count_and_order():
    df = _synthetic_df()
    result = build_dataset_with_target(df)
    assert len(result) == len(df)
    assert result["HomeTeam"].tolist() == df["HomeTeam"].tolist()


def test_build_dataset_with_target_excludes_magnitude_model_path():
    result = build_dataset_with_target(_synthetic_df())
    assert TARGET_MAGNITUDE_COLUMN not in result.columns


def test_build_diagnostic_dataset_includes_magnitude_and_drops_close_odds():
    result = build_diagnostic_dataset(_synthetic_df())

    assert TARGET_MAGNITUDE_COLUMN in result.columns
    assert all(math.isclose(m, 0.25, abs_tol=1e-9) for m in result[TARGET_MAGNITUDE_COLUMN])
    assert not (set(CLOSE_ODDS_COLUMNS) & set(result.columns))


def test_diagnostic_only_columns_never_overlap_model_feature_columns():
    # Structural guarantee: even if build_diagnostic_dataset's output were fed to
    # the preprocessor by mistake, MODEL_FEATURE_COLUMNS wouldn't pick up
    # movement_target/movement_magnitude - it only ever selects its own explicit
    # whitelist.
    diagnostic_only = {TARGET_COLUMN, TARGET_MAGNITUDE_COLUMN}
    assert not (diagnostic_only & set(MODEL_FEATURE_COLUMNS))
