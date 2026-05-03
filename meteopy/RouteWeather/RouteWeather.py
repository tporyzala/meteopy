from datetime import timedelta
from math import asin, ceil, cos, radians, sin, sqrt

import numpy as np
import pandas as pd
import requests


ROUTE_FORECAST_API_URL = "https://api.open-meteo.com/v1/forecast"
OPENROUTESERVICE_DIRECTIONS_API_URL = (
    "https://api.openrouteservice.org/v2/directions/{profile}/geojson"
)

OPENROUTESERVICE_PROFILES = {
    "driving-car",
    "foot-walking",
    "foot-hiking",
    "cycling-regular",
}

ROUTE_HOURLY_VARIABLES = [
    "temperature_2m",
    "apparent_temperature",
    "dew_point_2m",
    "relative_humidity_2m",
    "precipitation_probability",
    "cloud_cover",
    "surface_pressure",
    "weather_code",
    "precipitation",
    "rain",
    "showers",
    "snowfall",
    "wind_speed_10m",
    "wind_gusts_10m",
    "uv_index",
    "visibility",
]

ROUTE_PLOT_VARIABLES = [
    "temperature_2m",
    "apparent_temperature",
    "dew_point_2m",
    "relative_humidity_2m",
    "precipitation_probability",
    "cloud_cover",
    "surface_pressure",
    "weathercode",
    "precipitation",
    "rain",
    "showers",
    "snowfall",
    "wind_speed_10m",
    "wind_gusts_10m",
    "uv_index",
    "visibility",
]


class RouteWeatherError(RuntimeError):
    pass


def _lat_lng(waypoint):
    if isinstance(waypoint, dict):
        lat = waypoint.get("lat", waypoint.get("latitude"))
        lng = waypoint.get("lng", waypoint.get("lon", waypoint.get("longitude")))
    else:
        lat, lng = waypoint

    if lat is None or lng is None:
        raise ValueError("Route waypoint must include latitude and longitude")

    return float(lat), float(lng)


def _timestamp(value):
    ts = pd.Timestamp(value)
    if ts.tzinfo is not None:
        ts = ts.tz_convert(None)
    return ts


def _format_coordinate(value):
    return f"{float(value):.5f}".rstrip("0").rstrip(".")


def haversine_distance_km(start, end):
    start_lat, start_lng = _lat_lng(start)
    end_lat, end_lng = _lat_lng(end)
    earth_radius_km = 6371.0088

    lat1 = radians(start_lat)
    lat2 = radians(end_lat)
    dlat = radians(end_lat - start_lat)
    dlng = radians(end_lng - start_lng)

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlng / 2) ** 2
    return earth_radius_km * 2 * asin(sqrt(a))


def cumulative_route_distances(waypoints):
    if not waypoints:
        return []

    distances = [0.0]
    for index in range(1, len(waypoints)):
        distances.append(
            distances[-1]
            + haversine_distance_km(waypoints[index - 1], waypoints[index])
        )
    return distances


def _interpolate_point_at_distance(waypoints, cumulative_distances, distance_km):
    if len(waypoints) == 1:
        lat, lng = _lat_lng(waypoints[0])
        return {
            "lat": lat,
            "lng": lng,
            "distance_km": 0.0,
            "segment_index": 0,
        }

    target = min(max(float(distance_km), 0.0), cumulative_distances[-1])
    for index in range(1, len(cumulative_distances)):
        segment_start = cumulative_distances[index - 1]
        segment_end = cumulative_distances[index]
        if target > segment_end and index < len(cumulative_distances) - 1:
            continue

        start_lat, start_lng = _lat_lng(waypoints[index - 1])
        end_lat, end_lng = _lat_lng(waypoints[index])
        segment_distance = segment_end - segment_start
        ratio = 0.0
        if segment_distance > 0:
            ratio = (target - segment_start) / segment_distance

        return {
            "lat": start_lat + (end_lat - start_lat) * ratio,
            "lng": start_lng + (end_lng - start_lng) * ratio,
            "distance_km": target,
            "segment_index": index - 1,
        }

    lat, lng = _lat_lng(waypoints[-1])
    return {
        "lat": lat,
        "lng": lng,
        "distance_km": cumulative_distances[-1],
        "segment_index": max(0, len(waypoints) - 2),
    }


