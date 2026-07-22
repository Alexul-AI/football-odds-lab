import math

import pandas as pd
import pytest

from football_odds_lab.analysis.ev_backtest import run_ev_backtest_segment
from football_odds_lab.analysis.ev_candidate_price import PinnacleAsCandidateError


def _football_data_df() -> pd.DataFrame:
    return pd.DataFrame([
        # Fair (Pinnacle close, devigged ~0.4615/0.2308/0.3077 for 2.10/4.20/3.15... use round numbers.
        {"HomeTeam": "Arsenal", "AwayTeam": "Chelsea", "PSCH": 2.00, "PSCD": 3.50, "PSCA": 4.00, "FTR": "H"},
        {"HomeTeam": "Everton", "AwayTeam": "Fulham", "PSCH": 2.00, "PSCD": 3.50, "PSCA": 4.00, "FTR": "A"},
        # Missing fair odds - must be excluded, never silently bet on.
        {"HomeTeam": "Burnley", "AwayTeam": "Luton", "PSCH": None, "PSCD": 3.50, "PSCA": 4.00, "FTR": "H"},
    ])


def _decision_snapshots_df() -> pd.DataFrame:
    return pd.DataFrame([
        # Arsenal vs Chelsea: williamhill offers a generous Home price -> positive EV bet, wins (FTR=H).
        {"home_team": "Arsenal", "away_team": "Chelsea", "decision_offset_hours": 6, "bookmaker": "williamhill",
         "price_home": 2.30, "price_draw": 3.40, "price_away": 3.80},
        {"home_team": "Arsenal", "away_team": "Chelsea", "decision_offset_hours": 6, "bookmaker": "pinnacle",
         "price_home": 2.00, "price_draw": 3.50, "price_away": 4.00},
        # Everton vs Fulham: williamhill offers fair-or-worse prices everywhere -> no bet.
        {"home_team": "Everton", "away_team": "Fulham", "decision_offset_hours": 6, "bookmaker": "williamhill",
         "price_home": 1.90, "price_draw": 3.30, "price_away": 3.70},
        # Burnley vs Luton has snapshot data too, but its match row has no fair odds - must be excluded upstream.
        {"home_team": "Burnley", "away_team": "Luton", "decision_offset_hours": 6, "bookmaker": "williamhill",
         "price_home": 2.50, "price_draw": 3.50, "price_away": 4.50},
    ])


def test_run_ev_backtest_segment_places_expected_bet_and_excludes_missing_fair():
    segment = run_ev_backtest_segment(
        _decision_snapshots_df(), _football_data_df(), offset_hours=6, candidate_policy="williamhill", threshold=0.0
    )

    assert segment.n_matches_total == 3
    assert segment.excluded_missing_fair == 1  # Burnley vs Luton
    assert segment.excluded_missing_candidate == 0
    assert segment.n_bets_placed == 1  # only Arsenal vs Chelsea clears EV>0
    assert segment.result is not None
    assert segment.result.n_bets == 1
    assert segment.result.win_rate == 1.0  # Arsenal won, and Home was the bet


def test_run_ev_backtest_segment_hand_computed_profit():
    segment = run_ev_backtest_segment(
        _decision_snapshots_df(), _football_data_df(), offset_hours=6, candidate_policy="williamhill", threshold=0.0
    )
    # Backed Home at 2.30, won -> profit = 2.30 - 1 = 1.30
    assert math.isclose(segment.result.total_profit, 1.30, abs_tol=1e-9)


def test_run_ev_backtest_segment_higher_threshold_can_yield_zero_bets():
    segment = run_ev_backtest_segment(
        _decision_snapshots_df(), _football_data_df(), offset_hours=6, candidate_policy="williamhill", threshold=0.5
    )
    assert segment.n_bets_placed == 0
    assert segment.result is None  # explicitly None, not a crash - report must handle this


def test_run_ev_backtest_segment_avg_policy_excludes_pinnacle_automatically():
    segment = run_ev_backtest_segment(
        _decision_snapshots_df(), _football_data_df(), offset_hours=6, candidate_policy="avg", threshold=0.0
    )
    # Should run without error - avg policy silently excludes pinnacle's own row from the average.
    assert segment.n_matches_total == 3


def test_run_ev_backtest_segment_pinnacle_as_policy_raises():
    with pytest.raises(PinnacleAsCandidateError):
        run_ev_backtest_segment(
            _decision_snapshots_df(), _football_data_df(), offset_hours=6, candidate_policy="pinnacle", threshold=0.0
        )


def test_run_ev_backtest_segment_missing_candidate_book_excludes_not_crashes():
    segment = run_ev_backtest_segment(
        _decision_snapshots_df(), _football_data_df(), offset_hours=6, candidate_policy="betclic", threshold=0.0
    )
    # betclic never appears in the synthetic snapshot data at all. Burnley vs
    # Luton is excluded earlier for missing FAIR odds (checked first), so only
    # the other 2 matches reach - and fail - candidate resolution.
    assert segment.excluded_missing_fair == 1
    assert segment.excluded_missing_candidate == 2
    assert segment.n_bets_placed == 0
    assert segment.result is None
