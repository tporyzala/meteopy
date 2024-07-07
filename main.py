
import streamlit as st
import folium
import folium.plugins
import folium.raster_layers
from streamlit_folium import st_folium

import pandas as pd
import numpy as np
import pydeck as pdk
import meteopy as mp
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.figure_factory as ff
from math import radians, isclose
from streamlit_extras.buy_me_a_coffee import button

st.set_page_config(layout='wide', page_title='Point Weather Forecasting')

debug = False


# @st.cache_data
def fetch_forcast(latitude, longitude):
    api_url = mp.MeteoManager.forecast
    options = mp.OptionsForecast(latitude, longitude)
    hourly = mp.HourlyForcast().all()
    daily = mp.DailyForcast().all()
    manager = mp.MeteoManager(api_url, options, hourly, daily)
    r = manager.fetch()
    print("fetching...")
    return r


# @st.cache_data
def fetch_ensemble(latitude, longitude):
    api_url = mp.MeteoManager.ensemble
    options = mp.OptionsEnsemble(latitude, longitude)
    hourly = mp.HourlyEnsemble().all()
    manager = mp.MeteoManager(api_url, options, hourly)
    r = manager.fetch()
    print("fetching...")
    return r


def moving_average(data, window):
    weights = np.repeat(1.0, window) / window
    return np.convolve(data, weights, mode='valid')


def add_position(df):
    tmp = pd.DataFrame(
        {
            'Latitude': df['latitude'],
            'Longitude': df['longitude'],
            'Elevation': df['elevation'],
        },
        index=[0],
    )
    st.dataframe(tmp, use_container_width=True, hide_index=True)


# Title columns
col1, col2 = st.columns([3, 1])
with col1:
    st.title('Point Weather Forecasting')
with col2:
    button(username="tporyzala", floating=False, width=221)

# Initialize map
tiles = 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png'
attr = 'Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)'
m = folium.Map(
    # location=[40.0158, -105.2792], Boulder
    location=[47.6943, 11.7749],  # Tegernsee
    zoom_start=12,
    tiles=tiles,
    attr=attr,
)

folium.LatLngPopup().add_to(m)
folium.plugins.Geocoder().add_to(m)
folium.plugins.LocateControl(auto_start=False).add_to(m)
folium.plugins.MousePosition().add_to(m)
folium.raster_layers.WmsTileLayer(
    url='https://opengeo.ncep.noaa.gov:443/geoserver/conus/conus_bref_qcd/ows?SERVICE=WMS&',
    layers='conus_bref_qcd',
    version='1.3.0',
    fmt='image/png',
    transparent=True,
).add_to(m)
folium.LayerControl().add_to(m)
folium.GeoJson(
    data='http://www.wpc.ncep.noaa.gov/NationalForecastChart/mapdata/ERODay2.geojson',
)

# Draw map
st_data = st_folium(
    m,
    use_container_width=True,
)

# Latitude and longitude from map
if st_data['last_clicked'] == None:
    latitude = st_data['center']['lat']
    longitude = st_data['center']['lng']
else:
    latitude = st_data['last_clicked']['lat']
    longitude = st_data['last_clicked']['lng']

# Fetch forecast
df = fetch_forcast(latitude, longitude)
df_hourly = df['hourly']
df_daily = df['daily']

# Fetch ensemble
de = fetch_ensemble(latitude, longitude)
de_hourly = de['hourly']

# Add position table under map
add_position(df)

# Subplots (forecast)
f_fig = make_subplots(
    rows=4,
    cols=1,
    shared_xaxes=True,
    vertical_spacing=0.0,
    specs=[[{'secondary_y': True}],
           [{'secondary_y': True}],
           [{'secondary_y': True}],
           [{'secondary_y': True}],
           ],
)

f_fig.add_trace(
    go.Scatter(
        x=df_hourly['time'], y=df_hourly['temperature_2m'], name='Temperature', line=dict(color='firebrick'), opacity=1, legendgroup='1',
    ),
    secondary_y=False, row=1, col=1,
)

f_fig.add_trace(
    go.Scatter(
        x=df_hourly['time'], y=df_hourly['apparent_temperature'], name='Feels like', line=dict(color='firebrick'), opacity=0.4, legendgroup='1',
    ),
    secondary_y=False, row=1, col=1,
)

