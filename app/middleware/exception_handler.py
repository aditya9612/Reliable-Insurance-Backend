import logging
from typing import Union
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError
from app.middleware.request_id import get_request_id

logger = logging.getLogger("reliable.error")


def create_error_response(
    status_code: int,
    code: str,
    message: str,
    details: Union[dict, list, str, None] = None,
    headers: Union[dict, None] = None,
) -> JSONResponse:
    """
    Standardizes error responses across all endpoints.
    Format:
    {
        "success": false,
        "error": {
            "code": "...",
            "message": "...",
            "details": ...
        }
    }
    """
    response_headers = headers.copy() if headers else {}
    req_id = get_request_id()
    if req_id:
        response_headers["X-Request-ID"] = req_id

    error_body = {
        "code": code,
        "message": message,
    }
    if details is not None:
        error_body["details"] = details

    return JSONResponse(
        status_code=status_code,
        content={"success": False, "error": error_body},
        headers=response_headers,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """
    Registers centralized exception handlers on the FastAPI application instance.
    Guarantees no raw SQL, stack traces, credentials, or secrets leak to API consumers.
    """

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        req_id = get_request_id()
        logger.warning(f"[{req_id}] HTTP {exc.status_code}: {exc.detail} on {request.method} {request.url.path}")
        
        # Standardize code from status code
        code_map = {
            status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
            status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
            status.HTTP_403_FORBIDDEN: "FORBIDDEN",
            status.HTTP_404_NOT_FOUND: "NOT_FOUND",
            status.HTTP_405_METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
            status.HTTP_409_CONFLICT: "CONFLICT",
            status.HTTP_422_UNPROCESSABLE_ENTITY: "UNPROCESSABLE_ENTITY",
            status.HTTP_429_TOO_MANY_REQUESTS: "RATE_LIMIT_EXCEEDED",
        }
        error_code = code_map.get(exc.status_code, "HTTP_ERROR")
        return create_error_response(
            status_code=exc.status_code,
            code=error_code,
            message=str(exc.detail),
            headers=getattr(exc, "headers", None)
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        req_id = get_request_id()
        # Clean validation errors to prevent leaking internal structures
        formatted_errors = []
        for err in exc.errors():
            formatted_errors.append({
                "field": " -> ".join(str(loc) for loc in err.get("loc", [])),
                "message": err.get("msg", "Invalid value"),
                "type": err.get("type", "value_error"),
            })
        logger.info(f"[{req_id}] Validation error on {request.method} {request.url.path}: {len(formatted_errors)} issue(s)")
        
        return create_error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="VALIDATION_ERROR",
            message="Input validation failed for one or more fields",
            details=formatted_errors,
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
        req_id = get_request_id()
        # Log the full database error internally for engineering diagnostics
        logger.error(f"[{req_id}] Database error on {request.method} {request.url.path}: {type(exc).__name__}", exc_info=True)
        
        # NEVER leak SQL queries, table names, or database credentials to clients
        return create_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="DATABASE_ERROR",
            message="A database error occurred while processing the request. Please try again or contact support.",
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        req_id = get_request_id()
        logger.critical(f"[{req_id}] Unhandled exception on {request.method} {request.url.path}: {type(exc).__name__}", exc_info=True)
        
        # NEVER leak stack traces or internal filenames to clients
        return create_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected internal server error occurred.",
        )
