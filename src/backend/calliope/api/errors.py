from calliope.domain.errors import AppError
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        payload = {
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        }
        return JSONResponse(
            status_code=exc.status_code,
            content=jsonable_encoder(payload),
        )
