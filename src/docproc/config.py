"""Configuration loader for PaperRoute.

Reads config.yaml, substitutes environment variables, resolves paths,
validates constraints, and caches the result as a singleton.
"""

import os
import re
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

_ENV_VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")


class DirectoriesConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    watch: Path
    output: Path


class DeepfellowConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    base_url: str = Field(min_length=1)
    responses_endpoint: str = Field(min_length=1)
    ocr_endpoint: str = Field(min_length=1)
    api_key: str
    vision_model: str = Field(min_length=1)
    llm_model: str = Field(min_length=1)
    rag_collection: str = Field(min_length=1)

    @field_validator("api_key")
    @classmethod
    def api_key_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            msg = "API key must not be blank"
            raise ValueError(msg)
        return v


class Recipient(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1)
    tags: tuple[str, ...] = Field(min_length=1)

    @field_validator("tags")
    @classmethod
    def tags_must_not_contain_blanks(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        for tag in v:
            if not tag.strip():
                msg = "Tags must not contain blank strings"
                raise ValueError(msg)
        return v


class Config(BaseModel):
    model_config = ConfigDict(frozen=True)

    directories: DirectoriesConfig
    deepfellow: DeepfellowConfig
    recipients: tuple[Recipient, ...] = Field(min_length=1)


_config: Config | None = None


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
    """Validate runtime constraints that depend on the environment."""
    if not config.directories.watch.exists():
        msg = f"Watch directory does not exist: {config.directories.watch}"
        raise FileNotFoundError(msg)


def load_config(config_path: Path | None = None) -> Config:
    """Load, parse, validate, and cache the configuration."""
    global _config
    if _config is not None:
        if config_path is None:
            return _config
        msg = "Configuration is already loaded. Call _reset_config() first to reload."
        raise RuntimeError(msg)

    load_dotenv()

    if config_path is None:
        root = _find_project_root()
        config_path = root / "config.yaml"
    else:
        config_path = config_path.resolve()

    root = config_path.parent

    if not config_path.is_file():
        msg = f"Configuration file not found: {config_path}"
        raise FileNotFoundError(msg)

    try:
        text = config_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        msg = f"Failed to read configuration file {config_path}: {e}"
        raise ValueError(msg) from e

    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as e:
        msg = f"Failed to parse configuration file {config_path}: {e}"
        raise ValueError(msg) from e

    if not isinstance(raw, dict):
        msg = f"Configuration file is empty or invalid: {config_path}"
        raise ValueError(msg)

    try:
        processed = _process_env_vars(raw)
    except ValueError as e:
        msg = f"Invalid configuration in {config_path}: {e}"
        raise ValueError(msg) from e

    try:
        config = Config.model_validate(processed)
    except ValidationError as e:
        msg = f"Invalid configuration in {config_path}: {e}"
        raise ValueError(msg) from e

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
