import math

import pytest

from football_odds_lab.analysis.betting_stats import summarize_bets
from football_odds_lab.analysis.clv_hypothesis import MatchBet


def _bet(profit: float, won: bool) -> MatchBet:
    return MatchBet(side="H", clv_edge=0.0, odds_at_open=2.0, won=won, profit=profit)


def test_summarize_bets_raises_on_empty_list():
    with pytest.raises(ValueError, match="zero bets"):
        summarize_bets([])


def test_summarize_bets_single_bet_has_nan_significance_not_a_crash():
    result = summarize_bets([_bet(profit=1.0, won=True)])

    assert result.n_bets == 1
    assert result.total_profit == 1.0
    assert result.roi == 1.0
    assert math.isnan(result.p_value)
    assert math.isnan(result.t_statistic)
    assert math.isnan(result.ci_95_low)
    assert math.isnan(result.ci_95_high)


def test_summarize_bets_two_bets_still_computes_real_stats():
    result = summarize_bets([_bet(profit=1.0, won=True), _bet(profit=-1.0, won=False)])

    assert result.n_bets == 2
    assert not math.isnan(result.p_value)
    assert not math.isnan(result.ci_95_low)
