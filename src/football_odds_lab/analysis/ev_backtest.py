"""Phase 2 EV backtest: ties the already-ingested decision-snapshot dataset,
Pinnacle's closing price (fair benchmark), and value_betting_hypothesis's
existing select_value_bet/betting_stats.summarize_bets together.

See docs/PHASE2_EV_METHODOLOGY.md - this module computes ROI/CI/sample-size
per (decision offset, candidate policy, threshold) segment. Missing fair
(Pinnacle close) or missing candidate price for a match are both explicit
exclusions, counted and reported - never silently treated as "no bet" via a
fabricated price.
"""

from dataclasses import dataclass

import pandas as pd

from football_odds_lab.analysis.betting_stats import HypothesisTestResult, summarize_bets
from football_odds_lab.analysis.ev_candidate_price import resolve_avg_odds, resolve_named_bookmaker_odds
from football_odds_lab.analysis.odds_math import devig_multiplicative
from football_odds_lab.analysis.value_betting_hypothesis import DevigFn, ValueBet, select_value_bet

AVG_POLICY = "avg"


@dataclass(frozen=True)
class EVBacktestSegment:
    decision_offset_hours: int
    candidate_policy: str
    threshold: float
    n_matches_total: int
    excluded_missing_fair: int
    excluded_missing_candidate: int
    n_bets_placed: int
    result: HypothesisTestResult | None
    mean_edge_of_placed_bets: float | None


def _resolve_candidate(match_records: pd.DataFrame, policy: str) -> dict[str, float] | None:
    if policy == AVG_POLICY:
        return resolve_avg_odds(match_records)
    return resolve_named_bookmaker_odds(match_records, policy)


def run_ev_backtest_segment(
    decision_snapshots_df: pd.DataFrame,
    football_data_df: pd.DataFrame,
    offset_hours: int,
    candidate_policy: str,
    threshold: float,
    devig_fn: DevigFn = devig_multiplicative,
) -> EVBacktestSegment:
    """football_data_df must have HomeTeam/AwayTeam/PSCH/PSCD/PSCA/FTR.
    decision_snapshots_df is the normalized long-format dataset from
    scripts/run_phase2_decision_snapshot_fetch.py.

    devig_fn defaults to devig_multiplicative (Phase 2's original, still-
    canonical result, unchanged). Passing odds_math.devig_shin instead re-
    runs this segment as a favorite-longshot-bias-corrected robustness check."""
    offset_snapshots = decision_snapshots_df[decision_snapshots_df["decision_offset_hours"] == offset_hours]

    bets: list[ValueBet] = []
    excluded_missing_fair = 0
    excluded_missing_candidate = 0

    for row in football_data_df.itertuples(index=False):
        if pd.isna(row.PSCH) or pd.isna(row.PSCD) or pd.isna(row.PSCA):
            excluded_missing_fair += 1
            continue
        fair_odds = {"H": row.PSCH, "D": row.PSCD, "A": row.PSCA}

        match_records = offset_snapshots[
            (offset_snapshots["home_team"] == row.HomeTeam) & (offset_snapshots["away_team"] == row.AwayTeam)
        ]
        candidate_odds = _resolve_candidate(match_records, candidate_policy)
        if candidate_odds is None:
            excluded_missing_candidate += 1
            continue

        bet = select_value_bet(
            fair_odds, candidate_odds, actual_result=row.FTR, min_edge=threshold, devig_fn=devig_fn
        )
        if bet is not None:
            bets.append(bet)

    result = summarize_bets(bets) if bets else None
    mean_edge = sum(b.edge for b in bets) / len(bets) if bets else None

    return EVBacktestSegment(
        decision_offset_hours=offset_hours,
        candidate_policy=candidate_policy,
        threshold=threshold,
        n_matches_total=len(football_data_df),
        excluded_missing_fair=excluded_missing_fair,
        excluded_missing_candidate=excluded_missing_candidate,
        n_bets_placed=len(bets),
        result=result,
        mean_edge_of_placed_bets=mean_edge,
    )
