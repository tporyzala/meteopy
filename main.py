
import base64
import os
from datetime import datetime, timedelta
from pathlib import Path

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
DEFAULT_MAP_CENTER = [33.76634, -118.16699]
DEFAULT_MAP_ZOOM = 12
SIDEBAR_GRAPHIC_PATH = Path(__file__).resolve().parent / 'assets' / 'weather-route-mark.svg'
TOOL_OPTIONS = {
    'point': 'Point Forecast',
    'route': 'Route Weather',
}
ROUTE_PATH_OPTIONS = {
    'Manual': None,
    'Driving': 'driving-car',
    'Walking': 'foot-walking',
    'Hiking': 'foot-hiking',
    'Cycling': 'cycling-regular',
}

HISTORICAL_VARIABLE_OPTIONS = {
    'Weather Code': 'weather_code',
    'Temperature Max': 'temperature_2m_max',
    'Temperature Min': 'temperature_2m_min',
    'Apparent Temperature Max': 'apparent_temperature_max',
    'Apparent Temperature Min': 'apparent_temperature_min',
    'Sunrise': 'sunrise',
    'Sunset': 'sunset',
    'Daylight Duration': 'daylight_duration',
    'Sunshine Duration': 'sunshine_duration',
    'UV Index Max': 'uv_index_max',
    'UV Index Clear Sky Max': 'uv_index_clear_sky_max',
    'Precipitation Sum': 'precipitation_sum',
    'Rain Sum': 'rain_sum',
    'Showers Sum': 'showers_sum',
    'Snowfall Sum': 'snowfall_sum',
    'Precipitation Hours': 'precipitation_hours',
    'Precipitation Probability Max': 'precipitation_probability_max',
    'Wind Speed Max': 'wind_speed_10m_max',
    'Wind Gusts Max': 'wind_gusts_10m_max',
    'Wind Direction Dominant': 'wind_direction_10m_dominant',
    'Shortwave Radiation Sum': 'shortwave_radiation_sum',
    'ET0 FAO Evapotranspiration': 'et0_fao_evapotranspiration',
}


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


def fetch_airquality(latitude, longitude):
    api_url = mp.MeteoManager.air_quality
    options = mp.OptionsAirQuality(latitude, longitude)
    hourly = mp.HourlyAirQuality().all()
    manager = mp.MeteoManager(api_url, options, hourly)
    r = manager.fetch()
    print("fetching...")
    return r


def fetch_historical(latitude, longitude, variables=None, years=40):
    today = pd.Timestamp.now('UTC').date()
    current_year = today.year
    start_date = f"{current_year - years + 1}-01-01"
    end_date = today.isoformat()

    if not variables:
        variables = ['temperature_2m_max']

    api_url = mp.MeteoManager.historical
    options = mp.OptionsHistorical(latitude, longitude, start_date, end_date)
    daily = mp.DailyHistorical()

    unsupported = [
        variable for variable in variables
        if not callable(getattr(daily, variable, None))
    ]
    if unsupported:
        raise ValueError(
            "Unsupported historical daily variable(s): "
            + ", ".join(unsupported)
        )

    for variable in variables:
        getattr(daily, variable)()

    manager = mp.MeteoManager(api_url, options, daily=daily)
    r = manager.fetch()
    print("fetching historical...")
    return r


@st.cache_data
def fetch_elevation(latitude, longitude):
    api_url = mp.MeteoManager.elevation
    options = mp.OptionsElevation(latitude, longitude)
    manager = mp.MeteoManager(api_url, options)
    r = manager.fetch()
    print("fetching elevation...")
    return r


@st.cache_data(ttl=300)
def fetch_rainviewer_frames():
    return mp.fetch_rainviewer_radar_frames()


def moving_average(data, window):
    return (
        pd.Series(data)
        .rolling(window=window, min_periods=1, center=True)
        .mean()
        .to_numpy()
    )


def route_precipitation_bins(route_hourly):
    precip_columns = ['rain', 'showers', 'snowfall']
    if route_hourly.empty or 'time' not in route_hourly.columns:
        return pd.DataFrame(columns=['time', *precip_columns])

    precip = route_hourly.copy()
    for column in precip_columns:
        if column not in precip.columns:
            precip[column] = 0.0

    precip = precip[['time', *precip_columns]].copy()
    precip['time'] = pd.to_datetime(precip['time'])
    precip = (
        precip
        .sort_values('time')
        .drop_duplicates('time', keep='last')
        .set_index('time')
    )
    bins = precip.resample('1h', label='left', closed='left').mean().dropna(how='all')
    if bins.empty:
        return pd.DataFrame(columns=['time', *precip_columns])

    bins = bins.reset_index()
    bins['time'] = bins['time'] + pd.Timedelta(minutes=30)
    return bins


