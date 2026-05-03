from datetime import datetime
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]

if "meteopy" not in sys.modules:
    package = types.ModuleType("meteopy")
    package.__path__ = [str(ROOT / "meteopy")]
    sys.modules["meteopy"] = package

from meteopy.RouteWeather.RouteWeather import (
    OPENROUTESERVICE_DIRECTIONS_API_URL,
    ROUTE_FORECAST_API_URL,
    RouteWeatherError,
    attach_route_sample_etas,
    build_hourly_timeline,
    build_route_hourly_report,
    calculate_route_waypoint_etas,
    calculate_route_waypoint_times,
    classify_route_hazards,
    cumulative_route_distances,
    fetch_openrouteservice_route,
    fetch_route_forecasts,
    haversine_distance_km,
    linear_interpolate_by_time,
    parse_openrouteservice_route,
    parse_route_forecast_response,
    route_forecast_days_needed,
    sample_route,
)


class RouteGeometryTests(unittest.TestCase):
    def test_haversine_distance_is_reasonable(self):
        distance = haversine_distance_km(
            {"lat": 0, "lng": 0},
            {"lat": 0, "lng": 1},
        )

        self.assertAlmostEqual(111.2, distance, places=1)

    def test_cumulative_route_distances_handles_empty_and_one_point(self):
        self.assertEqual([], cumulative_route_distances([]))
        self.assertEqual([0.0], cumulative_route_distances([{"lat": 0, "lng": 0}]))

    def test_sample_route_handles_empty_one_point_and_caps_samples(self):
        self.assertEqual([], sample_route([]))

        one_point = sample_route([{"lat": 1, "lng": 2}])
        self.assertEqual(1, len(one_point))
        self.assertEqual(0.0, one_point[0]["distance_km"])

        samples = sample_route(
            [{"lat": 0, "lng": 0}, {"lat": 0, "lng": 1}],
            spacing_km=1,
            max_samples=5,
        )

        self.assertEqual(5, len(samples))
        self.assertAlmostEqual(0.0, samples[0]["distance_km"])
        self.assertAlmostEqual(111.2, samples[-1]["distance_km"], places=1)

    def test_sample_route_includes_multiple_segments(self):
        samples = sample_route(
            [
                {"lat": 0, "lng": 0},
                {"lat": 0, "lng": 0.5},
                {"lat": 0, "lng": 1.0},
            ],
            spacing_km=50,
            max_samples=10,
        )

        self.assertGreaterEqual(len(samples), 3)
        self.assertAlmostEqual(0.0, samples[0]["lng"])
        self.assertAlmostEqual(1.0, samples[-1]["lng"])

    def test_sample_route_always_includes_forced_waypoint_samples(self):
        route_geometry = [
            {"lat": 0, "lng": 0},
            {"lat": 0, "lng": 1},
        ]
        waypoint = {"lat": 0.25, "lng": 0.5}

        samples = sample_route(
            route_geometry,
            spacing_km=1,
            max_samples=2,
            forced_points=[
                {"lat": 0, "lng": 0},
                waypoint,
                {"lat": 0, "lng": 1},
            ],
            forced_distances=[0.0, 55.6, 111.2],
        )

        forced_samples = [
            sample for sample in samples
            if sample.get("sample_type") == "waypoint"
        ]

        self.assertEqual(3, len(forced_samples))
        self.assertGreater(len(samples), 2)
        self.assertEqual(1, forced_samples[1]["waypoint_index"])
        self.assertAlmostEqual(0.25, forced_samples[1]["lat"])
        self.assertAlmostEqual(0.5, forced_samples[1]["lng"])

    def test_parse_openrouteservice_route_extracts_geometry_and_waypoint_distances(self):
        payload = {
            "features": [
                {
                    "geometry": {
                        "coordinates": [
                            [0.0, 0.0],
                            [0.5, 0.0],
                            [1.0, 0.0],
                        ],
                    },
                    "properties": {
                        "summary": {
                            "distance": 111200,
                            "duration": 3600,
                        },
                        "way_points": [0, 1, 2],
                    },
                }
            ]
        }

        route = parse_openrouteservice_route(payload, waypoint_count=3)

        self.assertEqual(3, len(route["geometry"]))
        self.assertEqual({"lat": 0.0, "lng": 0.0}, route["geometry"][0])
        self.assertEqual([0, 1, 2], route["waypoint_indices"])
        self.assertEqual(111.2, route["distance_km"])
        self.assertEqual(3600, route["duration_seconds"])
        self.assertAlmostEqual(55.6, route["waypoint_distances_km"][1], places=1)

    def test_parse_openrouteservice_route_falls_back_to_nearest_waypoint_indices(self):
        payload = {
            "features": [
                {
                    "geometry": {
                        "coordinates": [
                            [0.0, 0.0],
                            [0.5, 0.0],
                            [1.0, 0.0],
                        ],
                    },
                    "properties": {},
                }
            ]
        }

        route = parse_openrouteservice_route(
            payload,
            waypoint_count=2,
            waypoints=[
                {"lat": 0.0, "lng": 0.1},
                {"lat": 0.0, "lng": 0.9},
            ],
        )

        self.assertEqual([0, 2], route["waypoint_indices"])


