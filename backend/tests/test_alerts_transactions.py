import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


# ─── Alert Tests ─────────────────────────────────────────────────────────────

async def test_list_alerts_authenticated(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/alerts", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_list_alerts_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/v1/alerts")
    assert resp.status_code == 403


async def test_list_alerts_filter_by_status(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/alerts?status=open", headers=auth_headers)
    assert resp.status_code == 200
    for alert in resp.json():
        assert alert["status"] == "open"


async def test_list_alerts_filter_by_severity(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/alerts?severity=critical", headers=auth_headers)
    assert resp.status_code == 200
    for alert in resp.json():
        assert alert["severity"] == "critical"


async def test_get_alert_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.get(
        "/api/v1/alerts/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
    )
    assert resp.status_code == 404


async def test_update_alert_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.put(
        "/api/v1/alerts/00000000-0000-0000-0000-000000000000",
        json={"status": "resolved"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


# ─── Transaction Tests ────────────────────────────────────────────────────────

async def test_list_transactions_authenticated(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/transactions", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_transaction_stats(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/transactions/stats", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "fraud_count" in data
    assert "fraud_rate" in data
    assert "avg_amount" in data


async def test_get_transaction_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.get(
        "/api/v1/transactions/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
    )
    assert resp.status_code == 404


async def test_delete_transaction_requires_admin(client: AsyncClient, auth_headers: dict):
    # analyst should get 403
    resp = await client.delete(
        "/api/v1/transactions/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
    )
    assert resp.status_code == 403


async def test_list_transactions_fraud_filter(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/transactions?fraud_only=true", headers=auth_headers)
    assert resp.status_code == 200


async def test_list_transactions_amount_filter(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/transactions?amount_min=10&amount_max=500", headers=auth_headers)
    assert resp.status_code == 200


# ─── Analytics Tests ──────────────────────────────────────────────────────────

async def test_dashboard_authenticated(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/analytics/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_transactions" in data
    assert "fraud_rate" in data
    assert "open_alerts" in data


async def test_list_models_authenticated(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/models", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
