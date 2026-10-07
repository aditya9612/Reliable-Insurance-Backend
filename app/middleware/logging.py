import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.middleware.request_id import get_request_id

logger = logging.getLogger("reliable.access")


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that emits structured logs for incoming HTTP requests.
    Includes correlation request_id, latency, client IP, method, path, and response status.
    Guarantees no sensitive credentials or passwords are leaked to log output.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()
        req_id = get_request_id() or getattr(request.state, "request_id", "unknown")
        
        # Determine client IP safely
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path

        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            
            logger.info(
                f"[{req_id}] {method} {path} - Status: {response.status_code} ({duration_ms}ms) Client: {client_ip}"
            )
            return response
        except Exception as ex:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                f"[{req_id}] {method} {path} - Unhandled Error ({duration_ms}ms) Client: {client_ip}: {type(ex).__name__}"
            )
            raise
