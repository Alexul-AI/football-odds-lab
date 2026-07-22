# football-odds-lab PRD

Status: v0.3
Mode: Research Lab first
Last updated: 2026-07-21

> Editorial note (2026-07-21): revised from the original v0.1 draft after review.
> One item was removed rather than merely deprioritized - see §6 - and a few
> sections were trimmed for ceremony. v0.3 adds §14, naming a possible future
> research stream while keeping it explicitly unscoped and outside this
> collaboration - see §14 for what that means precisely.

## 1. Vision

`football-odds-lab` is a football betting research lab.

The goal is not to build a betting bot first. The goal is to find out whether football markets contain a real, reproducible, look-ahead-free edge.

The project should grow in stages:

1. Historical odds research.
2. Market movement research.
3. External signal research.
4. Paper-mode prediction journal.
5. Only much later: legally reviewed betting workflows through allowed local channels.

The guiding principle:

> Evidence first. Automation later. Real betting last, if ever.

## 2. Product Thesis

Football outcomes and odds may be affected by information that reaches the market unevenly:

- player injuries;
- lineup uncertainty;
- a player's own public statements about form, fitness, or personal circumstances;
- travel fatigue;
- coach statements;
- training reports;
- club politics;
- local news;
- official social media channels (player, coach, club);
- fan/community rumors;
- bookmaker line movement.

The hypothesis is not "social media predicts matches."

The real hypothesis is:

> Public information around players, coaches, and clubs may sometimes appear before odds fully adjust. If captured ethically and tested rigorously, it may help predict line movement or market mispricing.

This must be proven, not assumed.

## 3. Current Product Mode

The current mode is **Research Lab**.

The system may:

- download historical odds;
- analyze historical results;
- test hypotheses;
- generate reports;
- compare odds movement;
- evaluate signals;
- document negative findings.

The system must not:

- place bets;
- tell the user "bet on X today";
- scrape private data;
- harass players or families;
- bypass platform restrictions;
- use non-public personal information;
- monitor family members or a player's personal circle as an instrumented signal source, even if their posts are technically public - see §6;
- imply legal approval for betting.

## 4. Long-Term Direction

Long term, the project may become a multi-source football intelligence system.

Possible data domains:

### 4.1 Odds Data

- opening odds;
- closing odds;
- bookmaker overround;
- line movement;
- cross-bookmaker spread;
- market liquidity proxies;
- Pinnacle as sharp reference;
- local legal bookmaker odds if available.

### 4.2 Match Data

- team strength;
- recent form;
- home/away context;
- schedule congestion;
- travel distance;
- rest days;
- injuries;
- suspensions;
- expected lineups;
- weather;
- referee tendencies.

### 4.3 News Data

- club news;
- local sports portals;
- press conferences;
- coach quotes;
- training reports;
- transfer rumors;
- disciplinary issues.

**Data availability caveat**: unlike odds data, there is no free, reliable point-in-time
archive of news/press coverage going back years. Expect most of this domain to be
validatable only *prospectively*, by collecting it going forward through the Phase 3
paper journal (§5, §9) - not by backtesting against years of historical odds the way
Phase 0/0.5 did. This is the same wall `ai-trading-agent` hit with its sentiment/insider
filters (current-state-only APIs, no historical snapshot) - worth stating now so it
isn't a surprise later. Where a genuine historical archive does exist for some source,
use it; don't assume one exists by default.

### 4.4 Public Social Signals

Only public, ethically accessible information, and only about the public figures
themselves - not their family or personal circle (see §6 for why that line matters
and is firm, not a matter of degree).

Potential sources:

- players' own public posts/statements;
- coaches' public posts/statements;
- club staff public posts;
- public comments from local journalists;
- public fan/community signals.

This data should be treated as weak, noisy context, not truth.

### 4.5 Sentiment and Context Signals

Possible extracted features, all derived from the sources in §4.3/§4.4 above:

- injury hints;
- confidence/motivation;
- squad morale;
- coach pressure;
- fan unrest;
- local media pessimism/optimism;
- uncertainty spikes;
- contradiction between official and unofficial narratives.

Every signal must be timestamped by when it became publicly available.

## 5. Core Research Questions

### Phase 0: Does line movement contain real signal?

Already tested through CLV.

Question:

> If we know where Pinnacle moved from open to close, would betting the moved-toward side at open have been profitable?

Interpretation:

