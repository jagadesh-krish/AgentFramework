import asyncio
import json
import logging
import os
import structlog

from agentframework.agent import create_moderator_agent
from agentframework.response_schema import WeatherInfo
from agentframework.service_layer.chat_handlers import (
    RabbitMQBus,
    REQUEST_QUEUE,
    RESPONSE_QUEUE,
)

procs = [
    structlog.contextvars.merge_contextvars,
    structlog.processors.add_log_level,
    structlog.processors.StackInfoRenderer(),
    structlog.dev.set_exc_info,
    structlog.processors.TimeStamper(fmt="iso"),
]
procs.append(structlog.dev.ConsoleRenderer())
structlog.configure(
    processors=procs,
    wrapper_class=structlog.BoundLogger,
    context_class=dict,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


def get_logger():
    return logger.bind()


async def get_thread_for_session(log, session_id, agent):
    if os.path.exists(f"threads/{session_id}.json"):
        log.msg("Loading thread for session", session_id=session_id)
        with open(f"threads/{session_id}.json", "r") as f:
            loaded_json = f.read()
        reloaded_data = json.loads(loaded_json)
        resume_thread = await agent.deserialize_thread(reloaded_data)
        return resume_thread
    else:
        log.msg("No thread found for session, creating new one", session_id=session_id)
        return agent.get_new_thread()


async def save_thread_for_session(log, session_id, thread):
    if os.path.exists(f"threads/{session_id}.json"):
        log.msg("Saving thread for session", session_id=session_id)
        serialized_thread = await thread.serialize()
        serialized_json = json.dumps(serialized_thread)
        with open(f"threads/{session_id}.json", "w") as f:
            f.write(serialized_json)
    else:
        log.msg("No thread found for session, creating new one", session_id=session_id)
        serialized_thread = await thread.serialize()
        serialized_json = json.dumps(serialized_thread)
        with open(f"threads/{session_id}.json", "w") as f:
            f.write(serialized_json)


async def handle_message(bus, msg):
    log = get_logger()
    session_id = msg.get("session_id")
    content = msg.get("content", "")
    # history = msg.get("conversation_history", [])
    agent = await create_moderator_agent()
    try:
        # Use run with conversation history if the agent supports it
        conversation_thread = await get_thread_for_session(log, session_id, agent)
        response = await agent.run(content, thread=conversation_thread)
        resp_text = (
            json.dumps(response, default=str, ensure_ascii=False)
            if not isinstance(response, str)
            else response
        )
        await save_thread_for_session(log, session_id, conversation_thread)
        log.msg("Publishing response to response queue", response_queue=RESPONSE_QUEUE, session_id=session_id)
        await bus.publish(
            f"{RESPONSE_QUEUE}",
            {"content": resp_text, "source": "agent", "session_id": session_id},
        )
    except Exception as e:
        log.error("Error processing message", error=str(e), session_id=session_id)
        await bus.publish(
            f"{RESPONSE_QUEUE}",
            {"content": f"Error: {e}", "source": "agent", "session_id": session_id},
        )


async def run_worker() -> None:
    bus = RabbitMQBus()
    await bus.connect()
    log = get_logger()
    log.info("response_worker_started", request_queue=REQUEST_QUEUE)
    try:
        async for msg in bus.consume(REQUEST_QUEUE):
            asyncio.create_task(handle_message(bus, msg))
    finally:
        await bus.close()


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()


