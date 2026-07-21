"""Phase 0.5: cross-bookmaker value-betting hypothesis - no look-ahead.

See docs/PHASE0B_VALUE_BETTING_METHODOLOGY.md for the full writeup. Short version:

The Phase 0 CLV test (clv_hypothesis.py) needed the CLOSING line to decide which
side to back at the OPENING price - information that doesn't exist yet at bet time.
This test fixes that: it only ever compares odds from the SAME point in time across
two different bookmakers, so nothing here requires knowing the future.

For each match, treat Pinnacle's closing devigged probability as the best available
estimate of the true probability, and compare it against the best closing price any
tracked retail book offered for the same outcome (`MaxC*` columns). Back the outcome
with the highest positive expected value (fair_prob * market_odds - 1); skip the
match entirely if no outcome clears EV > 0. Zero is the natural break-even point,
not a tuned threshold.
"""

from dataclasses import dataclass

from football_odds_lab.analysis.odds_math import OUTCOMES, devig_multiplicative


def compute_edge(fair_devigged_prob: float, market_odds: float) -> float:
    """Expected value per unit stake if `market_odds` is taken, given `fair_devigged_prob`."""
    return fair_devigged_prob * market_odds - 1.0


@dataclass(frozen=True)
class ValueBet:
    side: str
    edge: float
    odds: float
    won: bool
    profit: float


def select_value_bet(
    fair_odds: dict[str, float],
    market_odds: dict[str, float],
    actual_result: str,
    stake: float = 1.0,
) -> ValueBet | None:
    fair_probs = dict(zip(OUTCOMES, devig_multiplicative([fair_odds[o] for o in OUTCOMES])))
    edges = {o: compute_edge(fair_probs[o], market_odds[o]) for o in OUTCOMES}

    best_side = max(edges, key=edges.get)
    if edges[best_side] <= 0:
        return None

    won = best_side == actual_result
    profit = (market_odds[best_side] - 1.0) * stake if won else -stake

    return ValueBet(side=best_side, edge=edges[best_side], odds=market_odds[best_side], won=won, profit=profit)
