import logging

from calliope.api.errors import register_error_handlers
from calliope.api.routes import (
    chat,
    documents,
    editor,
    filesystem,
    profiles,
    search,
    sessions,
    workspaces,
)
from calliope.config import Settings
from calliope.services.versioning import VersioningService
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or Settings()
    if resolved_settings.versioning_enabled and not VersioningService.is_available():
        logger.warning(
            "CALLIOPE_VERSIONING_ENABLED is set but the 'git' binary was not found; "
            "file version history will be inactive.",
        )
    app = FastAPI(title=resolved_settings.api_title)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(workspaces.router)
    app.include_router(profiles.router)
    app.include_router(search.router)
    app.include_router(chat.router)
    app.include_router(documents.router)
    app.include_router(sessions.router)
    app.include_router(filesystem.router)
    app.include_router(editor.router)
    register_error_handlers(app)
    app.state.settings = resolved_settings
    return app
