# Phase 3 Betfair Exchange Spike Plan

Status: plan only - no code, no Betfair account, no data fetched yet
Last updated: 2026-07-22

## Purpose

Per `docs/RESEARCH_RESET.md`'s re-ranked Phase 3 candidate shortlist:
exchange liquidity/order-book depth (Betfair) is now the top open candidate,
since team news/injuries (the prior top candidate) was audited and closed
(`docs/PHASE3_INJURY_SPIKE_PLAN.md`, reject-for-backtest). This is a
genuinely different risk profile than either prior spike (The Odds API,
API-Football): not "another price series from another book," but market
*microstructure* - volume, spread, available liquidity, order-book depth.
Per the user's framing when this plan was requested: the question isn't
"what price?" but "how does the market breathe before the price moves?" -
a potentially new signal family, not another odds-only source.

**This plan intentionally does not contain code and does not commit to any
spend.** Same sequencing as every prior spike: plan and review first,
account/access second, real requests third, code only after that.

## Source for this spike

**Betfair Historical Data Service** (`historicdata.betfair.com` +
`developer.betfair.com/historical-data-services-api/`). Verified 2026-07-22
against the provider's own support docs and developer documentation, not
assumed:

- Real historical archive since ~2015-2016 (matches
  `docs/PHASE2_DATA_SOURCE_SELECTION.md`'s earlier finding for candidate #3's
  Betfair alternative - re-confirmed here, not a new number).
- Three tiers: **Basic (free)** - 1-minute snapshot frequency, **no volume**,
  last-traded-price only, not a full price ladder. **Advanced** and **Pro**
  (paid, price unconfirmed) - same underlying data, higher frequency, and -
  the part that actually matters for this candidate's hypothesis - up to 3
  levels of back/lay price-ladder depth (`batb`/`batl`) plus traded volume.
- A real, scriptable API exists (`GetCollectionOptions`,
  `DownloadListOfFiles`, `DownloadFile`) - this can be audited the same way
  as the prior two spikes (a small number of real calls/downloads, not a
  manual browser-only workflow), even though the underlying data is
  delivered as compressed file downloads rather than JSON API responses.
- Coverage is stated to include both pre-match and in-play periods, not
  in-play only - relevant since this project's entire framework (decision
  timestamps, T-24h/T-12h/T-6h/T-1h) is pre-match only.

## The central problem this plan is structured around

**The free Basic tier, by itself, cannot answer this candidate's actual
hypothesis.** Per the provider's own documentation, Basic has no volume and
no price-ladder depth - if that's all this spike ever looks at, the honest
conclusion would be "yet another price series, still the odds-only family
Cycle 1 already exhausted," not a genuinely new signal. Confirming real
liquidity/depth data requires the paid Advanced or Pro tier, and real
pricing for those hasn't been confirmed yet (open question, see below).

This plan is deliberately split into two stages so the free/no-spend audit
work can proceed now, without silently drifting into a real purchase
decision along the way:

- **Stage A (this spike, free tier only)**: everything that can be checked
  without spending anything - account access reality, pre-match historical
  coverage, entity resolution, ToS, and an *empirical* confirmation of what
  the free tier actually contains (not just trusting the documentation
  summary above).
- **Stage B (a separate, later decision - explicitly out of scope here)**:
  whether to purchase Advanced/Pro tier data specifically to verify real
  liquidity/depth. Gated on Stage A looking clean on everything else, and on
  the user's own explicit approval + payment, same standing rule as every
  real financial commitment in this project. This plan does not request or
  assume that approval.

## A boundary specific to this source, not the prior two

Betfair is a **live, real-money betting exchange**, not a pure read-only
stats/odds API like The Odds API or API-Football - the account needed for
Historical Data access is a real Betfair customer account, and the same
account technically has access to Betfair's live betting/order-placement
API. This changes nothing about this project's standing rules, but is worth
stating explicitly here since it's the closest this project has come to a
source with real execution capability sitting next to the data:

- This project will **only ever use the read-only Historical Data API**
  (`GetCollectionOptions`/`DownloadListOfFiles`/`DownloadFile`) - never
  Betfair's betting/order-placement endpoints, for any reason.
- A Betfair account existing for data-download purposes creates **no
  exception** to `docs/PRD.md`'s standing rule: no live or paper betting
  execution by any code in this repository, ever.
- Registering the account, and any deposit/verification Betfair's signup
  flow might require, is entirely the user's own action - same hard
  boundary as every account-creation case in this project, applied here
  with extra emphasis given what kind of account this is.

## Minimal scope (Stage A only)

- **One source only** - Betfair Historical Data, Basic (free) tier, nothing
  else, this round.
- **One league** - EPL, matching every prior phase's primary dataset.
- **One season, or a small sample within it** - 2023-24 if available at
  this granularity, else the most recent season with full Basic-tier
  coverage; a handful of individual match files, not the full season, since
  this is an audit of file structure and access, not a coverage sweep.
- **Read-only audit** - download and inspect, no persistent pipeline, no
  scheduled job.
- **No betting simulation, no EV/ROI of any kind.**
- **No model training**, not even a baseline.
- **No use of Betfair's betting/order-placement API**, under any
  circumstance - see the boundary section above.

## QA gates - all required, none optional

- **No payment for this spike.** Stage A stays inside the Basic (free)
  tier, full stop. If anything requires a paid tier to even inspect
  (unlikely for Basic-tier file structure, but not yet confirmed), that
  triggers Stage B's separate gate, not silent escalation.
