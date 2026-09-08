import ast
from pathlib import Path
import unittest

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


ROOT = Path(__file__).resolve().parents[1]


class PlotHelperTests(unittest.TestCase):
    def test_value_box_hover_uses_colored_number_labels_across_subplots(self):
        apply_value_box_hover = self._load_function(
            "apply_value_box_hover")
        figure = make_subplots(rows=2, cols=1, shared_xaxes=True)
        figure.add_trace(go.Scatter(
            x=["2026-09-07 13:00"], y=[79], name="Temperature"),
            row=1, col=1)
        figure.add_trace(go.Scatter(
            x=["2026-09-07 13:00"], y=[67], name="Dewpoint"),
            row=2, col=1)

        apply_value_box_hover(figure)

        self.assertEqual("x", figure.layout.hovermode)
        self.assertEqual("axis", figure.layout.hoversubplots)
        self.assertEqual(-1, figure.layout.spikedistance)
        self.assertEqual(
            "rgba(0,0,0,0)", figure.layout.hoverlabel.bgcolor)
        self.assertEqual(
            "rgba(0,0,0,0)", figure.layout.hoverlabel.bordercolor)
        self.assertEqual(
            "rgba(0,0,0,0)", figure.layout.hoverlabel.font.color)
        self.assertFalse(figure.layout.hoverlabel.showarrow)
        for axis in (figure.layout.xaxis, figure.layout.xaxis2):
            self.assertTrue(axis.showspikes)
            self.assertEqual("across", axis.spikemode)
        self.assertEqual(
            "%{y:.2~f}<extra></extra>", figure.data[0].hovertemplate)
        self.assertEqual("#b91c1c", figure.data[0].hoverlabel.bgcolor)
        self.assertEqual("#4d7c0f", figure.data[1].hoverlabel.bgcolor)

    def test_hover_time_label_shows_short_weekday_and_is_not_duplicated(self):
        add_hover_time_label = self._load_function(
            "add_hover_time_label", {"go": go})
        figure = make_subplots(rows=2, cols=1, shared_xaxes=True)

        add_hover_time_label(
            figure,
            ["2026-09-07 12:00", "2026-09-07 13:00"],
            [77, 82, 65, 67],
        )
        add_hover_time_label(
            figure,
            ["2026-09-07 12:00", "2026-09-07 13:00"],
            [77, 82, 65, 67],
        )

        self.assertEqual(1, len(figure.data))
        time_trace = figure.data[0]
        self.assertEqual("forecast-hover-time", time_trace.meta)
        self.assertIn("%a", time_trace.hovertemplate)
        self.assertIn("%-I%p", time_trace.hovertemplate)

    def test_daily_weather_card_is_a_continuous_html_fragment(self):
        daily_weather_card_html = self._load_function(
            "daily_weather_card_html")

        card = daily_weather_card_html(
            pd.Timestamp("2026-09-06"),
            "data:image/svg+xml;base64,example",
            "Sunny",
            '<div class="daily-weather-temperatures">25°C / 19°C</div>',
        )

        self.assertNotIn("\n", card)
        self.assertTrue(card.startswith('<div class="daily-weather-card">'))
        self.assertTrue(card.endswith("</div>"))

    def test_daily_weather_symbol_maps_wmo_conditions(self):
        daily_weather_symbol = self._load_function("daily_weather_symbol")

        expected = {
            0: ("sunny", "Sunny"),
            2: ("partly-cloudy", "Partly cloudy"),
            3: ("cloudy", "Cloudy"),
            45: ("fog", "Fog"),
            53: ("rain", "Drizzle"),
            63: ("rain", "Rain"),
            81: ("rain", "Showers"),
            73: ("snow", "Snow"),
            95: ("storm", "Thunderstorms"),
        }
        for code, symbol in expected.items():
            with self.subTest(code=code):
                self.assertEqual(symbol, daily_weather_symbol(code))

    def test_daily_weather_symbol_uses_wind_only_for_non_precipitation_days(self):
        daily_weather_symbol = self._load_function("daily_weather_symbol")

        self.assertEqual(
            ("windy", "Windy"),
            daily_weather_symbol(1, wind_speed=41, wind_gust=30),
        )
        self.assertEqual(
            ("rain", "Rain"),
            daily_weather_symbol(63, wind_speed=60, wind_gust=80),
        )

    def test_daily_forecast_range_uses_complete_calendar_days(self):
        daily_forecast_range = self._load_function("daily_forecast_range")
        daily = pd.DataFrame({
            "time": ["2026-09-06", "2026-09-07", "2026-09-08"],
        })

        self.assertEqual(
            [pd.Timestamp("2026-09-06"), pd.Timestamp("2026-09-09")],
            daily_forecast_range(daily),
        )

    def test_moving_average_preserves_series_length(self):
        moving_average = self._load_function("moving_average")

        for length in [1, 2, 3, 8]:
            values = list(range(length))
            smoothed = moving_average(values, 3)

            self.assertEqual(length, len(smoothed))
            self.assertFalse(np.isnan(smoothed).any())

    def test_route_precipitation_bins_groups_dense_samples_into_hours(self):
        route_precipitation_bins = self._load_function("route_precipitation_bins")
        route_hourly = pd.DataFrame(
            {
                "time": pd.to_datetime(
                    [
                        "2026-05-02 08:00",
                        "2026-05-02 08:15",
                        "2026-05-02 08:45",
                        "2026-05-02 09:10",
                    ]
                ),
                "rain": [1.0, 2.0, 3.0, 4.0],
            }
        )

        bins = route_precipitation_bins(route_hourly)

        self.assertEqual(
            [
                pd.Timestamp("2026-05-02 08:30"),
                pd.Timestamp("2026-05-02 09:30"),
            ],
            bins["time"].tolist(),
        )
        self.assertEqual([2.0, 4.0], bins["rain"].tolist())
        self.assertEqual([0.0, 0.0], bins["showers"].tolist())

    def test_clamp_date_respects_bounds(self):
        clamp_date = self._load_function("clamp_date")

        self.assertEqual(
            pd.Timestamp("2026-05-02").date(),
            clamp_date("2026-05-01", pd.Timestamp("2026-05-02").date(), pd.Timestamp("2026-05-10").date()),
        )
        self.assertEqual(
            pd.Timestamp("2026-05-10").date(),
            clamp_date("2026-05-15", pd.Timestamp("2026-05-02").date(), pd.Timestamp("2026-05-10").date()),
        )
        self.assertEqual(
            pd.Timestamp("2026-05-06").date(),
            clamp_date("2026-05-06", pd.Timestamp("2026-05-02").date(), pd.Timestamp("2026-05-10").date()),
        )

    @staticmethod
    def _load_function(name, extra_namespace=None):
        tree = ast.parse((ROOT / "main.py").read_text())
        function_node = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == name
        )
        module = ast.Module(body=[function_node], type_ignores=[])
        ast.fix_missing_locations(module)
        namespace = {"pd": pd, "np": np}
        if extra_namespace:
            namespace.update(extra_namespace)
        exec(compile(module, "main.py", "exec"), namespace)
        return namespace[name]


if __name__ == "__main__":
    unittest.main()
