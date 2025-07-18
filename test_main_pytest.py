import pytest
import os
import json
import main
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def setup_and_teardown(tmp_path, monkeypatch):
    # Patch CACHE_DIR to use a temp dir
    monkeypatch.setattr(main, "CACHE_DIR", str(tmp_path))
    os.makedirs(main.CACHE_DIR, exist_ok=True)
    yield
    # Clean up cache files
    for f in os.listdir(main.CACHE_DIR):
        os.remove(os.path.join(main.CACHE_DIR, f))


@pytest.mark.parametrize(
    "code,expected",
    [
        ("GB", "🇬🇧"),
        ("DE", "🇩🇪"),
        ("US", "🇺🇸"),
    ],
)
def test_country_code_to_flag_standard(code, expected):
    assert main.country_code_to_flag(code) == expected


@pytest.mark.parametrize(
    "code,expected",
    [
        ("KSA", "🇸🇦"),
        ("MON", "🇲🇨"),
        ("UAE", "🇦🇪"),
    ],
)
def test_country_code_to_flag_manual_map(code, expected):
    assert main.country_code_to_flag(code) == expected


@pytest.mark.parametrize("code", [None, "ZZZ", "123"])
def test_country_code_to_flag_invalid(code):
    assert main.country_code_to_flag(code) == ""


def test_load_and_save_cache():
    data = {"foo": "bar"}
    fname = "test_cache.json"
    main.save_cache(fname, data)
    loaded = main.load_cache(fname)
    assert data == loaded


@patch("main.requests.get")
def test_get_races_and_results(mock_get):
    # Mock race sessions
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = [
        {"session_key": 1, "date_start": "2025-01-01", "meeting_name": "Test GP"},
        {"session_key": 2, "date_start": "2025-02-01", "meeting_name": "Test GP2"},
    ]
    races = main.get_races(2025, force_update=True)
    assert len(races) == 2
    assert races[0]["session_key"] == 1

    # Mock race results
    mock_get.return_value.json.return_value = [
        {"driver_number": 44, "position": 1},
        {"driver_number": 33, "position": 2},
    ]
    results = main.get_race_results(1)
    assert len(results) == 2
    assert results[0]["driver_number"] == 44


@patch("main.requests.get")
def test_get_driver_map(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = [{"full_name": "Lewis Hamilton"}]
    pairs = [(44, 1)]
    driver_map = main.get_driver_map(pairs)
    assert driver_map[("44", "1")] == "Lewis Hamilton"


@patch("main.get_race_results")
def test_calculate_standings(mock_results):
    races = [
        {"session_key": 1, "meeting_name": "Test GP"},
        {"session_key": 2, "meeting_name": "Test GP2"},
    ]
    driver_map = {"44": "Lewis Hamilton", "33": "Max Verstappen"}
    mock_results.side_effect = [
        [
            {"driver_number": 44, "position": 1, "points": 25},
            {"driver_number": 33, "position": 2, "points": 18},
        ],
        [
            {"driver_number": 33, "position": 1, "points": 25},
            {"driver_number": 44, "position": 2, "points": 18},
        ],
    ]
    standings, race_names, driver_names = main.calculate_standings(races, driver_map)
    assert standings[-1]["Lewis Hamilton"] == 43
    assert standings[-1]["Max Verstappen"] == 43
    assert "Test GP" in race_names[0]
    assert "Lewis Hamilton" in driver_names


def test_season_to_chart():
    assert main.season_to_chart(2025) == 2025
    assert main.season_to_chart(None) == int(str(main.datetime.now().year))


def test_load_cache_missing_file():
    assert main.load_cache("nonexistent_cache.json") is None


def test_load_cache_invalid_json(tmp_path):
    fname = "invalid_cache.json"
    cache_dir = main.CACHE_DIR
    with open(os.path.join(cache_dir, fname), "w") as f:
        f.write("not a json")
    with pytest.raises(json.JSONDecodeError):
        main.load_cache(fname)


@patch("main.requests.get")
def test_get_races_api_error(mock_get):
    mock_get.return_value.status_code = 500
    mock_get.return_value.raise_for_status.side_effect = Exception("API error")
    with pytest.raises(Exception):
        main.get_races(2025, force_update=True)


@patch("main.requests.get")
def test_get_race_results_api_error(mock_get):
    mock_get.return_value.status_code = 500
    mock_get.return_value.raise_for_status.side_effect = Exception("API error")
    with pytest.raises(Exception):
        main.get_race_results(1)


@patch("main.requests.get")
def test_get_driver_map_rate_limit(mock_get):
    resp_429 = MagicMock()
    resp_429.status_code = 429
    resp_429.json.return_value = []
    resp_429.raise_for_status.side_effect = None
    resp_200 = MagicMock()
    resp_200.status_code = 200
    resp_200.json.return_value = [{"full_name": "Test Driver"}]
    resp_200.raise_for_status.side_effect = None
    mock_get.side_effect = [resp_429, resp_200]
    pairs = [(99, 1)]
    driver_map = main.get_driver_map(pairs, max_retries=2)
    assert driver_map[("99", "1")] == "Test Driver"


@patch("main.pd.DataFrame")
def test_plot_standings(mock_df):
    mock_df.return_value.ffill.return_value.fillna.return_value = mock_df.return_value
    mock_df.return_value.melt.return_value = mock_df.return_value
    mock_fig = MagicMock()
    with patch("main.px.line", return_value=mock_fig):
        main.plot_standings([{"A": 1}], ["Race1"], ["A"])
        mock_fig.write_html.assert_called_once()


@patch(
    "main.argparse.ArgumentParser.parse_args",
    return_value=type("Args", (), {"year": 2025, "force_update": False})(),
)
def test_main_flow(mock_args):
    with (
        patch(
            "main.get_races",
            return_value=[{"session_key": 1, "meeting_name": "Test GP"}],
        ),
        patch(
            "main.get_race_results",
            return_value=[{"driver_number": 44, "position": 1}],
        ),
        patch("main.get_driver_map", return_value={("44", "1"): "Lewis Hamilton"}),
        patch("main.plot_standings") as mock_plot,
    ):
        main.main()
        mock_plot.assert_called_once()
