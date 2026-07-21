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


def compute_movement_target(open_odds: dict[str, float], close_odds: dict[str, float]) -> str:
    """Which outcome (H/D/A) Pinnacle's own devigged probability moved toward the
    most, open to close. Same selection rule as clv_hypothesis.select_bet_and_profit,
    used here as a label instead of a bet."""
    open_probs = dict(zip(OUTCOMES, devig_multiplicative([open_odds[o] for o in OUTCOMES])))
    close_probs = dict(zip(OUTCOMES, devig_multiplicative([close_odds[o] for o in OUTCOMES])))
    edges = {o: clv_edge(open_probs[o], close_probs[o]) for o in OUTCOMES}
    return max(edges, key=edges.get)


def build_targets(df: pd.DataFrame) -> pd.Series:
    """df must contain PSH/PSD/PSA/PSCH/PSCD/PSCA. Returns a Series of H/D/A labels,
    same index as df. This is the only function in the Phase 1 pipeline that reads
    the PSC* columns - callers should drop them immediately after calling this,
    before building the feature matrix."""
    targets = [
        compute_movement_target(
            open_odds={"H": row.PSH, "D": row.PSD, "A": row.PSA},
            close_odds={"H": row.PSCH, "D": row.PSCD, "A": row.PSCA},
        )
        for row in df.itertuples(index=False)
    ]
    return pd.Series(targets, index=df.index, name=TARGET_COLUMN)
