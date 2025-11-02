import os
import json
import uuid
from agent_framework.azure import AzureOpenAIChatClient
from agent_framework.openai import OpenAIChatClient
from dotenv import load_dotenv
from agent_framework import ChatAgent, ai_function
from agentframework.agent_middewares import (
    timing_middleware,
    security_middleware,
    function_logger_middleware,
    token_counter_middleware,
)

load_dotenv()


@ai_function(name="get_weather", description="Retrieves weather information for any location/city")
def get_weather(city: str) -> str:
    """Get the weather for the given city"""
    return f"The weather in city {city} is around 20 degree celsius."


@ai_function(name="reset_password", description="calls reset passowrd api for the specified upn")
def reset_password(upn: str) -> str:
    """Reset Password for specified UPN"""
    return f"User password have been reset successfully for upn: {upn}"

@ai_function(name="get_menu", description="Fetches the restaurant menu for customers.")
def get_menu() -> str:
    """Fetch the restaurant menu."""
    # Example menu; replace with dynamic fetching logic if needed
    menu = {
        "Appetizers": ["Spring Rolls", "Garlic Bread"],
        "Main Course": ["Grilled Chicken", "Veggie Burger"],
        "Desserts": ["Cheesecake", "Brownie Sundae"],
        "Beverages": ["Coffee", "Lemonade"]
    }
    return json.dumps(menu, indent=2)

@ai_function(name="place_order", description="Places an order for the customer.")
def place_order(order_details: dict) -> str:
    """Place an order with the given details."""
    # Example logic; replace with actual order processing
    order_id = str(uuid.uuid4())
    return f"Order placed successfully! Order ID: {order_id}, Details: {json.dumps(order_details, indent=2)}"

@ai_function(name="get_reviews", description="Fetches reviews for a specific menu item.")
def get_reviews(item_name: str) -> str:
    """Fetch reviews for the given menu item."""
    # Example reviews; replace with dynamic fetching logic if needed
    reviews = {
        "Spring Rolls": ["Crispy and delicious!", "Too oily for my taste."],
        "Grilled Chicken": ["Perfectly cooked!", "A bit dry, but flavorful."],
        "Cheesecake": ["Heavenly!", "Too sweet for me."]
    }
    item_reviews = reviews.get(item_name, ["No reviews available for this item."])
    return json.dumps(item_reviews, indent=2)

@ai_function(name="get_food_details", description="Provides detailed information about a specific food item.")
def get_food_details(item_name: str) -> str:
    """Get details for the given food item."""
    # Example details; replace with dynamic fetching logic if needed
    details = {
        "Spring Rolls": "Crispy rolls filled with fresh vegetables and served with a tangy dipping sauce.",
        "Grilled Chicken": "Juicy grilled chicken breast seasoned with herbs and spices.",
        "Cheesecake": "Rich and creamy cheesecake with a graham cracker crust."
    }
    return details.get(item_name, "No details available for this item.")

@ai_function(name="follow_up_order", description="Tracks and provides updates on a customer's order.")
def follow_up_order(order_id: str) -> str:
    """Provide updates for the given order ID."""
    # Example follow-up logic; replace with actual tracking system
    updates = {
        "123e4567-e89b-12d3-a456-426614174000": "Your order is being prepared.",
        "123e4567-e89b-12d3-a456-426614174001": "Your order is out for delivery."
    }
    return updates.get(order_id, "No updates available for this order ID.")

    
def create_model_client_local():
    return OpenAIChatClient(
        model_id="qwen3:4b",
        api_key="ollama",
        base_url="http://localhost:11434/v1",
    )


agent = ChatAgent(
    name="WeatherAgent",
    description="A helpful agent that provide details of current weather informaton",
    instructions="You are a Weather Agent who is responsible for getting information abput weather details regarding weather queries",
    chat_client=create_model_client_local(),
    tools=[get_weather]
)

restaurant_agent = ChatAgent(
    name="RestaurantAgent",
    description="A helpful agent that provide assistance regarding restaurant related queries to the customers",
    instructions="You are a Restaurant Agent who is responsible for assisting customers with their restaurant needs and services",
    chat_client=create_model_client_local(),
    tools=[get_menu, place_order, get_reviews, get_food_details, follow_up_order]
)

it_admin_agent = ChatAgent(
    name="ITAdminAgent",
    description="A helpful agent that provide tools to IT admin ops",
    instructions="You are a IT Admin Agent who is responsible for IT infrastructure things and related queries",
    chat_client=create_model_client_local(),
    tools=[reset_password]
)

async def create_weather_agent():
    return ChatAgent(
        name="WeatherAgent",
        description="A helpful agent that provide details of current weather informaton",
        instructions="You are a Weather Agent who is responsible for getting information abput weather details regarding weather queries",
        chat_client=create_model_client_local(),
        tools=[get_weather]
    )
    

async def create_restaurant_agent():
    return ChatAgent(
        name="RestaurantAgent",
        description="A helpful agent that provide assistance regarding restaurant related queries to the customers",
        instructions="You are a Restaurant Agent who is responsible for assisting customers with their restaurant needs and services",
        chat_client=create_model_client_local(),
        tools=[get_menu, place_order, get_reviews, get_food_details, follow_up_order]
    )

async def create_it_admin_agent():
    return ChatAgent(
        name="ITAdminAgent",
        description="A helpful agent that provide tools to IT admin ops",
        instructions="You are a IT Admin Agent who is responsible for IT infrastructure things and related queries",
        chat_client=create_model_client_local(),
        tools=[reset_password],
    )


async def create_moderator_agent():
    return ChatAgent(
        name="ModeratorAgent",
        description="A helpful agent that acts a mediator between human and other agents in the system",
        instructions="""You are a moderator Agent who is responsible for handling interactions with user and routing them to appropriate agents based on their queries/context.
        Keep the context of previous interactions in mind while responding to user queries.
        Give proper user readable responses. And don't just reply with the tool output format them as human readable text. and rely without quotes.""",
        chat_client=create_model_client_local(),
        tools=[restaurant_agent.as_tool(), agent.as_tool(), it_admin_agent.as_tool()],
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