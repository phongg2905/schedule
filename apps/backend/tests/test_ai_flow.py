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
        "email": f"ai-user-{token}@example.com",
        "password": "Password123!",
        "name": f"AI User {token}",
        "timezone": "Asia/Saigon",
    }


def test_ai_daily_plan_generation_and_explanation() -> None:
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
                "title": "Write proposal",
                "description": "Draft the weekly proposal",
                "estimated_duration": 45,
                "deadline": "2026-07-01",
                "priority": "high",
                "tags": ["writing"],
            },
        )
        client.post(
            "/api/v1/tasks",
            json={
                "title": "Reply emails",
                "description": "Clear inbox",
                "estimated_duration": 30,
                "deadline": "2026-07-02",
                "priority": "normal",
                "tags": ["admin"],
            },
        )

        generate_response = client.post(
            "/api/v1/ai/generate-daily-plan",
            json={"plan_date": "2026-07-01", "context_window_type": "ai_generation", "trigger_source": "manual"},
        )
        assert generate_response.status_code == 200
        generated_plan = generate_response.json()
        assert generated_plan["source"] == "ai"
        assert generated_plan["explanation"] is not None
        assert len(generated_plan["items"]) == 2

        explain_response = client.post(
            "/api/v1/ai/explain",
            json={"daily_plan_id": generated_plan["id"], "question": "Why is this order?"},
        )
        assert explain_response.status_code == 200
        assert explain_response.json()["explanation"]
