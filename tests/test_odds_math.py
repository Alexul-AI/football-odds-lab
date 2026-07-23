import math

from football_odds_lab.analysis.odds_math import (
    clv_edge,
    devig_multiplicative,
    devig_shin,
    implied_probabilities,
    overround,
)


def test_implied_probabilities_fair_coin():
    assert implied_probabilities([2.0, 2.0]) == [0.5, 0.5]


def test_overround_positive_for_realistic_market():
    # Typical retail 1X2 market: ~5-8% overround
    home, draw, away = 2.10, 3.40, 3.60
    assert 0.03 < overround([home, draw, away]) < 0.10


def test_overround_zero_for_fair_odds():
    assert math.isclose(overround([2.0, 2.0]), 0.0, abs_tol=1e-9)


def test_devig_multiplicative_sums_to_one():
    probs = devig_multiplicative([2.10, 3.40, 3.60])
    assert math.isclose(sum(probs), 1.0, abs_tol=1e-9)


def test_devig_multiplicative_preserves_fair_odds():
    assert devig_multiplicative([2.0, 2.0]) == [0.5, 0.5]


def test_clv_edge_positive_when_market_moves_toward_your_side():
    # You bet a selection devigged at 40%; by close the market devigs it at 45%
    # -> the market moved toward you, you beat the closing line.
    assert math.isclose(clv_edge(devigged_prob_at_bet=0.40, devigged_prob_at_close=0.45), 0.05, abs_tol=1e-9)


def test_clv_edge_negative_when_market_moves_away():
    assert math.isclose(clv_edge(devigged_prob_at_bet=0.45, devigged_prob_at_close=0.40), -0.05, abs_tol=1e-9)


def test_clv_edge_zero_when_odds_unchanged():
    assert clv_edge(devigged_prob_at_bet=0.33, devigged_prob_at_close=0.33) == 0.0


# Real market example used throughout the PR that added devig_shin - a heavy
# favorite market: [1.2, 6.0, 15.0]. Real overround: sum(1/odds) = 1.0667 (6.67%).
_SHIN_TEST_ODDS = [1.2, 6.0, 15.0]


def test_devig_shin_sums_to_one():
    probs = devig_shin(_SHIN_TEST_ODDS)
    assert math.isclose(sum(probs), 1.0, abs_tol=1e-6)


def test_devig_shin_favorite_probability_exceeds_proportional():
    # Shin's method corrects the favorite-longshot bias: the favorite's true
    # probability should be HIGHER than the naive proportional devig gives it.
    shin_probs = devig_shin(_SHIN_TEST_ODDS)
    proportional_probs = devig_multiplicative(_SHIN_TEST_ODDS)
    assert shin_probs[0] > proportional_probs[0]


def test_devig_shin_longshot_probability_below_proportional():
    # ...and the longshot's true probability should be LOWER than proportional.
    shin_probs = devig_shin(_SHIN_TEST_ODDS)
    proportional_probs = devig_multiplicative(_SHIN_TEST_ODDS)
    assert shin_probs[2] < proportional_probs[2]


def test_devig_shin_preserves_fair_odds():
    # No overround (book_sum == 1.0) -> falls back to proportional, same as
    # devig_multiplicative would give, since Shin's z has nothing to correct.
    assert devig_shin([2.0, 2.0]) == [0.5, 0.5]


def test_devig_shin_matches_hand_derived_values():
    # Hand-derived via the closed-form p_i = [sqrt(z^2 + 4(1-z)*pi_i^2/B) - z] / (2(1-z)),
    # solved for z numerically (z ~ 0.0354 for this market) - cross-checked against
    # the PR's own manual derivation, not just re-deriving the same code path.
    probs = devig_shin(_SHIN_TEST_ODDS)
    assert math.isclose(probs[0], 0.803, abs_tol=0.005)
    assert math.isclose(probs[1], 0.147, abs_tol=0.005)
    assert math.isclose(probs[2], 0.050, abs_tol=0.005)
