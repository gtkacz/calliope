from sqlalchemy.orm import Session

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
        return self.repository.get(workspace_id)
