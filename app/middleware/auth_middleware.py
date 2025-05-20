from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Callable, Awaitable
import logging
from app.core.auth import is_authenticated

logger = logging.getLogger(__name__)

async def auth_middleware(
    request: Request, 
    call_next: Callable[[Request], Awaitable[JSONResponse]]
) -> JSONResponse:
    """
    Middleware to check authentication for protected routes.
    """
    # Skip authentication for all routes except chat
    # Note: We're handling authentication in the chat handler itself
    # This middleware is just a safety net for any future protected routes
    if request.url.path != "/chat" or request.method == "OPTIONS":
        return await call_next(request)
    
    # For chat endpoint, we'll handle authentication in the handler
    # So we'll just pass through here
    return await call_next(request) 