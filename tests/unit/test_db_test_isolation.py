import pytest
from conftest import DEFAULT_TEST_DATABASE_URL, assert_test_database_url
from sqlalchemy.engine import make_url


def test_default_test_database_url_targets_test_database() -> None:
    assert make_url(DEFAULT_TEST_DATABASE_URL).database == "calliope_test"


def test_assert_test_database_url_refuses_app_database() -> None:
    with pytest.raises(RuntimeError, match="Refusing destructive test database operation"):
        assert_test_database_url("postgresql+psycopg://calliope:calliope@localhost:5432/calliope")


def test_assert_test_database_url_allows_test_database() -> None:
    assert_test_database_url("postgresql+psycopg://calliope:calliope@localhost:5432/calliope_test")


@pytest.mark.parametrize(
    "database_name",
    [
        "contest",
        "integration_test_backup",
        "testshared",
    ],
)
def test_assert_test_database_url_refuses_near_miss_test_names(database_name: str) -> None:
    with pytest.raises(RuntimeError, match="Refusing destructive test database operation"):
        assert_test_database_url(f"postgresql+psycopg://calliope:calliope@localhost:5432/{database_name}")
