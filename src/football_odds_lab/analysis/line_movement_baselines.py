"""Phase 1 baselines: majority-class, opening-favorite heuristic, logistic regression.

See docs/PHASE1_BASELINE_MODEL_PLAN.md section 3 - in this exact order, each one
the bar the next has to clear. No random forest / gradient boosting here - that's
explicitly out of scope for this PR (see the plan doc's acceptance criterion).
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from football_odds_lab.analysis.odds_math import OUTCOMES


@dataclass
class MajorityClassBaseline:
    class_probabilities: dict[str, float]

    def predict_proba(self, n_rows: int) -> np.ndarray:
        row = [self.class_probabilities[o] for o in OUTCOMES]
        return np.tile(row, (n_rows, 1))

    def predict(self, n_rows: int) -> list[str]:
        majority = max(self.class_probabilities, key=self.class_probabilities.get)
        return [majority] * n_rows


def fit_majority_class_baseline(train_targets: pd.Series) -> MajorityClassBaseline:
    counts = train_targets.value_counts(normalize=True)
    class_probabilities = {o: float(counts.get(o, 0.0)) for o in OUTCOMES}
    return MajorityClassBaseline(class_probabilities=class_probabilities)


def opening_favorite_heuristic_predict(df: pd.DataFrame) -> tuple[list[str], np.ndarray]:
    """No fitting, no learned parameters: predicts the market keeps moving toward
    whichever side is already the opening favorite (highest opening_prob_*).

    Returns (hard predictions, a probability matrix that puts all mass on the
    predicted class) - the all-or-nothing "probabilities" let this be scored with
    the same log-loss/Brier machinery as the other two baselines, even though it
    isn't a real probabilistic model; expect it to score poorly on log loss for
    exactly that reason, that's expected and not a bug.
    """
    probs_matrix = df[["opening_prob_home", "opening_prob_draw", "opening_prob_away"]].to_numpy()
    favorite_index = probs_matrix.argmax(axis=1)  # column order matches OUTCOMES: 0=H, 1=D, 2=A
    predictions = [OUTCOMES[i] for i in favorite_index]

    soft = np.zeros((len(df), len(OUTCOMES)))
    soft[np.arange(len(df)), favorite_index] = 1.0
    return predictions, soft


@dataclass
class LogisticRegressionBaseline:
    model: LogisticRegression

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        raw = self.model.predict_proba(X)
        # sklearn orders classes_ alphabetically (A, D, H) - reorder to this
        # project's consistent OUTCOMES order (H, D, A) so every baseline's output
        # lines up column-for-column.
        reorder = [list(self.model.classes_).index(o) for o in OUTCOMES]
        return raw[:, reorder]

    def predict(self, X: pd.DataFrame) -> list[str]:
        proba = self.predict_proba(X)
        return [OUTCOMES[i] for i in proba.argmax(axis=1)]


def fit_logistic_regression_baseline(X_train: pd.DataFrame, y_train: pd.Series) -> LogisticRegressionBaseline:
    model = LogisticRegression(max_iter=1000)
    model.fit(X_train, y_train)
    return LogisticRegressionBaseline(model=model)
