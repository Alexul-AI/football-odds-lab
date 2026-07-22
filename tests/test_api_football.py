from football_odds_lab.data_sources.api_football import find_season_coverage, flatten_keys, has_api_errors


def _leagues_response() -> dict:
    return {
        "errors": [],
        "response": [
            {
                "league": {"id": 39, "name": "Premier League"},
                "seasons": [
                    {"year": 2022, "coverage": {"injuries": False}},
                    {"year": 2023, "coverage": {"injuries": True}},
                    {"year": 2025, "coverage": {"injuries": True}},
                ],
            }
        ],
    }


def test_find_season_coverage_returns_matching_season():
    coverage = find_season_coverage(_leagues_response(), 2023)
    assert coverage == {"injuries": True}


def test_find_season_coverage_distinguishes_true_false_by_season():
    assert find_season_coverage(_leagues_response(), 2022) == {"injuries": False}
    assert find_season_coverage(_leagues_response(), 2025) == {"injuries": True}


def test_find_season_coverage_none_when_season_absent():
    assert find_season_coverage(_leagues_response(), 1999) is None


def test_find_season_coverage_none_when_response_empty():
    assert find_season_coverage({"response": []}, 2023) is None


def test_has_api_errors_false_for_empty_list():
    assert has_api_errors({"errors": []}) is False


def test_has_api_errors_false_for_empty_dict():
    assert has_api_errors({"errors": {}}) is False


def test_has_api_errors_true_for_nonempty_list():
    assert has_api_errors({"errors": ["rate limit exceeded"]}) is True


def test_has_api_errors_true_for_nonempty_dict():
    assert has_api_errors({"errors": {"season": "should be numeric"}}) is True


def test_has_api_errors_false_when_field_missing():
    assert has_api_errors({}) is False


def test_flatten_keys_flat_record():
    assert flatten_keys({"type": "Injury", "reason": "Knee Injury"}) == {"type", "reason"}


def test_flatten_keys_nested_record_uses_dotted_paths():
    record = {"player": {"id": 1, "name": "Some Player"}, "type": "Injury"}
    assert flatten_keys(record) == {"player", "player.id", "player.name", "type"}


def test_flatten_keys_empty_record():
    assert flatten_keys({}) == set()
