"""Phase 0.5: run the cross-bookmaker value-betting test (no look-ahead).

Usage:
    python scripts/run_phase0b_value_betting_test.py

Reuses the same cached historical data as run_phase0_clv_test.py. Compares
Pinnacle's closing devigged probability (PSC*) against a retail closing price for
the same match, at the same point in time - unlike the Phase 0 CLV test, nothing
here requires knowing the future.

Runs TWO market sources, not one:

- Max (MaxC*): the best closing price any tracked retail book offered per outcome.
  Mechanically biased toward showing "value" - taking the max of several noisy
  quotes tends to beat a single reference price even with zero real edge, purely
  because it's a maximum over several books, not necessarily any one achievable book.
- Avg (AvgC*): the average closing price across tracked retail books. Doesn't have
  that selection bias, so it's the more trustworthy read of whether real cross-book
  mispricing exists - Max is included for context, not as the primary result.

See docs/PHASE0B_VALUE_BETTING_METHODOLOGY.md for the full reasoning.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from football_odds_lab.analysis.betting_stats import HypothesisTestResult, summarize_bets
from football_odds_lab.analysis.odds_math import devig_multiplicative, overround
from football_odds_lab.analysis.value_betting_hypothesis import DevigFn, ValueBet, select_value_bet
from football_odds_lab.data_sources.football_data_co_uk import EARLIEST_SEASON_START_YEAR, LEAGUES, download_all

REPO_ROOT = Path(__file__).resolve().parent.parent

# MaxC*/AvgC* columns only exist from the 2019-20 season onward (verified empirically
# 2026-07-21 - absent in 2018-19 and earlier, present from 2019-20). Unlike the Phase 0
# CLV test's 2012-2025 range, there's no room for a symmetric multi-season split here -
# this splits the one available ~7-season range roughly in half instead.
WINDOW_SPLIT_YEAR = 2023

MARKET_SOURCES = {
    "Max": ("MaxCH", "MaxCD", "MaxCA"),
    "Avg": ("AvgCH", "AvgCD", "AvgCA"),
}
FAIR_COLUMNS = ("PSCH", "PSCD", "PSCA")
REQUIRED_COLUMNS = [*FAIR_COLUMNS, *MARKET_SOURCES["Max"], *MARKET_SOURCES["Avg"], "FTR"]


def load_dataset(cache_dir: Path) -> pd.DataFrame:
    df = download_all(cache_dir=cache_dir, start_year=EARLIEST_SEASON_START_YEAR)
    before = len(df)
    df = df.dropna(subset=REQUIRED_COLUMNS).reset_index(drop=True)
    dropped = before - len(df)
    if dropped:
        print(f"Dropped {dropped}/{before} rows missing required odds/result columns.", file=sys.stderr)
    return df


def run_bets(
    df: pd.DataFrame, market_columns: tuple[str, str, str], devig_fn: DevigFn = devig_multiplicative
) -> list[ValueBet | None]:
    """devig_fn defaults to devig_multiplicative (this script's original,
    still-canonical behavior, unchanged). Passing odds_math.devig_shin
    instead re-runs this exact test as a favorite-longshot-bias-corrected
    robustness check - see scripts/run_shin_devig_robustness_check.py."""
    h_col, d_col, a_col = market_columns
    bets: list[ValueBet | None] = []
    for row in df.itertuples(index=False):
        fair_odds = {"H": row.PSCH, "D": row.PSCD, "A": row.PSCA}
        market_odds = {"H": getattr(row, h_col), "D": getattr(row, d_col), "A": getattr(row, a_col)}
        bets.append(select_value_bet(fair_odds, market_odds, actual_result=row.FTR, devig_fn=devig_fn))
    return bets


def summarize_or_none(bets: list[ValueBet]) -> HypothesisTestResult | None:
    return summarize_bets(bets) if bets else None


def format_result_line(label: str, result: HypothesisTestResult | None, n_matches: int) -> str:
    if result is None or result.n_bets == 0:
        return f"| {label} | 0 / {n_matches} | - | - | - | - | - | - |"
    significant = "yes" if result.p_value < 0.05 else "no"
    return (
        f"| {label} | {result.n_bets} / {n_matches} | {result.roi:+.2%} | {result.win_rate:.1%} | "
        f"{result.mean_profit_per_bet:+.4f} | [{result.ci_95_low:+.4f}, {result.ci_95_high:+.4f}] | "
        f"{result.p_value:.4f} | {significant} |"
    )


def build_results_table(df: pd.DataFrame, all_bets: list[ValueBet | None]) -> list[str]:
    placed_bets = [b for b in all_bets if b is not None]
    overall = summarize_or_none(placed_bets)

    window_a_mask = df["SeasonStartYear"] < WINDOW_SPLIT_YEAR
    window_a_bets = [b for b, keep in zip(all_bets, window_a_mask) if keep and b is not None]
    window_b_bets = [b for b, keep in zip(all_bets, ~window_a_mask) if keep and b is not None]

    lines = [
        f"Bets placed (edge > 0 on at least one outcome): {len(placed_bets)} "
        f"({len(placed_bets) / len(df):.1%} of matches)",
        "",
        "| Segment | N bets / N matches | ROI | Win rate | Mean profit/bet | 95% CI | "
        "p-value | Significant (p<0.05) |",
        "|---|---|---|---|---|---|---|---|",
        format_result_line("**Overall (pooled)**", overall, len(df)),
        format_result_line(
            f"Window A (seasons < {WINDOW_SPLIT_YEAR})", summarize_or_none(window_a_bets), int(window_a_mask.sum())
        ),
        format_result_line(
            f"Window B (seasons >= {WINDOW_SPLIT_YEAR})",
            summarize_or_none(window_b_bets),
            int((~window_a_mask).sum()),
        ),
    ]
    for league_code in LEAGUES:
        league_mask = df["League"] == league_code
        league_bets = [b for b, keep in zip(all_bets, league_mask) if keep and b is not None]
        lines.append(format_result_line(f"{league_code} ({LEAGUES[league_code]})", summarize_or_none(league_bets), int(league_mask.sum())))
    return lines


def main() -> None:
    cache_dir = REPO_ROOT / "data" / "raw"
    reports_dir = REPO_ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    df = load_dataset(cache_dir)
    avg_fair_overround = df.apply(lambda r: overround([r.PSCH, r.PSCD, r.PSCA]), axis=1).mean()

    lines = [
        "# Phase 0.5 Value-Betting Hypothesis Test Report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Seasons: {EARLIEST_SEASON_START_YEAR}-{EARLIEST_SEASON_START_YEAR + 1} through "
        f"{df['SeasonStartYear'].max()}-{df['SeasonStartYear'].max() + 1}",
        f"Leagues: {', '.join(f'{code} ({name})' for code, name in LEAGUES.items())}",
        f"Matches after filtering for complete Pinnacle-close + Max/Avg-close odds: {len(df)}",
        "",
        "**Data limitation, not a bug**: `MaxC*`/`AvgC*` columns only exist from the "
        "2019-20 season onward on football-data.co.uk (verified empirically - absent "
        "2018-19 and earlier). So unlike the Phase 0 CLV test's 2012-2025 range, this "
        "test only has ~7 seasons total to work with, split in half below rather than "
        "at the same year Phase 0 used. Both windows here are much smaller than Phase "
        "0's - read the significance results accordingly, they have less statistical "
        "power to begin with.",
        "",
        "## Hypothesis under test",
        "",
        "Treat Pinnacle's closing devigged probability as the fair-value reference. "
        "Compare it against a retail closing price for the SAME match at the SAME "
        "point in time - no look-ahead. Back the outcome with the highest positive "
        "expected value; skip the match if no outcome clears EV > 0 (the natural "
        "break-even point, not a tuned threshold). Run twice, against `Max` and "
        "`Avg` closing prices - see the module docstring and "
        "docs/PHASE0B_VALUE_BETTING_METHODOLOGY.md for why both are shown and which "
        "one to actually trust.",
        "",
        f"Sanity check - average Pinnacle-close overround: {avg_fair_overround:.2%} "
        "(expected ~2-4%, confirms the fair-value reference column mapping is sane).",
        "",
    ]

    for source_name, market_columns in MARKET_SOURCES.items():
        avg_market_overround = df.apply(lambda r, cols=market_columns: overround([getattr(r, c) for c in cols]), axis=1).mean()
        bets = run_bets(df, market_columns)

        lines.append(f"## Results - vs {source_name} closing price")
        lines.append("")
        lines.append(f"Average {source_name} overround: {avg_market_overround:.2%}.")
        if source_name == "Max":
            lines.append(
                "Negative or near-zero here is EXPECTED, not a bug: this is the max "
                "closing price per outcome across several books, so combining three "
                "independent maxima can easily push the blended implied probability "
                "below 100% even with no real edge anywhere - this is exactly why the "
                "Max results below should be treated as upper-bound/context, not the "
                "real answer."
            )
        lines.append("")
        lines.extend(build_results_table(df, bets))
        lines.append("")

        bets_df = df.assign(
            bet_side=[b.side if b else None for b in bets],
            bet_edge=[b.edge if b else None for b in bets],
            bet_odds=[b.odds if b else None for b in bets],
            bet_won=[b.won if b else None for b in bets],
            bet_profit=[b.profit if b else None for b in bets],
        )
        bets_df.to_csv(reports_dir / f"phase0b-value-betting-bets-{source_name.lower()}.csv", index=False)

    lines += [
        "## Read this honestly",
        "",
        "- The `Avg` table is the one to trust; `Max` is shown for context and is "
        "expected to look more favorable than reality purely from the "
        "best-of-several-books selection effect described above, not from real edge.",
        "- Same bar as Phase 0: a positive, significant ROI in the pooled row AND in "
        "BOTH non-overlapping windows is 'worth a second look.' One window positive "
        "and one negative/flat is inconclusive.",
        "- A near-100% bet-placement rate (as seen for `Max`) is itself a diagnostic "
        "that the EV signal is dominated by the selection artifact above, not by rare, "
        "genuine mispricing - real value bets should be uncommon, not on 9 of 10 matches.",
        "- This result should be read against the Phase 0 CLV report, not in isolation - "
        "the interesting comparison is whether a look-ahead-free test still finds value, "
        "not whether this one number alone looks good.",
    ]

    report_path = reports_dir / "phase0b-value-betting-report.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n".join(lines))
    print(f"\nFull report written to {report_path}")


if __name__ == "__main__":
    main()
