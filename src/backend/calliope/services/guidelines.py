from __future__ import annotations

import logging

from calliope.repositories.workspaces import WorkspaceRepository
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def resolve_workspace_guidelines(
    session: Session,
    *,
    workspace_id: str | None,
    apply_guidelines: bool,
) -> str | None:
    """Standing guidelines for a workspace addressed by id (chat/write surfaces).

    Returns None when the request suppresses guidelines, when no workspace is
    given, when the workspace stores none, or on any lookup failure. Best-effort:
    a guideline lookup must never break a generation, so this never raises."""
    if not apply_guidelines or workspace_id is None:
        return None
    try:
        workspace = WorkspaceRepository(session).get(workspace_id)
    except Exception:
        logger.warning(
            "guideline resolution failed for workspace_id %r; continuing without guidelines",
            workspace_id,
            exc_info=True,
        )
        return None
    return workspace.guidelines or None


def resolve_guidelines_for_path(
    session: Session,
    *,
    path: str,
    apply_guidelines: bool,
) -> str | None:
    """Standing guidelines for the workspace whose root contains `path`.

    Used by the editor surface, which has no workspace id but a file path. Mirrors
    the editor's existing best-effort workspace resolution; returns None when
    suppressed, when no workspace contains the path, or on any lookup failure."""
    if not apply_guidelines:
        return None
    try:
        workspace = WorkspaceRepository(session).find_by_path(path)
    except Exception:
        logger.warning(
            "guideline resolution failed for path %r; continuing without guidelines",
            path,
            exc_info=True,
        )
        return None
    if workspace is None:
        return None
    return workspace.guidelines or None
