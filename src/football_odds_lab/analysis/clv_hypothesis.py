"""Phase 0 CLV hypothesis: core bet-selection and profit logic.

The hypothesis under test (see docs/PHASE0_METHODOLOGY.md for the full writeup):

For each match, look at how Pinnacle's own devigged 1X2 probabilities moved between
their opening snapshot and closing snapshot. Back the outcome the line moved toward
the most, at the OPENING price, flat 1-unit stake, no threshold/filter. Test whether
the resulting profit series has a mean significantly different from zero across a
large historical sample.

This is a single, pre-specified, unfiltered rule on purpose - no threshold sweeping,
no per-league tuning before the first honest look at results (same discipline as
ai-trading-agent's "no p-hacking, report the miss too" standard).

Important limitation, not a footnote: this test uses the closing line to pick which
side to bet at the opening price - information that, by definition, doesn't exist yet
at the time you'd actually place that bet. It answers "does inefficiency between
Pinnacle's open and close exist and would perfect foresight of its direction have
been profitable net of vig" - a necessary precondition for any real-time strategy,
not a live-tradeable strategy by itself. A live strategy still needs an independent
signal that predicts the move before it happens.
"""

from dataclasses import dataclass

import numpy as np
from scipy import stats

from football_odds_lab.analysis.odds_math import clv_edge, devig_multiplicative

OUTCOMES = ("H", "D", "A")


@dataclass(frozen=True)
class MatchBet:
    side: str
    clv_edge: float
    odds_at_open: float
    won: bool
    profit: float


def select_bet_and_profit(
    open_odds: dict[str, float],
    close_odds: dict[str, float],
    actual_result: str,
    stake: float = 1.0,
) -> MatchBet:
    open_probs = dict(zip(OUTCOMES, devig_multiplicative([open_odds[o] for o in OUTCOMES])))
    close_probs = dict(zip(OUTCOMES, devig_multiplicative([close_odds[o] for o in OUTCOMES])))
    edges = {o: clv_edge(open_probs[o], close_probs[o]) for o in OUTCOMES}

    side = max(edges, key=edges.get)
    won = side == actual_result
    profit = (open_odds[side] - 1.0) * stake if won else -stake

    return MatchBet(side=side, clv_edge=edges[side], odds_at_open=open_odds[side], won=won, profit=profit)


@dataclass(frozen=True)
class HypothesisTestResult:
    n_bets: int
    total_staked: float
    total_profit: float
    roi: float
    win_rate: float
    mean_profit_per_bet: float
    t_statistic: float
    p_value: float
    ci_95_low: float
    ci_95_high: float


def summarize_bets(bets: list[MatchBet]) -> HypothesisTestResult:
    profits = np.array([b.profit for b in bets], dtype=float)
    n = len(profits)
    total_staked = float(n)
    total_profit = float(profits.sum())
    mean_profit = float(profits.mean())

    t_stat, p_value = stats.ttest_1samp(profits, popmean=0.0)
    sem = stats.sem(profits)
    ci_low, ci_high = stats.t.interval(0.95, df=n - 1, loc=mean_profit, scale=sem)

    return HypothesisTestResult(
        n_bets=n,
        total_staked=total_staked,
        total_profit=total_profit,
        roi=total_profit / total_staked,
        win_rate=float(np.mean([b.won for b in bets])),
        mean_profit_per_bet=mean_profit,
        t_statistic=float(t_stat),
        p_value=float(p_value),
        ci_95_low=float(ci_low),
        ci_95_high=float(ci_high),
    )
