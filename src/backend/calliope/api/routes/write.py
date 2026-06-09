from typing import Annotated

from calliope.api.dependencies import (
    api_key_for,
    get_chat_client_for_profile,
    get_db_session,
    get_embedding_client,
    get_settings,
)
from calliope.config import Settings
from calliope.domain.enums import ProfileCapability
from calliope.domain.schemas import WriteRequest, WriteResponse
from calliope.ingest.indexer import EmbeddingClient
from calliope.llm.openai_compatible import OpenAICompatibleRerankClient
from calliope.retrieval.hybrid import RerankClient, _AsyncRunner, aclose_client
from calliope.services.profiles import ProfileService
from calliope.services.write import ChatClient, WriteService
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter()


@router.post("/v1/write", response_model=WriteResponse)
def write(
    request: WriteRequest,
    session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> WriteResponse:
    embedding_client: EmbeddingClient = get_embedding_client(session, settings)
    try:
        chat_client: ChatClient = get_chat_client_for_profile(
            session,
            request.chat_profile_id,
            settings,
            request.policy,
        )
    except Exception:
        runner = _AsyncRunner()
        try:
            runner.run(aclose_client(embedding_client))
        except Exception:
            pass
        finally:
            runner.close()
        raise

    rerank_client: RerankClient | None = None
    if request.chat_profile_id is not None:
        profile = ProfileService(session).require_capability_by_id(
            request.chat_profile_id,
            ProfileCapability.CHAT,
        )
        if ProfileCapability.RERANK in profile.capabilities:
            rerank_client = OpenAICompatibleRerankClient(
                base_url=profile.base_url,
                model=profile.model,
                api_key=api_key_for(profile),
                timeout_seconds=settings.llm_request_timeout_seconds,
            )

    service = WriteService(
        session,
        embedding_client=embedding_client,
        chat_client=chat_client,
        close_embedding_client=True,
        close_chat_client=True,
        close_rerank_client=True,
        score_threshold=settings.retrieval_score_threshold,
        rerank_client=rerank_client,
        max_continuation_rounds=settings.max_continuation_rounds,
    )
    operation_error: Exception | None = None
    try:
        return service.write(request)
    except Exception as exc:
        operation_error = exc
        raise
    finally:
        try:
            service.close()
        except Exception:
            if operation_error is None:
                raise
