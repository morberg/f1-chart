import unittest
from unittest.mock import patch, mock_open, MagicMock
import main
import os
import json


class TestMain(unittest.TestCase):
    def setUp(self):
        self.cache_dir = main.CACHE_DIR
        os.makedirs(self.cache_dir, exist_ok=True)

    def tearDown(self):
        # Clean up cache files created during tests
        for f in os.listdir(self.cache_dir):
            os.remove(os.path.join(self.cache_dir, f))

    def test_load_and_save_cache(self):
        data = {"foo": "bar"}
        fname = "test_cache.json"
        main.save_cache(fname, data)
        loaded = main.load_cache(fname)
        self.assertEqual(data, loaded)

    def test_country_code_to_flag_standard(self):
        self.assertEqual(main.country_code_to_flag("GB"), "🇬🇧")
        self.assertEqual(main.country_code_to_flag("DE"), "🇩🇪")
        self.assertEqual(main.country_code_to_flag("US"), "🇺🇸")

    def test_country_code_to_flag_manual_map(self):
        self.assertEqual(main.country_code_to_flag("KSA"), "🇸🇦")
        self.assertEqual(main.country_code_to_flag("MON"), "🇲🇨")
        self.assertEqual(main.country_code_to_flag("UAE"), "🇦🇪")

    def test_country_code_to_flag_invalid(self):
        self.assertEqual(main.country_code_to_flag(None), "")
        self.assertEqual(main.country_code_to_flag("ZZZ"), "")
        self.assertEqual(main.country_code_to_flag("123"), "")

    @patch("main.requests.get")
    def test_get_races_and_results(self, mock_get):
        # Mock race sessions
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [
            {"session_key": 1, "date_start": "2025-01-01", "meeting_name": "Test GP"},
            {"session_key": 2, "date_start": "2025-02-01", "meeting_name": "Test GP2"},
        ]
        races = main.get_races(2025, force_update=True)
        self.assertEqual(len(races), 2)
        self.assertEqual(races[0]["session_key"], 1)

        # Mock race results
        mock_get.return_value.json.return_value = [
            {"driver_number": 44, "position": 1},
            {"driver_number": 33, "position": 2},
        ]
        results = main.get_race_results(1)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["driver_number"], 44)

    @patch("main.requests.get")
    def test_get_driver_map(self, mock_get):
        # Mock driver API response
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [{"full_name": "Lewis Hamilton"}]
        pairs = [(44, 1)]
        driver_map = main.get_driver_map(pairs)
        self.assertEqual(driver_map[("44", "1")], "Lewis Hamilton")

    def test_calculate_standings(self):
        # Use sample races and driver map
        races = [
            {"session_key": 1, "meeting_name": "Test GP"},
            {"session_key": 2, "meeting_name": "Test GP2"},
        ]
        driver_map = {"44": "Lewis Hamilton", "33": "Max Verstappen"}
        # Patch get_race_results to return fixed results
        with patch("main.get_race_results") as mock_results:
            mock_results.side_effect = [
                [
                    {"driver_number": 44, "position": 1},
                    {"driver_number": 33, "position": 2},
                ],
                [
                    {"driver_number": 33, "position": 1},
                    {"driver_number": 44, "position": 2},
                ],
            ]
            standings, race_names, driver_names = main.calculate_standings(
                races, driver_map
            )
            self.assertEqual(standings[-1]["Lewis Hamilton"], 43)  # 25+18
            self.assertEqual(standings[-1]["Max Verstappen"], 43)  # 18+25
            self.assertIn("Test GP", race_names[0])
            self.assertIn("Lewis Hamilton", driver_names)

    def test_season_to_chart(self):
        self.assertEqual(main.season_to_chart(2025), 2025)
        # Should default to current year if None
        self.assertEqual(main.season_to_chart(None), int(str(main.datetime.now().year)))

    def test_load_cache_missing_file(self):
        # Should return None if file does not exist
        self.assertIsNone(main.load_cache("nonexistent_cache.json"))

    def test_load_cache_invalid_json(self):
        fname = "invalid_cache.json"
        with open(os.path.join(self.cache_dir, fname), "w") as f:
            f.write("not a json")
        # Should raise json.JSONDecodeError
        with self.assertRaises(json.JSONDecodeError):
            main.load_cache(fname)

    @patch("main.requests.get")
    def test_get_races_api_error(self, mock_get):
        mock_get.return_value.status_code = 500
        mock_get.return_value.raise_for_status.side_effect = Exception("API error")
        with self.assertRaises(Exception):
            main.get_races(2025, force_update=True)

    @patch("main.requests.get")
    def test_get_race_results_api_error(self, mock_get):
        mock_get.return_value.status_code = 500
        mock_get.return_value.raise_for_status.side_effect = Exception("API error")
        with self.assertRaises(Exception):
            main.get_race_results(1)

    @patch("main.requests.get")
    def test_get_driver_map_rate_limit(self, mock_get):
        # Simulate rate limit then success
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
        self.assertEqual(driver_map[("99", "1")], "Test Driver")

    @patch("main.pd.DataFrame")
    def test_plot_standings(self, mock_df):
        # Test that plot_standings calls DataFrame and write_html
        mock_df.return_value.ffill.return_value.fillna.return_value = mock_df.return_value
        mock_df.return_value.melt.return_value = mock_df.return_value
        mock_fig = MagicMock()
        with patch("main.px.line", return_value=mock_fig):
            main.plot_standings([{"A": 1}], ["Race1"], ["A"])
            mock_fig.write_html.assert_called_once()

    @patch("main.argparse.ArgumentParser.parse_args", return_value=type('Args', (), {'year': 2025, 'force_update': False})())
    def test_main_flow(self, mock_args):
        # Patch all network and plotting calls
        with patch("main.get_races", return_value=[{"session_key": 1, "meeting_name": "Test GP"}]), \
             patch("main.get_race_results", return_value=[{"driver_number": 44, "position": 1}]), \
             patch("main.get_driver_map", return_value={("44", "1"): "Lewis Hamilton"}), \
             patch("main.plot_standings") as mock_plot:
            main.main()
            mock_plot.assert_called_once()


if __name__ == "__main__":
    unittest.main()
