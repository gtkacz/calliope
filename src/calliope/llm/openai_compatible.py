import asyncio
import threading
from collections.abc import Coroutine
from typing import Any

import httpx

from calliope.domain.errors import AppError


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

        self._run_sync(self.aclose())

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

    def _run_sync(self, coroutine: Coroutine[Any, Any, None]) -> None:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(coroutine)
            return

        error: BaseException | None = None

        def runner() -> None:
            nonlocal error
            try:
                asyncio.run(coroutine)
            except BaseException as exc:
                error = exc

        thread = threading.Thread(target=runner)
        thread.start()
        thread.join()
        if error is not None:
            raise error
