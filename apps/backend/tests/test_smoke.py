from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.main import create_app
from src.modules.health.routes import health, ready


def test_health_endpoints_return_expected_payloads() -> None:
    assert health() == {"status": "ok"}
    assert ready() == {"status": "ready"}


def test_app_registers_core_routes() -> None:
    app = create_app()
    routes = {route.path for route in app.routes}

    assert "/api/v1/health" in routes
    assert "/api/v1/health/ready" in routes
    assert "/api/v1/auth/login" in routes
    assert "/api/v1/tasks" in routes
