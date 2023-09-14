from ..utils.mytypes import *


class HourlyForcast:
    def __init__(self):
        self.params = TypedList()

    def temperature_2m(self):
        self.params.append("temperature_2m")
        return self

    def relativehumidity_2m(self):
        self.params.append("temperature_2m")
        return self

    def dewpoint_2m(self):
        self.params.append("dewpoint_2m")
        return self

    def apparent_temperature(self):
        self.params.append("apparent_temperature")
        return self

    def pressure_msl(self):
        self.params.append("pressure_msl")
        return self

    def surface_pressure(self):
        self.params.append("surface_pressure")
        return self

    def cloudcover(self):
        self.params.append("cloudcover")
        return self

    def cloudcover_low(self):
        self.params.append("cloudcover_low")
        return self

    def cloudcover_mid(self):
        self.params.append("cloudcover_mid")
        return self

    def cloudcover_high(self):
        self.params.append("cloudcover_high")
        return self

    def windspeed_10m(self):
        self.params.append("windspeed_10m")
        return self

    def windspeed_80m(self):
        self.params.append("windspeed_80m")
        return self

    def windspeed_120m(self):
        self.params.append("windspeed_120m")
        return self

    def windspeed_180m(self):
        self.params.append("windspeed_180m")
        return self

    def winddirection_10m(self):
        self.params.append("winddirection_10m")
        return self

    def winddirection_80m(self):
        self.params.append("winddirection_80m")
        return self

    def winddirection_120m(self):
        self.params.append("winddirection_120m")
        return self

    def winddirection_180m(self):
        self.params.append("winddirection_180m")
        return self

    def windgusts_10m(self):
        self.params.append("windgusts_10m")
        return self

    def shortwave_radiation(self):
        self.params.append("shortwave_radiation")
        return self

    def direct_radiation(self):
        self.params.append("direct_radiation")
        return self

    def direct_normal_irradiance(self):
        self.params.append("direct_normal_irradiance")
        return self

    def diffuse_radiation(self):
        self.params.append("diffuse_radiation")
        return self

    def vapor_pressure_deficit(self):
        self.params.append("vapor_pressure_deficit")
        return self

    def cape(self):
        self.params.append("cape")
        return self

    def evapotranspiration(self):
        self.params.append("evapotranspiration")
        return self

    def et0_fao_evapotranspiration(self):
        self.params.append("et0_fao_evapotranspiration")
        return self

    def precipitation(self):
        self.params.append("precipitation")
        return self

    def snowfall(self):
        self.params.append("snowfall")
        return self

    def precipitation_probability(self):
        self.params.append("precipitation_probability")
        return self

    def rain(self):
        self.params.append("rain")
        return self

    def showers(self):
        self.params.append("showers")
        return self

    def weathercode(self):
        self.params.append("weathercode")
        return self

    def snow_depth(self):
        self.params.append("snow_depth")
        return self

    def freezinglevel_height(self):
        self.params.append("freezinglevel_height")
        return self

    def visibility(self):
        self.params.append("visibility")
        return self

    def soil_temperature_0cm(self):
        self.params.append("soil_temperature_0cm")
        return self

    def soil_temperature_6cm(self):
        self.params.append("soil_temperature_6cm")
        return self

    def soil_temperature_18cm(self):
        self.params.append("soil_temperature_18cm")
        return self

    def soil_temperature_54cm(self):
        self.params.append("soil_temperature_54cm")
        return self

    def soil_moisture_0_1cm(self):
        self.params.append("soil_moisture_0_1cm")
        return self

    def soil_moisture_1_3cm(self):
        self.params.append("soil_moisture_1_3cm")
        return self

    def soil_moisture_3_9cm(self):
        self.params.append("soil_moisture_3_9cm")
        return self

    def soil_moisture_9_27cm(self):
        self.params.append("soil_moisture_9_27cm")
        return self

    def soil_moisture_27_81cm(self):
        self.params.append("soil_moisture_27_81cm")
        return self

    def is_day(self):
        self.params.append("is_day")
        return self
