import csv
import json
from dataclasses import replace
from datetime import datetime, timezone
import time
from enum import Enum
from typing import Any, List, Optional
import open_meteo
import utils
from open_meteo import OpenMeteoRequestError, OpenMeteoResponse
import weather_api
from weather_api import WeatherApiRequestError, WeatherApiCityNotFoundError, WeatherApiResponse
from weather_service import WeatherServiceError


class WeatherCondition(Enum):
    CLEAR = (0, "Clear")
    PARTIALLY_CLOUDY = (1, "Partially Cloudy")
    CLOUDY = (2, "Cloudy")
    DRIZZLE = (3, "Drizzle")
    LIGHT_RAIN = (4, "Light Rain")
    MODERATE_RAIN = (5, "Moderate Rain")
    HEAVY_RAIN = (6, "Heavy Rain")
    LIGHT_SNOW = (7, "Light Snow")
    MODERATE_SNOW = (8, "Moderate Snow")
    HEAVY_SNOW = (9, "Heavy Snow")
    OVERCAST = (10, "Overcast")
    MIST = (11, "Mist")
    FOG = (12, "Fog")
    UNRECOGNIZED = (13, "Unrecognized")


class CityWeatherData:
    def __init__(self, latitude: float, longitude: float, last_update_epoch: int, temp_c: float,
                 weather_condition: WeatherCondition|List[WeatherCondition]):
        self.latitude = latitude
        self.longitude = longitude
        self.last_update_epoch = last_update_epoch
        self.temp_c = temp_c
        self.weather_condition = weather_condition \
            if type(weather_condition) is list else [weather_condition]

    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"latitude={self.latitude!r}, "
            f"longitude={self.longitude!r}, "
            f"last_update_epoch={self.last_update_epoch!r}, "
            f"temp_c={self.temp_c!r}, "
            f"weather_condition={self.weather_condition!r})"
        )

    def to_json(self):
        return json.dumps({
            "latitude": self.latitude,
            "longitude": self.longitude,
            #"last_update": datetime.fromtimestamp(self.last_update_epoch, tz=timezone.utc).isoformat(),
            "last_update": utils.epoch_timestamp_to_iso_format(self.last_update_epoch),
            "temp_c": f"{self.temp_c:.2f}" if self.temp_c is not None else "N / A",
            "weather_condition": " or ".join(wc.value[1] for wc in self.weather_condition)
            if len(self.weather_condition) > 0
            else "N / A"
        })

class CityWeatherDataFetchError(Exception):
    pass

class CityWeatherDataCityNotFoundError(CityWeatherDataFetchError):
    def __repr__(self):
        return f"{self.__class__.__name__}()"

class CityWeatherDataRequestError(CityWeatherDataFetchError):
    def __init__(self, weather_service_error: WeatherServiceError):
        self.weather_service_error = weather_service_error
    def __repr__(self):
        return f"{self.__class__.__name__}({repr(self.weather_service_error)})"

def convert_weather_condition_text_to_weather_condition(weather_condition_text: str) -> WeatherCondition:
    clear_weather_condition_text = (weather_condition_text.lower().replace("shower", "")
                              .replace("at times", "")
                              .replace("slight", "light")
                              .replace("fall", "")
                              .replace("partly", "partially")
                              .replace("patchy", "light")
                              .replace("violent", "heavy")
                              .strip())

    if "clear" in clear_weather_condition_text or "sunny" in clear_weather_condition_text:
        return WeatherCondition.CLEAR
    elif "cloudy" in clear_weather_condition_text:
        if "partially" in clear_weather_condition_text:
            return WeatherCondition.PARTIALLY_CLOUDY
        else:
            return WeatherCondition.CLOUDY
    elif "drizzle" in clear_weather_condition_text:
            return WeatherCondition.DRIZZLE
    elif "rain" in clear_weather_condition_text:
        if "light" in clear_weather_condition_text:
            return WeatherCondition.LIGHT_RAIN
        elif "moderate" in clear_weather_condition_text:
            return WeatherCondition.MODERATE_RAIN
        elif "heavy" in clear_weather_condition_text:
            return WeatherCondition.HEAVY_RAIN
        else:
            return WeatherCondition.MODERATE_RAIN
    elif "snow" in clear_weather_condition_text:
        if "light" in clear_weather_condition_text:
            return WeatherCondition.LIGHT_SNOW
        elif "moderate" in clear_weather_condition_text:
            return WeatherCondition.MODERATE_SNOW
        elif "heavy" in clear_weather_condition_text:
            return WeatherCondition.HEAVY_SNOW
        else:
            return WeatherCondition.MODERATE_SNOW
    elif "mist" in clear_weather_condition_text:
        return WeatherCondition.MIST
    elif "fog" in clear_weather_condition_text:
        return WeatherCondition.FOG
    elif "overcast" in clear_weather_condition_text:
        return WeatherCondition.OVERCAST
    else:
        return WeatherCondition.UNRECOGNIZED


