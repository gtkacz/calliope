import logging
from pathlib import Path

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


def _warn_if_browse_root_empty(browse_root: str | None) -> None:
    """A configured-but-empty browse root is the classic containerized trap: the
    bind mount points at an empty dir, so the picker/indexer/editor see nothing.
    An unset root falls back to the user's home and needs no warning."""
    if not browse_root:
        return
    try:
        if any(Path(browse_root).resolve(strict=True).iterdir()):
            return
    except OSError:
        pass  # Missing or not a directory — treat as empty and warn.
    logger.warning(
        "CALLIOPE_BROWSE_ROOT=%s is empty or missing; the folder picker, indexer, "
        "and file editor will see no files. In a container, set CALLIOPE_BROWSE_ROOT "
        "to a host directory that is bind-mounted in (e.g. your home) and restart.",
        browse_root,
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or Settings()
    if resolved_settings.versioning_enabled and not VersioningService.is_available():
        logger.warning(
            "CALLIOPE_VERSIONING_ENABLED is set but the 'git' binary was not found; "
            "file version history will be inactive.",
        )
    _warn_if_browse_root_empty(resolved_settings.browse_root)
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
