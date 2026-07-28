"""Tests for the ML monitoring API endpoint."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4
import sys

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.db.models import MLPredictionLog, User, DailyPlan, Task, new_id
from src.db.session import get_db
from src.main import app


def _credentials() -> dict[str, str]:
    token = uuid4().hex[:8]
    return {
        "email": f"ml-mon-{token}@example.com",
        "password": "Password123!",
        "name": f"ML Mon User {token}",
        "timezone": "Asia/Saigon",
    }


def test_ml_monitoring_returns_empty_when_no_data() -> None:
    """Call /ml/monitoring before any ML predictions — expect empty stats."""
    with TestClient(app) as client:
        creds = _credentials()
        assert client.post("/api/v1/auth/register", json=creds).status_code == 200
        assert client.post("/api/v1/auth/login", json={
            "email": creds["email"], "password": creds["password"],
        }).status_code == 200

        resp = client.get("/api/v1/ml/monitoring")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_predictions"] == 0
        assert data["recent_7d_predictions"] == 0
        assert data["confidence_distribution"] == []
        assert data["outcome_breakdown"] == []


def test_ml_monitoring_returns_stats() -> None:
    """Seed MLPredictionLog data and verify the monitoring response."""
    with TestClient(app) as client:
        creds = _credentials()
        assert client.post("/api/v1/auth/register", json=creds).status_code == 200
        login_resp = client.post("/api/v1/auth/login", json={
            "email": creds["email"], "password": creds["password"],
        })
        assert login_resp.status_code == 200

        # Grab the user ID from the app state so we can seed data
        # Use the same db session as the app
        db = get_db()
        try:
            user = db.query(User).filter(User.email == creds["email"]).one()
            uid = user.id

            now = datetime.now(UTC)
            plan = DailyPlan(id=new_id(), user_id=uid,
                             plan_date=(now.date() + timedelta(days=1)).isoformat(),
                             status="draft", source="ml_boosted")
            task = Task(id=new_id(), user_id=uid, title="Monitored Task",
                        task_type="scheduled")
            db.add(plan)
            db.add(task)
            db.flush()

            # Seed predictions with varied scores and outcomes
            preds = [
                MLPredictionLog(user_id=uid, plan_id=plan.id, task_id=task.id,
                               prediction_score=0.92, confidence_band="high",
                               model_version="v1", model_type="LR",
                               outcome="completed",
                               outcome_updated_at=now - timedelta(hours=1),
                               created_at=now - timedelta(hours=24)),
                MLPredictionLog(user_id=uid, plan_id=plan.id, task_id=task.id,
                               prediction_score=0.78, confidence_band="high",
                               model_version="v1", model_type="LR",
                               outcome="pending",
                               created_at=now - timedelta(hours=24)),
                MLPredictionLog(user_id=uid, plan_id=plan.id, task_id=task.id,
                               prediction_score=0.55, confidence_band="medium",
                               model_version="v1", model_type="LR",
                               outcome="deferred",
                               created_at=now - timedelta(hours=24)),
                MLPredictionLog(user_id=uid, plan_id=plan.id, task_id=task.id,
                               prediction_score=0.30, confidence_band="low",
                               model_version="v2", model_type="XGB",
                               outcome="skipped",
                               created_at=now - timedelta(hours=24)),
            ]
            db.add_all(preds)
            db.commit()
        finally:
            db.close()

        # Call monitoring endpoint
        resp = client.get("/api/v1/ml/monitoring")
        assert resp.status_code == 200
        data = resp.json()

        # Totals
        assert data["total_predictions"] == 4
        assert data["recent_7d_predictions"] == 4

        # Confidence distribution
        bands = {b["band"]: b for b in data["confidence_distribution"]}
        assert bands["high"]["count"] == 2
        assert bands["medium"]["count"] == 1
        assert bands["low"]["count"] == 1

        # Outcome breakdown
        outcomes = {o["outcome"]: o for o in data["outcome_breakdown"]}
        assert outcomes["completed"]["count"] == 1
        assert outcomes["pending"]["count"] == 1
        assert outcomes["deferred"]["count"] == 1
        assert outcomes["skipped"]["count"] == 1

        # High-confidence completion rate: 1 completed out of 2 high = 50%
        assert data["high_confidence_completion_rate"] == 50.0

        # Score trends
        assert data["score_trend_recent"] is not None
        assert data["score_trend_all"] is not None
        assert data["score_trend_all"]["count"] == 4

        # Drift
        assert data["drift"] is not None

        # Model versions
        versions = {v["model_version"]: v for v in data["model_versions"]}
        assert versions["v1"]["count"] == 3
        assert versions["v2"]["count"] == 1

        # Unauthorized access
        resp_noauth = client.get("/api/v1/ml/monitoring")
        # Should still work since cookie is maintained by TestClient
        assert resp_noauth.status_code == 200


def test_ml_monitoring_requires_auth() -> None:
    """Call /ml/monitoring without authentication — expect 401."""
    with TestClient(app) as client:
        # Clear cookies by creating a new client
        resp = TestClient(app).get("/api/v1/ml/monitoring")
        assert resp.status_code == 401