- useful mechanism discovery;
- not live-tradeable;
- uses future information.

### Phase 0.5: Does same-time cross-bookmaker value work?

Question:

> At the same timestamp, does comparing Pinnacle fair price to retail price reveal edge?

Interpretation:

- useful anti-look-ahead test;
- `Max` prices can create selection artifacts;
- `Avg` is more honest;
- negative result should be preserved.

### Phase 1: Can we predict line movement before it happens?

This is the next important phase. Full methodology:
[`docs/PHASE1_LINE_MOVEMENT_SIGNAL_METHODOLOGY.md`](PHASE1_LINE_MOVEMENT_SIGNAL_METHODOLOGY.md).
The leakage-safe feature builder is done (`line_movement_features.py`); the first
baseline model's locked scope is
[`docs/PHASE1_BASELINE_MODEL_PLAN.md`](PHASE1_BASELINE_MODEL_PLAN.md). First real
run: **WEAK** - logistic regression beats majority-class but not the
opening-favorite heuristic. A follow-up diagnostic
(`scripts/run_phase1_diagnostic.py`) confirmed the favorite effect is a real,
broad market pattern (monotonic with favorite strength, consistent across all 5
leagues and all 10 walk-forward folds, won on larger-than-average moves) rather
than a target-structure artifact - see the CLAUDE.md findings log for the full
numbers before proposing a more complex model. Phase 1 is now formally
concluded: [`docs/PHASE1_CONCLUSION.md`](PHASE1_CONCLUSION.md) - opening odds
already encode most available pre-match signal; more schedule/rolling features
in the same family are not expected to help further without new evidence.
Next: either Phase 2 (does the existing favorite signal convert to positive EV
net of vig) or a genuinely different feature family, not more of the same kind.

Question:

> Predict future Pinnacle open-to-close movement direction using only features
> available at or before the opening snapshot, excluding any feature derived from
> the future closing line.

**Not** "early odds drift" - with only two snapshots per match (open, close), there
is no third, earlier point to measure drift from; the open-to-close delta already
is the prediction target, so using a piece of it as a feature would be leakage or a
tautology. See the methodology doc's dedicated section on this.

Honest baseline (details in the methodology doc): league, home/away, opening odds
level and overround, day of week, season stage, rest days, match congestion, and
strictly-lagged rolling team-level CLV-direction/efficiency features.

Candidate external signals for later, once the baseline is understood, in order of
lowest to highest effort/risk - see §12:

- public injury/news signals;
- lineup uncertainty;
- coach statements;
- official social media context (player/coach/club);
- local media intensity.

Start with the cleanest measurable baseline first: odds movement + match metadata only,
no external signals at all. Add §4.3/§4.4 sources one at a time only once that baseline
exists and is understood - see §12.

Success criteria:

- no look-ahead;
- signal timestamp is before odds movement;
- positive out-of-sample CLV;
- robust across time windows;
- not dependent on one league or one lucky period.

### Phase 2: Can predicted line movement become positive EV?

Per `docs/PHASE1_CONCLUSION.md`, Phase 2 doesn't start with a methodology doc -
it starts with picking a new data source, since opening odds alone are already
mostly exhausted. See
[`docs/PHASE2_DATA_SOURCE_SELECTION.md`](PHASE2_DATA_SOURCE_SELECTION.md)
(added 2026-07-21, research/design only, no source picked yet) for the
candidate evaluation. The audit plan for the first candidate (timestamped odds
via The Odds API) is
[`docs/PHASE2_SOURCE_SPIKE_PLAN.md`](PHASE2_SOURCE_SPIKE_PLAN.md). **Spike
complete, result: ACCEPT** - Pinnacle confirmed in The Odds API's historical
snapshots, 98.6% entity-match rate against the existing dataset, price
agreement within 1.56 devigged-probability percentage points, reproducible on
re-fetch. See the plan doc's "Result" section for the full numbers and the
one real caveat (coverage figures depend on snapshot sampling density, not
just source availability). Confirms the source is usable - does not mean
Phase 2 itself is done; EV/vig/betting economics haven't been touched yet.

