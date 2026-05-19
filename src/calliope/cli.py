import typer
import uvicorn

app = typer.Typer(help="Calliope local markdown knowledge backend.")


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the HTTP API."""
    uvicorn.run("calliope.api.app:create_app", factory=True, host=host, port=port)
