class OptionsGeocoding:
    def __init__(self, name: str, count: float = 10, format='json', language='en') -> None:

        if count < 0 or count > 100:
            raise ValueError('count must be between 0 and 100')

        self.name = name.replace(' ', '+')
        self.count = count
        self.format = format
        self.language = language
        return None

    def listify(self, response) -> list:
        out = []
        for r in response["results"]:
            out.append(
                r["name"]
                + ", "
                + r["admin1"]
                + ", "
                + r["country_code"]
            )
        return out
