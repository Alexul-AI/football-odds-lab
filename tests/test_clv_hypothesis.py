import math

from football_odds_lab.analysis.clv_hypothesis import select_bet_and_profit, summarize_bets


def test_select_bet_picks_side_market_moved_toward():
    # Home price shortens from 2.10 -> 1.90 (market moves toward Home).
    # Draw/Away odds held fixed for this synthetic example.
    open_odds = {"H": 2.10, "D": 3.40, "A": 3.60}
    close_odds = {"H": 1.90, "D": 3.60, "A": 3.90}

    bet = select_bet_and_profit(open_odds, close_odds, actual_result="H")

    assert bet.side == "H"
    assert bet.clv_edge > 0
    assert bet.odds_at_open == 2.10


def test_select_bet_profit_when_won():
    open_odds = {"H": 2.10, "D": 3.40, "A": 3.60}
    close_odds = {"H": 1.90, "D": 3.60, "A": 3.90}

    bet = select_bet_and_profit(open_odds, close_odds, actual_result="H", stake=1.0)

    assert bet.won is True
    assert math.isclose(bet.profit, 2.10 - 1.0, abs_tol=1e-9)


def test_select_bet_profit_when_lost():
    open_odds = {"H": 2.10, "D": 3.40, "A": 3.60}
    close_odds = {"H": 1.90, "D": 3.60, "A": 3.90}

    bet = select_bet_and_profit(open_odds, close_odds, actual_result="A", stake=1.0)

    assert bet.won is False
    assert bet.profit == -1.0


def test_select_bet_respects_custom_stake():
    open_odds = {"H": 2.10, "D": 3.40, "A": 3.60}
    close_odds = {"H": 1.90, "D": 3.60, "A": 3.90}

    bet = select_bet_and_profit(open_odds, close_odds, actual_result="H", stake=10.0)

    assert math.isclose(bet.profit, (2.10 - 1.0) * 10.0, abs_tol=1e-9)


def test_summarize_bets_matches_hand_computed_totals():
    open_odds = {"H": 2.0, "D": 3.0, "A": 4.0}
    close_odds = {"H": 1.8, "D": 3.2, "A": 4.5}  # market moves toward Home

    bets = [
        select_bet_and_profit(open_odds, close_odds, actual_result="H"),  # win: +1.0
        select_bet_and_profit(open_odds, close_odds, actual_result="A"),  # lose: -1.0
    ]

    result = summarize_bets(bets)

    assert result.n_bets == 2
    assert result.total_staked == 2.0
    assert math.isclose(result.total_profit, 0.0, abs_tol=1e-9)
    assert math.isclose(result.win_rate, 0.5, abs_tol=1e-9)
    assert math.isclose(result.mean_profit_per_bet, 0.0, abs_tol=1e-9)
