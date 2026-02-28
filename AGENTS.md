# AGENTS.md

## Cursor Cloud specific instructions

### Overview

Clawdfolio is a single-service Python CLI/library for quantitative portfolio analytics. No databases, Docker, or external services are required for development or testing.

### Running the CLI in demo mode

The default config disables the demo broker. To use CLI commands without real broker credentials, create `~/.config/clawdfolio/config.yaml`:

```yaml
brokers:
  demo:
    enabled: true
  longport:
    enabled: false
  futu:
    enabled: false
```

Then run: `clawdfolio summary`, `clawdfolio risk`, etc.

### PATH caveat

`pip install --user` installs scripts to `~/.local/bin`. Ensure this is on `PATH`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

### Development commands

See `CONTRIBUTING.md` for full details. Quick reference:

- **Lint:** `ruff check src/ tests/`
- **Type check:** `mypy src/clawdfolio --ignore-missing-imports`
- **Test:** `pytest tests/ -v --cov=src/clawdfolio`
- **Format:** `ruff format src/ tests/`

### Notes

- All 357 tests pass; the coverage gate (`fail_under=70`) may report exit code 1 at ~69% — this is a pre-existing threshold gap, not a test failure.
- The `legacy_finance` directory is excluded from both ruff and mypy (`pyproject.toml` config).
- Pre-commit hooks (ruff + ruff-format) are configured in `.pre-commit-config.yaml`; install with `pre-commit install` if needed.
