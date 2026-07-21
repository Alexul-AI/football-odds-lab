# Phase 1 baseline model plan (PR #7 scope)

Direct follow-up to `docs/PHASE1_LINE_MOVEMENT_SIGNAL_METHODOLOGY.md` (the
question/feature spec) and `src/football_odds_lab/analysis/line_movement_features.py`
(PR #6, the leakage-safe feature builder). This document locks the scope for the
first modeling PR before writing the code, same discipline as every other phase in
this repo - agree the design, then implement it, not the other way around.

**Deliberately tight scope.** No new external data, no news/social signals, no
multiple models fighting for attention, no threshold tuning for ROI. One honest
walk-forward baseline, reported straight - including if it's null.

## 1. Target

Multiclass: which outcome (`H`/`D`/`A`) has the largest Pinnacle open→close devigged
probability increase - the exact same label `clv_hypothesis.select_bet_and_profit`
already computes internally as `side`, used here as a prediction target instead of
something looked up after the fact. Binary/one-vs-rest framings are a possible
follow-up, not this PR.

## 2. Features

Only what PR #6 already built (`line_movement_features.FEATURE_COLUMNS`) - no
additions. Before fitting anything, this PR must resolve the two open items from
[issue #7](https://github.com/Alexul-AI/football-odds-lab/issues/7):

- **Long-absence handling**: `rest_days` values from a promotion/relegation gap
  (confirmed real, e.g. Sunderland's 3009-day case) need either clipping/winsorizing
  at a reasonable ceiling, or an explicit `home_long_absence_from_dataset` /
  `away_long_absence_from_dataset` boolean feature - decide and document which,
  don't leave both on the table.
- **Model input policy**: scaling for logistic regression (features are on very
  different scales - `opening_prob_*` is 0-1, `rest_days`/rolling-CLV magnitudes are
  not), and what happens to cold-start `None`/`NaN` rows (a team's first appearance
  with no rolling history) - impute, or exclude those rows from training entirely.
  Given `line_movement_features.py`'s own documented warm-up limitation, excluding
  is the more defensible default; imputing needs a specific justification if chosen
  instead.

## 3. Baselines

In order, each one the bar the next has to clear:

1. **Majority-class baseline** - always predict whichever outcome the line has
   historically moved toward most often in the training fold.
2. **Opening-favorite heuristic** - a simple rule using only `opening_prob_home/
   draw/away` (e.g. predict movement toward the current favorite, or away from it -
   whichever direction is actually implied by the rule; the point is a one-line
   rule with no learned parameters, not a model).
3. **Logistic regression** on the resolved feature set from §2.

No random forest / gradient boosting in this PR - only if logistic regression
already shows real, walk-forward-stable signal over both baselines above.

## 4. Validation: expanding walk-forward by season

No random split. Folds validate on one season at a time, with all prior seasons as
training data, expanding forward - same causal-ordering discipline as the leakage
tests in PR #6, just applied at the fold level. Concrete fold sequence over the
actual available range (`SeasonStartYear` 2012-2025, i.e. seasons 2012-13 through
2025-26):

| Fold | Train (SeasonStartYear) | Validate (SeasonStartYear) |
|---|---|---|
| 1 | 2012-2015 | 2016 |
| 2 | 2012-2016 | 2017 |
| 3 | 2012-2017 | 2018 |
| 4 | 2012-2018 | 2019 |
| 5 | 2012-2019 | 2020 |
| 6 | 2012-2020 | 2021 |
| 7 | 2012-2021 | 2022 |
| 8 | 2012-2022 | 2023 |
| 9 | 2012-2023 | 2024 |
| 10 | 2012-2024 | 2025 |

Ten folds, minimum 4-season training window for fold 1 (a deliberate floor, not
just "whatever's left" - gives the rolling CLV/volatility features real history to
build on before the first validation fold, consistent with PR #6's warm-up
limitation). Report metrics per fold AND pooled across all folds - a model that
does well pooled but is unstable fold-to-fold is not the same result as one that's
consistently decent, and both numbers should be visible, not just the pooled one.

## 5. Metrics

- accuracy vs. majority-class baseline (not vs. random chance - the baseline
  already gets "always guess the modal outcome" for free);
- log loss;
- Brier score (one-vs-rest per outcome, or multiclass Brier - pick one and state
  which, don't silently mix);
- calibration notes (do predicted probabilities roughly match observed
  frequencies, at least qualitatively - a full reliability diagram is not required
  for this first pass);
- a simulated CLV-selection report (if the model's predicted side had been bet at
  the opening price, using the same profit accounting as `clv_hypothesis.py`) -
  **explicitly secondary**, reported for context, not the headline number. Phase 1
  is about prediction accuracy; whether prediction translates to profitable
  betting is Phase 2's question, not this PR's.

## 6. Acceptance criterion

If logistic regression does not beat both baselines out-of-sample (pooled AND
across a real majority of the ten folds, not just in aggregate) - report that as
the result and stop. No threshold tuning, no feature reshuffling, no narrative
rescue to make a null result look better. A clean null here is a legitimate,
useful Phase 1 outcome, same standard already applied to Phase 0.5's `Avg`-based
test.

## Main guardrail

The model has to prove it's predicting *future* line movement, not just
re-discovering favorite/home-advantage/team-history artifacts that happen to
correlate with movement direction for boring structural reasons. Concretely: report
logistic regression's lift over the **opening-favorite heuristic** specifically,
not only over the majority-class baseline. If logistic regression barely beats the
one-line heuristic despite using ten more features, that's a sign the extra
features (rest days, congestion, rolling CLV/volatility) aren't adding real
information - worth stating plainly, not glossing over because the accuracy number
alone looks fine.

## Out of scope for this PR (explicitly)

- any new data source, news, or social signal;
- more than the three baselines above;
- ROI/threshold optimization;
- Phase 2 (predicted-movement-to-EV) work of any kind.
