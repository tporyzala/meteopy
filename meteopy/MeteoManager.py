import http.client
import requests
import json
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

    def __init__(self, api_url: str = None, options=None, hourly=None, daily=None, apikey=None) -> None:
        self.api_url = api_url
        self.options = options
        self.hourly = hourly
        self.daily = daily
        self.apikey = apikey

        return None

    def get_payload(self) -> str:
        payload = vars(self.options)

        if self.hourly is not None:
            payload['hourly'] = ",".join(self.hourly.params)

        if self.daily is not None:
            payload['daily'] = ",".join(self.daily.params)

        payload = "&".join("%s=%s" % (i, j) for i, j in payload.items())

        return payload

    def get_data(self):
        payload = self.get_payload()

        r = requests.get(self.api_url, payload)
        print(self.api_url, payload)

        return json.loads(r.content.decode('utf-8'))
