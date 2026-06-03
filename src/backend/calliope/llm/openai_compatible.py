import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import httpx
from calliope.config import DEFAULT_LLM_REQUEST_TIMEOUT_SECONDS
from calliope.domain.errors import AppError
from calliope.llm.sampling import SamplingParams

logger = logging.getLogger(__name__)

# OpenAI-compatible finish_reason emitted when generation stopped at the token
# ceiling rather than a natural end. Surfaced because the truncated content is
# otherwise indistinguishable from a complete response.
_FINISH_REASON_LENGTH = "length"


@dataclass(frozen=True)
class ChatCompletion:
    """A chat generation plus the one piece of response metadata callers act on.

    `truncated` carries the finish_reason=length signal up to the service layer so
    a cut-off document can be flagged to the writer, rather than being silently
    stored as if complete."""

    content: str
    truncated: bool = False


def verify_embedding_dimension(
    vector: list[float],
    expected: int,
    *,
    model: str | None = None,
) -> list[float]:
    """Guard the embedding/column-width contract at the point of production.

    A vector whose width differs from the pgvector column would otherwise fail
    deep in the driver with an opaque error on insert (indexing) or on the `<->`
    operator (retrieval). Comparing here lets us fail fast with a message that
    names the offending model and the expected width, which is the only
    actionable information for the operator."""
    actual = len(vector)
    if actual == expected:
        return vector

    raise AppError(
        code="embedding_dimension_mismatch",
        message=(
            f"Embedding model {model or '<unknown>'!r} returned {actual}-dimensional "
            f"vectors, but the database stores {expected}-dimensional embeddings. "
            f"Select an embeddings model whose native output width is {expected}, "
            f"or migrate CALLIOPE_EMBEDDING_DIMENSIONS and the chunks.embedding column."
        ),
        status_code=500,
        details={"expected": expected, "actual": actual, "model": model},
    )


