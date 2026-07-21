# Phase 0 methodology: the CLV hypothesis test

This document is the single source of truth for what the Phase 0 test actually does,
so results in `reports/phase0-clv-report.md` (local only, gitignored) can be read
correctly without re-deriving the design from the code each time.

## Why CLV, and why this test specifically

Closing Line Value (CLV) - whether you can consistently get a better price than the
eventual closing line - is a standard proxy for skill in sports betting research: the
closing line, especially from a sharp book like Pinnacle, is generally the most
efficient price available, so beating it consistently correlates with genuine edge.

Before building any model, agent, or data pipeline, this project's own methodology
(see `CLAUDE.md`) requires a cheap, honest test of ONE hypothesis using only
historical odds + results - no separate prediction model needed yet. The CLV
mechanism gives exactly that: it can be tested using only two odds snapshots per
match (Pinnacle open, Pinnacle close) plus the actual result.

## Data schema (verified empirically 2026-07-20, not assumed from memory)

Source: [football-data.co.uk](https://www.football-data.co.uk), CSV per league/season
at `https://www.football-data.co.uk/mmz4281/{season}/{league}.csv`.

- `PSH` / `PSD` / `PSA` - Pinnacle decimal odds (Home/Draw/Away) at football-data.co.uk's
  earlier snapshot.
- `PSCH` / `PSCD` / `PSCA` - Pinnacle decimal odds at closing (their "C" suffix
  convention, applied uniformly across every bookmaker column in the file).
- `FTR` - actual full-time result: `H` (home win), `D` (draw), `A` (away win).

Confirmed present, for all five top-5 leagues (`E0`/`SP1`/`D1`/`I1`/`F1`), starting
from the **2012-13 season** onward (checked back to 2010-11, where these columns do
not exist yet - pre-2012-13 files use different, non-Pinnacle bookmaker columns with
no opening/closing distinction at all, not usable for this test).

## The hypothesis, precisely

For every match with complete `PSH/PSD/PSA/PSCH/PSCD/PSCA/FTR` data:

1. Devig both the opening and closing Pinnacle 1X2 prices (proportional/multiplicative
   devig - see `football_odds_lab.analysis.odds_math.devig_multiplicative`).
2. For each of the three outcomes, compute `clv_edge = devigged_close_prob - devigged_open_prob`.
3. Back the outcome with the single largest `clv_edge` (the side the market moved
   toward the most), at the **opening** decimal price, flat 1-unit stake. No minimum
   `clv_edge` threshold, no per-league or per-window tuning - one rule, applied
   everywhere, decided before looking at results.
4. Profit = `odds_at_open - 1` if that side won, else `-1`.

Test: is the mean profit per bet significantly different from zero (one-sample
t-test), pooled across the full sample and separately across two non-overlapping
time windows (seasons before vs. from 2019-20) and per league, for context.

## What this test can and cannot tell us

**Can:** answer whether there is *any* exploitable gap between Pinnacle's opening and
closing 1X2 prices at all, net of their own vig, across a large sample (thousands of
matches, two independent multi-season windows) - a necessary precondition for any
CLV-based strategy to be worth pursuing further.

**Cannot:** be traded live as-is. Step 3 uses the closing price to decide which side
to back at the opening price - the closing price doesn't exist yet at the time you'd
actually place that bet. A positive result here means the *mechanism* (early-money
inefficiency relative to Pinnacle's own close) is real and profitable in principle;
it does **not** mean we have a way to predict, in real time, which direction the line
will move before it moves. That would be a separate, harder problem for a later
phase, contingent on this test succeeding first.

## Reading the result honestly

Same standard as `ai-trading-agent`'s regime-filter/ATR-stop findings: a real,
actionable result needs the pooled number AND both independent windows to agree in
sign and be statistically significant - not just the most convenient-looking subset
of the table. One positive window and one negative/flat window is "inconclusive,"
not "confirmed," and should be reported as such, not narrated around.

## Known limitations of this first pass

- **Vig-inclusive stake, no bankroll/Kelly modeling.** Flat 1-unit stakes only - this
  is a statistical existence test, not a bankroll simulation. Kelly sizing is a later
  question, contingent on this test succeeding.
- **1X2 market only.** Over/under and Asian handicap columns exist in the same files
  (`P>2.5`/`PC>2.5`, `PAHH`/`PCAHH`, etc.) but are out of scope for this first pass.
- **No transaction costs beyond the vig itself** (e.g. no account-limiting risk modeled
  here - see `CLAUDE.md`'s note that a consistently winning account can be limited or
  closed, a real structural risk not captured by a backtest).
- **Multiple rows in the same results table (pooled/window/per-league) is itself a
  multiple-comparisons situation.** The p-values shown are each individually valid for
  their own segment, not corrected for testing several segments at once - treat the
  per-league breakdown as context, not as N independent chances to find significance.
