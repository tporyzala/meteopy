from dataclasses import dataclass
from datetime import datetime, timezone
import json

from branca.element import MacroElement, Template
import requests


RAINVIEWER_API_URL = "https://api.rainviewer.com/public/weather-maps.json"
RAINVIEWER_ATTRIBUTION = (
    'Radar imagery &copy; '
    '<a href="https://www.rainviewer.com/" target="_blank">Rain Viewer</a>'
)


class RainViewerError(RuntimeError):
    pass


@dataclass(frozen=True)
class RainViewerFrame:
    time: int
    label: str
    tile_url: str


def build_rainviewer_tile_url(
    host,
    path,
    tile_size=256,
    color_scheme=2,
    smooth=True,
    snow=True,
):
    if not host or not path:
        raise RainViewerError("RainViewer frame is missing host or path")

    clean_host = str(host).rstrip("/")
    clean_path = str(path)
    if not clean_path.startswith("/"):
        clean_path = "/" + clean_path

    smooth_option = 1 if smooth else 0
    snow_option = 1 if snow else 0

    return (
        f"{clean_host}{clean_path}/{tile_size}/"
        f"{{z}}/{{x}}/{{y}}/{color_scheme}/{smooth_option}_{snow_option}.png"
    )


def parse_rainviewer_radar_frames(metadata):
    if not isinstance(metadata, dict):
        raise RainViewerError("RainViewer returned invalid metadata")

    host = metadata.get("host")
    radar = metadata.get("radar")
    past_frames = radar.get("past") if isinstance(radar, dict) else None

    if not host or not isinstance(past_frames, list):
        raise RainViewerError("RainViewer radar metadata is incomplete")

    frames = []
    for frame in past_frames:
        if not isinstance(frame, dict):
            continue

        frame_time = frame.get("time")
        path = frame.get("path")
        if frame_time is None or not path:
            continue

        try:
            timestamp = int(frame_time)
        except (TypeError, ValueError):
            continue

        frames.append(
            RainViewerFrame(
                time=timestamp,
                label=format_rainviewer_time(timestamp),
                tile_url=build_rainviewer_tile_url(host, path),
            )
        )

    if not frames:
        raise RainViewerError("RainViewer returned no radar frames")

    return frames


