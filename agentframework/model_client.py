from agent_framework.openai import OpenAIChatClient


def create_model_client_local():
    return OpenAIChatClient(
        model_id="qwen3:4b",
        api_key="ollama",
        base_url="http://localhost:11434/v1",
    )
