"""Pure odds-math primitives: implied probability, overround, devigging, CLV edge.

No I/O here on purpose — keeps this testable and reusable from any data source
or script, same convention as `ai-trading-agent`'s pure decision-logic modules.
"""

from collections.abc import Sequence


def implied_probabilities(decimal_odds: Sequence[float]) -> list[float]:
    return [1.0 / odds for odds in decimal_odds]


def overround(decimal_odds: Sequence[float]) -> float:
    """Bookmaker margin baked into a full market's odds (e.g. 1X2). 0.05 = 5% overround."""
    return sum(implied_probabilities(decimal_odds)) - 1.0


def devig_multiplicative(decimal_odds: Sequence[float]) -> list[float]:
    """Proportional devig: normalizes implied probabilities to sum to 1.

    Simplest devigging method. Doesn't correct for favorite-longshot bias the way
    Shin's method does — a documented limitation, not implemented here yet.
    """
    raw = implied_probabilities(decimal_odds)
    total = sum(raw)
    return [p / total for p in raw]


def clv_edge(devigged_prob_at_bet: float, devigged_prob_at_close: float) -> float:
    """Closing Line Value, in probability terms, for one selection.

    Positive means the closing (sharper) market ended up assessing this outcome
    as MORE likely than the price you could have gotten implied — i.e. you beat
    the closing line on this selection. Negative means the opposite.
    """
    return devigged_prob_at_close - devigged_prob_at_bet
