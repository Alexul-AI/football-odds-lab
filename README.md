# football-odds-lab

A disciplined research lab that tested a narrow, concrete hypothesis - is
there an exploitable edge in football 1X2 value-betting, using only public
odds data - through four separate sub-hypotheses, and reports what happened
honestly: none of them found an edge that survives real statistical
scrutiny. **Analytics only - no live or paper betting is placed by any code
in this repository**, and never will be.

## TL;DR

This project set out to find a value-betting edge and, through four
increasingly rigorous tests plus a robustness check on the math itself,
consistently failed to find one that survives contact with real evidence -
on the specific data tested (EPL-heavy, 1X2 market, ~2012-2026 depending on
the phase). That's not a failed project. It's what a disciplined research
process is supposed to produce when an easy edge doesn't exist: weak ideas
killed cleanly, one at a time, with the reasoning and the null results
documented as prominently as a positive result would have been. See
[`docs/RESEARCH_RESET.md`](docs/RESEARCH_RESET.md) for the full synthesis -
this README is the short version.

## The journey

### Phase 0 → 0.5: chasing the same-time value bet, and the look-ahead trap

**Phase 0** asked the simplest version of the question: does Pinnacle's own
opening-to-closing price movement predict outcomes profitably? Both
non-overlapping historical windows came back positive and statistically
significant (+3.3%/+3.8% ROI) - a real, repeatable pattern. But the test
needs to know the closing line to decide which side to back at the opening
price - information that doesn't exist yet at bet time. Interesting
mechanism, not a live strategy.

**Phase 0.5** removed that look-ahead directly: compare Pinnacle's closing
fair price against a retail book's closing price at the *same* moment in
time - no future knowledge required. First pass looked promising, until it
turned out to be a selection-bias artifact: taking the best ("Max") price
across several noisy retail quotes mechanically manufactures apparent value
even with zero real mispricing anywhere. Corrected to a true average
("Avg") price across books, the result was null in both windows. See
[`docs/PHASE0_METHODOLOGY.md`](docs/PHASE0_METHODOLOGY.md) and
[`docs/PHASE0B_VALUE_BETTING_METHODOLOGY.md`](docs/PHASE0B_VALUE_BETTING_METHODOLOGY.md).

### Phase 1 → 2: walk-forward prediction, honest EV, and a robustness check on the math

**Phase 1** asked a harder question: can pre-match features predict which
way the closing line will move, without any information from the future? A
leakage-safe walk-forward model (majority-class → opening-favorite heuristic
→ logistic regression) came back WEAK - the model beat a naive baseline but
never beat "just back whoever the market already favors." A follow-up
diagnostic confirmed the favorite effect is real and broad (monotonic with
favorite strength, consistent across 5 leagues and 10 walk-forward folds),
not a fluke - meaning opening odds already encode most of the predictable
pre-match signal. See
[`docs/PHASE1_LINE_MOVEMENT_SIGNAL_METHODOLOGY.md`](docs/PHASE1_LINE_MOVEMENT_SIGNAL_METHODOLOGY.md)
and [`docs/PHASE1_CONCLUSION.md`](docs/PHASE1_CONCLUSION.md).

**Phase 2** asked the question that actually matters for profitability: does
an early retail price, compared honestly against Pinnacle's eventual close
(no Max-selection artifact, four pre-declared decision timestamps, four
pre-declared EV thresholds, all reported side by side, no post-hoc
cherry-picking), clear a real, positive expected value? Across all 32 tested
segments: **NO EDGE** - every 95% confidence interval crossed zero. See
[`docs/PHASE2_EV_METHODOLOGY.md`](docs/PHASE2_EV_METHODOLOGY.md).

An external review of this repository correctly flagged a real, if already-
documented, gap: the devigging method used throughout (proportional) doesn't
correct for the well-known favorite-longshot bias the way Shin's (1992)
method does. Its own suggested implementation of Shin's method was checked
against the primary source before being trusted - and found to have a real
formula bug (a missing squared term) that would have silently produced
wrong probabilities. Fixed properly and re-run as a robustness check across
Phase 0.5 and all 32 of Phase 2's segments: point estimates shifted,
sometimes substantially, but **not one segment's significance verdict
changed**. The devig method wasn't hiding an edge either.

### Phase 3: the graveyard - two external data candidates, closed cleanly

With the odds-only data family reasonably exhausted, Phase 3 asked whether a
genuinely external signal - timestamped, available before market movement,
historical or prospectively collectible, matchable, legal/ethical - could
add anything opening odds don't already encode.

- **Team news/injuries (API-Football)**: real EPL 2023-24 coverage exists,
  confirmed in one API request. But every injury record's only date field is
  the *match's* own kickoff date, not a publication/update timestamp - no
  way to establish what was actually knowable at any pre-match decision
  point. Closed:
  [`reject-for-backtest-but-viable-for-paper-journal`](docs/PHASE3_INJURY_SPIKE_PLAN.md).
