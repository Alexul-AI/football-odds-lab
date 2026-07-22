"""Candidate-price resolution for the Phase 2 EV backtest.

Structurally prevents the two failure modes flagged in review:

1. Pinnacle used as both the fair benchmark AND the candidate bookmaker in the
   same primary test - resolve_named_bookmaker_odds raises if asked for
   Pinnacle, rather than silently returning it.
2. A Max/best-of-many candidate price - there is deliberately no such function
   in this module at all. Only a named single bookmaker or a true average
   across bookmakers are implemented; a max is not a missing feature, it's an
   intentional omission (see docs/PHASE2_EV_METHODOLOGY.md's Max-artifact
   guardrail, already caught once for real in Phase 0.5).

See docs/PHASE2_EV_METHODOLOGY.md's "Candidate price" and "Bookmaker role
separation" sections.
"""

import pandas as pd

PINNACLE_BOOKMAKER_KEY = "pinnacle"


class PinnacleAsCandidateError(ValueError):
    """Raised when code attempts to use Pinnacle as the candidate bookmaker in
    the primary EV test. Pinnacle's close is the fair benchmark - it cannot
    also be the candidate being evaluated against itself in the same test
    (that would just be Phase 0's mechanism again, not a test of retail-book
    behavior). A Pinnacle-as-candidate comparison is only valid as a separate,
    explicitly labeled diagnostic - never through this function.
    """


def resolve_named_bookmaker_odds(match_records: pd.DataFrame, bookmaker: str) -> dict[str, float] | None:
    """match_records: the subset of the normalized decision-snapshot dataset
    for one (match, decision_offset) pair - one row per bookmaker. Returns
    None if this bookmaker has no row for this match/offset (missing, not an
    error - callers must exclude, never silently substitute another book).
    """
    if bookmaker == PINNACLE_BOOKMAKER_KEY:
        raise PinnacleAsCandidateError(
            f"'{PINNACLE_BOOKMAKER_KEY}' cannot be used as the candidate bookmaker here - "
            "see PinnacleAsCandidateError's docstring."
        )
    rows = match_records[match_records["bookmaker"] == bookmaker]
    if len(rows) == 0:
        return None
    row = rows.iloc[0]
    return {"H": float(row["price_home"]), "D": float(row["price_draw"]), "A": float(row["price_away"])}


def resolve_avg_odds(match_records: pd.DataFrame) -> dict[str, float] | None:
    """True mean price across every non-Pinnacle bookmaker present for this
    match/offset - never a max. Returns None if no non-Pinnacle bookmaker has
    a row (nothing to average)."""
    non_pinnacle = match_records[match_records["bookmaker"] != PINNACLE_BOOKMAKER_KEY]
    if len(non_pinnacle) == 0:
        return None
    return {
        "H": float(non_pinnacle["price_home"].mean()),
        "D": float(non_pinnacle["price_draw"].mean()),
        "A": float(non_pinnacle["price_away"].mean()),
    }
