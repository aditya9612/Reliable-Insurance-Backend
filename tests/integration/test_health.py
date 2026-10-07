import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(async_client: AsyncClient):
    """Verify application root endpoint provides basic health status."""
    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert data["app"] == "Reliable Assurance Backend"


@pytest.mark.asyncio
async def test_health_liveness_endpoint(async_client: AsyncClient):
    """
    Verify /api/v1/health liveness probe.
    Must return 200 OK without requiring authentication.
    """
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "x-request-id" in response.headers


@pytest.mark.asyncio
async def test_readiness_endpoint_structure_and_safety(async_client: AsyncClient):
    """
    Verify /api/v1/ready readiness probe.
    Confirms local database and Redis connectivity reporting.
    CRITICAL CHECK: Verifies runtime database is NEVER 'brahmainsurance'.
    """
    response = await async_client.get("/api/v1/ready")
    assert response.status_code in [200, 503]
    data = response.json()
    
    assert "status" in data
    assert "components" in data
    assert "database" in data["components"]
    assert "redis" in data["components"]

    # Verify database component details
    db_info = data["components"]["database"]
    assert db_info["database_name"] != "brahmainsurance"
    
    if response.status_code == 200:
        assert data["status"] == "ready"
        assert db_info["status"] == "connected"
        assert db_info["database_name"] == "reliable_insurance_dev"