def sample_route(waypoints, spacing_km=10.0, max_samples=40):
    if spacing_km <= 0:
        raise ValueError("Route sample spacing must be greater than 0")
    if max_samples < 2:
        raise ValueError("Route max sample count must be at least 2")
    if not waypoints:
        return []
    if len(waypoints) == 1:
        lat, lng = _lat_lng(waypoints[0])
        return [{"lat": lat, "lng": lng, "distance_km": 0.0, "segment_index": 0}]

    cumulative_distances = cumulative_route_distances(waypoints)
    total_distance = cumulative_distances[-1]
    if total_distance <= 0:
        lat, lng = _lat_lng(waypoints[0])
        return [{"lat": lat, "lng": lng, "distance_km": 0.0, "segment_index": 0}]

    sample_distances = [0.0]
    next_distance = float(spacing_km)
    while next_distance < total_distance:
        sample_distances.append(next_distance)
        next_distance += float(spacing_km)
    sample_distances.append(total_distance)

    if len(sample_distances) > max_samples:
        step_count = max_samples - 1
        sample_distances = [
            total_distance * index / step_count
            for index in range(max_samples)
        ]

    return [
        _interpolate_point_at_distance(waypoints, cumulative_distances, distance)
        for distance in sample_distances
    ]


def calculate_route_waypoint_etas(
    waypoints,
    start_time,
    speed_kmh,
    anchor_times=None,
):
    if speed_kmh <= 0:
        raise ValueError("Route speed must be greater than 0")
    if not waypoints:
        return []

    start_ts = _timestamp(start_time)
    cumulative_distances = cumulative_route_distances(waypoints)
    known_times = {0: start_ts}

    for raw_index, raw_anchor_time in (anchor_times or {}).items():
        if raw_anchor_time in (None, ""):
            continue
        index = int(raw_index)
        if index < 0 or index >= len(waypoints):
            raise ValueError(f"Route waypoint anchor index is out of range: {index}")

        anchor_time = _timestamp(raw_anchor_time)
        if index == 0 and anchor_time != start_ts:
            raise ValueError("The first waypoint time must match the route start time")
        known_times[index] = anchor_time

    known_indices = sorted(known_times)
    previous_index = known_indices[0]
    previous_time = known_times[previous_index]

    for index in known_indices[1:]:
        anchor_time = known_times[index]
        distance_delta = cumulative_distances[index] - cumulative_distances[previous_index]
        seconds_delta = (anchor_time - previous_time).total_seconds()
        if seconds_delta < 0 or (distance_delta > 0 and seconds_delta <= 0):
            raise ValueError("Route waypoint arrival times must increase along the route")
        previous_index = index
        previous_time = anchor_time

    etas = [None] * len(waypoints)
    for left_index, right_index in zip(known_indices, known_indices[1:]):
        left_time = known_times[left_index]
        right_time = known_times[right_index]
        left_distance = cumulative_distances[left_index]
        right_distance = cumulative_distances[right_index]
        span_distance = right_distance - left_distance
        span_seconds = (right_time - left_time).total_seconds()

        for index in range(left_index, right_index + 1):
            ratio = 0.0
            if span_distance > 0:
                ratio = (cumulative_distances[index] - left_distance) / span_distance
            etas[index] = left_time + pd.Timedelta(seconds=span_seconds * ratio)

    last_known_index = known_indices[-1]
    last_known_time = known_times[last_known_index]
    last_known_distance = cumulative_distances[last_known_index]
    etas[last_known_index] = last_known_time

    for index in range(last_known_index + 1, len(waypoints)):
        distance_delta = cumulative_distances[index] - last_known_distance
        hours_delta = distance_delta / float(speed_kmh)
        etas[index] = last_known_time + pd.Timedelta(hours=hours_delta)

    return etas


