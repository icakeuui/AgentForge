import uuid
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from backend.core.logging import (
    logger,
    set_auth_mode,
    set_path,
    set_request_id,
    set_resource_id,
    set_resource_type,
    set_team_id,
    set_user_id,
)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Extract or generate request_id
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        set_request_id(request_id)
        set_team_id("")
        set_user_id("")
        set_auth_mode("unknown")
        set_path(request.url.path)
        set_resource_type("")
        set_resource_id("")
        request.state.request_id = request_id
        
        # Log request entry
        logger.info(f"Incoming request: {request.method} {request.url}")
        
        start_time = time.time()
        # Exceptions will bubble up to global_exception_handler
        response = await call_next(request)
        
        process_time = time.time() - start_time
        logger.info(
            f"Completed request: {request.method} {request.url} - "
            f"Status: {response.status_code} - Duration: {process_time:.4f}s"
        )
        
        # Inject request_id into response headers
        response.headers["X-Request-ID"] = request_id
        return response