- **A known terminology trap, named here so it isn't mistaken for scope
  creep later**: Betfair's own download flow requires adding a file to "My
  Data" / a "purchase" step in their UI even for Basic-tier files, before
  the API will serve it - the word "purchase" appears in their own workflow
  regardless of tier. This is allowed for Stage A **only if the total cost
  for that step is confirmed to be zero and no paid tier, card, or deposit
  is involved** - if a real charge shows up anywhere in that flow for a
  Basic-tier file, that's a Stage B question, not something to click through.
- **Account registration is the user's own action** - Claude does not
  create the Betfair account, does not log in, and does not handle
  Betfair account credentials as plaintext, same convention already used
  for `THE_ODDS_API_KEY`/`API_FOOTBALL_KEY`: the user adds session
  credentials directly to `.env`, never pasted into chat.
- **No API keys or session tokens in the repo.** `.env` locally only.
  `.env.example` gets new placeholder line(s) when implementation starts -
  never a real value.
- **Sample scope cap, fixed before any download**: at most **10 sample
  match files** downloaded for this audit (a scope-discipline limit, not a
  financial-risk limit - Basic tier is free and not credit-metered, unlike
  The Odds API or API-Football). If 10 files isn't enough to answer the
  questions below, stop and report what's known - do not quietly expand
  scope mid-spike.
- **Raw downloaded files are never committed** - gitignored, same
  convention as `data/raw/the_odds_api/` and `data/raw/api_football/`. If
  the spike report quotes an example record, it must be a minimal excerpt,
  not a raw file dump.
- **Every inspected record preserves `source`, `fetched_at`, and provider
  market/event identifiers** - matches `docs/PRD.md` §8's data governance
  standard, applied here the same way as the prior two spikes.
- **Entity matching must produce a report, not just a result** - match rate
  against `football-data.co.uk`'s `HomeTeam`/`AwayTeam` strings, plus an
  explicit list of unmatched cases.
- **ToS checked against the live terms page before any caching decision** -
  not assumed from the redistribution finding on a different source
  (The Odds API's terms don't transfer to Betfair's).
- **"Reject" is a valid, first-class outcome.**

## Stop/go criteria - the five questions, in the order given

1. **Are there historical pre-match snapshots with a real timestamp?** Not
   just settlement/result data, and not in-play-only - a snapshot dated
   meaningfully before kickoff, matching this project's T-24h/T-12h/T-6h/
   T-1h decision-timestamp framework. If Betfair's historical files turn out
   to be in-play-heavy with sparse or absent pre-match snapshots - **STOP**;
   this candidate doesn't fit this project's pre-match decision framework
   regardless of what else it offers.
2. **Is there order-book depth / available liquidity / traded volume, not
   just matched/last-traded odds?** The central differentiator - if only
   the free Basic tier is checked and it confirms no volume/depth (as
   documentation currently states), this question can only be fully
   answered by Stage B's paid-tier decision, not resolved here. Stage A's
   job is to *empirically confirm* what Basic tier actually contains (not
   just trust the doc summary) and clearly report that this question
   remains open pending Stage B if that's what the free-tier file shows.
3. **Can Betfair events be matched to our fixtures without manual magic?**
   Same entity-resolution discipline as every prior spike - explicit
   mapping, match-rate report, unmatched-case list, not fuzzy string
   matching.
4. **Is price/access/ToS sane for a research lab?** Real Advanced/Pro
   pricing (currently unconfirmed - open question for this spike to
   resolve, at least by locating the actual number, without purchasing
   anything), account requirements, and terms of service for this project's
   actual use case (internal research, not redistribution).
5. **Does this source add a genuinely new signal beyond opening odds, or is
   it still the odds-only family?** The meta-question tying 1-4 together.
   If Stage A can only confirm Basic-tier (price-only) data and Stage B's
   paid-tier decision is deferred, this question's honest answer is
   "unresolved, pending Stage B" - not a premature yes or no.

## Fallback / staged outcome

Unlike the injury spike, this plan does not expect a single clean verdict
from Stage A alone, because the central question (#2 above) structurally
requires paid data this stage doesn't purchase. Stage A's report must state
one of:

- **Stage A clears the board (1, 3, 4 pass; free tier's lack of depth
  confirmed empirically) - Stage B (paid-tier purchase decision) is worth
  bringing to the user as an explicit, separate ask.**
- **Stage A already finds a disqualifying problem (e.g., no real pre-match
  snapshots, unworkable entity resolution, or ToS that rules out this use
  case)** - reject the source outright, Stage B is moot, no need to ever
  raise the paid-tier question.

## Deliverables

A single Stage A spike report (`docs/PHASE3_BETFAIR_EXCHANGE_SPIKE_REPORT.md`
or under `reports/`, TBD at implementation time) covering:

- Answers to questions 1, 3, 4, and the empirical Basic-tier content check
  for question 2, with real response/file data.
- Entity match rate + unmatched-case list.
- Real Advanced/Pro pricing, if locatable without purchasing.
- Explicit recommendation on whether Stage B (paid-tier verification) is
  worth proposing to the user as a separate, later decision - not a
  decision made here.

## Explicitly out of scope for this spike

- Any purchase of Advanced/Pro tier data - that is Stage B, a separate,
  later, explicitly-gated decision.
- Betfair's betting/order-placement API, under any circumstance.
- Any other league or season beyond a small EPL sample without updating
  this document first.
- Any model, backtest, or EV/ROI computation.
- Any player-family, social, or personal-circle data, in any form.
