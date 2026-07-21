# Phase 1 methodology: predicting line movement before it happens

Direct follow-up to `docs/PHASE0_METHODOLOGY.md` and
`docs/PHASE0B_VALUE_BETTING_METHODOLOGY.md`. Both of those found or ruled out
whether a *mechanism* exists (does Pinnacle's line move in an exploitable way, does
a same-time cross-bookmaker gap exist). Phase 1 asks a different, harder question:
can we predict the mechanism **before** it happens, using only information that is
genuinely available at that time - no hindsight.

This document defines the question, the honest feature set, what's forbidden and
why, and the validation approach. It intentionally does not lock in a specific
model/algorithm - that's an implementation decision, made after this design is
agreed, not before.

## The question, precisely

> Predict future Pinnacle open-to-close movement direction using only features
> available at or before the opening snapshot, excluding any feature derived from
> the future closing line.

Target: which 1X2 outcome (H/D/A) Pinnacle's own line moves toward the most between
open and close - the exact same label Phase 0's `select_bet_and_profit` already
computes (`clv_hypothesis.py`), just used here as a prediction **target** instead of
something looked up after the fact.

**This is prediction only, not a profitability test.** A model that predicts
direction well is a necessary input to Phase 2 ("can predicted movement become
positive EV") - it is not itself evidence of a tradeable edge. Don't conflate
"beats the accuracy baseline" with "beats the vig." Those are different bars,
tested in different phases.

## Why "early line movement" is not a Phase 1 feature

An earlier draft of this plan included "early line movement" as a candidate
predictor. It's wrong, and worth stating exactly why so it doesn't get
re-proposed later without remembering the reason: **football-data.co.uk gives
exactly two snapshots per match - opening (`PSH/PSD/PSA`) and closing
(`PSCH/PSCD/PSCA`).** There is no third, intermediate point in time. The
open-to-close delta *is* the target. A feature built from "movement" using only
these two points would either:

- literally be the target itself (tautological, not a real test), or
- require a third snapshot we don't have.

If a future data source provides genuinely timestamped intermediate odds (three or
more snapshots per match), this is worth revisiting. Not with the current schema.

## Honest baseline feature set

All of the following are computable strictly from information available at or
before the opening snapshot for the match being predicted:

- league;
- home/away, encoded via team role;
- opening odds level (`PSH`/`PSD`/`PSA`, the raw prices themselves - a snapshot,
  not a movement);
- opening overround (bookmaker margin at open - see `odds_math.overround`);
- opening implied/devigged probabilities (`odds_math.devig_multiplicative` on the
  opening prices);
- day of week;
- season stage (e.g. matchweek number or fraction of season elapsed);
- rest days per team (days since each team's previous match **in this dataset**);
- match congestion per team (matches played in the last N days - N is an
  implementation parameter, not fixed here);
- rolling team-level historical CLV direction, **strictly lagged** (has the market
  historically tended to move toward or away from this team, computed only from
  that team's matches strictly before the current match date);
- rolling team-level market efficiency/volatility, **strictly lagged** (trailing
  average magnitude of `|clv_edge|` for that team's matches, same causal
  constraint).

### Known limitation: rest days and congestion undercount true fixture load

This dataset only covers the five top-5 domestic leagues - no cup competitions, no
European competitions (Champions League, Europa League, etc.). A club that played a
midweek European away game has real fatigue this dataset can't see: its "rest days"
and "congestion" features, computed only from what's in this dataset, will look
more rested than the team actually is. This is a real, known gap, not something to
silently paper over - if these features end up mattering, it's worth checking
whether a supplementary fixture-list source (even just match dates, not odds) could
close it. Not required to start.

### Known limitation: promotion/relegation produces extreme rest-days outliers

Confirmed empirically once the feature builder was run against the full dataset
(2026-07-21): `home_rest_days` had a max of 3009 days. Real example, not a parsing
bug - Sunderland's last Premier League match in this dataset was 2017-05-21; they
were relegated, spent 8 seasons outside the top-5 leagues (not in this dataset,
same root cause as the fixture-load gap above), and returned for 2025-26, with
their first match back showing a "rest days" value spanning the entire absence.
This is honest given what the feature is actually measuring ("days since this
team's last match *in this dataset*"), not a bug to fix in the feature builder -
but a model consuming this feature raw would treat an 8-year gap the same shape as
a normal 3-10 day gap, which is almost certainly wrong. Handling this (clipping,
winsorizing, or an explicit "newly promoted / returning from an absence" indicator)
is a modeling-stage decision for the walk-forward baseline (PR #7), not something
the feature builder should silently decide on its behalf.

### Known limitation: rolling features need real warm-up

A team's first several appearances in the dataset have thin-to-nonexistent rolling
history - the same class of bug as the RSI/MACD warm-up issue already learned the
hard way in the sibling `ai-trading-agent` project (a rolling stat computed on too
little history isn't "less precise," it's biased or wrong). Any implementation of
the rolling CLV-direction/efficiency features needs to either exclude matches before
a team has enough trailing history, or explicitly flag low-confidence early rows -
not silently compute a rolling average over 1-2 prior matches and treat it the same
as one over 50.

## Explicitly forbidden Phase 1 features

Not "discouraged" - forbidden, because each of these is a direct or indirect leak
of the target:

- `PSCH`/`PSCD`/`PSCA` (the closing line itself) in any form;
- any open-to-close delta, for this match or computed as if it were a feature;
- any feature computed using matches **after** the current match's date (this
  includes getting a rolling-window boundary condition wrong - see the leakage
  test below);
- "early line movement" in any form, per the section above, unless a future data
  source provides genuinely timestamped intermediate odds snapshots.

## Leakage test (required before any result is trusted)

Every rolling/lagged feature must satisfy, and must be tested to satisfy:

> For match M on date D, every rolling feature for both teams must be computed
> only from matches with date < D.

Concretely, once implementation starts: a test that takes a real match, computes
its rolling features, then mutates or removes match data with date >= D and
recomputes - the feature values must be identical. A test that only checks "the
code doesn't crash" or "the number looks plausible" does not satisfy this - it has
to actually prove future data isn't reachable, the same standard already applied to
`autopilotWorker.ts`'s `testDataFilePaths` I/O-seam work in `ai-trading-agent`.

## Validation: walk-forward, not two static windows

Phase 0 and 0.5's two-non-overlapping-windows standard is right for testing a fixed,
pre-specified rule (existence test: does this one rule work or not). Phase 1 is a
genuine forecasting task - a model that gets refit or re-evaluated - so it needs
walk-forward (expanding-window) validation instead:

- train on seasons 2012-13 through 2015-16, validate on 2016-17;
- train on seasons 2012-13 through 2016-17, validate on 2017-18;
- train on seasons 2012-13 through 2017-18, validate on 2018-19;
- ... continue expanding by one season each fold, through the latest available
  season (currently 2025-26).

Each fold's validation season must never influence that fold's training - standard
walk-forward discipline, and the same causal-ordering requirement as the leakage
test above, just applied at the fold level instead of the per-feature level.

## Model progression

Start simple, add complexity only if the simpler thing shows real signal:

1. **Rule-based / majority-class baseline** - e.g. always predict whichever outcome
   the line has historically moved toward most often. This is the bar every later
   model must clear, not just "better than random."
2. **Logistic regression** on the honest feature set above.
3. **Gradient boosting / random forest** - only if (2) already shows real,
   walk-forward-validated signal over (1). Don't reach for a more complex model to
   rescue a baseline that shows nothing - that's the same trap already named in
   `ai-trading-agent`'s history ("complex signal != working signal," learned from
   RSI/MACD).

## Success metrics

- target-direction accuracy vs. the majority-class baseline (not vs. random chance -
  the baseline already has "always guess the modal outcome" for free);
- log loss / Brier score (calibration-sensitive, not just accuracy);
- calibration (do predicted probabilities match observed frequencies, not just rank
  order correctly);
- stability across walk-forward folds and across leagues - one good fold or one
  good league is not a result, matching every other phase's standard in this repo;
- positive out-of-sample CLV, if and when this gets used for actual bet selection
  (Phase 2's question, not Phase 1's, but worth tracking here too since it's cheap
  to compute alongside the classification metrics);
- **no improvement is accepted without a leakage audit first.** A model that
  suddenly looks great is at least as likely to have a leak as to have found real
  signal - check the boring explanation before the exciting one.

## Relationship to later phases

Phase 1 succeeding (real, walk-forward-stable, leakage-audited signal) is a
precondition for Phase 2 (can predicted movement become positive EV after vig) -
not a substitute for it. A good classifier that never gets checked against
real betting economics doesn't tell us anything about edge by itself.
