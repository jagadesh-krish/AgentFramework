from pydantic import BaseModel

class WeatherInfo(BaseModel):
    """Information about a location's weather info."""
    location: str | None = None
    temprature: int | None = None