import pytest
from httpx import AsyncClient
from fastapi import APIRouter
from sqlalchemy.exc import OperationalError
from app.main import app

# Create mock router to simulate specific exception conditions (avoid test_ prefix for router variable)
middleware_mock_router = APIRouter(prefix="/api/v1/mock-middleware")


@middleware_mock_router.get("/trigger-db-error")
async def trigger_db_error():
    raise OperationalError(
        statement="SELECT * FROM secret_table WHERE password='super_secret'",
        params={},
        orig=Exception("Connection refused to internal node 192.168.1.55")
    )


@middleware_mock_router.get("/trigger-unhandled-error")
async def trigger_unhandled_error():
    raise ZeroDivisionError("division by zero in test endpoint")


app.include_router(middleware_mock_router)


@pytest.mark.asyncio
async def test_request_id_generated_automatically(async_client: AsyncClient):
    """Verify that every response includes a valid X-Request-ID header."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    assert "x-request-id" in response.headers
    req_id = response.headers["x-request-id"]
    assert len(req_id) > 10


@pytest.mark.asyncio
async def test_request_id_preserved_when_supplied(async_client: AsyncClient):
    """Verify that client-provided X-Request-ID is preserved across request/response."""
    custom_id = "test-custom-trace-uuid-12345"
    response = await async_client.get(
        "/api/v1/health",
        headers={"X-Request-ID": custom_id}
    )
    assert response.status_code == 200
    assert response.headers.get("x-request-id") == custom_id


@pytest.mark.asyncio
async def test_404_error_standardized_json(async_client: AsyncClient):
    """Verify 404 responses conform to standardized JSON schema without leaking server info."""
    response = await async_client.get("/api/v1/nonexistent-route-404")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "NOT_FOUND"
    assert "x-request-id" in response.headers


@pytest.mark.asyncio
async def test_database_error_does_not_leak_sql_or_secrets(async_client: AsyncClient):
    """
    CRITICAL SECURITY TEST:
    Verify that SQLAlchemy database exceptions do NOT leak SQL statements,
    table names, passwords, or connection parameters in HTTP responses.
    """
    response = await async_client.get("/api/v1/mock-middleware/trigger-db-error")
    assert response.status_code == 500
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "DATABASE_ERROR"
    
    # Assert NO internal SQL or secret was exposed
    response_text = response.text
    assert "secret_table" not in response_text
    assert "super_secret" not in response_text
    assert "192.168.1.55" not in response_text


@pytest.mark.asyncio
async def test_unhandled_error_does_not_leak_stack_traces(async_client: AsyncClient):
    """
    CRITICAL SECURITY TEST:
    Verify that general unhandled exceptions do NOT leak stack traces,
    line numbers, or source filenames to API clients.
    """
    response = await async_client.get("/api/v1/mock-middleware/trigger-unhandled-error")
    assert response.status_code == 500
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
    
    # Assert NO traceback leaked
    response_text = response.text
    assert "Traceback" not in response_text
    assert "ZeroDivisionError" not in response_text
