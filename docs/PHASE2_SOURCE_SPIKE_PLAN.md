# Phase 2 Source Spike Plan

Status: plan only - no code, no API key obtained, no data fetched yet
Last updated: 2026-07-21

## Purpose

Per `docs/PHASE2_DATA_SOURCE_SELECTION.md`'s recommendation: before building
anything, audit whether the primary candidate (timestamped odds snapshots)
actually delivers what its docs promise, for this project's specific leagues
and the specific way this project would use it. This is an audit, not a
pipeline - it can end in "reject this source" as a legitimate, successful
outcome, same standard as every statistical result in this repo.

**This plan intentionally does not contain code.** Per the agreed sequencing,
implementation is a separate follow-up PR, scoped to exactly what's written
here - not "whatever seems convenient once we're in the code."

## Source for this spike

**The Odds API's historical odds endpoint**, per `PHASE2_DATA_SOURCE_SELECTION.md`'s
primary recommendation - Pinnacle coverage matches what this project already
uses as its sharp reference throughout Phase 0/0.5/1, and the incremental-signal
rationale (a real third time point) is the cleanest of the five candidates
evaluated.

**Not Betfair** for this first spike, even though it has a free tier - it's a
different market structure (peer-to-peer exchange, not a fixed-odds book like
Pinnacle), which would make this spike's findings less directly comparable to
everything already built. Worth a look later if The Odds API is rejected or
found insufficient, not the first thing to try.

If this spike rejects The Odds API, the next move is either a Betfair spike
(same plan, different source substituted) or falling back to the secondary
candidate (injuries/team news) - not silently downgrading scope on the same
source.

## Minimal scope

- **One source only** - The Odds API, nothing else, this round.
- **1-2 leagues** - proposed: `E0` (Premier League) only for the first pass.
  Largest, best-covered market, lowest risk of a coverage gap muddying the
  read on the source itself. Add a second league only if E0 looks clean and
  the budget cap (below) allows it.
- **1-2 seasons or a small date range** - proposed: the most recent completed
  season (2025-26) first, since recency maximizes the odds of good coverage
  for a first read. A short older window can be added afterward specifically
  to test the "how far back does this actually work" question, once the
  recent-season read is understood.
- **Read-only ingestion** - fetch and inspect, no persistent pipeline, no
  scheduled job.
- **No betting simulation.** No profit/EV/ROI computation of any kind - that's
  Phase 2 proper, gated on this spike succeeding first.
- **No model training.** Not even a baseline - this spike answers "is the data
  any good," not "does it predict anything."
- **Audit only**: coverage, timestamp granularity vs. advertised, entity
  matchability against the existing `football-data.co.uk` dataset, actual cost
  incurred, and reproducibility.

## QA gates - all required, none optional

- **No API keys in the repo.** `.env` locally only (already gitignored - see
  `.gitignore`'s existing `.env`/`.env.*` + `!.env.example` rule from PR #1,
  no changes needed there). A `.env.example` with a placeholder key gets
  committed when implementation starts, never a real key.
- **Raw response caching only if The Odds API's ToS actually permits it** for
  this use case. `PHASE2_DATA_SOURCE_SELECTION.md` already checked the
  redistribution clause (internal research use is fine); caching specifically
  hasn't been separately confirmed and must be checked against the live terms
  page before any response gets written to disk, not assumed from the
  redistribution finding alone.
- **Every fetched record preserves `source`, `fetched_at`, `event_timestamp`,
  and `provider_fixture_id`** - matches `docs/PRD.md` §8's data governance
  standard exactly, applied here for the first time to an external source
  instead of football-data.co.uk's CSVs.
- **Entity matching must produce a report, not just a result.** Match rate
  (what % of The Odds API fixtures matched a `football-data.co.uk` row) and an
  explicit list of unmatched cases - no silent fuzzy-matching that "looks fine"
  without a number behind it.
- **Budget cap, fixed before any request is made:**
  - Hard ceiling: **200 historical API requests** for the entire spike (a
    fraction of the Business plan's 200,000/month credit pool, but the point
    is bounding exploratory spend deliberately, not "we have plenty so it
    doesn't matter").
  - Scope ceiling: 1 league, 1 season for the first pass (see above) - do not
    silently expand to a second league/season without updating this document
    first.
  - If the 200-request ceiling is hit before the audit questions below are
    answered, stop and report what's known so far - do not quietly raise the
    cap mid-spike.
- **"Reject source" is a valid, first-class outcome.** The spike's report must
  end in one of: accept (data matches what's needed, proceed to a real Phase 2
  methodology doc), accept-with-caveats (usable but with named limitations),
  or reject (not usable, and why) - not just a data dump with no verdict.

## Payment / access gate - requires the user, not Claude

The Odds API's historical archive is a **paid-plan-only feature** (confirmed
in `PHASE2_DATA_SOURCE_SELECTION.md`, verified 2026-07-21) - the Business plan
at $99/month is the tier that includes it. Before implementation starts:

1. Confirm whether a cheaper path exists (e.g. pay-per-request access to the
   historical endpoint without the full monthly subscription) - re-check the
   live pricing page, don't assume $99/month is the only door in.
2. If a paid plan is genuinely required, **the user obtains and pays for the
   API key themselves** - this is a real financial commitment and Claude
   cannot and will not sign up or pay on the user's behalf, consistent with
   the standing rule against executing purchases. This gate blocks
   implementation from starting, not just a formality.

## Deliverables

A single spike report (`docs/PHASE2_SOURCE_SPIKE_REPORT.md` or under
`reports/`, TBD at implementation time) covering:

- Coverage: what fraction of E0's 2025-26 matches actually have historical
  odds available, and for which bookmakers (confirm Pinnacle specifically).
- Timestamp granularity: does the advertised 5-minute interval actually show
  up in real responses, or is it coarser/sparser in practice?
- Entity match rate + the unmatched-case list (see QA gates above).
- Actual cost incurred (request count against the 200-request cap).
- Reproducibility: re-fetch the same historical window a second time (e.g. a
  few days apart) and confirm the results are identical - a genuine historical
  archive shouldn't change on re-fetch; if it does, that's itself a finding.
- Explicit verdict: accept / accept-with-caveats / reject, with reasoning.

## Explicitly out of scope for this spike

- A second data source (Betfair, injuries, etc.) - one at a time.
- Any pipeline, scheduled job, or persistent ingestion service.
- Any betting/EV/ROI computation.
- Any model training or feature engineering beyond what's needed to check
  entity matchability against the existing dataset.
- Expanding league/season scope beyond what's written above without updating
  this document first.
