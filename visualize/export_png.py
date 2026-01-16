"""Export quick PNGs from env_field.npy.

- A 2D heatmap for each species at a chosen depth slice

Usage:
  python -m visualize.export_png --in-dir artifacts --out-dir artifacts/png --z 0
"""

from __future__ import annotations

import argparse
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--z", type=int, default=0)
    args = ap.parse_args()

    in_path = os.path.join(args.in_dir, "env_field.npy")
    summary_path = os.path.join(args.in_dir, "summary.csv")

    W = np.load(in_path)
    df = pd.read_csv(summary_path)

    os.makedirs(args.out_dir, exist_ok=True)

    z = max(0, min(args.z, W.shape[2] - 1))

    for i, row in df.iterrows():
        name = str(row["name"]).replace(" ", "_")
        img = W[:, :, z, i].T  # transpose so y is vertical

        plt.figure()
        plt.imshow(img)
        plt.title(f"{row['name']} (z={z})")
        plt.colorbar()
        out = os.path.join(args.out_dir, f"heatmap_{int(row['species_id'])}_{name}_z{z}.png")
        plt.savefig(out, dpi=150, bbox_inches="tight")
        plt.close()

    print(f"Exported PNGs -> {args.out_dir}")


if __name__ == "__main__":
    main()
