# cpassgen

Deterministic password generator and profile manager for CLI workflows.

`cpassgen` stores password profiles (username/resource + constraints) and generates the same password for the same input
set every time.

## What is new

- Multi-command CLI: `create`, `set`, `get`, `sync`
- File-based profile repository with deterministic sharded layout
- Git sync: add/commit/push changes to remote, pull updates, conflict detection
- Constraint-driven password generation with stable pseudo-random expansion
- Backward-compatible legacy mode for default constraints
- Generation versioning: version embedded in derivation string, version history stored
- Constraints cannot be changed without bumping generation version
- Explicit validation and clear CLI errors (`exit code 1`)

## How generation works

`cpassgen` supports two deterministic methods. Both include `generation_version`
in the input string so different versions produce different passwords.

1. Legacy mode (backward compatibility)
    - Input: `username:resource:version:secret`
    - Pipeline: URL-safe Base64 -> SHA256 -> URL-safe Base64
    - Triggered when profile constraints are default:
        - `min_length=24`, `max_length=32`, `upper=0`, `lower=0`, `digits=0`, `specials=0`, `mask=0`

2. Constraint mode (recommended)
    - Input seed: `SHA256(username:resource:version:secret)`
    - Seed is expanded by deterministic HMAC-SHA256 stream generator
    - Password is built to satisfy quotas and range constraints:
        - `min_length`, `max_length`, `upper`, `lower`, `digits`, `specials`, `mask`
    - Character order is deterministically shuffled

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install poetry
poetry install
```

## Configuration

Required environment variable:

- `PASS_GEN_GIT_PERSISTENCE_PATH` - directory where profiles are stored

Optional environment variable:

- `PASS_GEN_KEY_WORD` - secret for the `get` command (if set, prompt is skipped)

Example:

```bash
export PASS_GEN_GIT_PERSISTENCE_PATH="$HOME/.cpassgen"
export PASS_GEN_KEY_WORD="my-secret"
```

### Git sync setup

The `sync` command and automatic sync prompts require a git repository with an `origin` remote:

```bash
export PASS_GEN_GIT_PERSISTENCE_PATH="$HOME/.cpassgen"
git -C "$HOME/.cpassgen" init
git -C "$HOME/.cpassgen" remote add origin <your-remote-url>
git -C "$HOME/.cpassgen" commit --allow-empty -m "initial"  # optional
```

## CLI commands

Run CLI:

```bash
poetry run python -m app.main --help
```

Create profile:

```bash
poetry run python -m app.main create \
  --username user1 \
  --resource example.com
```

Create profile with custom generation version:

```bash
poetry run python -m app.main create \
  --username user1 \
  --resource example.com \
  --generation-version 3
```

Update existing profile constraints:

```bash
poetry run python -m app.main set \
  --username user1 \
  --resource example.com \
  --generation-version 2 \
  --min-length 16 \
  --max-length 20 \
  --upper 2 \
  --lower 4 \
  --digits 2 \
  --specials 2 \
  --mask 1
```

Generate password from profile:

```bash
poetry run python -m app.main get \
  --username user1 \
  --resource example.com
```

Sync profile storage with remote git repository:

```bash
poetry run python -m app.main sync
```

Notes:

- `create` fails if profile already exists
- `set` fails if profile does not exist
- `get` fails if profile does not exist
- after successful `create` or `set`, the tool prompts to sync changes with the remote repository (skipped in non-interactive mode)
- `sync` commits uncommitted changes, pulls remote updates via rebase, pushes local changes; on conflict prints detailed resolution instructions
- all failures are returned as human-readable `Error: ...` messages
- `--generation-version` defaults to 1 and can be set on both `create` and `set`
- changing `PasswordConstraints` without bumping `--generation-version` is rejected
- each version or constraint change records the previous state in `version_history` inside the profile JSON

## Best practices for CLI password services

- Keep one profile per real account identity (`username + resource`)
- Use `set` to evolve constraints gradually instead of recreating profiles
- Store secrets in environment variables or secure prompt input, not shell history
- Keep persistence path in private local storage and back it up securely
- Validate constraint changes in CI (`make lint`, `make test`) before sharing
- Prefer deterministic generation for reproducible recovery workflows

## Development commands

```bash
make fmt        # isort + black
make fmt_check  # formatting check
make lint       # flake8
make test       # pytest + coverage
```

Run one test module:

```bash
pytest tests/test_main.py
```

## Project structure

```text
app/main.py         CLI entrypoint (Click group + commands)
app/generator.py    deterministic password generation logic
app/persistence.py  profile repository and filesystem layout
app/sync_service.py git sync, commit, push, pull, conflict detection
app/seed_expander.py deterministic pseudo-random byte stream
app/models.py       immutable domain models
app/validators.py   constraints validation
tests/              unit tests
pyproject.toml      Poetry project manifest
Makefile            dev shortcuts
```

## License

Apache License 2.0. See `LICENSE`.
