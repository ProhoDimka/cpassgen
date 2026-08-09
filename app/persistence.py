"""Filesystem-backed storage for password profiles."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict
from pathlib import Path

from app.models import PasswordConstraints, PasswordProfile
from app.validators import validate_constraints

PERSISTENCE_PATH_ENV = "PASS_GEN_GIT_PERSISTENCE_PATH"


class ProfileNotFoundError(ValueError):
    """Raised when the requested profile does not exist in storage."""


class ProfileAlreadyExistsError(ValueError):
    """Raised when attempting to create a profile that already exists."""


def load_repository_from_env() -> "PasswordProfileRepository":
    root = os.getenv(PERSISTENCE_PATH_ENV)
    if not root:
        raise ValueError(
            f"Environment variable {PERSISTENCE_PATH_ENV} must be set.",
        )
    return PasswordProfileRepository(Path(root))


class PasswordProfileRepository:
    """Store profiles as JSON files in a deterministic directory layout."""

    def __init__(self, root: Path):
        self._root = root
        self._profiles_root = root / "profiles"

    def create(self, profile: PasswordProfile) -> PasswordProfile:
        validated_profile = self._validate_profile(profile)
        path = self._profile_path(
            validated_profile.username, validated_profile.resource
        )
        if path.exists():
            raise ProfileAlreadyExistsError(
                "PasswordProfile already exists for given username/resource.",
            )
        self._write_profile(path, validated_profile)
        return validated_profile

    def set(self, profile: PasswordProfile) -> PasswordProfile:
        validated_profile = self._validate_profile(profile)
        path = self._profile_path(
            validated_profile.username, validated_profile.resource
        )
        if not path.exists():
            raise ProfileNotFoundError(
                "PasswordProfile does not exist for given username/resource.",
            )
        self._write_profile(path, validated_profile)
        return validated_profile

    def get(self, username: str, resource: str) -> PasswordProfile:
        path = self._profile_path(username, resource)
        if not path.exists():
            raise ProfileNotFoundError(
                "PasswordProfile does not exist for given username/resource.",
            )
        raw_data = json.loads(path.read_text(encoding="utf-8"))
        constraints = PasswordConstraints(**raw_data["constraints"])
        return PasswordProfile(
            username=raw_data["username"],
            resource=raw_data["resource"],
            constraints=validate_constraints(constraints),
        )

    def _validate_profile(self, profile: PasswordProfile) -> PasswordProfile:
        return PasswordProfile(
            username=profile.username,
            resource=profile.resource,
            constraints=validate_constraints(profile.constraints),
        )

    def _profile_path(self, username: str, resource: str) -> Path:
        identity = f"{username}:{resource}".encode("utf-8")
        key = hashlib.sha256(identity).hexdigest()
        shard = key[:2]
        return self._profiles_root / shard / f"{key}.json"

    def _write_profile(self, path: Path, profile: PasswordProfile) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = asdict(profile)
        payload_json = json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            indent=2,
        )
        path.write_text(
            payload_json + "\n",
            encoding="utf-8",
        )
