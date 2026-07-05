from datetime import date, timedelta
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
        "email": f"task-user-{token}@example.com",
        "password": "Password123!",
        "name": f"Task User {token}",
        "timezone": "Asia/Saigon",
    }


def _login(client: TestClient) -> None:
    credentials = _credentials()
    register_response = client.post("/api/v1/auth/register", json=credentials)
    assert register_response.status_code == 200
    login_response = client.post("/api/v1/auth/login", json={"email": credentials["email"], "password": credentials["password"]})
    assert login_response.status_code == 200


def test_task_crud_flow() -> None:
    with TestClient(app) as client:
        today = date.today()
        deadline = (today + timedelta(days=1)).isoformat()

        _login(client)

        create_response = client.post(
            "/api/v1/tasks",
            json={
                "title": "Plan weekly review",
                "description": "Prepare weekly notes",
                "estimated_duration": 45,
                "deadline": deadline,
                "priority": "high",
                "tags": ["work", "review"],
            },
        )
        assert create_response.status_code == 201
        task = create_response.json()
        assert task["title"] == "Plan weekly review"
        assert task["deadline"] == deadline
        assert task["tags"] == ["work", "review"]
        assert task["completed_at"] is None

        list_response = client.get("/api/v1/tasks")
        assert list_response.status_code == 200
        assert len(list_response.json()) == 1

        task_id = task["id"]
        update_response = client.patch(
            f"/api/v1/tasks/{task_id}",
            json={"status": "completed", "tags": ["work", "review", "done"]},
        )
        assert update_response.status_code == 200
        updated_task = update_response.json()
        assert updated_task["status"] == "completed"
        assert updated_task["completed_at"] is not None
        assert updated_task["tags"] == ["work", "review", "done"]

        delete_response = client.delete(f"/api/v1/tasks/{task_id}")
        assert delete_response.status_code == 204

        list_after_delete = client.get("/api/v1/tasks")
        assert list_after_delete.status_code == 200
        assert list_after_delete.json() == []
