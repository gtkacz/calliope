from calliope.domain.schemas import WorkspaceCreate, WorkspacePatch, WorkspaceRead
from calliope.repositories.workspaces import WorkspaceRepository
from sqlalchemy.orm import Session


class WorkspaceService:
    def __init__(self, session: Session) -> None:
        self.repository = WorkspaceRepository(session)

    def create(self, payload: WorkspaceCreate) -> WorkspaceRead:
        return self.repository.create(payload)

    def list(self) -> list[WorkspaceRead]:
        return self.repository.list()

    def get(self, workspace_id: str) -> WorkspaceRead:
        return self.repository.get(workspace_id)

    def update(self, workspace_id: str, payload: WorkspacePatch) -> WorkspaceRead:
        return self.repository.update(workspace_id, payload)

    def delete(self, workspace_id: str) -> None:
        self.repository.delete(workspace_id)
