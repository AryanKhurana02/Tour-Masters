from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit


BACKEND_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    database_path: Path
    cors_origins: tuple[str, ...]
    enable_llm: bool
    llm_api_key: str | None = field(default=None, repr=False)
    llm_model: str | None = None
    ors_api_key: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not self.cors_origins:
            raise ValueError("CORS_ORIGINS must contain at least one explicit origin.")
        for origin in self.cors_origins:
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.path not in {"", "/"}
                or parsed.query
                or parsed.fragment
                or parsed.username
                or parsed.password
                or origin == "*"
            ):
                raise ValueError(f"CORS origin is not a valid explicit HTTP(S) origin: {origin}")
        if self.enable_llm and not self.llm_model:
            raise ValueError("ENABLE_LLM=true requires LLM_MODEL to be configured.")


def _dotenv_values(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        key, separator, value = line.partition("=")
        if not separator or not re.fullmatch(r"[A-Z][A-Z0-9_]*", key.strip()):
            raise ValueError(f"{path.name}:{line_number}: expected KEY=VALUE.")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key.strip()] = value
    return values


def load_settings(
    environ: dict[str, str] | None = None,
    env_file: str | Path | None = None,
) -> Settings:
    process_values = dict(os.environ if environ is None else environ)
    file_path = Path(env_file) if env_file is not None else BACKEND_ROOT / ".env"
    values = {**_dotenv_values(file_path), **process_values}

    raw_database_path = Path(values.get("DATABASE_PATH", "./pahadpath.db"))
    database_path = (
        raw_database_path if raw_database_path.is_absolute() else BACKEND_ROOT / raw_database_path
    ).resolve()
    raw_origins = values.get("CORS_ORIGINS", "http://localhost:5173")
    cors_origins = tuple(
        dict.fromkeys(origin.strip().rstrip("/") for origin in raw_origins.split(",") if origin.strip())
    )
    raw_llm_enabled = values.get("ENABLE_LLM", "false").strip().casefold()
    if raw_llm_enabled not in {"true", "false"}:
        raise ValueError("ENABLE_LLM must be 'true' or 'false'.")
    return Settings(
        database_path=database_path,
        cors_origins=cors_origins,
        enable_llm=raw_llm_enabled == "true",
        llm_api_key=values.get("LLM_API_KEY") or None,
        llm_model=values.get("LLM_MODEL") or None,
        ors_api_key=values.get("ORS_API_KEY") or None,
    )
