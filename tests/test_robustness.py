import ast
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch

import requests


ROOT = Path(__file__).resolve().parents[1]

if "meteopy" not in sys.modules:
    package = types.ModuleType("meteopy")
    package.__path__ = [str(ROOT / "meteopy")]
    sys.modules["meteopy"] = package

from meteopy.Daily.DailyHistorical import DailyHistorical
from meteopy.MeteoManager.MeteoManager import MeteoManager


class Options:
    def __init__(self):
        self.latitude = 33.0
        self.longitude = -118.0
        self.current = ["temperature_2m"]


class Selector:
    def __init__(self, params):
        self.params = params


class MeteoManagerRobustnessTests(unittest.TestCase):
    def test_get_payload_does_not_mutate_options(self):
        options = Options()
        hourly = Selector(["temperature_2m", "rain"])
        daily = Selector(["sunrise"])
        manager = MeteoManager("https://example.test", options, hourly, daily)

        first_payload = manager.get_payload()
        second_payload = manager.get_payload()

        self.assertEqual(options.current, ["temperature_2m"])
        self.assertEqual(first_payload["current"], "temperature_2m")
        self.assertEqual(second_payload["current"], "temperature_2m")
        self.assertEqual(first_payload["hourly"], "temperature_2m,rain")
        self.assertEqual(first_payload["daily"], "sunrise")

    @patch("meteopy.MeteoManager.MeteoManager.requests.get")
    def test_fetch_uses_params_and_timeout(self, mock_get):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "hourly": {
                "time": ["2026-05-02T00:00"],
                "temperature_2m": [18.0],
            },
            "daily": {
                "time": ["2026-05-02"],
                "sunrise": ["2026-05-02T05:30"],
            },
        }
        mock_get.return_value = response

        options = Options()
        hourly = Selector(["temperature_2m"])
        daily = Selector(["sunrise"])
        manager = MeteoManager("https://example.test", options, hourly, daily, timeout=7)
        result = manager.fetch()

        mock_get.assert_called_once_with(
            "https://example.test",
            params={
                "latitude": 33.0,
                "longitude": -118.0,
                "current": "temperature_2m",
                "hourly": "temperature_2m",
                "daily": "sunrise",
            },
            timeout=7,
        )
        self.assertEqual(result["hourly"].loc[0, "temperature_2m"], 18.0)
        self.assertEqual(result["daily"].loc[0, "sunrise"], "2026-05-02T05:30")

    @patch("meteopy.MeteoManager.MeteoManager.requests.get")
    def test_fetch_raises_clear_error_for_open_meteo_error_payload(self, mock_get):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "error": True,
            "reason": "Cannot initialize WeatherVariable from invalid String value",
        }
        mock_get.return_value = response

        manager = MeteoManager("https://example.test", Options())

        with self.assertRaisesRegex(RuntimeError, "Cannot initialize WeatherVariable"):
            manager.fetch()

    @patch("meteopy.MeteoManager.MeteoManager.requests.get")
    def test_fetch_uses_error_reason_from_http_error_response(self, mock_get):
        response = Mock()
        response.json.return_value = {
            "error": True,
            "reason": "bad request reason",
        }
        error = requests.HTTPError("400 Client Error")
        error.response = response
        response.raise_for_status.side_effect = error
        mock_get.return_value = response

        manager = MeteoManager("https://example.test", Options())

        with self.assertRaisesRegex(RuntimeError, "bad request reason"):
            manager.fetch()

    @patch("meteopy.MeteoManager.MeteoManager.requests.get")
    def test_fetch_wraps_timeout(self, mock_get):
        mock_get.side_effect = requests.Timeout("request timed out")

        manager = MeteoManager("https://example.test", Options())

        with self.assertRaisesRegex(RuntimeError, "request timed out"):
            manager.fetch()

    @patch("meteopy.MeteoManager.MeteoManager.requests.get")
    def test_fetch_wraps_invalid_json(self, mock_get):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.side_effect = ValueError("invalid json")
        mock_get.return_value = response

        manager = MeteoManager("https://example.test", Options())

        with self.assertRaisesRegex(RuntimeError, "invalid JSON"):
            manager.fetch()


class HistoricalVariableTests(unittest.TestCase):
    def test_every_ui_historical_variable_is_supported_by_daily_historical(self):
        variables = self._historical_variable_options().values()
        daily = DailyHistorical()

        unsupported = [
            variable for variable in variables
            if not callable(getattr(daily, variable, None))
        ]

        self.assertEqual([], unsupported)

    def test_daily_historical_all_populates_unique_params(self):
        daily = DailyHistorical()

        returned = daily.all()

        self.assertIs(returned, daily)
        self.assertIn("et0_fao_evapotranspiration", daily.params)
        self.assertGreater(len(daily.params), 0)
        self.assertEqual(len(daily.params), len(set(daily.params)))

    @staticmethod
    def _historical_variable_options():
        tree = ast.parse((ROOT / "main.py").read_text())

        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue

            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "HISTORICAL_VARIABLE_OPTIONS":
                    return ast.literal_eval(node.value)

        raise AssertionError("HISTORICAL_VARIABLE_OPTIONS was not found in main.py")


if __name__ == "__main__":
    unittest.main()