- **Exchange liquidity/order-book depth (Betfair)**: never got past the
  first step. The account required for historical data access was blocked
  by Betfair's own geographic restriction before it could even be
  registered, consistent with this project's documented legal context
  (state-monopoly sports betting in the researcher's jurisdiction). No
  workaround was attempted or considered - circumventing a regulated
  betting operator's country restriction for a research project is out of
  scope on ethical grounds, independent of whatever the data would have
  shown. Closed: [`REJECT`](docs/PHASE3_BETFAIR_EXCHANGE_SPIKE_PLAN.md).

Both closures are treated as first-class, legitimate results, not
disappointments - see [`docs/RESEARCH_RESET.md`](docs/RESEARCH_RESET.md) for
the full candidate shortlist and why the remaining candidates (lower-tier/
cup broadening, lineups, deferred press-conference/social signals) weren't
pursued further.

## Engineering standards

- **142 tests, all green, CI on every PR** - concentrated on the pure
  decision logic (devigging, EV, statistical summary, entity resolution,
  leakage guards), not incidental coverage.
- **Pure math separated from I/O everywhere**: `odds_math.py`,
  `betting_stats.py`, and every hypothesis-selection module take primitives
  in, return primitives out - no network calls, no file I/O, fully unit
  testable and independently verifiable by hand.
- **Walk-forward, not random-split, validation** for Phase 1's model - the
  only honest way to test a time-ordered prediction problem without leaking
  the future into the past.
- **Every external data source got a budget-capped, plan-before-code audit
  spike** before any pipeline was built around it - explicit stop/go
  criteria, explicit "reject" as a valid outcome, written down before the
  first API key ever existed.
- **Null and negative results are reported with the same rigor and
  prominence as positive ones** - every phase's report states its own
  limitations, sample size, and what it does and doesn't prove, not just
  the headline number.
- **Hard ethical boundaries held under real pressure, not just stated**: no
  live or paper betting execution anywhere in this codebase; no family or
  personal-circle monitoring of players/coaches; no circumventing a
  bookmaker's KYC or jurisdiction controls, even when an external review
  suggested treating that as a modelable cost center - declined explicitly,
  in writing, in the commit history.

## Why stop here

Going further - Asian handicap/totals markets, lower-efficiency leagues,
tick-level exchange feeds, in-play modeling - is a real, legitimate research
direction, not a dead end for the *idea* of finding edge in football
markets. But it requires a different kind of infrastructure than this
project ever needed: institutional-grade tick data (Betradar/LSports-style
feeds run $1,000-5,000+/month), or Asian-broker access (BetInAsia,
Sportmarket, Asianodds and similar) that requires KYC, deposits, and often
blocks the same jurisdictions this project's Betfair spike already hit a
wall on. That's a different project, with a different risk/access profile,
not a next PR - see [`docs/RESEARCH_RESET.md`](docs/RESEARCH_RESET.md) for
the reasoning in full.

This repository is a complete, honest record of what a rigorous test of the
narrower, retail-accessible-data question actually found. See the
methodology docs before drawing conclusions from any single number in
isolation - the limitations are as much a part of each result as the
headline figure.

## Setup

Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash; use .venv/bin/activate on macOS/Linux
pip install -e ".[dev]"
```

## Running the tests

```bash
pytest
```

## Running the hypothesis tests

```bash
python scripts/run_phase0_clv_test.py
python scripts/run_phase0b_value_betting_test.py
python scripts/run_phase1_baseline_model.py
python scripts/run_phase2_ev_backtest.py
python scripts/run_shin_devig_robustness_check.py
```

Scripts that touch football-data.co.uk download and cache CSVs under
`data/raw/` (gitignored, re-downloadable); all scripts write a markdown
report plus supporting CSVs to `reports/` (also gitignored - local research
output). `run_phase2_source_spike.py`, `run_phase2_decision_snapshot_fetch.py`,
and `run_phase3_injury_spike.py` need a real API key in `.env` (see
`.env.example`) and real network access - see each script's own docstring
and the corresponding methodology/plan doc before running them.

## Project layout

```
src/football_odds_lab/
  data_sources/
    football_data_co_uk.py    # historical odds CSV downloader (2012-present)
    the_odds_api.py           # Phase 2 timestamped-odds client
    api_football.py           # Phase 3 injury-data client
    entity_matching.py        # explicit team-name maps, never fuzzy matching
  analysis/
    odds_math.py                    # pure: implied probability, overround, devig (proportional + Shin's method), CLV edge
    betting_stats.py                # pure: shared statistical summary (t-test, CI, ROI)
    clv_hypothesis.py               # pure: Phase 0 bet-selection rule
    value_betting_hypothesis.py     # pure: Phase 0.5/2 bet-selection rule (EV, devig-method-pluggable)
    line_movement_features.py / _target.py / _preprocessing.py / _baselines.py  # Phase 1 leakage-safe feature/target/model pipeline
    walk_forward.py / baseline_verdict.py / classification_metrics.py           # Phase 1 validation harness
    decision_timestamps.py / decision_snapshot_extraction.py / ev_candidate_price.py / ev_backtest.py  # Phase 2 EV backtest pipeline
scripts/          # one end-to-end runner per phase/spike - see each docstring
tests/            # unit tests for the pure analysis modules - 142 as of this writing
docs/             # one methodology or spike-plan doc per phase; docs/RESEARCH_RESET.md is the synthesis
```

## Known gaps (transparent, not hidden)

- Dependencies in `pyproject.toml` use loose lower-bound pins (`>=`), no lockfile yet.
  Fine for a research repo at this stage; worth revisiting if reproducibility across
  machines becomes an issue.
- 1X2 market only - no over/under, no Asian handicap, no other sports.
- No account-limiting / bankroll-scaling risk modeled - see `CLAUDE.md`'s note that
  a consistently winning bettor can be limited or closed by a bookmaker, a structural
  risk a backtest can't capture.
