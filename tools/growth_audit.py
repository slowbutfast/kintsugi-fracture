#!/usr/bin/env python3
"""Audit the growth-mode crack graph over held-out seeds.

For every (preset, severity) pair the tool runs ``generate_crack_growth_paths``
for each requested seed and aggregates the metrics returned by
``analyze_growth_paths``: crossings, clearance violations, minimum clearances
and incidence angles, T/Y junction counts and tortuosity percentiles.

Gates (all must hold for the audit to pass):
    * zero crossings
    * zero clearance violations
    * mean T-junction ratio >= 0.80
    * median tortuosity >= 1.05

Usage:
    .venv/bin/python tools/growth_audit.py [--presets tea_bowl vase]
        [--severities 0.6 1.0] [--seeds 300-499]
        [--output output/verification/growth_audit.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
import kintsugi  # noqa: E402

DEFAULT_OUTPUT = "output/verification/growth_audit.json"


# ---------------------------------------------------------------------------
# CLI parsing helpers
# ---------------------------------------------------------------------------
def parse_seeds(tokens) -> list[int]:
    """Parse seed tokens: ``300-499``, ``300 301`` or ``300,301,302``."""
    seeds: list[int] = []
    seen: set[int] = set()
    for token in tokens:
        for part in str(token).replace(",", " ").split():
            if not part:
                continue
            if "-" in part:
                start_text, end_text = part.split("-", 1)
                start, end = int(start_text), int(end_text)
                if end < start:
                    start, end = end, start
                values = range(start, end + 1)
            else:
                values = (int(part),)
            for value in values:
                if value not in seen:
                    seen.add(value)
                    seeds.append(value)
    return seeds


def _preset_path(preset: str) -> Path:
    path = REPO / "presets" / f"{preset}.stl"
    return path if path.exists() else Path(preset)


# ---------------------------------------------------------------------------
# Metric helpers
# ---------------------------------------------------------------------------
def _finite_float(value):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if np.isfinite(result) else None


def _minimum(values):
    defined = [value for value in values if value is not None]
    return float(min(defined)) if defined else None


def _sample(analysis: dict) -> dict:
    """Flatten one ``analyze_growth_paths`` result to the metrics we need."""
    return {
        "crossings": int(analysis.get("crossings", 0) or 0),
        "clearance_violations": int(
            analysis.get("clearance_violations", 0) or 0
        ),
        "min_clearance": _finite_float(analysis.get("min_clearance")),
        "min_incidence_deg": _finite_float(
            analysis.get("min_incidence_deg")
        ),
        "t_junction_ratio": _finite_float(
            analysis.get("t_junction_ratio", 0.0)
        )
        or 0.0,
        "t_junctions": int(analysis.get("t_junctions", 0) or 0),
        "y_junctions": int(analysis.get("y_junctions", 0) or 0),
        "tortuosity_median": _finite_float(
            analysis.get("tortuosity_median", 0.0)
        )
        or 0.0,
        "tortuosity_p05": _finite_float(
            analysis.get("tortuosity_p05", 0.0)
        )
        or 0.0,
    }


def _aggregate(preset, severity, seed_count, samples, errors, examples):
    return {
        "preset": preset,
        "S": float(severity),
        "seeds": int(seed_count),
        "crossings": int(sum(s["crossings"] for s in samples)),
        "clearance_violations": int(
            sum(s["clearance_violations"] for s in samples)
        ),
        "minimum_clearance": _minimum(
            s["min_clearance"] for s in samples
        ),
        "min_incidence_deg": _minimum(
            s["min_incidence_deg"] for s in samples
        ),
        "t_junction_ratio": (
            float(np.mean([s["t_junction_ratio"] for s in samples]))
            if samples
            else 0.0
        ),
        "t_junctions": int(sum(s["t_junctions"] for s in samples)),
        "y_junctions": int(sum(s["y_junctions"] for s in samples)),
        "tortuosity_median": (
            float(np.median([s["tortuosity_median"] for s in samples]))
            if samples
            else 0.0
        ),
        "tortuosity_p05": (
            float(np.median([s["tortuosity_p05"] for s in samples]))
            if samples
            else 0.0
        ),
        "errors": int(errors),
        "error_examples": examples,
    }


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------
def audit(preset: str, severity: float, seeds: list[int]):
    """Run every seed for one (preset, severity) row."""
    path = _preset_path(preset)
    validation = kintsugi.validate_and_load_mesh(path, 0.0)
    mesh, manifold = validation
    params = kintsugi.compute_parameters(
        severity, mesh, manifold=manifold
    )

    samples = []
    errors = 0
    examples: list[str] = []
    for seed in seeds:
        try:
            paths = kintsugi.generate_crack_growth_paths(
                params, np.random.default_rng(seed)
            )
            analysis = kintsugi.analyze_growth_paths(paths, params)
        except Exception as exc:  # report the seed and keep going
            errors += 1
            if len(examples) < 8:
                message = f"{type(exc).__name__}: {exc}"
                examples.append(f"seed {seed}: {message[:200]}")
            continue
        samples.append(_sample(analysis))

    row = _aggregate(
        Path(preset).stem,
        severity,
        len(seeds),
        samples,
        errors,
        examples,
    )
    return row, samples


def _summary(seeds, rows, samples, total_errors):
    total_crossings = int(sum(row["crossings"] for row in rows))
    total_clearance = int(
        sum(row["clearance_violations"] for row in rows)
    )
    min_clearance = _minimum(s["min_clearance"] for s in samples)
    min_incidence = _minimum(s["min_incidence_deg"] for s in samples)
    t_ratio = (
        float(np.mean([s["t_junction_ratio"] for s in samples]))
        if samples
        else 0.0
    )
    tortuosity_median = (
        float(np.median([s["tortuosity_median"] for s in samples]))
        if samples
        else 0.0
    )
    tortuosity_p05 = (
        float(np.median([s["tortuosity_p05"] for s in samples]))
        if samples
        else 0.0
    )

    summary = {
        "seeds_requested": len(seeds),
        "rows": len(rows),
        "total_crossings": total_crossings,
        "total_clearance_violations": total_clearance,
        "min_clearance": min_clearance,
        "min_incidence_deg": min_incidence,
        "t_junction_ratio": t_ratio,
        "tortuosity_median": tortuosity_median,
        "tortuosity_p05": tortuosity_p05,
        "errors": int(total_errors),
        "pass_crossings": total_crossings == 0,
        "pass_clearance": total_clearance == 0,
        "pass_t_junctions": t_ratio >= 0.80,
        "pass_tortuosity": tortuosity_median >= 1.05,
    }
    summary["ok"] = all(
        summary[key]
        for key in (
            "pass_crossings",
            "pass_clearance",
            "pass_t_junctions",
            "pass_tortuosity",
        )
    )
    return summary


def _fmt(value, spec=".3f") -> str:
    return "n/a" if value is None else format(float(value), spec)


def _print_row(row: dict) -> None:
    print(
        f"{row['preset']:>12} S={row['S']:<4g} seeds={row['seeds']:<4d}"
        f" cross={row['crossings']:<4d}"
        f" clear={row['clearance_violations']:<4d}"
        f" min_clear={_fmt(row['minimum_clearance'])}"
        f" min_inc={_fmt(row['min_incidence_deg'], '.1f')}"
        f" T-ratio={row['t_junction_ratio']:.3f}"
        f" T/Y={row['t_junctions']}/{row['y_junctions']}"
        f" tort={row['tortuosity_median']:.3f}"
        f"/{row['tortuosity_p05']:.3f}"
        f" err={row['errors']}",
        flush=True,
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--presets",
        nargs="+",
        default=["tea_bowl", "vase"],
        help="Preset ids or mesh paths (default: tea_bowl vase)",
    )
    parser.add_argument(
        "--severities",
        nargs="+",
        type=float,
        default=[0.6, 1.0],
        help="Severity values S (default: 0.6 1.0)",
    )
    parser.add_argument(
        "--seeds",
        nargs="+",
        default=["300-499"],
        help="Seeds: '300-499' and/or a list, comma-separated",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"JSON output path (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args(argv)

    seeds = parse_seeds(args.seeds)
    if not seeds:
        parser.error("--seeds did not contain any integers")

    rows: list[dict] = []
    all_samples: list[dict] = []
    total_errors = 0

    for preset in args.presets:
        for severity in args.severities:
            try:
                row, samples = audit(preset, severity, seeds)
            except Exception as exc:  # a bad preset must not abort the audit
                message = f"{type(exc).__name__}: {exc}"
                row = _aggregate(
                    Path(preset).stem,
                    severity,
                    len(seeds),
                    [],
                    len(seeds),
                    [message[:200]],
                )
                samples = []
            rows.append(row)
            all_samples.extend(samples)
            total_errors += row["errors"]
            _print_row(row)

    summary = _summary(seeds, rows, all_samples, total_errors)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps({"summary": summary, "rows": rows}, indent=2)
    )

    verdict = "PASS" if (summary["ok"] and total_errors == 0) else "FAIL"
    print(
        f"growth audit {verdict}: seeds={summary['seeds_requested']}"
        f" rows={summary['rows']}"
        f" crossings={summary['total_crossings']}"
        f" clearance={summary['total_clearance_violations']}"
        f" min_clear={_fmt(summary['min_clearance'])}"
        f" T-ratio={summary['t_junction_ratio']:.3f}"
        f" tort={summary['tortuosity_median']:.3f}"
        f" errors={summary['errors']}",
        flush=True,
    )
    print(output)
    return 0 if (summary["ok"] and total_errors == 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())
