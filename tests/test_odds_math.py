import math

from football_odds_lab.analysis.odds_math import (
    clv_edge,
    devig_multiplicative,
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