class RouteTimingTests(unittest.TestCase):
    def test_eta_generation_uses_default_speed_without_anchors(self):
        waypoints = [{"lat": 0, "lng": 0}, {"lat": 0, "lng": 1}]
        start = datetime(2026, 5, 2, 8, 0)

        etas = calculate_route_waypoint_etas(waypoints, start, speed_kmh=111.2)

        self.assertEqual(pd.Timestamp(start), etas[0])
        self.assertAlmostEqual(
            1.0,
            (etas[1] - etas[0]).total_seconds() / 3600,
            places=2,
        )

    def test_eta_generation_interpolates_between_arrival_anchors(self):
        waypoints = [
            {"lat": 0, "lng": 0},
            {"lat": 0, "lng": 0.5},
            {"lat": 0, "lng": 1.0},
        ]
        start = datetime(2026, 5, 2, 8, 0)

        etas = calculate_route_waypoint_etas(
            waypoints,
            start,
            speed_kmh=50,
            anchor_times={2: datetime(2026, 5, 2, 10, 0)},
        )

        self.assertEqual(pd.Timestamp(datetime(2026, 5, 2, 9, 0)), etas[1])
        self.assertEqual(pd.Timestamp(datetime(2026, 5, 2, 10, 0)), etas[2])

    def test_explicit_waypoint_times_use_start_and_end_anchors(self):
        waypoints = [
            {"lat": 0, "lng": 0},
            {"lat": 0, "lng": 0.5},
            {"lat": 0, "lng": 1.0},
        ]

        etas = calculate_route_waypoint_times(
            waypoints,
            datetime(2026, 5, 2, 8, 0),
            datetime(2026, 5, 2, 10, 0),
        )

        self.assertEqual(pd.Timestamp(datetime(2026, 5, 2, 8, 0)), etas[0])
        self.assertEqual(pd.Timestamp(datetime(2026, 5, 2, 9, 0)), etas[1])
        self.assertEqual(pd.Timestamp(datetime(2026, 5, 2, 10, 0)), etas[2])

    def test_explicit_waypoint_times_use_optional_interior_anchors(self):
        waypoints = [
            {"lat": 0, "lng": 0},
            {"lat": 0, "lng": 0.5},
            {"lat": 0, "lng": 1.0},
        ]

        etas = calculate_route_waypoint_times(
            waypoints,
            datetime(2026, 5, 2, 8, 0),
            datetime(2026, 5, 2, 12, 0),
            anchor_times={1: datetime(2026, 5, 2, 11, 0)},
        )

        self.assertEqual(pd.Timestamp(datetime(2026, 5, 2, 8, 0)), etas[0])
        self.assertEqual(pd.Timestamp(datetime(2026, 5, 2, 11, 0)), etas[1])
        self.assertEqual(pd.Timestamp(datetime(2026, 5, 2, 12, 0)), etas[2])

    def test_explicit_waypoint_times_can_use_snapped_route_distances(self):
        waypoints = [
            {"lat": 0, "lng": 0},
            {"lat": 0, "lng": 0.5},
            {"lat": 0, "lng": 1.0},
        ]

        etas = calculate_route_waypoint_times(
            waypoints,
            datetime(2026, 5, 2, 8, 0),
            datetime(2026, 5, 2, 12, 0),
            waypoint_distances=[0.0, 30.0, 120.0],
        )

        self.assertEqual(pd.Timestamp(datetime(2026, 5, 2, 9, 0)), etas[1])

    def test_explicit_waypoint_times_reject_out_of_order_anchors(self):
        with self.assertRaisesRegex(ValueError, "must increase"):
            calculate_route_waypoint_times(
                [
                    {"lat": 0, "lng": 0},
                    {"lat": 0, "lng": 0.5},
                    {"lat": 0, "lng": 1.0},
                ],
                datetime(2026, 5, 2, 8, 0),
                datetime(2026, 5, 2, 10, 0),
                anchor_times={1: datetime(2026, 5, 2, 11, 0)},
            )

    def test_eta_generation_rejects_out_of_order_anchors(self):
        with self.assertRaisesRegex(ValueError, "must increase"):
            calculate_route_waypoint_etas(
                [{"lat": 0, "lng": 0}, {"lat": 0, "lng": 1}],
                datetime(2026, 5, 2, 8, 0),
                speed_kmh=50,
                anchor_times={1: datetime(2026, 5, 2, 7, 0)},
            )

    def test_attach_route_sample_etas_interpolates_by_distance(self):
        waypoints = [
            {"lat": 0, "lng": 0},
            {"lat": 0, "lng": 1},
        ]
        samples = sample_route(waypoints, spacing_km=55.6, max_samples=5)
        etas = [
            pd.Timestamp(datetime(2026, 5, 2, 8, 0)),
            pd.Timestamp(datetime(2026, 5, 2, 10, 0)),
        ]

        attached = attach_route_sample_etas(samples, waypoints, etas)

        self.assertEqual(etas[0], attached[0]["eta"])
        self.assertEqual(etas[-1], attached[-1]["eta"])
        self.assertGreater(attached[1]["eta"], attached[0]["eta"])

    def test_attach_route_sample_etas_can_use_snapped_route_distances(self):
        samples = [
            {"lat": 0.0, "lng": 0.0, "distance_km": 0.0},
            {"lat": 0.0, "lng": 0.5, "distance_km": 30.0},
            {"lat": 0.0, "lng": 1.0, "distance_km": 120.0},
        ]
        etas = [
            pd.Timestamp(datetime(2026, 5, 2, 8, 0)),
            pd.Timestamp(datetime(2026, 5, 2, 12, 0)),
        ]

        attached = attach_route_sample_etas(
            samples,
            [{"lat": 0, "lng": 0}, {"lat": 0, "lng": 1}],
            etas,
            waypoint_distances=[0.0, 120.0],
        )

        self.assertEqual(pd.Timestamp(datetime(2026, 5, 2, 9, 0)), attached[1]["eta"])

    def test_hourly_timeline_includes_start_hourly_ticks_and_end(self):
        timeline = build_hourly_timeline(
            datetime(2026, 5, 2, 8, 30),
            datetime(2026, 5, 2, 10, 10),
        )

        self.assertEqual(
            [
                pd.Timestamp("2026-05-02 08:30"),
                pd.Timestamp("2026-05-02 09:00"),
                pd.Timestamp("2026-05-02 10:00"),
                pd.Timestamp("2026-05-02 10:10"),
            ],
            timeline,
        )

    def test_route_forecast_days_needed_rejects_past_max_window(self):
        with self.assertRaisesRegex(RouteWeatherError, "16-day"):
            route_forecast_days_needed(
                datetime(2026, 5, 20, 12, 0),
                now=datetime(2026, 5, 2, 12, 0),
            )

    def test_route_forecast_days_needed_adds_timezone_boundary_buffer(self):
        self.assertEqual(
            2,
            route_forecast_days_needed(
                datetime(2026, 5, 2, 23, 0),
                now=datetime(2026, 5, 2, 12, 0),
            ),
        )
        self.assertEqual(
            16,
            route_forecast_days_needed(
                datetime(2026, 5, 17, 12, 0),
                now=datetime(2026, 5, 2, 12, 0),
            ),
        )


