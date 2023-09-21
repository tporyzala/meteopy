
import streamlit as st
import folium
import folium.plugins
import folium.raster_layers
from streamlit_folium import st_folium

import pandas as pd
import numpy as np
import pydeck as pdk
import meteopy as mp


st.set_page_config(layout="wide")


def fetch_forcast(latitude, longitude):
    api_url = mp.MeteoManager.forecast
    options_forecast = mp.OptionsForecast(latitude, longitude)
    hourly = mp.HourlyForcast()
    daily = mp.DailyForcast()
    hourly.all()
    daily.all()
    manager_forecast = mp.MeteoManager(
        api_url, options_forecast, hourly, daily)
    r2 = manager_forecast.fetch()
    return r2


st.title('Weather Forcasting')

# Initialize map
latitude = 40.0158
longitude = -105.2792
tiles = "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png"
attr = 'Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)'
m = folium.Map(
    location=[latitude, longitude],
    zoom_start=12,
    tiles=tiles,
    attr=attr,
)
folium.LatLngPopup().add_to(m)
folium.plugins.Geocoder().add_to(m)
folium.plugins.LocateControl(auto_start=False).add_to(m)
folium.raster_layers.WmsTileLayer(
    url='https://opengeo.ncep.noaa.gov:443/geoserver/conus/conus_bref_qcd/ows?SERVICE=WMS&',
    layers='conus_bref_qcd',
    version='1.3.0',
    fmt='image/png',
    transparent=True,
).add_to(m)

# Call to render Folium map in Streamlit
st_data = st_folium(m, use_container_width=True,)

st.write(st_data)

# Update latitude and longitude when clicked on map
if st_data["last_clicked"]:
    latiude = st_data["last_clicked"]["lat"]
    longitude = st_data["last_clicked"]["lng"]
else:
    latiude = st_data["center"]["lat"]
    longitude = st_data["center"]["lng"]
forcast = fetch_forcast(latitude, longitude)

# Forcast options
with st.expander('Forcast'):
    st.write(forcast)

with st.expander('Models'):
    st.write('b')
