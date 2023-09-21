from ..utils.mytypes import *


class DailyForcast:
    def __init__(self):
        self.params = TypedList()
        return None

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
    def showers_sum(self):
        self.params.append("showers_sum")
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
    def precipitation_probability_max(self):
        self.params.append("precipitation_probability_max")
        return self

    @run_all
    def precipitation_probability_min(self):
        self.params.append("precipitation_probability_min")
        return self

    @run_all
    def precipitation_probability_mean(self):
        self.params.append("precipitation_probability_mean")
        return self

    @run_all
    def weathercode(self):
        self.params.append("weathercode")
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
    def windspeed_10m_max(self):
        self.params.append("windspeed_10m_max")
        return self

    @run_all
    def windgusts_10m_max(self):
        self.params.append("windgusts_10m_max")
        return self

    @run_all
    def winddirection_10m_dominant(self):
        self.params.append("winddirection_10m_dominant")
        return self

    @run_all
    def shortwave_radiation_sum(self):
        self.params.append("shortwave_radiation_sum")
        return self

    @run_all
    def et0_fao_evapotranspiration(self):
        self.params.append("et0_fao_evapotranspiration")
        return self

    @run_all
    def uv_index_max(self):
        self.params.append("uv_index_max")
        return self

    @run_all
    def uv_index_clear_sky_max(self):
        self.params.append("uv_index_clear_sky_max")
        return self

    def all(self):
        for method_name in dir(self):
            attr = getattr(self, method_name)
            if getattr(attr, '_run_all', False):
                getattr(self, method_name)()
        return self
