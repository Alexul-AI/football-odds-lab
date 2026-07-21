# Phase 1 Conclusion

Status: concluded 2026-07-21

## Finding

Opening odds already encode most of the available pre-match signal for
predicting Pinnacle's own future line movement. Additional schedule/rolling
features (rest days, congestion, rolling team-level CLV direction and
market efficiency) did not demonstrably improve on the market-implied
favorite alone.

## Evidence

- Walk-forward logistic regression beat majority-class but not the
  opening-favorite heuristic (PR #9, WEAK verdict).
- The favorite effect itself is real and broad: monotonic with favorite
  strength, consistent across all 5 leagues and all 10 walk-forward folds,
  won on larger-than-average moves, not noise (PR #10 diagnostic).

## What this does NOT claim

This is a statement about *predictability of direction*, not a proven
betting edge. Vig, entry price, odds availability, account limits, and
execution timing are all still unaddressed (Phase 2).

## Implication for next steps

Adding more schedule/rolling-derived features to the same feature family
is not expected to help further without new evidence otherwise. The next
logical move is either (a) Phase 2 - test whether the *existing* favorite
signal converts to positive EV net of vig, before adding any new features,
or (b) a genuinely different feature family (external signals per the PRD's
Phase 1 candidate list), not more of the same kind.
