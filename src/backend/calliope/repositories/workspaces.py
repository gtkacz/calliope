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
            created_at=workspace.created_at,
        )
