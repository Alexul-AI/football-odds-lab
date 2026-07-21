import json

from football_odds_lab.data_sources.the_odds_api import (
    PinnacleSnapshotRecord,
    extract_pinnacle_records,
    fetch_historical_snapshot,
)

# Trimmed, real structure - based on an actual response fetched 2026-07-21 for
# EPL fixtures around 2024-03-02 (see docs/PHASE2_SOURCE_SPIKE_PLAN.md). Two
# events: one with a Pinnacle price, one without, to exercise both paths.
SAMPLE_SNAPSHOT = {
    "timestamp": "2024-03-02T11:55:41Z",
    "previous_timestamp": "2024-03-02T11:50:39Z",
    "next_timestamp": "2024-03-02T12:00:40Z",
    "data": [
        {
            "id": "946a43585665587575794c942c4837c7",
            "sport_key": "soccer_epl",
            "commence_time": "2024-03-02T15:00:00Z",
            "home_team": "Brentford",
            "away_team": "Chelsea",
            "bookmakers": [
                {
                    "key": "betclic",
                    "markets": [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {"name": "Brentford", "price": 3.22},
                                {"name": "Chelsea", "price": 2.06},
                                {"name": "Draw", "price": 3.78},
                            ],
                        }
                    ],
                },
                {
                    "key": "pinnacle",
                    "markets": [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {"name": "Brentford", "price": 3.29},
                                {"name": "Chelsea", "price": 2.15},
                                {"name": "Draw", "price": 3.87},
                            ],
                        }
                    ],
                },
            ],
        },
        {
            "id": "no_pinnacle_here",
            "sport_key": "soccer_epl",
            "commence_time": "2024-03-13T19:30:00Z",
            "home_team": "Bournemouth",
            "away_team": "Luton",
            "bookmakers": [
                {
                    "key": "marathonbet",
                    "markets": [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {"name": "Bournemouth", "price": 1.5},
                                {"name": "Luton", "price": 6.0},
                                {"name": "Draw", "price": 4.2},
                            ],
                        }
                    ],
                },
            ],
        },
    ],
}


def test_extract_pinnacle_records_pulls_correct_prices():
    records = extract_pinnacle_records(SAMPLE_SNAPSHOT, fetched_at="2026-07-21T12:00:00Z")

    assert len(records) == 2
    brentford_chelsea = records[0]
    assert brentford_chelsea == PinnacleSnapshotRecord(
        source="the_odds_api",
        fetched_at="2026-07-21T12:00:00Z",
        snapshot_timestamp="2024-03-02T11:55:41Z",
        event_timestamp="2024-03-02T15:00:00Z",
        provider_fixture_id="946a43585665587575794c942c4837c7",
        home_team="Brentford",
        away_team="Chelsea",
        price_home=3.29,
        price_draw=3.87,
        price_away=2.15,
    )


def test_extract_pinnacle_records_none_when_pinnacle_absent():
    records = extract_pinnacle_records(SAMPLE_SNAPSHOT, fetched_at="2026-07-21T12:00:00Z")

    no_pinnacle_record = records[1]
    assert no_pinnacle_record.price_home is None
    assert no_pinnacle_record.price_draw is None
    assert no_pinnacle_record.price_away is None
    # Non-Pinnacle fields still populated - absence of Pinnacle shouldn't drop the event.
    assert no_pinnacle_record.home_team == "Bournemouth"
    assert no_pinnacle_record.provider_fixture_id == "no_pinnacle_here"


def test_fetch_historical_snapshot_uses_cache_without_network_call(tmp_path, monkeypatch):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    cache_file = cache_dir / "soccer_epl_2024-03-02T11-55-00Z_eu_h2h.json"
    cache_file.write_text(json.dumps(SAMPLE_SNAPSHOT), encoding="utf-8")

    def _fail_if_called(*args, **kwargs):
        raise AssertionError("fetch_historical_snapshot should not hit the network when cached")

    monkeypatch.setattr("football_odds_lab.data_sources.the_odds_api.requests.get", _fail_if_called)

    result = fetch_historical_snapshot(
        sport_key="soccer_epl",
        snapshot_datetime="2024-03-02T11:55:00Z",
        api_key="unused-because-cached",
        cache_dir=cache_dir,
    )

    assert result == SAMPLE_SNAPSHOT


def test_fetch_historical_snapshot_never_writes_api_key_to_cache(tmp_path, monkeypatch):
    cache_dir = tmp_path / "cache"

    class _FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return SAMPLE_SNAPSHOT

    captured_params = {}

    def _fake_get(url, params, timeout):
        captured_params.update(params)
        return _FakeResponse()

    monkeypatch.setattr("football_odds_lab.data_sources.the_odds_api.requests.get", _fake_get)

    fetch_historical_snapshot(
        sport_key="soccer_epl",
        snapshot_datetime="2024-03-02T11:55:00Z",
        api_key="totally-secret-key",
        cache_dir=cache_dir,
    )

    cache_files = list(cache_dir.glob("*.json"))
    assert len(cache_files) == 1
    assert "totally-secret-key" not in cache_files[0].read_text(encoding="utf-8")
    assert captured_params["apiKey"] == "totally-secret-key"  # the request itself does need it
