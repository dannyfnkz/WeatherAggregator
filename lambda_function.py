import json
import boto3
import time
from typing import Optional
from typing import Tuple
from botocore.exceptions import ClientError

import city_weather_data
import utils
from city_weather_data import CityWeatherDataFetchError
from city_weather_data import CityWeatherDataCityNotFoundError
from city_weather_data import CityWeatherDataRequestError
from weather_api import WeatherApiCityNotFoundError

dynamodb = boto3.resource('dynamodb')
ip_table = dynamodb.Table("RequestIPLogs")


def get_request_ip(event):
    return event.get('requestContext', {}).get('http', {}).get('sourceIp', None)


def get_request_city_param(event):
    return event.get('queryStringParameters', {}).get('city', None)


def get_ip_last_accessed_timestamp_from_db(ip) -> Tuple[Optional[int], bool]:
    try:
        # Only retrieve the 'LastAccessTimestamp' attribute
        response = ip_table.get_item(Key={'ip': ip},
                                     ProjectionExpression='LastAccessTimestamp')
        last_access_timestamp = response.get('Item', {}).get('LastAccessTimestamp', None)

        return (int(last_access_timestamp) if last_access_timestamp else None), True
    except ClientError as e:
        print(f"Error retrieving LastAccessTimestamp: {e}")
        return None, False


def update_ip_last_accessed_timestamp_in_db(ip) -> Tuple[Optional[int], bool]:
    timestamp_seconds = int(time.time())

    try:
        # 4. Perform the Update
        response = ip_table.update_item(
            Key={
                'ip': ip
            },
            UpdateExpression="SET LastAccessTimestamp = :t",
            ExpressionAttributeValues={
                ':t': timestamp_seconds
            },
            ReturnValues="UPDATED_NEW"
        )
        print(f"LastAccessTimestamp Update successful: {response['Attributes']}")
        return int(response['Attributes']['LastAccessTimestamp']), True

    except ClientError as e:
        print(f"LastAccessTimestamp Update failed: {str(e)}")
        return None, False


def handle_missing_parameter_city(context):
    return {
        'statusCode': 400,
        'headers': {
            'Content-Type': 'application/json',
            "X-Request-ID": context.aws_request_id
        },
        'body': json.dumps({
            "error": "Bad Request",
            "message": "The required query parameter 'city' is missing.",
            "details": "Please include ?city=CityName in the request URL.",
            "request_id": context.aws_request_id
        })
    }

def handle_city_not_found(context, city: str, last_access_timestamp_message: str):
    return {
        'statusCode': 404,
        'headers': {
            'Content-Type': 'application/json',
            "X-Request-ID": context.aws_request_id
        },
        'body': json.dumps({
            "error": "Not Found",
            "message": "No data available for the specified city.",
            "details": f"No matching city was found with the name '{city}'.",
            "last_access": last_access_timestamp_message,
            "request_id": context.aws_request_id
        })
    }


def handle_internal_server_error(context):
    return {
        'statusCode': 500,
        'headers': {
            'Content-Type': 'application/json',
            "X-Request-ID": context.aws_request_id
        },
        'body': json.dumps({
            "error": "Internal Server Error",
            "message": "An unexpected error occurred.",
            "details": "Please try again later.",
            "request_id": context.aws_request_id
        })
    }

def handle_service_unavailable_error(context, last_access_timestamp_message: str):
    return {
        'statusCode': 503,
        'headers': {
            'Content-Type': 'application/json',
            "X-Request-ID": context.aws_request_id
        },
        'body': json.dumps({
            "error": "Service Unavailable",
            "message": "Service is currently unavailable.",
            "details": "Please try again later.",
            "last_access": last_access_timestamp_message,
            "request_id": context.aws_request_id
        })
    }

def lambda_handler(event, context):
    city = get_request_city_param(event)

    if not city:
        print("Request missing 'city' parameter")
        return handle_missing_parameter_city(context)

    request_ip = get_request_ip(event)

    if not request_ip:
        return handle_internal_server_error(context)

    print(f"Received request from IP: {request_ip}")

    prev_last_access_timestamp, success = get_ip_last_accessed_timestamp_from_db(request_ip)

    if not success:
        return handle_internal_server_error(context)

    cur_last_access_timestamp, success = update_ip_last_accessed_timestamp_in_db(request_ip)

    if not success:
        return handle_internal_server_error(context)

    prev_last_access_timestamp_message = utils.epoch_timestamp_to_iso_format(prev_last_access_timestamp) \
        if prev_last_access_timestamp else "N / A"

    print(f"Previous last access: {prev_last_access_timestamp_message}")

    try:
        weather_data = city_weather_data.fetch_city_weather_data(city)

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                "X-Request-ID": context.aws_request_id
            },
            'body': json.dumps({
                "city": city,
                "weather": weather_data.to_json(),
                "last_access": prev_last_access_timestamp_message,
                "request_id": context.aws_request_id
            })
        }

    except CityWeatherDataCityNotFoundError as e:
        print(f'City Weather data fetching failed as city was not found: {e}')
        return handle_city_not_found(context, city, prev_last_access_timestamp_message)
    except CityWeatherDataRequestError as e:
        print(f'City Weather data fetching failed due to a request error: {e}')
        return handle_service_unavailable_error(context, prev_last_access_timestamp_message)




