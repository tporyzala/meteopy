from ..utils.mytypes import *


class DailyHistorical:
    def __init__(self):
        self.params = TypedList()
        return None

    @run_all
    def weather_code(self):
        self.params.append("weather_code")
        return self

    @run_all
    def temperature_2m_max(self):
        self.params.append("temperature_2m_max")
        return self

    @run_all
    def temperature_2m_min(self):
        self.params.append("temperature_2m_min")
        return self

    @run_all
    def apparent_temperature_max(self):
        self.params.append("apparent_temperature_max")
        return self

    @run_all
    def apparent_temperature_min(self):
        self.params.append("apparent_temperature_min")
        return self

    @run_all
    def precipitation_sum(self):
        self.params.append("precipitation_sum")
        return self

    @run_all
    def rain_sum(self):
        self.params.append("rain_sum")
        return self

    @run_all
    def snowfall_sum(self):
        self.params.append("snowfall_sum")
        return self

    @run_all
    def precipitation_hours(self):
        self.params.append("precipitation_hours")
        return self

    @run_all
    def sunrise(self):
        self.params.append("sunrise")
        return self

    @run_all
    def sunset(self):
        self.params.append("sunset")
        return self

    @run_all
    def sunshine_duration(self):
        self.params.append("sunshine_duration")
        return self

    @run_all
    def daylight_duration(self):
        self.params.append("daylight_duration")
        return self

    @run_all
    def wind_speed_10m_max(self):
        self.params.append("wind_speed_10m_max")
        return self

    @run_all
    def wind_gusts_10m_max(self):
        self.params.append("wind_gusts_10m_max")
        return self

    @run_all
    def wind_direction_10m_dominant(self):
        self.params.append("wind_direction_10m_dominant")
        return self

    @run_all
    def shortwave_radiation_sum(self):
        self.params.append("shortwave_radiation_sum")
        return self

    @run_all
    def et0_fao_evapotranspiration(self):
        self.params.append("et0_fao_evapotranspiration")
        return self

    def all(self):
        for method_name in dir(self):
            attr = getattr(self, method_name)
            if getattr(attr, '_run_all', False):
                getattr(self, method_name)()
        return self
