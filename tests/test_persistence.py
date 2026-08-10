import json

import pytest

from app.models import PasswordConstraints, PasswordProfile
from app.persistence import (
    PasswordProfileRepository,
    ProfileAlreadyExistsError,
    ProfileNotFoundError,
)


def _profile(min_length=24, max_length=32, generation_version=1):
    return PasswordProfile(
        username="user",
        resource="resource",
        constraints=PasswordConstraints(
            min_length=min_length,
            max_length=max_length,
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


def test_set_updates_constraints(tmp_path):
    repository = PasswordProfileRepository(tmp_path)
    repository.create(_profile())

    updated = _profile(min_length=8, max_length=8, generation_version=2)
    repository.set(updated)
    loaded = repository.get("user", "resource")

    assert loaded.constraints.min_length == 8
    assert loaded.constraints.max_length == 8
    assert loaded.generation_version == 2


def test_set_missing_profile_fails(tmp_path):
    repository = PasswordProfileRepository(tmp_path)

    with pytest.raises(ProfileNotFoundError):
        repository.set(_profile())


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


def test_set_constraints_change_without_version_bump_fails(tmp_path):
    repository = PasswordProfileRepository(tmp_path)
    repository.create(_profile(min_length=24, max_length=32, generation_version=1))

    updated = _profile(min_length=8, max_length=8, generation_version=1)

    with pytest.raises(
        ValueError,
        match="generation_version was not incremented",
    ):
        repository.set(updated)


def test_set_records_version_history(tmp_path):
    repository = PasswordProfileRepository(tmp_path)
    repository.create(_profile(min_length=24, max_length=32, generation_version=1))

    updated = _profile(min_length=16, max_length=16, generation_version=2)
    repository.set(updated)

    json_files = list((tmp_path / "profiles").rglob("*.json"))
    raw = json.loads(json_files[0].read_text(encoding="utf-8"))

    assert "version_history" in raw
    assert len(raw["version_history"]) == 1
    entry = raw["version_history"][0]
    assert entry["generation_version"] == 1
    assert entry["constraints"]["min_length"] == 24
    assert entry["constraints"]["max_length"] == 32


def test_set_version_bump_only_records_history(tmp_path):
    repository = PasswordProfileRepository(tmp_path)
    repository.create(_profile(min_length=24, max_length=32, generation_version=1))

    updated = _profile(min_length=24, max_length=32, generation_version=2)
    repository.set(updated)

    json_files = list((tmp_path / "profiles").rglob("*.json"))
    raw = json.loads(json_files[0].read_text(encoding="utf-8"))

    assert len(raw["version_history"]) == 1
    entry = raw["version_history"][0]
    assert entry["generation_version"] == 1


def test_set_multiple_times_accumulates_history(tmp_path):
    repository = PasswordProfileRepository(tmp_path)
    repository.create(_profile(min_length=24, max_length=32, generation_version=1))

    repository.set(_profile(min_length=20, max_length=20, generation_version=2))
    repository.set(_profile(min_length=16, max_length=16, generation_version=3))

    json_files = list((tmp_path / "profiles").rglob("*.json"))
    raw = json.loads(json_files[0].read_text(encoding="utf-8"))

    assert len(raw["version_history"]) == 2
    assert raw["version_history"][0]["generation_version"] == 1
    assert raw["version_history"][1]["generation_version"] == 2
    assert raw["generation_version"] == 3


def test_set_no_change_is_allowed(tmp_path):
    repository = PasswordProfileRepository(tmp_path)
    repository.create(_profile(min_length=24, max_length=32, generation_version=1))

    updated = _profile(min_length=24, max_length=32, generation_version=1)
    repository.set(updated)

    json_files = list((tmp_path / "profiles").rglob("*.json"))
    raw = json.loads(json_files[0].read_text(encoding="utf-8"))

    assert raw["generation_version"] == 1
    assert len(raw.get("version_history", [])) == 0
