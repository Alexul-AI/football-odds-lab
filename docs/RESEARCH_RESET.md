# Research Reset: End of Cycle 1 (Odds-Only Research)

Status: reset checkpoint - synthesizes closed work, does not open new work
Last updated: 2026-07-22

## Why this document exists

Four hypotheses have now been tested end-to-end (Phase 0 through Phase 2), all
using the same data family: historical odds (football-data.co.uk + The Odds
API). This is the natural point to stop and look at the four results
together, rather than reach for a bigger model on the same data because
that's the next line in a to-do list. Per `docs/PRD.md` §13: "ambitious in
data collection, conservative in conclusions." This document is the
conservative half of that, after Cycle 1.

Nothing here is a new hypothesis or new code - it summarizes what has already
shipped, and formalizes the selection bar for what comes next.

## Cycle 1: four hypotheses, one data family

| Phase | Question | Result | Live-tradeable? |
|---|---|---|---|
| 0 | Does Pinnacle's own open→close movement predict outcomes, picking the side with the closing line? | Positive, significant, both windows (+3.3% / +3.8% ROI) | No - needs the closing line to pick the opening bet, a look-ahead |
| 0.5 | At the same timestamp, does Pinnacle's fair (devigged) price beat retail closing price? | Null - `Avg` policy found no significant edge in either window; `Max` policy was a selection-bias artifact, caught and corrected | Yes in principle (no look-ahead) - but no edge found |
| 1 | Can pre-match features (odds level, overround, schedule, rolling CLV) predict which way the line will move? | WEAK - logistic regression beat majority-class but not the opening-favorite heuristic | N/A - direction ≠ EV, that's Phase 2's question |
| 2 | Does an early retail price vs. Pinnacle's eventual close clear a positive-EV threshold, honest timestamps, no Max artifact? | NO EDGE - 0 of 32 segments had a 95% CI entirely above zero ROI | Yes in principle (no look-ahead, honest timestamps) - but no edge found |

Full detail lives in each phase's own doc - this table doesn't replace them:
[`PHASE0_METHODOLOGY.md`](PHASE0_METHODOLOGY.md),
[`PHASE0B_VALUE_BETTING_METHODOLOGY.md`](PHASE0B_VALUE_BETTING_METHODOLOGY.md),
[`PHASE1_CONCLUSION.md`](PHASE1_CONCLUSION.md),
[`PHASE2_EV_METHODOLOGY.md`](PHASE2_EV_METHODOLOGY.md).

## Honest reading

- The one genuinely positive, statistically significant finding (Phase 0) is
  not live-tradeable by construction - it needs to know the future close to
  pick the current bet.
- Every test that removed that look-ahead (0.5, and 2 directly; 1 indirectly,
  by testing direction rather than profitability) came back null or weak.
- Phase 1's diagnostic gives a mechanism for why: the market's opening price
  already encodes most of the predictable pre-match signal - the favorite
  effect is real, broad, and monotonic, just not *new* information once the
  opening odds are already known.
- This is not "the project failed." Four hypotheses tested, three killed
  cleanly, one real (but non-actionable) mechanism found, with none of the
  artifacts that would make these numbers untrustworthy: Max-selection-bias
  caught and fixed (Phase 0.5), look-ahead caught and named (Phase 0),
  BST/UTC timestamp bug caught before any budget was spent (Phase 2),
  threshold/timestamp cherry-picking structurally prevented throughout. Per
  `docs/PRD.md` §10, "weak ideas are killed early" is a *success* metric here,
  not a failure one.

## What this does NOT mean

- It does not mean football odds markets have zero inefficiency anywhere - it
  means this specific data family (historical 1X2 opening/closing prices, the
  comparison methods tried so far) has been reasonably exhausted for this
  project's current tools.
- It does not mean these four results are a final verdict. Coverage so far is
  mostly one league (EPL for Phase 2 specifically) and, for Phase 2, one
  season - `docs/PRD.md`'s own standing rule throughout has been "one window
  is informative, not a validated finding."

## What NOT to do next

Extending modeling on the *same* odds-only data - XGBoost, neural nets, more
threshold/hyperparameter search on Phase 1's or Phase 2's existing features -
is not a good next step. Reasoning, not just a rule: Phase 1's diagnostic
already showed the opening-favorite effect explains most of what a stronger
model could find in this feature family, so a more flexible model on the same
inputs is very likely to just be a better-fit repackaging of the same
opening-odds signal, not new information. `docs/PRD.md` §1's original vision
already separates "market movement research" (stages 1-2, now closed for this
cycle) from "external signal research" (stage 3, not yet started) - that's
the axis this project hasn't tried, not model complexity.

## Phase 3: External Signal Discovery (formalized)

This was already named as stage 3 in `docs/PRD.md` §1's original vision, and
candidates already exist in §4.2-§4.4, §12, and
[`PHASE2_DATA_SOURCE_SELECTION.md`](PHASE2_DATA_SOURCE_SELECTION.md) - this
section formalizes the selection bar given Cycle 1's actual result. It does
not invent new candidates from nothing.

### What "counts" as a Phase 3 candidate

A source must satisfy all of:

1. **Timestamped** - a real publication/availability time, not just
   current-state.
