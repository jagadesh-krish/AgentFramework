import asyncio
import contextlib
import json
import logging
import os
import time
import uuid
from typing import Dict

from fastapi import APIRouter, FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from aiofiles import os as aio_os
from fastapi.staticfiles import StaticFiles
import structlog

from agentframework.service_layer.chat_handlers import RabbitMQBus, REQUEST_QUEUE, RESPONSE_QUEUE
from routes import router


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

log = get_logger()

if os.path.exists("agentframework/client"):
    app.mount(
        "/static", StaticFiles(directory="agentframework/client"), name="static"
    )

# Include routes
app.include_router(router)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    # Log request
    try:
        body_bytes = await request.body()
        body_text = body_bytes.decode("utf-8") if body_bytes else ""
    except Exception:
        body_text = "<unreadable>"

    log.info(
        "http_request",
        method=request.method,
        path=request.url.path,
        body=body_text[:500],
    )  # Limit body size

    # Process request
    try:
        response = await call_next(request)
    except Exception as e:
        process_time = round(time.time() - start_time, 3)
        log.error("http_request_failed", error=str(e), duration=process_time)
        return JSONResponse(status_code=500, content={"error": "Internal Server Error"})

    process_time = round(time.time() - start_time, 3)
    log.info(
        "http_response", status_code=response.status_code, duration=process_time
    )
    return response


connections: Dict[str, WebSocket] = {}
user_context: Dict[str, dict] = {}  # Store user-specific context
conversation_history: Dict[str, list] = {}  # Store conversation history per session: [{"role": "user", "content": "..."}, ...]
processing_status: Dict[str, bool] = {}  # Track if a session is currently processing a message


@app.websocket("/ws/chat")
async def chat_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    session_id = str(uuid.uuid4())
    connections[session_id] = websocket
    user_context[session_id] = {}  # Initialize context for the session
    conversation_history[session_id] = []  # Initialize conversation history
    processing_status[session_id] = False  # Initialize processing status
    log.msg("Websocket connection accepted", session_id=session_id)

    bus: RabbitMQBus | None = RabbitMQBus()
    consumer_task: asyncio.Task | None = None
    try:
        await bus.connect()  # type: ignore[arg-type]

        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            user_message = data.get("content", raw)
            
            # Check if already processing - block new messages
            if processing_status.get(session_id, False):
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "content": "Please wait for the current response to complete before sending another message.",
                    "session_id": session_id
                }))
                continue
            
            # Mark as processing
            processing_status[session_id] = True
            
            # Add user message to conversation history
            conversation_history[session_id].append({"role": "user", "content": user_message})
            
            payload = {
                "session_id": session_id,
                "type": data.get("type", "TextMessage"),
                "content": user_message
            }
            await bus.publish(REQUEST_QUEUE, payload)
    except WebSocketDisconnect:
        pass
    finally:
        try:
            if consumer_task is not None:
                consumer_task.cancel()
                with contextlib.suppress(Exception):
                    await consumer_task
            if bus is not None:
                await bus.close()
        except Exception:
            pass
        connections.pop(session_id, None)
        user_context.pop(session_id, None)  # Clean up context
        conversation_history.pop(session_id, None)  # Clean up history
        processing_status.pop(session_id, None)  # Clean up processing status


@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    log.info("Resto Chef Chatbot System starting up...")
    log.info("Application startup complete")
    bus = RabbitMQBus()
    await bus.connect()
    
    async def forward_responses() -> None:
            async for msg in bus.consume(f"{RESPONSE_QUEUE}"):
                session_id = msg.get("session_id")
                content = msg.get("content", "")
                is_streaming = msg.get("stream", False)
                is_done = msg.get("done", False)
                
                log.msg("Active Connections", connections=list(connections.keys()))
                websocket = connections.get(session_id)
                if websocket:
                    if is_streaming:
                        # Forward streaming chunk immediately
                        await websocket.send_text(json.dumps(msg))
                        
                        # If this is the final chunk, mark processing as complete
                        if is_done:
                            processing_status[session_id] = False
                            # Update conversation history with full content
                            if session_id in conversation_history:
                                full_content = msg.get("full_content", "")
                                conversation_history[session_id].append({"role": "assistant", "content": full_content})
                            log.msg("Streaming complete", session_id=session_id)
                    else:
                        # Non-streaming response
                        log.msg("Forwarding response to websocket", msg=msg, session_id=session_id)
                        await websocket.send_text(json.dumps(msg))
                        processing_status[session_id] = False
                        
                        # Update conversation history when response is received
                        if session_id in conversation_history:
                            conversation_history[session_id].append({"role": "assistant", "content": content})
                else:
                    log.msg("No active websocket for session", session_id=session_id)
                    # Still mark as not processing even if no connection
                    if is_done:
                        processing_status[session_id] = False

    consumer_task = asyncio.create_task(forward_responses())


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    log.info("Resto Chef Chatbot System shutting down...")

if __name__ == "__main__":
    import asyncio
    from hypercorn.asyncio import serve
    from hypercorn.config import Config

    config = Config()
    config.bind = ["0.0.0.0:8002"]
    asyncio.run(serve(app, config))