import math

import pandas as pd
import pytest

from football_odds_lab.analysis.ev_candidate_price import (
    PinnacleAsCandidateError,
    resolve_avg_odds,
    resolve_named_bookmaker_odds,
)


def _match_records() -> pd.DataFrame:
    return pd.DataFrame([
        {"bookmaker": "pinnacle", "price_home": 2.00, "price_draw": 3.50, "price_away": 4.00},
        {"bookmaker": "williamhill", "price_home": 2.10, "price_draw": 3.40, "price_away": 3.80},
        {"bookmaker": "betclic", "price_home": 2.20, "price_draw": 3.60, "price_away": 3.90},
    ])


def test_resolve_named_bookmaker_odds_returns_that_books_prices():
    odds = resolve_named_bookmaker_odds(_match_records(), "williamhill")
    assert odds == {"H": 2.10, "D": 3.40, "A": 3.80}


def test_resolve_named_bookmaker_odds_none_when_book_missing():
    odds = resolve_named_bookmaker_odds(_match_records(), "unibet_eu")
    assert odds is None


def test_resolve_named_bookmaker_odds_pinnacle_raises():
    # The critical guard: Pinnacle cannot be the candidate when it's also the
    # fair benchmark elsewhere in the same test.
    with pytest.raises(PinnacleAsCandidateError):
        resolve_named_bookmaker_odds(_match_records(), "pinnacle")


def test_resolve_avg_odds_excludes_pinnacle_and_is_a_true_mean():
    odds = resolve_avg_odds(_match_records())
    # Mean of williamhill (2.10) and betclic (2.20) only - pinnacle excluded.
    assert math.isclose(odds["H"], (2.10 + 2.20) / 2, abs_tol=1e-9)
    assert math.isclose(odds["D"], (3.40 + 3.60) / 2, abs_tol=1e-9)
    assert math.isclose(odds["A"], (3.80 + 3.90) / 2, abs_tol=1e-9)


def test_resolve_avg_odds_is_never_the_max():
    # Explicit negative check: the average must NOT equal the max of the
    # non-Pinnacle books - if it did, this would silently be the Max artifact
    # Phase 0.5 already caught, not a true average.
    odds = resolve_avg_odds(_match_records())
    assert odds["H"] < max(2.10, 2.20)
    assert odds["D"] < max(3.40, 3.60)
    assert odds["A"] < max(3.80, 3.90)


def test_resolve_avg_odds_none_when_only_pinnacle_present():
    only_pinnacle = pd.DataFrame([
        {"bookmaker": "pinnacle", "price_home": 2.00, "price_draw": 3.50, "price_away": 4.00},
    ])
    assert resolve_avg_odds(only_pinnacle) is None


def test_no_max_function_exists_in_this_module():
    # Structural guard, not just a convention: there must be no best-of-many/
    # max resolution function anywhere in this module at all.
    import football_odds_lab.analysis.ev_candidate_price as module

    public_names = [name for name in dir(module) if not name.startswith("_")]
    assert not any("max" in name.lower() for name in public_names)
