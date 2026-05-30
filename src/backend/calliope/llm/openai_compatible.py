import asyncio
from typing import Any

import httpx
from calliope.domain.errors import AppError


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
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key or "not-needed"
        self._owns_http_client = http_client is None
        self.http_client = http_client or httpx.AsyncClient(timeout=30)
        self._closed = False

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

    async def chat(self, messages: list[dict[str, Any]]) -> str:
        response = await self._post(
            f"{self.base_url}/chat/completions",
            code="generation_failed",
            headers=self._headers(),
            json={"model": self.model, "messages": messages},
        )
        self._raise_for_status(response, code="generation_failed")

        data = response.json()
        return data["choices"][0]["message"]["content"]

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