2. **Available before market movement** - exists, in principle, before the
   relevant odds have already adjusted. A source that only confirms minutes
   before kickoff (e.g. some lineup confirmations) is a weak candidate on
   this axis even if everything else about it is clean.
3. **Historical, or prospectively collectible starting now** - either a real
   backtestable archive exists (verify before assuming -
   `PHASE2_DATA_SOURCE_SELECTION.md` already found this varies a lot by
   source, and even by league/season within one source), or the source suits
   Phase 4's paper journal instead (`docs/PRD.md` §4.3's "data availability
   caveat" already flags that most news/social-type sources fall in this
   bucket, not the historical-archive one - that changes the validation path,
   it doesn't disqualify the source).
4. **Matchable** - ties to a specific fixture/team without fragile
   fuzzy-matching, same entity-resolution discipline already used in
   `entity_matching.py`'s explicit mapping dict, not heuristic string
   similarity.
5. **Legal/ethical, per `docs/PRD.md` §6** - public source, sane terms of
   service, and specifically: never the player/coach's family or personal
   circle, full stop, not a matter of degree.

### Candidate shortlist, re-ranked after Cycle 1

`PHASE2_DATA_SOURCE_SELECTION.md`'s candidate #3 (timestamped odds snapshots)
was this cycle's actual pick - it's now a *tried, closed* candidate (NO
EDGE), not an open one. That promotes its own original secondary
recommendation:

1. ~~**Team news / injuries / suspensions** (was candidate #1)~~ - **spike
   run, closed 2026-07-22**: `docs/PHASE3_INJURY_SPIKE_PLAN.md`'s "Result"
   section. API-Football's `/injuries` endpoint has real EPL 2023-24
   coverage (3,853 records, 1 request), but every record's only date field
   is the match's own `fixture.date` - not a publication/update timestamp.
   Reads structurally as a matchday absence report, not a point-in-time
   news feed - the same timing-risk profile already flagged for candidate
   #2 (lineups) below, not what this candidate's original hypothesis
   needed. **Verdict: reject-for-backtest, not yet confirmed even for
   Phase 4's paper journal** (that needs its own small forward-looking
   check - does a record populate before its own fixture's kickoff, or
   only at/near it). It originally promoted exchange liquidity to the top
   *open* candidate; that candidate has since also been closed below.
2. ~~**Exchange liquidity / order-book depth**~~ - **spike blocked before
   Stage A even started, closed 2026-07-23**:
   [`docs/PHASE3_BETFAIR_EXCHANGE_SPIKE_PLAN.md`](PHASE3_BETFAIR_EXCHANGE_SPIKE_PLAN.md)'s
   "Result" section. The user hit a hard geographic-access restriction
   attempting to reach `betfair.com` at all (`Region: IL`) - Betfair's
   Historical Data service requires a real Betfair account, and the account
   itself isn't reachable from this jurisdiction, consistent with
   `CLAUDE.md`'s already-documented Israeli sports-betting-monopoly context.
   **Verdict: REJECT** (access-level, not data-quality) - no workaround was
   attempted or considered, since circumventing a regulated betting
   operator's country restriction is out of scope for this project on
   ethical grounds, independent of the data-quality question this spike
   never got to ask. Promotes the remaining two candidates below.
3. **Lower-tier / cup / non-league fixture broadening** (cheap, safe path) -
   now the top remaining candidate, by elimination rather than by strength:
   not a new signal type, a broader universe where markets may be less
   efficient. Honest framing: this tests a different axis (market efficiency
   by league tier) than genuine external-signal discovery, and should be
   labeled as such if pursued, not conflated with it.
4. **Lineups, extended fixture-congestion** (was candidates #2, #4) - stay
   ranked below injuries for the same reasons as the original evaluation:
   real timing risk for lineups, weak incremental-signal case for extending
   congestion tracking. Still viable as secondary enrichment once a primary
   candidate is chosen, not as a first pick.
5. **Press conferences / social signals** - stay deferred, per the original
   evaluation and `docs/PRD.md` §14's explicit gate. Not reconsidered by this
   document.

**Two of the top two candidates are now closed** (injuries: reject-for-
backtest; exchange liquidity: reject-jurisdiction) - worth pausing to decide
deliberately whether candidate #3 (lower-tier/cup broadening, an honest
"different axis" rather than a new signal) is actually worth pursuing next,
or whether Phase 3's active search should pause here for now, rather than
mechanically working down the list.

### What this section does not do

Does not pick a final Phase 3 source, does not commit any spend, does not
write a methodology doc, does not write code. The next concrete step, if and
when picked up, is the same shape as every prior phase's opening move: a
small, cheap verification spike (a handful of real API calls) confirming
whether the injury-coverage historical-depth question is actually real,
before any design work - exactly what `PHASE2_DATA_SOURCE_SELECTION.md`
already recommended before this reset.

## What does not change

- No live or paper betting execution by any code in this repo.
- No personalized betting advice.
- Family/personal-circle monitoring stays fully out of scope
  (`docs/PRD.md` §6).
- Workflow: `claude/<feature>` branches, PR review, explicit merge approval
  before every merge.
- Null results get reported exactly as prominently as positive ones
  (`docs/PRD.md` §7 checklist).
