# Phase 2 EV Methodology

Status: methodology only - no code, no new API calls, no betting simulation,
no live betting, no recommendation to bet
Last updated: 2026-07-21

## Core question

> If, at some decision timestamp before a match, a bookmaker's offered price is
> higher than the "fair probability" estimated via Pinnacle's later close, does
> that give a positive ROI net of vig and realistic constraints?

This is retrospective research into whether a mechanism exists - not a live
strategy, not betting advice. See "Hard disclaimers" below; that boundary is
load-bearing, not a footnote.

## Lineage - this is not a new, independent mechanism

Phase 2's question is a synthesis of two things this project has already
tested separately, not a fresh hypothesis invented from nothing:

- **Phase 0** (`docs/PHASE0_METHODOLOGY.md`) found that Pinnacle's own
  open-to-close movement is real and predictable *in hindsight* - a genuine,
  broad, statistically significant effect across multiple windows.
- **Phase 0.5** (`docs/PHASE0B_VALUE_BETTING_METHODOLOGY.md`) found that
  comparing Pinnacle's close against a retail book's price at the SAME moment
  in time showed no significant edge, once corrected for a selection-bias
  artifact in how "best price" was computed.

Phase 2's question combines both: does a retail book's EARLY price (decision
timestamp, well before kickoff) lag behind where Pinnacle's OWN price will
eventually land (its close)? That's a real, different question from either
prior phase - a "soft book is slow to catch up to where the sharp market ends
up" hypothesis - but it is built on both, and should be read as such, not as
an unrelated new direction.

## Definitions

### Decision timestamps

Test **multiple** offsets before kickoff, not one: `T-24h`, `T-12h`, `T-6h`,
`T-1h`. Report all four separately - do not average them into one number or
pick "the best one" after seeing results (see "Threshold discipline" below;
the same discipline applies to timestamp choice).

### Fair probability

Pinnacle's closing price, devigged (`odds_math.devig_multiplicative`) - same
convention as every prior phase. **Retrospective evaluation target only.**
Pinnacle's close does not exist at decision time and must never be treated as
a live feature - it answers "was this decision good, in hindsight," not "what
should I decide right now." Exactly the same limitation Phase 0's CLV test
already documented; repeated here because it's the single easiest thing to
get wrong when writing the actual backtest code.

### Candidate price - the Max-artifact guardrail

The offered price at the decision timestamp must come from **one specific,
named bookmaker, or from `Avg` (the average across tracked books)** - never a
silent "best price available across several books" (`Max`-style). Phase 0.5
already found and had to correct for exactly this: combining the best price
per outcome across several books mechanically inflates apparent value even
with zero real edge, because taking a maximum over several noisy quotes tends
to beat any single reference almost by construction. That correction is not
optional here - it's required from the start, not something to rediscover
after a suspiciously good first result.

### Bookmaker role separation

