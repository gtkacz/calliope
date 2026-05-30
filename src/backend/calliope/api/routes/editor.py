from typing import Annotated

from calliope.api.dependencies import get_chat_client_for_profile, get_db_session, get_settings
from calliope.config import Settings
from calliope.domain.schemas import EditProposal, EditProposalRequest
from calliope.services.editor import EditorService
from calliope.services.filesystem import FilesystemService
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter()


@router.post("/v1/editor/propose", response_model=EditProposal)
def propose_edit(
    request: EditProposalRequest,
    session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> EditProposal:
    chat_client = get_chat_client_for_profile(session, request.chat_profile_id)
    service = EditorService(
        filesystem=FilesystemService(browse_root=settings.browse_root),
        chat_client=chat_client,
        close_chat_client=True,
    )
    operation_error: Exception | None = None
    try:
        return service.propose(request)
    except Exception as exc:
        operation_error = exc
        raise
    finally:
        try:
            service.close()
        except Exception:
            if operation_error is None:
                raise
