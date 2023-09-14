
class OptionsElevation:
    def __init__(self, latitude: float, longitude: float) -> None:
        if latitude < -90 or latitude > 90:
            raise ValueError('Latitude must be between -90 and 90 degrees')

        if longitude < -180 or longitude > 180:
            raise ValueError('Longitude must be between -180 and 180 degrees')

        self.latitude = latitude
        self.longitude = longitude
