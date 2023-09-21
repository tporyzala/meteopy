# %%
import folium.raster_layers
import folium.plugins
import folium
import meteopy as mp


# %
api_url = mp.MeteoManager.geocoding
options_geocoding = mp.OptionsGeocoding('boulder', count=20, format='json')
manager_geo = mp.MeteoManager(api_url, options_geocoding)

r1 = manager_geo.fetch()

latitude = r1["results"][0]["latitude"]
longitude = r1["results"][0]["longitude"]
elevation = r1["results"][0]["elevation"]
print("Latitude: {}".format(latitude), "\nLongitude: {}".format(
    longitude), "\nElevation: {}".format(elevation))

tmp = options_geocoding.listify(r1)
# %
api_url = mp.MeteoManager.forecast
options_forecast = mp.OptionsForecast(latitude, longitude, elevation)

hourly = mp.HourlyForcast()
hourly.all()

daily = mp.DailyForcast()
daily.all()


manager_forecast = mp.MeteoManager(api_url, options_forecast, hourly, daily)

r2 = manager_forecast.fetch()

# %%

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
