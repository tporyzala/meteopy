# %% GEOCODING
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

r = manager_forecast.fetch()
hourly = r['hourly']
daily = r['daily']


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
d = {
    'a': 1,
    'b': 2,
    'c': 3,
}

df = pd.DataFrame(d, index=[0])
df