f_fig.add_trace(
    go.Scatter(
        x=df_hourly['time'], y=df_hourly['dewpoint_2m'], name='Dewpoint', line=dict(color='forestgreen'), opacity=0.4, legendgroup='1',
    ),
    secondary_y=False, row=1, col=1,
)

f_fig.add_hline(
    y=0, row=1, col=1, opacity=0.5, line=dict(color='rgb(0,0,255)')
)

f_fig.add_trace(
    go.Scatter(
        x=df_hourly['time'], y=df_hourly['precipitation_probability'], name='Precip. %', fill='tozeroy', line_color='rgba(165,210,225,0.8)', fillcolor='rgba(165,210,225,0.8)', legendgroup='2',
    ),
    secondary_y=True, row=2, col=1,
)

f_fig.add_trace(
    go.Scatter(
        x=df_hourly['time'], y=moving_average(df_hourly['cloudcover'], 3), fill='tozeroy', line_color='rgba(0,0,0,0.1)', fillcolor='rgba(0,0,0,0.1)', name='Cloud Cover', legendgroup='2',
    ),
    secondary_y=True, row=2, col=1,
)

f_fig.add_trace(
    go.Scatter(
        x=df_hourly['time'], y=moving_average(df_hourly['surface_pressure'], 3), name='Pressure', legendgroup='2', line=dict(color='rgba(0,0,0,0.95)')
    ),
    secondary_y=False, row=2, col=1,
)

f_fig.add_trace(
    go.Scatter(
        x=df_hourly['time'], y=df_hourly['weathercode'], name='WCO', legendgroup='2',
    ),
    secondary_y=True, row=2, col=1,
)

f_fig.add_trace(
    go.Bar(
        x=df_hourly['time'], y=df_hourly['rain'], name='Rain', legendgroup='3',
    ),
    secondary_y=False, row=3, col=1,
)

f_fig.add_trace(
    go.Bar(
        x=df_hourly['time'], y=df_hourly['showers'], name='Shower', legendgroup='3',
    ),
    secondary_y=False, row=3, col=1,
)

f_fig.add_trace(
    go.Bar(
        x=df_hourly['time'], y=df_hourly['snowfall']*10, name='Snow', legendgroup='3',
    ),
    secondary_y=False, row=3, col=1,
)

f_fig.add_trace(
    go.Scatter(
        x=df_hourly['time'], y=moving_average(df_hourly['windspeed_10m'], 3), name='Wind Speed', legendgroup='4',
    ),
    secondary_y=False, row=4, col=1,
)

f_fig.add_trace(
    go.Scatter(
        x=df_hourly['time'], y=moving_average(df_hourly['windgusts_10m'], 3), name='Wind Gusts', legendgroup='4',
    ),
    secondary_y=False, row=4, col=1,
)

f_fig.add_vline(
    x=df['current_weather']['time'], row='all', col=1, opacity=0.5, line=dict(color='rgb(100,100,100)')
)

for i, row in df_daily.iterrows():
    f_fig.add_vline(
        x=row["time"], row='all', col=1, opacity=0.05, line=dict(color='rgb(100,100,100)')
    )
    if i == 0:
        ss = row['sunset']
    else:
        sr = row['sunrise']
        f_fig.add_vrect(
            x0=ss,
            x1=sr,
            fillcolor="rgb(100,100,100)",
            opacity=0.05,
            line_width=0,
        )
        ss = row['sunset']

