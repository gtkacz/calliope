import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, Any

import typer
import uvicorn
from sqlalchemy.orm import Session

from calliope.config import Settings
from calliope.db.session import create_session_factory
from calliope.domain.enums import CanonPolicy, ProfileCapability, ProfileKind
from calliope.domain.errors import AppError
from calliope.domain.schemas import ChatRequest, ProfileCreate, SearchRequest, WorkspaceCreate
from calliope.ingest.indexer import Reindexer
from calliope.llm.openai_compatible import OpenAICompatibleClient
from calliope.repositories.chats import ChatRepository
from calliope.retrieval.hybrid import _AsyncRunner, aclose_client
from calliope.services.chat import ChatService
from calliope.services.profiles import ProfileService
from calliope.services.search import SearchService
from calliope.services.workspaces import WorkspaceService

app = typer.Typer(help="Calliope local markdown knowledge backend.")
workspace_app = typer.Typer(help="Manage workspaces.")
profiles_app = typer.Typer(help="Manage model connection profiles.")
sessions_app = typer.Typer(help="Inspect chat sessions.")

app.add_typer(workspace_app, name="workspace")
app.add_typer(profiles_app, name="profiles")
app.add_typer(sessions_app, name="sessions")


@contextmanager
def session_scope(settings: Settings | None = None) -> Iterator[Session]:
    resolved_settings = settings or Settings()
    factory = create_session_factory(resolved_settings.database_url)
    with factory() as session:
        yield session


def api_key_for(api_key_ref: str | None) -> str | None:
    if api_key_ref is None:
        return None

    return os.environ.get(api_key_ref)


def profile_client(
    session: Session,
    capability: ProfileCapability,
    settings: Settings,
) -> OpenAICompatibleClient:
    profile = ProfileService(session).require_default_capability(capability)
    return OpenAICompatibleClient(
        base_url=profile.base_url,
        model=profile.model,
        api_key=api_key_for(profile.api_key_ref),
        timeout_seconds=settings.llm_request_timeout_seconds,
    )


def close_client_suppress(client: object) -> None:
    runner = _AsyncRunner()
    try:
        runner.run(aclose_client(client))
    except Exception:
        pass
    finally:
        runner.close()


def raise_cli_error(exc: AppError) -> None:
    typer.echo(f"{exc.code}: {exc.message}", err=True)
    if exc.details:
        typer.echo(json.dumps(exc.details, sort_keys=True), err=True)
    raise typer.Exit(exc.status_code)


def dump_json(value: Any) -> str:
    if hasattr(value, "model_dump"):
        return json.dumps(value.model_dump(mode="json"), indent=2)
    if isinstance(value, list):
        return json.dumps(
            [
                item.model_dump(mode="json") if hasattr(item, "model_dump") else item
                for item in value
            ],
            indent=2,
        )
    return json.dumps(value, indent=2)


