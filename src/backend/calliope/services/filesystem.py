from pathlib import Path

from calliope.domain.errors import AppError
from calliope.domain.schemas import DirectoryEntry, DirectoryListing, FileContent


class FilesystemService:
    def __init__(self, browse_root: str | None = None) -> None:
        self._browse_root = browse_root

    def list_directory(self, raw_path: str | None, include_files: bool = False) -> DirectoryListing:
        target = self._resolve(raw_path)
        entries = self._read_entries(target, include_files=include_files)
        return DirectoryListing(
            path=str(target),
            parent=str(target.parent) if target.parent != target else None,
            entries=entries,
        )

    def read_file(self, raw_path: str | None) -> FileContent:
        if raw_path is None or raw_path.strip() == "":
            raise AppError(
                code="filesystem.not_found",
                message="Path not found: None",
                status_code=404,
            )

        candidate = Path(raw_path)
        try:
            resolved = candidate.resolve(strict=True)
        except FileNotFoundError as exc:
            raise AppError(
                code="filesystem.not_found",
                message=f"Path not found: {raw_path}",
                status_code=404,
            ) from exc
        except PermissionError as exc:
            raise AppError(
                code="filesystem.permission_denied",
                message=f"Permission denied: {raw_path}",
                status_code=403,
            ) from exc

        if not resolved.is_file():
            raise AppError(
                code="filesystem.not_a_file",
                message=f"Not a file: {resolved}",
                status_code=400,
            )

        self._confine(resolved)

        try:
            content = resolved.read_text(encoding="utf-8")
        except PermissionError as exc:
            raise AppError(
                code="filesystem.permission_denied",
                message=f"Permission denied: {resolved}",
                status_code=403,
            ) from exc

        return FileContent(path=str(resolved), content=content)

    def write_file(self, raw_path: str, content: str) -> FileContent:
        candidate = Path(raw_path)
        try:
            resolved = candidate.resolve(strict=True)
        except FileNotFoundError as exc:
            raise AppError(
                code="filesystem.not_found",
                message=f"Path not found: {raw_path}",
                status_code=404,
            ) from exc
        except PermissionError as exc:
            raise AppError(
                code="filesystem.permission_denied",
                message=f"Permission denied: {raw_path}",
                status_code=403,
            ) from exc

        # Only allow editing files that already exist — no file creation via this endpoint.
        if not resolved.is_file():
            raise AppError(
                code="filesystem.not_a_file",
                message=f"Not a file: {resolved}",
                status_code=400,
            )

        self._confine(resolved)

        try:
            resolved.write_text(content, encoding="utf-8")
        except PermissionError as exc:
            raise AppError(
                code="filesystem.permission_denied",
                message=f"Permission denied: {resolved}",
                status_code=403,
            ) from exc
        except OSError as exc:
            raise AppError(
                code="filesystem.write_failed",
                message=f"Write failed: {resolved}",
                status_code=400,
            ) from exc

        return FileContent(path=str(resolved), content=content)

    def _confine(self, resolved: Path) -> None:
        """Guard against path-traversal: resolved must be inside browse_root."""
        if not self._browse_root:
            return

        root = Path(self._browse_root)
        try:
            root_resolved = root.resolve(strict=True)
        except OSError as exc:
            # If browse_root itself cannot be resolved, deny access as a safe fallback.
            raise AppError(
                code="filesystem.outside_root",
                message="Path is outside the permitted root.",
                status_code=403,
            ) from exc

        if not resolved.is_relative_to(root_resolved):
            raise AppError(
                code="filesystem.outside_root",
                message="Path is outside the permitted root.",
                status_code=403,
            )

    def _resolve(self, raw_path: str | None) -> Path:
        if raw_path is None or raw_path.strip() == "":
            candidate = self._default_root()
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

    def _read_entries(self, target: Path, include_files: bool = False) -> list[DirectoryEntry]:
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
        files: list[DirectoryEntry] = []
        for child in children:
            try:
                is_dir = child.is_dir()
            except OSError:
                continue
            if is_dir:
                dirs.append(
                    DirectoryEntry(
                        name=child.name,
                        path=str(child),
                        is_dir=True,
                        is_hidden=child.name.startswith("."),
                    )
                )
            elif include_files:
                files.append(
                    DirectoryEntry(
                        name=child.name,
                        path=str(child),
                        is_dir=False,
                        is_hidden=child.name.startswith("."),
                    )
                )

        dirs.sort(key=lambda e: e.name.casefold())
        files.sort(key=lambda e: e.name.casefold())
        return dirs + files

    def _default_root(self) -> Path:
        if self._browse_root:
            configured = Path(self._browse_root)
            if self._is_readable_dir(configured):
                return configured

        home = Path.home()
        if self._is_readable_dir(home):
            return home

        return Path("/")

    @staticmethod
    def _is_readable_dir(path: Path) -> bool:
        try:
            return path.is_dir()
        except OSError:
            return False