layout = {
    'hovermode': 'x unified',
    'hoverlabel': dict(
        bgcolor='rgba(255,255,255,0.5)',
    ),
    'legend_tracegroupgap': 90,
    'height': 800,
    'barmode': 'stack',
    'xaxis': {
        'anchor': 'y',
        'matches': 'x2',
        'showticklabels': False,
    },
    'xaxis2': {
        'anchor': 'y3',
        'showticklabels': False,
    },
    'xaxis3': {
        'anchor': 'y5',
        'showticklabels': False,
    },
    'xaxis4': {
        'anchor': 'y7',
        'showticklabels': True,
    },
    'yaxis': {
        'anchor': 'x',
        'ticksuffix': df['hourly_units']['temperature_2m'],
        'title': 'Temperature',
    },
    'yaxis2': {
        'anchor': 'x',
        'side': 'right',
        'showgrid': False,
        'showticklabels': False,
    },
    'yaxis3': {
        'anchor': 'x2',
        'rangemode': 'nonnegative',
        'ticksuffix': df['hourly_units']['surface_pressure'],
        'title': 'Pressure',
    },
    'yaxis4': {
        'anchor': 'x2',
        'range': [0, 100],
        'side': 'right',
        'ticksuffix': df['hourly_units']['precipitation_probability'],
        'title': 'Precipitation Probability',
    },
    'yaxis5': {
        'anchor': 'x3',
        'ticksuffix': df['hourly_units']['precipitation'],
        'rangemode': 'nonnegative',
        'title': 'Precipitation',
    },
    'yaxis6': {
        'anchor': 'x3',
        'side': 'right',
        'showgrid': False,
        'showticklabels': False,
    },
    'yaxis7': {
        'anchor': 'x4',
        'ticksuffix': df['hourly_units']['windspeed_10m'],
        'rangemode': 'nonnegative',
        'title': 'Wind Speed',
    },
    'yaxis8': {
        'anchor': 'x4',
        'side': 'right',
        'showgrid': False,
        'showticklabels': False,
    },
    'legend': dict(
        orientation="h",
        groupclick='toggleitem',
    ),
}
f_fig.update_layout(**layout)

# Subplots (ensemble)
e_fig = make_subplots(
    rows=5,
    cols=1,
    shared_xaxes=True,
    vertical_spacing=0.0,
    specs=[[{'secondary_y': True}],
           [{'secondary_y': True}],
           [{'secondary_y': True}],
           [{'secondary_y': True}],
           [{'secondary_y': True}],
           ],
)

dat = pd.DataFrame()
for key in de_hourly.columns.tolist():
    if key.startswith('apparent_temperature_'):
        tmp = pd.DataFrame({'time': de_hourly['time'], 'dat': de_hourly[key]})
        dat = pd.concat([dat, tmp], ignore_index=True)
e_fig.add_trace(
    go.Box(
        x=dat['time'], y=dat['dat'],
    ),
    secondary_y=False, row=1, col=1,
)

e_fig.add_hline(
    y=0, row=1, col=1, opacity=0.5, line=dict(color='rgb(0,0,255)')
)

dat = pd.DataFrame()
for key in de_hourly.columns.tolist():
    if key.startswith('cloudcover_'):
        tmp = pd.DataFrame({'time': de_hourly['time'], 'dat': de_hourly[key]})
        dat = pd.concat([dat, tmp], ignore_index=True)
e_fig.add_trace(
    go.Box(
        x=dat['time'], y=dat['dat'],
    ),
    secondary_y=False, row=2, col=1,
)

dat = pd.DataFrame()
for key in de_hourly.columns.tolist():
    if key.startswith('precipitation_'):
        tmp = pd.DataFrame({'time': de_hourly['time'], 'dat': de_hourly[key]})
        dat = pd.concat([dat, tmp], ignore_index=True)
e_fig.add_trace(
    go.Box(
        x=dat['time'], y=dat['dat'],
    ),
    secondary_y=False, row=3, col=1,
)

dat = pd.DataFrame()
for key in de_hourly.columns.tolist():
    if key.startswith('windspeed_10m_'):
        tmp = pd.DataFrame({'time': de_hourly['time'], 'dat': de_hourly[key]})
        dat = pd.concat([dat, tmp], ignore_index=True)
e_fig.add_trace(
    go.Box(
        x=dat['time'], y=dat['dat'],
    ),
    secondary_y=False, row=4, col=1,
)

dat = pd.DataFrame()
for key in de_hourly.columns.tolist():
    if key.startswith('windgusts_10m_'):
        tmp = pd.DataFrame({'time': de_hourly['time'], 'dat': de_hourly[key]})
        dat = pd.concat([dat, tmp], ignore_index=True)
e_fig.add_trace(
    go.Box(
        x=dat['time'], y=dat['dat'],
    ),
    secondary_y=False, row=4, col=1,
)