def make_forecast_plot(df, aq=None):
    # Subplots (forecast)

    df_hourly = df['hourly']
    df_daily = df.get('daily', pd.DataFrame())
    hourly_units = df.get('hourly_units', {})

    f_fig = make_subplots(
        rows=6,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        specs=[[{'secondary_y': True}],
               [{'secondary_y': True}],
               [{'secondary_y': True}],
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
            x=df_hourly['time'], y=df_hourly['dew_point_2m'], name='Dewpoint', line=dict(color='forestgreen'), opacity=0.4, legendgroup='1',
        ),
        secondary_y=False, row=1, col=1,
    )

    f_fig.add_hline(
        y=0, row=1, col=1, opacity=0.5, line=dict(color='rgb(0,0,255)')
    )

    f_fig.add_trace(
        go.Scatter(
            x=df_hourly['time'], y=df_hourly['relative_humidity_2m'], name='Humidity', line=dict(color='darkblue'), opacity=0.4, legendgroup='1',
        ),
        secondary_y=False, row=2, col=1,
    )

    f_fig.add_trace(
        go.Scatter(
            x=df_hourly['time'], y=df_hourly['precipitation_probability'], name='Precip. %', fill='tozeroy', line_color='rgba(165,210,225,0.8)', fillcolor='rgba(165,210,225,0.8)', legendgroup='2',
        ),
        secondary_y=False, row=3, col=1,
    )

    f_fig.add_trace(
        go.Scatter(
            x=df_hourly['time'], y=moving_average(df_hourly['cloud_cover'], 3), fill='tozeroy', line_color='rgba(0,0,0,0.1)', fillcolor='rgba(0,0,0,0.1)', name='Cloud Cover', legendgroup='2',
        ),
        secondary_y=False, row=3, col=1,
    )

    f_fig.add_trace(
        go.Scatter(
            x=df_hourly['time'], y=moving_average(df_hourly['surface_pressure'], 3), name='Pressure', legendgroup='2', line=dict(color='rgba(0,0,0,0.95)')
        ),
        secondary_y=True, row=3, col=1,
    )

    f_fig.add_trace(
        go.Scatter(
            x=df_hourly['time'], y=df_hourly['weathercode'], name='WCO', legendgroup='2',
        ),
        secondary_y=False, row=3, col=1,
    )

    f_fig.add_trace(
        go.Bar(
            x=df_hourly['time'], y=df_hourly['rain'], name='Rain', legendgroup='3',
        ),
        secondary_y=False, row=4, col=1,
    )

    f_fig.add_trace(
        go.Bar(
            x=df_hourly['time'], y=df_hourly['showers'], name='Shower', legendgroup='3',
        ),
        secondary_y=False, row=4, col=1,
    )

    f_fig.add_trace(
        go.Bar(
            x=df_hourly['time'], y=df_hourly['snowfall']*10, name='Snow', legendgroup='3',
        ),
        secondary_y=False, row=4, col=1,
    )

    f_fig.add_trace(
        go.Scatter(
            x=df_hourly['time'], y=moving_average(df_hourly['wind_speed_10m'], 3), name='Wind Speed', legendgroup='4',
        ),
        secondary_y=False, row=5, col=1,
    )

    f_fig.add_trace(
        go.Scatter(
            x=df_hourly['time'], y=moving_average(df_hourly['wind_gusts_10m'], 3), name='Wind Gusts', legendgroup='4',
        ),
        secondary_y=False, row=5, col=1,
    )

    if aq is not None and 'hourly' in aq:
        aq_hourly = aq['hourly']
        if 'pm2_5' in aq_hourly.columns:
            f_fig.add_trace(
                go.Scatter(
                    x=aq_hourly['time'], y=aq_hourly['pm2_5'], name='PM2.5', line=dict(color='maroon'), legendgroup='5',
                ),
                secondary_y=False, row=6, col=1,
            )
        if 'pm10' in aq_hourly.columns:
            f_fig.add_trace(
                go.Scatter(
                    x=aq_hourly['time'], y=aq_hourly['pm10'], name='PM10', line=dict(color='darkorange'), legendgroup='5',
                ),
                secondary_y=False, row=6, col=1,
            )
        elif 'european_aqi' in aq_hourly.columns:
            f_fig.add_trace(
                go.Scatter(
                    x=aq_hourly['time'], y=aq_hourly['european_aqi'], name='AQI', line=dict(color='purple'), legendgroup='5',
                ),
                secondary_y=False, row=6, col=1,
            )

    current_time = df.get('current', {}).get('time')
    if current_time is not None:
        f_fig.add_vline(
            x=current_time, row='all', col=1, opacity=0.5, line=dict(color='rgb(100,100,100)')
        )

    if not df_daily.empty and {'time', 'sunrise', 'sunset'}.issubset(df_daily.columns):
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
        'hovermode': 'x',
        'hoverlabel': dict(
            bgcolor='rgba(255,255,255,0.5)',
        ),
        'legend_tracegroupgap': 90,
        'height': 1300,
        'barmode': 'stack',
        'xaxis': {
            'anchor': 'y',
            'matches': 'x2',
            'showticklabels': True,
        },
        'xaxis2': {
            'anchor': 'y3',
            'showticklabels': True,
        },
        'xaxis3': {
            'anchor': 'y5',
            'showticklabels': True,
        },
        'xaxis4': {
            'anchor': 'y7',
            'showticklabels': True,
        },
        'xaxis5': {
            'anchor': 'y9',
            'showticklabels': True,
        },
        'xaxis6': {
            'anchor': 'y11',
            'showticklabels': True,
        },
        'yaxis': {
            'anchor': 'x',
            'ticksuffix': hourly_units.get('temperature_2m', ''),
            'title': 'Temperature',
        },
        'yaxis3': {
            'anchor': 'x2',
            'range': [0, 100],
            'ticksuffix': hourly_units.get('relative_humidity_2m', ''),
            'title': 'Relative Humidy %',
        },
        'yaxis5': {
            'anchor': 'x3',
            'range': [0, 100],
            'ticksuffix': hourly_units.get('precipitation_probability', ''),
            'title': 'Precipitation &</br></br> Cloud Cover %',
        },
        'yaxis6': {
            'anchor': 'x3',
            'rangemode': 'nonnegative',
            'ticksuffix': hourly_units.get('surface_pressure', ''),
            'title': 'Pressure',
        },
        'yaxis7': {
            'anchor': 'x4',
            'ticksuffix': hourly_units.get('precipitation', hourly_units.get('rain', '')),
            'rangemode': 'nonnegative',
            'title': 'Precipitation',
        },
        'yaxis8': {
            'anchor': 'x4',
            'side': 'right',
            'showgrid': False,
            'showticklabels': False,
        },
        'yaxis9': {
            'anchor': 'x5',
            'ticksuffix': hourly_units.get('wind_speed_10m', ''),
            'rangemode': 'nonnegative',
            'title': 'Wind Speed',
        },
        'yaxis10': {
            'anchor': 'x5',
            'side': 'right',
            'showgrid': False,
            'showticklabels': False,
        },
        'yaxis11': {
            'anchor': 'x6',
            'rangemode': 'nonnegative',
            'title': 'Air Quality',
        },
        'legend': dict(
            orientation="h",
            groupclick='toggleitem',
        ),
    }
    f_fig.update_layout(**layout)
    return f_fig


def make_ensemble_plot(de, df):
    # Subplots (ensemble)

    de_hourly = de['hourly']
    df_daily = df['daily']

    e_fig = make_subplots(
        rows=6,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        specs=[[{'secondary_y': True}],
               [{'secondary_y': True}],
               [{'secondary_y': True}],
               [{'secondary_y': True}],
               [{'secondary_y': True}],
               [{'secondary_y': True}],
               ],
    )

    dat = pd.DataFrame()
    for key in de_hourly.columns.tolist():
        if key.startswith('apparent_temperature_'):
            tmp = pd.DataFrame(
                {'time': de_hourly['time'], 'dat': de_hourly[key]})
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
        if key.startswith('cloud_cover_'):
            tmp = pd.DataFrame(
                {'time': de_hourly['time'], 'dat': de_hourly[key]})
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
            tmp = pd.DataFrame(
                {'time': de_hourly['time'], 'dat': de_hourly[key]})
            dat = pd.concat([dat, tmp], ignore_index=True)
    e_fig.add_trace(
        go.Box(
            x=dat['time'], y=dat['dat'],
        ),
        secondary_y=False, row=3, col=1,
    )

    dat = pd.DataFrame()
    for key in de_hourly.columns.tolist():
        if key.startswith('wind_speed_10m_'):
            tmp = pd.DataFrame(
                {'time': de_hourly['time'], 'dat': de_hourly[key]})
            dat = pd.concat([dat, tmp], ignore_index=True)
    e_fig.add_trace(
        go.Box(
            x=dat['time'], y=dat['dat'],
        ),
        secondary_y=False, row=4, col=1,
    )

    dat = pd.DataFrame()
    for key in de_hourly.columns.tolist():
        if key.startswith('wind_gusts_10m_'):
            tmp = pd.DataFrame(
                {'time': de_hourly['time'], 'dat': de_hourly[key]})
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
            tmp = pd.DataFrame(
                {'time': de_hourly['time'], 'dat': de_hourly[key]})
            dat = pd.concat([dat, tmp], ignore_index=True)
    e_fig.add_trace(
        go.Box(
            x=dat['time'], y=dat['dat'],
        ),
        secondary_y=False, row=5, col=1,
    )

    e_fig.add_vline(
        x=df['current']['time'], row='all', col=1, opacity=0.5, line=dict(color='rgb(100,100,100)')
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
        'hovermode': 'x',
        'hoverlabel': dict(
            bgcolor='rgba(255,255,255,0.5)',
        ),
        'legend_tracegroupgap': 90,
        'height': 1300,
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
            'ticksuffix': de['hourly_units']['cloud_cover'],
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
            'ticksuffix': de['hourly_units']['wind_speed_10m'],
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
        'yaxis11': {
            'anchor': 'x6',
            'rangemode': 'nonnegative',
            'title': 'Air Quality',
        },
        'legend': dict(
            orientation="h",
            groupclick='toggleitem',
        ),
    }
    e_fig.update_layout(**layout)
    return e_fig