If Pinnacle's close is the fair-value benchmark, **Pinnacle's own decision-time
price must not also be the candidate price in the same primary EV test.**
Comparing Pinnacle against itself (early vs. late) is Phase 0's mechanism
again, not a new test of retail-book behavior - it would silently blend two
different questions into one number. Pinnacle-as-candidate is fine as a
**separate, clearly labeled diagnostic baseline** (answers "how much of any
effect is Pinnacle's own known movement vs. something specific to retail
books"), never merged into the primary result.

### Nearest snapshot rule

For a given decision timestamp `T_decision`, use the snapshot whose own
`timestamp` is the **latest one at or before `T_decision`** - never the
nearest snapshot overall, and never one after `T_decision`, even if it happens
to be closer in absolute time. A snapshot fetched after the decision point is
information that didn't exist yet at decision time; using it is exactly the
same class of leakage the Phase 1 feature builder's tests exist to catch,
just at the snapshot-selection level instead of the per-feature level. If no
snapshot exists within a defined staleness tolerance before `T_decision`
(proposed: 48 hours - wide enough to tolerate this project's sampling gaps,
narrow enough that "48 hours stale" isn't silently treated as "current"),
exclude that match/timestamp combination from the backtest rather than using
a too-stale price and calling it representative.

## EV formula - reuse, don't reinvent

```
EV = offered_odds * fair_probability - 1
```

This is exactly `football_odds_lab.analysis.value_betting_hypothesis.compute_edge`,
already implemented and tested in Phase 0.5. The implementation PR must import
and reuse it, not write a second copy of the same formula.

## Threshold discipline

Report results at **`EV > 0%`, `> 1%`, `> 2%`, and `> 3%`** as separate rows in
the same table - do not select one threshold as "the" result after looking at
which one performs best. Same standard already applied to every prior phase
in this repo (Phase 0.5's "zero is the natural break-even point, not a tuned
threshold"; Phase 1's "no threshold tuning for ROI" acceptance criterion).
Picking a threshold post-hoc from a swept table is p-hacking with extra steps.

## Request budget reality

A full first pass - all 4 decision timestamps, the full E0 2023-24 season
(~380 matches), 1 region/1 market per request - costs roughly
`380 x 4 x 10 = 15,200 credits`. That's within the $30/month/20,000-credit
plan for one month, but leaves little headroom for anything else that month,
and is a meaningfully larger spend than the spike's 190 credits.

**Recommendation for the implementation PR: start with ONE decision
timestamp** (proposed: `T-6h`, a reasonable middle point) for the first real
result - roughly `380 x 10 = 3,800` credits, comparable in spirit to how
small the source spike itself was kept. Expand to the other three timestamps
in a follow-up only if the first result is actually worth pursuing further -
same "smallest sufficient step" discipline used for Phase 1's baseline model
(majority -> heuristic -> logistic regression, not all three orthogonal
questions asked in parallel with maximum expense.)

## Backtest outputs

For each decision timestamp x threshold combination:

- number of bets (how many matches cleared that EV threshold);
- ROI;
- hit rate;
- average EV at bet time;
- realized closing-line value (compare the bet's price against Pinnacle's
  close, same accounting as `clv_hypothesis.py`);
- 95% confidence interval on ROI (same one-sample-t approach as
  `betting_stats.summarize_bets`, reused, not reinvented);
- per-league and per-bookmaker breakdown.

**Same caveat as every prior phase's per-segment table**: per-league/
per-bookmaker rows are for context, not for picking whichever segment happened
to look best - small-N segments have correspondingly wide confidence
intervals and little power, exactly the same reading discipline already
established for Phase 0's per-league table and Phase 1's per-fold table.

## Hard disclaimers

- **Not betting advice.** This project does not, and will not, tell the user
  to place a bet - see `CLAUDE.md`'s hard boundaries.
- **Retrospective research, not a live strategy.** Positive backtested ROI
  here does not mean a live bettor could have captured it - see the next
  point.
- **Does not model**: bookmaker limits or account restrictions (see
  `CLAUDE.md`'s note that a consistently winning account can be limited or
  closed - not a backtest-visible risk), slippage (the price actually
  available at execution time may differ from the recorded snapshot price),
  or real execution mechanics (manual betting takes real time; the "decision
  timestamp" price may not be gettable in practice by the time a human acts
  on it).
- **A result of "no edge" is a fully legitimate, useful outcome** - same
  standard as Phase 0.5's null result and Phase 1's WEAK verdict. This
  methodology is written so that a null result is exactly as easy to report
  as a positive one, not something the pipeline struggles to express cleanly.

## Out of scope for this PR

- Any code.
- Any new API calls (the request budget above is a plan, not something
  executed here).
- Any betting simulation.
- Any live betting or paper-betting infrastructure.
- Any recommendation to bet, on any specific match or in general.

## Ingestion result (2026-07-21): 100% coverage, all four offsets

The decision-snapshot ingestion PR (`scripts/run_phase2_decision_snapshot_fetch.py`)
is done, ahead of the "start with one timestamp" recommendation above - the
real dry-run estimate (856 unique requests after deduplicating shared kickoff
slots, 8,560 credits) came in well under the 15,200-credit cap even for all
four offsets at once, so there was no need to phase it further. Confirmed and
approved before spending, per this project's standing rule on real financial/
quota spend.

Result: **100% coverage** on T-24h/T-12h/T-6h/T-1h (380/380 matches each, zero
missing). 24,338 normalized long-format rows (every bookmaker present, not
just Pinnacle) written locally. Zero EV/ROI/hit-rate computed - purely
ingestion, exactly per this doc's scope. Caught one real, significant bug
along the way, before any budget was spent: football-data.co.uk's kickoff
`Time` column is UK local time (BST-aware), not UTC - naively treating it as
UTC would have silently misaligned every BST-period match's decision
timestamps by exactly one hour. Fixed with a real timezone-aware conversion,
verified against real data from both sources.

## EV Backtest result (2026-07-21): NO EDGE

`scripts/run_phase2_ev_backtest.py` reads the already-ingested normalized
dataset - no new API calls, no network I/O at all. Ran all 4 decision offsets
x 2 candidate policies (`avg`, `williamhill`) x 4 thresholds (0/1/2/3%) = 32
segments, every one reported side by side per the threshold-discipline rule
above.

**Result: NO EDGE.** None of the 32 segments showed a 95% confidence interval
entirely above zero ROI - point estimates ranged roughly +12% to -22% with
wide, always-zero-crossing intervals, sample sizes 41-240 bets per segment.
No systematic pattern by offset, policy, or threshold. Pinnacle never
appeared as a candidate bookmaker (enforced in code, `PinnacleAsCandidateError`);
no Max/best-of-many candidate price existed anywhere in the pipeline
(structurally absent, not just avoided).

**Read together with the rest of this project's history**: this is the third
null/weak-or-null result out of Phase 0's four hypothesis tests so far (Phase
0.5 null, Phase 1 WEAK/opening-favorite-dominant, now this) against Phase 0's
one genuinely positive-and-robust finding (the temporal CLV effect itself,
which remains not-live-tradeable). Consistent with `PHASE1_CONCLUSION.md`'s
reading: opening/closing prices in this market look close to efficient once
look-ahead is removed, and simple cross-bookmaker timing gaps don't appear to
survive contact with real statistical testing on this one season. One season,
one league - informative, not yet a final verdict on the whole approach.

## Robustness check (2026-07-23): Shin's method devig

Same background as `docs/PHASE0B_VALUE_BETTING_METHODOLOGY.md`'s equivalent
section - an external review correctly flagged the proportional-devig
favorite-longshot-bias gap (already documented, not a new finding), and its
own suggested Shin's-method code was found to have a real formula bug on
verification against the primary source, fixed properly in
`odds_math.devig_shin` before use here.

`scripts/run_shin_devig_robustness_check.py` re-ran all 32 EV backtest
segments with `devig_shin` instead of `devig_multiplicative`, side by side,
same threshold-discipline standard as the original table (every segment
reported, no post-hoc selection). **Result: no change to the NO EDGE
verdict.** Point estimates shifted, sometimes substantially and toward more
positive ROI (e.g. T-1h/williamhill/1%: -11.20% -> +24.36%), but **not one
of the 32 segments' significance verdict flipped** - every 95% CI still
crosses zero under Shin's method, same as under proportional. The devig
method choice was not hiding a real edge in this data. Full 32-row
comparison table in the robustness-check report (gitignored, local only,
same convention as every other phase's report).
