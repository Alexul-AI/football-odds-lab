"""Per-match decision timestamps and fetch-plan deduplication - pure, no I/O.

See docs/PHASE2_EV_METHODOLOGY.md's "Decision timestamps" and "Nearest snapshot
rule" sections. Many matches share a kickoff slot (multiple Saturday 3pm
fixtures, for example) - deduplicating by the resulting decision_timestamp
value means one API fetch can serve several matches at once, the same way one
snapshot already returns many events in the source spike (PR #14).
"""

from dataclasses import dataclass

import pandas as pd

DECISION_OFFSETS_HOURS = (24, 12, 6, 1)


@dataclass(frozen=True)
class DecisionPoint:
    match_index: int
    home_team: str
    away_team: str
    kickoff: pd.Timestamp
    offset_hours: int
    decision_timestamp: pd.Timestamp


def build_decision_points(
    football_data_df: pd.DataFrame, offsets_hours: tuple[int, ...] = DECISION_OFFSETS_HOURS
) -> list[DecisionPoint]:
    """football_data_df must have a `Kickoff` column (parsed datetime, combining
    Date + Time) and HomeTeam/AwayTeam. One DecisionPoint per (match, offset)."""
    points = []
    for idx, row in football_data_df.iterrows():
        for offset in offsets_hours:
            points.append(
                DecisionPoint(
                    match_index=idx,
                    home_team=row["HomeTeam"],
                    away_team=row["AwayTeam"],
                    kickoff=row["Kickoff"],
                    offset_hours=offset,
                    decision_timestamp=row["Kickoff"] - pd.Timedelta(hours=offset),
                )
            )
    return points


def group_by_unique_timestamp(points: list[DecisionPoint]) -> dict[pd.Timestamp, list[DecisionPoint]]:
    """The fetch plan: one API request per key, serving every DecisionPoint in
    its value list. len(result) * 10 credits is the real request-budget cost -
    the dry-run estimate is exactly `10 * len(group_by_unique_timestamp(...))`.
    """
    groups: dict[pd.Timestamp, list[DecisionPoint]] = {}
    for point in points:
        groups.setdefault(point.decision_timestamp, []).append(point)
    return groups
