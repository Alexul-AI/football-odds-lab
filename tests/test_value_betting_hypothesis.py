import math

from football_odds_lab.analysis.value_betting_hypothesis import compute_edge, select_value_bet


def test_compute_edge_positive_when_market_odds_beat_fair_price():
    # Fair probability implies fair odds of 2.0; market offers 2.2 -> positive EV.
    assert compute_edge(fair_devigged_prob=0.5, market_odds=2.2) > 0


def test_compute_edge_negative_when_market_odds_below_fair_price():
    assert compute_edge(fair_devigged_prob=0.5, market_odds=1.8) < 0


def test_compute_edge_zero_at_exact_fair_price():
    assert math.isclose(compute_edge(fair_devigged_prob=0.5, market_odds=2.0), 0.0, abs_tol=1e-9)


def test_select_value_bet_finds_the_mispriced_side():
    # Pinnacle (fair) close: roughly 45%/27%/27% after devig.
    fair_odds = {"H": 2.10, "D": 3.60, "A": 3.60}
    # Retail best price on Home is generous relative to that fair probability.
    market_odds = {"H": 2.40, "D": 3.50, "A": 3.40}

    bet = select_value_bet(fair_odds, market_odds, actual_result="H")

    assert bet is not None
    assert bet.side == "H"
    assert bet.edge > 0
    assert bet.odds == 2.40


def test_select_value_bet_returns_none_when_no_positive_edge():
    # Retail prices all at or below fair value on every outcome -> no bet.
    fair_odds = {"H": 2.10, "D": 3.60, "A": 3.60}
    market_odds = {"H": 2.00, "D": 3.40, "A": 3.40}

    bet = select_value_bet(fair_odds, market_odds, actual_result="H")

    assert bet is None


def test_select_value_bet_profit_when_won():
    fair_odds = {"H": 2.10, "D": 3.60, "A": 3.60}
    market_odds = {"H": 2.40, "D": 3.50, "A": 3.40}

    bet = select_value_bet(fair_odds, market_odds, actual_result="H", stake=1.0)

    assert bet.won is True
    assert math.isclose(bet.profit, 2.40 - 1.0, abs_tol=1e-9)


def test_select_value_bet_profit_when_lost():
    fair_odds = {"H": 2.10, "D": 3.60, "A": 3.60}
    market_odds = {"H": 2.40, "D": 3.50, "A": 3.40}

    bet = select_value_bet(fair_odds, market_odds, actual_result="A", stake=1.0)

    assert bet.won is False
    assert bet.profit == -1.0
