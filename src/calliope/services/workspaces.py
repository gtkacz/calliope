from sqlalchemy.orm import Session

from calliope.domain.errors import AppError
from calliope.domain.schemas import WorkspaceCreate, WorkspaceRead
from calliope.repositories.workspaces import WorkspaceRepository


class WorkspaceService:
    def __init__(self, session: Session) -> None:
        self.repository = WorkspaceRepository(session)

    def create(self, payload: WorkspaceCreate) -> WorkspaceRead:
        return self.repository.create(payload)

    def list(self) -> list[WorkspaceRead]:
        return self.repository.list()

    def get(self, workspace_id: str) -> WorkspaceRead:
        workspace = self.repository.get(workspace_id)
        if workspace is None:
            raise AppError(
                code="workspace_not_found",
                message="Workspace not found.",
                status_code=404,
                details={"workspace_id": workspace_id},
            )

        return workspace
