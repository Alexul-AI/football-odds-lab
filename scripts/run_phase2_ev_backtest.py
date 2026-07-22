"""Phase 2 EV Backtest Runner - computes ROI/CI/sample-size/CLV for the first time.

Usage:
    python scripts/run_phase2_ev_backtest.py

Reads the already-ingested normalized decision-snapshot dataset (PR #16,
reports/phase2-decision-snapshots.csv) and football-data.co.uk's E0 2023-24
Pinnacle closing price (the fair benchmark) - no new API calls, no new
network I/O of any kind. Implements docs/PHASE2_EV_METHODOLOGY.md exactly:
Pinnacle close (devigged) as fair benchmark, candidate price is one named
bookmaker OR a true average (never Max/best-of-many), EV via the existing
tested compute_edge/select_value_bet, all four thresholds (0%/1%/2%/3%)
reported side by side with no post-hoc winner selection, bookmaker role
separation enforced in code (Pinnacle can never be the candidate).

Explicitly NOT included, per the methodology doc's scope: live betting, model
training, threshold optimization, automatic "best bookmaker/threshold"
selection, staking/Kelly sizing, any new API fetch.
"""

import sys
from datetime import datetime, timezone
from itertools import product
from pathlib import Path

import pandas as pd

from football_odds_lab.analysis.ev_backtest import AVG_POLICY, run_ev_backtest_segment
from football_odds_lab.analysis.line_movement_features import parse_match_dates

REPO_ROOT = Path(__file__).resolve().parent.parent
DECISION_OFFSETS_HOURS = (24, 12, 6, 1)
CANDIDATE_POLICIES = (AVG_POLICY, "williamhill")
THRESHOLDS = (0.0, 0.01, 0.02, 0.03)
SIGNIFICANT_CI_LOW_BOUND = 0.0  # a segment counts as "significant positive" if its whole 95% CI is above this


def load_football_data_e0_2324() -> pd.DataFrame:
    df = pd.read_csv(REPO_ROOT / "data" / "raw" / "E0_2324.csv")
    df["Date"] = parse_match_dates(df["Date"])
    return df


def load_decision_snapshots() -> pd.DataFrame:
    path = REPO_ROOT / "reports" / "phase2-decision-snapshots.csv"
    if not path.exists():
        print(
            f"{path} not found - run scripts/run_phase2_decision_snapshot_fetch.py --execute first "
            "(this script reads that data, it does not fetch anything itself).",
            file=sys.stderr,
        )
        sys.exit(1)
    return pd.read_csv(path)


def format_segment_row(seg) -> str:
    if seg.result is None:
        return (
            f"| T-{seg.decision_offset_hours}h | {seg.candidate_policy} | {seg.threshold:.0%} | "
            f"0 | {seg.excluded_missing_fair} | {seg.excluded_missing_candidate} | - | - | - | - | - |"
        )
    r = seg.result
    return (
        f"| T-{seg.decision_offset_hours}h | {seg.candidate_policy} | {seg.threshold:.0%} | "
        f"{r.n_bets} | {seg.excluded_missing_fair} | {seg.excluded_missing_candidate} | "
        f"{r.roi:+.2%} | {r.win_rate:.1%} | {seg.mean_edge_of_placed_bets:+.4f} | "
        f"[{r.ci_95_low:+.2%}, {r.ci_95_high:+.2%}] | {r.p_value:.4f} |"
    )


def main() -> None:
    football_data_df = load_football_data_e0_2324()
    decision_snapshots_df = load_decision_snapshots()

    segments = []
    for offset, policy, threshold in product(DECISION_OFFSETS_HOURS, CANDIDATE_POLICIES, THRESHOLDS):
        segments.append(
            run_ev_backtest_segment(decision_snapshots_df, football_data_df, offset, policy, threshold)
        )

    significant_positive = [
        s for s in segments if s.result is not None and s.result.ci_95_low > SIGNIFICANT_CI_LOW_BOUND
    ]
    n_segments_with_bets = sum(1 for s in segments if s.result is not None)

    if not significant_positive:
        verdict = "NO EDGE"
        verdict_text = (
            "No segment (of {} tested, {} had any bets at all) showed a 95% confidence interval "
            "entirely above zero ROI. Reported as-is - a clean NO EDGE result across the full "
            "threshold/timestamp/policy sweep is a legitimate, useful Phase 2 outcome, not a "
            "pipeline failure, per docs/PHASE2_EV_METHODOLOGY.md's explicit acceptance of this."
        ).format(len(segments), n_segments_with_bets)
    else:
        verdict = "MIXED - SOME SEGMENTS SIGNIFICANT"
        verdict_text = (
            f"{len(significant_positive)} of {len(segments)} segments tested showed a 95% CI "
            "entirely above zero ROI. **Read this with real caution**: 32 segments were tested "
            "at nominal 5% significance, so roughly 1-2 false positives are expected by chance "
            "alone even if there is no real edge anywhere - this is not evidence of a validated "
            "edge, it's a list of segments that might deserve a closer, independent look (e.g. "
            "on a different season), not a recommendation to act on any of them."
        )

    lines = [
        "# Phase 2 EV Backtest Report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Season: E0 2023-24. Offsets: {DECISION_OFFSETS_HOURS}. "
        f"Candidate policies: {CANDIDATE_POLICIES}. Thresholds: {[f'{t:.0%}' for t in THRESHOLDS]}.",
        f"Total segments: {len(segments)} (offsets x policies x thresholds)",
        "",
        "## Verdict",
        "",
        f"**{verdict}**",
        "",
        verdict_text,
        "",
        "**Retrospective research only, not betting advice** - see "
        "docs/PHASE2_EV_METHODOLOGY.md's hard disclaimers: does not model account "
        "limits, slippage, or real execution mechanics.",
        "",
        "## All segments",
        "",
        "| Offset | Policy | Threshold | N bets | Excl. missing fair | Excl. missing candidate | "
        "ROI | Win rate | Mean CLV (edge) | 95% CI | p-value |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    lines.extend(format_segment_row(s) for s in segments)

    lines += [
        "",
        "## Read this honestly",
        "",
        "- No threshold, offset, or bookmaker policy was selected as \"the best\" - every "
        "combination is reported side by side, per the methodology's explicit prohibition "
        "on post-hoc winner selection.",
        "- `avg` and `williamhill` are reported as parallel policies, not compared to pick a "
        "winner - a real difference between them is itself informative (bookmaker-specific "
        "behavior vs a market-wide pattern), not a reason to discard one.",
        "- Pinnacle never appears as a candidate bookmaker in this table - enforced in code "
        "(PinnacleAsCandidateError), not just by convention.",
        "- This is one season, one league. Same standard as every other phase in this repo: "
        "one window is informative, not yet a validated finding.",
    ]

    reports_dir = REPO_ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / "phase2-ev-backtest-report.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n".join(lines))
    print(f"\nFull report written to {report_path}")


if __name__ == "__main__":
    main()
