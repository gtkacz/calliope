from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from calliope.db.models import Workspace
from calliope.domain.errors import AppError
from calliope.domain.schemas import WorkspaceCreate, WorkspaceRead


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
        workspace = self.session.get(Workspace, workspace_id)
        if workspace is None:
            raise AppError(
                code="workspace_not_found",
                message="Workspace not found.",
                status_code=404,
                details={"workspace_id": workspace_id},
            )

        return self._to_read(workspace)

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
