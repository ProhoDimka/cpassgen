# cpassgen

Deterministic password generator CLI using SHA256 + URL-safe Base64.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install poetry
poetry install
```

## Usage

Interactive prompts with advanced options:

```bash
poetry run python -m app.main
# or
python app/main.py
```

Or pass arguments:

```bash
poetry run python -m app.main \
  --username user1 \
  --resource example.com \
  --secret mysecret \
  --min-length 14 \
  --max-length 18 \
  --upper 3 \
  --lower 4 \
  --digits 3 \
  --specials 2 \
  --mask 1
```

Without additional flags the CLI returns the legacy deterministic Base64 output to remain backward compatible.

## Commands

```bash
make fmt        # isort, black
make fmt_check  # check formatting
make lint       # flake8
make test       # pytest with coverage
```

Run single test:

```bash
pytest tests/test_main.py
```

## Project Structure

```
app/           CLI source (main.py)
tests/         unit tests
p.yproject.toml project manifest
Makefile       shortcuts for fmt, lint, test
```

## License

Apache License 2.0

See LICENSE for details.
