"""Pure odds-math primitives: implied probability, overround, devigging, CLV edge.

No I/O here on purpose — keeps this testable and reusable from any data source
or script, same convention as `ai-trading-agent`'s pure decision-logic modules.
"""

from collections.abc import Sequence

from scipy.optimize import bisect

OUTCOMES = ("H", "D", "A")


def implied_probabilities(decimal_odds: Sequence[float]) -> list[float]:
    return [1.0 / odds for odds in decimal_odds]


def overround(decimal_odds: Sequence[float]) -> float:
    """Bookmaker margin baked into a full market's odds (e.g. 1X2). 0.05 = 5% overround."""
    return sum(implied_probabilities(decimal_odds)) - 1.0


def devig_multiplicative(decimal_odds: Sequence[float]) -> list[float]:
    """Proportional devig: normalizes implied probabilities to sum to 1.

    Simplest devigging method. Doesn't correct for favorite-longshot bias the way
    Shin's method does — see devig_shin below.
    """
    raw = implied_probabilities(decimal_odds)
    total = sum(raw)
    return [p / total for p in raw]


def devig_shin(decimal_odds: Sequence[float], xtol: float = 1e-12) -> list[float]:
    """Shin's method devig - corrects for favorite-longshot bias.

    Closed-form inversion of Shin's (1992) insider-trading model, derived by
    Cain, Law & Peel (1997, 2001):

        p_i = [sqrt(z^2 + 4(1-z) * pi_i^2 / B) - z] / (2(1-z))

    where pi_i = 1/odds_i (raw implied probability) and B = sum(pi_i) (the
    book's overround-inclusive total). z (the estimated insider-trading
    proportion) is solved for by finding the root where sum(p_i) == 1.

    Verified against the closed-form derivation in Whelan (2024), "On
    Estimates of Insider Trading in Sports Betting" (eqs. 1-10, deriving this
    from Shin's original profit-maximization model), cross-checked against
    the independently-documented closed form used by the R `implied`
    package (Jullien et al.) - both agree on the pi_i^2/B term. This is not
    an approximation someone might plausibly misremember as just `pi_i` -
    that specific mistake was caught in review before this function existed
    (see the PR that added this function for the worked-through arithmetic
    counterexample) and produces materially different, wrong probabilities,
    not a harmless rescaling.

    Falls back to devig_multiplicative if there's no real overround
    (book_sum <= 1.0, e.g. arbitrage or exactly fair odds) - Shin's model
    needs positive overround for z to be meaningful.
    """
    raw = implied_probabilities(decimal_odds)
    book_sum = sum(raw)

    if book_sum <= 1.0:
        return [p / book_sum for p in raw]

    def prob_given_z(z: float, pi: float) -> float:
        return (((z**2 + 4 * (1 - z) * pi**2 / book_sum) ** 0.5) - z) / (2 * (1 - z))

    def sum_minus_one(z: float) -> float:
        return sum(prob_given_z(z, pi) for pi in raw) - 1.0

    z = bisect(sum_minus_one, 0.0, 1.0 - 1e-9, xtol=xtol)
    return [prob_given_z(z, pi) for pi in raw]


def clv_edge(devigged_prob_at_bet: float, devigged_prob_at_close: float) -> float:
    """Closing Line Value, in probability terms, for one selection.

    Positive means the closing (sharper) market ended up assessing this outcome
    as MORE likely than the price you could have gotten implied — i.e. you beat
    the closing line on this selection. Negative means the opposite.
    """
    return devigged_prob_at_close - devigged_prob_at_bet
