from pathlib import Path

from calliope.domain.errors import AppError
from calliope.domain.schemas import DirectoryEntry, DirectoryListing


class FilesystemService:
    def list_directory(self, raw_path: str | None) -> DirectoryListing:
        target = self._resolve(raw_path)
        entries = self._read_entries(target)
        return DirectoryListing(
            path=str(target),
            parent=str(target.parent) if target.parent != target else None,
            entries=entries,
        )

    def _resolve(self, raw_path: str | None) -> Path:
        if raw_path is None or raw_path.strip() == "":
            candidate = Path.home()
            if not self._is_readable_dir(candidate):
                candidate = Path("/")
        else:
            candidate = Path(raw_path)

        try:
            resolved = candidate.resolve(strict=True)
        except FileNotFoundError as exc:
            raise AppError(
                code="filesystem.not_found",
                message=f"Path not found: {raw_path or candidate}",
                status_code=404,
            ) from exc
        except PermissionError as exc:
            raise AppError(
                code="filesystem.permission_denied",
                message=f"Permission denied: {raw_path or candidate}",
                status_code=403,
            ) from exc
        except OSError as exc:
            raise AppError(
                code="filesystem.invalid_path",
                message=f"Could not resolve path: {raw_path or candidate}",
                status_code=400,
            ) from exc

        if not resolved.is_dir():
            raise AppError(
                code="filesystem.not_a_directory",
                message=f"Not a directory: {resolved}",
                status_code=400,
            )

        return resolved

    def _read_entries(self, target: Path) -> list[DirectoryEntry]:
        try:
            children = list(target.iterdir())
        except PermissionError as exc:
            raise AppError(
                code="filesystem.permission_denied",
                message=f"Permission denied: {target}",
                status_code=403,
            ) from exc

        # Best-effort: skip entries that fail to stat (broken symlinks, races, perms).
        dirs: list[DirectoryEntry] = []
        for child in children:
            try:
                if not child.is_dir():
                    continue
            except OSError:
                continue
            dirs.append(
                DirectoryEntry(
                    name=child.name,
                    path=str(child),
                    is_dir=True,
                    is_hidden=child.name.startswith("."),
                )
            )

        dirs.sort(key=lambda e: e.name.casefold())
        return dirs

    @staticmethod
    def _is_readable_dir(path: Path) -> bool:
        try:
            return path.is_dir()
        except OSError:
            return False
