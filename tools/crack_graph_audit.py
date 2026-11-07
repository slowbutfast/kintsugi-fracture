"""Crack-graph audit against the true periodic Voronoi diagram.

Usage:
    .venv/bin/python tools/crack_graph_audit.py --presets tea_bowl vase \
        --severities 0.6 1.0 --seeds 200 [--output out.json]

Runs ``generate_crack_paths`` with the noise field patched to zero and every
other stage (seed tiling, ray orientation, band-edge jitter, wall-range
clamp/truncation) exactly as shipped, then reports per (preset, S):

* ``phantom_seeds``: seeds for which some path point is NOT on the periodic
  Voronoi diagram, i.e. its two nearest seeds in a 9-tile copy are not
  equidistant (tolerance 1e-6 * period).  Ground truth uses 9 tiles so strip-end
  distortion cannot reach the central tile.
* ``crossing_seeds``: seeds where two segments of different paths properly
  intersect (exact orientation test in unrolled (u, z); wrap segments skipped).
* ``clamp_line_fraction``: mean / max fraction of NON-terminal path points that
  sit exactly (1e-9) on a horizontal clamp line (band edge +/- W/2 or wall
  range +/- W/2).  Flattened runs along a clamp line show up here.

The seed draw order (u then z, N each, from the run's rng) must match
``generate_crack_paths``; this tool rebuilds the seeds the same way.
"""
from __future__ import annotations

import argparse
import json
import sys
import unittest.mock
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
import kintsugi  # noqa: E402


def _zero_noise(rbar, base_amplitude, rng):
    def eta(u, z):
        zeros = np.zeros_like(np.asarray(u, dtype=np.float64))
        return zeros, zeros.copy()

    return eta


def _segments(paths, period):
    out = []
    for index, path in enumerate(paths):
        for a, b in zip(path[:-1], path[1:]):
            if abs(a[0] - b[0]) > 0.5 * period:
                continue
            out.append((index, a, b))
    return out


def _orient(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _has_crossing(paths, period, eps=1e-9):
    segs = _segments(paths, period)
    if not segs:
        return False
    boxes = np.array(
        [[min(a[0], b[0]), max(a[0], b[0]), min(a[1], b[1]), max(a[1], b[1])]
         for _, a, b in segs]
    )
    for x, (px, a, b) in enumerate(segs):
        cand = np.nonzero(
            (boxes[:, 0] <= boxes[x, 1]) & (boxes[:, 1] >= boxes[x, 0])
            & (boxes[:, 2] <= boxes[x, 3]) & (boxes[:, 3] >= boxes[x, 2])
        )[0]
        for y in cand:
            if y <= x or segs[y][0] == px:
                continue
            c, d = segs[y][1], segs[y][2]
            if (_orient(a, b, c) * _orient(a, b, d) < -eps
                    and _orient(c, d, a) * _orient(c, d, b) < -eps):
                return True
    return False


def _off_diagram(paths, params, seed):
    period = float(params["period"])
    n = max(int(params["N"]), 1)
    rng = np.random.default_rng(seed)
    seeds = np.column_stack((
        rng.uniform(0.0, period, size=n),
        rng.uniform(float(params["z_min"]), float(params["z_max"]), size=n),
    ))
    tiled = np.vstack([seeds + [k * period, 0.0] for k in range(-4, 5)])
    points = np.vstack(paths)
    d = np.linalg.norm(points[:, None, :] - tiled[None, :, :], axis=2)
    d.sort(axis=1)
    return bool(np.any(d[:, 1] - d[:, 0] > 1e-6 * period))


def _clamp_fraction(paths, params):
    W = float(params["W"])
    lines = [
        float(params["z_min"]) + 0.5 * W,
        float(params["z_max"]) - 0.5 * W,
        float(params.get("wall_z_min", params["z_min"])) + 0.5 * W,
        float(params.get("wall_z_max", params["z_max"])) - 0.5 * W,
    ]
    inner = [p[1:-1] for p in paths if len(p) > 2]
    if not inner:
        return 0.0
    z = np.concatenate([p[:, 1] for p in inner])
    on = np.zeros(len(z), dtype=bool)
    for line in lines:
        on |= np.abs(z - line) < 1e-9
    return float(on.mean())


def audit(preset, severity, seeds):
    path = REPO / "presets" / f"{preset}.stl"
    if not path.exists():
        path = Path(preset)
    mesh, manifold = kintsugi.validate_and_load_mesh(path, 0.0)
    params = kintsugi.compute_parameters(severity, mesh, manifold=manifold)
    phantom, crossing, fractions = [], [], []
    with unittest.mock.patch.object(kintsugi, "_make_noise", _zero_noise):
        for seed in range(seeds):
            paths = kintsugi.generate_crack_paths(
                dict(params),
                np.random.default_rng(seed),
                generator="voronoi",
            )
            if not paths:
                fractions.append(0.0)
                continue
            if _off_diagram(paths, params, seed):
                phantom.append(seed)
            if _has_crossing(paths, float(params["period"])):
                crossing.append(seed)
            fractions.append(_clamp_fraction(paths, params))
    return {
        "preset": Path(preset).stem,
        "S": severity,
        "seeds": seeds,
        "phantom_seeds": len(phantom),
        "phantom_examples": phantom[:8],
        "crossing_seeds": len(crossing),
        "crossing_examples": crossing[:8],
        "clamp_line_fraction_mean": float(np.mean(fractions)),
        "clamp_line_fraction_max": float(np.max(fractions)),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--presets", nargs="+", default=["tea_bowl", "vase"])
    parser.add_argument("--severities", nargs="+", type=float, default=[0.6, 1.0])
    parser.add_argument("--seeds", type=int, default=200)
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    rows = []
    for preset in args.presets:
        for severity in args.severities:
            row = audit(preset, severity, args.seeds)
            rows.append(row)
            print(
                f"{row['preset']:>9} S={severity:<4} phantom {row['phantom_seeds']}/{args.seeds}"
                f"  crossing {row['crossing_seeds']}/{args.seeds}"
                f"  clamp-line pts mean {row['clamp_line_fraction_mean']:.1%}"
                f" max {row['clamp_line_fraction_max']:.1%}",
                flush=True,
            )
    if args.output:
        Path(args.output).write_text(json.dumps(rows, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
