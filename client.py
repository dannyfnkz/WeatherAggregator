import requests
import json

API_ENDPOINT = "https://vt7rupl6qklrnz4z6w2acoo22u0mzgdi.lambda-url.eu-north-1.on.aws?city=Tel Aviv"


def fetch_data_from_api():
    try:
        # Send a GET request to the API
        response = requests.get(API_ENDPOINT)

        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status()

        # The response body from Lambda is a JSON string, which we load into a Python dict
        data = response.json()

        print("✅ API Call Successful!")
        print("Status Code:", response.status_code)
        print("Response Data (Python dict):")
        # Pretty print the dictionary for readability
        print(json.dumps(data, indent=4))

    except requests.exceptions.HTTPError as err:
        print("❌ HTTP Error occurred")
        print("Status Code:", err.response.status_code)
        print("Content:", err.response.content)
    except requests.exceptions.RequestException as err:
        print(f"❌ An error occurred during the request: {err}")


if __name__ == "__main__":
    fetch_data_from_api()


# TODO
# build get_response function
# clear database in aws
# on lambda end, return response with just the last unique 10 cities, keep the order
# check implications of keeping large lists as fields in dynamo db
# cash system for requests for same city - inmemory / in db
# authentication system via an API key
# rate limiting with an API key
# continuous polling of api services so that lambda only retrieves available data - maybe poll only most popular cities - server architecture required
# https://open-meteo.com/en/docs?daily=weather_code
