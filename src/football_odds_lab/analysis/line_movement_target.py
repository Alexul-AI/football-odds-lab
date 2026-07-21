"""Phase 1 target builder - the ONLY module allowed to read PSCH/PSCD/PSCA.

See docs/PHASE1_BASELINE_MODEL_PLAN.md section 1-2: the closing line is required
to compute the target label (that's what's being predicted) but must never reach
the feature matrix. Keeping that read confined to this one small module, with no
other module in the Phase 1 pipeline importing PSCH/PSCD/PSCA at all, makes the
boundary easy to audit instead of just easy to state.
"""

import pandas as pd

from football_odds_lab.analysis.odds_math import OUTCOMES, clv_edge, devig_multiplicative

TARGET_COLUMN = "movement_target"
TARGET_MAGNITUDE_COLUMN = "movement_magnitude"


def compute_movement_edges(open_odds: dict[str, float], close_odds: dict[str, float]) -> dict[str, float]:
    """clv_edge for all three outcomes, open to close - the shared computation the
    label and magnitude functions below both build on."""
    open_probs = dict(zip(OUTCOMES, devig_multiplicative([open_odds[o] for o in OUTCOMES])))
    close_probs = dict(zip(OUTCOMES, devig_multiplicative([close_odds[o] for o in OUTCOMES])))
    return {o: clv_edge(open_probs[o], close_probs[o]) for o in OUTCOMES}


def compute_movement_target(open_odds: dict[str, float], close_odds: dict[str, float]) -> str:
    """Which outcome (H/D/A) Pinnacle's own devigged probability moved toward the
    most, open to close. Same selection rule as clv_hypothesis.select_bet_and_profit,
    used here as a label instead of a bet."""
    edges = compute_movement_edges(open_odds, close_odds)
    return max(edges, key=edges.get)


def compute_movement_magnitude(open_odds: dict[str, float], close_odds: dict[str, float]) -> float:
    """The clv_edge of the target side specifically - how big the winning move
    was, not just its direction. A match where the line barely crept toward H and
    one where it swung hard toward H both get target='H', but very different
    magnitudes - useful for checking whether a heuristic is winning on real,
    substantial moves or on near-noise micro-movements."""
    edges = compute_movement_edges(open_odds, close_odds)
    return edges[max(edges, key=edges.get)]


def build_targets(df: pd.DataFrame) -> pd.Series:
    """df must contain PSH/PSD/PSA/PSCH/PSCD/PSCA. Returns a Series of H/D/A labels,
    same index as df. This is one of only two functions in the Phase 1 pipeline
    that read the PSC* columns (the other is build_target_magnitudes below) -
    callers should drop them immediately after calling this, before building the
    feature matrix."""
    targets = [
        compute_movement_target(
            open_odds={"H": row.PSH, "D": row.PSD, "A": row.PSA},
            close_odds={"H": row.PSCH, "D": row.PSCD, "A": row.PSCA},
        )
        for row in df.itertuples(index=False)
    ]
    return pd.Series(targets, index=df.index, name=TARGET_COLUMN)


def build_target_magnitudes(df: pd.DataFrame) -> pd.Series:
    """Same PSC*-column requirement and same "drop them right after" rule as
    build_targets. Diagnostic use only (see the Phase 1 favorite-effect
    diagnostic) - not part of the feature matrix, not part of the baseline
    model's training/scoring path."""
    magnitudes = [
        compute_movement_magnitude(
            open_odds={"H": row.PSH, "D": row.PSD, "A": row.PSA},
            close_odds={"H": row.PSCH, "D": row.PSCD, "A": row.PSCA},
        )
        for row in df.itertuples(index=False)
    ]
    return pd.Series(magnitudes, index=df.index, name=TARGET_MAGNITUDE_COLUMN)
