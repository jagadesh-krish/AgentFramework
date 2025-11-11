from datetime import date
from agent_framework import ai_function
import requests
from typing import Optional, Annotated
import os
from agentframework.weather_agents.enums import WeatherInfoType

from agentframework.agent_middewares import log


# Simple mapping of Open-Meteo weather codes to human-readable descriptions
WEATHER_CODE_DESCRIPTION = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "moderate drizzle",
    55: "dense drizzle",
    56: "light freezing drizzle",
    57: "dense freezing drizzle",
    61: "slight rain",
    63: "moderate rain",
    65: "heavy rain",
    66: "light freezing rain",
    67: "heavy freezing rain",
    71: "slight snow fall",
    73: "moderate snow fall",
    75: "heavy snow fall",
    77: "snow grains",
    80: "slight rain showers",
    81: "moderate rain showers",
    82: "violent rain showers",
    85: "slight snow showers",
    86: "heavy snow showers",
    95: "thunderstorm",
    96: "thunderstorm with slight hail",
    99: "thunderstorm with heavy hail",
}


# Geocode a location name to latitude and longitude using Open-Meteo's geocoding API
@ai_function(name="geocode_location", description="Geocodes a location name to latitude and longitude")
async def geocode_location(location: str) -> Optional[dict]:
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1"
    resp = requests.get(url)
    log.msg("Geocoding location with status code", location=location, status_code=resp.status_code)
    if resp.status_code == 200:
        data = resp.json()
        if "results" in data and len(data["results"]) > 0:
            loc_data = data["results"][0]
            log.msg("Geocoded location data", geo_code_data=loc_data)
            return {
                "latitude": loc_data["latitude"],
                "longitude": loc_data["longitude"],
                "name": loc_data["name"],
                "country": loc_data.get("country")
            }
    return None


# Geocode a location name to latitude and longitude using nominatim geocoding API
@ai_function(name="geocode_nominatim", description="Geocodes a location name to latitude and longitude using Nominatim")
async def geocode_nominatim(location: str) -> Optional[dict]:
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": location,
        "format": "json",
        "limit": 1
    }
    headers = {
        "User-Agent": f"TravelAgentChatbot/1.0 ({os.getenv('USER_AGENT_EMAIL', 'default@example.com')})"
    }
    log.msg(f"Geocoding location using Nominatim", params=params, location=location)
    response = requests.get(url, params=params, headers=headers)
    log.msg("Nominatim response status code", status_code=response.status_code)
    if response.status_code == 200 and response.json():
        data = response.json()[0]
        log.msg("Nominatim geocoded data", geo_code_data=data)
        return {
            "latitude": float(data["lat"]),
            "longitude": float(data["lon"]),
            "display_name": data["display_name"]
        }
    return None


# Fetch current weather for given latitude and longitude
@ai_function(name="get_current_weather", description="Fetches current weather for given latitude and longitude")
async def get_current_weather(latitude: float, longitude: float) -> Optional[dict]:
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={latitude}&longitude={longitude}&current_weather=true"
    )
    log.msg("Fetching current weather for", latitude=latitude, longitude=longitude)
    resp = requests.get(url)
    log.msg("Current weather fetch status code", status_code=resp.status_code)
    if resp.status_code == 200:
        data = resp.json()
        log.msg("Current weather data", current_weather_data=data)
        return data.get("current_weather")
    return None


# Get daily forecast data (up to 7 days)
@ai_function(name="get_forecast_weather", description="Fetches daily forecast weather data for given location")
async def get_forecast_weather(lat: float, lon: float) -> Optional[dict]:
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}&daily=temperature_2m_max,temperature_2m_min,"
        f"precipitation_sum,weathercode&timezone=auto"
    )
    log.msg(f"Fetching forecast weather for", latitude=lat, longitude=lon)
    resp = requests.get(url)
    log.msg(f"Forecast weather fetch status code", status_code=resp.status_code)
    if resp.status_code == 200:
        data = resp.json()
        log.msg(f"Forecast weather data", fore_cast_data=data)
        return resp.json().get("daily")
    return None


