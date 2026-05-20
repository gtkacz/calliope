from typer.testing import CliRunner

from calliope.cli import app


def test_cli_lists_commands() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "workspace" in result.output
    assert "profiles" in result.output
    assert "search" in result.output
    assert "chat" in result.output


def test_workspace_add_command_persists_workspace(db_session, database_url) -> None:
    result = CliRunner().invoke(
        app,
        ["workspace", "add", "/tmp/world", "--name", "World"],
        env={"CALLIOPE_DATABASE_URL": database_url},
    )

    assert result.exit_code == 0
    assert "World" in result.output