def calculate_route_waypoint_times(
    waypoints,
    start_time,
    end_time,
    anchor_times=None,
    waypoint_distances=None,
):
    if not waypoints:
        return []

    start_ts = _timestamp(start_time)
    end_ts = _timestamp(end_time)
    if end_ts <= start_ts:
        raise ValueError("Route end time must be after route start time")
    if len(waypoints) == 1:
        return [start_ts]

    known_times = {
        0: start_ts,
        len(waypoints) - 1: end_ts,
    }

    for raw_index, raw_anchor_time in (anchor_times or {}).items():
        if raw_anchor_time in (None, ""):
            continue
        index = int(raw_index)
        if index < 0 or index >= len(waypoints):
            raise ValueError(f"Route waypoint anchor index is out of range: {index}")
        if index == 0:
            anchor_time = _timestamp(raw_anchor_time)
            if anchor_time != start_ts:
                raise ValueError("The first waypoint time must match the route start time")
            continue
        if index == len(waypoints) - 1:
            anchor_time = _timestamp(raw_anchor_time)
            if anchor_time != end_ts:
                raise ValueError("The final waypoint time must match the route end time")
            continue

        known_times[index] = _timestamp(raw_anchor_time)

    known_indices = sorted(known_times)
    previous_index = known_indices[0]
    previous_time = known_times[previous_index]
    cumulative_distances = (
        list(waypoint_distances)
        if waypoint_distances is not None
        else cumulative_route_distances(waypoints)
    )
    if len(cumulative_distances) != len(waypoints):
        raise ValueError("Route waypoint distance count must match waypoint count")

    for index in known_indices[1:]:
        anchor_time = known_times[index]
        distance_delta = cumulative_distances[index] - cumulative_distances[previous_index]
        seconds_delta = (anchor_time - previous_time).total_seconds()
        if seconds_delta < 0 or (distance_delta > 0 and seconds_delta <= 0):
            raise ValueError("Route waypoint times must increase along the route")
        previous_index = index
        previous_time = anchor_time

    waypoint_times = [None] * len(waypoints)
    for left_index, right_index in zip(known_indices, known_indices[1:]):
        left_time = known_times[left_index]
        right_time = known_times[right_index]
        left_distance = cumulative_distances[left_index]
        right_distance = cumulative_distances[right_index]
        span_distance = right_distance - left_distance
        span_seconds = (right_time - left_time).total_seconds()

        for index in range(left_index, right_index + 1):
            ratio = 0.0
            if span_distance > 0:
                ratio = (cumulative_distances[index] - left_distance) / span_distance
            waypoint_times[index] = left_time + pd.Timedelta(seconds=span_seconds * ratio)

    return waypoint_times


def _interpolate_times_by_distance(target_distances, source_distances, source_times):
    if len(source_distances) != len(source_times):
        raise ValueError("Route distances and ETA counts must match")
    if not source_distances:
        return []
    if len(source_distances) == 1:
        return [_timestamp(source_times[0]) for _ in target_distances]

    source_times = [_timestamp(value) for value in source_times]
    interpolated = []

    for target_distance in target_distances:
        target = min(max(float(target_distance), source_distances[0]), source_distances[-1])
        for index in range(1, len(source_distances)):
            left_distance = source_distances[index - 1]
            right_distance = source_distances[index]
            if target > right_distance and index < len(source_distances) - 1:
                continue

            span_distance = right_distance - left_distance
            ratio = 0.0
            if span_distance > 0:
                ratio = (target - left_distance) / span_distance

            left_time = source_times[index - 1]
            right_time = source_times[index]
            span_seconds = (right_time - left_time).total_seconds()
            interpolated.append(left_time + pd.Timedelta(seconds=span_seconds * ratio))
            break

    return interpolated


def attach_route_sample_etas(samples, waypoints, waypoint_etas, waypoint_distances=None):
    waypoint_distances = (
        list(waypoint_distances)
        if waypoint_distances is not None
        else cumulative_route_distances(waypoints)
    )
    sample_distances = [sample["distance_km"] for sample in samples]
    sample_etas = _interpolate_times_by_distance(
        sample_distances,
        waypoint_distances,
        waypoint_etas,
    )

    return [
        {
            **sample,
            "eta": sample_etas[index],
        }
        for index, sample in enumerate(samples)
    ]


def build_hourly_timeline(start_time, end_time):
    start_ts = _timestamp(start_time)
    end_ts = _timestamp(end_time)
    if end_ts < start_ts:
        raise ValueError("Route end time must be after route start time")

    timeline = [start_ts]
    next_hour = start_ts.ceil("h")
    if next_hour <= start_ts:
        next_hour = next_hour + pd.Timedelta(hours=1)

    while next_hour < end_ts:
        timeline.append(next_hour)
        next_hour = next_hour + pd.Timedelta(hours=1)

    if end_ts != timeline[-1]:
        timeline.append(end_ts)

    return timeline


