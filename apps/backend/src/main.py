from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.errors import register_exception_handlers
from src.core.config import get_settings
from src.core.logging import configure_logging
from src.core.middleware import RequestContextMiddleware
from src.db.session import init_db
from src.modules.ai.routes import router as ai_router
from src.modules.auth.routes import router as auth_router
from src.modules.daily_plans.routes import router as daily_plans_router
from src.modules.events.routes import router as events_router
from src.modules.insights.routes import router as insights_router
from src.modules.ml.routes import router as ml_router
from src.modules.health.routes import router as health_router
from src.modules.feedback.routes import router as feedback_router
from src.modules.preferences.routes import router as preferences_router
from src.modules.progress.routes import router as progress_router
from src.modules.tasks.routes import router as tasks_router


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        init_db()
        yield

    app = FastAPI(title="AI Planner API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(health_router, prefix="/api/v1", tags=["health"])
    app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(tasks_router, prefix="/api/v1/tasks", tags=["tasks"])
    app.include_router(daily_plans_router, prefix="/api/v1/daily-plans", tags=["daily-plans"])
    app.include_router(ai_router, prefix="/api/v1/ai", tags=["ai"])
    app.include_router(events_router, prefix="/api/v1/events", tags=["events"])
    app.include_router(feedback_router, prefix="/api/v1/feedback", tags=["feedback"])
    app.include_router(progress_router, prefix="/api/v1/progress", tags=["progress"])
    app.include_router(insights_router, prefix="/api/v1/insights", tags=["insights"])
    app.include_router(ml_router, prefix="/api/v1/ml", tags=["ml"])
    app.include_router(preferences_router, prefix="/api/v1/settings/preferences", tags=["preferences"])

    return app


app = create_app()
