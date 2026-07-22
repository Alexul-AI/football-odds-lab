import pandas as pd

from football_odds_lab.analysis.decision_snapshot_extraction import (
    DEFAULT_STALENESS_TOLERANCE_HOURS,
    extract_decision_records_for_point,
    find_event_for_match,
    is_snapshot_valid_for_decision,
)

RAW_SNAPSHOT_BEFORE = {
    "timestamp": "2024-03-02T08:00:00Z",  # 1h before the decision point below
    "data": [
        {
            "id": "evt123",
            "home_team": "Brentford",
            "away_team": "Chelsea",
            "commence_time": "2024-03-02T15:00:00Z",
            "bookmakers": [
                {
                    "key": "pinnacle",
                    "markets": [{"key": "h2h", "outcomes": [
                        {"name": "Brentford", "price": 3.29},
                        {"name": "Chelsea", "price": 2.15},
                        {"name": "Draw", "price": 3.87},
                    ]}],
                },
                {
                    "key": "williamhill",
                    "markets": [{"key": "h2h", "outcomes": [
                        {"name": "Brentford", "price": 3.10},
                        {"name": "Chelsea", "price": 2.20},
                        {"name": "Draw", "price": 3.75},
                    ]}],
                },
            ],
        }
    ],
}

DECISION_TIMESTAMP = pd.Timestamp("2024-03-02T09:00:00Z")  # 1h after the snapshot above


def test_is_snapshot_valid_when_strictly_before():
    assert is_snapshot_valid_for_decision(pd.Timestamp("2024-03-02T08:00:00Z"), DECISION_TIMESTAMP) is True


def test_is_snapshot_valid_when_exactly_equal():
    assert is_snapshot_valid_for_decision(DECISION_TIMESTAMP, DECISION_TIMESTAMP) is True


def test_is_snapshot_invalid_when_after_even_by_a_minute():
    # The leakage rule: after the decision point is always rejected, no matter
    # how close - this is the test the QA gate explicitly required.
    after = DECISION_TIMESTAMP + pd.Timedelta(minutes=1)
    assert is_snapshot_valid_for_decision(after, DECISION_TIMESTAMP) is False


def test_is_snapshot_invalid_when_too_stale():
    too_old = DECISION_TIMESTAMP - pd.Timedelta(hours=DEFAULT_STALENESS_TOLERANCE_HOURS + 1)
    assert is_snapshot_valid_for_decision(too_old, DECISION_TIMESTAMP) is False


def test_is_snapshot_valid_at_exactly_the_staleness_boundary():
    boundary = DECISION_TIMESTAMP - pd.Timedelta(hours=DEFAULT_STALENESS_TOLERANCE_HOURS)
    assert is_snapshot_valid_for_decision(boundary, DECISION_TIMESTAMP) is True


def test_find_event_for_match_maps_the_odds_api_name_to_football_data_name():
    event = find_event_for_match(RAW_SNAPSHOT_BEFORE["data"], "Brentford", "Chelsea")
    assert event is not None
    assert event["id"] == "evt123"


def test_find_event_for_match_returns_none_when_not_present():
    event = find_event_for_match(RAW_SNAPSHOT_BEFORE["data"], "Arsenal", "Everton")
    assert event is None


def test_extract_decision_records_returns_one_row_per_bookmaker():
    records = extract_decision_records_for_point(
        RAW_SNAPSHOT_BEFORE, "Brentford", "Chelsea", DECISION_TIMESTAMP, decision_offset_hours=1, fetched_at="now"
    )
    assert len(records) == 2
    bookmakers = {r.bookmaker for r in records}
    assert bookmakers == {"pinnacle", "williamhill"}

    pinnacle_row = next(r for r in records if r.bookmaker == "pinnacle")
    assert pinnacle_row.price_home == 3.29
    assert pinnacle_row.price_draw == 3.87
    assert pinnacle_row.price_away == 2.15
    assert pinnacle_row.decision_offset_hours == 1
    assert pinnacle_row.home_team == "Brentford"  # football-data.co.uk-style name preserved


def test_extract_decision_records_empty_when_snapshot_is_after_decision_timestamp():
    # The leakage rule applied end-to-end: a snapshot from AFTER the decision
    # point must never contribute records, even though the match/bookmaker
    # data is otherwise perfectly valid.
    leaky_snapshot = {**RAW_SNAPSHOT_BEFORE, "timestamp": "2024-03-02T10:00:00Z"}  # 1h AFTER decision point
    records = extract_decision_records_for_point(
        leaky_snapshot, "Brentford", "Chelsea", DECISION_TIMESTAMP, decision_offset_hours=1, fetched_at="now"
    )
    assert records == []


def test_extract_decision_records_empty_when_match_not_found():
    records = extract_decision_records_for_point(
        RAW_SNAPSHOT_BEFORE, "Arsenal", "Everton", DECISION_TIMESTAMP, decision_offset_hours=1, fetched_at="now"
    )
    assert records == []


def test_extract_decision_records_skips_bookmaker_missing_a_full_outcome_set():
    incomplete_snapshot = {
        "timestamp": "2024-03-02T08:00:00Z",
        "data": [{
            "id": "evt456",
            "home_team": "Brentford",
            "away_team": "Chelsea",
            "commence_time": "2024-03-02T15:00:00Z",
            "bookmakers": [{
                "key": "sketchybook",
                "markets": [{"key": "h2h", "outcomes": [
                    {"name": "Brentford", "price": 3.0},
                    {"name": "Chelsea", "price": 2.0},
                    # Draw missing - malformed/partial data, should be skipped not crash
                ]}],
            }],
        }],
    }
    records = extract_decision_records_for_point(
        incomplete_snapshot, "Brentford", "Chelsea", DECISION_TIMESTAMP, decision_offset_hours=1, fetched_at="now"
    )
    assert records == []
