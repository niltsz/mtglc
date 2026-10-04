# mtglc



**Status:** work in progress.

## Setup

```bash
uv sync
```

## Usage

TODO

## Tests

```bash
uv run pytest -m "not needs_data"
```

Tests marked `needs_data` require local data or model weights and are skipped in CI.

## Repository layout

```
src/mtglc/   package code
tests/         tests
docs/          documentation and decision log
scripts/       helper scripts
data/          local data (not version-controlled)
external/      third-party software (not version-controlled)
```
