from typing import Annotated

from calliope.api.dependencies import get_settings
from calliope.config import Settings
from calliope.domain.schemas import DirectoryListing, FileContent, FileWriteRequest
from calliope.services.filesystem import FilesystemService
from fastapi import APIRouter, Depends, Query

router = APIRouter()


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
    body: FileWriteRequest,
) -> FileContent:
    return FilesystemService(browse_root=settings.browse_root).write_file(body.path, body.content)
