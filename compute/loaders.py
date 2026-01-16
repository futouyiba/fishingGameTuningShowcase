from __future__ import annotations

import json
from pathlib import Path

from .schema import GridSpec, PondSample, Scenario, Species


def load_species(static_dir: Path) -> list[Species]:
    data = json.loads((static_dir / "fish_species.json").read_text(encoding="utf-8"))
    out: list[Species] = []
    for s in data["species"]:
        out.append(
            Species(
                id=int(s["id"]),
                name=str(s["name"]),
                temp_pref_c=float(s["temp_pref_c"]),
                temp_width_c=float(s["temp_width_c"]),
            )
        )
    return out


def load_structure_affinity(static_dir: Path) -> dict[tuple[int, str], float]:
    data = json.loads((static_dir / "structure_affinity.json").read_text(encoding="utf-8"))
    m: dict[tuple[int, str], float] = {}
    for r in data["affinity"]:
        m[(int(r["species_id"]), str(r["structure"]))] = float(r["coeff"])
    return m


def load_pond_sample(sample_path: Path) -> PondSample:
    d = json.loads(sample_path.read_text(encoding="utf-8"))
    grid = d["grid"]
    scen = d["scenario"]
    island = d.get("structure_map", {}).get("island")
    island_tuple = None
    if island:
        island_tuple = (
            int(island["x0"]),
            int(island["y0"]),
            int(island["x1"]),
            int(island["y1"]),
            str(island["structure"]),
        )
    return PondSample(
        pond_id=int(d["pond_id"]),
        grid=GridSpec(
            x=int(grid["x"]),
            y=int(grid["y"]),
            z=int(grid["z"]),
            cell_size_m=float(grid["cell_size_m"]),
        ),
        scenario=Scenario(
            surface_temp_c=float(scen["surface_temp_c"]),
            thermocline_z=int(scen["thermocline_z"]),
            temp_gradient_c_per_layer=float(scen["temp_gradient_c_per_layer"]),
        ),
        structure_default=str(d.get("structure_map", {}).get("default", "weeds")),
        structure_island=island_tuple,
    )