dat = pd.DataFrame()
for key in de_hourly.columns.tolist():
    if key.startswith('pressure_msl_'):
        tmp = pd.DataFrame({'time': de_hourly['time'], 'dat': de_hourly[key]})
        dat = pd.concat([dat, tmp], ignore_index=True)
e_fig.add_trace(
    go.Box(
        x=dat['time'], y=dat['dat'],
    ),
    secondary_y=False, row=5, col=1,
)

e_fig.add_vline(
    x=df['current_weather']['time'], row='all', col=1, opacity=0.5, line=dict(color='rgb(100,100,100)')
)

for i, row in df_daily.iterrows():
    e_fig.add_vline(
        x=row["time"], row='all', col=1, opacity=0.05, line=dict(color='rgb(100,100,100)')
    )
    if i == 0:
        ss = row['sunset']
    else:
        sr = row['sunrise']
        e_fig.add_vrect(
            x0=ss,
            x1=sr,
            fillcolor="rgb(100,100,100)",
            opacity=0.05,
            line_width=0,
        )
        ss = row['sunset']

layout = {
    'hovermode': 'x unified',
    'hoverlabel': dict(
        bgcolor='rgba(255,255,255,0.5)',
    ),
    'legend_tracegroupgap': 90,
    'height': 800,
    'barmode': 'stack',
    'xaxis': {
        'anchor': 'y',
        'matches': 'x2',
        'showticklabels': False,
    },
    'xaxis2': {
        'anchor': 'y3',
        'showticklabels': False,
    },
    'xaxis3': {
        'anchor': 'y5',
        'showticklabels': False,
    },
    'xaxis4': {
        'anchor': 'y7',
        'showticklabels': False,
    },
    'xaxis5': {
        'anchor': 'y9',
        'showticklabels': True,
    },
    'yaxis': {
        'anchor': 'x',
        'ticksuffix': de['hourly_units']['apparent_temperature'],
        'title': 'Temperature',
    },
    'yaxis2': {
        'anchor': 'x',
        'side': 'right',
        'showgrid': False,
        'showticklabels': False,
    },
    'yaxis3': {
        'anchor': 'x2',
        'range': [0, 100],
        'ticksuffix': de['hourly_units']['cloudcover'],
        'title': 'Cloud Cover',
    },
    'yaxis4': {
        'anchor': 'x2',
        'side': 'right',
        'showgrid': False,
        'showticklabels': False,
    },
    'yaxis5': {
        'anchor': 'x3',
        'ticksuffix': de['hourly_units']['precipitation'],
        'rangemode': 'nonnegative',
        'title': 'Precipitation',
    },
    'yaxis6': {
        'anchor': 'x3',
        'side': 'right',
        'showgrid': False,
        'showticklabels': False,
    },
    'yaxis7': {
        'anchor': 'x4',
        'ticksuffix': de['hourly_units']['windspeed_10m'],
        'rangemode': 'nonnegative',
        'title': 'Wind Speed',
    },
    'yaxis8': {
        'anchor': 'x4',
        'side': 'right',
        'showgrid': False,
        'showticklabels': False,
    },
    'yaxis9': {
        'anchor': 'x5',
        'ticksuffix': de['hourly_units']['pressure_msl'],
        'rangemode': 'nonnegative',
        'title': 'Pressure',
    },
    'yaxis10': {
        'anchor': 'x5',
        'side': 'right',
        'showgrid': False,
        'showticklabels': False,
    },
    'legend': dict(
        orientation="h",
        groupclick='toggleitem',
    ),
}
e_fig.update_layout(**layout)

tab1, tab2 = st.tabs(["Forecast", "Ensemble"])
with tab1:
    st.plotly_chart(f_fig, use_container_width=True)
with tab2:
    st.plotly_chart(e_fig, use_container_width=True)

# st.dataframe(
#     data=df_daily[[
#         'time',
#         'temperature_2m_max',
#         'apparent_temperature_max',
#         'temperature_2m_min',
#         'apparent_temperature_min',
#         'rain_sum',
#         'showers_sum',
#         'snowfall_sum',
#         'windspeed_10m_max',
#         'windgusts_10m_max',

#     ]].T,
#     use_container_width=True,
#     hide_index=False,
# )


if debug:
    st.write('DEBUG')
    st.write(st_data)
    st.write(df_daily)
    st.write(df)
    st.write(de)
