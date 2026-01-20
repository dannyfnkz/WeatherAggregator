import requests
from weather_service import WeatherServiceError


class OpenMeteoRequestError(WeatherServiceError):
    def __init__(self, error: requests.exceptions.HTTPError|requests.exceptions.RequestException):
        self.error = error
    def __repr__(self):
        return f"{self.__class__.__name__}({repr(self.error)})"

class OpenMeteoResponse:
    def __init__(self, latitude: float, longitude: float, time: str, temp_c: float, weather_code: int):
        self.latitude = latitude
        self.longitude = longitude
        self.time = time
        self.temp_c = temp_c
        self.weather_code = weather_code

    def __repr__(self):
        return (
            f"OpenMeteoResponse("
            f"latitude={self.latitude!r}, "
            f"longitude={self.longitude!r}, "
            f"time={self.time!r}, "
            f"temp_c={self.temp_c!r}, "
            f"weather_code={self.weather_code!r})"
        )

def fetch_data_open_meteo(latitude: float, longitude: float):
    OPEAN_METEO_ENDPOINT = (f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}"
                            f"&current_weather=true")
    try:
        response = requests.get(OPEAN_METEO_ENDPOINT)

        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status()

        # The response body from Lambda is a JSON string, which we load into a Python dict
        data = response.json()

       #  print("✅ API Call Successful!")
       #  print("Status Code:", response.status_code)
       #  print("Response Data (Python dict):")
       #  # Pretty print the dictionary for readability
       # # print(json.dumps(data, indent=4))

        latitude = data.get("latitude", None)
        longitude = data.get("longitude", None)

        current_weather_dict = data.get("current_weather", {})
        time = current_weather_dict.get("time", None)
        temperature_c = current_weather_dict.get("temperature", None)
        weather_code = current_weather_dict.get("weathercode", None)

        return OpenMeteoResponse(latitude, longitude, time, temperature_c, weather_code)

    except (requests.exceptions.HTTPError, requests.exceptions.RequestException) as err:
       raise OpenMeteoRequestError(err)

# fetch_data_open_meteo(7.0, 15.5)