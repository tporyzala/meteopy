from ..utils.constants import *
from pytz import all_timezones


class OptionsEnsemble:
    def __init__(self, latitude: float, longitude: float, temperature_unit=celsius, windspeed_unit=kmh, precipitation_unit=mm, timeformat=iso8601, timezone=auto, past_days=2, forecast_days=7, models=gfs_seamless, cell_selection=land) -> None:

        if latitude < -90 or latitude > 90:
            raise ValueError('Latitude must be between -90 and 90 degrees')

        if longitude < -180 or longitude > 180:
            raise ValueError('Longitude must be between -180 and 180 degrees')

        if (timezone not in 'auto') and (timezone not in all_timezones):
            raise ValueError('Must specify a valid time zone')

        self.latitude = latitude
        self.longitude = longitude
        # self.elevation = elevation
        self.temperature_unit = temperature_unit
        self.windspeed_unit = windspeed_unit
        self.precipitation_unit = precipitation_unit
        self.timeformat = timeformat
        self.timezone = timezone
        self.past_days = past_days
        self.forecast_days = forecast_days
        self.models = models
        self.cell_selection = cell_selection
