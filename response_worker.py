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
    agent = await create_moderator_agent()
    try:
        # Get conversation thread for context
        conversation_thread = await get_thread_for_session(log, session_id, agent)
        
        # Use run_stream for streaming responses
        accumulated_text = ""
        chunk_count = 0
        
        # Send initial thinking step
        await bus.publish(
            f"{RESPONSE_QUEUE}",
            {
                "type": "thinking_step",
                "step": {
                    "type": "ai_thinking",
                    "message": "Analyzing your request...",
                    "status": "thinking"
                },
                "source": "agent",
                "session_id": session_id,
                "stream": False,
                "done": False
            },
        )
        active_function_calls = {}  # Track function calls by their ID or index
        
        try:
            async for update in agent.run_stream(content, thread=conversation_thread):
                # Check for function calls and results in the update contents
                if hasattr(update, 'contents') and update.contents:
                    for content_item in update.contents:
                        # Get content type - check class name, type attribute
                        content_type = None
                        class_name = None
                        
                        # Check class name for FunctionCallContent or FunctionResultContent
                        if hasattr(content_item, '__class__'):
                            class_name = content_item.__class__.__name__
                        
                        # Check type attribute
                        if hasattr(content_item, 'type'):
                            content_type = content_item.type

                        
                        # Log for debugging
                        # log.debug("Processing content item", 
                        #     class_name=class_name, 
                        #     content_type=content_type,
                        #     has_function=True if content_type == 'function_call' else False,
                        #     has_result=True if content_type == 'function_result' else False
                        # )
                        
                        # Handle FunctionCallContent - check by class name or type
                        is_function_call = (
                            class_name and 'FunctionCall' in class_name
                        ) or (
                            content_type and ('function_call' in str(content_type).lower())
                        ) 
                        
                        # Handle FunctionResultContent - check by class name or type
                        is_function_result = (
                            class_name and 'FunctionResult' in class_name
                        ) or (
                            content_type and ('function_result' in str(content_type).lower())
                        ) or (
                            hasattr(content_item, 'result') and not is_function_call
                        )
                        
                        if is_function_call:
                            func_name = None
                            func_args = None
                            func_id = None
                            
                            # Try to get function name and ID
                            if hasattr(content_item, 'name'):
                                func_name = content_item.name
                            if hasattr(content_item, 'arguments'):
                                func_args = content_item.arguments
                            if hasattr(content_item, 'call_id'):
                                func_id = content_item.call_id
                            
                            if class_name and 'FunctionCall' in class_name:
                                # Store function call for later matching with results
                                if func_id:
                                    active_function_calls[func_id] = {
                                        "function_name": func_name,
                                        "arguments": func_args
                                    }
                                
                                # Send thinking step for function call
                                step = {
                                    "type": "function_call",
                                    "function_name": str(func_name),
                                    "arguments": str(func_args) if func_args else "N/A",
                                    "status": "calling",
                                    "function_id": str(func_id) if func_id else None
                                }
                                await bus.publish(
                                    f"{RESPONSE_QUEUE}",
                                    {
                                        "type": "thinking_step",
                                        "step": step,
                                        "source": "agent",
                                        "session_id": session_id,
                                        "stream": False,
                                        "done": False
                                    },
                                )
                                log.msg("Sent thinking step for function call", function_name=func_name, session_id=session_id)
                        
                        if is_function_result:
                            result = None
                            func_id = None
                            func_name = None
                            
                            # Try to get function ID to match with the call
                            if hasattr(content_item, 'call_id'):
                                func_id = content_item.call_id
                            
                            if hasattr(content_item, 'result'):
                                result = content_item.result
                            
                            # Try to get function name from stored calls
                            if func_id and func_id in active_function_calls:
                                func_name = active_function_calls[func_id]["function_name"]
                            
                            if result:
                                # Send thinking step for function result
                                step = {
                                    "type": "function_call",
                                    "function_name": str(func_name) if func_name else "Function",
                                    "status": "completed",
                                    "result": str(result)[:500],  # Truncate long results
                                    "function_id": str(func_id) if func_id else None
                                }
                                await bus.publish(
                                    f"{RESPONSE_QUEUE}",
                                    {
                                        "type": "thinking_step",
                                        "step": step,
                                        "source": "agent",
                                        "session_id": session_id,
                                        "stream": False,
                                        "done": False
                                    },
                                )
                                log.msg("Sent thinking step for function result", function_name=func_name or "unknown", session_id=session_id)
                                
                                # Clean up tracked function call
                                if func_id and func_id in active_function_calls:
                                    del active_function_calls[func_id]
                
                # Extract text content from update
                chunk = None
                
                # Use the text property which concatenates all TextContent
                if hasattr(update, 'text') and update.text:
                    chunk = update.text
                elif hasattr(update, 'contents') and update.contents:
                    # Extract text from TextContent items
                    text_parts = []
                    for content_item in update.contents:
                        content_type = None
                        if hasattr(content_item, 'type'):
                            content_type = content_item.type
                        elif isinstance(content_item, dict):
                            content_type = content_item.get('type')
                        
                        # Only extract text from TextContent, not function calls/results
                        if content_type == 'text' or (hasattr(content_item, 'text') and content_type != 'function_call' and content_type != 'function_result'):
                            if hasattr(content_item, 'text'):
                                text_parts.append(content_item.text)
                            elif isinstance(content_item, dict):
                                text_parts.append(content_item.get('text', ''))
                    
                    if text_parts:
                        chunk = ''.join(text_parts)
                
                if chunk:
                    accumulated_text += chunk
                    chunk_count += 1
                    
                    # Send streaming chunk to response queue
                    await bus.publish(
                        f"{RESPONSE_QUEUE}",
                        {
                            "content": chunk,
                            "source": "agent",
                            "session_id": session_id,
                            "stream": True,
                            "done": False
                        },
                    )
                    # log.debug("Sent streaming chunk", chunk_num=chunk_count, session_id=session_id)
            
            # Send final message indicating streaming is complete
            await bus.publish(
                f"{RESPONSE_QUEUE}",
                {
                    "content": "",
                    "source": "agent",
                    "session_id": session_id,
                    "stream": True,
                    "done": True,
                    "full_content": accumulated_text
                },
            )
            
            # Save thread with final accumulated text
            await save_thread_for_session(log, session_id, conversation_thread)
            log.msg("Streaming complete", 
                   session_id=session_id, 
                   chunks_sent=chunk_count,
                   total_length=len(accumulated_text))
            
        except AttributeError as attr_error:
            # If run_stream doesn't exist, fallback to run
            log.warning("run_stream not available, falling back to run", error=str(attr_error))
            response = await agent.run(content, thread=conversation_thread)
            resp_text = (
                json.dumps(response, default=str, ensure_ascii=False)
                if not isinstance(response, str)
                else response
            )
            await save_thread_for_session(log, session_id, conversation_thread)
            await bus.publish(
                f"{RESPONSE_QUEUE}",
                {"content": resp_text, "source": "agent", "session_id": session_id, "stream": False, "done": True},
            )
        except Exception as stream_error:
            # Handle streaming errors and fallback
            log.error("Streaming error, falling back to run", error=str(stream_error), session_id=session_id)
            response = await agent.run(content, thread=conversation_thread)
            resp_text = (
                json.dumps(response, default=str, ensure_ascii=False)
                if not isinstance(response, str)
                else response
            )
            await save_thread_for_session(log, session_id, conversation_thread)
            await bus.publish(
                f"{RESPONSE_QUEUE}",
                {"content": resp_text, "source": "agent", "session_id": session_id, "stream": False, "done": True},
            )
            
    except Exception as e:
        log.error("Error processing message", error=str(e), session_id=session_id)
        await bus.publish(
            f"{RESPONSE_QUEUE}",
            {"content": f"Error: {e}", "source": "agent", "session_id": session_id, "stream": False, "done": True},
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


