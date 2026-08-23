#!/usr/bin/env bash
set -euo pipefail

PYTHON=${PYTHON:-python}

# Ensure tooling deps exist (ruff/pytest/numpy/pandas/matplotlib)
$PYTHON -m pip show ruff >/dev/null 2>&1 || $PYTHON -m pip install -r requirements.txt >/dev/null

# Verification must not mutate the checked-out commit. Developers can run
# `python -m ruff format .` locally before invoking this gate.
$PYTHON -m ruff format --check .
$PYTHON -m ruff check .
$PYTHON -m pytest