def make_historical_plot(historical, variables, start_month=1):
    daily = historical['daily'].copy()
    missing_variables = [
        variable for variable in variables
        if variable not in daily.columns
    ]
    if missing_variables:
        raise ValueError(
            "Historical data is missing selected variable(s): "
            + ", ".join(missing_variables)
            + ". Fetch historical weather again for the selected outputs."
        )

    daily['time'] = pd.to_datetime(daily['time'])
    daily['season'] = daily['time'].apply(lambda t: t.year if t.month >= start_month else t.year - 1)

    def season_plot_time(t):
        base = t.replace(year=2000)
        if t.month < start_month:
            base = base + pd.DateOffset(years=1)
        return base

    daily['plot_time'] = daily['time'].apply(season_plot_time)

    now = pd.Timestamp.now('UTC')
    current_season = now.year if now.month >= start_month else now.year - 1
    seasons = sorted(daily['season'].unique())
    row_count = max(1, len(variables))

    h_fig = make_subplots(
        rows=row_count,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
    )

    for row, variable in enumerate(variables, start=1):
        for season in seasons:
            year_data = daily[daily['season'] == season].sort_values('time')
            if year_data.empty:
                continue

            year_data = year_data.copy()
            if 'sum' in variable:
                year_data[variable] = year_data[variable].cumsum()

            season_label = f"{season}-{season + 1}" if start_month != 1 else str(season)
            is_current = season == current_season
            h_fig.add_trace(
                go.Scatter(
                    x=year_data['plot_time'],
                    y=year_data[variable],
                    mode='lines',
                    name=season_label,
                    line=dict(color='firebrick' if is_current else 'lightgray', width=3 if is_current else 1),
                    opacity=1.0 if is_current else 0.4,
                ),
                row=row,
                col=1,
            )

    x_start = pd.Timestamp(f"2000-{start_month:02d}-01")
    x_end = x_start + pd.DateOffset(years=1) - pd.Timedelta(days=1)

    layout = {
        'hovermode': 'x',
        'hoverlabel': dict(bgcolor='rgba(255,255,255,0.5)'),
        'legend_tracegroupgap': 90,
        'height': 400 + 250 * row_count,
        'xaxis': {
            'title': 'Day of Year',
            'range': [x_start, x_end],
            'tickformat': '%b %d',
            'showgrid': True,
        },
        'yaxis': {
            'title': variables[0].replace('_', ' ').title(),
            'ticksuffix': historical['daily_units'].get(variables[0], ''),
        },
        'legend': dict(orientation='h', groupclick='toggleitem'),
    }

    for row in range(2, row_count + 1):
        layout[f'yaxis{row}'] = {
            'title': variables[row - 1].replace('_', ' ').title(),
            'ticksuffix': historical['daily_units'].get(variables[row - 1], ''),
        }

    h_fig.update_layout(**layout)
    return h_fig


def render_header(title):
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title(title)
    with col2:
        button(username="tporyzala", floating=False, width=221)


def create_weather_map(location=None, zoom_start=DEFAULT_MAP_ZOOM, include_radar=True, include_lat_lng_popup=True):
    tiles = 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png'
    attr = 'Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)'
    weather_map = folium.Map(
        location=location or DEFAULT_MAP_CENTER,
        zoom_start=zoom_start,
        tiles=tiles,
        attr=attr,
        attribution_control=False,
    )

    if include_radar:
        try:
            radar_frames = fetch_rainviewer_frames()
            mp.RainViewerRadarAnimation(radar_frames).add_to(weather_map)
        except mp.RainViewerError as e:
            st.warning(f"Radar overlay unavailable: {e}")

    if include_lat_lng_popup:
        folium.LatLngPopup().add_to(weather_map)
    folium.plugins.Geocoder().add_to(weather_map)
    folium.plugins.LocateControl().add_to(weather_map)
    folium.plugins.MousePosition().add_to(weather_map)
    return weather_map


def render_point_forecast_tool():
    render_header('Point Weather Forecasting')

    selected_location = st.session_state.get('selected_location', DEFAULT_MAP_CENTER)
    weather_map = create_weather_map(DEFAULT_MAP_CENTER)

    cont1 = st.container(height=400)
    with cont1:
        st_data = st_folium(
            weather_map,
            width='stretch',
            height=340,
            key='weather_map',
            returned_objects=['last_clicked'],
        )
    st.caption('Map data: OpenStreetMap, SRTM, OpenTopoMap. Radar imagery: Rain Viewer.')

    if st_data.get('last_clicked') is not None:
        selected_location = [
            st_data['last_clicked']['lat'],
            st_data['last_clicked']['lng'],
        ]
        st.session_state['selected_location'] = selected_location
    else:
        selected_location = st.session_state.get('selected_location', DEFAULT_MAP_CENTER)

    selected_location = st.session_state.get('selected_location', DEFAULT_MAP_CENTER)
    latitude = selected_location[0]
    longitude = selected_location[1]

    col1, col2, col3, col4 = st.columns(4, vertical_alignment='center')

    with col1:
        st.metric(label='Latitude', value=f"{latitude:.4f}")

    with col2:
        st.metric(label='Longitude', value=f"{longitude:.4f}")

    with col3:
        try:
            elevation_data = fetch_elevation(round(latitude, 4), round(longitude, 4))
            elevation = elevation_data.get('elevation', [None])[0] if 'elevation' in elevation_data else None
            if elevation is not None:
                elevation_ft = elevation * 3.28084
                st.metric(label='Elevation', value=f"{elevation:.1f} m / {elevation_ft:.1f} ft")
        except Exception as e:
            st.metric(label='Elevation', value='Error')
            if debug:
                st.error(f"Elevation fetch error: {e}")

    with col4:
        if st.button(
            label='Fetch Forecast!',
            help='Click to get the forecast at the latitude-longitude above.',
            type='primary',
        ):
            try:
                df = fetch_forcast(latitude, longitude)
                aq = fetch_airquality(latitude, longitude)
                de = fetch_ensemble(latitude, longitude)

                f_fig = make_forecast_plot(df, aq)
                e_fig = make_ensemble_plot(de, df)

                st.session_state['df'] = df
                st.session_state['de'] = de
                st.session_state['aq'] = aq
                st.session_state['f_fig'] = f_fig
                st.session_state['e_fig'] = e_fig
            except RuntimeError as e:
                st.error(f"Forecast data could not be fetched: {e}")

    tabs = ['Forecast', 'Ensemble', 'Historical']
    tab_objs = st.tabs(tabs)
    for tab_name, tab_obj in zip(tabs, tab_objs):
        with tab_obj:
            if tab_name == 'Forecast':
                if 'f_fig' in st.session_state:
                    st.plotly_chart(st.session_state['f_fig'], width='stretch')
                else:
                    st.info('Forecast is ready after you click Fetch Forecast!')
            elif tab_name == 'Ensemble':
                if 'e_fig' in st.session_state:
                    st.plotly_chart(st.session_state['e_fig'], width='stretch')
                else:
                    st.info('Ensemble is ready after you click Fetch Forecast!')
            elif tab_name == 'Historical':
                years_back = st.slider('Years back', min_value=1, max_value=50, value=50, step=1)

                start_month = st.slider('Start month', min_value=1, max_value=12, value=1, step=1)

                default_labels = ['Temperature Max', 'Temperature Min', 'Precipitation Sum']
                if 'historical_vars' in st.session_state:
                    default_labels = [label for label, var in HISTORICAL_VARIABLE_OPTIONS.items() if var in st.session_state['historical_vars']]

                selected_labels = st.multiselect(
                    label='Historical outputs',
                    options=list(HISTORICAL_VARIABLE_OPTIONS.keys()),
                    default=default_labels,
                    key='historical_outputs',
                )

                selected_vars = [HISTORICAL_VARIABLE_OPTIONS[label] for label in selected_labels]

                if st.button(
                    label='Fetch Historical Weather',
                    help='Manual fetch for expensive historical archive data for the current location.',
                    type='secondary',
                    key='fetch_historical_button',
                ):
                    if not selected_vars:
                        st.warning('Please select at least one historical output before fetching.')
                    else:
                        try:
                            hist = fetch_historical(latitude, longitude, selected_vars, years_back)
                            h_fig = make_historical_plot(hist, selected_vars, start_month)

                            st.session_state['historical'] = hist
                            st.session_state['h_fig'] = h_fig
                            st.session_state['historical_vars'] = selected_vars
                        except (RuntimeError, ValueError) as e:
                            st.error(f"Historical data could not be fetched: {e}")

                can_plot_historical = (
                    'historical' in st.session_state
                    and selected_vars
                    and all(
                        variable in st.session_state.get('historical_vars', [])
                        for variable in selected_vars
                    )
                )

                if can_plot_historical:
                    try:
                        st.session_state['h_fig'] = make_historical_plot(st.session_state['historical'], selected_vars, start_month)
                    except ValueError as e:
                        can_plot_historical = False
                        st.session_state.pop('h_fig', None)
                        st.error(f"Historical chart could not be rendered: {e}")
                elif 'historical' in st.session_state and selected_vars:
                    st.info('Fetch historical weather to update the chart for the selected outputs.')

                if can_plot_historical and 'h_fig' in st.session_state:
                    st.plotly_chart(st.session_state['h_fig'], width='stretch')


