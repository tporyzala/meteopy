from ..utils.mytypes import *


class HourlyEnsemble:
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

    # @run_all
    # def evapotranspiration(self):
    #     self.params.append("evapotranspiration")
    #     return self

    @run_all
    def et0_fao_evapotranspiration(self):
        self.params.append("et0_fao_evapotranspiration")
        return self

    @run_all
    def weathercode(self):
        self.params.append("weathercode")
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
    def rain(self):
        self.params.append("rain")
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
    def cape(self):
        self.params.append("cape")
        return self

    @run_all
    def surface_temperature(self):
        self.params.append("surface_temperature")
        return self

    @run_all
    def soil_temperature_0_to_10cm(self):
        self.params.append("soil_temperature_0_to_10cm")
        return self

    @run_all
    def soil_temperature_10_to_40cm(self):
        self.params.append("soil_temperature_10_to_40cm")
        return self

    @run_all
    def soil_temperature_40_to_100cm(self):
        self.params.append("soil_temperature_40_to_100cm")
        return self

    @run_all
    def soil_temperature_100_to_200cm(self):
        self.params.append("soil_temperature_100_to_200cm")
        return self

    @run_all
    def soil_moisture_0_to_10cm(self):
        self.params.append("soil_moisture_0_to_10cm")
        return self

    @run_all
    def soil_moisture_10_to_40cm(self):
        self.params.append("soil_moisture_10_to_40cm")
        return self

    @run_all
    def soil_moisture_40_to_100cm(self):
        self.params.append("soil_moisture_40_to_100cm")
        return self

    @run_all
    def soil_moisture_100_to_200cm(self):
        self.params.append("soil_moisture_100_to_200cm")
        return self

    def all(self):
        for method_name in dir(self):
            attr = getattr(self, method_name)
            if getattr(attr, '_run_all', False):
                getattr(self, method_name)()
        return self
