# Phase 2 Data Source Selection

Status: draft, research/design only - no code, no source picked for implementation yet
Last updated: 2026-07-21

## Purpose

Per `docs/PHASE1_CONCLUSION.md`: opening odds already encode most available
pre-match signal, and adding more schedule/rolling features in the same family
isn't expected to help further. The question for Phase 2 isn't "which model,"
it's **which new data source could plausibly add signal that opening odds don't
already contain.**

Goal here is narrow: pick 1-2 real candidates worth a small verification spike,
not survey everything that exists. Social/press-conference sources stay in the
backlog per `docs/PRD.md` §14 and §12 - not evaluated here on purpose.

## Evaluation matrix

Every candidate scored against:

1. **Available before market close** - does the signal exist before the line has
   already moved, or does it arrive too late to matter?
2. **Timestamped** - is there a real publication/update time, not just "current
   state"?
3. **Historical depth** - can past seasons be reconstructed, or is this live-only?
4. **Entity resolution** - can an event be tied to a specific team/player/match
   without a lot of fragile name-matching?
5. **Incremental signal hypothesis** - a concrete reason this should add
   information beyond opening odds, not just "seems related."
6. **Legal/ethical safety** - public source, sane ToS, no personal-circle/family
   monitoring (see `docs/PRD.md` §6 - that boundary applies here too).
7. **Cost/reliability** - real pricing, rate limits, how established the provider is.

## Candidates

### 1. Team news / injuries / suspensions

The most direct hypothesis: injury/availability news moves lines, and if it's
known before the market has fully absorbed it, that's a real signal.

- **Before close**: yes in principle - injury news typically breaks days before
  a match.
- **Timestamped**: partial. API-Football's `/sidelined` endpoint gives every
  injury/suspension a player has had with start/end dates - but that's the
  injury's own duration, not necessarily when the NEWS became public. The gap
  between "injury started" and "market found out" matters and isn't obviously
  covered by this field - needs checking against a real response, not assumed.
- **Historical depth**: real open risk, not yet verified. API-Football's docs
  say injury coverage is per-league-per-season (a `coverage.injuries` flag) -
  it is NOT a blanket "every league since some fixed year." Given this
  project's existing data already goes back to 2012-13, there is a real chance
  injury coverage for our specific 5 leagues is much thinner in the early
  years than in recent ones - needs a real API call per league/season range
  before trusting this for a full-history backtest, same discipline as every
  data-floor check already done in this project (football-data.co.uk's
  Max/Avg columns, the 2019-20 cutoff, etc.).
- **Entity resolution**: should be workable - team/player IDs exist, but
  matching those IDs to our existing team-name strings (`HomeTeam`/`AwayTeam`
  from football-data.co.uk) is its own small integration task, not free.
- **Incremental signal hypothesis**: strong, well-established in the sports
  betting literature - the most classical "why would this help" story of any
  candidate here.
- **Legal/ethical safety**: clean - official team news via a standard
  commercial API, no personal-circle monitoring.
- **Cost/reliability**: API-Football plans start at $19/month, all endpoints
  included at every tier. Established provider (api-football.com / api-sports.io).

**Verdict: strong hypothesis, real unverified risk on historical depth for our
specific leagues/seasons.** Worth a small spike (a handful of real API calls
against 2012-13 and a recent season, same leagues we already use) before any
design work.

### 2. Lineups

- **Before close**: risky - confirmed lineups typically publish only ~60
  minutes before kickoff. Depending on how close to kickoff Pinnacle's own
  "closing" snapshot is taken, this may leave little or no window between
  lineup confirmation and market close - the exact execution-timing risk
  already flagged in review.
- **Timestamped**: yes, lineup announcement time is generally recorded by
  providers (Sportmonks, API-Football).
- **Historical depth**: not verified - same open question as injuries.
- **Entity resolution**: workable, same caveat as injuries.
- **Incremental signal hypothesis**: real but narrower than injuries - a
  surprise lineup change (a key player unexpectedly rested/injured) is
  informative, but a lot of that same information likely already leaked via
  injury/press news *before* the lineup is officially confirmed, so the
  *incremental* value specifically from lineups over injury news is genuinely
  unclear, not just a timing inconvenience.
- **Legal/ethical safety**: clean.
- **Cost/reliability**: same family of providers as injuries (Sportmonks,
  API-Football).

**Verdict: weaker candidate than injuries specifically because of the timing
risk the user flagged - worth testing "what if we knew lineups at time X" as a
research question, but not a safe first pick for anything meant to be
live-actionable.**

### 3. Timestamped odds snapshots (a third time point)

Not a new external signal - a fix to a known, already-documented methodological
gap: `docs/PHASE1_LINE_MOVEMENT_SIGNAL_METHODOLOGY.md` explicitly rules out
"early line movement" as a Phase 1 feature because football-data.co.uk only
gives two points (open, close). A source with real intermediate snapshots would
let that question finally be asked honestly.

- **Before close**: N/A - this is about resolution of the price series itself,
  not an external event.
- **Timestamped**: yes, explicitly. The Odds API takes snapshots at 10-minute
  intervals from June 2020, 5-minute intervals from September 2022 onward.
  Betfair's Historical Data service has time-stamped Exchange data (price,
  volume, BSP) since 2016.
