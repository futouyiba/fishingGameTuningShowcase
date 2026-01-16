from __future__ import annotations

import numpy as np

from .schema import PondSample, Species


def temperature_profile(sample: PondSample) -> np.ndarray:
    """Return temperature per z-layer (shape: [z])."""
    z = sample.grid.z
    temps = np.empty((z,), dtype=np.float32)
    for k in range(z):
        # Simple piecewise-ish profile: linear gradient after thermocline layer.
        # Replace with your real water-column model later.
        delta = (k - 0) * sample.scenario.temp_gradient_c_per_layer
        temps[k] = sample.scenario.surface_temp_c + delta
    return temps


def structure_coeff_map(
    sample: PondSample, species: list[Species], affinity: dict[tuple[int, str], float]
) -> np.ndarray:
    """Return structure coefficient per (x,y,species). shape: [x,y,f]."""
    x, y = sample.grid.x, sample.grid.y
    f = len(species)
    out = np.ones((x, y, f), dtype=np.float32)

    def structure_at(i: int, j: int) -> str:
        if sample.structure_island is None:
            return sample.structure_default
        x0, y0, x1, y1, sname = sample.structure_island
        if x0 <= i < x1 and y0 <= j < y1:
            return sname
        return sample.structure_default

    for i in range(x):
        for j in range(y):
            sname = structure_at(i, j)
            for idx, sp in enumerate(species):
                out[i, j, idx] = float(affinity.get((sp.id, sname), 1.0))
    return out


def gaussian_pref(x: np.ndarray, mu: float, width: float) -> np.ndarray:
    # width is roughly 1-sigma-ish; tune later.
    sigma = max(width, 1e-3)
    return np.exp(-0.5 * ((x - mu) / sigma) ** 2)


def derive_weight_field(
    sample: PondSample,
    species: list[Species],
    affinity: dict[tuple[int, str], float],
) -> np.ndarray:
    """Derive weights field. Output shape: [x,y,z,f]."""
    x, y, z = sample.grid.x, sample.grid.y, sample.grid.z
    f = len(species)

    temps_z = temperature_profile(sample)  # [z]
    struct_xyf = structure_coeff_map(sample, species, affinity)  # [x,y,f]

    out = np.empty((x, y, z, f), dtype=np.float32)

    # Broadcast temp preference across xyzf
    for fi, sp in enumerate(species):
        temp_w = gaussian_pref(temps_z.astype(np.float32), sp.temp_pref_c, sp.temp_width_c)  # [z]
        # out[:,:,k,fi] = struct_xyf[:,:,fi] * temp_w[k]
        out[:, :, :, fi] = struct_xyf[:, :, fi][:, :, None] * temp_w[None, None, :]

    # Normalize per-voxel (optional): make weights comparable across species
    denom = out.sum(axis=3, keepdims=True)
    denom = np.maximum(denom, 1e-6)
    out = out / denom
    return out


# Friendly alias name used throughout docs/tests


def derive_env_field(
    sample: PondSample, species: list[Species], affinity: dict[tuple[int, str], float]
) -> np.ndarray:
    """Alias for :func:`derive_weight_field`.

    Returns an array shaped [x, y, z, fish].
    """
    return derive_weight_field(sample, species, affinity)
