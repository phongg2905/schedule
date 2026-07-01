from pathlib import Path
from uuid import uuid4
import sys

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.main import app


def _credentials() -> dict[str, str]:
    token = uuid4().hex[:8]
    return {
        "email": f"user-{token}@example.com",
        "password": "Password123!",
        "name": f"User {token}",
        "timezone": "Asia/Saigon",
    }


def test_auth_flow_register_login_refresh_logout() -> None:
    credentials = _credentials()

    with TestClient(app) as client:
        register_response = client.post("/api/v1/auth/register", json=credentials)
        assert register_response.status_code == 200
        assert register_response.json()["user"]["email"] == credentials["email"]

        login_response = client.post("/api/v1/auth/login", json={"email": credentials["email"], "password": credentials["password"]})
        assert login_response.status_code == 200
        first_refresh_token = client.cookies.get("refresh_token")
        assert first_refresh_token

        me_response = client.get("/api/v1/auth/me")
        assert me_response.status_code == 200
        assert me_response.json()["email"] == credentials["email"]

        refresh_response = client.post("/api/v1/auth/refresh")
        assert refresh_response.status_code == 200
        second_refresh_token = client.cookies.get("refresh_token")
        assert second_refresh_token
        assert second_refresh_token != first_refresh_token

        logout_response = client.post("/api/v1/auth/logout")
        assert logout_response.status_code == 200

        me_after_logout = client.get("/api/v1/auth/me")
        assert me_after_logout.status_code == 401


def test_protected_route_requires_authentication() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/tasks")

        assert response.status_code == 401
