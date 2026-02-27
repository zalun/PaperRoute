"""Tests for the configuration system."""

from pathlib import Path
from unittest import mock

import pytest
import yaml

from docproc.config import (
    Config,
    _find_project_root,
    _process_env_vars,
    _reset_config,
    _substitute_env_vars,
    get_config,
    load_config,
)

MINIMAL_CONFIG = {
    "directories": {"watch": "./inbox", "output": "./output"},
    "deepfellow": {
        "base_url": "http://localhost:8000",
        "responses_endpoint": "/v1/responses",
        "ocr_endpoint": "/v1/ocr",
        "api_key": "test-key",
        "vision_model": "gpt-4-vision",
        "llm_model": "deepseek",
        "rag_collection": "documents",
    },
    "recipients": [{"name": "Test User", "tags": ["tag1", "tag2"]}],
}


@pytest.fixture(autouse=True)
def reset_config():
    _reset_config()
    yield
    _reset_config()


@pytest.fixture()
def config_dir(tmp_path: Path) -> Path:
    """Create a temporary directory with config.yaml and required dirs."""
    (tmp_path / "inbox").mkdir()
    (tmp_path / "output").mkdir()
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump(MINIMAL_CONFIG))
    return tmp_path


# --- _substitute_env_vars ---


@pytest.mark.parametrize(
    "template,env,expected",
    [
        ("${MY_VAR}", {"MY_VAR": "hello"}, "hello"),
        ("prefix-${MY_VAR}-suffix", {"MY_VAR": "mid"}, "prefix-mid-suffix"),
        ("no vars here", {}, "no vars here"),
        ("${A}and${B}", {"A": "1", "B": "2"}, "1and2"),
    ],
)
def test_substitute_env_vars_replaces_patterns(template, env, expected):
    with mock.patch.dict("os.environ", env, clear=True):
        assert _substitute_env_vars(template) == expected


def test_substitute_env_vars_raises_on_missing_var():
    with (
        mock.patch.dict("os.environ", {}, clear=True),
        pytest.raises(ValueError, match="MISSING_VAR"),
    ):
        _substitute_env_vars("${MISSING_VAR}")


# --- _process_env_vars ---


def test_process_env_vars_handles_nested_dict():
    data = {"outer": {"inner": "${VAR}"}}
    with mock.patch.dict("os.environ", {"VAR": "value"}):
        result = _process_env_vars(data)
    assert result == {"outer": {"inner": "value"}}


def test_process_env_vars_handles_list():
    data = ["${VAR}", "plain"]
    with mock.patch.dict("os.environ", {"VAR": "value"}):
        result = _process_env_vars(data)
    assert result == ["value", "plain"]


def test_process_env_vars_passes_non_strings_through():
    assert _process_env_vars(42) == 42
    assert _process_env_vars(3.14) == 3.14
    assert _process_env_vars(True) is True
    assert _process_env_vars(None) is None


# --- load_config ---


@mock.patch("docproc.config.load_dotenv")
def test_load_config_returns_typed_config(mock_load_dotenv, config_dir):
    config = load_config(config_dir / "config.yaml")
    assert isinstance(config, Config)
    assert config.deepfellow.base_url == "http://localhost:8000"
    assert config.deepfellow.api_key == "test-key"
    assert mock_load_dotenv.call_count == 1


@mock.patch("docproc.config.load_dotenv")
def test_load_config_resolves_relative_paths(mock_load_dotenv, config_dir):
    config = load_config(config_dir / "config.yaml")
    assert config.directories.watch.is_absolute()
    assert config.directories.output.is_absolute()
    assert config.directories.watch == (config_dir / "inbox").resolve()
    assert config.directories.output == (config_dir / "output").resolve()


@mock.patch("docproc.config.load_dotenv")
def test_load_config_loads_recipients(mock_load_dotenv, config_dir):
    config = load_config(config_dir / "config.yaml")
    assert len(config.recipients) == 1
    assert config.recipients[0].name == "Test User"
    assert config.recipients[0].tags == ("tag1", "tag2")


@mock.patch("docproc.config.load_dotenv")
def test_load_config_caches_singleton(mock_load_dotenv, config_dir):
    config1 = load_config(config_dir / "config.yaml")
    config2 = load_config()
    assert config1 is config2


