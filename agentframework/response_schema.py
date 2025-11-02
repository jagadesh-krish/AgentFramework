from pydantic import BaseModel

class WeatherInfo(BaseModel):
    """Information about a location's weather info."""
    location: str | None = None
    temprature: int | None = None
    
    
class MenuItems(BaseModel):
    """Information about restaurant menu items."""
    appetizers: list[str] | None = None
    main_course: list[str] | None = None
    desserts: list[str] | None = None
    beverages: list[str] | None = None