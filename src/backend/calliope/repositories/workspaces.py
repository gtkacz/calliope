from pathlib import Path

from calliope.db.models import Workspace
from calliope.domain.errors import AppError
from calliope.domain.schemas import WorkspaceCreate, WorkspacePatch, WorkspaceRead
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


class WorkspaceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, payload: WorkspaceCreate) -> WorkspaceRead:
        workspace = Workspace(
            name=payload.name,
            root_path=payload.root_path,
            include_globs=payload.include_globs,
            exclude_globs=payload.exclude_globs,
            versioning_enabled=payload.versioning_enabled,
        )
        self.session.add(workspace)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise AppError(
                code="workspace_already_exists",
                message="Workspace already exists.",
                status_code=409,
                details={"name": payload.name},
            ) from exc
        self.session.refresh(workspace)

        return self._to_read(workspace)

    def list(self) -> list[WorkspaceRead]:
        workspaces = self.session.scalars(
            select(Workspace).order_by(Workspace.created_at, Workspace.id)
        ).all()

        return [self._to_read(workspace) for workspace in workspaces]

    def get(self, workspace_id: str) -> WorkspaceRead:
        return self._to_read(self._get_row(workspace_id))

    def update(self, workspace_id: str, payload: WorkspacePatch) -> WorkspaceRead:
        workspace = self._get_row(workspace_id)
        if payload.name is not None:
            workspace.name = payload.name
        if payload.root_path is not None:
            workspace.root_path = payload.root_path
        if payload.include_globs is not None:
            workspace.include_globs = payload.include_globs
        if payload.exclude_globs is not None:
            workspace.exclude_globs = payload.exclude_globs
        # None is a meaningful value here (inherit global), so distinguish an
        # explicit null from an omitted field via the set of provided fields.
        if "versioning_enabled" in payload.model_fields_set:
            workspace.versioning_enabled = payload.versioning_enabled
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise AppError(
                code="workspace_already_exists",
                message="Workspace already exists.",
                status_code=409,
                details={"name": payload.name},
            ) from exc
        self.session.refresh(workspace)
        return self._to_read(workspace)

    def delete(self, workspace_id: str) -> None:
        workspace = self._get_row(workspace_id)
        self.session.delete(workspace)
        self.session.commit()

    def find_by_path(self, absolute_path: str) -> Workspace | None:
        """Return the workspace whose root_path contains the given absolute path,
        preferring the longest (most specific) root when several overlap."""
        target = Path(absolute_path)
        best: Workspace | None = None
        best_len = -1
        for workspace in self.session.scalars(select(Workspace)).all():
            try:
                root = Path(workspace.root_path).resolve()
            except OSError:
                continue
            if target == root or root in target.parents:
                root_len = len(str(root))
                if root_len > best_len:
                    best, best_len = workspace, root_len
        return best

    def _get_row(self, workspace_id: str) -> Workspace:
        workspace = self.session.get(Workspace, workspace_id)
        if workspace is None:
            raise AppError(
                code="workspace_not_found",
                message="Workspace not found.",
                status_code=404,
                details={"workspace_id": workspace_id},
            )
        return workspace

    @staticmethod
    def _to_read(workspace: Workspace) -> WorkspaceRead:
        return WorkspaceRead(
            id=workspace.id,
            name=workspace.name,
            root_path=workspace.root_path,
            include_globs=workspace.include_globs,
            exclude_globs=workspace.exclude_globs,
            versioning_enabled=workspace.versioning_enabled,
            created_at=workspace.created_at,
        )