@mock.patch("docproc.config.load_dotenv")
def test_reset_config_clears_cache(mock_load_dotenv, config_dir):
    config1 = load_config(config_dir / "config.yaml")
    _reset_config()
    config2 = load_config(config_dir / "config.yaml")
    assert config1 is not config2


# --- validation errors ---


@mock.patch("docproc.config.load_dotenv")
def test_load_config_raises_on_missing_watch_dir(mock_load_dotenv, tmp_path):
    (tmp_path / "output").mkdir()
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump(MINIMAL_CONFIG))
    with pytest.raises(FileNotFoundError, match="Watch directory"):
        load_config(config_path)


@mock.patch("docproc.config.load_dotenv")
def test_load_config_raises_on_empty_recipients(mock_load_dotenv, config_dir):
    config_data = {**MINIMAL_CONFIG, "recipients": []}
    (config_dir / "config.yaml").write_text(yaml.dump(config_data))
    with pytest.raises(ValueError, match="Invalid configuration"):
        load_config(config_dir / "config.yaml")


@mock.patch("docproc.config.load_dotenv")
def test_load_config_raises_on_missing_env_var(mock_load_dotenv, config_dir):
    config_data = {
        **MINIMAL_CONFIG,
        "deepfellow": {**MINIMAL_CONFIG["deepfellow"], "api_key": "${NONEXISTENT}"},
    }
    (config_dir / "config.yaml").write_text(yaml.dump(config_data))
    with (
        mock.patch.dict("os.environ", {}, clear=True),
        pytest.raises(ValueError, match="NONEXISTENT"),
    ):
        load_config(config_dir / "config.yaml")


@mock.patch("docproc.config.load_dotenv")
def test_load_config_raises_on_blank_api_key(mock_load_dotenv, config_dir):
    config_data = {
        **MINIMAL_CONFIG,
        "deepfellow": {**MINIMAL_CONFIG["deepfellow"], "api_key": "   "},
    }
    (config_dir / "config.yaml").write_text(yaml.dump(config_data))
    with pytest.raises(ValueError, match="Invalid configuration"):
        load_config(config_dir / "config.yaml")


@mock.patch("docproc.config.load_dotenv")
def test_load_config_raises_on_empty_yaml(mock_load_dotenv, config_dir):
    (config_dir / "config.yaml").write_text("")
    with pytest.raises(ValueError, match="empty or invalid"):
        load_config(config_dir / "config.yaml")


@mock.patch("docproc.config.load_dotenv")
def test_load_config_raises_on_missing_config_file(mock_load_dotenv, tmp_path):
    with pytest.raises(FileNotFoundError, match="Configuration file not found"):
        load_config(tmp_path / "nonexistent.yaml")


@mock.patch("docproc.config.load_dotenv")
def test_load_config_raises_on_invalid_yaml(mock_load_dotenv, config_dir):
    (config_dir / "config.yaml").write_text("{{invalid: yaml: [")
    with pytest.raises(ValueError, match="Failed to parse"):
        load_config(config_dir / "config.yaml")


# --- get_config ---


@mock.patch("docproc.config.load_dotenv")
def test_get_config_returns_cached_instance(mock_load_dotenv, config_dir):
    config1 = load_config(config_dir / "config.yaml")
    config2 = get_config()
    assert config1 is config2


@mock.patch("docproc.config.load_dotenv")
def test_get_config_loads_on_first_call(mock_load_dotenv, config_dir):
    import docproc.config as config_module

    with mock.patch.object(
        config_module, "_find_project_root", return_value=config_dir
    ):
        config = get_config()
    assert isinstance(config, Config)


# --- _find_project_root ---


def test_find_project_root_raises_when_no_config_found(tmp_path):
    fake_file = tmp_path / "sub" / "deep" / "file.py"
    fake_file.parent.mkdir(parents=True)
    fake_file.touch()
    import docproc.config as config_module

    with (
        mock.patch.object(config_module, "__file__", str(fake_file)),
        pytest.raises(FileNotFoundError, match="config.yaml"),
    ):
        _find_project_root()


def test_find_project_root_finds_config_in_parent(tmp_path):
    (tmp_path / "config.yaml").touch()
    fake_file = tmp_path / "src" / "pkg" / "module.py"
    fake_file.parent.mkdir(parents=True)
    fake_file.touch()
    import docproc.config as config_module

    with mock.patch.object(config_module, "__file__", str(fake_file)):
        root = _find_project_root()
    assert root == tmp_path
