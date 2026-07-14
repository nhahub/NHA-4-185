import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _get_admin_headers(client: AsyncClient) -> dict:
    """Register an admin and return auth headers."""
    await client.post("/api/v1/auth/register", json={
        "email": "admin_test@test.com",
        "password": "Admin1234!",
        "full_name": "Admin Tester",
        "role": "admin",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "admin_test@test.com",
        "password": "Admin1234!",
    })
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_list_users_requires_admin(client: AsyncClient, auth_headers: dict):
    """Analyst role should be denied."""
    resp = await client.get("/api/v1/admin/users", headers=auth_headers)
    assert resp.status_code == 403


async def test_list_users_as_admin(client: AsyncClient):
    headers = await _get_admin_headers(client)
    resp = await client.get("/api/v1/admin/users", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 1  # at least the admin itself


async def test_get_user_not_found(client: AsyncClient):
    headers = await _get_admin_headers(client)
    resp = await client.get(
        "/api/v1/admin/users/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )
    assert resp.status_code == 404


async def test_audit_logs_requires_admin(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/admin/audit-logs", headers=auth_headers)
    assert resp.status_code == 403


async def test_audit_logs_as_admin(client: AsyncClient):
    headers = await _get_admin_headers(client)
    resp = await client.get("/api/v1/admin/audit-logs", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_audit_logs_filter_by_action(client: AsyncClient):
    headers = await _get_admin_headers(client)
    resp = await client.get("/api/v1/admin/audit-logs?action=LOGIN", headers=headers)
    assert resp.status_code == 200


async def test_update_user_role(client: AsyncClient):
    admin_headers = await _get_admin_headers(client)

    # Create a target user
    await client.post("/api/v1/auth/register", json={
        "email": "target_user@test.com",
        "password": "Target1234!",
        "full_name": "Target User",
        "role": "analyst",
    })

    # Fetch to get ID
    users_resp = await client.get("/api/v1/admin/users", headers=admin_headers)
    target = next((u for u in users_resp.json() if u["email"] == "target_user@test.com"), None)
    assert target is not None

    # Update role
    resp = await client.patch(
        f"/api/v1/admin/users/{target['id']}",
        json={"role": "viewer"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "viewer"
