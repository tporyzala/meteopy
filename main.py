
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


st.set_page_config(layout='wide')


@st.cache_data
def fetch_forcast(latitude, longitude):
    api_url = mp.MeteoManager.forecast
    options = mp.OptionsForecast(latitude, longitude)
    hourly = mp.HourlyForcast().all()
    daily = mp.DailyForcast().all()
    manager = mp.MeteoManager(api_url, options, hourly, daily)
    r = manager.fetch()
    print("fetching...")
    return r


def fetch_ensemble(latitude, longitude):
    api_url = mp.MeteoManager.ensemble
    options = mp.OptionsEnsemble(latitude, longitude)
    hourly = mp.HourlyEnsemble().all()
    manager = mp.MeteoManager(api_url, options, hourly)
    r = manager.fetch()
    return r


def moving_average(data, window):
    weights = np.repeat(1.0, window) / window
    return np.convolve(data, weights, mode='valid')


def add_position_to_c(c, df):
    with c:
        tmp = pd.DataFrame(
            {
                'Latitude': df['latitude'],
                'Longitude': df['longitude'],
                'Elevation': df['elevation'],
            },
            index=[0],
        )
        st.dataframe(tmp, use_container_width=True, hide_index=True)


st.title('Weather Forcasting')

# Initialize map
latitude = 40.0158
longitude = -105.2792
tiles = 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png'
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
folium.plugins.MousePosition().add_to(m)
folium.raster_layers.WmsTileLayer(
    url='https://opengeo.ncep.noaa.gov:443/geoserver/conus/conus_bref_qcd/ows?SERVICE=WMS&',
    layers='conus_bref_qcd',
    version='1.3.0',
    fmt='image/png',
    transparent=True,
).add_to(m)
folium.LayerControl().add_to(m)

# Call to render Folium map in Streamlit
c1, c2 = st.columns([0.3, 0.7], gap='small')
with c1:
    # Draw map
    st_data = st_folium(
        m,
        use_container_width=True,
        returned_objects=["last_clicked"],
    )
    if st_data['last_clicked']:
        latitude = st_data['last_clicked']['lat']
        longitude = st_data['last_clicked']['lng']
    df = fetch_forcast(latitude, longitude)
    hourly = df['hourly']
    daily = df['daily']
    add_position_to_c(c1, df)
with c2:
    fig = make_subplots(
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
    fig.add_trace(
        go.Scatter(
            x=hourly['time'], y=hourly['temperature_2m'], name='Temperature', line=dict(color='firebrick'), opacity=1, legendgroup='1',
        ),
        secondary_y=False, row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=hourly['time'], y=hourly['apparent_temperature'], name='Feels like', line=dict(color='firebrick'), opacity=0.4, legendgroup='1',
        ),
        secondary_y=False, row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=hourly['time'], y=hourly['dewpoint_2m'], name='Dewpoint', line=dict(color='forestgreen'), opacity=0.4, legendgroup='1',
        ),
        secondary_y=False, row=1, col=1,
    )
    fig.add_hline(
        y=0, row=1, col=1, opacity=0.5, line=dict(color='rgb(0,0,255)')
    )

    fig.add_trace(
        go.Scatter(
            x=hourly['time'], y=hourly['precipitation_probability'], name='Precip. %', fill='tozeroy', line_color='rgba(165,210,225,0.8)', fillcolor='rgba(165,210,225,0.8)', legendgroup='2',
        ),
        secondary_y=True, row=2, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=hourly['time'], y=moving_average(hourly['cloudcover'], 3), fill='tozeroy', line_color='rgba(0,0,0,0.1)', fillcolor='rgba(0,0,0,0.1)', name='Cloud Cover', legendgroup='2',
        ),
        secondary_y=True, row=2, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=hourly['time'], y=moving_average(hourly['surface_pressure'], 3), name='Pressure', legendgroup='2', line=dict(color='rgba(0,0,0,0.95)')
        ),
        secondary_y=False, row=2, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=hourly['time'], y=hourly['weathercode'], name='WCO', legendgroup='2',
        ),
        secondary_y=True, row=2, col=1,
    )

    fig.add_trace(
        go.Bar(
            x=hourly['time'], y=hourly['rain'], name='Rain', legendgroup='3',
        ),
        secondary_y=False, row=3, col=1,
    )
    fig.add_trace(
        go.Bar(
            x=hourly['time'], y=hourly['showers'], name='Shower', legendgroup='3',
        ),
        secondary_y=False, row=3, col=1,
    )
    fig.add_trace(
        go.Bar(
            x=hourly['time'], y=hourly['snowfall']*10, name='Snow', legendgroup='3',
        ),
        secondary_y=False, row=3, col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=hourly['time'], y=moving_average(hourly['windspeed_10m'], 3), name='Wind Speed', legendgroup='4',
        ),
        secondary_y=False, row=4, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=hourly['time'], y=moving_average(hourly['windgusts_10m'], 3), name='Wind Gusts', legendgroup='4',
        ),
        secondary_y=False, row=4, col=1,
    )
    fig.add_vline(
        x=df['current_weather']['time'], row='all', col=1, opacity=0.5, line=dict(color='rgb(100,100,100)')
    )

    for i, row in daily.iterrows():
        fig.add_vline(
            x=row["time"], row='all', col=1, opacity=0.05, line=dict(color='rgb(100,100,100)')
        )
        if i == 0:
            ss = row['sunset']
        else:
            sr = row['sunrise']
            fig.add_vrect(
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
        },
        'yaxis4': {
            'anchor': 'x2',
            'range': [0, 100],
            'side': 'right',
            'ticksuffix': df['hourly_units']['precipitation_probability'],
        },
        'yaxis5': {
            'anchor': 'x3',
            'ticksuffix': df['hourly_units']['precipitation'],
            'rangemode': 'nonnegative',
        },
        'yaxis6': {
            'anchor': 'x3',
            'side': 'right',
        },
        'yaxis7': {
            'anchor': 'x4',
            'ticksuffix': df['hourly_units']['windspeed_10m'],
            'rangemode': 'nonnegative',
        },
        'yaxis8': {
            'anchor': 'x4',
            'side': 'right',
        },
        'legend': dict(
            orientation="h",
            groupclick='toggleitem',
        ),
    }
    fig.update_layout(**layout)

    st.plotly_chart(fig, use_container_width=True)

# st.write(daily)
# st.write(df)


# with st.expander('Ensemble', expanded=False):
#     st.button("Fetch Ensemble", type="primary",key=1):
#         r = fetch_ensemble(latitude, longitude)
#         st.write(r)
