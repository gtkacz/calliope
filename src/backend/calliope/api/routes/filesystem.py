from pathlib import Path
from typing import Annotated

from calliope.api.dependencies import get_db_session, get_settings
from calliope.config import Settings
from calliope.domain.errors import AppError
from calliope.domain.schemas import (
    DirectoryListing,
    FileContent,
    FileHistory,
    FileRestoreRequest,
    FileWriteRequest,
)
from calliope.repositories.workspaces import WorkspaceRepository
from calliope.services.filesystem import FilesystemService
from calliope.services.versioning import VersioningService
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

router = APIRouter()


def _versioning_for_path(
    settings: Settings,
    session: Session,
    raw_path: str,
) -> VersioningService | None:
    """Resolve the version store for a path, honoring the global flag, git
    availability, and the owning workspace's tri-state toggle. Returns None when
    versioning should not apply (so callers fall back to a plain write)."""
    if not settings.versioning_enabled:
        return None
    if not VersioningService.is_available():
        return None
    try:
        resolved = Path(raw_path).resolve()
    except OSError:
        return None
    workspace = WorkspaceRepository(session).find_by_path(str(resolved))
    if workspace is None:
        return None
    # NULL inherits the (enabled) global default; only an explicit False disables.
    if workspace.versioning_enabled is False:
        return None
    return VersioningService(root_path=workspace.root_path)


@router.get("/v1/filesystem/list", response_model=DirectoryListing)
def list_directory(
    settings: Annotated[Settings, Depends(get_settings)],
    path: str | None = Query(default=None),
    include_files: bool = Query(default=False),
) -> DirectoryListing:
    return FilesystemService(browse_root=settings.browse_root).list_directory(
        path, include_files=include_files
    )


@router.get("/v1/filesystem/read", response_model=FileContent)
def read_file(
    settings: Annotated[Settings, Depends(get_settings)],
    path: str = Query(),
) -> FileContent:
    return FilesystemService(browse_root=settings.browse_root).read_file(path)


@router.put("/v1/filesystem/write", response_model=FileContent)
def write_file(
    settings: Annotated[Settings, Depends(get_settings)],
    session: Annotated[Session, Depends(get_db_session)],
    body: FileWriteRequest,
) -> FileContent:
    versioning = _versioning_for_path(settings, session, body.path)
    return FilesystemService(browse_root=settings.browse_root).write_file(
        body.path, body.content, cause=body.cause, versioning=versioning
    )


@router.get("/v1/filesystem/history", response_model=FileHistory)
def file_history(
    settings: Annotated[Settings, Depends(get_settings)],
    session: Annotated[Session, Depends(get_db_session)],
    path: str = Query(),
) -> FileHistory:
    versioning = _versioning_for_path(settings, session, path)
    if versioning is None:
        return FileHistory(path=path, versions=[])
    resolved = Path(path).resolve()
    return FileHistory(path=str(resolved), versions=versioning.history(resolved))


@router.post("/v1/filesystem/restore", response_model=FileContent)
def restore_file(
    settings: Annotated[Settings, Depends(get_settings)],
    session: Annotated[Session, Depends(get_db_session)],
    body: FileRestoreRequest,
) -> FileContent:
    versioning = _versioning_for_path(settings, session, body.path)
    if versioning is None:
        raise AppError(
            code="filesystem.versioning_unavailable",
            message="Version history is not available for this path.",
            status_code=404,
        )
    resolved = Path(body.path).resolve()
    content = versioning.read_version(resolved, body.sha)
    return FilesystemService(browse_root=settings.browse_root).write_file(
        body.path, content, cause=f"restore: {body.sha}", versioning=versioning
    )
