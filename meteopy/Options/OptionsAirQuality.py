from ..utils.constants import *
from pytz import all_timezones


class OptionsAirQuality:
    def __init__(self, latitude: float, longitude: float, timeformat=iso8601, timezone=auto, past_days=2, forecast_days=7, cell_selection=land) -> None:

        if latitude < -90 or latitude > 90:
            raise ValueError('Latitude must be between -90 and 90 degrees')

        if longitude < -180 or longitude > 180:
            raise ValueError('Longitude must be between -180 and 180 degrees')

        if (timezone not in 'auto') and (timezone not in all_timezones):
            raise ValueError('Must specify a valid time zone')

        self.latitude = latitude
        self.longitude = longitude
        self.timeformat = timeformat
        self.timezone = timezone
        self.past_days = past_days
        self.forecast_days = forecast_days
        self.cell_selection = cell_selection