def clear_route_results():
    for key in [
        'route_report',
        'route_fig',
        'route_units',
        'route_samples',
        'route_waypoint_schedule',
        'route_summary',
    ]:
        st.session_state.pop(key, None)


def clear_route_forecast_cache():
    clear_route_results()
    for key in [
        'route_sample_geometry',
        'route_forecasts',
        'route_forecast_signature',
        'route_geometry',
        'route_waypoint_distances_km',
        'route_path_label',
        'route_path_provider',
    ]:
        st.session_state.pop(key, None)


def clear_route_anchor_state():
    for key in list(st.session_state.keys()):
        if key.startswith('route_anchor_'):
            st.session_state.pop(key, None)


def handle_route_map_change():
    route_data = st.session_state.get('route_weather_map', {})
    clicked = route_data.get('last_clicked')
    if clicked is None:
        return

    click_token = f"{clicked['lat']:.6f},{clicked['lng']:.6f}"
    if click_token == st.session_state.get('route_last_click_token'):
        return

    st.session_state['route_last_click_token'] = click_token
    st.session_state.setdefault('route_waypoints', []).append(
        {
            'lat': clicked['lat'],
            'lng': clicked['lng'],
        }
    )
    clear_route_forecast_cache()


def route_path_provider_name(route_path_label):
    return 'Manual' if ROUTE_PATH_OPTIONS.get(route_path_label) is None else 'OpenRouteService'


def route_uses_openrouteservice(route_path_label):
    return route_path_provider_name(route_path_label) == 'OpenRouteService'


def clear_stale_route_path_cache(route_path_label):
    cached_signature = st.session_state.get('route_forecast_signature')
    if cached_signature and cached_signature.get('route_path') != route_path_label:
        clear_route_forecast_cache()


def build_route_feature_group(waypoints):
    route_features = folium.FeatureGroup(name='Route waypoints', overlay=True)
    if len(waypoints) >= 2:
        route_locations = [[point['lat'], point['lng']] for point in waypoints]
        route_geometry = st.session_state.get('route_geometry')
        route_path_label = st.session_state.get('route_path_label', 'Manual')
        has_openrouteservice_route = (
            route_geometry
            and len(route_geometry) >= 2
            and st.session_state.get('route_path_provider') == 'OpenRouteService'
            and route_uses_openrouteservice(route_path_label)
        )
        if has_openrouteservice_route:
            folium.PolyLine(
                locations=[[point['lat'], point['lng']] for point in route_geometry],
                color='firebrick',
                weight=5,
                opacity=0.9,
                tooltip=f"OpenRouteService {route_path_label} route",
            ).add_to(route_features)
            folium.PolyLine(
                locations=route_locations,
                color='#64748b',
                weight=2,
                opacity=0.45,
                dash_array='6,8',
                tooltip='Selected waypoint control line',
            ).add_to(route_features)
        else:
            folium.PolyLine(
                locations=route_locations,
                color='firebrick',
                weight=4,
                opacity=0.85,
                tooltip='Manual waypoint route',
            ).add_to(route_features)

    for index, waypoint in enumerate(waypoints, start=1):
        folium.Marker(
            location=[waypoint['lat'], waypoint['lng']],
            tooltip=f"Waypoint {index}",
            popup=f"Waypoint {index}: {waypoint['lat']:.5f}, {waypoint['lng']:.5f}",
        ).add_to(route_features)

    return route_features


def render_route_path_status(route_path_label, waypoints):
    cached_label = st.session_state.get('route_path_label')
    cached_provider = st.session_state.get('route_path_provider')
    has_route_geometry = bool(st.session_state.get('route_geometry'))

    if (
        route_uses_openrouteservice(route_path_label)
        and has_route_geometry
        and cached_label == route_path_label
        and cached_provider == 'OpenRouteService'
    ):
        st.markdown(
            f"""
            <div style="font-size:0.9rem; color:#334155; line-height:1.5;">
              <span style="display:inline-block; width:34px; border-top:5px solid firebrick; margin:0 8px 4px 0;"></span>
              OpenRouteService {route_path_label} route
              <span style="display:inline-block; width:34px; border-top:2px dashed #64748b; margin:0 8px 4px 20px;"></span>
              selected waypoint line
            </div>
            """,
            unsafe_allow_html=True,
        )
    elif route_uses_openrouteservice(route_path_label):
        st.caption(
            f"OpenRouteService {route_path_label} selected. Fetch Route Weather to draw the snapped path; "
            "until then the map shows your selected waypoint segments."
        )
    elif len(waypoints) >= 2:
        st.caption('Manual route: solid red line follows the selected waypoint segments.')
    else:
        st.caption('Add at least two waypoints to draw a route.')


def render_route_map(waypoints, route_path_label):
    route_map = create_weather_map(DEFAULT_MAP_CENTER, include_lat_lng_popup=False)

    with st.container(height=430):
        st_folium(
            route_map,
            width='stretch',
            height=370,
            key='route_weather_map',
            returned_objects=['last_clicked'],
            feature_group_to_add=build_route_feature_group(waypoints),
            on_change=handle_route_map_change,
        )
    render_route_path_status(route_path_label, waypoints)
    st.caption('Map data: OpenStreetMap, SRTM, OpenTopoMap. Radar imagery: Rain Viewer.')


