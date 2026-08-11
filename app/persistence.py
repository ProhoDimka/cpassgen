"""Filesystem-backed storage for password profiles."""

from __future__ import annotations

import hashlib
import json
import os
from copy import deepcopy
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
        payload = self._make_payload(validated_profile, version_history=[])
        self._write_payload(path, payload)
        return validated_profile

    def bump(
        self,
        username: str,
        resource: str,
        new_constraints: PasswordConstraints | None = None,
    ) -> PasswordProfile:
        path = self._profile_path(username, resource)
        if not path.exists():
            raise ProfileNotFoundError(
                "PasswordProfile does not exist for given username/resource.",
            )
        raw = path.read_text(encoding="utf-8")
        existing_data = json.loads(raw)
        constraints_raw = existing_data["constraints"]
        existing_constraints = PasswordConstraints(**constraints_raw)
        existing_version = existing_data.get("generation_version", 1)

        new_version = existing_version + 1
        constraints = (
            validate_constraints(new_constraints)
            if new_constraints is not None
            else existing_constraints
        )

        validated_profile = PasswordProfile(
            username=username,
            resource=resource,
            constraints=constraints,
            generation_version=new_version,
        )

        history = deepcopy(existing_data.get("version_history", []))
        any_change = constraints != existing_constraints
        if any_change:
            history.append(
                {
                    "generation_version": existing_version,
                    "constraints": existing_data["constraints"],
                }
            )

        payload = self._make_payload(
            validated_profile,
            version_history=history,
        )
        self._write_payload(path, payload)
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
            generation_version=raw_data.get("generation_version", 1),
        )

    def _validate_profile(self, profile: PasswordProfile) -> PasswordProfile:
        if profile.generation_version < 1:
            raise ValueError("generation_version must be >= 1.")
        return PasswordProfile(
            username=profile.username,
            resource=profile.resource,
            constraints=validate_constraints(profile.constraints),
            generation_version=profile.generation_version,
        )

    def _profile_path(self, username: str, resource: str) -> Path:
        identity = f"{username}:{resource}".encode("utf-8")
        key = hashlib.sha256(identity).hexdigest()
        shard = key[:2]
        return self._profiles_root / shard / f"{key}.json"

    @staticmethod
    def _make_payload(profile: PasswordProfile, version_history: list) -> dict:
        payload = asdict(profile)
        payload["version_history"] = version_history
        return payload

    def _write_payload(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
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
