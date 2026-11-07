#!/usr/bin/env python3
"""Multi-seed watertightness sweep for the Kintsugi engine.

Usage:
    .venv/bin/python tools/sweep.py \
        --presets tea_bowl vase \
        --ratios 0 0.05 0.2 0.5 0.9 0.99 \
        --modes ribbon vein \
        --seeds 0 1 2 3 4 5
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
import tempfile
import time
import traceback
from pathlib import Path

import numpy as np
import trimesh

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import kintsugi  # noqa: E402


def _bad_edge_count(mesh: trimesh.Trimesh) -> int:
    if len(mesh.edges_sorted) == 0:
        return 0
    rows = np.sort(np.asarray(mesh.edges_sorted, dtype=np.int64), axis=1)
    _, counts = np.unique(rows, axis=0, return_counts=True)
    return int(np.count_nonzero(counts != 2))


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
        default=[0.0, 0.05, 0.2, 0.5, 0.9, 0.99],
    )
    parser.add_argument(
        "--modes",
        nargs="+",
        choices=("ribbon", "vein"),
        default=["ribbon", "vein"],
    )
    parser.add_argument("--seeds", nargs="+", type=int, default=list(range(6)))
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO / "output" / "verification" / "sweep.json",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    counter: collections.Counter[str] = collections.Counter()
    failures: list[dict] = []
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
                            problems = []
                            bad_edges = 0
                            for key in ("ceramic_path", "gold_path"):
                                mesh = trimesh.load(
                                    result[key], process=True
                                )
                                key_bad = _bad_edge_count(mesh)
                                bad_edges += key_bad
                                if not (mesh.is_watertight and mesh.is_volume):
                                    problems.append(f"{key}:not_watertight")
                                if key_bad:
                                    problems.append(f"{key}:{key_bad}_bad_edges")
                            row["status"] = "ok" if not problems else "nonwatertight"
                            row["bad_edges"] = bad_edges
                            row["problems"] = problems
                            row["num_cracks"] = result["num_cracks"]
                            row["cutter_attempts"] = result.get(
                                "cutter_attempts", 0
                            )
                            row["cutter_variants"] = result.get(
                                "cutter_variants", 0
                            )
                            row["debris_unmoved"] = result.get(
                                "debris_unmoved", 0
                            )
                            row["triangle_counts"] = result["triangle_counts"]
                            row["total_s"] = time.perf_counter() - started
                        except ValueError as exc:
                            row["status"] = "rejected"
                            row["error"] = str(exc)
                            row["false_rejection"] = True
                        except Exception as exc:  # pragma: no cover - evidence
                            row["status"] = "error"
                            row["error"] = f"{type(exc).__name__}: {exc}"
                            row["traceback"] = traceback.format_exc()
                    counter[row["status"]] += 1
                    if row["status"] != "ok":
                        failures.append(row)
                    results.append(row)

    completed = counter["ok"] + counter["nonwatertight"]
    attempt_hist = collections.Counter(
        row.get("cutter_attempts", 0) for row in results
    )
    variant_hist = collections.Counter(
        row.get("cutter_variants", 0) for row in results
    )
    summary = {
        "command": " ".join(sys.argv),
        "total": len(results),
        "counts": dict(counter),
        "completed": completed,
        "clean": counter["ok"],
        "nonwatertight": counter["nonwatertight"],
        "false_rejections": counter["rejected"],
        "errors": counter["error"],
        "cutter_attempts": dict(attempt_hist),
        "cutter_variants": dict(variant_hist),
        "debris_unmoved_total": sum(
            row.get("debris_unmoved", 0) for row in results
        ),
        "run_time_median_s": float(
            np.median([row["total_s"] for row in results if "total_s" in row])
        ) if any("total_s" in row for row in results) else 0.0,
        "run_time_max_s": float(
            max(row["total_s"] for row in results if "total_s" in row)
        ) if any("total_s" in row for row in results) else 0.0,
        "failures": failures,
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
                    "completed",
                    "clean",
                    "nonwatertight",
                    "false_rejections",
                    "errors",
                    "cutter_attempts",
                    "cutter_variants",
                    "debris_unmoved_total",
                    "run_time_median_s",
                    "run_time_max_s",
                )
            },
            indent=2,
        )
    )
    print(f"Wrote {args.output}")
    return 0 if summary["nonwatertight"] == 0 and summary["false_rejections"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
