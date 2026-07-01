from collections.abc import Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, error_code: str, message: str, status_code: int = 400) -> None:
        self.error_code = error_code
        self.message = message
        self.status_code = status_code


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error_code": exc.error_code, "message": exc.message},
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(_: Request, __: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"error_code": "INTERNAL_SERVER_ERROR", "message": "Unexpected server error"},
        )
