#!/usr/bin/env python3
"""Out-of-sample watertightness sweep (seeds/R values not used for tuning).

Usage:
    .venv/bin/python tools/sweep_out_of_sample.py \
        --presets tea_bowl vase \
        --ratios 0 0.1 0.35 0.6 0.8 \
        --modes ribbon vein \
        --seeds 100 101 102 103 104 105 106 107
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
import tempfile
import time
import traceback
from collections import Counter
from pathlib import Path

import numpy as np
import trimesh

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import kintsugi  # noqa: E402


def _bad(path: str | Path) -> tuple[bool, int]:
    mesh = trimesh.load(path, process=True)
    if isinstance(mesh, trimesh.Scene):
        mesh = mesh.dump(concatenate=True)
    rows = np.sort(np.asarray(mesh.edges_sorted, dtype=np.int64), axis=1)
    _, counts = np.unique(rows, axis=0, return_counts=True)
    bad = int(np.count_nonzero(counts != 2))
    return bool(mesh.is_watertight and mesh.is_volume), bad


def _preset_path(name: str) -> Path:
    candidate = Path(name)
    if candidate.exists():
        return candidate
    return REPO / "presets" / f"{name}.stl"


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--presets",
        nargs="+",
        default=["tea_bowl", "vase"],
        help="Preset ids or STL paths",
    )
    parser.add_argument(
        "--ratios",
        nargs="+",
        type=float,
        default=[0.0, 0.1, 0.35, 0.6, 0.8],
    )
    parser.add_argument(
        "--modes",
        nargs="+",
        choices=("ribbon", "vein"),
        default=["ribbon", "vein"],
    )
    parser.add_argument("--seeds", nargs="+", type=int, default=list(range(100, 108)))
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO / "output" / "verification" / "sweep_out_of_sample.json",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    res: collections.Counter[str] = collections.Counter()
    attempts: collections.Counter[int] = collections.Counter()
    variants: collections.Counter[int] = collections.Counter()
    component_counts: collections.Counter[int] = collections.Counter()
    fails: list[dict] = []
    results: list[dict] = []

    for preset in args.presets:
        preset_path = _preset_path(preset)
        preset_name = preset_path.stem
        for ratio in args.ratios:
            for mode in args.modes:
                for seed in args.seeds:
                    row = {
                        "preset": preset_name,
                        "R": ratio,
                        "mode": mode,
                        "seed": seed,
                    }
                    with tempfile.TemporaryDirectory() as tmp:
                        try:
                            started = time.perf_counter()
                            result = kintsugi.generate_kintsugi_mesh(
                                preset_path, tmp, R=ratio, mode=mode, seed=seed
                            )
                            outputs = [
                                _bad(result[key])
                                for key in ("ceramic_path", "gold_path")
                            ]
                            ok = all(watertight for watertight, _ in outputs) and all(
                                bad == 0 for _, bad in outputs
                            )
                            row["status"] = "ok" if ok else "nonwatertight"
                            row["outputs"] = [
                                {"watertight": watertight, "bad_edges": bad}
                                for watertight, bad in outputs
                            ]
                            row["cutter_attempts"] = result.get(
                                "cutter_attempts", 0
                            )
                            row["cutter_variants"] = result.get(
                                "cutter_variants", 0
                            )
                            attempts[row["cutter_attempts"]] += 1
                            variants[row["cutter_variants"]] += 1
                            if mode == "ribbon":
                                ceramic = trimesh.load(
                                    result["ceramic_path"], process=True
                                )
                                if isinstance(ceramic, trimesh.Scene):
                                    ceramic = ceramic.dump(concatenate=True)
                                count = len(
                                    ceramic.split(only_watertight=False)
                                )
                                component_counts[count] += 1
                                row["ceramic_components"] = count
                            row["total_s"] = time.perf_counter() - started
                        except Exception as exc:  # pragma: no cover - evidence
                            row["status"] = "error"
                            row["error"] = f"{type(exc).__name__}: {exc}"
                            row["traceback"] = traceback.format_exc()
                    res[row["status"]] += 1
                    if row["status"] != "ok":
                        fails.append(row)
                    results.append(row)

    summary = {
        "command": " ".join(sys.argv),
        "total": len(results),
        "counts": dict(res),
        "clean": res["ok"],
        "nonwatertight": res["nonwatertight"],
        "errors": res["error"],
        "cutter_attempts": dict(attempts),
        "cutter_variants": dict(variants),
        "ribbon_ceramic_components": dict(component_counts),
        "run_time_median_s": float(
            np.median([row["total_s"] for row in results if "total_s" in row])
        ) if any("total_s" in row for row in results) else 0.0,
        "run_time_max_s": float(
            max(row["total_s"] for row in results if "total_s" in row)
        ) if any("total_s" in row for row in results) else 0.0,
        "failures": fails,
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2))

    print(
        json.dumps(
            {
                key: summary[key]
                for key in (
                    "total",
                    "counts",
                    "clean",
                    "nonwatertight",
                    "errors",
                    "cutter_attempts",
                    "cutter_variants",
                    "ribbon_ceramic_components",
                    "run_time_median_s",
                    "run_time_max_s",
                )
            },
            indent=2,
        )
    )
    print(f"Wrote {args.output}")
    return 0 if summary["nonwatertight"] == 0 and summary["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