The EV/betting-economics methodology itself is
[`docs/PHASE2_EV_METHODOLOGY.md`](PHASE2_EV_METHODOLOGY.md) - synthesizes
Phase 0's temporal-movement finding and Phase 0.5's cross-bookmaker finding
into one retrospective EV test, with explicit guardrails against the
Max-selection-bias artifact Phase 0.5 already caught once and threshold/
timestamp cherry-picking. **Decision-snapshot ingestion is done**: 100%
coverage on all four decision offsets (T-24h/12h/6h/1h), 24,338 normalized
rows, zero EV/ROI computed (ingestion only, per scope). Caught and fixed a
real bug before spending budget: football-data.co.uk's kickoff time is UK
local (BST-aware), not UTC - see the methodology doc's "Ingestion result"
section. **The EV Backtest Runner is also done - result: NO EDGE** across all
32 segments (4 offsets x 2 candidate policies x 4 thresholds), none reaching
a 95%-CI-positive ROI. See the methodology doc's "EV Backtest result" section
for the full table and honest read (this is the third null/weak-or-null
result out of Phase 0-2's four hypothesis tests so far).

Question:

> If we predict line movement early, can that translate into positive expected value after vig?

Success criteria:

- positive CLV;
- positive or near-positive ROI;
- sufficient sample size;
- realistic bet-placement rate;
- no hidden threshold tuning.

### Phase 3: Paper-mode signal journal

Before any real betting, the system should run in paper mode.

It should log:

- match;
- timestamp;
- available data at that time;
- model/signal output;
- implied probability;
- bookmaker odds;
- hypothetical decision;
- closing odds;
- final result;
- profit/loss if paper bet existed.

The paper journal must be immutable enough to prevent hindsight editing.

This is also where most §4.3/§4.4 signals get their real validation, per the data
availability caveat in §4.3 - prospective collection, not retrospective backtesting.

### Phase 4: Legal betting workflow

Only much later.

Possible local context:

- Winner / Israeli legal sports betting channel;
- מפעל הפיס or related legal channels, if applicable;
- jurisdiction-specific legal review.

Before this phase:

- consult a lawyer;
- verify what is legal in Israel;
- verify platform terms;
- define bankroll risk;
- define account-limiting assumptions;
- decide whether real betting is even acceptable.

This phase is not approved by default.

## 6. Ethical and Legal Boundaries

The project may use:

- public odds;
- public match data;
- public news;
- a player/coach/club's own public statements and official social media;
- public reports.

The project must not use:

- hacked data;
- private accounts;
- leaked medical/private information;
- direct contact with players or relatives;
- intimidation, pressure, manipulation;
- automated stalking;
- hidden identity accounts;
- anything requiring platform abuse.

**Family and personal-circle monitoring is explicitly out of scope, not merely
"handle carefully."** An earlier draft of this document treated a player's family/
personal-circle public posts as a candidate signal source, gated by an ethical
framing ("a public post appears to suggest..." vs. "we know private facts"). That
framing was rejected on review: systematically mining a private individual's public
posts to infer something about someone else is a privacy harm in itself - the fact
that a post is technically public doesn't mean its author consented to being an
instrumented data point in someone else's research, commercial or not. This isn't a
question of degree or careful framing; it's excluded. If this is ever reconsidered,
it needs its own explicit decision and review, not a rewording of this section.

Allowed framing:

> "The player's own public statement suggests uncertainty/fatigue/injury context."

Not allowed:

> "A family member's post suggests X about the player" (any form) - or any use of
> non-public medical/family information, regardless of source.

The system must never expose unnecessary personal details in reports. Prefer aggregated signal labels over quoting or naming private individuals.

## 7. Research PR Checklist

Every research PR should be able to check these off - a checklist, not a narrative
essay to write out each time:

- [ ] Hypothesis stated in one sentence
- [ ] Look-ahead check: is this retrospective-only or genuinely live-tradeable?
- [ ] Data source and date range documented
- [ ] Dropped rows counted and reported (not silently discarded)
- [ ] Windows/thresholds pre-specified before looking at results (no post-hoc tuning)
- [ ] Sample size sufficient for the claim being made
- [ ] CI passing
- [ ] Negative/null results documented as prominently as positive ones

A result is not trusted just because tests pass.

## 8. Data Governance

Every data source needs metadata:

- source name;
- access method;
- timestamp;
- public/private classification;
- legal/terms risk;
- freshness;
- reliability;
- known gaps;
- whether it can be used historically;
- whether it can be used in paper/live mode.

For news/social data specifically, every extracted feature must include:

- source timestamp;
- collection timestamp;
- match timestamp;
- signal category;
- confidence;
- whether the information was available before market movement.

## 9. Architecture Roadmap

Same rule at every stage below, not just the first one: **don't build the next
stage's structure until real, repeated duplication in the current stage actually
forces it.** This roadmap describes what a stage looks like *if and when* it's
needed, not a schedule to build against.

### Stage 1: Simple Research Scripts

Current architecture, and the only one that exists today:

```text
src/football_odds_lab/
  data_sources/
  analysis/
scripts/
docs/
tests/
```

### Stage 2: Experiment Runner

Only once several experiments have real, repeated duplication in how they load data,
run a hypothesis, and write a report:

```text
configs/experiments/
src/football_odds_lab/experiments/
src/football_odds_lab/reporting/
fixtures/
```

Goal: repeatable experiments, standardized reports, easier comparison across
hypotheses.

### Stage 3: Signal Pipeline

Only once Phase 1's clean baseline (odds + match metadata) is done and has earned a
next signal to add. Modules for:

- odds movement features;
- news features;
- social signal features (player/coach/club official channels only - see §6);
- team/player context features;
- feature timestamp validation.

No live betting yet.

### Stage 4: Paper Journal

- daily candidate generation;
- timestamped signal snapshots;
- paper decisions;
- result reconciliation.

### Stage 5: Dashboard / Notion

Only after the research workflow is stable. Views:

- hypothesis results;
- signal history;
- paper-mode outcomes;
- CLV trends;
- ROI trends;
- sample size warnings;
- negative findings.

## 10. Success Metrics

Research success:

- positive out-of-sample CLV;
- positive or explainable ROI;
- stable performance across windows;
- low evidence of overfitting;
- honest negative findings.

Engineering success:

- clean CI;
- reproducible reports;
- small pure modules;
- documented methodology;
- easy PR review.

Product success:

- the project makes better research decisions;
- weak ideas are killed early;
- promising mechanisms are promoted carefully;
- no false confidence is created.

## 11. Immediate Next Steps

1. Keep Phase 0 and Phase 0.5 documented (done).
2. Define and build Phase 1's clean baseline: predict closing-line direction using
   only odds movement + match metadata, no external signals yet.
3. Add fixture-based tests for data loading/report generation once Stage 2 is
   actually warranted (see §9 - not before).
4. Start a "signal catalog" document (see §12) as candidate signals get added one at
   a time, not all at once.

## 12. Next Hypothesis Candidate

A good next hypothesis:

> Public pre-match information and early odds movement can predict future Pinnacle closing-line direction better than chance.

Initial simple version:

- no external signals yet;
- use only odds movement and match metadata;
- establish baseline.

Then add signals one at a time, from lowest to highest effort/risk, all within the
§6 boundary (official/public-figure sources only, never family/personal circle):

1. team/player injury news;
2. coach press conference signals;
3. local news sentiment;
4. official player/club social media channels.

Start with the cleanest measurable baseline. Don't add a new signal source until the
previous one has been evaluated on its own.

## 13. Final Principle

The project should be ambitious in data collection, but conservative in conclusions.

It is acceptable to observe many signals.

It is not acceptable to believe them without validation.

## 14. Deferred: "Public Context Intelligence Layer" (not scoped, not started)

Named and gated here so the direction isn't lost - not an approval to start building it.

- **Status: future research stream, not a current requirement.** Not scoped in
  detail, no code, no data collection. To be introduced later as its own document
  and its own PR, once the research base from earlier phases has proven itself -
  not on this PRD's current timeline.
- **Working name**: Public Context Intelligence Layer.
- **Stated guardrails**, to be re-reviewed in full before any actual scoping work
  starts:
  - only open public sources;
  - no private scraping, no bypassing logins, no fake accounts, no contact with people;
  - no storing excess personal detail;
  - no inferential claims about a specific person's private life (e.g. "player has
    a problem at home");
  - store only normalized signal labels (e.g. `morale_uncertainty`, `injury_hint`,
    `coach_pressure`, `travel_disruption`, `lineup_uncertainty`), never
    person-identifying narrative;
  - every signal timestamped by public-availability time;
  - validated only via out-of-sample effect on CLV/odds movement, never a post-hoc
    narrative.
- **Explicitly outside this repository and this collaboration**: any research
  involving monitoring family members' or a player's personal circle's own
  accounts. That, if it happens, is the user's own separate, personal work - not
  something built, documented, or reviewed as part of this project.

This section records that the topic exists and stays gated. It is not a queued
task.
