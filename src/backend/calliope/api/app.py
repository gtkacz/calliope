from calliope.api.errors import register_error_handlers
from calliope.api.routes import chat, documents, profiles, search, sessions, workspaces
from calliope.config import Settings
from fastapi import FastAPI


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or Settings()
    app = FastAPI(title=resolved_settings.api_title)
    app.include_router(workspaces.router)
    app.include_router(profiles.router)
    app.include_router(search.router)
    app.include_router(chat.router)
    app.include_router(documents.router)
    app.include_router(sessions.router)
    register_error_handlers(app)
    app.state.settings = resolved_settings
    return app
