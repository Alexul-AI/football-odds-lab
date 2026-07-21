"""Phase 1 diagnostic: why does the opening-favorite heuristic beat logistic regression?

Usage:
    python scripts/run_phase1_diagnostic.py

Pure analysis - no model changes, no new baselines, no threshold tuning. PR #9's
walk-forward run came back WEAK: logistic regression beat majority-class but not
the opening-favorite heuristic. This answers the follow-up question: is the
favorite heuristic's edge a real, stable market pattern, or an artifact of how the
target is defined, concentrated in a few leagues/years, or won mostly on
near-noise micro-movements?

Five checks:
1. Target distribution - overall, by league, by season.
2. Odds bucket analysis - does a stronger favorite make the heuristic MORE
   reliable (does the line keep moving further into strong favorites)?
3. Class asymmetry - home favorite vs away favorite vs no-clear-favorite; how
   often does the market actually move toward a draw at all?
4. Magnitude check - direction alone doesn't say whether a "correct" prediction
   was won on a real, substantial move or a coin-flip-sized one.
5. Baseline sanity - opening-favorite vs an analytical weighted-random baseline
   (not just majority-class), and stability by league and by walk-forward fold.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from football_odds_lab.analysis.classification_metrics import accuracy, expected_weighted_random_accuracy
from football_odds_lab.analysis.line_movement_baselines import (
    fit_majority_class_baseline,
    opening_favorite_heuristic_predict,
)
from football_odds_lab.analysis.line_movement_features import parse_match_dates
from football_odds_lab.analysis.line_movement_preprocessing import apply_long_absence_handling, drop_cold_start_rows
from football_odds_lab.analysis.line_movement_target import TARGET_COLUMN, TARGET_MAGNITUDE_COLUMN
from football_odds_lab.analysis.odds_math import OUTCOMES
from football_odds_lab.analysis.phase1_dataset import REQUIRED_COLUMNS, build_diagnostic_dataset
from football_odds_lab.analysis.walk_forward import generate_expanding_season_folds, split_fold
from football_odds_lab.data_sources.football_data_co_uk import EARLIEST_SEASON_START_YEAR, LEAGUES, download_all

REPO_ROOT = Path(__file__).resolve().parent.parent
MIN_TRAIN_SEASONS = 4
FAVORITE_PROBABILITY_BUCKET_EDGES = [0.0, 0.40, 0.50, 0.60, 1.0001]
FAVORITE_PROBABILITY_BUCKET_LABELS = ["<40%", "40-50%", "50-60%", "60%+"]


def load_dataset(cache_dir: Path) -> pd.DataFrame:
    df = download_all(cache_dir=cache_dir, start_year=EARLIEST_SEASON_START_YEAR)
    before = len(df)
    df = df.dropna(subset=REQUIRED_COLUMNS).reset_index(drop=True)
    dropped = before - len(df)
    if dropped:
        print(f"Dropped {dropped}/{before} rows missing required odds/result columns.", file=sys.stderr)
    df["Date"] = parse_match_dates(df["Date"])
    return df


def build_pct_table(series: pd.Series, group: pd.Series | None = None) -> pd.DataFrame:
    if group is None:
        return series.value_counts(normalize=True).reindex(OUTCOMES).to_frame("share")
    return series.groupby(group).value_counts(normalize=True).unstack().reindex(columns=OUTCOMES)


def section_target_distribution(dataset: pd.DataFrame, favorite_pred: list[str]) -> list[str]:
    overall = dataset[TARGET_COLUMN].value_counts(normalize=True).reindex(OUTCOMES)
    by_league = build_pct_table(dataset[TARGET_COLUMN], dataset["League"])
    by_season = build_pct_table(dataset[TARGET_COLUMN], dataset["SeasonStartYear"])
    favorite_match_rate = accuracy(dataset[TARGET_COLUMN].tolist(), favorite_pred)

    lines = [
        "## 1. Target distribution",
        "",
        f"Overall: H={overall['H']:.3f}, D={overall['D']:.3f}, A={overall['A']:.3f} (n={len(dataset)})",
        "",
        f"**Share of matches where the target already equals the opening favorite: "
        f"{favorite_match_rate:.3f}** - this is the opening-favorite heuristic's overall accuracy, "
        "restated as a plain descriptive stat (should match PR #9's pooled favorite accuracy).",
        "",
        "### By league",
        "",
        "| League | H | D | A | N |",
        "|---|---|---|---|---|",
    ]
    for league in LEAGUES:
        if league not in by_league.index:
            continue
        row = by_league.loc[league]
        n = int((dataset["League"] == league).sum())
        lines.append(f"| {league} | {row['H']:.3f} | {row['D']:.3f} | {row['A']:.3f} | {n} |")

    lines += ["", "### By season", "", "| Season | H | D | A | N |", "|---|---|---|---|---|"]
    for season in sorted(by_season.index):
        row = by_season.loc[season]
        n = int((dataset["SeasonStartYear"] == season).sum())
        lines.append(f"| {season} | {row['H']:.3f} | {row['D']:.3f} | {row['A']:.3f} | {n} |")

    lines.append("")
    return lines


def section_odds_buckets(dataset: pd.DataFrame, favorite_pred: list[str]) -> list[str]:
    favorite_probability = dataset[["opening_prob_home", "opening_prob_draw", "opening_prob_away"]].max(axis=1)
    bucket = pd.cut(
        favorite_probability,
        bins=FAVORITE_PROBABILITY_BUCKET_EDGES,
        labels=FAVORITE_PROBABILITY_BUCKET_LABELS,
        right=False,
    )
    correct = pd.Series(
        [t == p for t, p in zip(dataset[TARGET_COLUMN], favorite_pred)], index=dataset.index
    )

    lines = [
        "## 2. Odds bucket analysis",
        "",
        "Favorite-heuristic accuracy by the favorite's own opening implied probability - "
        "checks whether a stronger favorite makes the heuristic MORE reliable (line "
        "keeps moving further into strong favorites) or whether the relationship is flat/inverted.",
        "",
        "| Bucket | N | Favorite heuristic accuracy | Mean favorite probability |",
        "|---|---|---|---|",
    ]
    for label in FAVORITE_PROBABILITY_BUCKET_LABELS:
        mask = bucket == label
        n = int(mask.sum())
        if n == 0:
            continue
        bucket_accuracy = float(correct[mask].mean())
        mean_prob = float(favorite_probability[mask].mean())
        lines.append(f"| {label} | {n} | {bucket_accuracy:.3f} | {mean_prob:.3f} |")
    lines.append("")
    return lines


def section_class_asymmetry(dataset: pd.DataFrame, favorite_pred: list[str]) -> list[str]:
    probs = dataset[["opening_prob_home", "opening_prob_draw", "opening_prob_away"]]
    favorite_side = probs.idxmax(axis=1).map(
        {"opening_prob_home": "home_favorite", "opening_prob_draw": "draw_favorite", "opening_prob_away": "away_favorite"}
    )
    correct = pd.Series(
        [t == p for t, p in zip(dataset[TARGET_COLUMN], favorite_pred)], index=dataset.index
    )

    lines = [
        "## 3. Class asymmetry",
        "",
        "| Favorite side | N | Favorite heuristic accuracy | Target=H | Target=D | Target=A |",
        "|---|---|---|---|---|---|",
    ]
    for category in ["home_favorite", "away_favorite", "draw_favorite"]:
        mask = favorite_side == category
        n = int(mask.sum())
        if n == 0:
            lines.append(f"| {category} | 0 | - | - | - | - |")
            continue
        category_accuracy = float(correct[mask].mean())
        target_dist = dataset.loc[mask, TARGET_COLUMN].value_counts(normalize=True).reindex(OUTCOMES).fillna(0.0)
        lines.append(
            f"| {category} | {n} | {category_accuracy:.3f} | {target_dist['H']:.3f} | "
            f"{target_dist['D']:.3f} | {target_dist['A']:.3f} |"
        )

    draw_target_rate = float((dataset[TARGET_COLUMN] == "D").mean())
    lines += [
        "",
        f"**Overall share of matches where the line moves toward a draw: {draw_target_rate:.3f}.** "
        "If this is far below 1/3, 'D' is close to a structurally near-dead target class - "
        "any classifier has little to learn there regardless of features.",
        "",
    ]
    return lines


def section_magnitude(dataset: pd.DataFrame, favorite_pred: list[str]) -> list[str]:
    correct = pd.Series(
        [t == p for t, p in zip(dataset[TARGET_COLUMN], favorite_pred)], index=dataset.index
    )
    magnitude = dataset[TARGET_MAGNITUDE_COLUMN]

    lines = [
        "## 4. Magnitude check",
        "",
        "Direction alone doesn't say whether a 'correct' prediction was won on a real, "
        "substantial move or a coin-flip-sized one. Mean/median movement_magnitude "
        "(the winning side's own clv_edge):",
        "",
        "| Group | N | Mean magnitude | Median magnitude |",
        "|---|---|---|---|",
        f"| Favorite heuristic correct | {int(correct.sum())} | {magnitude[correct].mean():.4f} | "
        f"{magnitude[correct].median():.4f} |",
        f"| Favorite heuristic incorrect | {int((~correct).sum())} | {magnitude[~correct].mean():.4f} | "
        f"{magnitude[~correct].median():.4f} |",
    ]
    for outcome in OUTCOMES:
        mask = dataset[TARGET_COLUMN] == outcome
        lines.append(
            f"| Target={outcome} | {int(mask.sum())} | {magnitude[mask].mean():.4f} | "
            f"{magnitude[mask].median():.4f} |"
        )
    lines.append("")
    return lines


def section_baseline_sanity(dataset: pd.DataFrame, favorite_pred: list[str]) -> list[str]:
    correct = pd.Series(
        [t == p for t, p in zip(dataset[TARGET_COLUMN], favorite_pred)], index=dataset.index
    )

    lines = [
        "## 5. Baseline sanity",
        "",
        "### By league",
        "",
        "| League | N | Favorite heuristic accuracy |",
        "|---|---|---|",
    ]
    for league in LEAGUES:
        mask = dataset["League"] == league
        n = int(mask.sum())
        if n == 0:
            continue
        lines.append(f"| {league} | {n} | {correct[mask].mean():.3f} |")

    available_seasons = sorted(dataset["SeasonStartYear"].unique().tolist())
    folds = generate_expanding_season_folds(available_seasons, min_train_seasons=MIN_TRAIN_SEASONS)

    lines += [
        "",
        "### By walk-forward fold (same folds as PR #9's baseline model run)",
        "",
        "| Fold | Validate season | N | Majority acc | Weighted-random acc (expected) | Favorite heuristic acc |",
        "|---|---|---|---|---|---|",
    ]
    for i, fold in enumerate(folds, start=1):
        train_df, validate_df = split_fold(dataset, fold)
        y_train = train_df[TARGET_COLUMN]
        y_validate = validate_df[TARGET_COLUMN].tolist()

        majority = fit_majority_class_baseline(y_train)
        majority_pred = majority.predict(len(validate_df))
        majority_accuracy = accuracy(y_validate, majority_pred)

        train_freqs = y_train.value_counts(normalize=True).to_dict()
        validate_freqs = pd.Series(y_validate).value_counts(normalize=True).to_dict()
        weighted_random_accuracy = expected_weighted_random_accuracy(train_freqs, validate_freqs)

        fold_favorite_pred, _ = opening_favorite_heuristic_predict(validate_df)
        fold_favorite_accuracy = accuracy(y_validate, fold_favorite_pred)

        lines.append(
            f"| {i} | {fold.validate_season} | {len(validate_df)} | {majority_accuracy:.3f} | "
            f"{weighted_random_accuracy:.3f} | {fold_favorite_accuracy:.3f} |"
        )

    lines += [
        "",
        "**Read this section for stability, not just magnitude**: if the favorite heuristic "
        "beats majority-class and the weighted-random baseline consistently across nearly "
        "every league and every fold, that's evidence of a real, broad market pattern. If "
        "it's only strong in a handful of leagues/years, that's a local effect being "
        "averaged into a pooled number that overstates how general it is.",
        "",
    ]
    return lines


def main() -> None:
    cache_dir = REPO_ROOT / "data" / "raw"
    reports_dir = REPO_ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    df = load_dataset(cache_dir)
    dataset = build_diagnostic_dataset(df)
    dataset = apply_long_absence_handling(dataset)
    dataset = drop_cold_start_rows(dataset)

    favorite_pred, _ = opening_favorite_heuristic_predict(dataset)

    lines = [
        "# Phase 1 Diagnostic: Opening Favorite Effect",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Rows (same filtering as PR #9's baseline model run - long-absence handling, "
        f"cold-start drop): {len(dataset)}",
        "",
        "Pure analysis, no model changes. Follow-up to PR #9's WEAK verdict: is the "
        "opening-favorite heuristic's edge over logistic regression a real, stable "
        "market pattern, or an artifact of the target's structure / concentrated in a "
        "few leagues or years / won mostly on near-noise micro-movements?",
        "",
        "**Read this report's word 'edge' as 'wins this classification comparison,' "
        "never as 'profitable betting edge.'** Everything below is about whether the "
        "line's OWN direction of movement is predictable - it says nothing about "
        "entry price, vig/margin, odds availability, account limits, or execution "
        "timing, all of which are required before 'predictable direction' could ever "
        "become 'positive EV' (Phase 2's question, not this one's, and not yet asked "
        "here). A strong, stable pattern in *movement direction* is not the same claim "
        "as a proven betting edge - do not read it as one.",
        "",
    ]
    lines += section_target_distribution(dataset, favorite_pred)
    lines += section_odds_buckets(dataset, favorite_pred)
    lines += section_class_asymmetry(dataset, favorite_pred)
    lines += section_magnitude(dataset, favorite_pred)
    lines += section_baseline_sanity(dataset, favorite_pred)

    report_path = reports_dir / "phase1-diagnostic-favorite-effect-report.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n".join(lines))
    print(f"\nFull report written to {report_path}")


if __name__ == "__main__":
    main()
