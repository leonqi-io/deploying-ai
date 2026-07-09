from fastmcp import FastMCP
from pydantic import BaseModel, Field

mcp = FastMCP(
    name="weather_advice_service",
    instructions="Given current weather conditions, suggests what to wear or what activities are suitable."
)

class ActivityAdvice(BaseModel):
    clothing_advice: str = Field(..., description="What to wear given the conditions.")
    activity_advice: str = Field(..., description="Whether outdoor activity is a good idea, and why.")

@mcp.tool(
    name="get_weather_advice",
    description="Given a temperature (Celsius) and weather condition, suggests clothing and activities."
)
def get_weather_advice(temperature_c: float, condition: str) -> ActivityAdvice:
    """Rule-based advice generator — no external API call needed."""
    if temperature_c < 0:
        clothing_advice = "Wear a heavy coat, gloves, and a hat."
        activity_advice = "Best to stay indoors; outdoor activities are not recommended."
    elif 0 <= temperature_c < 15:
        clothing_advice = "Wear a warm jacket or coat."
        activity_advice = "Outdoor activities are okay, but dress warmly."
    elif 15 <= temperature_c < 25:
        clothing_advice = "Wear a light jacket or long sleeves."
        activity_advice = "Outdoor activities are suitable."
    else:  #temperature_c >= 25
        clothing_advice = "Wear short sleeves and light clothing."
        activity_advice = "Great weather for outdoor activities."

    if "rain" in condition.lower():
        activity_advice = "It's wet outside; consider indoor activities or bring an umbrella."
    elif "snow" in condition.lower():
        activity_advice = "Snowy conditions; outdoor activities may be fun but dress warmly and be cautious."

    return ActivityAdvice(clothing_advice=clothing_advice, activity_advice=activity_advice)

if __name__ == "__main__":
    mcp.run(transport="stdio")