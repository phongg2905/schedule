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
        "email": f"plan-user-{token}@example.com",
        "password": "Password123!",
        "name": f"Plan User {token}",
        "timezone": "Asia/Saigon",
    }


def test_rule_based_daily_plan_generation() -> None:
    with TestClient(app) as client:
        credentials = _credentials()
        assert client.post("/api/v1/auth/register", json=credentials).status_code == 200
        assert client.post("/api/v1/auth/login", json={"email": credentials["email"], "password": credentials["password"]}).status_code == 200

        assert (
            client.put(
                "/api/v1/settings/preferences",
                json={
                    "timezone": "Asia/Saigon",
                    "work_start_time": "08:00",
                    "work_end_time": "18:00",
                    "lunch_start_time": "12:00",
                    "lunch_end_time": "13:00",
                    "day_offs": [],
                    "focus_hours": ["09:00-11:00", "14:00-16:00"],
                },
            ).status_code
            == 200
        )

        client.post(
            "/api/v1/tasks",
            json={
                "title": "Urgent task",
                "description": "Do first",
                "estimated_duration": 60,
                "deadline": "2026-07-01",
                "priority": "urgent",
                "tags": ["critical"],
            },
        )
        client.post(
            "/api/v1/tasks",
            json={
                "title": "Normal task",
                "description": "Do second",
                "estimated_duration": 45,
                "deadline": "2026-07-03",
                "priority": "normal",
                "tags": ["later"],
            },
        )

        generate_response = client.post(
            "/api/v1/daily-plans/generate",
            json={"plan_date": "2026-07-01", "context_window_type": "rule_based_daily_plan", "trigger_source": "manual"},
        )
        assert generate_response.status_code == 201
        plan = generate_response.json()
        assert plan["source"] == "rule_based"
        assert plan["explanation"] is not None
        assert len(plan["items"]) == 2
        assert plan["items"][0]["label"] == "Urgent task"

        today_response = client.get("/api/v1/daily-plans/today")
        assert today_response.status_code == 200
        today_plan = today_response.json()
        assert today_plan["plan_date"] == "2026-07-01"
        assert len(today_plan["items"]) == 2
