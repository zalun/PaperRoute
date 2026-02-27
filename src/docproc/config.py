"""Configuration loader for PaperRoute.

Reads config.yaml, substitutes environment variables, resolves paths,
validates constraints, and caches the result as a singleton.
"""

import os
import re
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel

_ENV_VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")

_config: Config | None = None


class DirectoriesConfig(BaseModel):
    watch: Path
    output: Path


class DeepfellowConfig(BaseModel):
    base_url: str
    responses_endpoint: str
    api_key: str
    vision_model: str
    llm_model: str
    rag_collection: str


class Recipient(BaseModel):
    name: str
    tags: list[str]


class Config(BaseModel):
    directories: DirectoriesConfig
    deepfellow: DeepfellowConfig
    recipients: list[Recipient]


def _substitute_env_vars(value: str) -> str:
    """Replace ${VAR} patterns with environment variable values."""

    def replacer(match: re.Match[str]) -> str:
        var_name = match.group(1)
        try:
            return os.environ[var_name]
        except KeyError:
            msg = f"Environment variable '{var_name}' is not set"
            raise ValueError(msg) from None

    return _ENV_VAR_PATTERN.sub(replacer, value)


def _process_env_vars(data: object) -> object:
    """Recursively walk parsed YAML and substitute env vars in strings."""
    if isinstance(data, str):
        return _substitute_env_vars(data)
    if isinstance(data, dict):
        return {k: _process_env_vars(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_process_env_vars(item) for item in data]
    return data


def _find_project_root() -> Path:
    """Walk up from this file's directory looking for config.yaml."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "config.yaml").exists():
            return current
        current = current.parent
    msg = "Could not find config.yaml in any parent directory"
    raise FileNotFoundError(msg)


def _resolve_paths(config: Config, root: Path) -> Config:
    """Resolve relative directory paths against the project root."""
    watch = config.directories.watch
    output = config.directories.output
    if not watch.is_absolute():
        watch = (root / watch).resolve()
    if not output.is_absolute():
        output = (root / output).resolve()
    return config.model_copy(
        update={
            "directories": config.directories.model_copy(
                update={"watch": watch, "output": output}
            )
        }
    )


def _validate_config(config: Config) -> None:
    """Validate configuration constraints."""
    if not config.directories.watch.exists():
        msg = f"Watch directory does not exist: {config.directories.watch}"
        raise FileNotFoundError(msg)
    if not config.recipients:
        msg = "Recipients list must not be empty"
        raise ValueError(msg)
    if not config.deepfellow.api_key.strip():
        msg = "API key must not be blank"
        raise ValueError(msg)


def load_config(config_path: Path | None = None) -> Config:
    """Load, parse, validate, and cache the configuration."""
    global _config
    if _config is not None:
        return _config

    load_dotenv()

    if config_path is None:
        root = _find_project_root()
        config_path = root / "config.yaml"
    else:
        config_path = config_path.resolve()

    root = config_path.parent

    raw = yaml.safe_load(config_path.read_text())
    processed = _process_env_vars(raw)
    config = Config.model_validate(processed)
    config = _resolve_paths(config, root)
    _validate_config(config)

    _config = config
    return _config


def get_config() -> Config:
    """Return cached config, loading it if necessary."""
    if _config is None:
        return load_config()
    return _config


def _reset_config() -> None:
    """Clear the singleton cache (for tests)."""
    global _config
    _config = None
