import json
from enum import Enum

import requests
from weather_service import WeatherServiceError


class WeatherApiError(WeatherServiceError):
    pass

class WeatherApiCityNotFoundError(WeatherApiError):
    pass

class WeatherApiRequestError(WeatherApiError):
    def __init__(self, error: requests.exceptions.HTTPError|requests.exceptions.RequestException):
        self.error = error

    def __repr__(self):
        return f"{self.__class__.__name__}({repr(self.error)})"



class WeatherApiResponse:
    # class WeatherCondition(Enum):
    #     SUNNY = (1000, "Sunny")
    #     PARTIALLY_CLOUDY = (1003, "Partially Cloudy")
    #     CLOUDY = (1006, "Cloudy")
    #     OVERCAST = (1009, "Overcast")
    #     MIST = (1030, "Mist"),
    #     PATCHY_LIGHT_DRIZZLE = (1150, "Patchy Light Drizzle")
    #     LIGHT_DRIZZLE = (1153, "Light Drizzle")
    #     FREEZING_DRIZZLE = (1168, "Freezing Drizzle")
    #     HEAVY_FREEZING_DRIZZLE = (1171, "Heavy Freezing Drizzle")
    #     LIGHT_RAIN = (1183, "Light Rain")
    #     MODERATE_RAIN_AT_TIMES = (1186, "Moderate Rain at Times")
    #     MODERATE_RAIN = (1189, "Moderate Rain")
    #     HEAVY_RAIN_AT_TIMES = (1192, "Heavy rain at Times")
    #     HEAVY_RAIN = (1195, "Heavy rain")
    #     LIGHT_SNOW = (1213, "Light Snow")
    #     PATCHY_MODERATE_SNOW = (1216, "Patchy Moderate Snow")


    def __init__(self, city_name: str, country_name: str,
                 latitude: float, longitude: float, last_update_epoch: int, temp_c: float, condition_text: str,
                 condition_code: int):
        self.city_name = city_name
        self.country_name = country_name
        self.latitude = latitude
        self.longitude = longitude
        self.last_update_epoch = last_update_epoch
        self.temp_c = temp_c
        self.condition_text = condition_text
        self.condition_code = condition_code

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"city_name={self.city_name!r}, "
            f"country_name={self.country_name!r}, "
            f"latitude={self.latitude!r}, "
            f"longitude={self.longitude!r}, "
            f"temp_c={self.temp_c!r}, "
            f"condition_text={self.condition_text!r})"
        )


def fetch_data_weather_api(city_name) -> WeatherApiResponse:
    WEATHER_API_KEY = "dabfd11ef5ff4c8da5e215521253012"
    WEATHER_API_ENDPOINT = f"https://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={city_name}"
    try:
        response = requests.get(WEATHER_API_ENDPOINT)

        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status()

        # The response body from Lambda is a JSON string, which we load into a Python dict
        data = response.json()

        # print("✅ API Call Successful!")
        # print("Status Code:", response.status_code)
        # print("Response Data (Python dict):")
        # # Pretty print the dictionary for readability
        #print(json.dumps(data, indent=4))

        location_dict = data.get("location", {})
        city_name = location_dict.get("name")
        country_name = location_dict.get("country")
        latitude = location_dict.get("lat", None)
        longitude = location_dict.get("lon", None)

        current_dict = data.get("current", {})
        last_updated_epoch = current_dict.get("last_updated_epoch", None)
        temp_c = current_dict.get("temp_c", None)

        condition_dict = current_dict.get("condition", {})
        condition_text = condition_dict.get("text", None)
        condition_code = condition_dict.get("code", None)

        return WeatherApiResponse(city_name, country_name, latitude, longitude, last_updated_epoch, temp_c,
                                  condition_text, condition_code)

    except (requests.exceptions.HTTPError, requests.exceptions.RequestException) as err:
        if err.response is not None and err.response.content is not None \
            and json.loads(err.response.content.decode('utf-8')).get("error", {}).get("code", -1) == 1006:
            raise WeatherApiCityNotFoundError()
        else:
            raise WeatherApiRequestError(err)
    # except requests.exceptions.HTTPError as err:
    #     print(f"❌ HTTP Error occurred")
    #     print("Status Code:", err.response.status_code)
    #     print("Content:", err.response.content)
    # except requests.exceptions.RequestException as err:
    #     print(f"❌ An error occurred during the request: {err}")