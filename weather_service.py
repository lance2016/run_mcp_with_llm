from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP
from loguru import logger


mcp = FastMCP("weather", log_level="ERROR")

NWS_API_BASE="https://api.weather.gov"
USER_AGENT = "weather-app/1.0"

async def make_nws_request(url:str) ->dict[str, Any] | None:
    """
    Make a request to the NWS API and return the response as a dictionary.
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json",
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error making request to NWS API: {e=}")
            return None


async def format_alert(feature:dict)->str:
    """
    Format a weather alert into a string.
    """
    props = feature["properties"]
    return f"""
Event: {props.get("event", "Unknown event")}
Area: {props.get("areaDesc", "Unknown area")}
Severity: {props.get("severity", "Unknown severity")}
Description: {props.get("description", "No description available")}
Instruction: {props.get("instruction", "No instruction available")}
"""

@mcp.tool()
async def get_alerts(state:str) ->str:
    """
    Get weather alerts for a given state.
    """
    url = f"{NWS_API_BASE}/alerts/active/area/{state}"
    data = await make_nws_request(url)
    if not data or "features" not in data:
        return "Unable to fetch alerts or no alerts found."
    features = data.get("features", [])
    if not features:
        return "No active alerts for this state."
    
   
    alerts = [await format_alert(feature) for feature in features]
    return "\n---\n".join(alerts)


@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """
    Get the weather forecast for a given latitude and longitude.
    """
    points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
    points_data = await make_nws_request(points_url)
    if not points_data:
        return "Unable to fetch forecast data for this location."
    
    forecast_url = points_data.get("properties", {}).get("forecast")
    forcast_data = await make_nws_request(forecast_url)
    if not forcast_data:
        return "Unable to fetch forecast data for this location."
    
    periods = forcast_data.get("properties", {}).get("periods", [])
    forecasts = []
    for period in periods[:5]:
        forecast = f"""
{period.get("name", "Unknown period")}:
Temperature: {period.get("temperature", "Unknown temperature")} {period.get("temperatureUnit", "Unknown unit")}
Wind: {period.get("windSpeed", "Unknown wind speed")} {period.get("windDirection", "Unknown wind direction")}
Forecast: {period.get("detailedForecast", "No forecast available")}
"""
        forecasts.append(forecast)
    return "\n---\n".join(forecasts)

import fastapi

app = fastapi.FastAPI()

app.mount("/", mcp.sse_app())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)