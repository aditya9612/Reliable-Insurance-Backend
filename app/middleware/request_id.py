import uuid
from contextvars import ContextVar
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variable to hold the current request ID across async tasks
request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    """Returns the current request ID from context."""
    return request_id_ctx_var.get()


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware to ensure every request has a unique correlation ID (X-Request-ID).
    If supplied by the client, it is preserved (if alphanumeric/UUID); otherwise, a new UUID4 is generated.
    The request ID is added to response headers and set in task context for logging.
    """
    HEADER_NAME = "X-Request-ID"

    async def dispatch(self, request: Request, call_next) -> Response:
        incoming_id = request.headers.get(self.HEADER_NAME)
        
        # Validate or generate request ID
        if incoming_id and len(incoming_id) <= 64 and incoming_id.replace("-", "").isalnum():
            req_id = incoming_id
        else:
            req_id = str(uuid.uuid4())

        # Set context variable for structured logging
        token = request_id_ctx_var.set(req_id)
        request.state.request_id = req_id

        try:
            response = await call_next(request)
            response.headers[self.HEADER_NAME] = req_id
            return response
        finally:
            request_id_ctx_var.reset(token)
