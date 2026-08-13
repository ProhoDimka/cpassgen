# cpassgen

Deterministic password generator and profile manager for CLI workflows.

`cpassgen` stores password profiles (username/resource + constraints) and generates the same password for the same input
set every time.

## What is new

- Multi-command CLI: `create`, `bump`, `get`, `sync`
- File-based profile repository with deterministic sharded layout
- Git sync: add/commit/push changes to remote, pull updates, conflict detection
- Constraint-driven password generation with stable pseudo-random expansion
- Generation versioning: version embedded in derivation string, version history stored
- Constraints cannot be changed without bumping generation version
- Explicit validation and clear CLI errors (`exit code 1`)

## How generation works

`cpassgen` generates passwords deterministically. The `generation_version`
is included in the input string so different versions produce different passwords.

- Input seed: `SHA256(username:resource:version:secret)`
- Seed is expanded by deterministic HMAC-SHA256 stream generator
- Password is built to satisfy quotas:
    - `length`, `upper`, `lower`, `digits`, `specials`, `mask`
- `upper`, `lower`, `digits` and `specials` generate exactly that many
  characters; `mask` escapes that many special characters; remaining
  slots are filled with lowercase characters only
- Character order is deterministically shuffled

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install poetry
poetry install
```

## Configuration

`cpassgen` reads configuration from three sources, merged with the following
priority (lowest to highest):

1. A config file in the home directory: `~/.cpassgen.json`
2. A config file passed via the global `--config PATH` argument
3. Environment variables

Config files are JSON objects:

```json
{
  "git_persistence_path": "/path/to/profiles",
  "key_word": "my-secret"
}
```

Environment variables:

- `PASS_GEN_GIT_PERSISTENCE_PATH` - directory where profiles are stored
- `PASS_GEN_KEY_WORD` - secret for the `get` command (if set, prompt is skipped)

Environment variables override config file values; the `--config` file
overrides the home config file.

Example:

```bash
export PASS_GEN_GIT_PERSISTENCE_PATH="$HOME/.cpassgen"
export PASS_GEN_KEY_WORD="my-secret"
```

Or via a config file:

```bash
cat > "$HOME/.cpassgen.json" <<'EOF'
{
  "git_persistence_path": "~/.cpassgen",
  "key_word": "my-secret"
}
EOF
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
poetry run python -m app.main bump \
  --username user1 \
  --resource example.com \
  --length 16 \
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
- `bump` fails if profile does not exist
- `get` fails if profile does not exist
- after successful `create` or `bump`, the tool prompts to sync changes with the remote repository (skipped in non-interactive mode)
- `sync` commits uncommitted changes, pulls remote updates via rebase, pushes local changes; on conflict prints detailed resolution instructions
- all failures are returned as human-readable `Error: ...` messages
- `bump` automatically increments the `generation_version`; constraint changes are optional
- each constraint change via `bump` records the previous state in `version_history` inside the profile JSON

## Best practices for CLI password services

- Keep one profile per real account identity (`username + resource`)
- Use `bump` to evolve constraints gradually instead of recreating profiles
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
app/config.py       configuration loading (files + environment variables)
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
