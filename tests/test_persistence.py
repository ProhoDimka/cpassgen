import json

import pytest

from app.models import PasswordConstraints, PasswordProfile
from app.persistence import (
    PasswordProfileRepository,
    ProfileAlreadyExistsError,
    ProfileNotFoundError,
)


def _profile(length=24, generation_version=1):
    return PasswordProfile(
        username="user",
        resource="resource",
        constraints=PasswordConstraints(
            length=length,
            upper=0,
            lower=0,
            digits=0,
            specials=0,
            mask=0,
        ),
        generation_version=generation_version,
    )


def test_create_and_get_profile(tmp_path):
    repository = PasswordProfileRepository(tmp_path)
    profile = _profile()

    repository.create(profile)
    loaded = repository.get("user", "resource")

    assert loaded == profile


def test_create_existing_profile_fails(tmp_path):
    repository = PasswordProfileRepository(tmp_path)
    profile = _profile()

    repository.create(profile)

    with pytest.raises(ProfileAlreadyExistsError):
        repository.create(profile)


def test_bump_updates_constraints(tmp_path):
    repository = PasswordProfileRepository(tmp_path)
    repository.create(_profile())

    new_constraints = PasswordConstraints(
        length=8,
        upper=0,
        lower=0,
        digits=0,
        specials=0,
        mask=0,
    )
    result = repository.bump("user", "resource", new_constraints=new_constraints)
    loaded = repository.get("user", "resource")

    assert result.generation_version == 2
    assert loaded.constraints.length == 8
    assert loaded.generation_version == 2


def test_bump_missing_profile_fails(tmp_path):
    repository = PasswordProfileRepository(tmp_path)

    with pytest.raises(ProfileNotFoundError):
        repository.bump("user", "resource")


def test_storage_layout_uses_profiles_shards(tmp_path):
    repository = PasswordProfileRepository(tmp_path)

    repository.create(_profile())

    profiles_dir = tmp_path / "profiles"
    shard_dirs = [entry for entry in profiles_dir.iterdir() if entry.is_dir()]
    json_files = list(profiles_dir.rglob("*.json"))

    assert len(shard_dirs) == 1
    assert len(shard_dirs[0].name) == 2
    assert len(json_files) == 1


def test_create_stores_generation_version_in_json(tmp_path):
    repository = PasswordProfileRepository(tmp_path)
    profile = _profile(generation_version=3)

    repository.create(profile)
    loaded = repository.get("user", "resource")

    assert loaded.generation_version == 3


def test_get_returns_default_version_for_legacy_profiles(tmp_path):
    repository = PasswordProfileRepository(tmp_path)
    profile = _profile()

    repository.create(profile)

    json_files = list((tmp_path / "profiles").rglob("*.json"))
    raw = json.loads(json_files[0].read_text(encoding="utf-8"))
    del raw["generation_version"]

    json_files[0].write_text(
        json.dumps(raw, ensure_ascii=True, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    loaded = repository.get("user", "resource")
    assert loaded.generation_version == 1


def test_bump_always_increments_version(tmp_path):
    repository = PasswordProfileRepository(tmp_path)
    repository.create(_profile(length=24, generation_version=1))

    result = repository.bump("user", "resource")
    loaded = repository.get("user", "resource")

    assert result.generation_version == 2
    assert loaded.generation_version == 2
    assert loaded.constraints.length == 24


def test_bump_records_version_history(tmp_path):
    repository = PasswordProfileRepository(tmp_path)
    repository.create(_profile(length=24, generation_version=1))

    new_constraints = PasswordConstraints(
        length=16,
        upper=0,
        lower=0,
        digits=0,
        specials=0,
        mask=0,
    )
    repository.bump("user", "resource", new_constraints=new_constraints)

    json_files = list((tmp_path / "profiles").rglob("*.json"))
    raw = json.loads(json_files[0].read_text(encoding="utf-8"))

    assert "version_history" in raw
    assert len(raw["version_history"]) == 1
    entry = raw["version_history"][0]
    assert entry["generation_version"] == 1
    assert entry["constraints"]["length"] == 24


def test_bump_version_only_records_previous_version(tmp_path):
    repository = PasswordProfileRepository(tmp_path)
    repository.create(_profile(length=24, generation_version=1))

    repository.bump("user", "resource")

    json_files = list((tmp_path / "profiles").rglob("*.json"))
    raw = json.loads(json_files[0].read_text(encoding="utf-8"))

    assert raw["generation_version"] == 2
    assert len(raw["version_history"]) == 1
    entry = raw["version_history"][0]
    assert entry["generation_version"] == 1
    assert entry["constraints"]["length"] == 24


def test_bump_multiple_times_accumulates_history(tmp_path):
    repository = PasswordProfileRepository(tmp_path)
    repository.create(_profile(length=24, generation_version=1))

    repository.bump(
        "user",
        "resource",
        new_constraints=PasswordConstraints(
            length=20,
            upper=0,
            lower=0,
            digits=0,
            specials=0,
            mask=0,
        ),
    )
    repository.bump(
        "user",
        "resource",
        new_constraints=PasswordConstraints(
            length=16,
            upper=0,
            lower=0,
            digits=0,
            specials=0,
            mask=0,
        ),
    )

    json_files = list((tmp_path / "profiles").rglob("*.json"))
    raw = json.loads(json_files[0].read_text(encoding="utf-8"))

    assert len(raw["version_history"]) == 2
    assert raw["version_history"][0]["generation_version"] == 1
    assert raw["version_history"][1]["generation_version"] == 2
    assert raw["generation_version"] == 3


def test_bump_no_constraints_change_still_increments(tmp_path):
    repository = PasswordProfileRepository(tmp_path)
    repository.create(_profile(length=24, generation_version=1))

    result = repository.bump("user", "resource")
    loaded = repository.get("user", "resource")

    assert result.generation_version == 2
    assert loaded.generation_version == 2
    assert loaded.constraints == result.constraints
