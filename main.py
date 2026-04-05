
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
    for variable in variables:
        if hasattr(daily, variable):
            getattr(daily, variable)()

    manager = mp.MeteoManager(api_url, options, daily=daily)
    r = manager.fetch()
    print("fetching historical...")
    return r


def fetch_elevation(latitude, longitude):
    api_url = mp.MeteoManager.elevation
    options = mp.OptionsElevation(latitude, longitude)
    manager = mp.MeteoManager(api_url, options)
    r = manager.fetch()
    print("fetching elevation...")
    return r


def moving_average(data, window):
    weights = np.repeat(1.0, window) / window
    return np.convolve(data, weights, mode='valid')


def make_forecast_plot(df, aq=None):
    # Subplots (forecast)

    df_hourly = df['hourly']
    df_daily = df['daily']

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

    f_fig.add_vline(
        x=df['current']['time'], row='all', col=1, opacity=0.5, line=dict(color='rgb(100,100,100)')
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
            'ticksuffix': df['hourly_units']['temperature_2m'],
            'title': 'Temperature',
        },
        'yaxis3': {
            'anchor': 'x2',
            'range': [0, 100],
            'ticksuffix': df['hourly_units']['relative_humidity_2m'],
            'title': 'Relative Humidy %',
        },
        'yaxis5': {
            'anchor': 'x3',
            'range': [0, 100],
            'ticksuffix': df['hourly_units']['precipitation_probability'],
            'title': 'Precipitation &</br></br> Cloud Cover %',
        },
        'yaxis6': {
            'anchor': 'x3',
            'rangemode': 'nonnegative',
            'ticksuffix': df['hourly_units']['surface_pressure'],
            'title': 'Pressure',
        },
        'yaxis7': {
            'anchor': 'x4',
            'ticksuffix': df['hourly_units']['precipitation'],
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
            'ticksuffix': df['hourly_units']['wind_speed_10m'],
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
    # location=[47.6943, 11.7749],  # Tegernsee
    # location=[40.0401, -105.2631],  # Boulder
    location = [33.76634, -118.16699],  # Long Beach
    zoom_start=12,
    tiles=tiles,
    attr=attr,
)

folium.LatLngPopup().add_to(m)
folium.plugins.Geocoder().add_to(m)
folium.plugins.LocateControl().add_to(m)
folium.plugins.MousePosition().add_to(m)

cont1 = st.container(height=400)
with cont1:
    st_data = st_folium(m, width='stretch', height=340)

if st_data['last_clicked'] is None:
    if 'center' in st_data:
        latitude = st_data['center']['lat']
        longitude = st_data['center']['lng']
    else:
        latitude = 33.76634  # Default Long Beach
        longitude = -118.16699
else:
    latitude = st_data['last_clicked']['lat']
    longitude = st_data['last_clicked']['lng']

col1, col2, col3, col4 = st.columns(4, vertical_alignment='center')

with col1:
    st.metric(label='Latitude', value=f"{latitude:.4f}")

with col2:
    st.metric(label='Longitude', value=f"{longitude:.4f}")

with col3:
    try:
        elevation_data = fetch_elevation(latitude, longitude)
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

tabs = ['Forecast', 'Ensemble', 'Historical']

if tabs:
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
                years_back = st.slider('Years back', min_value=1, max_value=50, value=10, step=1)

                start_month = st.slider('Start month', min_value=1, max_value=12, value=1, step=1)

                default_labels = ['Temperature Max']
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
                        hist = fetch_historical(latitude, longitude, selected_vars, years_back)
                        h_fig = make_historical_plot(hist, selected_vars, start_month)

                        st.session_state['historical'] = hist
                        st.session_state['h_fig'] = h_fig
                        st.session_state['historical_vars'] = selected_vars

                if 'historical' in st.session_state and selected_vars:
                    st.session_state['h_fig'] = make_historical_plot(st.session_state['historical'], selected_vars, start_month)

                if 'h_fig' in st.session_state:
                    st.plotly_chart(st.session_state['h_fig'], width='stretch')
