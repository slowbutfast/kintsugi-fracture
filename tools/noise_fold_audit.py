"""Noise-field folding audit (finding F18).

Usage:
    .venv/bin/python tools/noise_fold_audit.py --presets tea_bowl vase \
        --severities 0.3 0.6 1.0 --seeds 300 500 [--output out.json]

The crack graph is planar before noise (see ``tools/crack_graph_audit.py``).
The displacement ``(u, z) -> (u, z) + eta(u, z)`` keeps it planar only if the
map is injective; a sufficient condition is ``Lip(eta) < 1``.  This tool reports,
per (preset, S):

* ``fold_area``: mean / max fraction of the band where ``det J < 0`` (the map
  folds), sampled on a 600 x 150 grid, over the first 20 seeds.
* ``max_grad``: the largest |partial derivative| of eta found on that grid.
* ``crossing_seeds_with_noise``: seeds in [start, stop) whose shipped
  ``generate_crack_paths`` output (noise ON) contains two properly
  intersecting segments from different paths.

Target once F18 is fixed: fold_area 0.0%, max_grad < 1, crossings 0.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))
import kintsugi  # noqa: E402
from crack_graph_audit import _has_crossing  # noqa: E402


def fold_stats(params, seeds=20):
    spacing = math.sqrt(params["period"] * params["H"] / max(params["N"], 1))
    u, z = np.meshgrid(
        np.linspace(0.0, params["period"], 600),
        np.linspace(params["z_min"], params["z_max"], 150),
    )
    h = 1e-3
    folds, grads = [], []
    for seed in range(seeds):
        eta = kintsugi._make_noise(
            params["rbar"], 0.15 * spacing, np.random.default_rng(seed)
        )
        du0, dz0 = eta(u, z)
        duu, dzu = eta(u + h, z)
        duz, dzz = eta(u, z + h)
        a, b = (duu - du0) / h, (duz - du0) / h
        c, d = (dzu - dz0) / h, (dzz - dz0) / h
        det = (1 + a) * (1 + d) - b * c
        folds.append(float(np.mean(det < 0)))
        grads.append(float(np.max(np.abs([a, b, c, d]))))
    return float(np.mean(folds)), float(np.max(folds)), float(np.max(grads))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--presets", nargs="+", default=["tea_bowl", "vase"])
    parser.add_argument("--severities", nargs="+", type=float, default=[0.3, 0.6, 1.0])
    parser.add_argument("--seeds", nargs=2, type=int, default=[300, 500])
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    start, stop = args.seeds
    rows = []
    for preset in args.presets:
        path = REPO / "presets" / f"{preset}.stl"
        mesh, manifold = kintsugi.validate_and_load_mesh(path, 0.0)
        for severity in args.severities:
            params = kintsugi.compute_parameters(severity, mesh, manifold=manifold)
            fold_mean, fold_max, grad = fold_stats(params)
            crossing = [
                seed for seed in range(start, stop)
                if _has_crossing(
                    kintsugi.generate_crack_paths(dict(params), np.random.default_rng(seed)),
                    float(params["period"]),
                )
            ]
            row = {
                "preset": preset, "S": severity,
                "fold_area_mean": fold_mean, "fold_area_max": fold_max,
                "max_grad": grad,
                "crossing_seeds_with_noise": len(crossing),
                "seeds": stop - start, "crossing_examples": crossing[:8],
            }
            rows.append(row)
            print(
                f"{preset:>9} S={severity:<4} fold area mean {fold_mean:.1%} max {fold_max:.1%}"
                f"  max|grad eta| {grad:.2f}  crossings (noise on) {len(crossing)}/{stop - start}",
                flush=True,
            )
    if args.output:
        Path(args.output).write_text(json.dumps(rows, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
