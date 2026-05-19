import typer
import uvicorn

from calliope.config import Settings

app = typer.Typer(help="Calliope local markdown knowledge backend.")


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the HTTP API."""
    Settings()
    uvicorn.run("calliope.api.app:create_app", factory=True, host=host, port=port)