class RouteForecastParsingTests(unittest.TestCase):
    def test_linear_interpolation_by_time(self):
        rows = [
            {"time": datetime(2026, 5, 2, 8, 0), "temperature_2m": 10},
            {"time": datetime(2026, 5, 2, 10, 0), "temperature_2m": 20},
        ]

        result = linear_interpolate_by_time(
            rows,
            [datetime(2026, 5, 2, 9, 0)],
            numeric_columns=["temperature_2m"],
        )

        self.assertEqual(15, result.loc[0, "temperature_2m"])

    def test_linear_interpolation_handles_fractional_timestamp_resolution(self):
        rows = [
            {
                "time": pd.Timestamp("2026-05-02 08:00:00"),
                "distance_km": 0.0,
            },
            {
                "time": pd.Timestamp("2026-05-02 08:43:31.623746"),
                "distance_km": 14.509,
            },
        ]

        result = linear_interpolate_by_time(
            rows,
            [rows[0]["time"], rows[1]["time"]],
            numeric_columns=["distance_km"],
        )

        self.assertEqual(0.0, result.loc[0, "distance_km"])
        self.assertAlmostEqual(14.509, result.loc[1, "distance_km"], places=3)

    def test_parse_multi_coordinate_response_normalizes_weather_code(self):
        payload = [
            {
                "latitude": 33.1,
                "longitude": -118.1,
                "elevation": 2100.0,
                "hourly_units": {"temperature_2m": "C", "weather_code": "wmo code"},
                "hourly": {
                    "time": ["2026-05-02T08:00"],
                    "temperature_2m": [18.0],
                    "weather_code": [3],
                },
            },
            {
                "latitude": 33.2,
                "longitude": -118.2,
                "hourly": {
                    "time": ["2026-05-02T08:00"],
                    "temperature_2m": [19.0],
                    "weather_code": [51],
                },
            },
        ]

        parsed = parse_route_forecast_response(payload, expected_count=2)

        self.assertEqual(2, len(parsed))
        self.assertIn("weathercode", parsed[0]["hourly"].columns)
        self.assertEqual("wmo code", parsed[0]["hourly_units"]["weathercode"])
        self.assertEqual(2100.0, parsed[0]["elevation"])

    def test_parse_open_meteo_error_raises_clear_error(self):
        with self.assertRaisesRegex(RouteWeatherError, "bad variable"):
            parse_route_forecast_response({"error": True, "reason": "bad variable"})

    @patch("meteopy.RouteWeather.RouteWeather.requests.get")
    def test_fetch_route_forecasts_uses_multi_coordinate_params_and_timeout(self, mock_get):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = [
            {
                "hourly": {
                    "time": ["2026-05-02T08:00"],
                    "temperature_2m": [18.0],
                },
            },
            {
                "hourly": {
                    "time": ["2026-05-02T08:00"],
                    "temperature_2m": [19.0],
                },
            },
        ]
        mock_get.return_value = response

        forecasts = fetch_route_forecasts(
            [
                {"lat": 33.123456, "lng": -118.123456},
                {"lat": 33.2, "lng": -118.2},
            ],
            forecast_days=3,
            timeout=9,
        )

        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        self.assertEqual((ROUTE_FORECAST_API_URL,), args)
        self.assertEqual("33.12346,33.2", kwargs["params"]["latitude"])
        self.assertEqual("-118.12346,-118.2", kwargs["params"]["longitude"])
        self.assertIn("temperature_2m", kwargs["params"]["hourly"])
        self.assertIn("weather_code", kwargs["params"]["hourly"])
        self.assertEqual(3, kwargs["params"]["forecast_days"])
        self.assertEqual(9, kwargs["timeout"])
        self.assertEqual(2, len(forecasts))

    @patch("meteopy.RouteWeather.RouteWeather.requests.post")
    def test_fetch_openrouteservice_route_uses_profile_key_and_coordinates(self, mock_post):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "features": [
                {
                    "geometry": {
                        "coordinates": [
                            [-118.0, 33.0],
                            [-118.1, 33.1],
                        ],
                    },
                    "properties": {
                        "summary": {"distance": 15000},
                        "way_points": [0, 1],
                    },
                }
            ]
        }
        mock_post.return_value = response

        route = fetch_openrouteservice_route(
            [
                {"lat": 33.0, "lng": -118.0},
                {"lat": 33.1, "lng": -118.1},
            ],
            "foot-hiking",
            "test-key",
            timeout=8,
        )

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(
            (OPENROUTESERVICE_DIRECTIONS_API_URL.format(profile="foot-hiking"),),
            args,
        )
        self.assertEqual(
            [[-118.0, 33.0], [-118.1, 33.1]],
            kwargs["json"]["coordinates"],
        )
        self.assertFalse(kwargs["json"]["instructions"])
        self.assertEqual("test-key", kwargs["headers"]["Authorization"])
        self.assertEqual(8, kwargs["timeout"])
        self.assertEqual(15.0, route["distance_km"])

    @patch("meteopy.RouteWeather.RouteWeather.requests.post")
    def test_fetch_openrouteservice_route_wraps_request_errors(self, mock_post):
        mock_post.side_effect = requests.Timeout("timed out")

        with self.assertRaisesRegex(RouteWeatherError, "timed out"):
            fetch_openrouteservice_route(
                [{"lat": 33.0, "lng": -118.0}, {"lat": 33.1, "lng": -118.1}],
                "driving-car",
                "test-key",
            )

    @patch("meteopy.RouteWeather.RouteWeather.requests.get")
    def test_fetch_route_forecasts_wraps_request_errors(self, mock_get):
        mock_get.side_effect = requests.Timeout("timed out")

        with self.assertRaisesRegex(RouteWeatherError, "timed out"):
            fetch_route_forecasts([{"lat": 33.0, "lng": -118.0}])

    def test_build_route_hourly_report_interpolates_sample_weather_by_time(self):
        samples = [
            {
                "lat": 33.0,
                "lng": -118.0,
                "distance_km": 0.0,
                "eta": pd.Timestamp("2026-05-02 08:00"),
            },
            {
                "lat": 34.0,
                "lng": -119.0,
                "distance_km": 20.0,
                "eta": pd.Timestamp("2026-05-02 10:00"),
            },
        ]
        forecasts = [
            self._forecast([10, 12, 14], [0, 0, 0]),
            self._forecast([20, 22, 24], [51, 51, 51]),
        ]

        report, units = build_route_hourly_report(samples, forecasts)

        self.assertEqual(
            [
                pd.Timestamp("2026-05-02 08:00"),
                pd.Timestamp("2026-05-02 09:00"),
                pd.Timestamp("2026-05-02 10:00"),
            ],
            report["time"].tolist(),
        )
        self.assertEqual(17.0, report.loc[1, "temperature_2m"])
        self.assertEqual(10.0, report.loc[1, "distance_km"])
        self.assertIn(report.loc[1, "weathercode"], [0, 51])
        self.assertEqual("C", units["temperature_2m"])

    def test_build_route_hourly_report_preserves_non_hourly_sample_rows(self):
        samples = [
            {
                "lat": 33.0,
                "lng": -118.0,
                "distance_km": 0.0,
                "eta": pd.Timestamp("2026-05-02 08:00"),
                "sample_type": "interval",
            },
            {
                "lat": 33.5,
                "lng": -118.5,
                "distance_km": 10.0,
                "eta": pd.Timestamp("2026-05-02 08:30"),
                "sample_type": "interval",
            },
            {
                "lat": 34.0,
                "lng": -119.0,
                "distance_km": 20.0,
                "eta": pd.Timestamp("2026-05-02 10:00"),
                "sample_type": "interval",
            },
        ]
        forecasts = [
            self._forecast([10, 10, 10], [0, 0, 0]),
            self._forecast([20, 20, 20], [51, 51, 51]),
            self._forecast([30, 30, 30], [61, 61, 61]),
        ]

        report, _ = build_route_hourly_report(samples, forecasts)

        self.assertIn(pd.Timestamp("2026-05-02 08:30"), report["time"].tolist())
        sample_row = report[report["time"] == pd.Timestamp("2026-05-02 08:30")].iloc[0]
        self.assertTrue(sample_row["is_route_sample"])
        self.assertEqual(20.0, sample_row["temperature_2m"])

    def test_build_route_hourly_report_includes_waypoint_eta_rows_and_elevation(self):
        samples = [
            {
                "lat": 33.0,
                "lng": -118.0,
                "distance_km": 0.0,
                "eta": pd.Timestamp("2026-05-02 08:00"),
                "sample_type": "waypoint",
                "waypoint_index": 0,
            },
            {
                "lat": 33.5,
                "lng": -118.5,
                "distance_km": 10.0,
                "eta": pd.Timestamp("2026-05-02 08:30"),
                "sample_type": "waypoint",
                "waypoint_index": 1,
            },
            {
                "lat": 34.0,
                "lng": -119.0,
                "distance_km": 20.0,
                "eta": pd.Timestamp("2026-05-02 10:00"),
                "sample_type": "waypoint",
                "waypoint_index": 2,
            },
        ]
        forecasts = [
            {**self._forecast([10, 10, 10], [0, 0, 0]), "elevation": 100.0},
            {**self._forecast([20, 20, 20], [51, 51, 51]), "elevation": 2000.0},
            {**self._forecast([30, 30, 30], [61, 61, 61]), "elevation": 300.0},
        ]

        report, _ = build_route_hourly_report(samples, forecasts)

        waypoint_row = report[report["time"] == pd.Timestamp("2026-05-02 08:30")].iloc[0]
        self.assertEqual("Waypoint 2", waypoint_row["waypoint"])
        self.assertEqual(20.0, waypoint_row["temperature_2m"])
        self.assertEqual(2000.0, waypoint_row["elevation"])

    def test_build_route_hourly_report_rejects_times_outside_forecast_window(self):
        samples = [
            {
                "lat": 33.0,
                "lng": -118.0,
                "distance_km": 0.0,
                "eta": pd.Timestamp("2026-05-02 07:00"),
            },
        ]

        with self.assertRaisesRegex(RouteWeatherError, "outside the fetched forecast window"):
            build_route_hourly_report(samples, [self._forecast([10, 12, 14], [0, 0, 0])])

    def test_classify_route_hazards(self):
        hazards = classify_route_hazards(
            {
                "precipitation_probability": 70,
                "wind_gusts_10m": 55,
                "uv_index": 7,
                "visibility": 4000,
                "temperature_2m": -1,
            }
        )

        self.assertIn("Rain likely", hazards)
        self.assertIn("Strong gusts", hazards)
        self.assertIn("High UV", hazards)
        self.assertIn("Low visibility", hazards)
        self.assertIn("Freezing", hazards)

    @staticmethod
    def _forecast(temperatures, weather_codes):
        return {
            "hourly_units": {"temperature_2m": "C"},
            "hourly": pd.DataFrame(
                {
                    "time": pd.to_datetime(
                        [
                            "2026-05-02 08:00",
                            "2026-05-02 09:00",
                            "2026-05-02 10:00",
                        ]
                    ),
                    "temperature_2m": temperatures,
                    "apparent_temperature": temperatures,
                    "dew_point_2m": temperatures,
                    "relative_humidity_2m": [50, 50, 50],
                    "precipitation_probability": [0, 0, 0],
                    "cloud_cover": [0, 0, 0],
                    "surface_pressure": [1010, 1010, 1010],
                    "weathercode": weather_codes,
                    "rain": [0, 0, 0],
                    "showers": [0, 0, 0],
                    "snowfall": [0, 0, 0],
                    "wind_speed_10m": [10, 10, 10],
                    "wind_gusts_10m": [15, 15, 15],
                    "uv_index": [3, 3, 3],
                    "visibility": [10000, 10000, 10000],
                }
            ),
        }


if __name__ == "__main__":
    unittest.main()
