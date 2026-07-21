# football-odds-lab

Phase 0 research: is there a real, statistically significant edge in football
value-betting? Analytics only - no live or paper betting is placed by any code in
this repository.

See [`docs/PRD.md`](docs/PRD.md) for the product plan (stages, ethical boundaries,
what's in/out of scope), [`CLAUDE.md`](CLAUDE.md) for full project context (goals,
hard boundaries, legal notes), and
[`docs/PHASE0_METHODOLOGY.md`](docs/PHASE0_METHODOLOGY.md) /
[`docs/PHASE0B_VALUE_BETTING_METHODOLOGY.md`](docs/PHASE0B_VALUE_BETTING_METHODOLOGY.md) /
[`docs/PHASE1_LINE_MOVEMENT_SIGNAL_METHODOLOGY.md`](docs/PHASE1_LINE_MOVEMENT_SIGNAL_METHODOLOGY.md)
for exactly what each hypothesis test does and does not show, and
[`docs/PHASE1_CONCLUSION.md`](docs/PHASE1_CONCLUSION.md) for where Phase 1 landed.
Phase 2 planning (data source candidates, no source picked yet) is in
[`docs/PHASE2_DATA_SOURCE_SELECTION.md`](docs/PHASE2_DATA_SOURCE_SELECTION.md).

## Status

**Phase 0, 0.5, and 1 complete.** Three research passes so far:

- **Phase 0 (CLV)**: does Pinnacle's own opening-to-closing price movement predict
  match outcomes profitably? Both non-overlapping time windows came back positive
  and statistically significant - but the test needs the closing line to pick which
  side to back at the opening price, so it isn't live-tradeable as-is.
- **Phase 0.5 (cross-bookmaker value)**: direct follow-up removing that look-ahead -
  compares Pinnacle's closing fair price against retail closing prices at the SAME
  point in time. Came back null (no significant edge in either non-overlapping
  window) once corrected for a selection-bias artifact in the naive version.
- **Phase 1 (predict line movement before it happens)**: a leakage-safe walk-forward
  baseline model (majority-class / opening-favorite heuristic / logistic regression)
  came back WEAK - logistic regression beat majority-class but not the
  opening-favorite heuristic. A follow-up diagnostic confirmed the favorite effect
  is a real, broad market pattern, not a target-structure artifact - so the
  conclusion is that opening odds already encode most of the available pre-match
  signal, not that the model is broken. See
  [`docs/PHASE1_CONCLUSION.md`](docs/PHASE1_CONCLUSION.md).

See the methodology docs before drawing conclusions from any of these - the honest
limitations matter as much as the headline numbers.

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
```

Both download and cache historical odds CSVs from
[football-data.co.uk](https://www.football-data.co.uk) under `data/raw/` (gitignored,
re-downloadable), then write a markdown report plus per-match CSVs to `reports/`
(also gitignored - local research output, same convention as `ai-trading-agent`'s
`data/backtest-reports/`).

## Project layout

```
src/football_odds_lab/
  data_sources/       # football-data.co.uk downloader
  analysis/
    odds_math.py                 # pure: implied probability, overround, devig, CLV edge
    betting_stats.py             # pure: shared statistical summary (t-test, CI, ROI)
    clv_hypothesis.py            # pure: Phase 0 bet-selection rule
    value_betting_hypothesis.py  # pure: Phase 0.5 bet-selection rule
scripts/
  run_phase0_clv_test.py            # end-to-end: download -> Phase 0 test -> report
  run_phase0b_value_betting_test.py # end-to-end: download -> Phase 0.5 test -> report
tests/                # unit tests for the pure analysis modules
docs/
  PHASE0_METHODOLOGY.md              # Phase 0 (CLV): what it shows, what it can't
  PHASE0B_VALUE_BETTING_METHODOLOGY.md  # Phase 0.5 (cross-bookmaker value): same
```

## Known gaps (transparent, not hidden)

- Dependencies in `pyproject.toml` use loose lower-bound pins (`>=`), no lockfile yet.
  Fine for a research repo at this stage; worth revisiting if reproducibility across
  machines becomes an issue.
- 1X2 market only - no over/under, no Asian handicap, no other sports.
- No account-limiting / bankroll-scaling risk modeled - see `CLAUDE.md`'s note that
  a consistently winning bettor can be limited or closed by a bookmaker, a structural
  risk a backtest can't capture.
