from ..utils.mytypes import *


class HourlyHistorical:
    def __init__(self):
        self.params = TypedList()

    @run_all
    def temperature_2m(self):
        self.params.append("temperature_2m")
        return self

    @run_all
    def relative_humidity_2m(self):
        self.params.append("relative_humidity_2m")
        return self

    @run_all
    def dew_point_2m(self):
        self.params.append("dew_point_2m")
        return self

    @run_all
    def apparent_temperature(self):
        self.params.append("apparent_temperature")
        return self

    @run_all
    def pressure_msl(self):
        self.params.append("pressure_msl")
        return self

    @run_all
    def surface_pressure(self):
        self.params.append("surface_pressure")
        return self

    @run_all
    def precipitation(self):
        self.params.append("precipitation")
        return self

    @run_all
    def rain(self):
        self.params.append("rain")
        return self

    @run_all
    def snowfall(self):
        self.params.append("snowfall")
        return self

    @run_all
    def cloud_cover(self):
        self.params.append("cloud_cover")
        return self

    @run_all
    def cloud_cover_low(self):
        self.params.append("cloud_cover_low")
        return self

    @run_all
    def cloud_cover_mid(self):
        self.params.append("cloud_cover_mid")
        return self

    @run_all
    def cloud_cover_high(self):
        self.params.append("cloud_cover_high")
        return self

    @run_all
    def shortwave_radiation(self):
        self.params.append("shortwave_radiation")
        return self

    @run_all
    def direct_radiation(self):
        self.params.append("direct_radiation")
        return self

    @run_all
    def direct_normal_irradiance(self):
        self.params.append("direct_normal_irradiance")
        return self

    @run_all
    def diffuse_radiation(self):
        self.params.append("diffuse_radiation")
        return self

    @run_all
    def global_tilted_irradiance(self):
        self.params.append("global_tilted_irradiance")
        return self

    @run_all
    def sunshine_duration(self):
        self.params.append("sunshine_duration")
        return self

    @run_all
    def wind_speed_10m(self):
        self.params.append("wind_speed_10m")
        return self

    @run_all
    def wind_speed_100m(self):
        self.params.append("wind_speed_100m")
        return self

    @run_all
    def wind_direction_10m(self):
        self.params.append("wind_direction_10m")
        return self

    @run_all
    def wind_direction_100m(self):
        self.params.append("wind_direction_100m")
        return self

    @run_all
    def wind_gusts_10m(self):
        self.params.append("wind_gusts_10m")
        return self

    @run_all
    def et0_fao_evapotranspiration(self):
        self.params.append("et0_fao_evapotranspiration")
        return self

    @run_all
    def weather_code(self):
        self.params.append("weather_code")
        return self

    @run_all
    def snow_depth(self):
        self.params.append("snow_depth")
        return self

    @run_all
    def vapour_pressure_deficit(self):
        self.params.append("vapour_pressure_deficit")
        return self

    @run_all
    def soil_temperature_0_to_7cm(self):
        self.params.append("soil_temperature_0_to_7cm")
        return self

    @run_all
    def soil_temperature_7_to_28cm(self):
        self.params.append("soil_temperature_7_to_28cm")
        return self

    @run_all
    def soil_temperature_28_to_100cm(self):
        self.params.append("soil_temperature_28_to_100cm")
        return self

    @run_all
    def soil_temperature_100_to_255cm(self):
        self.params.append("soil_temperature_100_to_255cm")
        return self

    @run_all
    def soil_moisture_0_to_7cm(self):
        self.params.append("soil_moisture_0_to_7cm")
        return self

    @run_all
    def soil_moisture_7_to_28cm(self):
        self.params.append("soil_moisture_7_to_28cm")
        return self

    @run_all
    def soil_moisture_28_to_100cm(self):
        self.params.append("soil_moisture_28_to_100cm")
        return self

    @run_all
    def soil_moisture_100_to_255cm(self):
        self.params.append("soil_moisture_100_to_255cm")
        return self

    def all(self):
        for method_name in dir(self):
            attr = getattr(self, method_name)
            if getattr(attr, '_run_all', False):
                getattr(self, method_name)()
        return self