def fetch_rainviewer_radar_frames(timeout=20):
    try:
        response = requests.get(RAINVIEWER_API_URL, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RainViewerError(f"RainViewer metadata request failed: {exc}") from exc

    try:
        metadata = response.json()
    except ValueError as exc:
        raise RainViewerError("RainViewer returned invalid JSON") from exc

    return parse_rainviewer_radar_frames(metadata)


def format_rainviewer_time(timestamp):
    return datetime.fromtimestamp(int(timestamp), tz=timezone.utc).strftime("%H:%M UTC")


class RainViewerRadarAnimation(MacroElement):
    _template = Template(
        """
        {% macro html(this, kwargs) %}
        <style>
            .rainviewer-control-{{ this.get_name() }} {
                background: rgba(255, 255, 255, 0.92);
                border: 1px solid rgba(0, 0, 0, 0.2);
                border-radius: 4px;
                box-shadow: 0 1px 5px rgba(0, 0, 0, 0.25);
                color: #1f2933;
                display: flex;
                align-items: center;
                gap: 6px;
                font: 12px/1.2 Arial, sans-serif;
                padding: 6px;
            }
            .rainviewer-control-{{ this.get_name() }} button {
                background: #ffffff;
                border: 1px solid rgba(0, 0, 0, 0.28);
                border-radius: 3px;
                color: #1f2933;
                cursor: pointer;
                font: 12px/1.2 Arial, sans-serif;
                min-width: 42px;
                padding: 3px 6px;
            }
            .rainviewer-control-{{ this.get_name() }} input {
                width: 96px;
            }
            .rainviewer-control-{{ this.get_name() }} span {
                min-width: 84px;
                text-align: right;
            }
        </style>
        {% endmacro %}
        {% macro script(this, kwargs) %}
        (function() {
            var map = {{ this._parent.get_name() }};
            var frames = {{ this.frames_json|safe }};
            if (!frames.length) {
                return;
            }

            var layers = frames.map(function(frame) {
                return L.tileLayer(frame.tile_url, {
                    attribution: {{ this.attribution_json|safe }},
                    maxNativeZoom: {{ this.max_native_zoom }},
                    maxZoom: {{ this.max_zoom }},
                    opacity: 0,
                    pane: "overlayPane",
                    tileSize: {{ this.tile_size }},
                    updateWhenIdle: true,
                    zIndex: {{ this.z_index }}
                });
            });

            var currentIndex = frames.length - 1;
            var frameDelay = {{ this.frame_delay }};
            var visibleOpacity = {{ this.opacity }};
            var radarVisible = true;
            var timer = null;
            var labelNode = null;
            var sliderNode = null;
            var buttonNode = null;
            var radarToggleNode = null;

            function isAdjacent(index) {
                return Math.abs(index - currentIndex) <= 1;
            }

            function ensureLayer(index) {
                if (index < 0 || index >= layers.length) {
                    return;
                }
                if (!map.hasLayer(layers[index])) {
                    layers[index].addTo(map);
                }
            }

            function syncLayers() {
                if (!radarVisible) {
                    for (var hiddenIndex = 0; hiddenIndex < layers.length; hiddenIndex += 1) {
                        if (map.hasLayer(layers[hiddenIndex])) {
                            map.removeLayer(layers[hiddenIndex]);
                        }
                    }
                    return;
                }

                for (var index = 0; index < layers.length; index += 1) {
                    if (index === currentIndex || isAdjacent(index)) {
                        ensureLayer(index);
                    } else if (map.hasLayer(layers[index])) {
                        map.removeLayer(layers[index]);
                    }

                    if (map.hasLayer(layers[index])) {
                        layers[index].setOpacity(index === currentIndex ? visibleOpacity : 0);
                    }
                }
            }

            function formatFrameTime(frame) {
                if (!frame || frame.time === null || frame.time === undefined) {
                    return frame && frame.label ? frame.label : "";
                }

                try {
                    return new Date(frame.time * 1000).toLocaleTimeString(
                        [],
                        {
                            hour: "numeric",
                            minute: "2-digit",
                            timeZoneName: "short"
                        }
                    );
                } catch (error) {
                    return frame.label || "";
                }
            }

            function updateControl() {
                if (labelNode) {
                    labelNode.textContent = formatFrameTime(frames[currentIndex]);
                }
                if (sliderNode) {
                    sliderNode.value = currentIndex;
                }
                if (buttonNode) {
                    buttonNode.textContent = timer ? "Pause" : "Play";
                }
                if (radarToggleNode) {
                    radarToggleNode.textContent = radarVisible ? "Hide" : "Radar";
                    radarToggleNode.title = radarVisible ? "Hide radar overlay" : "Show radar overlay";
                }
            }

            function showFrame(index) {
                currentIndex = (index + frames.length) % frames.length;
                syncLayers();
                updateControl();
            }

            function stepForward() {
                showFrame(currentIndex + 1);
            }

            function stopAnimation() {
                if (timer) {
                    window.clearInterval(timer);
                    timer = null;
                    updateControl();
                }
            }

            function toggleAnimation() {
                if (!radarVisible) {
                    radarVisible = true;
                    showFrame(currentIndex);
                }
                if (timer) {
                    stopAnimation();
                    return;
                }
                timer = window.setInterval(stepForward, frameDelay);
                updateControl();
            }

            function toggleRadar() {
                radarVisible = !radarVisible;
                if (!radarVisible) {
                    stopAnimation();
                }
                syncLayers();
                updateControl();
            }

            var control = L.control({position: "bottomleft"});
            control.onAdd = function() {
                var container = L.DomUtil.create(
                    "div",
                    "rainviewer-control-{{ this.get_name() }}"
                );

                radarToggleNode = L.DomUtil.create("button", "", container);
                radarToggleNode.type = "button";
                radarToggleNode.textContent = "Hide";
                radarToggleNode.title = "Hide radar overlay";

                buttonNode = L.DomUtil.create("button", "", container);
                buttonNode.type = "button";
                buttonNode.textContent = "Play";
                buttonNode.title = "Play radar animation";

                sliderNode = L.DomUtil.create("input", "", container);
                sliderNode.type = "range";
                sliderNode.min = 0;
                sliderNode.max = frames.length - 1;
                sliderNode.step = 1;
                sliderNode.value = currentIndex;
                sliderNode.title = "Radar frame time";

                labelNode = L.DomUtil.create("span", "", container);
                labelNode.textContent = formatFrameTime(frames[currentIndex]);
                labelNode.title = "Radar frame time in your local time zone";

                L.DomEvent.disableClickPropagation(container);
                L.DomEvent.disableScrollPropagation(container);
                L.DomEvent.on(radarToggleNode, "click", function(event) {
                    L.DomEvent.stop(event);
                    toggleRadar();
                });
                L.DomEvent.on(buttonNode, "click", function(event) {
                    L.DomEvent.stop(event);
                    toggleAnimation();
                });
                L.DomEvent.on(sliderNode, "input", function(event) {
                    stopAnimation();
                    showFrame(parseInt(event.target.value, 10));
                });

                return container;
            };
            control.addTo(map);

            showFrame(currentIndex);
        })();
        {% endmacro %}
        """
    )

    def __init__(
        self,
        frames,
        frame_delay=700,
        opacity=0.65,
        tile_size=256,
        max_native_zoom=7,
        max_zoom=18,
        z_index=450,
        attribution=RAINVIEWER_ATTRIBUTION,
    ):
        super().__init__()
        self._name = "RainViewerRadarAnimation"
        self.frames = list(frames)
        self.frame_delay = int(frame_delay)
        self.opacity = float(opacity)
        self.tile_size = int(tile_size)
        self.max_native_zoom = int(max_native_zoom)
        self.max_zoom = int(max_zoom)
        self.z_index = int(z_index)
        self.frames_json = json.dumps(
            [
                {
                    "time": frame.time,
                    "label": frame.label,
                    "tile_url": frame.tile_url,
                }
                for frame in self.frames
            ]
        )
        self.attribution_json = json.dumps(attribution)
