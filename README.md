# football-odds-lab

Phase 0 research: is there a real, statistically significant edge in football
value-betting? Analytics only - no live or paper betting is placed by any code in
this repository.

See [`CLAUDE.md`](CLAUDE.md) for full project context (goals, hard boundaries, legal
notes) and [`docs/PHASE0_METHODOLOGY.md`](docs/PHASE0_METHODOLOGY.md) for exactly
what the current hypothesis test does and does not show.

## Status

**Phase 0, first pass complete.** The CLV (Closing Line Value) hypothesis test
described in `docs/PHASE0_METHODOLOGY.md` has been run once on the full available
history (2012-13 through 2025-26, top-5 European leagues, ~24k matches). Both
non-overlapping time windows came back positive and statistically significant - see
the report for the numbers and, more importantly, the limitations section before
drawing any conclusions from that.

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

## Running the Phase 0 CLV hypothesis test

```bash
python scripts/run_phase0_clv_test.py
```

Downloads and caches historical odds CSVs from
[football-data.co.uk](https://www.football-data.co.uk) under `data/raw/` (gitignored,
re-downloadable), then writes a markdown report plus a full per-match CSV to
`reports/` (also gitignored - local research output, same convention as
`ai-trading-agent`'s `data/backtest-reports/`).

## Project layout

```
src/football_odds_lab/
  data_sources/       # football-data.co.uk downloader
  analysis/
    odds_math.py      # pure: implied probability, overround, devig, CLV edge
    clv_hypothesis.py # pure: bet-selection rule + statistical summary
scripts/
  run_phase0_clv_test.py  # end-to-end: download -> test -> report
tests/                # unit tests for the pure analysis modules
docs/
  PHASE0_METHODOLOGY.md  # what the test does, what it can't tell us, how to read it
```

## Known gaps (transparent, not hidden)

- Dependencies in `pyproject.toml` use loose lower-bound pins (`>=`), no lockfile yet.
  Fine for a research repo at this stage; worth revisiting if reproducibility across
  machines becomes an issue.
- 1X2 market only - no over/under, no Asian handicap, no other sports.
- No account-limiting / bankroll-scaling risk modeled - see `CLAUDE.md`'s note that
  a consistently winning bettor can be limited or closed by a bookmaker, a structural
  risk a backtest can't capture.
