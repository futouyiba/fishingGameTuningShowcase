from __future__ import annotations

from pathlib import Path

import numpy as np

from compute.derive_env_field import derive_env_field
from compute.loaders import load_pond_sample, load_species, load_structure_affinity


def test_weights_are_normalized_per_voxel() -> None:
    static_dir = Path(__file__).resolve().parents[1] / "data" / "static"
    sample_path = Path(__file__).resolve().parents[1] / "data" / "samples" / "pond_1001.json"

    species = load_species(static_dir)
    affinity = load_structure_affinity(static_dir)
    sample = load_pond_sample(sample_path)

    w = derive_env_field(sample, species, affinity)
    s = w.sum(axis=3)
    assert np.allclose(s, 1.0, atol=1e-4)


def test_cold_fish_prefers_colder_layers_on_average() -> None:
    """A very coarse invariant: cold-pref fish should have higher weight in deeper (colder) layers."""
    static_dir = Path(__file__).resolve().parents[1] / "data" / "static"
    sample_path = Path(__file__).resolve().parents[1] / "data" / "samples" / "pond_1001.json"

    species = load_species(static_dir)
    affinity = load_structure_affinity(static_dir)
    sample = load_pond_sample(sample_path)

    w = derive_env_field(sample, species, affinity)
    # species[0] is "Bluegill" (warmer pref), species[1] is "Trout" (colder pref) in sample data.
    bluegill = w[:, :, :, 0].mean(axis=(0, 1))  # [z]
    trout = w[:, :, :, 1].mean(axis=(0, 1))

    # compare top vs bottom half
    z = w.shape[2]
    top = slice(0, z // 2)
    bot = slice(z // 2, z)

    assert trout[bot].mean() > trout[top].mean()
    assert bluegill[top].mean() > bluegill[bot].mean()