def render_route_waypoint_controls(waypoints):
    col1, col2, col3, col4 = st.columns([1, 1, 1.2, 2.8])
    with col1:
        if st.button('Undo last waypoint', disabled=not waypoints, key='undo_route_waypoint'):
            st.session_state.setdefault('route_waypoints', []).pop()
            st.session_state.pop('route_last_click_token', None)
            clear_route_forecast_cache()
            st.rerun()
    with col2:
        if st.button('Clear route', disabled=not waypoints, key='clear_route'):
            st.session_state['route_waypoints'] = []
            st.session_state.pop('route_last_click_token', None)
            clear_route_anchor_state()
            clear_route_forecast_cache()
            st.rerun()
    with col3:
        if st.button('Mirror waypoints', disabled=len(waypoints) < 2, key='mirror_route_waypoints'):
            mirrored_waypoints = [
                {'lat': waypoint['lat'], 'lng': waypoint['lng']}
                for waypoint in reversed(waypoints[:-1])
            ]
            st.session_state.setdefault('route_waypoints', []).extend(mirrored_waypoints)
            st.session_state.pop('route_last_click_token', None)
            clear_route_forecast_cache()
            st.rerun()

    if waypoints:
        waypoint_table = pd.DataFrame(
            [
                {
                    'Waypoint': index,
                    'Latitude': round(waypoint['lat'], 5),
                    'Longitude': round(waypoint['lng'], 5),
                }
                for index, waypoint in enumerate(waypoints, start=1)
            ]
        )
        st.dataframe(waypoint_table, width='stretch', hide_index=True)
    else:
        st.info('Click the route map to add at least two waypoints.')


def route_start_default():
    now = pd.Timestamp.now().ceil('h')
    return now.to_pydatetime().replace(second=0, microsecond=0)


def route_end_default(waypoints, start_dt):
    duration_hours = 2.0
    if len(waypoints) >= 2:
        duration_hours = max(
            1.0,
            mp.cumulative_route_distances(waypoints)[-1] / 5.0,
        )
    return (pd.Timestamp(start_dt) + pd.Timedelta(hours=duration_hours)).to_pydatetime()


def configured_openrouteservice_api_key():
    env_key = os.environ.get('OPENROUTESERVICE_API_KEY')
    if env_key:
        return env_key

    try:
        return st.secrets.get('OPENROUTESERVICE_API_KEY')
    except Exception:
        return None


def render_route_path_controls():
    col1, col2 = st.columns([1, 2])
    with col1:
        route_path_label = st.selectbox(
            'Route path',
            options=list(ROUTE_PATH_OPTIONS.keys()),
            index=0,
            key='route_path_label_select',
            help='Manual uses straight waypoint segments. Other modes snap the route with OpenRouteService when you fetch.',
        )

    profile = ROUTE_PATH_OPTIONS[route_path_label]
    api_key = None
    with col2:
        if profile is None:
            st.caption('Manual route: weather samples follow straight lines between waypoints.')
        else:
            configured_key = configured_openrouteservice_api_key()
            if configured_key:
                api_key = configured_key
                st.caption('Using OpenRouteService API key from environment or Streamlit secrets.')
            else:
                api_key = st.text_input(
                    'OpenRouteService API key',
                    type='password',
                    key='route_openrouteservice_api_key',
                    help='Used only when Fetch Route Weather is clicked.',
                )

    return route_path_label, profile, api_key


def active_route_waypoint_distances(waypoints):
    distances = st.session_state.get('route_waypoint_distances_km')
    if distances and len(distances) == len(waypoints):
        return distances
    return None


def collect_route_anchor_times_from_state(waypoints):
    anchor_times = {}
    for index in range(1, max(1, len(waypoints) - 1)):
        if not st.session_state.get(f"route_anchor_enabled_{index}"):
            continue

        anchor_date = st.session_state.get(f"route_anchor_date_{index}")
        anchor_time = st.session_state.get(f"route_anchor_time_{index}")
        if anchor_date is not None and anchor_time is not None:
            anchor_times[index] = datetime.combine(anchor_date, anchor_time)
    return anchor_times


def render_route_timing_controls(waypoints):
    default_start = route_start_default()
    default_end = route_end_default(waypoints, default_start)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        route_start_date = st.date_input(
            'Start date',
            value=default_start.date(),
            min_value=pd.Timestamp.now().date(),
            max_value=(pd.Timestamp.now() + pd.Timedelta(days=15)).date(),
            key='route_start_date',
        )
    with col2:
        route_start_time = st.time_input(
            'Start time',
            value=default_start.time(),
            step=timedelta(minutes=15),
            key='route_start_time',
        )
    with col3:
        route_end_date = st.date_input(
            'End date',
            value=default_end.date(),
            min_value=pd.Timestamp.now().date(),
            max_value=(pd.Timestamp.now() + pd.Timedelta(days=15)).date(),
            key='route_end_date',
        )
    with col4:
        route_end_time = st.time_input(
            'End time',
            value=default_end.time().replace(second=0, microsecond=0),
            step=timedelta(minutes=15),
            key='route_end_time',
        )

    col1, col2 = st.columns([1, 3])
    with col1:
        spacing_km = st.number_input(
            'Sample spacing (km)',
            min_value=0.1,
            max_value=50.0,
            value=10.0,
            step=0.1,
            format='%.1f',
            key='route_spacing_km',
        )
    with col2:
        max_samples = st.slider(
            'Max sample points',
            min_value=5,
            max_value=80,
            value=40,
            step=5,
            key='route_max_samples',
        )
        st.caption('Caps automatic spacing samples. Selected waypoints are always included in addition to this cap.')

    start_dt = datetime.combine(route_start_date, route_start_time)
    end_dt = datetime.combine(route_end_date, route_end_time)

    anchor_times = collect_route_anchor_times_from_state(waypoints)
    waypoint_distances = active_route_waypoint_distances(waypoints)
    if len(waypoints) >= 3:
        try:
            estimated_etas = mp.calculate_route_waypoint_times(
                waypoints,
                start_dt,
                end_dt,
                anchor_times,
                waypoint_distances=waypoint_distances,
            )
        except ValueError:
            estimated_etas = [pd.Timestamp(start_dt)] * len(waypoints)

        with st.expander('Waypoint arrival anchors', expanded=True):
            st.caption('Start and end use the route times above. Add optional times only for interior waypoints where your pace changes.')
            for index, waypoint in enumerate(waypoints):
                if index == 0:
                    st.write(f"Waypoint 1: {start_dt:%Y-%m-%d %H:%M}")
                    continue
                if index == len(waypoints) - 1:
                    st.write(f"Waypoint {index + 1}: {end_dt:%Y-%m-%d %H:%M}")
                    continue

                default_eta = estimated_etas[index].to_pydatetime()
                cols = st.columns([1.2, 1, 1])
                with cols[0]:
                    enabled = st.checkbox(
                        f"Waypoint {index + 1}",
                        key=f"route_anchor_enabled_{index}",
                    )
                with cols[1]:
                    if enabled:
                        anchor_date = st.date_input(
                            f"Date {index + 1}",
                            value=default_eta.date(),
                            key=f"route_anchor_date_{index}",
                        )
                    else:
                        anchor_date = default_eta.date()
                        st.text_input(
                            f"Date {index + 1}",
                            value=anchor_date.isoformat(),
                            disabled=True,
                        )
                with cols[2]:
                    if enabled:
                        anchor_time = st.time_input(
                            f"Time {index + 1}",
                            value=default_eta.time().replace(second=0, microsecond=0),
                            step=timedelta(minutes=15),
                            key=f"route_anchor_time_{index}",
                        )
                    else:
                        anchor_time = default_eta.time().replace(second=0, microsecond=0)
                        st.text_input(
                            f"Time {index + 1}",
                            value=anchor_time.strftime('%H:%M'),
                            disabled=True,
                        )
                if enabled:
                    anchor_times[index] = datetime.combine(anchor_date, anchor_time)

    elif len(waypoints) >= 2:
        st.caption('Waypoint 1 uses the start time and the final waypoint uses the end time.')

    return start_dt, end_dt, spacing_km, max_samples, anchor_times


