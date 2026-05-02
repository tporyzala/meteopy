import requests
import pandas as pd


class MeteoManager:

    forecast = "https://api.open-meteo.com/v1/forecast?"
    historical = "https://archive-api.open-meteo.com/v1/archive?"
    ensemble = "https://ensemble-api.open-meteo.com/v1/ensemble?"
    climate = "https://climate-api.open-meteo.com/v1/climate?"
    marine = "https://marine-api.open-meteo.com/v1/marine?"
    air_quality = "https://air-quality-api.open-meteo.com/v1/air-quality?"
    geocoding = "https://geocoding-api.open-meteo.com/v1/search?"
    elevation = "https://api.open-meteo.com/v1/elevation?"
    flood = "https://flood-api.open-meteo.com/v1/flood?"
    default_timeout = 20

    def __init__(self, api_url: str = None, options=None, hourly=None, daily=None, apikey=None, timeout=None) -> None:
        self.api_url = api_url
        self.options = options
        self.hourly = hourly
        self.daily = daily
        self.apikey = apikey
        self.timeout = timeout or self.default_timeout

        return None

    def get_payload(self) -> dict:
        payload = dict(vars(self.options)) if self.options is not None else {}

        if hasattr(self.options, 'current') and self.options.current is not None:
            payload['current'] = self._join_params(self.options.current)

        if self.hourly is not None:
            payload['hourly'] = self._join_params(self.hourly.params)

        if self.daily is not None:
            payload['daily'] = self._join_params(self.daily.params)

        return payload

    @staticmethod
    def _join_params(params):
        if isinstance(params, str):
            return params
        return ",".join(params)

    @staticmethod
    def _response_error_reason(response):
        if response is None:
            return None

        try:
            body = response.json()
        except ValueError:
            return None

        if isinstance(body, dict) and body.get('error'):
            return body.get('reason', 'Unknown Open-Meteo API error')

        return None

    def fetch(self, out=1):
        """Fetches data from API

        Returns:
            json: JSON response
        """
        payload = self.get_payload()

        try:
            response = requests.get(
                self.api_url,
                params=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.HTTPError as exc:
            reason = self._response_error_reason(exc.response)
            if reason is None:
                reason = str(exc)
            raise RuntimeError(f"Open-Meteo request failed: {reason}") from exc
        except requests.RequestException as exc:
            raise RuntimeError(f"Open-Meteo request failed: {exc}") from exc

        try:
            r = response.json()
        except ValueError as exc:
            raise RuntimeError("Open-Meteo returned invalid JSON") from exc

        if isinstance(r, dict) and r.get('error'):
            reason = r.get('reason', 'Unknown Open-Meteo API error')
            raise RuntimeError(f"Open-Meteo request failed: {reason}")

        if 'daily' in r.keys():
            r['daily'] = pd.DataFrame.from_dict(
                r['daily'],
                orient='index',
            ).T
        if 'hourly' in r.keys():
            r['hourly'] = pd.DataFrame.from_dict(
                r['hourly'],
                orient='index',
            ).T

        return r
