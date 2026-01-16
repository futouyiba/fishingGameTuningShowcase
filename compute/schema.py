from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GridSpec:
    x: int
    y: int
    z: int
    cell_size_m: float


@dataclass(frozen=True)
class Scenario:
    surface_temp_c: float
    thermocline_z: int
    temp_gradient_c_per_layer: float


@dataclass(frozen=True)
class Species:
    id: int
    name: str
    temp_pref_c: float
    temp_width_c: float


@dataclass(frozen=True)
class PondSample:
    pond_id: int
    grid: GridSpec
    scenario: Scenario
    structure_default: str
    structure_island: tuple[int, int, int, int, str] | None
