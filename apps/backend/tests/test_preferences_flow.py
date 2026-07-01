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
        "email": f"prefs-user-{token}@example.com",
        "password": "Password123!",
        "name": f"Prefs User {token}",
        "timezone": "Asia/Saigon",
    }


def test_preferences_flow() -> None:
    with TestClient(app) as client:
        credentials = _credentials()
        assert client.post("/api/v1/auth/register", json=credentials).status_code == 200
        assert client.post("/api/v1/auth/login", json={"email": credentials["email"], "password": credentials["password"]}).status_code == 200

        get_response = client.get("/api/v1/settings/preferences")
        assert get_response.status_code == 200
        assert get_response.json()["timezone"] == "Asia/Saigon"

        update_response = client.put(
            "/api/v1/settings/preferences",
            json={
                "timezone": "Asia/Ho_Chi_Minh",
                "work_start_time": "08:30",
                "work_end_time": "17:30",
                "lunch_start_time": "12:00",
                "lunch_end_time": "13:00",
                "day_offs": ["Sunday"],
                "focus_hours": ["09:00-11:00", "14:00-16:00"],
            },
        )
        assert update_response.status_code == 200
        body = update_response.json()
        assert body["timezone"] == "Asia/Ho_Chi_Minh"
        assert body["work_start_time"] == "08:30"
        assert body["day_offs"] == ["Sunday"]
        assert body["focus_hours"] == ["09:00-11:00", "14:00-16:00"]
