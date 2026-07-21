"""Statistical summary shared by every betting hypothesis test in this repo.

Pure, generic over any bet-result type that has `.won: bool` and `.profit: float`
(structural typing via Protocol) - both `clv_hypothesis.MatchBet` and
`value_betting_hypothesis.ValueBet` satisfy it without inheritance.
"""

from dataclasses import dataclass
from typing import Protocol, Sequence

import numpy as np
from scipy import stats


class BetOutcome(Protocol):
    won: bool
    profit: float


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


def summarize_bets(bets: Sequence[BetOutcome]) -> HypothesisTestResult:
    n = len(bets)
    if n == 0:
        raise ValueError("summarize_bets: cannot summarize zero bets - check for an empty segment first")

    profits = np.array([b.profit for b in bets], dtype=float)
    total_staked = float(n)
    total_profit = float(profits.sum())
    mean_profit = float(profits.mean())

    if n < 2:
        # A single bet has no meaningful variance/CI/significance - NaN is the honest
        # answer, returned deliberately rather than via scipy's own small-sample warnings.
        t_stat, p_value, ci_low, ci_high = float("nan"), float("nan"), float("nan"), float("nan")
    else:
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
