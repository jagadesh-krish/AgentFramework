import os
import json
import uuid
from .model_client import create_model_client_local
from dotenv import load_dotenv
from agent_framework import ChatAgent, ai_function
from agentframework.agent_middewares import (
    timing_middleware,
    security_middleware,
    function_logger_middleware,
    token_counter_middleware,
)
from agentframework.weather_agents.agents import weather_agent

load_dotenv()



async def create_moderator_agent():
    return ChatAgent(
        name="TravelPlanningAgent",
        description="A helpful agent that acts a mediator between human and other agents in the system",
        instructions="""You are a moderator Agent who is responsible for handling interactions with user and routing them to appropriate agents based on their queries/context.
        Keep the context of previous interactions in mind while responding to user queries.
        Give proper user readable responses. And don't just reply with the tool output, format them as human readable text. and reply without quotes, but its ok to add emojis if needed.
        Your goal is to assist users in planning their travel by coordinating with specialized agents like WeatherAgent, etc...
        NOTE: Always use the WeatherAgent to get weather information when the user asks about weather conditions at a location.
        Keep your responses concise and to the point. Do not include unnecessary details. Give factual information only. Do not fabricate information.
        If multiple agents or tool calls are involved in answering a query, synthesize their responses into a coherent final answer for the user.
        
        Tools and Agent Capabilities:
        - WeatherAgent: Use this agent to get weather information for any location-based queries from the user.
                        The WeatherAgent can provide current weather details as well as forecast information.
        """,
        chat_client=create_model_client_local(),
        tools=[weather_agent.as_tool()],
        middleware=[
            timing_middleware,          # Agent middleware #1
            security_middleware,        # Agent middleware #2
            function_logger_middleware, # Function middleware
            token_counter_middleware,   # Chat middleware
        ]
    )


async def run_weather_agent():
    import logging
    from agent_framework.devui import serve
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger(__name__)
    logger.info("Starting Weather Agent")
    mod_agent = await create_moderator_agent()
    logger.info("Endpoint available at http://localhost:8090")
    serve(entities=[mod_agent], port=8090, auto_open=True)


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_weather_agent())