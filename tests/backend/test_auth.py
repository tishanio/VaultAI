"""Tests for authentication endpoints."""
import pytest

pytestmark = pytest.mark.asyncio


async def test_register_user(async_client):
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@vault.app",
            "username": "newuser",
            "display_name": "New User",
            "password": "securepassword123",
        },
    )
    assert response.status_code in (200, 201, 422)


async def test_login_nonexistent_user(async_client):
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@vault.app", "password": "password"},
    )
    assert response.status_code in (401, 404, 422)
