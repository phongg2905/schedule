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
        "email": f"progress-user-{token}@example.com",
        "password": "Password123!",
        "name": f"Progress User {token}",
        "timezone": "Asia/Saigon",
    }


def test_daily_progress_ai_adjustment_and_insight_flow() -> None:
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

        first_task = client.post(
            "/api/v1/tasks",
            json={
                "title": "Finish quarterly report",
                "description": "Draft and review",
                "estimated_duration": 60,
                "deadline": "2026-07-01",
                "priority": "urgent",
                "tags": ["work"],
            },
        ).json()
        second_task = client.post(
            "/api/v1/tasks",
            json={
                "title": "Prepare standup notes",
                "description": "Short update",
                "estimated_duration": 30,
                "deadline": "2026-07-02",
                "priority": "normal",
                "tags": ["work"],
            },
        ).json()

        generate_response = client.post(
            "/api/v1/daily-plans/generate",
            json={"plan_date": "2026-07-01", "context_window_type": "rule_based_daily_plan", "trigger_source": "manual"},
        )
        assert generate_response.status_code == 201
        plan = generate_response.json()

        complete_response = client.post(f"/api/v1/progress/tasks/{first_task['id']}/complete", json={"reason": "Done"})
        assert complete_response.status_code == 200
        assert complete_response.json()["task"]["status"] == "completed"

        complete_again_response = client.post(f"/api/v1/progress/tasks/{first_task['id']}/complete", json={"reason": "Done again"})
        assert complete_again_response.status_code == 200
        assert complete_again_response.json()["task"]["status"] == "completed"

        delay_response = client.post(
            f"/api/v1/progress/tasks/{second_task['id']}/delay",
            json={"new_deadline": "2026-07-03", "reason": "Need more time"},
        )
        assert delay_response.status_code == 200
        assert delay_response.json()["task"]["status"] == "deferred"

        delay_after_complete_response = client.post(
            f"/api/v1/progress/tasks/{first_task['id']}/delay",
            json={"new_deadline": "2026-07-04", "reason": "Should fail"},
        )
        assert delay_after_complete_response.status_code == 409

        adjustment_response = client.post(
            "/api/v1/ai/adjust",
            json={"daily_plan_id": plan["id"], "change_description": "I have a meeting at 15:00"},
        )
        assert adjustment_response.status_code == 200
        assert adjustment_response.json()["explanation"]

        insight_response = client.get("/api/v1/insights/today")
        assert insight_response.status_code == 200
        insight = insight_response.json()
        assert insight["completed_tasks"] == 1
        assert insight["deferred_tasks"] == 1
        assert insight["top_focus"]
        assert insight["highlights"]

        today_plan_response = client.get("/api/v1/daily-plans/today")
        assert today_plan_response.status_code == 200
        assert today_plan_response.json()["status"] == "completed"

        events_response = client.get("/api/v1/events")
        assert events_response.status_code == 200
        event_types = {event["event_type"] for event in events_response.json()}
        assert "task_completed" in event_types
        assert "task_delayed" in event_types
        assert "day_summary_generated" in event_types
        assert "ai_adjustment_created" in event_types
