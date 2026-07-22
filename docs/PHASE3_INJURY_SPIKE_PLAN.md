# Phase 3 Injury Spike Plan

Status: plan only - no code, no API key obtained, no data fetched yet
Last updated: 2026-07-22

## Purpose

Per `docs/RESEARCH_RESET.md`'s re-ranked Phase 3 candidate shortlist: team
news/injuries is the top open candidate now that the former top candidate
(timestamped odds snapshots) was tried in Phase 2 and closed with NO EDGE.
This plan is the "airlock" this project has used before every external
source it has actually adopted (scope, budget, secret policy, stop/go
criteria, written down *before* any key exists) - for injuries specifically
that discipline matters even more than it did for odds, because the real
risk here isn't price, it's **timestamp leakage**: knowing a player was
injured is worthless, and actively misleading, if we can't also establish
whether the market could have known it at decision time.

**This plan intentionally does not contain code and does not commit to any
spend.** Per this project's standing sequencing, implementation is a
separate follow-up PR, scoped to exactly what's written here - not "whatever
seems convenient once we're in the code."

## Source for this spike

**API-Football, free tier only.** Verified 2026-07-22 (via the provider's
own pricing/documentation pages and public write-ups, not assumption):

- Free tier: 100 requests/day, documented as covering every endpoint
  (including `/injuries`).
- The `/injuries` endpoint returns `type` (Injury/Suspension), `reason`
  (e.g. "Knee Injury", "Hamstring Strain"), and ties to
  `player`/`team`/`fixture`/`date`; documented update cadence is roughly
  every 4 hours.
- **No explicit "publication" or "reported at" timestamp field surfaced in
  what's publicly visible** - the official field-by-field schema page
  returned an HTTP 403 to an unauthenticated fetch, so this has **not**
  been confirmed against a real response yet. That confirmation is this
  spike's second stop/go question below, not something to assume either
  way from documentation summaries.
- Free-tier historical season access is commonly restricted to the current
  season across football data APIs generally - **not yet confirmed
  specifically for API-Football's free tier**. This is the spike's first
  stop/go question, not an assumption baked into this plan.

**Sportmonks is the fallback/paid candidate, not this round's pick.**
Verified 2026-07-22: Sportmonks has no standalone injuries endpoint (it's a
`sidelined` include on team/player/fixture endpoints), and - the real
disqualifier for a free spike - **its free plan does not cover the Premier
League at all**, only the Danish Superliga and Scottish Premiership. Testing
Sportmonks for EPL would require a paid Starter plan (~€29/month) or a
one-time 14-day trial - real spend, not appropriate for an audit-only first
look. Revisit only if API-Football is rejected.

## Minimal scope

- **One source only** - API-Football, nothing else, this round.
- **One league** - EPL (`E0`), matching every prior phase's primary
  dataset for direct comparability.
- **One season** - 2023-24, matching Phase 2's decision-snapshot dataset
  exactly, so a future methodology doc (if this spike passes) can reuse the
  same football-data.co.uk rows without a second data-alignment problem.
- **Read-only audit** - fetch and inspect, no persistent pipeline, no
  scheduled job.
- **No betting simulation, no EV/ROI of any kind.**
- **No model training**, not even a baseline.
- **Audit only**: schema (does a usable timestamp field exist at all),
  historical coverage, entity matchability against the existing
  `football-data.co.uk` dataset, actual cost incurred.

## QA gates - all required, none optional

- **No payment, no card, no subscription.** This spike stays inside
  API-Football's free tier, full stop. If the free tier turns out to gate
  2023-24 behind a paid plan, that is a stop condition for this spike (see
  below), not a trigger to ask the user to pay - any upgrade decision is
  separate, future, and requires its own explicit approval, same standing
  rule as every real financial commitment in this project.
- **No API keys in the repo.** `.env` locally only (already gitignored).
  `.env.example` gets a new `API_FOOTBALL_KEY=` placeholder line when
  implementation starts - never a real key.
