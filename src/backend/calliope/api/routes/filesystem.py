from calliope.domain.schemas import DirectoryListing
from calliope.services.filesystem import FilesystemService
from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/v1/filesystem/list", response_model=DirectoryListing)
def list_directory(
    path: str | None = Query(default=None),
) -> DirectoryListing:
    return FilesystemService().list_directory(path)
