#!/usr/bin/env bash
set -euo pipefail

PYTHON=${PYTHON:-python}

# Ensure tooling deps exist (ruff/pytest/numpy/pandas/matplotlib)
$PYTHON -m pip show ruff >/dev/null 2>&1 || $PYTHON -m pip install -r requirements.txt >/dev/null

$PYTHON -m ruff format .
$PYTHON -m ruff check .
$PYTHON -m pytest
