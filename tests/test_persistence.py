import pytest

from app.models import PasswordConstraints, PasswordProfile
from app.persistence import (
    PasswordProfileRepository,
    ProfileAlreadyExistsError,
    ProfileNotFoundError,
)


def _profile(min_length=24, max_length=32):
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

    updated = _profile(min_length=8, max_length=8)
    repository.set(updated)
    loaded = repository.get("user", "resource")

    assert loaded.constraints.min_length == 8
    assert loaded.constraints.max_length == 8


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
