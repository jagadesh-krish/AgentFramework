"""Route definitions for the weaver application"""
from fastapi import APIRouter, WebSocket

from agentframework.service_layer.http_handlers import serve_chat_interface, serve_chat_script, serve_logo


# Create router
router = APIRouter()

# Static file routes
@router.get("/")
async def root():
    """Serve main chat interface"""
    return await serve_chat_interface()

@router.get("/chat-script")
async def chat_script():
    """Serve chat JavaScript"""
    return await serve_chat_script()

@router.get("/chatbot-logo.png")
async def logo():
    """Serve logo"""
    return await serve_logo()

# WebSocket route
# @router.websocket("/ws/chat")
# async def chat_websocket(websocket: WebSocket):
#     """WebSocket endpoint for chat"""
#     await handle_websocket_connection(websocket)

# History routes
# @router.get("/history")
# async def history():
#     """Get chat history endpoint"""
#     return await get_chat_history()

# @router.post("/history/clear")
# async def clear_history():
#     """Clear chat history endpoint"""
#     return await clear_chat_history()