class OpenAICompatibleClient:
    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str | None = None,
        http_client: httpx.AsyncClient | None = None,
        timeout_seconds: float = DEFAULT_LLM_REQUEST_TIMEOUT_SECONDS,
        sampling_params: SamplingParams | None = None,
        use_ollama_native: bool = False,
        num_ctx: int | None = None,
        use_koboldcpp: bool = False,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key or "not-needed"
        self._owns_http_client = http_client is None
        self.http_client = http_client or httpx.AsyncClient(timeout=timeout_seconds)
        self._closed = False
        self.sampling_params = sampling_params
        self.use_ollama_native = use_ollama_native
        self.num_ctx = num_ctx
        self.use_koboldcpp = use_koboldcpp

    async def aclose(self) -> None:
        if self._closed:
            return

        self._closed = True
        if self._owns_http_client:
            await self.http_client.aclose()

    async def embed(self, text: str) -> list[float]:
        response = await self._post(
            f"{self.base_url}/embeddings",
            code="embedding_failed",
            headers=self._headers(),
            json={"model": self.model, "input": text},
        )
        self._raise_for_status(response, code="embedding_failed")

        data = response.json()
        return data["data"][0]["embedding"]

    async def chat(self, messages: list[dict[str, Any]]) -> ChatCompletion:
        if self.use_ollama_native:
            return await self._chat_ollama_native(messages)
        payload: dict[str, Any] = {"model": self.model, "messages": messages}
        if self.sampling_params is not None:
            p = self.sampling_params
            payload["temperature"] = p.temperature
            if p.min_p is not None:
                payload["min_p"] = p.min_p
            if p.repetition_penalty is not None:
                payload["repetition_penalty"] = p.repetition_penalty
            if p.top_p is not None:
                payload["top_p"] = p.top_p
            if p.frequency_penalty is not None:
                payload["frequency_penalty"] = p.frequency_penalty
            if p.max_tokens is not None:
                payload["max_tokens"] = p.max_tokens
        if self.use_koboldcpp and "repetition_penalty" in payload:
            # KoboldCpp's /v1 endpoint honors only its native rep_pen field and
            # silently ignores OpenAI's repetition_penalty, which would otherwise
            # leave repetition unconstrained.
            payload["rep_pen"] = payload.pop("repetition_penalty")
        response = await self._post(
            f"{self.base_url}/chat/completions",
            code="generation_failed",
            headers=self._headers(),
            json=payload,
        )
        self._raise_for_status(response, code="generation_failed")

        data = response.json()
        choice = data["choices"][0]
        truncated = choice.get("finish_reason") == _FINISH_REASON_LENGTH
        if truncated:
            logger.warning(
                "generation hit the token ceiling (finish_reason=length, max_tokens=%s, "
                "model=%s); the response is truncated. Raise CALLIOPE_DEFAULT_MAX_TOKENS "
                "or the profile's max_tokens if documents are being cut off.",
                payload.get("max_tokens"),
                self.model,
            )
        return ChatCompletion(content=choice["message"]["content"], truncated=truncated)

    def _ollama_base(self) -> str:
        """Return the Ollama server root, stripping a trailing ``/v1``.

        Ollama profiles store the ``/v1`` base_url so the shared embeddings path
        (`/v1/embeddings`) keeps working; the native chat endpoint lives at the
        server root (`/api/chat`), so the OpenAI-compat suffix is removed here."""
        suffix = "/v1"
        if self.base_url.endswith(suffix):
            return self.base_url[: -len(suffix)]
        return self.base_url

    async def _chat_ollama_native(self, messages: list[dict[str, Any]]) -> ChatCompletion:
        """Generate via Ollama's native ``/api/chat`` instead of ``/v1``.

        Ollama's OpenAI-compatible endpoint silently discards num_ctx, min_p, and
        repeat_penalty, so the prompt is left-truncated against a tiny default
        window and sampling runs unconstrained — the cause of short, hallucinated,
        off-format output. The native endpoint accepts these under an `options`
        object, where Ollama's own parameter names apply (max_tokens is
        num_predict; repetition_penalty is repeat_penalty)."""
        options: dict[str, Any] = {}
        if self.num_ctx is not None:
            options["num_ctx"] = self.num_ctx
        if self.sampling_params is not None:
            p = self.sampling_params
            options["temperature"] = p.temperature
            if p.min_p is not None:
                options["min_p"] = p.min_p
            if p.repetition_penalty is not None:
                options["repeat_penalty"] = p.repetition_penalty
            if p.top_p is not None:
                options["top_p"] = p.top_p
            if p.frequency_penalty is not None:
                options["frequency_penalty"] = p.frequency_penalty
            if p.max_tokens is not None:
                options["num_predict"] = p.max_tokens
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        if options:
            payload["options"] = options
        response = await self._post(
            f"{self._ollama_base()}/api/chat",
            code="generation_failed",
            headers=self._headers(),
            json=payload,
        )
        self._raise_for_status(response, code="generation_failed")

        data = response.json()
        message = data.get("message") or {}
        truncated = data.get("done_reason") == _FINISH_REASON_LENGTH
        if truncated:
            logger.warning(
                "generation hit the token ceiling (done_reason=length, num_predict=%s, "
                "model=%s); the response is truncated. Raise CALLIOPE_DEFAULT_MAX_TOKENS "
                "or the profile's max_tokens if documents are being cut off.",
                options.get("num_predict"),
                self.model,
            )
        return ChatCompletion(content=message.get("content", ""), truncated=truncated)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def close(self) -> None:
        if self._closed:
            return

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self.aclose())
            return

        raise RuntimeError(
            "OpenAICompatibleClient.close() cannot be called while an event loop "
            "is running. Use 'await aclose()' in async contexts."
        )

    async def _post(
        self,
        url: str,
        *,
        code: str,
        headers: dict[str, str],
        json: dict[str, Any],
    ) -> httpx.Response:
        try:
            return await self.http_client.post(url, headers=headers, json=json)
        except httpx.RequestError as exc:
            raise AppError(
                code=code,
                message="OpenAI-compatible request failed.",
                status_code=502,
                details={
                    "exception": type(exc).__name__,
                    "message": str(exc),
                },
            ) from exc

    def _raise_for_status(self, response: httpx.Response, *, code: str) -> None:
        if response.status_code < 400:
            return

        raise AppError(
            code=code,
            message="OpenAI-compatible request failed.",
            status_code=502,
            details={"status_code": response.status_code, "body": response.text},
        )


class OpenAICompatibleRerankClient:
    """Cohere-compatible rerank endpoint wrapper.

    Implements the RerankClient Protocol so it can be passed to HybridRetriever
    without importing the Protocol here (avoids a circular dependency)."""

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str | None = None,
        http_client: httpx.AsyncClient | None = None,
        timeout_seconds: float = DEFAULT_LLM_REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key or "not-needed"
        self._owns_http_client = http_client is None
        self.http_client = http_client or httpx.AsyncClient(timeout=timeout_seconds)
        self._closed = False

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._owns_http_client:
            await self.http_client.aclose()

    async def rerank(self, query: str, documents: list[str]) -> list[float]:
        response = await self._post(
            f"{self.base_url}/rerank",
            code="rerank_failed",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model, "query": query, "documents": documents},
        )
        self._raise_for_status(response, code="rerank_failed")
        data = response.json()
        # Cohere returns results in relevance order; re-sort by original index
        # to align scores with the input documents list.
        results: list[dict[str, Any]] = sorted(data["results"], key=lambda r: r["index"])
        return [item["relevance_score"] for item in results]

    async def _post(
        self,
        url: str,
        *,
        code: str,
        headers: dict[str, str],
        json: dict[str, Any],
    ) -> httpx.Response:
        try:
            return await self.http_client.post(url, headers=headers, json=json)
        except httpx.RequestError as exc:
            raise AppError(
                code=code,
                message="OpenAI-compatible request failed.",
                status_code=502,
                details={
                    "exception": type(exc).__name__,
                    "message": str(exc),
                },
            ) from exc

    def _raise_for_status(self, response: httpx.Response, *, code: str) -> None:
        if response.status_code < 400:
            return
        raise AppError(
            code=code,
            message="OpenAI-compatible request failed.",
            status_code=502,
            details={"status_code": response.status_code, "body": response.text},
        )
