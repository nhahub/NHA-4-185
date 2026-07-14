import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_trend_default_7_days(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/analytics/trend", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 7
    for point in data:
        assert "day" in point
        assert "total" in point
        assert "fraud" in point
        assert "fraud_rate" in point
        assert isinstance(point["total"], int)
        assert isinstance(point["fraud"], int)
        assert 0.0 <= point["fraud_rate"] <= 1.0


async def test_trend_custom_days(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/analytics/trend?days=30", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 30


async def test_trend_invalid_days(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/analytics/trend?days=0", headers=auth_headers)
    assert resp.status_code == 422

    resp = await client.get("/api/v1/analytics/trend?days=91", headers=auth_headers)
    assert resp.status_code == 422


async def test_confusion_matrix(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/analytics/confusion-matrix", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "tp" in data
    assert "tn" in data
    assert "fp" in data
    assert "fn" in data
    assert "total" in data
    # All counts should be non-negative integers
    for key in ["tp", "tn", "fp", "fn", "total"]:
        assert isinstance(data[key], int)
        assert data[key] >= 0


async def test_trend_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/analytics/trend")
    assert resp.status_code == 403


async def test_confusion_matrix_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/analytics/confusion-matrix")
    assert resp.status_code == 403