- **Historical depth - the real problem**: neither source reaches back to
  2012-13. **The Odds API starts June 2020; Betfair's modern API-based archive
  starts 2016.** Both fall well short of this project's current 2012-2025
  range. Adopting either means either (a) restricting any backtest using this
  data to a shorter window (2020-2025 or 2016-2025), a real loss of
  statistical power and multi-window validation ability versus what Phase 0/0.5
  had, or (b) treating it as supplementary depth for only the recent portion
  of the existing dataset. This is a hard ceiling, the same kind already hit
  with football-data.co.uk's Max/Avg columns (2019-20 floor) and the abandoned
  historical out-of-sample attempt for ETF Rotation in the sibling
  `ai-trading-agent` project - not a parameter to tune around.
- **Entity resolution**: already solved - same match/team identifiers as the
  existing dataset, this would extend or cross-check the same price series,
  not introduce a new one.
- **Incremental signal hypothesis**: the cleanest of all five candidates. This
  isn't a speculative "maybe this correlates" story - it's closing a
  documented gap in the existing methodology (no way to distinguish "early
  drift" from "the target itself" without a third point).
- **Legal/ethical safety**: The Odds API's terms prohibit reselling/redistributing
  their data as a standalone product, but internal research use (this
  project's actual use case) is not that - fine under standard terms.
  Betfair Exchange data is a different market structure (peer-to-peer
  exchange, not a fixed-odds book like Pinnacle) - real, sharp, but not
  directly the same thing being compared against elsewhere in this project;
  worth noting, not necessarily disqualifying.
- **Cost/reliability**: The Odds API Business plan $99/month (full historical
  archive + Pinnacle + international books at no extra credit cost). Betfair
  has a free tier (last-traded-price-per-minute only, no volume) plus paid
  tiers for higher frequency/full price ladder.

**Verdict: strongest methodological justification of the five, best entity-
resolution story, no execution-timing risk - but capped at ~5-6 years of
history instead of this project's current ~13, and that tradeoff needs to be
made consciously, not discovered after committing to it.**

### 4. Fixture congestion + travel, extended

Already partially implemented (`home_congestion`/`away_congestion`/
`home_rest_days`/`away_rest_days` in `line_movement_features.py`, PR #6) - this
would extend it with actual cup/European fixtures (Sportmonks covers UEFA
Champions League/Europa League/Conference League with historical data) to close
the already-documented gap where a club's European midweek game isn't visible
to the current rest-days calculation.

- **Before close / timestamped / entity resolution**: same as injuries -
  workable, not yet verified for our specific leagues/seasons.
- **Historical depth**: Sportmonks advertises historical coverage across UEFA
  competitions; exact depth for the 2012-13 season specifically not verified.
- **Incremental signal hypothesis**: weakest of the four "real" candidates (own
  assessment, agreed) - this closes a known undercounting gap rather than
  introducing new information; genuine but likely small effect size.
- **Legal/ethical safety**: clean.
- **Cost/reliability**: same provider family as injuries/lineups.

**Verdict: safe, cheap, low-risk enrichment - but not a strong enough
hypothesis on its own to be a Phase 2 headline candidate. Reasonable as a
secondary addition alongside whichever primary candidate gets picked, not as
the primary pick itself.**

### 5. Public coach/team press conferences

Deprioritized per review discussion - NLP/entity-extraction pipeline needed
(not just a JSON API), meaningfully higher engineering cost than the other
four, and the project hasn't yet demonstrated it can extract incremental
signal from a *clean, structured* source. Not evaluated in depth here; revisit
only after a structured source (injuries or timestamped odds) has actually
been tried.

### Explicitly out of scope here: social media

Per `docs/PRD.md` §14 - stays a named-but-unscoped future stream, not a Phase 2
candidate. Too much noise, entity/time-matching complexity, and ethical surface
area to be a sensible starting point before a cleaner source has proven the
project can extract incremental signal at all.

## Recommendation

**Primary: timestamped odds snapshots (#3).** Cleanest incremental-signal
rationale (fixes a real, already-documented methodological gap rather than
betting on a new, unproven information channel), zero new entity-resolution
work, no execution-timing risk. The historical-depth ceiling (~2020 or ~2016
onward) is a real, known cost - explicitly not being glossed over - but it's a
bounded, understood tradeoff rather than an open risk.

**Secondary: team news / injuries (#1).** Strongest classical signal-value
story of the remaining candidates, but historical-depth-per-league-per-season
is a genuine open question, not yet checked against a real API response.

**Both need a small verification spike before any design/implementation work**,
matching this project's own standing discipline (verify against real data
before committing to a methodology, per every prior phase in this repo):

1. For timestamped odds: pull one real historical window from The Odds API (or
   Betfair) for a handful of matches already in the existing dataset, confirm
   the data actually looks like what the docs promise (intervals, coverage of
   Pinnacle specifically, format).
2. For injuries: pull real `/injuries` and `/sidelined` responses for a 2012-13
   fixture and a 2024-25 fixture in the same league, to see whether the
   historical-depth risk above is real or overstated.

Neither spike commits to building anything - they're pure verification, same
spirit as the football-data.co.uk schema checks that opened this whole project.

## What this document does not do

Does not pick a final source, does not scope a Phase 2 methodology doc (that
comes after a candidate survives its verification spike, mirroring how Phase 1's
methodology doc came only after football-data.co.uk's schema was verified
empirically), and does not start any code.
