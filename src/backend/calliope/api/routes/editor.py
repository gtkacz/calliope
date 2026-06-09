import logging
from typing import Annotated

from calliope.api.dependencies import (
    get_chat_client_for_profile,
    get_db_session,
    get_embedding_client,
    get_settings,
)
from calliope.config import Settings
from calliope.domain.enums import CanonPolicy
from calliope.domain.schemas import (
    EditProposal,
    EditProposalRequest,
    SearchRequest,
    SourceReference,
)
from calliope.repositories.workspaces import WorkspaceRepository
from calliope.retrieval.hybrid import _AsyncRunner
from calliope.services.editor import EditorService
from calliope.services.filesystem import FilesystemService
from calliope.services.guidelines import resolve_guidelines_for_path
from calliope.services.search import SearchService
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter()

_EDITOR_POLICY = CanonPolicy.CANON_PLUS_INFERENCE


@router.post("/v1/editor/propose", response_model=EditProposal)
def propose_edit(
    request: EditProposalRequest,
    session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> EditProposal:
    chat_client = get_chat_client_for_profile(
        session,
        request.chat_profile_id,
        settings,
        _EDITOR_POLICY,
    )

    sources = _resolve_editor_sources(request, session, settings)
    guidelines = resolve_guidelines_for_path(
        session,
        path=request.path,
        apply_guidelines=request.apply_guidelines,
    )

    service = EditorService(
        filesystem=FilesystemService(browse_root=settings.browse_root),
        chat_client=chat_client,
        close_chat_client=True,
        max_continuation_rounds=settings.max_continuation_rounds,
    )
    operation_error: Exception | None = None
    try:
        return service.propose(
            request,
            policy=_EDITOR_POLICY,
            sources=sources,
            guidelines=guidelines,
        )
    except Exception as exc:
        operation_error = exc
        raise
    finally:
        try:
            service.close()
        except Exception:
            if operation_error is None:
                raise


def _resolve_editor_sources(
    request: EditProposalRequest,
    session: Session,
    settings: Settings,
) -> list[SourceReference] | None:
    """Attempt workspace-level source retrieval for the editor.

    Uses the workspace whose root_path contains request.path (longest-match).
    Silently returns None on any resolution or search failure so the editor
    never hard-fails due to a missing retrieval context."""
    try:
        workspace = WorkspaceRepository(session).find_by_path(request.path)
        if workspace is None:
            return None

        embedding_client = get_embedding_client(session, settings)
        async_runner = _AsyncRunner()
        search_service = SearchService(
            session,
            embedding_client,
            async_runner=async_runner,
            score_threshold=settings.retrieval_score_threshold,
            close_embedding_client=True,
        )
        try:
            response = search_service.search(
                SearchRequest(
                    query=request.instruction,
                    workspace_id=workspace.id,
                    limit=3,
                )
            )
            return response.sources or None
        finally:
            try:
                search_service.close()
            except Exception:
                pass
            async_runner.close()
    except Exception:
        logger.warning(
            "editor source retrieval failed for path %r; continuing without sources",
            request.path,
            exc_info=True,
        )
        return None
