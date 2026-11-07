#!/usr/bin/env python3
"""Generate the parametric bowl fixture at several R values and both modes."""

from __future__ import annotations

import json
import time
from pathlib import Path

import trimesh

import kintsugi
from sample_models import tea_bowl

RATIOS = (1.0, 0.7, 0.2)
MODES = ("ribbon", "vein")


def main(output_dir: str | Path = "output") -> int:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    input_mesh = tea_bowl()
    input_path = output_dir / "bowl_input.stl"
    input_path.write_bytes(
        trimesh.exchange.stl.export_stl(
            kintsugi.manifold_to_trimesh(input_mesh)
        )
    )
    print(f"Wrote parametric bowl fixture: {input_path}")

    summary = []
    for ratio in RATIOS:
        for mode in MODES:
            label = f"bowl_R{ratio:.1f}_{mode}"
            run_dir = output_dir / label
            three_mf = output_dir / f"{label}.3mf"
            print(f"\n--- {label} ---")
            started = time.perf_counter()
            result = kintsugi.generate_kintsugi_mesh(
                input_path,
                run_dir,
                R=ratio,
                mode=mode,
                seed=7,
                output_3mf_path=three_mf,
            )
            elapsed = time.perf_counter() - started

            row = {
                "label": label,
                "R": ratio,
                "mode": mode,
                "num_cracks": result["num_cracks"],
                "seam_width_mm": result["parameters"]["W"],
                "band_height_mm": result["parameters"]["H"],
                "volumes_mm3": result["volumes"],
                "triangle_counts": result["triangle_counts"],
                "timings_s": result["timings"],
                "wall_clock_s": elapsed,
                "ceramic_path": result["ceramic_path"],
                "gold_path": result["gold_path"],
                "three_mf_path": result["three_mf_path"],
            }
            summary.append(row)

            print(
                f"  cracks={row['num_cracks']:3d}  W={row['seam_width_mm']:.2f} mm  "
                f"H={row['band_height_mm']:.2f} mm"
            )
            print(
                f"  volumes: ceramic={result['volumes']['ceramic']:.2f} mm^3  "
                f"gold={result['volumes']['gold']:.2f} mm^3"
            )
            print(
                f"  triangles: ceramic={row['triangle_counts']['ceramic']:,}  "
                f"gold={row['triangle_counts']['gold']:,}"
            )
            print(f"  time: {elapsed:.2f} s")

    summary_path = output_dir / "sample_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    print(f"\nSummary: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
