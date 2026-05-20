from calliope.domain.schemas import SearchRequest, SearchResponse
from calliope.repositories.chats import ChatRepository
from calliope.repositories.chunks import ChunkRepository
from calliope.retrieval.hybrid import EmbeddingClient, HybridRetriever, _AsyncRunner
from sqlalchemy.orm import Session


class SearchService:
    def __init__(
        self,
        session: Session,
        embedding_client: EmbeddingClient,
        *,
        async_runner: _AsyncRunner | None = None,
        close_embedding_client: bool = False,
    ) -> None:
        self.session = session
        self.embedding_client = embedding_client
        self._retriever = HybridRetriever(
            self.session,
            self.embedding_client,
            async_runner=async_runner,
            close_embedding_client=close_embedding_client,
        )

    def search(self, request: SearchRequest) -> SearchResponse:
        hits = self._retriever.retrieve(
            request.query,
            workspace_id=request.workspace_id,
            limit=request.limit,
        )
        chunk_repo = ChunkRepository(self.session)
        sources = [chunk_repo.source_for_chunk(hit.chunk_id, hit.score) for hit in hits]

        session_summary = None
        search_message = None
        if request.persist:
            chat_repo = ChatRepository(self.session)
            try:
                session_id = request.session_id
                if session_id is None:
                    chat_session = chat_repo.create_session(title=request.query[:80])
                    session_id = chat_session.id
                else:
                    chat_repo.get_session_row(session_id)
                message = chat_repo.add_message(
                    session_id=session_id,
                    role="search",
                    content=request.query,
                    metadata={
                        "turn_kind": "search_result",
                        "query": request.query,
                        "sources": [source.model_dump(mode="json") for source in sources],
                    },
                )
                chat_repo.touch_session(session_id)
                self.session.commit()
            except Exception:
                self.session.rollback()
                raise
            session_summary = chat_repo.get_session_summary(session_id)
            search_message = chat_repo.message_to_read(message)

        return SearchResponse(
            sources=sources,
            session=session_summary,
            search_message=search_message,
        )

    def close(self) -> None:
        self._retriever.close()
