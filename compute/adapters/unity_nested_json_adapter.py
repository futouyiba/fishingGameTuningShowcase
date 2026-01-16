"""Adapter stubs for your existing nested-json config layout.

You mentioned layouts like:
- `data\1\1001` containing weather / fish stock / env affinity configs
- `Fishing_1006001_Dense_...\map_data.json` for grid origin / step / pool info

This module gives you a single place to map your *current* folders/files
into the simplified schemas used by this repo.

**Migration strategy (recommended):**
1) Keep your original files untouched.
2) Write *thin readers* here to load and normalize them.
3) Feed normalized dicts into `compute/derive_env_field.py`.

This is intentionally conservative and cache-friendly.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LegacyPaths:
    root: Path
    scenario_dir: Path
    map_data_json: Path


@lru_cache(maxsize=64)
def read_json(path: str) -> Any:
    import json

    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8"))


def load_legacy_scenario(legacy: LegacyPaths) -> dict[str, Any]:
    """Load nested-json scenario (weather / time / water temp parameters etc.).

    TODO: implement your exact lookup keys and normalization.

    Return a dict shaped like `data/static/scenario_defaults.json`.
    """
    # Example idea:
    # weather = read_json(str(legacy.scenario_dir / "weather.json"))
    # temp_layers = read_json(str(legacy.scenario_dir / "water_temp_layers.json"))
    # ...normalize...
    raise NotImplementedError("Fill in based on your existing files")


def load_legacy_map_grid(legacy: LegacyPaths) -> dict[str, Any]:
    """Load map grid metadata (origin, step, shape, etc.).

    Return a dict shaped like `data/static/map_grid.json`.
    """
    _raw = read_json(str(legacy.map_data_json))
    # TODO: map your `map_data.json` fields into origin/step/shape.
    # Provide reasonable defaults if a field is missing.
    raise NotImplementedError("Map your map_data.json into the normalized grid schema")
