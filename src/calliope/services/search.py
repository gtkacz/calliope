from sqlalchemy.orm import Session

from calliope.domain.schemas import SearchRequest, SearchResponse
from calliope.repositories.chunks import ChunkRepository
from calliope.retrieval.hybrid import EmbeddingClient, HybridRetriever


class SearchService:
    def __init__(self, session: Session, embedding_client: EmbeddingClient) -> None:
        self.session = session
        self.embedding_client = embedding_client

    def search(self, request: SearchRequest) -> SearchResponse:
        hits = HybridRetriever(self.session, self.embedding_client).retrieve(
            request.query,
            workspace_id=request.workspace_id,
            limit=request.limit,
        )
        chunk_repo = ChunkRepository(self.session)
        sources = [chunk_repo.source_for_chunk(hit.chunk_id, hit.score) for hit in hits]

        return SearchResponse(sources=sources)
