from __future__ import annotations

from pathlib import Path

import numpy as np

from compute.derive_env_field import derive_env_field
from compute.loaders import load_pond_sample, load_species, load_structure_affinity


def test_determinism_same_inputs_same_outputs() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    static_dir = repo_root / "data" / "static"
    sample_path = repo_root / "data" / "samples" / "pond_1001.json"
    species = load_species(static_dir)
    affinity = load_structure_affinity(static_dir)
    sample = load_pond_sample(sample_path)

    a = derive_env_field(sample, species, affinity)
    b = derive_env_field(sample, species, affinity)

    assert a.shape == b.shape
    assert np.allclose(a, b)
