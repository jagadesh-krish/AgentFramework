import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv
from typing import Callable, Awaitable

from agent_framework.azure import AzureOpenAIChatClient
from agent_framework import (
    AgentRunContext,
    FunctionInvocationContext,
    ChatContext,
    agent_middleware,
    function_middleware,
    chat_middleware
)
import structlog

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

log = get_logger()


# ============================================================================
# MIDDLEWARE 1: TIMING (Agent Middleware)
# ============================================================================

@agent_middleware
async def timing_middleware(
    context: AgentRunContext,
    next: Callable[[AgentRunContext], Awaitable[None]],
) -> None:
    """Tracks execution time for entire agent run."""
    global log  # Ensure the global log variable is used
    log = log.bind(func=timing_middleware.__qualname__)
    start_time = datetime.now()
    
    log.msg(f"\n⏱️  [TIMING] Started at {start_time.strftime('%H:%M:%S')}")
    
    # Execute agent
    await next(context)
    
    # Calculate duration
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    log.msg(f"⏱️  [TIMING] Completed in {duration:.2f} seconds")


# ============================================================================
# MIDDLEWARE 2: SECURITY (Agent Middleware)
# ============================================================================

@agent_middleware
async def security_middleware(
    context: AgentRunContext,
    next: Callable[[AgentRunContext], Awaitable[None]],
) -> None:
    """Blocks requests containing sensitive keywords."""
    global log  # Ensure the global log variable is used
    log = log.bind(func=security_middleware.__qualname__)
    # Check the last message for blocked content
    if context.messages:
        last_message = context.messages[-1]
        if hasattr(last_message, 'contents'):
            for content in last_message.contents:
                if hasattr(content, 'text'):
                    text = str(content.text).lower()
                    
                    # List of blocked keywords
                    blocked_keywords = ["secret", "hack", "exploit", "bypass"]
                    
                    for keyword in blocked_keywords:
                        if keyword in text:
                            log.msg(f"\n🚫 [SECURITY] Request BLOCKED! Detected: '{keyword}'")
                            log.msg(f"🚫 [SECURITY] This request contains sensitive content and cannot be processed.")
                            context.terminate = True
                            return
    
    # If safe, continue
    await next(context)


# ============================================================================
# MIDDLEWARE 3: FUNCTION LOGGER (Function Middleware)
# ============================================================================

@function_middleware
async def function_logger_middleware(
    context: FunctionInvocationContext,
    next: Callable[[FunctionInvocationContext], Awaitable[None]],
) -> None:
    """Logs every function/tool call with arguments and results."""
    global log  # Ensure the global log variable is used
    log = log.bind(func=function_logger_middleware.__qualname__)
    log.msg(f"\n🔧 [FUNCTION] Calling tool: {context.function.name}")
    log.msg(f"🔧 [FUNCTION] Arguments: {context.arguments}")
    
    # Execute the function
    await next(context)
    
    # Log the result
    log.msg(f"🔧 [FUNCTION] Result: {context.result}")


# ============================================================================
# MIDDLEWARE 4: TOKEN COUNTER (Chat Middleware)
# ============================================================================

@chat_middleware
async def token_counter_middleware(
    context: ChatContext,
    next: Callable[[ChatContext], Awaitable[None]],
) -> None:
    """Estimates and logs token usage for AI calls."""
    global log  # Ensure the global log variable is used
    log = log.bind(func=token_counter_middleware.__qualname__)
    # Estimate input tokens (rough: 1 token ≈ 4 characters)
    total_chars = sum(len(str(msg)) for msg in context.messages)
    estimated_input_tokens = total_chars // 4
    
    log.msg(f"\n🤖 [AI CALL] Sending request to qwen3:4b")
    log.msg(f"🤖 [AI CALL] Messages: {len(context.messages)}")
    log.msg(f"🤖 [AI CALL] Estimated input tokens: ~{estimated_input_tokens}")
    
    # Call the AI
    await next(context)
    
    # Estimate output tokens
    if context.result and hasattr(context.result, 'choices'):
        if hasattr(context.result.choices[0].message, 'content'):
            response_text = str(context.result.choices[0].message.content)
            estimated_output_tokens = len(response_text) // 4
            total_tokens = estimated_input_tokens + estimated_output_tokens
            
            log.msg(f"🤖 [AI CALL] Estimated output tokens: ~{estimated_output_tokens}")
            log.msg(f"🤖 [AI CALL] Total estimated tokens: ~{total_tokens}")
