"""HTTP handlers for REST endpoints"""
import json
import os
import structlog
from typing import Any, Dict, List
from fastapi import HTTPException
from fastapi.responses import FileResponse, JSONResponse
import aiofiles

logger = structlog.get_logger()

# Static file handlers
async def serve_chat_interface():
    """Serve main chat interface"""
    chat_file = "agentframework/client/index.html"
    if os.path.exists(chat_file):
        return FileResponse(chat_file, media_type="text/html")
    else:
        return JSONResponse({"message": "Chat interface not found"}, status_code=404)

async def serve_chat_script():
    """Serve chat JavaScript"""
    js_file = "agentframework/client/chat.js"
    if os.path.exists(js_file):
        return FileResponse(js_file, media_type="text/javascript")
    else:
        return JSONResponse({"message": "Chat script not found"}, status_code=404)

async def serve_logo():
    """Serve logo"""
    logo_file = "agentframework/client/chatbot-logo.png"
    if os.path.exists(logo_file):
        return FileResponse(logo_file, media_type="image/png")
    else:
        return JSONResponse({"message": "Logo not found"}, status_code=404)