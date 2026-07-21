import pandas as pd

from football_odds_lab.analysis.walk_forward import Fold, generate_expanding_season_folds, split_fold


def test_generate_expanding_season_folds_matches_plan_doc_sequence():
    # Mirrors docs/PHASE1_BASELINE_MODEL_PLAN.md's fold table for the real
    # 2012-2025 range: first fold trains on 2012-2015, validates 2016; last
    # fold trains on 2012-2024, validates 2025.
    seasons = list(range(2012, 2026))  # 2012..2025 inclusive

    folds = generate_expanding_season_folds(seasons, min_train_seasons=4)

    assert len(folds) == 10
    assert folds[0] == Fold(train_seasons=(2012, 2013, 2014, 2015), validate_season=2016)
    assert folds[-1] == Fold(
        train_seasons=tuple(range(2012, 2025)), validate_season=2025
    )


def test_generate_expanding_season_folds_handles_unsorted_and_duplicate_input():
    # 4 distinct seasons after dedup/sort, min_train_seasons=4 - no season left to
    # validate on, so zero folds is the correct, honest answer, not an error.
    folds = generate_expanding_season_folds([2015, 2012, 2014, 2013, 2013], min_train_seasons=4)
    assert folds == []


def test_split_fold_excludes_seasons_after_validation():
    df = pd.DataFrame({
        "SeasonStartYear": [2012, 2013, 2014, 2015, 2016, 2017],
        "value": ["a", "b", "c", "d", "e", "f"],
    })
    fold = Fold(train_seasons=(2012, 2013, 2014, 2015), validate_season=2016)

    train_df, validate_df = split_fold(df, fold)

    assert sorted(train_df["value"].tolist()) == ["a", "b", "c", "d"]
    assert validate_df["value"].tolist() == ["e"]
    # 2017 (after the validation season) must appear in neither split.
    assert "f" not in train_df["value"].tolist()
    assert "f" not in validate_df["value"].tolist()
