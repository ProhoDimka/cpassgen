"""Configuration loading from config files and environment variables."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

PERSISTENCE_PATH_ENV = "PASS_GEN_GIT_PERSISTENCE_PATH"
KEY_WORD_ENV = "PASS_GEN_KEY_WORD"

HOME_CONFIG_FILENAME = ".cpassgen/cpassgen.json"

_SECRET_FIELDS = frozenset({"key_word"})

_CONFIG_FIELDS = {
    "git_persistence_path": PERSISTENCE_PATH_ENV,
    "key_word": KEY_WORD_ENV,
}


@dataclass(frozen=True)
class Config:
    """Resolved runtime configuration."""

    git_persistence_path: str | None
    key_word: str | None

    def public_dict(self) -> dict:
        """Return non-secret configuration values as a mapping."""

        return {
            field: value
            for field, value in asdict(self).items()
            if field not in _SECRET_FIELDS
        }


def default_config_path() -> Path:
    """Path of the default config file in the user home directory."""

    return Path.home() / HOME_CONFIG_FILENAME


def _read_json_object(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Config file '{path}' is not valid JSON: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise ValueError(f"Config file '{path}' must contain a JSON object.")
    return data


def _merge_file_values(merged: dict, path: Path, required: bool) -> None:
    if not path.exists():
        if required:
            raise ValueError(f"Config file '{path}' does not exist.")
        return
    data = _read_json_object(path)
    for field in _CONFIG_FIELDS:
        if field in data:
            merged[field] = data[field]


def _merge_env_values(merged: dict) -> None:
    for field, env_name in _CONFIG_FIELDS.items():
        value = os.getenv(env_name)
        if value is not None and value != "":
            merged[field] = value


def load_config(config_path: str | None = None) -> Config:
    """Load configuration by merging file values and environment variables.

    Priority, lowest to highest: home config file, the file passed via
    ``config_path``, environment variables.
    """

    merged: dict = {}
    _merge_file_values(merged, default_config_path(), required=False)
    if config_path:
        _merge_file_values(
            merged,
            Path(config_path).expanduser(),
            required=True,
        )
    _merge_env_values(merged)

    return Config(
        git_persistence_path=merged.get("git_persistence_path"),
        key_word=merged.get("key_word"),
    )
