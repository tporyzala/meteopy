# %%
import meteopy as mp

# %%
api_url = mp.MeteoManager.geocoding
options_geocoding = mp.OptionsGeocoding('boulder')
manager_geo = mp.MeteoManager(api_url, options_geocoding)

r1 = manager_geo.get_data()

r1

latitude = r1["results"][0]["latitude"]
longitude = r1["results"][0]["longitude"]
elevation = r1["results"][0]["elevation"]
print("Latitude: {}".format(latitude), "\nLongitude: {}".format(
    longitude), "\nElevation: {}".format(elevation))


# %%
api_url = mp.MeteoManager.forecast
options_forecast = mp.OptionsForecast(latitude, longitude, elevation)
hourly = mp.HourlyForcast()
daily = mp.DailyForcast()
hourly.temperature_2m()
hourly.windspeed_10m()
hourly.precipitation()
hourly.cloudcover()
daily.temperature_2m_max()
daily.temperature_2m_min()
daily.precipitation_sum()
daily.precipitation_hours()

manager_forecast = mp.MeteoManager(api_url, options_forecast, hourly, daily)

r2 = manager_forecast.get_data()

r2


# %%