def linear_interpolate_by_time(rows, timeline, numeric_columns=None, nearest_columns=None):
    source = pd.DataFrame(rows).copy()
    if source.empty:
        return pd.DataFrame({"time": [_timestamp(value) for value in timeline]})
    if "time" not in source.columns:
        raise ValueError("Interpolation source rows must include a time column")

    source["time"] = pd.to_datetime(source["time"]).map(_timestamp)
    source = source.sort_values("time").drop_duplicates("time", keep="last")
    target_times = pd.Series([_timestamp(value) for value in timeline])
    result = pd.DataFrame({"time": target_times})

    source_ns = np.array([_timestamp(value).value for value in source["time"]])
    target_ns = np.array([_timestamp(value).value for value in target_times])
    origin_ns = source_ns[0]
    source_axis = (source_ns - origin_ns).astype(float)
    target_axis = (target_ns - origin_ns).astype(float)

    if numeric_columns is None:
        numeric_columns = [
            column for column in source.columns
            if column != "time" and pd.api.types.is_numeric_dtype(source[column])
        ]

    for column in numeric_columns:
        if column not in source.columns:
            continue
        values = pd.to_numeric(source[column], errors="coerce")
        valid = values.notna()
        if not valid.any():
            continue
        result[column] = np.interp(
            target_axis,
            source_axis[valid.to_numpy()],
            values[valid].to_numpy(dtype=float),
        )

    for column in nearest_columns or []:
        if column not in source.columns:
            continue
        nearest_values = []
        for target_value in target_axis:
            nearest_index = np.abs(source_axis - target_value).argmin()
            nearest_values.append(source.iloc[int(nearest_index)][column])
        result[column] = nearest_values

    return result


def _route_error_reason(response):
    if response is None:
        return None

    try:
        body = response.json()
    except ValueError:
        return None

    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict):
            return error.get("message") or error.get("code")
        if body.get("message"):
            return body.get("message")
        if body.get("reason"):
            return body.get("reason")

    return None


def _clamp_route_index(index, route_geometry):
    return min(max(int(index), 0), max(0, len(route_geometry) - 1))


def _nearest_route_indices(route_geometry, waypoints):
    indices = []
    start_index = 0
    for waypoint in waypoints:
        if start_index >= len(route_geometry):
            indices.append(len(route_geometry) - 1)
            continue

        nearest_index = min(
            range(start_index, len(route_geometry)),
            key=lambda index: haversine_distance_km(route_geometry[index], waypoint),
        )
        indices.append(nearest_index)
        start_index = nearest_index
    return indices


def _fallback_route_indices(route_geometry, waypoint_count):
    if waypoint_count <= 1:
        return [0] if route_geometry else []

    last_index = max(0, len(route_geometry) - 1)
    return [
        round(last_index * index / (waypoint_count - 1))
        for index in range(waypoint_count)
    ]


def parse_openrouteservice_route(payload, waypoint_count=None, waypoints=None):
    if not isinstance(payload, dict):
        raise RouteWeatherError("OpenRouteService returned invalid route data")

    features = payload.get("features")
    if not isinstance(features, list) or not features:
        raise RouteWeatherError("OpenRouteService returned no route")

    feature = features[0]
    geometry = feature.get("geometry", {}) if isinstance(feature, dict) else {}
    coordinates = geometry.get("coordinates")
    if not isinstance(coordinates, list) or len(coordinates) < 2:
        raise RouteWeatherError("OpenRouteService route is missing geometry")

    route_geometry = [
        {
            "lat": float(coordinate[1]),
            "lng": float(coordinate[0]),
        }
        for coordinate in coordinates
        if isinstance(coordinate, (list, tuple)) and len(coordinate) >= 2
    ]
    if len(route_geometry) < 2:
        raise RouteWeatherError("OpenRouteService route geometry is too short")

    properties = feature.get("properties", {})
    summary = properties.get("summary", {}) if isinstance(properties, dict) else {}
    cumulative_distances = cumulative_route_distances(route_geometry)

    raw_waypoint_indices = properties.get("way_points") if isinstance(properties, dict) else None
    if isinstance(raw_waypoint_indices, list) and waypoint_count and len(raw_waypoint_indices) == waypoint_count:
        waypoint_indices = [
            _clamp_route_index(index, route_geometry)
            for index in raw_waypoint_indices
        ]
    elif waypoints:
        waypoint_indices = _nearest_route_indices(route_geometry, waypoints)
    elif waypoint_count:
        waypoint_indices = _fallback_route_indices(route_geometry, waypoint_count)
    else:
        waypoint_indices = [0, len(route_geometry) - 1]

    waypoint_distances = [
        cumulative_distances[_clamp_route_index(index, route_geometry)]
        for index in waypoint_indices
    ]

    return {
        "geometry": route_geometry,
        "waypoint_indices": waypoint_indices,
        "waypoint_distances_km": waypoint_distances,
        "distance_km": float(summary.get("distance", cumulative_distances[-1] * 1000)) / 1000,
        "duration_seconds": summary.get("duration"),
    }


