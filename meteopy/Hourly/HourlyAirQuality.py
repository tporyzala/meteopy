from ..utils.mytypes import *


class HourlyAirQuality:
    def __init__(self):
        self.params = TypedList()

    @run_all
    def pm10(self):
        self.params.append("pm10")
        return self

    @run_all
    def pm2_5(self):
        self.params.append("pm2_5")
        return self

    @run_all
    def carbon_monoxide(self):
        self.params.append("carbon_monoxide")
        return self

    @run_all
    def nitrogen_dioxide(self):
        self.params.append("nitrogen_dioxide")
        return self

    @run_all
    def sulphur_dioxide(self):
        self.params.append("sulphur_dioxide")
        return self

    @run_all
    def ozone(self):
        self.params.append("ozone")
        return self

    @run_all
    def ammonia(self):
        self.params.append("ammonia")
        return self

    @run_all
    def aerosol_optical_depth(self):
        self.params.append("aerosol_optical_depth")
        return self

    @run_all
    def dust(self):
        self.params.append("dust")
        return self

    @run_all
    def uv_index(self):
        self.params.append("uv_index")
        return self

    @run_all
    def uv_index_clear_sky(self):
        self.params.append("uv_index_clear_sky")
        return self

    @run_all
    def alder_pollen(self):
        self.params.append("alder_pollen")
        return self

    @run_all
    def birch_pollen(self):
        self.params.append("birch_pollen")
        return self

    @run_all
    def grass_pollen(self):
        self.params.append("grass_pollen")
        return self

    @run_all
    def mugwort_pollen(self):
        self.params.append("mugwort_pollen")
        return self

    @run_all
    def olive_pollen(self):
        self.params.append("olive_pollen")
        return self

    @run_all
    def ragweed_pollen(self):
        self.params.append("ragweed_pollen")
        return self

    @run_all
    def european_aqi(self):
        self.params.append("european_aqi")
        return self

    @run_all
    def european_aqi_pm2_5(self):
        self.params.append("european_aqi_pm2_5")
        return self

    @run_all
    def european_aqi_pm10(self):
        self.params.append("european_aqi_pm10")
        return self

    @run_all
    def european_aqi_nitrogen_dioxide(self):
        self.params.append("european_aqi_nitrogen_dioxide")
        return self

    @run_all
    def european_aqi_ozone(self):
        self.params.append("european_aqi_ozone")
        return self

    @run_all
    def european_aqi_sulphur_dioxide(self):
        self.params.append("european_aqi_sulphur_dioxide")
        return self

    @run_all
    def us_aqi(self):
        self.params.append("us_aqi")
        return self

    @run_all
    def us_aqi_pm2_5(self):
        self.params.append("us_aqi_pm2_5")
        return self

    @run_all
    def us_aqi_pm10(self):
        self.params.append("us_aqi_pm10")
        return self

    @run_all
    def us_aqi_nitrogen_dioxide(self):
        self.params.append("us_aqi_nitrogen_dioxide")
        return self

    @run_all
    def us_aqi_ozone(self):
        self.params.append("us_aqi_ozone")
        return self

    @run_all
    def us_aqi_sulphur_dioxide(self):
        self.params.append("us_aqi_sulphur_dioxide")
        return self

    @run_all
    def us_aqi_carbon_monoxide(self):
        self.params.append("us_aqi_carbon_monoxide")
        return self

    def all(self):
        for method_name in dir(self):
            attr = getattr(self, method_name)
            if getattr(attr, '_run_all', False):
                getattr(self, method_name)()
        return self
