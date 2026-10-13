from pathlib import Path

import pytest

from app.config import Settings, load_settings


def test_backend_env_file_is_read_but_process_environment_wins(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_PATH=./from-file.db\nCORS_ORIGINS=https://example.test\n"
        "ENABLE_LLM=false\nLLM_API_KEY=do-not-print\n",
        encoding="utf-8",
    )

    settings = load_settings({"DATABASE_PATH": "./from-process.db"}, env_file)

    assert settings.database_path.name == "from-process.db"
    assert settings.cors_origins == ("https://example.test",)
    assert "do-not-print" not in repr(settings)


@pytest.mark.parametrize(
    "origins",
    ["*", "https://user:pass@example.test", "https://example.test/path", "javascript:alert(1)"],
)
def test_settings_reject_unsafe_cors_origins(origins: str) -> None:
    with pytest.raises(ValueError, match="CORS origin"):
        Settings(Path("catalogue.db"), tuple(origins.split(",")), False)


def test_llm_enabled_requires_a_model_name() -> None:
    with pytest.raises(ValueError, match="LLM_MODEL"):
        Settings(Path("catalogue.db"), ("http://localhost:5173",), True)


def test_malformed_env_line_fails_with_filename_and_line(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("not-a-setting\n", encoding="utf-8")

    with pytest.raises(ValueError, match=r"\.env:1"):
        load_settings({}, env_file)