def fetch_openrouteservice_route(waypoints, profile, api_key, timeout=20):
    if len(waypoints) < 2:
        raise RouteWeatherError("OpenRouteService routing requires at least two waypoints")
    if profile not in OPENROUTESERVICE_PROFILES:
        raise RouteWeatherError(f"Unsupported OpenRouteService profile: {profile}")
    if not api_key:
        raise RouteWeatherError("OpenRouteService API key is required for snapped routing")

    coordinates = [
        [float(_lat_lng(waypoint)[1]), float(_lat_lng(waypoint)[0])]
        for waypoint in waypoints
    ]
    headers = {
        "Authorization": api_key,
        "Accept": "application/json, application/geo+json",
        "Content-Type": "application/json",
    }
    body = {
        "coordinates": coordinates,
        "instructions": False,
    }

    try:
        response = requests.post(
            OPENROUTESERVICE_DIRECTIONS_API_URL.format(profile=profile),
            json=body,
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.HTTPError as exc:
        reason = _route_error_reason(exc.response)
        if reason is None:
            reason = str(exc)
        raise RouteWeatherError(f"OpenRouteService routing failed: {reason}") from exc
    except requests.RequestException as exc:
        raise RouteWeatherError(f"OpenRouteService routing failed: {exc}") from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise RouteWeatherError("OpenRouteService returned invalid JSON") from exc

    return parse_openrouteservice_route(
        payload,
        waypoint_count=len(waypoints),
        waypoints=waypoints,
    )


def _response_error_reason(response):
    if response is None:
        return None

    try:
        body = response.json()
    except ValueError:
        return None

    if isinstance(body, dict) and body.get("error"):
        return body.get("reason", "Unknown Open-Meteo API error")

    return None


def parse_route_forecast_response(payload, expected_count=None):
    if isinstance(payload, dict) and payload.get("error"):
        raise RouteWeatherError(
            f"Open-Meteo route forecast failed: {payload.get('reason', 'Unknown Open-Meteo API error')}"
        )

    locations = payload if isinstance(payload, list) else [payload]
    if expected_count is not None and len(locations) != expected_count:
        raise RouteWeatherError(
            f"Open-Meteo returned {len(locations)} route forecasts for {expected_count} sample points"
        )

    parsed = []
    for location in locations:
        if not isinstance(location, dict) or "hourly" not in location:
            raise RouteWeatherError("Open-Meteo route forecast response is missing hourly data")

        hourly = pd.DataFrame(location["hourly"])
        if hourly.empty or "time" not in hourly.columns:
            raise RouteWeatherError("Open-Meteo route forecast response has no hourly timestamps")
        hourly["time"] = pd.to_datetime(hourly["time"]).map(_timestamp)

        hourly_units = dict(location.get("hourly_units", {}))
        if "weather_code" in hourly.columns and "weathercode" not in hourly.columns:
            hourly["weathercode"] = hourly["weather_code"]
            if "weather_code" in hourly_units:
                hourly_units["weathercode"] = hourly_units["weather_code"]

        parsed.append(
            {
                "latitude": location.get("latitude"),
                "longitude": location.get("longitude"),
                "timezone": location.get("timezone"),
                "timezone_abbreviation": location.get("timezone_abbreviation"),
                "hourly_units": hourly_units,
                "hourly": hourly,
            }
        )

    return parsed


def fetch_route_forecasts(samples, forecast_days=7, timeout=20):
    if not samples:
        raise RouteWeatherError("Route forecast requires at least one sample point")

    params = {
        "latitude": ",".join(_format_coordinate(sample["lat"]) for sample in samples),
        "longitude": ",".join(_format_coordinate(sample["lng"]) for sample in samples),
        "hourly": ",".join(ROUTE_HOURLY_VARIABLES),
        "forecast_days": int(forecast_days),
        "timezone": "auto",
        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
    }

    try:
        response = requests.get(
            ROUTE_FORECAST_API_URL,
            params=params,
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.HTTPError as exc:
        reason = _response_error_reason(exc.response)
        if reason is None:
            reason = str(exc)
        raise RouteWeatherError(f"Open-Meteo route forecast failed: {reason}") from exc
    except requests.RequestException as exc:
        raise RouteWeatherError(f"Open-Meteo route forecast failed: {exc}") from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise RouteWeatherError("Open-Meteo route forecast returned invalid JSON") from exc

    return parse_route_forecast_response(payload, expected_count=len(samples))


def _interpolate_forecast_at_time(hourly, target_time):
    target_ts = _timestamp(target_time)
    hourly_times = pd.to_datetime(hourly["time"]).map(_timestamp)
    if target_ts < hourly_times.min() or target_ts > hourly_times.max():
        raise RouteWeatherError(
            "Selected route time is outside the fetched forecast window. "
            "Fetch Route Weather again for the updated time range."
        )

    continuous_columns = [
        column for column in ROUTE_PLOT_VARIABLES
        if column in hourly.columns and column != "weathercode"
    ]
    interpolated = linear_interpolate_by_time(
        hourly,
        [target_ts],
        numeric_columns=continuous_columns,
        nearest_columns=["weathercode"],
    )
    row = interpolated.iloc[0].to_dict()
    if "weathercode" in row and not pd.isna(row["weathercode"]):
        row["weathercode"] = int(round(float(row["weathercode"])))
    return row


def build_route_hourly_report(samples, forecasts):
    if not samples:
        raise RouteWeatherError("Route report requires route samples")
    if len(samples) != len(forecasts):
        raise RouteWeatherError("Route sample and forecast counts do not match")

    sample_rows = []
    units = {}

    for sample, forecast in zip(samples, forecasts):
        forecast_row = _interpolate_forecast_at_time(forecast["hourly"], sample["eta"])
        units.update(forecast.get("hourly_units", {}))
        sample_rows.append(
            {
                **forecast_row,
                "time": _timestamp(sample["eta"]),
                "distance_km": sample["distance_km"],
                "lat": sample["lat"],
                "lng": sample["lng"],
            }
        )

    timeline = build_hourly_timeline(sample_rows[0]["time"], sample_rows[-1]["time"])
    numeric_columns = [
        "distance_km",
        "lat",
        "lng",
        "temperature_2m",
        "apparent_temperature",
        "dew_point_2m",
        "relative_humidity_2m",
        "precipitation_probability",
        "cloud_cover",
        "surface_pressure",
        "precipitation",
        "rain",
        "showers",
        "snowfall",
        "wind_speed_10m",
        "wind_gusts_10m",
        "uv_index",
        "visibility",
    ]

    report = linear_interpolate_by_time(
        sample_rows,
        timeline,
        numeric_columns=numeric_columns,
        nearest_columns=["weathercode"],
    )
    if "weathercode" in report.columns:
        report["weathercode"] = report["weathercode"].round().astype("Int64")
    report["hazards"] = report.apply(classify_route_hazards, axis=1)

    return report, units


def classify_route_hazards(row):
    hazards = []

    precipitation_probability = row.get("precipitation_probability")
    precipitation_amount = (
        (row.get("rain") or 0)
        + (row.get("showers") or 0)
        + (row.get("snowfall") or 0)
    )
    wind_speed = row.get("wind_speed_10m")
    wind_gusts = row.get("wind_gusts_10m")
    uv_index = row.get("uv_index")
    visibility = row.get("visibility")
    temperature = row.get("temperature_2m")

    if pd.notna(precipitation_probability) and precipitation_probability >= 50:
        hazards.append("Rain likely")
    elif pd.notna(precipitation_amount) and precipitation_amount >= 1:
        hazards.append("Wet")

    if pd.notna(wind_gusts) and wind_gusts >= 50:
        hazards.append("Strong gusts")
    elif pd.notna(wind_speed) and wind_speed >= 35:
        hazards.append("Windy")

    if pd.notna(uv_index) and uv_index >= 6:
        hazards.append("High UV")

    if pd.notna(visibility) and visibility <= 5000:
        hazards.append("Low visibility")

    if pd.notna(temperature) and temperature <= 0:
        hazards.append("Freezing")
    elif pd.notna(temperature) and temperature >= 32:
        hazards.append("Heat")

    return ", ".join(hazards) if hazards else "Clear"


def route_forecast_days_needed(route_end_time, now=None, max_days=16):
    now_ts = _timestamp(now if now is not None else pd.Timestamp.now())
    route_end_ts = _timestamp(route_end_time)
    days_needed = max(1, (route_end_ts.normalize() - now_ts.normalize()).days + 1)
    if days_needed > max_days:
        raise RouteWeatherError(
            f"Route end time is beyond Open-Meteo's {max_days}-day forecast window"
        )
    return int(days_needed)