def resolve_workspace_id(session: Session, workspace: str) -> str:
    service = WorkspaceService(session)
    for candidate in service.list():
        if candidate.id == workspace or candidate.name == workspace:
            return candidate.id
    return service.get(workspace).id


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the HTTP API."""
    uvicorn.run("calliope.api.app:create_app", factory=True, host=host, port=port)


@workspace_app.command("add")
def workspace_add(
    path: Annotated[Path, typer.Argument(exists=False, file_okay=False, dir_okay=True)],
    name: Annotated[str, typer.Option("--name")],
) -> None:
    """Create a workspace."""
    try:
        with session_scope() as session:
            workspace = WorkspaceService(session).create(
                WorkspaceCreate(name=name, root_path=str(path))
            )
    except AppError as exc:
        raise_cli_error(exc)

    typer.echo(f"{workspace.id}\t{workspace.name}\t{workspace.root_path}")


@profiles_app.command("add")
def profiles_add(
    name: str,
    kind: ProfileKind,
    base_url: str,
    model: str,
    capability: Annotated[list[ProfileCapability] | None, typer.Option("--capability")] = None,
    api_key_ref: Annotated[str | None, typer.Option("--api-key-ref")] = None,
) -> None:
    """Create a model connection profile."""
    capabilities = capability or []
    if not capabilities:
        typer.echo("At least one --capability is required.", err=True)
        raise typer.Exit(2)

    try:
        with session_scope() as session:
            profile = ProfileService(session).create(
                ProfileCreate(
                    name=name,
                    kind=kind,
                    base_url=base_url,
                    model=model,
                    api_key_ref=api_key_ref,
                    capabilities=capabilities,
                )
            )
    except AppError as exc:
        raise_cli_error(exc)

    typer.echo(f"{profile.id}\t{profile.name}\t{profile.model}")


@profiles_app.command("list")
def profiles_list(
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """List model connection profiles."""
    with session_scope() as session:
        profiles = ProfileService(session).list()

    if json_output:
        typer.echo(dump_json(profiles))
        return

    for profile in profiles:
        capabilities = ",".join(capability.value for capability in profile.capabilities)
        typer.echo(
            f"{profile.id}\t{profile.name}\t{profile.kind.value}\t{profile.model}\t{capabilities}"
        )


@profiles_app.command("test")
def profiles_test(name: str) -> None:
    """Validate that a profile can be loaded."""
    client: OpenAICompatibleClient | None = None
    settings = Settings()
    try:
        with session_scope(settings) as session:
            profile = ProfileService(session).get_by_name(name)
            client = OpenAICompatibleClient(
                base_url=profile.base_url,
                model=profile.model,
                api_key=api_key_for(profile.api_key_ref),
                timeout_seconds=settings.llm_request_timeout_seconds,
            )
    except AppError as exc:
        raise_cli_error(exc)
    finally:
        if client is not None:
            close_client_suppress(client)

    typer.echo(f"ok\t{profile.id}\t{profile.name}\t{profile.model}")


@app.command()
def reindex(workspace: Annotated[str | None, typer.Argument()] = None) -> None:
    """Reindex one workspace or all workspaces."""
    settings = Settings()
    try:
        with session_scope(settings) as session:
            workspace_ids = (
                [resolve_workspace_id(session, workspace)]
                if workspace is not None
                else [candidate.id for candidate in WorkspaceService(session).list()]
            )
            for workspace_id in workspace_ids:
                embedding_client = profile_client(
                    session,
                    ProfileCapability.EMBEDDINGS,
                    settings,
                )
                result = Reindexer(
                    session,
                    embedding_client=embedding_client,
                    close_embedding_client=True,
                ).reindex_workspace(workspace_id)
                typer.echo(
                    f"{workspace_id}\t{result.documents_indexed} documents\t"
                    f"{result.chunks_indexed} chunks"
                )
    except AppError as exc:
        raise_cli_error(exc)


@app.command()
def search(
    query: str,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Search indexed workspace content."""
    settings = Settings()
    try:
        with session_scope(settings) as session:
            embedding_client = profile_client(
                session,
                ProfileCapability.EMBEDDINGS,
                settings,
            )
            service = SearchService(
                session,
                embedding_client,
                close_embedding_client=True,
            )
            operation_error: Exception | None = None
            try:
                response = service.search(SearchRequest(query=query))
            except Exception as exc:
                operation_error = exc
                raise
            finally:
                try:
                    service.close()
                except Exception:
                    if operation_error is None:
                        raise
    except AppError as exc:
        raise_cli_error(exc)

    if json_output:
        typer.echo(dump_json(response))
        return

    for source in response.sources:
        typer.echo(f"{source.score:.4f}\t{source.path}\t{source.heading}")


@app.command()
def chat(
    message: str,
    policy: Annotated[CanonPolicy, typer.Option("--policy")] = CanonPolicy.STRICT_CANON,
) -> None:
    """Ask a question against indexed content."""
    settings = Settings()
    try:
        with session_scope(settings) as session:
            embedding_client = profile_client(
                session,
                ProfileCapability.EMBEDDINGS,
                settings,
            )
            try:
                chat_client = profile_client(session, ProfileCapability.CHAT, settings)
            except Exception:
                close_client_suppress(embedding_client)
                raise

            service = ChatService(
                session,
                embedding_client=embedding_client,
                chat_client=chat_client,
                close_embedding_client=True,
                close_chat_client=True,
            )
            operation_error: Exception | None = None
            try:
                response = service.chat(ChatRequest(message=message, policy=policy))
            except Exception as exc:
                operation_error = exc
                raise
            finally:
                try:
                    service.close()
                except Exception:
                    if operation_error is None:
                        raise
    except AppError as exc:
        raise_cli_error(exc)

    typer.echo(response.answer)
    typer.echo(f"trace\t{response.trace_id}")


@sessions_app.command("show")
def sessions_show(session_id: str) -> None:
    """Show a chat session."""
    try:
        with session_scope() as session:
            chat_session = ChatRepository(session).get_session(session_id)
    except AppError as exc:
        raise_cli_error(exc)

    typer.echo(dump_json(chat_session))
