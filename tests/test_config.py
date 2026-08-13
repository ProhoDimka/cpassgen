import json

import pytest

from app import config as config_module
from app.config import load_config


def _write_config(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def _clear_env(monkeypatch):
    monkeypatch.delenv("PASS_GEN_GIT_PERSISTENCE_PATH", raising=False)
    monkeypatch.delenv("PASS_GEN_KEY_WORD", raising=False)


def test_load_config_from_env_only(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    monkeypatch.setattr(
        config_module, "default_config_path", lambda: tmp_path / "home.json"
    )
    monkeypatch.setenv(
        "PASS_GEN_GIT_PERSISTENCE_PATH", str(tmp_path / "profiles")
    )

    config = load_config()

    assert config.git_persistence_path == str(tmp_path / "profiles")
    assert config.key_word is None


def test_load_config_from_home_file(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    home = tmp_path / "home.json"
    _write_config(
        home,
        {"git_persistence_path": "/home/profiles", "key_word": "home-secret"},
    )
    monkeypatch.setattr(config_module, "default_config_path", lambda: home)

    config = load_config()

    assert config.git_persistence_path == "/home/profiles"
    assert config.key_word == "home-secret"


def test_explicit_config_file_overrides_home(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    home = tmp_path / "home.json"
    _write_config(
        home,
        {"git_persistence_path": "/home/profiles", "key_word": "home-secret"},
    )
    monkeypatch.setattr(config_module, "default_config_path", lambda: home)
    override = tmp_path / "override.json"
    _write_config(override, {"git_persistence_path": "/override/profiles"})

    config = load_config(str(override))

    assert config.git_persistence_path == "/override/profiles"
    assert config.key_word == "home-secret"


def test_env_vars_override_config_files(monkeypatch, tmp_path):
    home = tmp_path / "home.json"
    _write_config(
        home,
        {"git_persistence_path": "/home/profiles", "key_word": "home-secret"},
    )
    monkeypatch.setattr(config_module, "default_config_path", lambda: home)
    monkeypatch.setenv("PASS_GEN_GIT_PERSISTENCE_PATH", "/env/profiles")
    monkeypatch.setenv("PASS_GEN_KEY_WORD", "env-secret")

    config = load_config()

    assert config.git_persistence_path == "/env/profiles"
    assert config.key_word == "env-secret"


def test_missing_explicit_config_file_raises(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    monkeypatch.setattr(
        config_module, "default_config_path", lambda: tmp_path / "home.json"
    )

    with pytest.raises(ValueError, match="does not exist"):
        load_config(str(tmp_path / "missing.json"))


def test_invalid_json_config_file_raises(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    monkeypatch.setattr(
        config_module, "default_config_path", lambda: tmp_path / "home.json"
    )
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")

    with pytest.raises(ValueError, match="not valid JSON"):
        load_config(str(bad))


def test_config_file_not_a_json_object_raises(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    monkeypatch.setattr(
        config_module, "default_config_path", lambda: tmp_path / "home.json"
    )
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(["not", "an", "object"]))

    with pytest.raises(ValueError, match="JSON object"):
        load_config(str(bad))
