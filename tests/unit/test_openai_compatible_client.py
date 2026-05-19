import httpx
import pytest

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

    assert answer == "Grounded answer"
