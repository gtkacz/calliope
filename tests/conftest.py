import os

import pytest


@pytest.fixture(autouse=True)
def clear_calliope_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in tuple(os.environ):
        if key.startswith("CALLIOPE_"):
            monkeypatch.delenv(key, raising=False)
