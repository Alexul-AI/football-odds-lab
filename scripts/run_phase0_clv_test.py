"""Phase 0: run the CLV hypothesis test across the top-5 European leagues.

Usage:
    python scripts/run_phase0_clv_test.py

Downloads (and caches under data/raw/) football-data.co.uk history for the five
top-5 leagues from the earliest season with verified Pinnacle opening+closing
columns (2012-13) through the latest completed season, runs the single
pre-specified CLV bet rule from football_odds_lab.analysis.clv_hypothesis on
every match, and writes an honest markdown report to reports/.

See docs/PHASE0_METHODOLOGY.md for what this test does and does not show.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from football_odds_lab.analysis.betting_stats import HypothesisTestResult, summarize_bets
from football_odds_lab.analysis.clv_hypothesis import select_bet_and_profit
from football_odds_lab.analysis.odds_math import overround
from football_odds_lab.data_sources.football_data_co_uk import EARLIEST_SEASON_START_YEAR, LEAGUES, download_all

REPO_ROOT = Path(__file__).resolve().parent.parent
REQUIRED_COLUMNS = ["PSH", "PSD", "PSA", "PSCH", "PSCD", "PSCA", "FTR"]

# First season (start year) after which non-overlapping window B begins.
# Chosen as the midpoint of the validated 2012-13..latest range, not tuned on results.
WINDOW_SPLIT_YEAR = 2019


def load_dataset(cache_dir: Path) -> pd.DataFrame:
    df = download_all(cache_dir=cache_dir, start_year=EARLIEST_SEASON_START_YEAR)
    before = len(df)
    df = df.dropna(subset=REQUIRED_COLUMNS).reset_index(drop=True)
    dropped = before - len(df)
    if dropped:
        print(f"Dropped {dropped}/{before} rows missing required odds/result columns.", file=sys.stderr)
    return df


def run_bets(df: pd.DataFrame) -> tuple[list, pd.DataFrame]:
    bets = []
    for row in df.itertuples(index=False):
        open_odds = {"H": row.PSH, "D": row.PSD, "A": row.PSA}
        close_odds = {"H": row.PSCH, "D": row.PSCD, "A": row.PSCA}
        bets.append(select_bet_and_profit(open_odds, close_odds, actual_result=row.FTR))

    bets_df = df.assign(
        bet_side=[b.side for b in bets],
        bet_clv_edge=[b.clv_edge for b in bets],
        bet_odds_at_open=[b.odds_at_open for b in bets],
        bet_won=[b.won for b in bets],
        bet_profit=[b.profit for b in bets],
    )
    return bets, bets_df


def format_result_line(label: str, result: HypothesisTestResult) -> str:
    significant = "yes" if result.p_value < 0.05 else "no"
    return (
        f"| {label} | {result.n_bets} | {result.roi:+.2%} | {result.win_rate:.1%} | "
        f"{result.mean_profit_per_bet:+.4f} | [{result.ci_95_low:+.4f}, {result.ci_95_high:+.4f}] | "
        f"{result.p_value:.4f} | {significant} |"
    )


def main() -> None:
    cache_dir = REPO_ROOT / "data" / "raw"
    reports_dir = REPO_ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    df = load_dataset(cache_dir)
    bets, bets_df = run_bets(df)

    overall = summarize_bets(bets)

    window_a_mask = df["SeasonStartYear"] < WINDOW_SPLIT_YEAR
    window_a = summarize_bets([b for b, keep in zip(bets, window_a_mask) if keep])
    window_b = summarize_bets([b for b, keep in zip(bets, ~window_a_mask) if keep])

    per_league = {}
    for league_code in LEAGUES:
        league_mask = df["League"] == league_code
        league_bets = [b for b, keep in zip(bets, league_mask) if keep]
        if league_bets:
            per_league[league_code] = summarize_bets(league_bets)

    avg_open_overround = df.apply(lambda r: overround([r.PSH, r.PSD, r.PSA]), axis=1).mean()
    avg_close_overround = df.apply(lambda r: overround([r.PSCH, r.PSCD, r.PSCA]), axis=1).mean()

    lines = [
        "# Phase 0 CLV Hypothesis Test Report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Seasons: {EARLIEST_SEASON_START_YEAR}-{EARLIEST_SEASON_START_YEAR + 1} through "
        f"{df['SeasonStartYear'].max()}-{df['SeasonStartYear'].max() + 1}",
        f"Leagues: {', '.join(f'{code} ({name})' for code, name in LEAGUES.items())}",
        f"Matches after filtering for complete Pinnacle open+close odds: {len(df)}",
        "",
        "## Hypothesis under test",
        "",
        "Back the 1X2 outcome that Pinnacle's own devigged probability moved toward "
        "the most between their opening and closing snapshot, at the OPENING price, "
        "flat 1-unit stake, no threshold filter, on every match. Test whether mean "
        "profit per bet is significantly different from zero.",
        "",
        "**This is not a live-tradeable strategy.** It uses the closing line - which "
        "doesn't exist yet at the time you'd place the bet - to pick which side to "
        "back. It answers a narrower, necessary-precondition question: does exploitable "
        "inefficiency between Pinnacle's open and close exist at all, net of vig, with "
        "perfect hindsight of its direction? See docs/PHASE0_METHODOLOGY.md.",
        "",
        f"Sanity check - average Pinnacle overround: {avg_open_overround:.2%} (opening), "
        f"{avg_close_overround:.2%} (closing). Expected ~2-4% for a sharp book; if this "
        "is much higher, something is off with the column mapping above.",
        "",
        "## Results",
        "",
        "| Segment | N bets | ROI | Win rate | Mean profit/bet | 95% CI | p-value | "
        "Significant (p<0.05) |",
        "|---|---|---|---|---|---|---|---|",
        format_result_line("**Overall (pooled)**", overall),
        format_result_line(f"Window A (seasons < {WINDOW_SPLIT_YEAR})", window_a),
        format_result_line(f"Window B (seasons >= {WINDOW_SPLIT_YEAR})", window_b),
    ]
    for league_code, result in per_league.items():
        lines.append(format_result_line(f"{league_code} ({LEAGUES[league_code]})", result))

    lines += [
        "",
        "## Read this honestly",
        "",
        "- A positive, significant ROI in the pooled row and in BOTH non-overlapping "
        "windows is the bar for 'this looks like a real, robust effect worth a second "
        "look.' One window positive and one negative/flat means inconclusive, not confirmed.",
        "- Per-league rows are for context, not for picking whichever league happened to "
        "look best after the fact - that would be exactly the narrative-fitting this "
        "project's own methodology forbids.",
        "- p-value here tests 'mean profit per bet != 0' via a one-sample t-test on the "
        "profit series - a standard, defensible test at this sample size, not a "
        "guarantee against all forms of multiple-comparison risk across leagues/windows "
        "shown in this same table.",
    ]

    report_path = reports_dir / "phase0-clv-report.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    bets_df.to_csv(reports_dir / "phase0-clv-bets.csv", index=False)

    print("\n".join(lines))
    print(f"\nFull report written to {report_path}")


if __name__ == "__main__":
    main()