def make_route_plot(report, units):
    route_hourly = report.copy()
    precip_bins = route_precipitation_bins(route_hourly)
    if 'is_route_sample' in route_hourly.columns:
        route_samples = route_hourly[route_hourly['is_route_sample'].astype(bool)]
    else:
        route_samples = route_hourly.iloc[0:0]

    route_fig = make_subplots(
        rows=6,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        specs=[
            [{'secondary_y': True}],
            [{'secondary_y': True}],
            [{'secondary_y': True}],
            [{'secondary_y': True}],
            [{'secondary_y': True}],
            [{'secondary_y': True}],
        ],
    )

    if 'elevation' in route_hourly.columns and route_hourly['elevation'].notna().any():
        route_fig.add_trace(
            go.Scatter(
                x=route_hourly['time'],
                y=route_hourly['elevation'],
                name='Elevation',
                fill='tozeroy',
                line=dict(color='saddlebrown', width=2),
                fillcolor='rgba(139, 92, 45, 0.22)',
                customdata=route_hourly[['distance_km']].to_numpy(),
                hovertemplate='Elevation %{y:.0f} m<br>Distance %{customdata[0]:.2f} km<br>%{x}<extra></extra>',
                legendgroup='profile',
            ),
            secondary_y=False,
            row=1,
            col=1,
        )

    route_fig.add_trace(
        go.Scatter(
            x=route_hourly['time'], y=route_hourly['temperature_2m'], name='Temperature', line=dict(color='firebrick'), opacity=1, legendgroup='1',
        ),
        secondary_y=False, row=2, col=1,
    )
    route_fig.add_trace(
        go.Scatter(
            x=route_hourly['time'], y=route_hourly['apparent_temperature'], name='Feels like', line=dict(color='firebrick'), opacity=0.4, legendgroup='1',
        ),
        secondary_y=False, row=2, col=1,
    )
    route_fig.add_trace(
        go.Scatter(
            x=route_hourly['time'], y=route_hourly['dew_point_2m'], name='Dewpoint', line=dict(color='forestgreen'), opacity=0.4, legendgroup='1',
        ),
        secondary_y=False, row=2, col=1,
    )
    route_fig.add_hline(
        y=0, row=2, col=1, opacity=0.5, line=dict(color='rgb(0,0,255)')
    )

    route_fig.add_trace(
        go.Scatter(
            x=route_hourly['time'], y=route_hourly['relative_humidity_2m'], name='Humidity', line=dict(color='darkblue'), opacity=0.4, legendgroup='1',
        ),
        secondary_y=False, row=3, col=1,
    )

    route_fig.add_trace(
        go.Scatter(
            x=route_hourly['time'], y=route_hourly['precipitation_probability'], name='Precip. %', fill='tozeroy', line_color='rgba(165,210,225,0.8)', fillcolor='rgba(165,210,225,0.8)', legendgroup='2',
        ),
        secondary_y=False, row=4, col=1,
    )
    route_fig.add_trace(
        go.Scatter(
            x=route_hourly['time'], y=moving_average(route_hourly['cloud_cover'], 3), fill='tozeroy', line_color='rgba(0,0,0,0.1)', fillcolor='rgba(0,0,0,0.1)', name='Cloud Cover', legendgroup='2',
        ),
        secondary_y=False, row=4, col=1,
    )
    route_fig.add_trace(
        go.Scatter(
            x=route_hourly['time'], y=moving_average(route_hourly['surface_pressure'], 3), name='Pressure', legendgroup='2', line=dict(color='rgba(0,0,0,0.95)')
        ),
        secondary_y=True, row=4, col=1,
    )
    route_fig.add_trace(
        go.Scatter(
            x=route_hourly['time'], y=route_hourly['weathercode'], name='WCO', legendgroup='2',
        ),
        secondary_y=False, row=4, col=1,
    )

    route_fig.add_trace(
        go.Bar(
            x=precip_bins['time'],
            y=precip_bins['rain'],
            width=60 * 60 * 1000,
            name='Rain',
            legendgroup='3',
            hovertemplate='Rain %{y:.2f} mm<br>1h bin centered %{x}<extra></extra>',
        ),
        secondary_y=False, row=5, col=1,
    )
    route_fig.add_trace(
        go.Bar(
            x=precip_bins['time'],
            y=precip_bins['showers'],
            width=60 * 60 * 1000,
            name='Shower',
            legendgroup='3',
            hovertemplate='Showers %{y:.2f} mm<br>1h bin centered %{x}<extra></extra>',
        ),
        secondary_y=False, row=5, col=1,
    )
    route_fig.add_trace(
        go.Bar(
            x=precip_bins['time'],
            y=precip_bins['snowfall'] * 10,
            width=60 * 60 * 1000,
            name='Snow',
            legendgroup='3',
            hovertemplate='Snow %{y:.2f} mm water equiv. x10<br>1h bin centered %{x}<extra></extra>',
        ),
        secondary_y=False, row=5, col=1,
    )

    route_fig.add_trace(
        go.Scatter(
            x=route_hourly['time'], y=moving_average(route_hourly['wind_speed_10m'], 3), name='Wind Speed', legendgroup='4', line=dict(color='royalblue'),
        ),
        secondary_y=False, row=6, col=1,
    )
    route_fig.add_trace(
        go.Scatter(
            x=route_hourly['time'], y=moving_average(route_hourly['wind_gusts_10m'], 3), name='Wind Gusts', legendgroup='4', line=dict(color='darkorange'),
        ),
        secondary_y=False, row=6, col=1,
    )

    marker_specs = [
        ('elevation', 1, False, 'Elevation sample', 'saddlebrown'),
        ('temperature_2m', 2, False, 'Temperature sample', 'firebrick'),
        ('apparent_temperature', 2, False, 'Feels-like sample', 'rgba(178,34,34,0.55)'),
        ('dew_point_2m', 2, False, 'Dewpoint sample', 'forestgreen'),
        ('relative_humidity_2m', 3, False, 'Humidity sample', 'darkblue'),
        ('precipitation_probability', 4, False, 'Precip. % sample', 'rgba(74,144,164,0.9)'),
        ('cloud_cover', 4, False, 'Cloud sample', 'rgba(80,80,80,0.65)'),
        ('surface_pressure', 4, True, 'Pressure sample', 'black'),
        ('wind_speed_10m', 6, False, 'Wind sample', 'royalblue'),
        ('wind_gusts_10m', 6, False, 'Gust sample', 'darkorange'),
    ]
    for column, row, secondary_y, name, color in marker_specs:
        if column not in route_samples.columns or route_samples.empty:
            continue
        route_fig.add_trace(
            go.Scatter(
                x=route_samples['time'],
                y=route_samples[column],
                mode='markers',
                marker=dict(color=color, size=4, symbol='circle', opacity=0.75),
                name=name,
                legendgroup='route_samples',
                showlegend=False,
                hovertemplate=f'{name}<br>%{{x}}<br>%{{y}}<extra></extra>',
            ),
            secondary_y=secondary_y,
            row=row,
            col=1,
        )
    route_fig.add_vline(
        x=route_hourly['time'].iloc[0], row='all', col=1, opacity=0.5, line=dict(color='rgb(100,100,100)')
    )
    route_fig.update_layout(
        hovermode='x',
        hoverlabel=dict(bgcolor='rgba(255,255,255,0.5)'),
        legend_tracegroupgap=90,
        height=1450,
        barmode='stack',
        legend=dict(orientation='h', groupclick='toggleitem'),
    )
    for row in range(1, 7):
        route_fig.update_xaxes(showticklabels=True, row=row, col=1)
    route_fig.update_yaxes(title_text='Elevation', ticksuffix='m', row=1, col=1, secondary_y=False)
    route_fig.update_yaxes(title_text='Temperature', ticksuffix=units.get('temperature_2m', ''), row=2, col=1, secondary_y=False)
    route_fig.update_yaxes(title_text='Relative Humidity %', ticksuffix=units.get('relative_humidity_2m', ''), range=[0, 100], row=3, col=1, secondary_y=False)
    route_fig.update_yaxes(title_text='Precipitation &</br></br> Cloud Cover %', ticksuffix=units.get('precipitation_probability', ''), range=[0, 100], row=4, col=1, secondary_y=False)
    route_fig.update_yaxes(title_text='Pressure', ticksuffix=units.get('surface_pressure', ''), rangemode='nonnegative', row=4, col=1, secondary_y=True)
    route_fig.update_yaxes(title_text='Precipitation', ticksuffix=units.get('precipitation', units.get('rain', '')), rangemode='nonnegative', row=5, col=1, secondary_y=False)
    route_fig.update_yaxes(showgrid=False, showticklabels=False, row=5, col=1, secondary_y=True)
    route_fig.update_yaxes(title_text='Wind Speed', ticksuffix=units.get('wind_speed_10m', ''), rangemode='nonnegative', row=6, col=1, secondary_y=False)
    route_fig.update_yaxes(showgrid=False, showticklabels=False, row=6, col=1, secondary_y=True)
    return route_fig