# Get historical weather data for date range
@ai_function(name="get_historical_weather", description="Fetches historical weather data for given location and date range")
async def get_historical_weather(lat: float, lon: float, start_date: date, end_date: date) -> Optional[dict]:
    url = (
        f"https://archive-api.open-meteo.com/v1/archive?"
        f"latitude={lat}&longitude={lon}&start_date={start_date}&end_date={end_date}"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode&timezone=auto"
    )
    resp = requests.get(url)
    if resp.status_code == 200:
        return resp.json().get("daily")
    return None


# Tool function to be called by the agent for user's weather query
@ai_function(name="get_weather_for_location", description="Gets the current weather for a specified location")
async def get_weather_for_location(location: str) -> str:
    loc = await geocode_location(location)
    if not loc:
        return f"Sorry, I could not find any location named '{location}'."
    
    weather = await get_current_weather(loc["latitude"], loc["longitude"])
    if not weather:
        return f"Sorry, I could not retrieve weather data for {loc['name']}."

    temperature = weather.get("temperature")
    windspeed = weather.get("windspeed")
    winddirection = weather.get("winddirection")
    weathercode = weather.get("weathercode")

    weather_desc = WEATHER_CODE_DESCRIPTION.get(weathercode, "Unknown weather conditions")

    return (
        f"The current weather in {loc['name']}, {loc.get('country', '')} is {weather_desc} "
        f"with temperature {temperature}°C, wind speed {windspeed} km/h, "
        f"and wind direction {winddirection} degrees."
    )


# Unified function for agents to call
@ai_function(name="get_weather_info", description="Gets weather information for a location based on specified type")
async def get_weather_info(location: Annotated[str, "name of the location/address"], info_type: Annotated[WeatherInfoType, "type of the weather detail to get"] = WeatherInfoType.CURRENT, start_date: date = None, end_date: date = None) -> str:
    log.msg("tool invoked with parameters", location=location, info_type=info_type.value, start_date=start_date, end_date=end_date)
    loc =  await geocode_nominatim(location)
    log.msg("Geocoded location for", location=location, loc=loc)
    if not loc:
        return f"Could not find location '{location}'."
    
    lat = loc["latitude"]
    lon = loc["longitude"]
    
    if info_type.value == "current":
        log.msg(f"Fetching current weather for location", location=location)
        current = await get_current_weather(lat, lon)
        log.msg(f"Current weather data", current_weather=current)
        if not current:
            return f"Could not fetch current weather for {location}."
        desc = WEATHER_CODE_DESCRIPTION.get(current.get("weathercode", -1), "Unknown conditions")
        return (f"Current weather in {location}: {desc}, "
                f"{current.get('temperature')}°C, wind {current.get('windspeed')} km/h.")
    
    if info_type.value == "forecast":
        log.msg(f"Fetching forecast weather for location", location=location)
        forecast = await get_forecast_weather(lat, lon)
        log.msg(f"Forecast weather data", forecast_data=forecast)
        if not forecast:
            return f"Could not fetch forecast for {location}."
        response = f"7-day forecast for {location}:\n"
        for i in range(len(forecast["time"])):
            date_str = forecast["time"][i]
            desc = WEATHER_CODE_DESCRIPTION.get(forecast["weathercode"][i], "Unknown conditions")
            response += (f"{date_str}: {desc}, Max {forecast['temperature_2m_max'][i]}°C, "
                         f"Min {forecast['temperature_2m_min'][i]}°C, Precipitation: {forecast['precipitation_sum'][i]}mm\n")
        return response

    if info_type.value == "historical":
        if not start_date or not end_date:
            return "Please provide start_date and end_date for historical data."
        historical = await get_historical_weather(lat, lon, start_date, end_date)
        if not historical:
            return f"Could not fetch historical data for {location}."
        response = f"Historical weather for {location} from {start_date} to {end_date}:\n"
        for i in range(len(historical["time"])):
            date_str = historical["time"][i]
            desc = WEATHER_CODE_DESCRIPTION.get(historical["weathercode"][i], "Unknown conditions")
            response += (f"{date_str}: {desc}, Max {historical['temperature_2m_max'][i]}°C, "
                         f"Min {historical['temperature_2m_min'][i]}°C, Precipitation: {historical['precipitation_sum'][i]}mm\n")
        return response

    return "Invalid info_type specified."