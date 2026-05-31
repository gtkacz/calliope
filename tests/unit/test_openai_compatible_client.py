import httpx
import pytest
from calliope.domain.errors import AppError
from calliope.llm.openai_compatible import OpenAICompatibleClient


@pytest.mark.asyncio
async def test_create_embedding_calls_openai_compatible_endpoint() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={"data": [{"embedding": [0.1, 0.2, 0.3]}]},
        )
    )
    client = OpenAICompatibleClient(
        base_url="http://local/v1",
        model="embed-model",
        api_key="test",
        http_client=httpx.AsyncClient(transport=transport),
    )

    embedding = await client.embed("Kaelen")

    assert embedding == [0.1, 0.2, 0.3]


@pytest.mark.asyncio
async def test_chat_returns_message_content() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={"choices": [{"message": {"content": "Grounded answer"}}]},
        )
    )
    client = OpenAICompatibleClient(
        base_url="http://local/v1",
        model="chat-model",
        api_key="test",
        http_client=httpx.AsyncClient(transport=transport),
    )

    answer = await client.chat([{"role": "user", "content": "Who is Kaelen?"}])

    assert answer.content == "Grounded answer"
    assert answer.truncated is False


@pytest.mark.asyncio
async def test_embed_maps_transport_failure_to_app_error() -> None:
    def raise_transport_error(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    client = OpenAICompatibleClient(
        base_url="http://local/v1",
        model="embed-model",
        api_key="test",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(raise_transport_error)),
    )

    with pytest.raises(AppError) as exc_info:
        await client.embed("Kaelen")

    error = exc_info.value
    assert error.code == "embedding_failed"
    assert error.status_code == 502
    assert error.message == "OpenAI-compatible request failed."
    assert error.details == {
        "exception": "ConnectError",
        "message": "connection refused",
    }


@pytest.mark.asyncio
async def test_chat_maps_transport_failure_to_app_error() -> None:
    def raise_transport_error(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    client = OpenAICompatibleClient(
        base_url="http://local/v1",
        model="chat-model",
        api_key="test",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(raise_transport_error)),
    )

    with pytest.raises(AppError) as exc_info:
        await client.chat([{"role": "user", "content": "Who is Kaelen?"}])

    error = exc_info.value
    assert error.code == "generation_failed"
    assert error.status_code == 502
    assert error.message == "OpenAI-compatible request failed."
    assert error.details == {
        "exception": "ReadTimeout",
        "message": "timed out",
    }


@pytest.mark.asyncio
async def test_aclose_closes_owned_http_client() -> None:
    client = OpenAICompatibleClient(
        base_url="http://local/v1",
        model="embed-model",
    )

    await client.aclose()

    assert client.http_client.is_closed


@pytest.mark.asyncio
async def test_close_raises_inside_running_event_loop() -> None:
    client = OpenAICompatibleClient(
        base_url="http://local/v1",
        model="embed-model",
    )

    with pytest.raises(RuntimeError, match="Use 'await aclose\\(\\)'"):
        client.close()

    assert not client.http_client.is_closed
    await client.aclose()
    assert client.http_client.is_closed


def test_close_closes_owned_http_client_from_sync_context() -> None:
    client = OpenAICompatibleClient(
        base_url="http://local/v1",
        model="embed-model",
    )

    client.close()

    assert client.http_client.is_closed


def test_client_uses_configured_timeout_for_owned_http_client() -> None:
    client = OpenAICompatibleClient(
        base_url="http://local/v1",
        model="embed-model",
        timeout_seconds=240,
    )

    try:
        assert client.http_client.timeout.read == 240
        assert client.http_client.timeout.connect == 240
        assert client.http_client.timeout.write == 240
        assert client.http_client.timeout.pool == 240
    finally:
        client.close()


@pytest.mark.asyncio
async def test_aclose_does_not_close_injected_http_client() -> None:
    http_client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200))
    )
    client = OpenAICompatibleClient(
        base_url="http://local/v1",
        model="embed-model",
        http_client=http_client,
    )

    await client.aclose()

    assert not http_client.is_closed
    await http_client.aclose()