def convert_weather_service_response_to_weather_data(weather_service_response: Any) -> CityWeatherData:
    OPEN_METEO_WEATHER_CODES_FILENAME = "open_meteo_weather_codes.csv"
    weather_condition_text = None

    if type(weather_service_response) is WeatherApiResponse:
        last_update_epoch = weather_service_response.last_update_epoch
        weather_condition_text = weather_service_response.condition_text
    elif type(weather_service_response) is OpenMeteoResponse:
        last_update_epoch = int(datetime.strptime(weather_service_response.time, "%Y-%m-%dT%H:%M")
                                .replace(tzinfo=timezone.utc).timestamp()) \
                            if weather_service_response.time \
                            else None

        try:
            with open(OPEN_METEO_WEATHER_CODES_FILENAME, newline="") as f:
                weather_dict = {int(row["code"]): row["description"] for row in csv.DictReader(f)}
                if weather_service_response.weather_code in weather_dict:
                    weather_condition_text = weather_dict[weather_service_response.weather_code]
                else:
                    print(f"Weather code received in OpenMeteo response not in {OPEN_METEO_WEATHER_CODES_FILENAME}")

        except IOError as e:
            print(f"Could not read open meteo weather codes file: {e}")

    else:
        raise ValueError(f"weather_service_response must be an instance of {WeatherApiResponse.__class__.__name__}"
                         f" or {OpenMeteoResponse.__class__.__name__}")

    latitude = weather_service_response.latitude
    longitude = weather_service_response.longitude
    temp_c = weather_service_response.temp_c
    weather_condition = convert_weather_condition_text_to_weather_condition(weather_condition_text) \
        if weather_condition_text else WeatherCondition.UNRECOGNIZED

    return CityWeatherData(latitude, longitude, last_update_epoch, temp_c, weather_condition)

def average_city_weather_data(weather_data_list: List[CityWeatherData]) -> Optional[CityWeatherData]:
    def city_weather_data_filter(city_weather_data: CityWeatherData) -> bool:
        STALE_CUTOFF_NUM_SECONDS = 6 * 60 * 60
        return (city_weather_data.latitude is not None and city_weather_data.longitude is not None
                and city_weather_data.last_update_epoch is not None
                and time.time() - city_weather_data.last_update_epoch <= STALE_CUTOFF_NUM_SECONDS)

    filtered_weather_data_list = list(filter(city_weather_data_filter, weather_data_list))

    if len(filtered_weather_data_list) == 0:
        return None

    avg_last_update_epoch = min(filtered_weather_data_list, key=lambda data: data.last_update_epoch).last_update_epoch
    filtered_temp_c = [data.temp_c for data in filtered_weather_data_list if data.temp_c is not None]
    avg_temp_c = sum(filtered_temp_c) / len(filtered_temp_c) if len(filtered_temp_c) > 0 else None
    avg_weather_condition = list(set(data.weather_condition[0]
                                        for data in filtered_weather_data_list
                                        if data.weather_condition is not None
                                        and data.weather_condition != [WeatherCondition.UNRECOGNIZED]))


    return CityWeatherData(filtered_weather_data_list[0].latitude, filtered_weather_data_list[0].longitude,
                           avg_last_update_epoch, avg_temp_c, avg_weather_condition)

def fetch_city_weather_data(city_name: str) -> CityWeatherData:
    try:
        weather_service_responses = [weather_api.fetch_data_weather_api(city_name)]

        try:
            if weather_service_responses[0].latitude is not None and weather_service_responses[0].longitude is not None:
                weather_service_responses.append(open_meteo.fetch_data_open_meteo(weather_service_responses[0].latitude,
                                                                       weather_service_responses[0].longitude))
        except OpenMeteoRequestError as e:
            print(f'Could not fetch weather data from OpenMeteo: {e}')

        weather_data_list = [convert_weather_service_response_to_weather_data(response)
                                             for response in weather_service_responses]
        avg_weather_data = average_city_weather_data(weather_data_list)

        if avg_weather_data is None:
            raise CityWeatherDataFetchError("All city weather datas were filtered out")

        return avg_weather_data
    except WeatherApiCityNotFoundError as e:
        raise CityWeatherDataCityNotFoundError()
    except WeatherApiRequestError as e:
        raise CityWeatherDataRequestError(e)

print(fetch_city_weather_data("Tel Aviv").to_json())