- **Budget cap, fixed before any request is made: 20 requests**, out of the
  free tier's 100/day allowance. If 20 requests isn't enough to answer the
  three stop/go questions below, stop and report what's known - do not
  quietly raise the cap mid-spike or reach for "just one more request."
- **Raw response caching, if used, is never committed** - gitignored, same
  convention as `data/raw/the_odds_api/` from Phase 2.
- **Every fetched record preserves `source`, `fetched_at`, and provider
  fixture/player identifiers** - matches `docs/PRD.md` §8's data governance
  standard, applied here for injuries the same way it already was for
  Phase 2's odds snapshots.
- **Entity matching must produce a report, not just a result** - match rate
  against `football-data.co.uk`'s `HomeTeam`/`AwayTeam` strings, plus an
  explicit list of unmatched cases, same standard as `entity_matching.py`.
- **No player-family, social, or personal-circle monitoring of any kind** -
  restating `docs/PRD.md` §6's boundary explicitly here even though a
  structured injury API is nowhere near that line, because this is the
  closest this project has come to player-specific data and the boundary
  deserves restating, not silent assumption.
- **"Reject" is a valid, first-class outcome** - same standard as every
  spike and hypothesis test in this project so far.

## Stop/go criteria - ordered, each one gates the next

1. **Does `/injuries` (or `/sidelined`) respond at all for EPL 2023-24 on
   the free tier?** If historical season access is restricted to the
   current season only (the common free-tier pattern noted above, not yet
   confirmed for this provider specifically) - **STOP.** No historical
   audit is possible under the free tier. Whether upgrading is ever worth
   exploring is a separate future decision, not one to make from inside
   this spike.
2. **Does any field in a real response function as a genuine
   "when did this become publicly known" signal**, as opposed to only the
   injury's own start/end duration? If no such field exists - **STOP for
   backtesting purposes.** See the fallback outcome below; this is not
   automatically a full reject of the source.
3. **If both above pass**: check entity-resolution feasibility (provider
   team/player IDs against the existing `HomeTeam`/`AwayTeam` strings) and
   the coverage/missingness rate across the season - same shape as Phase
   2's spike audit.

## Fallback outcome if a stop condition trips

Tripping question 1 or 2 does **not** automatically mean "reject this
source forever." Per `docs/RESEARCH_RESET.md`'s Phase 3 candidate
criterion #3 (historical, *or* prospectively collectible), a source with no
real historical timestamp archive may still be viable for **Phase 4's paper
journal** - collecting it going forward, in real time, using this project's
own fetch timestamp as the honest "known as of" marker, sidestepping the
need for the provider to expose one itself. That changes which phase the
source belongs to; it doesn't disqualify it outright. This spike's report
must say explicitly which of these outcomes applies, not leave it implied.

## Deliverables

A single spike report (`docs/PHASE3_INJURY_SPIKE_REPORT.md` or under
`reports/`, TBD at implementation time) covering:

- Answers to all three stop/go questions above, in order, with the real
  response data (or the point at which the spike stopped, if it stopped
  early).
- Entity match rate + the unmatched-case list, if question 3 was reached.
- Actual request count against the 20-request cap.
- Explicit verdict: accept / accept-with-caveats / reject-for-backtest-
  but-viable-for-paper-journal / reject, with reasoning - not a data dump
  with no verdict.

## Explicitly out of scope for this spike

- Sportmonks itself this round - real spend required just to test EPL
  coverage, not appropriate for a free audit; revisit only if API-Football
  is rejected.
- Any other league or season without updating this document first.
- Any model, backtest, or EV/ROI computation.
- Lineups, press-conference, or social-signal candidates - separate
  candidates per `docs/RESEARCH_RESET.md`'s shortlist, not this spike.
- Any player-family or personal-circle data, in any form.
