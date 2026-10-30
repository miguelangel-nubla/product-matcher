"""Tests for Docker-secrets style <NAME>_FILE support."""

from pathlib import Path

import pytest

from app.config.loader import _substitute_env_vars
from app.core.config import SECRET_SETTINGS, Settings
from app.core.secret_files import getenv_or_file

DUMMY_SECRET = "dummy-secret-value"


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """Minimal environment for Settings, isolated from .env and the host env."""
    for name in SECRET_SETTINGS:
        monkeypatch.delenv(name, raising=False)
        monkeypatch.delenv(f"{name}_FILE", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "local")
    monkeypatch.setenv("PROJECT_NAME", "test")
    monkeypatch.setenv("POSTGRES_SERVER", "localhost")
    monkeypatch.setenv("POSTGRES_USER", "postgres")
    monkeypatch.setenv("FIRST_SUPERUSER", "admin@example.com")
    monkeypatch.setenv("FIRST_SUPERUSER_PASSWORD", "dummy-superuser-password")
    return monkeypatch


def make_settings() -> Settings:
    return Settings(_env_file=None)  # type: ignore[call-arg]


def write(tmp_path: Path, name: str, content: str) -> str:
    path = tmp_path / name
    path.write_text(content)
    return str(path)


@pytest.mark.parametrize(
    "name",
    ["SECRET_KEY", "POSTGRES_PASSWORD", "FIRST_SUPERUSER_PASSWORD", "SMTP_PASSWORD"],
)
def test_file_only(clean_env: pytest.MonkeyPatch, tmp_path: Path, name: str) -> None:
    clean_env.delenv(name, raising=False)
    clean_env.setenv(f"{name}_FILE", write(tmp_path, name, DUMMY_SECRET))
    assert getattr(make_settings(), name) == DUMMY_SECRET


def test_sentry_dsn_file(clean_env: pytest.MonkeyPatch, tmp_path: Path) -> None:
    dsn = "https://dummykey@sentry.example.com/1"
    clean_env.setenv("SENTRY_DSN_FILE", write(tmp_path, "dsn", dsn + "\n"))
    assert str(make_settings().SENTRY_DSN) == dsn


def test_env_only(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("SECRET_KEY", DUMMY_SECRET)
    settings = make_settings()
    assert settings.SECRET_KEY == DUMMY_SECRET
    assert settings.FIRST_SUPERUSER_PASSWORD == "dummy-superuser-password"


def test_file_wins_over_env(clean_env: pytest.MonkeyPatch, tmp_path: Path) -> None:
    clean_env.setenv("POSTGRES_PASSWORD", "dummy-from-env")
    clean_env.setenv("POSTGRES_PASSWORD_FILE", write(tmp_path, "pw", "dummy-from-file"))
    settings = make_settings()
    assert settings.POSTGRES_PASSWORD == "dummy-from-file"
    assert "dummy-from-file" in str(settings.SQLALCHEMY_DATABASE_URI)


def test_file_wins_over_dotenv(clean_env: pytest.MonkeyPatch, tmp_path: Path) -> None:
    dotenv = write(tmp_path, ".env", "SECRET_KEY=dummy-from-dotenv\n")
    clean_env.setenv("SECRET_KEY_FILE", write(tmp_path, "key", "dummy-from-file"))
    settings = Settings(_env_file=dotenv)  # type: ignore[call-arg]
    assert settings.SECRET_KEY == "dummy-from-file"


def test_trailing_newline_stripped(
    clean_env: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    clean_env.setenv("SECRET_KEY_FILE", write(tmp_path, "key", DUMMY_SECRET + "\n"))
    assert make_settings().SECRET_KEY == DUMMY_SECRET


def test_only_one_trailing_newline_stripped(
    clean_env: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    clean_env.setenv("SECRET_KEY_FILE", write(tmp_path, "key", DUMMY_SECRET + "\n\n"))
    assert make_settings().SECRET_KEY == DUMMY_SECRET + "\n"


def test_missing_file_error(clean_env: pytest.MonkeyPatch, tmp_path: Path) -> None:
    missing = str(tmp_path / "does-not-exist")
    clean_env.setenv("SECRET_KEY", DUMMY_SECRET)
    clean_env.setenv("SECRET_KEY_FILE", missing)
    with pytest.raises(ValueError) as exc_info:
        make_settings()
    message = str(exc_info.value)
    assert "SECRET_KEY_FILE" in message
    assert missing in message
    assert DUMMY_SECRET not in message


@pytest.mark.parametrize("content", ["", "\n"])
def test_empty_file_error(
    clean_env: pytest.MonkeyPatch, tmp_path: Path, content: str
) -> None:
    path = write(tmp_path, "empty", content)
    clean_env.setenv("FIRST_SUPERUSER_PASSWORD_FILE", path)
    with pytest.raises(ValueError, match="FIRST_SUPERUSER_PASSWORD_FILE") as exc_info:
        make_settings()
    assert path in str(exc_info.value)


def test_empty_file_var_is_ignored(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("SECRET_KEY", DUMMY_SECRET)
    clean_env.setenv("SECRET_KEY_FILE", "")
    assert make_settings().SECRET_KEY == DUMMY_SECRET


def test_getenv_or_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("PM_TEST_VAR", raising=False)
    monkeypatch.delenv("PM_TEST_VAR_FILE", raising=False)
    assert getenv_or_file("PM_TEST_VAR") is None
    monkeypatch.setenv("PM_TEST_VAR", "dummy-from-env")
    assert getenv_or_file("PM_TEST_VAR") == "dummy-from-env"
    monkeypatch.setenv("PM_TEST_VAR_FILE", write(tmp_path, "v", "dummy-from-file\n"))
    assert getenv_or_file("PM_TEST_VAR") == "dummy-from-file"


def test_yaml_substitution_honours_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("GROCY_API_KEY", "dummy-from-env")
    monkeypatch.setenv("GROCY_API_KEY_FILE", write(tmp_path, "k", "dummy-from-file\n"))
    config = {"api_key": "${GROCY_API_KEY:-demo_api_key_1}"}
    assert _substitute_env_vars(config) == {"api_key": "dummy-from-file"}


def test_yaml_substitution_missing_file_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    missing = str(tmp_path / "nope")
    monkeypatch.setenv("GROCY_API_KEY_FILE", missing)
    with pytest.raises(ValueError, match="GROCY_API_KEY_FILE"):
        _substitute_env_vars("${GROCY_API_KEY:-demo_api_key_1}")
