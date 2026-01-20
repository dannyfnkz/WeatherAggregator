from datetime import datetime, timezone
from typing import Optional

import numpy as np
import requests
import json

# Replace this with the actual Invoke URL from your AWS API Gateway
#API_ENDPOINT = "https://st0v5awjwg.execute-api.eu-north-1.amazonaws.com/default/sampleRestFunction?city=Jerusalem"
API_ENDPOINT = "https://vt7rupl6qklrnz4z6w2acoo22u0mzgdi.lambda-url.eu-north-1.on.aws?city=Jerusalem"


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
        print(f"❌ HTTP Error occurred")
        print("Status Code:", err.response.status_code)
        print("Content:", err.response.content)
    except requests.exceptions.RequestException as err:
        print(f"❌ An error occurred during the request: {err}")


if __name__ == "__main__":
    fetch_data_from_api()





# https://open-meteo.com/en/docs?daily=weather_code