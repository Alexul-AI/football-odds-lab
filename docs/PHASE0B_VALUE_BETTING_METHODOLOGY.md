# Phase 0.5 methodology: cross-bookmaker value-betting test

Direct follow-up to `docs/PHASE0_METHODOLOGY.md`. That test found a statistically
significant effect, but it needed the closing line to pick which side to bet at the
opening price - not something available in real time. This test removes that flaw:
it only ever compares two prices that exist at the same moment, so nothing here
requires knowing the future.

## The hypothesis, precisely

For every match with complete `PSCH/PSCD/PSCA` (Pinnacle close) and retail closing
odds:

1. Treat Pinnacle's devigged closing probability as the fair-value reference.
2. Compare it against a retail closing price for the SAME outcome, SAME match, SAME
   point in time.
3. Compute `edge = fair_prob * retail_odds - 1` (expected value per unit stake).
4. Back the outcome with the highest edge, but only if it's `> 0`. Skip the match
   entirely otherwise - 0 is the natural break-even point, not a tuned threshold.

Run against two different retail price sources, deliberately, not one:

- **`MaxC*`** - the best closing price any tracked book offered per outcome.
- **`AvgC*`** - the average closing price across tracked books.

## Why both, and which one to trust

Taking the max across several books' quotes for each of the three outcomes
independently is not the same as one book's real, tradeable 3-way market. Combining
three independent maxima can push the blended implied probability below 100% even
when no single book, and no real market inefficiency, exists - **confirmed
empirically**: average `MaxC` overround across the dataset came out to **-0.55%**
(a real book's margin is never negative). This is a known artifact of "best of N
books" aggregation, not a data bug - but it means any edge measured against `Max` is
inflated by this selection effect, not just by real mispricing.

The diagnostic that confirms this in practice: betting against `Max` fired on
**91.8%** of matches. Real cross-book value betting should be rare - if it fires on
9 of 10 matches, the "edge" is almost certainly the selection artifact, not genuine
opportunity. `Avg` doesn't have this bias (it's a real average, not a maximum), fired
on only **3.6%** of matches - much more plausible for "genuine occasional
mispricing" - and is the number to actually trust.

## Data availability limitation (verified empirically 2026-07-21)

`MaxC*`/`AvgC*` columns do not exist on football-data.co.uk before the **2019-20**
season (confirmed absent in 2018-19 and earlier, present from 2019-20 onward) -
unlike `PSH/PSD/PSA/PSCH/PSCD/PSCA`, which go back to 2012-13. This test therefore
only has ~7 seasons to work with, not Phase 0's ~13. The two-window split for this
test is *not* at the same year as Phase 0's - it splits the one available range in
half instead, and both windows are correspondingly smaller and lower-power than
Phase 0's. This is a hard ceiling on this specific data source, the same kind of
limitation already hit once before (see `ai-trading-agent`'s own historical
out-of-sample data-floor finding) - not something to solve by asking for more days,
only by eventually finding a different historical odds source with a longer Max/Avg
history, if this line of research earns that investment.

## Result summary (first run, 2026-07-21)

- **`Max`**: pooled +0.13% (not significant). But the two windows flatly disagree in
  sign - Window A (seasons <2023) +5.23% (significant), Window B (seasons >=2023)
  **-9.77%** (also significant, negative). Significant-but-opposite-sign across
  windows is itself evidence of instability/artifact, not a real effect - consistent
  with the selection-bias mechanism above, not contradicting it.
- **`Avg` (the trustworthy one)**: pooled -2.43% (not significant, n=418, wide CI).
  Window A +13.29% (not significant), Window B -27.03% (not significant, p=0.06,
  small sample). No window clears this project's own bar of "positive AND
  significant."

**Read honestly: this test does not find a real, robust edge.** Unlike Phase 0's CLV
result, this more realistic, look-ahead-free test comes back essentially null. That's
a meaningful, useful finding on its own - it means "just compare Pinnacle's fair line
to retail closing prices" isn't itself a source of edge, at least not one this
dataset and this simple rule can detect. It does not, by itself, invalidate Phase 0's
finding (a different mechanism, direction-of-movement over time, not a snapshot
cross-book gap) - the two results answer different questions and should be read
side by side, not merged into one verdict.

## What this rules in and out for next steps

- **Rules out** (tentatively, one run): "shop for the best retail price and compare
  it to Pinnacle's fair close" as a standalone source of edge on this data.
- **Does not test**: whether an INDEPENDENT signal (news, lineups, model of your own)
  could find value ahead of when the market catches up - that's a different, harder
  question than "does the market already misprice itself against its own sharp
  reference," which is what both Phase 0 and Phase 0.5 have tested so far.
- **Does not test**: markets other than 1X2 (over/under, Asian handicap columns exist
  in the same files, untested).
