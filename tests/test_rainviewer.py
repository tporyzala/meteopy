import unittest
from unittest.mock import Mock, patch
from pathlib import Path
import sys
import types

import folium
import requests


ROOT = Path(__file__).resolve().parents[1]

if "meteopy" not in sys.modules:
    package = types.ModuleType("meteopy")
    package.__path__ = [str(ROOT / "meteopy")]
    sys.modules["meteopy"] = package

from meteopy.RainViewer.RainViewer import (
    RAINVIEWER_API_URL,
    RainViewerError,
    RainViewerFrame,
    RainViewerRadarAnimation,
    build_rainviewer_tile_url,
    fetch_rainviewer_radar_frames,
    parse_rainviewer_radar_frames,
)


class RainViewerMetadataTests(unittest.TestCase):
    def test_parse_radar_frames_builds_labels_and_tile_urls(self):
        frames = parse_rainviewer_radar_frames(
            {
                "host": "https://tilecache.rainviewer.com",
                "radar": {
                    "past": [
                        {"time": 1609401600, "path": "/v2/radar/1609401600"},
                        {"time": "1609402200", "path": "v2/radar/1609402200"},
                    ],
                },
            }
        )

        self.assertEqual(2, len(frames))
        self.assertEqual(1609401600, frames[0].time)
        self.assertTrue(frames[0].label.endswith("UTC"))
        self.assertEqual(
            "https://tilecache.rainviewer.com/v2/radar/1609401600/256/{z}/{x}/{y}/2/1_1.png",
            frames[0].tile_url,
        )
        self.assertEqual(
            "https://tilecache.rainviewer.com/v2/radar/1609402200/256/{z}/{x}/{y}/2/1_1.png",
            frames[1].tile_url,
        )

    def test_build_tile_url_preserves_host_path_and_placeholders(self):
        tile_url = build_rainviewer_tile_url(
            "https://tilecache.rainviewer.com/",
            "/v2/radar/example",
        )

        self.assertIn("https://tilecache.rainviewer.com/v2/radar/example", tile_url)
        self.assertIn("{z}", tile_url)
        self.assertIn("{x}", tile_url)
        self.assertIn("{y}", tile_url)

    def test_parse_empty_frames_raises_clear_error(self):
        with self.assertRaisesRegex(RainViewerError, "no radar frames"):
            parse_rainviewer_radar_frames(
                {
                    "host": "https://tilecache.rainviewer.com",
                    "radar": {"past": []},
                }
            )

    def test_parse_malformed_metadata_raises_clear_error(self):
        with self.assertRaisesRegex(RainViewerError, "metadata is incomplete"):
            parse_rainviewer_radar_frames({"host": "https://tilecache.rainviewer.com"})

    @patch("meteopy.RainViewer.RainViewer.requests.get")
    def test_fetch_metadata_uses_timeout_and_parses_response(self, mock_get):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "host": "https://tilecache.rainviewer.com",
            "radar": {
                "past": [
                    {"time": 1609401600, "path": "/v2/radar/1609401600"},
                ],
            },
        }
        mock_get.return_value = response

        frames = fetch_rainviewer_radar_frames(timeout=9)

        mock_get.assert_called_once_with(RAINVIEWER_API_URL, timeout=9)
        self.assertEqual(1, len(frames))

    @patch("meteopy.RainViewer.RainViewer.requests.get")
    def test_fetch_metadata_wraps_request_errors(self, mock_get):
        mock_get.side_effect = requests.Timeout("timed out")

        with self.assertRaisesRegex(RainViewerError, "timed out"):
            fetch_rainviewer_radar_frames()

    @patch("meteopy.RainViewer.RainViewer.requests.get")
    def test_fetch_metadata_wraps_invalid_json(self, mock_get):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.side_effect = ValueError("invalid json")
        mock_get.return_value = response

        with self.assertRaisesRegex(RainViewerError, "invalid JSON"):
            fetch_rainviewer_radar_frames()


class RainViewerAnimationRenderTests(unittest.TestCase):
    def test_animation_element_renders_frame_urls_and_labels(self):
        weather_map = folium.Map(location=[33.76634, -118.16699], zoom_start=7)
        frames = [
            RainViewerFrame(
                time=1609401600,
                label="10:40 UTC",
                tile_url="https://tilecache.rainviewer.com/v2/radar/a/256/{z}/{x}/{y}/2/1_1.png",
            ),
            RainViewerFrame(
                time=1609402200,
                label="10:50 UTC",
                tile_url="https://tilecache.rainviewer.com/v2/radar/b/256/{z}/{x}/{y}/2/1_1.png",
            ),
        ]

        RainViewerRadarAnimation(frames, frame_delay=600).add_to(weather_map)
        rendered = weather_map.get_root().render()

        self.assertIn("rainviewer-control-", rendered)
        self.assertIn("https://tilecache.rainviewer.com/v2/radar/a/256/{z}/{x}/{y}/2/1_1.png", rendered)
        self.assertIn("https://tilecache.rainviewer.com/v2/radar/b/256/{z}/{x}/{y}/2/1_1.png", rendered)
        self.assertIn("10:40 UTC", rendered)
        self.assertIn("10:50 UTC", rendered)
        self.assertIn("frameDelay = 600", rendered)
        self.assertIn("tileSize: 256", rendered)
        self.assertIn('pane: "overlayPane"', rendered)
        self.assertIn("toggleRadar", rendered)
        self.assertIn("Hide radar overlay", rendered)
        self.assertIn("toLocaleTimeString", rendered)
        self.assertIn('timeZoneName: "short"', rendered)
        self.assertIn("Radar frame time in your local time zone", rendered)


if __name__ == "__main__":
    unittest.main()