def format_route_report_table(report):
    table = report.copy()
    table['time'] = pd.to_datetime(table['time']).dt.strftime('%Y-%m-%d %H:%M:%S')
    columns = [
        'time',
        'is_route_sample',
        'waypoint',
        'distance_km',
        'elevation',
        'lat',
        'lng',
        'temperature_2m',
        'apparent_temperature',
        'precipitation_probability',
        'rain',
        'showers',
        'snowfall',
        'wind_speed_10m',
        'wind_gusts_10m',
        'uv_index',
        'visibility',
        'hazards',
    ]
    table = table[[column for column in columns if column in table.columns]]
    if 'is_route_sample' in table.columns:
        table['is_route_sample'] = table['is_route_sample'].map(lambda value: 'Yes' if value else '')
    for column in table.select_dtypes(include='number').columns:
        table[column] = table[column].round(2)
    return table.rename(
        columns={
            'time': 'Time',
            'is_route_sample': 'Sample',
            'waypoint': 'Waypoint',
            'distance_km': 'Distance km',
            'elevation': 'Elevation m',
            'lat': 'Latitude',
            'lng': 'Longitude',
            'temperature_2m': 'Temp C',
            'apparent_temperature': 'Feels Like C',
            'precipitation_probability': 'Precip %',
            'rain': 'Rain mm',
            'showers': 'Showers mm',
            'snowfall': 'Snowfall cm',
            'wind_speed_10m': 'Wind km/h',
            'wind_gusts_10m': 'Gusts km/h',
            'uv_index': 'UV',
            'visibility': 'Visibility m',
            'hazards': 'Hazards',
        }
    )


def route_forecast_signature(waypoints, spacing_km, max_samples, route_path_label):
    return {
        'waypoints': [
            (round(waypoint['lat'], 6), round(waypoint['lng'], 6))
            for waypoint in waypoints
        ],
        'spacing_km': float(spacing_km),
        'max_samples': int(max_samples),
        'route_path': route_path_label,
    }


def resolve_route_path(waypoints, route_path_label, route_profile, openrouteservice_api_key):
    if route_profile is None:
        return {
            'geometry': [
                {'lat': waypoint['lat'], 'lng': waypoint['lng']}
                for waypoint in waypoints
            ],
            'waypoint_distances_km': mp.cumulative_route_distances(waypoints),
            'distance_km': mp.cumulative_route_distances(waypoints)[-1],
            'duration_seconds': None,
        }

    if not openrouteservice_api_key:
        raise ValueError('OpenRouteService API key is required for snapped route paths.')

    return mp.fetch_openrouteservice_route(
        waypoints,
        route_profile,
        openrouteservice_api_key,
    )


def store_route_report_from_cache(waypoints, start_dt, end_dt, anchor_times):
    if len(waypoints) < 2:
        raise ValueError('Add at least two route waypoints before building a route report.')

    if 'route_sample_geometry' not in st.session_state or 'route_forecasts' not in st.session_state:
        raise ValueError('Fetch route weather before adjusting route timing.')

    waypoint_distances = st.session_state.get('route_waypoint_distances_km')
    waypoint_etas = mp.calculate_route_waypoint_times(
        waypoints,
        start_dt,
        end_dt,
        anchor_times,
        waypoint_distances=waypoint_distances,
    )
    route_samples = mp.attach_route_sample_etas(
        st.session_state['route_sample_geometry'],
        waypoints,
        waypoint_etas,
        waypoint_distances=waypoint_distances,
    )
    report, units = mp.build_route_hourly_report(
        route_samples,
        st.session_state['route_forecasts'],
    )
    route_fig = make_route_plot(report, units)

    total_distance = waypoint_distances[-1] if waypoint_distances else mp.cumulative_route_distances(waypoints)[-1]
    route_duration = waypoint_etas[-1] - pd.Timestamp(start_dt)

    st.session_state['route_report'] = report
    st.session_state['route_units'] = units
    st.session_state['route_samples'] = route_samples
    st.session_state['route_fig'] = route_fig
    st.session_state['route_waypoint_schedule'] = pd.DataFrame(
        {
            'Waypoint': list(range(1, len(waypoints) + 1)),
            'ETA': waypoint_etas,
            'Distance km': waypoint_distances if waypoint_distances else mp.cumulative_route_distances(waypoints),
            'Latitude': [waypoint['lat'] for waypoint in waypoints],
            'Longitude': [waypoint['lng'] for waypoint in waypoints],
        }
    )
    st.session_state['route_summary'] = {
        'distance_km': total_distance,
        'duration_hours': route_duration.total_seconds() / 3600,
        'sample_count': len(route_samples),
        'finish_time': waypoint_etas[-1],
        'path_label': st.session_state.get('route_path_label', 'Manual'),
        'path_provider': st.session_state.get('route_path_provider', 'Manual'),
    }


def fetch_and_store_route_weather(
    waypoints,
    start_dt,
    end_dt,
    spacing_km,
    max_samples,
    anchor_times,
    route_path_label,
    route_profile,
    openrouteservice_api_key,
):
    if len(waypoints) < 2:
        raise ValueError('Add at least two route waypoints before fetching route weather.')

    if pd.Timestamp(start_dt) < pd.Timestamp.now() - pd.Timedelta(hours=1):
        raise ValueError('Route start time must be in the current forecast window.')

    route_path = resolve_route_path(
        waypoints,
        route_path_label,
        route_profile,
        openrouteservice_api_key,
    )
    route_geometry = route_path['geometry']
    waypoint_distances = route_path['waypoint_distances_km']

    waypoint_etas = mp.calculate_route_waypoint_times(
        waypoints,
        start_dt,
        end_dt,
        anchor_times,
        waypoint_distances=waypoint_distances,
    )
    route_sample_geometry = mp.sample_route(
        route_geometry,
        spacing_km=spacing_km,
        max_samples=max_samples,
        forced_points=waypoints,
        forced_distances=waypoint_distances,
    )
    forecast_days = mp.route_forecast_days_needed(waypoint_etas[-1])
    forecasts = mp.fetch_route_forecasts(route_sample_geometry, forecast_days=forecast_days)

    st.session_state['route_sample_geometry'] = route_sample_geometry
    st.session_state['route_forecasts'] = forecasts
    st.session_state['route_geometry'] = route_geometry
    st.session_state['route_waypoint_distances_km'] = waypoint_distances
    st.session_state['route_path_label'] = route_path_label
    st.session_state['route_path_provider'] = route_path_provider_name(route_path_label)
    st.session_state['route_forecast_signature'] = route_forecast_signature(
        waypoints,
        spacing_km,
        max_samples,
        route_path_label,
    )
    store_route_report_from_cache(waypoints, start_dt, end_dt, anchor_times)


