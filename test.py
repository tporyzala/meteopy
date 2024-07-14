# %% GEOCODING
import requests
import folium.raster_layers
import folium.plugins
import folium
import json

import pandas as pd
from pandas import json_normalize
import meteopy as mp
import plotly.io as pio
import numpy as np
import plotly.figure_factory as ff
import plotly.express as px

# %%
api_url = mp.MeteoManager.geocoding
options_geocoding = mp.OptionsGeocoding('boulder', count=20, format='json')
manager_geo = mp.MeteoManager(api_url, options_geocoding)

r = manager_geo.fetch()
r

# %% ELEVATION
api_url = mp.MeteoManager.elevation
options_elevation = mp.OptionsElevation(40.0150, 105.2705)
manager_elevation = mp.MeteoManager(api_url, options_elevation)

r = manager_elevation.fetch()
r
# %% FORECASTING

api_url = mp.MeteoManager.forecast
options_forecast = mp.OptionsForecast(40.0150, 105.2705)

hourly = mp.HourlyForcast()
hourly.all()

daily = mp.DailyForcast()
daily.all()


manager_forecast = mp.MeteoManager(api_url, options_forecast, hourly, daily)

df = manager_forecast.fetch()
hourly = df['hourly']
daily = df['daily']


# %% ENSEMBLE
api_url = mp.MeteoManager.ensemble
options_ensemble = mp.OptionsEnsemble(40.0150, 105.2705)

hourly = mp.HourlyEnsemble()
hourly.all()

manager_ensemble = mp.MeteoManager(api_url, options_ensemble, hourly)

de = manager_ensemble.fetch()
hourly = de['hourly']

# %%
df = px.data.tips()
fig = px.box(df, x="time", y="total_bill")
fig.show()


# %% MAPPING

m = folium.Map(location=[40.0255, -105.2751], zoom_start=10)
folium.LatLngPopup().add_to(m)
folium.plugins.Geocoder().add_to(m)
folium.plugins.LocateControl(auto_start=False).add_to(m)
folium.raster_layers.WmsTileLayer(
    url='https://opengeo.ncep.noaa.gov:443/geoserver/conus/conus_bref_qcd/ows?SERVICE=WMS&',
    layers='conus_bref_qcd',
    version='1.3.0',
    fmt='image/png',
    transparent=True,
    # kwargs='TIME=2023-09-21T06:22:02.000Z'
).add_to(m)
m

# %%
latitude = 40.0150
longitude = 105.2705

api_url = mp.MeteoManager.ensemble
options = mp.OptionsEnsemble(latitude, longitude)
hourly = mp.HourlyEnsemble().all()
manager = mp.MeteoManager(api_url, options, hourly)
r = manager.fetch()


r


# %%


def get_weather_forecast(latitude, longitude):
    """
    Fetches weather forecast for a specific location using the Open-Meteo API.

    Parameters:
    latitude (float): Latitude of the location.
    longitude (float): Longitude of the location.

    Returns:
    dict: The weather forecast data.
    """
    base_url = "https://api.open-meteo.com/v1/forecast"
    params = {
        'latitude': latitude,
        'longitude': longitude,
        'hourly': 'temperature_2m,precipitation',
        'daily': 'temperature_2m_max,temperature_2m_min',
        'timezone': 'auto'
    }

    response = requests.get(base_url, params=params)
    response.raise_for_status()  # Raise an error for bad status codes
    return response.json()


# Example usage:
forecast = get_weather_forecast(37.7749, -122.4194)
print(forecast)
