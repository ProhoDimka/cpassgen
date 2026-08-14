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


def _read_raw(tmp_path):
    json_files = list((tmp_path / "profiles").rglob("*.json"))
    return json.loads(json_files[0].read_text(encoding="utf-8"))


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
    created_at = _read_raw(tmp_path)["created_at"]

    new_constraints = PasswordConstraints(
        length=16,
        upper=0,
        lower=0,
        digits=0,
        specials=0,
        mask=0,
    )
    repository.bump("user", "resource", new_constraints=new_constraints)

    raw = _read_raw(tmp_path)

    assert "version_history" in raw
    assert len(raw["version_history"]) == 1
    entry = raw["version_history"][0]
    assert entry["generation_version"] == 1
    assert entry["constraints"]["length"] == 24
    assert entry["created_at"] == created_at
    assert raw["created_at"] != created_at


def test_bump_version_only_records_previous_version(tmp_path):
    repository = PasswordProfileRepository(tmp_path)
    repository.create(_profile(length=24, generation_version=1))
    created_at = _read_raw(tmp_path)["created_at"]

    repository.bump("user", "resource")

    raw = _read_raw(tmp_path)

    assert raw["generation_version"] == 2
    assert len(raw["version_history"]) == 1
    entry = raw["version_history"][0]
    assert entry["generation_version"] == 1
    assert entry["constraints"]["length"] == 24
    assert entry["created_at"] == created_at


def test_bump_multiple_times_accumulates_history(tmp_path):
    repository = PasswordProfileRepository(tmp_path)
    repository.create(_profile(length=24, generation_version=1))
    created_at_v1 = _read_raw(tmp_path)["created_at"]

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
    created_at_v2 = _read_raw(tmp_path)["created_at"]
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

    raw = _read_raw(tmp_path)

    assert len(raw["version_history"]) == 2
    assert raw["version_history"][0]["generation_version"] == 1
    assert raw["version_history"][1]["generation_version"] == 2
    assert raw["generation_version"] == 3
    assert raw["version_history"][0]["created_at"] == created_at_v1
    assert raw["version_history"][1]["created_at"] == created_at_v2


def test_bump_no_constraints_change_still_increments(tmp_path):
    repository = PasswordProfileRepository(tmp_path)
    repository.create(_profile(length=24, generation_version=1))

    result = repository.bump("user", "resource")
    loaded = repository.get("user", "resource")

    assert result.generation_version == 2
    assert loaded.generation_version == 2
    assert loaded.constraints == result.constraints


def test_create_writes_created_at(tmp_path):
    repository = PasswordProfileRepository(tmp_path)
    repository.create(_profile())

    raw = _read_raw(tmp_path)

    assert "created_at" in raw
    assert raw["created_at"].endswith("+00:00")


def test_history_entry_carries_previous_created_at(tmp_path):
    repository = PasswordProfileRepository(tmp_path)
    repository.create(_profile())
    created_at = _read_raw(tmp_path)["created_at"]

    repository.bump("user", "resource")

    raw = _read_raw(tmp_path)
    assert raw["version_history"][0]["created_at"] == created_at
    assert raw["created_at"] != created_at


def test_list_profiles_empty_when_root_missing(tmp_path):
    repository = PasswordProfileRepository(tmp_path)

    assert repository.list_profiles() == []


def test_list_profiles_returns_created_profiles_with_created_at(tmp_path):
    repository = PasswordProfileRepository(tmp_path)
    repository.create(
        PasswordProfile(
            username="alice",
            resource="example.com",
            constraints=PasswordConstraints(
                length=24, upper=0, lower=0, digits=0, specials=0, mask=0
            ),
            generation_version=1,
        )
    )
    repository.create(
        PasswordProfile(
            username="bob",
            resource="other.com",
            constraints=PasswordConstraints(
                length=16, upper=0, lower=0, digits=0, specials=0, mask=0
            ),
            generation_version=2,
        )
    )

    entries = repository.list_profiles()

    assert len(entries) == 2
    profiles = {profile.username for profile, _ in entries}
    assert profiles == {"alice", "bob"}
    assert all(created_at is not None for _, created_at in entries)


def test_history_returns_current_profile_and_empty_history(tmp_path):
    repository = PasswordProfileRepository(tmp_path)
    repository.create(_profile(length=24, generation_version=1))

    result = repository.history("user", "resource")

    assert result.profile.generation_version == 1
    assert result.profile.constraints.length == 24
    assert result.created_at is not None
    assert result.history == ()


def test_history_returns_previous_versions_with_constraints(tmp_path):
    repository = PasswordProfileRepository(tmp_path)
    repository.create(_profile(length=24, generation_version=1))
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

    result = repository.history("user", "resource")

    assert result.profile.generation_version == 2
    assert result.profile.constraints.length == 16
    assert len(result.history) == 1
    entry = result.history[0]
    assert entry.generation_version == 1
    assert entry.constraints.length == 24
    assert entry.created_at is not None


def test_history_missing_profile_fails(tmp_path):
    repository = PasswordProfileRepository(tmp_path)

    with pytest.raises(ProfileNotFoundError):
        repository.history("user", "resource")


def test_bump_legacy_profile_without_created_at_does_not_crash(tmp_path):
    repository = PasswordProfileRepository(tmp_path)
    repository.create(_profile())

    json_files = list((tmp_path / "profiles").rglob("*.json"))
    raw = json.loads(json_files[0].read_text(encoding="utf-8"))
    del raw["created_at"]
    json_files[0].write_text(
        json.dumps(raw, ensure_ascii=True, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    result = repository.bump("user", "resource")

    raw = _read_raw(tmp_path)
    assert result.generation_version == 2
    assert raw["version_history"][0]["created_at"] is None
    assert raw["created_at"] is not None
