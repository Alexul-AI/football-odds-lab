"""Shin's-method devig robustness check: re-run Phase 0.5 and Phase 2 with an
alternative devigging method, side by side against the original proportional
(devig_multiplicative) results.

Usage:
    python scripts/run_shin_devig_robustness_check.py

Background: an external review correctly flagged that odds_math.py's
proportional devig doesn't correct for the favorite-longshot bias, unlike
Shin's method - a documented, known limitation, not a new finding. That
review's own suggested Shin's-method code was independently verified against
the primary source (Cain, Law & Peel's closed-form inversion of Shin (1992),
reproduced in Whelan (2024) "On Estimates of Insider Trading in Sports
Betting") and found to have a real bug (missing the pi_i^2/B term) - fixed
properly in odds_math.devig_shin, with its own hand-derived tests.

This script answers the actual question: does correcting for that bias
change Phase 0.5's or Phase 2's null results? Reuses the real orchestration
logic from both phases' own scripts (not reimplemented), swapping only the
devig_fn argument - no new data, no new hypothesis, no model, no betting
simulation. Per this project's threshold-discipline standard, every
segment/window is reported side by side - no post-hoc "best" selection.

Requires the same local cached data as the two scripts it reuses
(data/raw/*.csv for Phase 0.5, reports/phase2-decision-snapshots.csv for
Phase 2) - no new network calls of any kind.
"""

import sys
from datetime import datetime, timezone
from itertools import product
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from football_odds_lab.analysis.odds_math import devig_multiplicative, devig_shin
from run_phase0b_value_betting_test import (
    MARKET_SOURCES,
    WINDOW_SPLIT_YEAR,
    load_dataset as load_phase0b_dataset,
    run_bets as run_phase0b_bets,
)
from run_phase2_ev_backtest import (
    CANDIDATE_POLICIES,
    DECISION_OFFSETS_HOURS,
    THRESHOLDS,
    load_decision_snapshots,
    load_football_data_e0_2324,
)

from football_odds_lab.analysis.betting_stats import summarize_bets
from football_odds_lab.analysis.ev_backtest import run_ev_backtest_segment

REPO_ROOT = Path(__file__).resolve().parent.parent
DEVIG_METHODS = {"proportional": devig_multiplicative, "shin": devig_shin}


def _phase0b_avg_pooled_row(df: pd.DataFrame, devig_fn) -> str:
    market_columns = MARKET_SOURCES["Avg"]
    bets = [b for b in run_phase0b_bets(df, market_columns, devig_fn=devig_fn) if b is not None]
    if not bets:
        return "0 bets"
    result = summarize_bets(bets)
    significant = "yes" if result.p_value < 0.05 else "no"
    return (
        f"{result.n_bets} bets, ROI {result.roi:+.2%}, "
        f"95% CI [{result.ci_95_low:+.4f}, {result.ci_95_high:+.4f}], "
        f"p={result.p_value:.4f}, significant={significant}"
    )


def _phase0b_avg_window_row(df: pd.DataFrame, devig_fn, window_mask: pd.Series) -> str:
    windowed = df[window_mask].reset_index(drop=True)
    return _phase0b_avg_pooled_row(windowed, devig_fn)


def run_phase0b_comparison() -> list[str]:
    df = load_phase0b_dataset(REPO_ROOT / "data" / "raw")
    window_a_mask = df["SeasonStartYear"] < WINDOW_SPLIT_YEAR

    lines = [
        "## Phase 0.5 robustness check (vs Avg closing price - the trustworthy table)",
        "",
        "| Segment | proportional (original) | shin |",
        "|---|---|---|",
    ]
    segments = [
        ("Overall (pooled)", df, None),
        (f"Window A (seasons < {WINDOW_SPLIT_YEAR})", df, window_a_mask),
        (f"Window B (seasons >= {WINDOW_SPLIT_YEAR})", df, ~window_a_mask),
    ]
    for label, data, mask in segments:
        row_data = data if mask is None else data[mask].reset_index(drop=True)
        prop = _phase0b_avg_pooled_row(row_data, devig_multiplicative)
        shin = _phase0b_avg_pooled_row(row_data, devig_shin)
        lines.append(f"| {label} | {prop} | {shin} |")
    lines.append("")
    return lines


def run_phase2_comparison() -> list[str]:
    football_data_df = load_football_data_e0_2324()
    decision_snapshots_df = load_decision_snapshots()

    lines = [
        "## Phase 2 EV backtest robustness check (all 32 segments)",
        "",
        "| Offset | Policy | Threshold | proportional ROI [95% CI] | shin ROI [95% CI] | "
        "Significance changed? |",
        "|---|---|---|---|---|---|",
    ]
    for offset, policy, threshold in product(DECISION_OFFSETS_HOURS, CANDIDATE_POLICIES, THRESHOLDS):
        prop_segment = run_ev_backtest_segment(
            decision_snapshots_df, football_data_df, offset, policy, threshold, devig_fn=devig_multiplicative
        )
        shin_segment = run_ev_backtest_segment(
            decision_snapshots_df, football_data_df, offset, policy, threshold, devig_fn=devig_shin
        )

        def fmt(seg):
            if seg.result is None:
                return "0 bets"
            r = seg.result
            return f"{r.roi:+.2%} [{r.ci_95_low:+.2%}, {r.ci_95_high:+.2%}]"

        prop_significant = prop_segment.result is not None and prop_segment.result.ci_95_low > 0.0
        shin_significant = shin_segment.result is not None and shin_segment.result.ci_95_low > 0.0
        changed = "YES" if prop_significant != shin_significant else "no"

        lines.append(
            f"| T-{offset}h | {policy} | {threshold:.0%} | {fmt(prop_segment)} | {fmt(shin_segment)} | {changed} |"
        )
    lines.append("")
    return lines


def main() -> None:
    reports_dir = REPO_ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Shin's-Method Devig Robustness Check",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "Re-runs Phase 0.5 and Phase 2 with `odds_math.devig_shin` (corrects "
        "favorite-longshot bias) instead of `devig_multiplicative` (proportional, "
        "the original method both phases' published results use), side by side. "
        "No new data, no new hypothesis - a robustness check on the existing "
        "null results, per an external review's correct observation that the "
        "devig method choice was an untested, documented gap.",
        "",
    ]
    lines += run_phase0b_comparison()
    lines += run_phase2_comparison()
    lines += [
        "## Read this honestly",
        "",
        "- Both devig methods are reported side by side for every segment - no "
        "post-hoc selection of whichever looks better, same discipline as every "
        "threshold/timestamp/policy table in this project.",
        "- A 'Significance changed? YES' row means the 95%-CI-above-zero "
        "verdict flipped between methods for that segment - read the actual ROI/CI "
        "numbers before treating that as meaningful; with 32+ segments tested, "
        "some flips are expected by chance alone even with no real effect, same "
        "multiple-comparisons caution as the original Phase 2 report.",
        "- This checks whether the devig METHOD was hiding an edge, not whether a "
        "new signal exists - a clean result either way (edge appears, or doesn't) "
        "answers a narrower question than the original Phase 0-3 research cycle.",
    ]

    report_path = reports_dir / "shin-devig-robustness-check-report.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n".join(lines))
    print(f"\nFull report written to {report_path}")


if __name__ == "__main__":
    main()
