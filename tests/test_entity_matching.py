import pandas as pd

from football_odds_lab.data_sources.entity_matching import match_event_to_football_data


def _football_data_df() -> pd.DataFrame:
    df = pd.DataFrame([
        {"HomeTeam": "Brentford", "AwayTeam": "Chelsea", "Date": "2024-03-02"},
        {"HomeTeam": "Man United", "AwayTeam": "Everton", "Date": "2024-03-09"},
        {"HomeTeam": "Nott'm Forest", "AwayTeam": "Liverpool", "Date": "2024-03-02"},
    ])
    df["Date"] = pd.to_datetime(df["Date"])
    return df


def test_matches_when_name_mapping_and_date_agree():
    result = match_event_to_football_data(
        "Brentford", "Chelsea", pd.Timestamp("2024-03-02T15:00:00Z"), _football_data_df()
    )
    assert result.matched is True
    assert result.football_data_home == "Brentford"
    assert result.football_data_away == "Chelsea"
    assert result.reason is None


def test_matches_full_name_variants_via_explicit_map():
    result = match_event_to_football_data(
        "Manchester United", "Everton", pd.Timestamp("2024-03-09T12:30:00Z"), _football_data_df()
    )
    assert result.matched is True
    assert result.football_data_home == "Man United"


def test_matches_nottingham_forest_abbreviation():
    result = match_event_to_football_data(
        "Nottingham Forest", "Liverpool", pd.Timestamp("2024-03-02T20:00:00Z"), _football_data_df()
    )
    assert result.matched is True
    assert result.football_data_home == "Nott'm Forest"


def test_unmatched_when_team_name_not_in_map():
    result = match_event_to_football_data(
        "Some New Club FC", "Chelsea", pd.Timestamp("2024-03-02T15:00:00Z"), _football_data_df()
    )
    assert result.matched is False
    assert "Some New Club FC" in result.reason


def test_unmatched_when_date_does_not_agree():
    # Same teams, mapped correctly, but no football-data.co.uk row on this date.
    result = match_event_to_football_data(
        "Brentford", "Chelsea", pd.Timestamp("2024-04-15T15:00:00Z"), _football_data_df()
    )
    assert result.matched is False
    assert "no football-data.co.uk row" in result.reason


def test_result_preserves_original_the_odds_api_names_even_when_matched():
    result = match_event_to_football_data(
        "Manchester United", "Everton", pd.Timestamp("2024-03-09T12:30:00Z"), _football_data_df()
    )
    # Original (unmapped) names stay on the record for audit/debugging purposes.
    assert result.the_odds_api_home == "Manchester United"
    assert result.football_data_home == "Man United"
