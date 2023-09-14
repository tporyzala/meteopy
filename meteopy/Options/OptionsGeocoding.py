class OptionsGeocoding:
    def __init__(self, name: str, count: float = 10, format='json', language='en') -> None:

        if count < 0 or count > 100:
            raise ValueError('count must be between 0 and 100')

        self.name = name.replace(' ', '+')
        self.count = count
        self.format = format
        self.language = language
