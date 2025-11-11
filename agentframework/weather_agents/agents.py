from agent_framework import ChatAgent
from agentframework.agent_middewares import function_logger_middleware, security_middleware, timing_middleware, token_counter_middleware
from agentframework.model_client import create_model_client_local
from agentframework.weather_agents.tools import get_weather_for_location, get_weather_info

weather_agent = ChatAgent(
    name="WeatherAgent",
    description="A helpful agent that provide details of current weather information",
    instructions="""You are a Weather Agent who is responsible for getting information about weather details regarding weather queries.
    Upon getting a weather query from the user, use the 'get_weather_info' tool to fetch the relevant weather information and provide a concise and accurate response to the user.
    Extract only the necessary details from the tool response and format them into a human-readable format.
    Try to pass exact location name to the tool to get accurate results.
    NOTE: Identify whether the user is asking for current weather or forecast and set the 'info_type' parameter of the tool accordingly with respect to the user's query and context.
    """,
    chat_client=create_model_client_local(),
    tools=[get_weather_info],
    middleware=[
        timing_middleware,          # Agent middleware #1
        security_middleware,        # Agent middleware #2
        function_logger_middleware, # Function middleware
        token_counter_middleware,   # Chat middleware
    ]
)


async def create_weather_agent():
    return ChatAgent(
        name="WeatherAgent",
        description="A helpful agent that provide details of current weather informaton",
        instructions="You are a Weather Agent who is responsible for getting information about weather details regarding weather queries",
        chat_client=create_model_client_local(),
        tools=[get_weather_info]
    )