def sync_cached_route_report(waypoints, start_dt, end_dt, spacing_km, max_samples, anchor_times, route_path_label):
    if 'route_forecasts' not in st.session_state:
        return

    current_signature = route_forecast_signature(waypoints, spacing_km, max_samples, route_path_label)
    if st.session_state.get('route_forecast_signature') != current_signature:
        clear_route_forecast_cache()
        st.info('Route geometry or sample settings changed. Fetch Route Weather again for this route.')
        return

    try:
        store_route_report_from_cache(waypoints, start_dt, end_dt, anchor_times)
    except (ValueError, mp.RouteWeatherError) as e:
        clear_route_results()
        st.warning(f"Route timing could not be re-interpolated: {e}")


def render_route_results():
    if 'route_report' not in st.session_state:
        return

    summary = st.session_state['route_summary']
    path_provider = summary.get('path_provider', 'Manual')
    path_label = summary.get('path_label', 'Manual')
    if path_provider == 'OpenRouteService':
        st.caption(f"Route path: OpenRouteService {path_label}. Weather samples follow the red snapped route on the map.")
    else:
        st.caption('Route path: Manual waypoint segments.')

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric('Distance', f"{summary['distance_km']:.1f} km")
    with col2:
        st.metric('Duration', f"{summary['duration_hours']:.1f} hr")
    with col3:
        st.metric('Samples', summary['sample_count'])
    with col4:
        st.metric('Finish', pd.Timestamp(summary['finish_time']).strftime('%Y-%m-%d %H:%M'))

    st.plotly_chart(st.session_state['route_fig'], width='stretch')

    if 'route_waypoint_schedule' in st.session_state:
        waypoint_schedule = st.session_state['route_waypoint_schedule'].copy()
        waypoint_schedule['ETA'] = pd.to_datetime(waypoint_schedule['ETA']).dt.strftime('%Y-%m-%d %H:%M')
        waypoint_schedule[['Latitude', 'Longitude']] = waypoint_schedule[['Latitude', 'Longitude']].round(5)
        if 'Distance km' in waypoint_schedule.columns:
            waypoint_schedule['Distance km'] = waypoint_schedule['Distance km'].round(2)
        st.dataframe(waypoint_schedule, width='stretch', hide_index=True)

    st.dataframe(
        format_route_report_table(st.session_state['route_report']),
        width='stretch',
        hide_index=True,
    )


def render_route_weather_tool():
    render_header('Route Weather')

    st.session_state.setdefault('route_waypoints', [])
    waypoints = st.session_state['route_waypoints']

    route_path_label, route_profile, openrouteservice_api_key = render_route_path_controls()
    clear_stale_route_path_cache(route_path_label)
    render_route_map(waypoints, route_path_label)
    render_route_waypoint_controls(waypoints)
    start_dt, end_dt, spacing_km, max_samples, anchor_times = render_route_timing_controls(waypoints)

    if st.button(
        'Fetch Route Weather',
        type='primary',
        disabled=len(waypoints) < 2,
        key='fetch_route_weather',
    ):
        try:
            clear_route_results()
            fetch_and_store_route_weather(
                waypoints,
                start_dt,
                end_dt,
                spacing_km,
                max_samples,
                anchor_times,
                route_path_label,
                route_profile,
                openrouteservice_api_key,
            )
            st.rerun()
        except (RuntimeError, ValueError, mp.RouteWeatherError) as e:
            clear_route_results()
            st.error(f"Route weather could not be fetched: {e}")
    else:
        sync_cached_route_report(
            waypoints,
            start_dt,
            end_dt,
            spacing_km,
            max_samples,
            anchor_times,
            route_path_label,
        )

    render_route_results()


def sidebar_graphic_data_uri():
    try:
        encoded = base64.b64encode(SIDEBAR_GRAPHIC_PATH.read_bytes()).decode('ascii')
    except OSError:
        return ''
    return f"data:image/svg+xml;base64,{encoded}"


def selected_tool_key():
    tool_key = st.query_params.get('tool', 'point')
    if isinstance(tool_key, list):
        tool_key = tool_key[0] if tool_key else 'point'
    if tool_key not in TOOL_OPTIONS:
        return 'point'
    return tool_key


def render_sidebar_navigation(active_tool_key):
    graphic_uri = sidebar_graphic_data_uri()
    graphic_html = (
        f'<img class="tool-sidebar-graphic" src="{graphic_uri}" alt="" />'
        if graphic_uri
        else '<div class="tool-sidebar-graphic-fallback"></div>'
    )
    point_active = 'active' if active_tool_key == 'point' else ''
    route_active = 'active' if active_tool_key == 'route' else ''

    st.sidebar.markdown(
        f"""
        <style>
            [data-testid="stSidebar"] .tool-sidebar-brand {{
                display: flex;
                align-items: center;
                gap: 0.7rem;
                margin: 0.2rem 0 1.2rem;
            }}
            [data-testid="stSidebar"] .tool-sidebar-graphic {{
                width: 86px;
                height: auto;
                border-radius: 16px;
                box-shadow: 0 12px 30px rgba(15, 23, 42, 0.12);
            }}
            [data-testid="stSidebar"] .tool-sidebar-graphic-fallback {{
                width: 86px;
                height: 58px;
                border-radius: 16px;
                background: linear-gradient(135deg, #e0f2fe, #fef3c7);
                box-shadow: 0 12px 30px rgba(15, 23, 42, 0.12);
            }}
            [data-testid="stSidebar"] .tool-sidebar-title {{
                color: #0f172a;
                font-size: 1.05rem;
                font-weight: 700;
                line-height: 1.15;
            }}
            [data-testid="stSidebar"] .tool-sidebar-nav {{
                display: flex;
                flex-direction: column;
                gap: 0.15rem;
                margin-top: 0.35rem;
            }}
            [data-testid="stSidebar"] .tool-sidebar-link {{
                color: #334155;
                display: block;
                font-size: 1rem;
                font-weight: 600;
                line-height: 1.2;
                padding: 0.62rem 0.7rem;
                border-radius: 8px;
                text-decoration: none;
                border-left: 3px solid transparent;
            }}
            [data-testid="stSidebar"] .tool-sidebar-link:hover {{
                color: #0f172a;
                background: rgba(14, 165, 233, 0.09);
                text-decoration: none;
            }}
            [data-testid="stSidebar"] .tool-sidebar-link.active {{
                color: #0f172a;
                background: rgba(15, 23, 42, 0.06);
                border-left-color: #ef4444;
            }}
        </style>
        <div class="tool-sidebar-brand">
            {graphic_html}
            <div class="tool-sidebar-title">Meteopy</div>
        </div>
        <nav class="tool-sidebar-nav" aria-label="Weather tools">
            <a class="tool-sidebar-link {point_active}" href="?tool=point" target="_self">Point Forecast</a>
            <a class="tool-sidebar-link {route_active}" href="?tool=route" target="_self">Route Weather</a>
        </nav>
        """,
        unsafe_allow_html=True,
    )


tool_key = selected_tool_key()
render_sidebar_navigation(tool_key)

if tool_key == 'route':
    render_route_weather_tool()
else:
    render_point_forecast_tool()
