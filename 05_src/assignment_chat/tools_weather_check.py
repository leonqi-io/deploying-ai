from langchain.tools import tool
import requests

@tool
def get_current_weather(location: str) -> dict:
    """
    Returns the current weather conditions for a given location.
    """
    url = f"https://wttr.in/{location}?format=j1"
    response = requests.get(url)
    data = response.json()
    current = data["current_condition"][0]

    return {
        "temperature_C": current["temp_C"],
        "feels_like_C": current["FeelsLikeC"],
        "condition": current["weatherDesc"][0]["value"],
        "humidity": current["humidity"],
        "wind_kmph": current["windspeedKmph"],
        "precip_mm": current["precipMM"],
    }