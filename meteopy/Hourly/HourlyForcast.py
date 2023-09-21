from ..utils.mytypes import *


class HourlyForcast:
    def __init__(self):
        self.params = TypedList()

    @run_all
    def temperature_2m(self):
        self.params.append("temperature_2m")
        return self

    @run_all
    def relativehumidity_2m(self):
        self.params.append("relativehumidity_2m")
        return self

    @run_all
    def dewpoint_2m(self):
        self.params.append("dewpoint_2m")
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
    def cloudcover(self):
        self.params.append("cloudcover")
        return self

    @run_all
    def cloudcover_low(self):
        self.params.append("cloudcover_low")
        return self

    @run_all
    def cloudcover_mid(self):
        self.params.append("cloudcover_mid")
        return self

    @run_all
    def cloudcover_high(self):
        self.params.append("cloudcover_high")
        return self

    @run_all
    def windspeed_10m(self):
        self.params.append("windspeed_10m")
        return self

    @run_all
    def windspeed_80m(self):
        self.params.append("windspeed_80m")
        return self

    @run_all
    def windspeed_120m(self):
        self.params.append("windspeed_120m")
        return self

    @run_all
    def windspeed_180m(self):
        self.params.append("windspeed_180m")
        return self

    @run_all
    def winddirection_10m(self):
        self.params.append("winddirection_10m")
        return self

    @run_all
    def winddirection_80m(self):
        self.params.append("winddirection_80m")
        return self

    @run_all
    def winddirection_120m(self):
        self.params.append("winddirection_120m")
        return self

    @run_all
    def winddirection_180m(self):
        self.params.append("winddirection_180m")
        return self

    @run_all
    def windgusts_10m(self):
        self.params.append("windgusts_10m")
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
    def vapor_pressure_deficit(self):
        self.params.append("vapor_pressure_deficit")
        return self

    @run_all
    def cape(self):
        self.params.append("cape")
        return self

    @run_all
    def evapotranspiration(self):
        self.params.append("evapotranspiration")
        return self

    @run_all
    def et0_fao_evapotranspiration(self):
        self.params.append("et0_fao_evapotranspiration")
        return self

    @run_all
    def precipitation(self):
        self.params.append("precipitation")
        return self

    @run_all
    def snowfall(self):
        self.params.append("snowfall")
        return self

    @run_all
    def precipitation_probability(self):
        self.params.append("precipitation_probability")
        return self

    @run_all
    def rain(self):
        self.params.append("rain")
        return self

    @run_all
    def showers(self):
        self.params.append("showers")
        return self

    @run_all
    def weathercode(self):
        self.params.append("weathercode")
        return self

    @run_all
    def snow_depth(self):
        self.params.append("snow_depth")
        return self

    @run_all
    def freezinglevel_height(self):
        self.params.append("freezinglevel_height")
        return self

    @run_all
    def visibility(self):
        self.params.append("visibility")
        return self

    @run_all
    def soil_temperature_0cm(self):
        self.params.append("soil_temperature_0cm")
        return self

    @run_all
    def soil_temperature_6cm(self):
        self.params.append("soil_temperature_6cm")
        return self

    @run_all
    def soil_temperature_18cm(self):
        self.params.append("soil_temperature_18cm")
        return self

    @run_all
    def soil_temperature_54cm(self):
        self.params.append("soil_temperature_54cm")
        return self

    @run_all
    def soil_moisture_0_1cm(self):
        self.params.append("soil_moisture_0_1cm")
        return self

    @run_all
    def soil_moisture_1_3cm(self):
        self.params.append("soil_moisture_1_3cm")
        return self

    @run_all
    def soil_moisture_3_9cm(self):
        self.params.append("soil_moisture_3_9cm")
        return self

    @run_all
    def soil_moisture_9_27cm(self):
        self.params.append("soil_moisture_9_27cm")
        return self

    @run_all
    def soil_moisture_27_81cm(self):
        self.params.append("soil_moisture_27_81cm")
        return self

    @run_all
    def is_day(self):
        self.params.append("is_day")
        return self

    def all(self):
        for method_name in dir(self):
            attr = getattr(self, method_name)
            if getattr(attr, '_run_all', False):
                getattr(self, method_name)()
        return self
