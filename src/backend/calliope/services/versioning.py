from __future__ import annotations

import contextlib
import fcntl
import logging
import os
import shutil
import subprocess
from collections.abc import Generator
from datetime import datetime
from pathlib import Path

from calliope.domain.constants import VERSION_STORE_DIRNAME
from calliope.domain.errors import AppError
from calliope.domain.schemas import FileVersion

logger = logging.getLogger(__name__)

# Set as the commit author/committer for every snapshot so commits succeed even
# when the container user has no ~/.gitconfig.
_GIT_IDENTITY = (
    "-c",
    "user.name=Calliope",
    "-c",
    "user.email=calliope@localhost",
)
# git log field separator; the unit-separator control char never appears in
# commit subjects or hashes, so it is safe to split on.
_FIELD_SEP = "\x1f"
_BINARY_SNIFF_BYTES = 8000


class VersioningService:
    """Best-effort file version history backed by a detached git store.

    The store lives at ``<root>/.calliope-git`` and uses ``<root>`` as its
    work-tree, so it tracks the same files the user sees without ever touching
    their own ``.git``. Every snapshot operation is best-effort: failures are
    logged and swallowed so they can never block a file write.
    """

    def __init__(self, root_path: str) -> None:
        self._root = Path(root_path).resolve()
        self._git_dir = self._root / VERSION_STORE_DIRNAME

    @staticmethod
    def is_available() -> bool:
        return shutil.which("git") is not None

    @contextlib.contextmanager
    def lock(self) -> Generator[None, None, None]:
        # Serialize the baseline+write+snapshot sequence per workspace: git's
        # index is workspace-scoped, so concurrent writes could otherwise race.
        handle = None
        try:
            self._git_dir.mkdir(parents=True, exist_ok=True)
            # Held open across the yield so the OS lock persists for the whole
            # snapshot+write sequence; closed in the finally below.
            handle = open(self._git_dir / "SNAPSHOT_LOCK", "w")
            fcntl.flock(handle, fcntl.LOCK_EX)
        except OSError as exc:
            logger.warning("versioning: lock unavailable for %s: %s", self._root, exc)
            if handle is not None:
                handle.close()
            yield
            return
        try:
            yield
        finally:
            with contextlib.suppress(OSError):
                fcntl.flock(handle, fcntl.LOCK_UN)
            handle.close()

    def ensure_initialized(self) -> None:
        try:
            if (self._git_dir / "HEAD").exists():
                return
            self._git_dir.mkdir(parents=True, exist_ok=True)
            self._init()
            self._write_store_exclude()
            self._register_user_repo_exclude()
        except (OSError, subprocess.SubprocessError) as exc:
            logger.warning("versioning: init failed for %s: %s", self._root, exc)

    def ensure_baseline(self, abs_path: Path) -> None:
        """Capture the file's pre-edit content once, so the user can roll back
        to the state before Calliope ever touched it."""
        if self.has_history(abs_path):
            return
        self._commit(abs_path, "baseline: before first edit")

    def snapshot(self, abs_path: Path, cause: str | None) -> None:
        self._commit(abs_path, cause or "manual save")

    def has_history(self, abs_path: Path) -> bool:
        rel = self._relpath(abs_path)
        if rel is None:
            return False
        try:
            result = self._git(["rev-list", "--count", "HEAD", "--", rel])
        except subprocess.SubprocessError:
            return False
        try:
            return int(result.stdout.strip()) > 0
        except ValueError:
            return False

    def history(self, abs_path: Path) -> list[FileVersion]:
        rel = self._relpath(abs_path)
        if rel is None:
            return []
        fmt = _FIELD_SEP.join(["%H", "%cI", "%s"])
        try:
            result = self._git(["log", f"--pretty=format:{fmt}", "--", rel])
        except subprocess.SubprocessError:
            return []

        versions: list[FileVersion] = []
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            parts = line.split(_FIELD_SEP)
            if len(parts) != 3:
                continue
            sha, iso_timestamp, cause = parts
            blob = self._read_blob(sha, rel)
            versions.append(
                FileVersion(
                    sha=sha,
                    timestamp=datetime.fromisoformat(iso_timestamp),
                    cause=cause,
                    size_bytes=len(blob) if blob is not None else 0,
                    is_binary=blob is not None and b"\x00" in blob[:_BINARY_SNIFF_BYTES],
                )
            )
        return versions

    def read_version(self, abs_path: Path, sha: str) -> str:
        rel = self._relpath(abs_path)
        blob = self._read_blob(sha, rel) if rel is not None else None
        if blob is None:
            raise AppError(
                code="filesystem.version_not_found",
                message="No stored version was found for this file.",
                status_code=404,
                details={"sha": sha},
            )
        if b"\x00" in blob[:_BINARY_SNIFF_BYTES]:
            raise AppError(
                code="filesystem.version_binary",
                message="Cannot restore a binary version through the text editor.",
                status_code=400,
            )
        try:
            return blob.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise AppError(
                code="filesystem.version_binary",
                message="Stored version is not valid UTF-8 text.",
                status_code=400,
            ) from exc

    def destroy(self) -> None:
        shutil.rmtree(self._git_dir, ignore_errors=True)

    def _commit(self, abs_path: Path, message: str) -> None:
        rel = self._relpath(abs_path)
        if rel is None:
            return
        try:
            self._git(["add", "--", rel])
            self._git(["commit", "-q", "-m", message, "--", rel])
        except subprocess.CalledProcessError as exc:
            output = (exc.stderr or "") + (exc.stdout or "")
            # Identical content yields "nothing to commit" — benign, not an error.
            if "nothing to commit" not in output and "no changes added" not in output:
                logger.warning("versioning: commit failed for %s: %s", rel, output.strip())
        except (OSError, subprocess.SubprocessError) as exc:
            logger.warning("versioning: commit error for %s: %s", rel, exc)

    def _init(self) -> None:
        # Pass only --git-dir (not --work-tree) so git initializes the store at
        # the detached path rather than trying to relocate the user's repo.
        subprocess.run(
            ["git", f"--git-dir={self._git_dir}", "init", "-q"],
            cwd=str(self._root),
            env=self._env(),
            capture_output=True,
            text=True,
            check=True,
        )

    def _write_store_exclude(self) -> None:
        info = self._git_dir / "info"
        info.mkdir(parents=True, exist_ok=True)
        (info / "exclude").write_text(f"/{VERSION_STORE_DIRNAME}/\n", encoding="utf-8")

    def _register_user_repo_exclude(self) -> None:
        """Keep the shadow store out of the user's own ``git status`` without
        modifying their history, branches, staging, or hooks."""
        user_git = self._root / ".git"
        if not user_git.is_dir():
            return
        exclude_file = user_git / "info" / "exclude"
        line = f"/{VERSION_STORE_DIRNAME}/"
        try:
            existing = exclude_file.read_text(encoding="utf-8") if exclude_file.exists() else ""
            if line in existing.splitlines():
                return
            exclude_file.parent.mkdir(parents=True, exist_ok=True)
            with open(exclude_file, "a", encoding="utf-8") as handle:
                if existing and not existing.endswith("\n"):
                    handle.write("\n")
                handle.write(f"{line}\n")
        except OSError as exc:
            logger.warning("versioning: could not update user exclude for %s: %s", self._root, exc)

    def _read_blob(self, sha: str, rel: str) -> bytes | None:
        try:
            result = subprocess.run(
                [
                    "git",
                    f"--git-dir={self._git_dir}",
                    f"--work-tree={self._root}",
                    "show",
                    f"{sha}:{rel}",
                ],
                cwd=str(self._root),
                env=self._env(),
                capture_output=True,
                check=True,
            )
            return result.stdout
        except (OSError, subprocess.SubprocessError):
            return None

    def _relpath(self, abs_path: Path) -> str | None:
        try:
            return abs_path.resolve().relative_to(self._root).as_posix()
        except (ValueError, OSError):
            return None

    def _git(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "git",
                f"--git-dir={self._git_dir}",
                f"--work-tree={self._root}",
                *_GIT_IDENTITY,
                *args,
            ],
            cwd=str(self._root),
            env=self._env(),
            capture_output=True,
            text=True,
            check=True,
        )

    def _env(self) -> dict[str, str]:
        env = dict(os.environ)
        # Never discover or inherit configuration from the surrounding filesystem
        # or the user's global/system git config (hooks, gpg signing, etc.).
        env["GIT_CEILING_DIRECTORIES"] = str(self._root)
        env["GIT_CONFIG_NOSYSTEM"] = "1"
        env["GIT_CONFIG_GLOBAL"] = os.devnull
        return env
