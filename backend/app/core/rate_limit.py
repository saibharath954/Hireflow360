"""
Rate limiting decorator for API endpoints
"""

import time
from functools import wraps
from typing import Dict, Tuple
from fastapi import HTTPException, Request
from starlette import status

# Simple in-memory rate limiter (use Redis in production)
_rate_limit_store: Dict[str, Tuple[int, float]] = {}

def rate_limiter(limit: int = 5, window: int = 60):
    """
    Decorator to limit requests per window (seconds)
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Use IP address as identifier
            ip = request.client.host if request.client else "unknown"
            key = f"{ip}:{func.__name__}"
            
            current_time = time.time()
            request_count, first_request_time = _rate_limit_store.get(key, (0, current_time))
            
            # Reset if window has passed
            if current_time - first_request_time > window:
                request_count = 0
                first_request_time = current_time
            
            # Check if limit exceeded
            if request_count >= limit:
                retry_after = int(window - (current_time - first_request_time))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                    headers={"Retry-After": str(retry_after)}
                )
            
            # Update count
            _rate_limit_store[key] = (request_count + 1, first_request_time)
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator