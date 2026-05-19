from fastapi import FastAPI

from calliope.api.errors import register_error_handlers
from calliope.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or Settings()
    app = FastAPI(title=resolved_settings.api_title)
    register_error_handlers(app)
    app.state.settings = resolved_settings
    return app
