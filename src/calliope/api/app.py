from fastapi import FastAPI

from calliope.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or Settings()
    app = FastAPI(title=resolved_settings.api_title)
    app.state.settings = resolved_settings
    return app
