# Add generation version to password derivation and constraint history tracking

## Summary

Adds a `generation_version` field to `PasswordProfile` that is incorporated into
the password derivation algorithm. When constraints change, the version must be
bumped. Each version change is recorded in a `version_history` array stored
alongside the profile in JSON.

## Changes

- **app/models.py**: Added `generation_version: int = 1` to `PasswordProfile`.
- **app/generator.py**: `generation_version` included in `_legacy_password` and
  `_derive_seed` input strings, so different versions produce different passwords.
- **app/main.py**: `--generation-version` CLI option added to `create` and `set`
  commands (default: 1).
- **app/persistence.py**:
  - `set()` now enforces that constraint changes require a version bump.
  - Profile JSON includes a `version_history` array recording previous
    (version, constraints) pairs on each version or constraint change.
  - `get()` reads `generation_version` from JSON, defaulting to 1 for legacy profiles.
  - `_validate_profile()` rejects `generation_version < 1`.
- **tests/**: Added 14 new tests covering version-dependent generation, history
  recording, enforcement of version bump on constraint change, CLI integration,
  and backward compatibility with legacy profiles.
