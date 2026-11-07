#!/usr/bin/env python3
"""Kintsugi mesh fracture engine.

The module turns a pristine, closed vessel mesh into a two-part Kintsugi
assembly whose crack density, seam width and vertical trauma band scale with an
income-ratio metric ``R``.  Geometry is built in an unrolled cylindrical
parameter space and cut with exact Manifold3D boolean operations.

Public API
----------
``generate_kintsugi_mesh(input_path, output_dir, R, ...)``
    End-to-end generation, returning paths, volumes, triangle counts and timings.

Command line
------------
``python kintsugi.py bowl.stl -o output --R 0.4 --mode ribbon``
"""

from __future__ import annotations

import argparse
import io
import json
import math
import time
import zipfile
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence
from xml.etree import ElementTree as ET

import manifold3d as mf
import numpy as np
import trimesh
from scipy.spatial import Voronoi, cKDTree

__all__ = [
    "compute_severity",
    "compute_parameters",
    "validate_and_load_mesh",
    "trimesh_to_manifold",
    "manifold_to_trimesh",
    "generate_kintsugi_mesh",
    "generate_crack_paths",
    "generate_crack_growth_paths",
    "generate_crack_voronoi_paths",
    "analyze_growth_paths",
    "project_crack_paths",
    "build_vein_cutter",
    "build_ribbon_cutter",
    "swap_debris",
    "export_kintsugi_stl",
    "export_kintsugi_3mf",
]

CORE_NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"

ET.register_namespace("", CORE_NS)

MIN_EXTENT_MM = 20.0
MAX_EXTENT_MM = 300.0
MIN_SEAM_WIDTH_MM = 0.8
DEBRIS_VOLUME_MM3 = 1.0
RECOMMENDED_CIRCULAR_SEGMENTS = 16
RASTER_Z_LEVELS = 9
RADIAL_PROBES = 48


# ---------------------------------------------------------------------------
# Metric validation and parameter table
# ---------------------------------------------------------------------------
def compute_severity(R: float) -> float:
    """Validate ``R`` and return severity ``S = 1 - clip(R, 0, 1)``."""
    try:
        value = float(R)
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
        raise ValueError(f"R must be a finite number, got {R!r}") from exc
    if not math.isfinite(value):
        raise ValueError(f"R must be a finite number, got {value!r}")
    return 1.0 - min(max(value, 0.0), 1.0)


def compute_parameters(
    S: float,
    mesh: trimesh.Trimesh,
    manifold: mf.Manifold | None = None,
    seam_width: float | None = None,
    probe: dict | None = None,
) -> dict:
    """Compute the metric-driven fracture parameter table for a mesh."""
    S = float(S)
    if not math.isfinite(S):
        raise ValueError("Severity must be finite")
    S = min(max(S, 0.0), 1.0)

    if seam_width is not None:
        seam_width = float(seam_width)
        if seam_width < MIN_SEAM_WIDTH_MM:
            raise ValueError(
                f"seam_width must be at least {MIN_SEAM_WIDTH_MM} mm, "
                f"got {seam_width}"
            )

    extents = np.asarray(mesh.extents, dtype=np.float64)
    H_mesh = float(extents[2])
    if H_mesh <= 0.0:
        raise ValueError("Input mesh has zero Z extent")

    z_lo = float(mesh.bounds[0][2])
    z_hi = float(mesh.bounds[1][2])
    z_center = 0.5 * (z_lo + z_hi)
    H = H_mesh * (0.2 + 0.8 * S)
    z_min = max(z_lo, z_center - 0.5 * H)
    z_max = min(z_hi, z_center + 0.5 * H)

    N = int(math.floor(2.0 + 8.0 * S))
    W = float(seam_width) if seam_width is not None else 0.8 + 1.4 * S

    if probe is None:
        if manifold is None:
            manifold = trimesh_to_manifold(mesh)
        rbar, miss_fraction = _radial_probe(
            manifold, mesh, z_min=z_min, z_max=z_max
        )
        wall_probe = _probe_wall_range(manifold, mesh)
    else:
        rbar = float(probe["rbar"])
        miss_fraction = float(probe["miss_fraction"])
        wall_probe = {
            "wall_z_min": float(probe["wall_z_min"]),
            "wall_z_max": float(probe["wall_z_max"]),
            "median_two_hit_wall": float(probe["median_two_hit_wall"]),
            "has_wall": bool(probe.get("has_wall", True)),
        }
    if miss_fraction > 0.05:
        raise ValueError(
            "The input is not a vessel that the cylindrical parameterisation "
            f"supports: {miss_fraction:.1%} of radial probes missed the mesh "
            "(limit 5%)"
        )

    if not bool(wall_probe.get("has_wall", True)):
        raise ValueError(
            "Input has no usable wall: radial probes never find the two hits "
            "needed for a vessel wall in any Z band"
        )

    wall_z_min = float(wall_probe["wall_z_min"])
    wall_z_max = float(wall_probe["wall_z_max"])
    # The lower side stays half a seam above the floor.  The upper side is
    # allowed to overshoot the rim by a full seam so the cutter can pierce the
    # lip; projection clamps the ray height just below the rim plane to avoid
    # coplanar faces on the horizontal top surface.
    z_wall_lo = wall_z_min + 0.5 * W
    z_wall_hi = wall_z_max + W
    if z_wall_lo >= z_wall_hi:
        raise ValueError(
            "Input has no usable wall range: the two-hit wall is thinner than "
            "one seam width"
        )

    return {
        "S": S,
        "N": N,
        "W": W,
        "H": H,
        "H_mesh": H_mesh,
        "z_center": z_center,
        "z_min": z_min,
        "z_max": z_max,
        "z_mesh_lo": z_lo,
        "z_mesh_hi": z_hi,
        "wall_z_min": wall_z_min,
        "wall_z_max": wall_z_max,
        "median_two_hit_wall": float(wall_probe["median_two_hit_wall"]),
        "z_wall_lo": z_wall_lo,
        "z_wall_hi": z_wall_hi,
        "rbar": float(rbar),
        "period": float(2.0 * math.pi * rbar),
    }


# ---------------------------------------------------------------------------
# Mesh conversion and input validation
# ---------------------------------------------------------------------------
def trimesh_to_manifold(mesh: trimesh.Trimesh) -> mf.Manifold:
    """Convert a Trimesh to Manifold using float64 vertices (``Mesh64``)."""
    vertices = np.array(mesh.vertices, dtype=np.float64, order="C", copy=True)
    faces = np.array(mesh.faces, dtype=np.uint64, order="C", copy=True)
    mesh64 = mf.Mesh64(vertices, faces)
    return mf.Manifold(mesh64)


def manifold_to_trimesh(manifold: mf.Manifold) -> trimesh.Trimesh:
    """Convert a Manifold to a Trimesh without repairing or reordering."""
    if manifold.is_empty():
        return trimesh.Trimesh(
            vertices=np.empty((0, 3), dtype=np.float64),
            faces=np.empty((0, 3), dtype=np.int64),
            process=False,
        )
    mesh64 = manifold.to_mesh64()
    vertices = np.array(mesh64.vert_properties[:, :3], dtype=np.float64, copy=True)
    faces = np.array(mesh64.tri_verts, dtype=np.int64, copy=True)
    return trimesh.Trimesh(vertices=vertices, faces=faces, process=False)


def _stl_bad_edge_count(mesh: trimesh.Trimesh) -> int:
    """Count edges used by ≠2 faces after a binary-STL reload."""
    if len(mesh.faces) == 0:
        return 0
    data = trimesh.exchange.stl.export_stl(mesh)
    loaded = trimesh.load(io.BytesIO(data), file_type="stl", process=True)
    if isinstance(loaded, trimesh.Scene):
        loaded = loaded.dump(concatenate=True)
    if len(loaded.edges_sorted) == 0:
        return 0
    rows = np.sort(np.asarray(loaded.edges_sorted, dtype=np.int64), axis=1)
    _, counts = np.unique(rows, axis=0, return_counts=True)
    return int(np.count_nonzero(counts != 2))


def _roundtrip_bad_edges(manifold: mf.Manifold) -> int:
    """Count bad edges after the same repair/export path used for writing."""
    if manifold.is_empty():
        return 0
    return _stl_bad_edge_count(_export_trimesh(manifold))


def _clean_mesh(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Lossless clean-up only: merge duplicates, drop degenerates, fix winding."""
    mesh = mesh.copy()
    mesh.merge_vertices()
    mesh.update_faces(mesh.nondegenerate_faces())
    mesh.remove_unreferenced_vertices()
    mesh.fix_normals(multibody=True)
    return mesh


def _load_trimesh(path: str | Path) -> trimesh.Trimesh:
    loaded = trimesh.load(str(path), force="mesh", process=False)
    if isinstance(loaded, trimesh.Scene):
        if not loaded.geometry:
            raise ValueError(f"No geometry found in {path}")
        loaded = loaded.dump(concatenate=True)
    if not isinstance(loaded, trimesh.Trimesh) or len(loaded.faces) == 0:
        raise ValueError(f"No triangle geometry found in {path}")
    return loaded


def _extent_error(extents: np.ndarray) -> str | None:
    for axis, value in zip("XYZ", extents):
        if value < MIN_EXTENT_MM or value > MAX_EXTENT_MM:
            return (
                f"Bounding-box {axis} extent is {value:.6g} mm; the supported "
                f"range is [{MIN_EXTENT_MM:g}, {MAX_EXTENT_MM:g}] mm. "
                "Check that the model is authored in millimetres."
            )
    return None


def _radial_probe(
    manifold: mf.Manifold,
    mesh: trimesh.Trimesh,
    z_min: float,
    z_max: float,
    *,
    z_levels: int = RASTER_Z_LEVELS,
    theta_samples: int = RADIAL_PROBES,
) -> tuple[float, float]:
    """Return mean outer radius and ray-miss fraction inside a Z band."""
    center = np.asarray(mesh.bounding_box.centroid, dtype=np.float64)
    cx, cy = float(center[0]), float(center[1])
    ray_length = 2.0 * float(np.max(mesh.extents)) + 10.0
    thetas = np.linspace(0.0, 2.0 * math.pi, theta_samples, endpoint=False)
    zs = np.linspace(z_min, z_max, z_levels + 2)[1:-1]

    radii: list[float] = []
    misses = 0
    total = 0
    for z in zs:
        for theta in thetas:
            total += 1
            start = np.array([cx, cy, z], dtype=np.float64)
            direction = np.array([math.cos(theta), math.sin(theta), 0.0])
            end = start + direction * ray_length
            hits = manifold.ray_cast(
                tuple(start.tolist()), tuple(end.tolist())
            )
            if not hits:
                misses += 1
                continue
            farthest = max(hit.distance for hit in hits) * ray_length
            radii.append(float(farthest))

    miss_fraction = misses / total if total else 1.0
    mean_radius = float(np.mean(radii)) if radii else 0.0
    return mean_radius, miss_fraction


def _probe_wall_range(
    manifold: mf.Manifold,
    mesh: trimesh.Trimesh,
    *,
    z_levels: int = 121,
    theta_samples: int = RADIAL_PROBES,
) -> dict:
    """Find the Z range where radial rays hit a wall (at least two hits).

    Returns the two-hit Z range and the median two-hit wall thickness.  The
    solid base of a bowl produces only one hit; crack points must stay out of
    that range so ribbon slots cannot run through the floor.
    """
    center = np.asarray(mesh.bounding_box.centroid, dtype=np.float64)
    cx, cy = float(center[0]), float(center[1])
    z_lo, z_hi = (float(value) for value in mesh.bounds[:, 2])
    ray_length = 2.0 * float(np.max(mesh.extents)) + 10.0
    thetas = np.linspace(0.0, 2.0 * math.pi, theta_samples, endpoint=False)
    zs = np.linspace(z_lo, z_hi, max(z_levels, 8))

    two_hit_fraction = []
    wall_thicknesses: list[float] = []
    for z in zs:
        two_hits = 0
        for theta in thetas:
            start = np.array([cx, cy, z], dtype=np.float64)
            direction = np.array([math.cos(theta), math.sin(theta), 0.0])
            end = start + direction * ray_length
            hits = manifold.ray_cast(
                tuple(start.tolist()), tuple(end.tolist())
            )
            if len(hits) >= 2:
                two_hits += 1
                ordered = sorted(hits, key=lambda hit: hit.distance)
                wall_thicknesses.append(
                    (float(ordered[-1].distance) - float(ordered[-2].distance))
                    * ray_length
                )
        two_hit_fraction.append(two_hits / theta_samples)

    fraction = np.asarray(two_hit_fraction, dtype=np.float64)
    wall_mask = fraction >= 0.95
    has_wall = bool(np.any(wall_mask))
    if has_wall:
        wall_z_min = float(zs[np.argmax(wall_mask)])
        wall_z_max = float(zs[len(wall_mask) - 1 - np.argmax(wall_mask[::-1])])
    else:
        wall_z_min, wall_z_max = z_lo, z_hi

    median_wall = (
        float(np.median(wall_thicknesses)) if wall_thicknesses else 1.0
    )
    return {
        "wall_z_min": wall_z_min,
        "wall_z_max": wall_z_max,
        "median_two_hit_wall": median_wall,
        "has_wall": has_wall,
    }


@dataclass
class MeshValidation:
    """Validated mesh plus the radial probe computed during validation.

    Iterable as ``(mesh, manifold)`` for backwards compatibility with callers
    that only need those two values.
    """

    mesh: trimesh.Trimesh
    manifold: mf.Manifold
    probe: dict

    def __iter__(self):
        yield self.mesh
        yield self.manifold


def validate_and_load_mesh(
    path: str | Path, S: float = 0.0
) -> MeshValidation:
    """Validate a mesh against the supported envelope and build one Manifold.

    This runs before any branch on ``R``, including the wealthy pass-through.
    The returned object carries the radial probe so ``compute_parameters`` can
    reuse it instead of probing the same mesh a second time.
    """
    mesh = _clean_mesh(_load_trimesh(path))

    if not mesh.is_watertight or not mesh.is_volume:
        raise ValueError(
            "Input mesh is not a valid closed solid: it must be a closed, "
            "orientable 2-manifold with positive volume and no boundary edges"
        )

    extents = np.asarray(mesh.extents, dtype=np.float64)
    extent_message = _extent_error(extents)
    if extent_message:
        raise ValueError(extent_message)

    manifold = trimesh_to_manifold(mesh)
    if manifold.status() != mf.Error.NoError:
        raise ValueError(
            f"Input mesh is not a valid closed solid: Manifold status is "
            f"{manifold.status()}"
        )
    if manifold.volume() <= 0.0:
        raise ValueError(
            "Input mesh is not a valid closed solid: non-positive volume"
        )

    # Envelope: radially star-shaped exterior inside the trauma band.  The
    # band is derived from S, but for all S in [0, 1] it is non-empty.
    H_mesh = float(extents[2])
    z_center = 0.5 * (float(mesh.bounds[0][2]) + float(mesh.bounds[1][2]))
    H = H_mesh * (0.2 + 0.8 * min(max(float(S), 0.0), 1.0))
    z_min = max(float(mesh.bounds[0][2]), z_center - 0.5 * H)
    z_max = min(float(mesh.bounds[1][2]), z_center + 0.5 * H)
    rbar, miss_fraction = _radial_probe(
        manifold, mesh, z_min=z_min, z_max=z_max
    )
    if miss_fraction > 0.05:
        raise ValueError(
            "The input is not a vessel that the cylindrical parameterisation "
            f"supports: {miss_fraction:.1%} of radial probes in the trauma band "
            "missed the mesh (limit 5%)"
        )

    wall_probe = _probe_wall_range(manifold, mesh)
    return MeshValidation(
        mesh=mesh,
        manifold=manifold,
        probe={
            "rbar": float(rbar),
            "miss_fraction": float(miss_fraction),
            **wall_probe,
        },
    )


# ---------------------------------------------------------------------------
# Parameter-space crack network
# ---------------------------------------------------------------------------
MAX_NOISE_GRADIENT = 0.70


def _make_noise(rbar: float, base_amplitude: float, rng: np.random.Generator):
    """Return a deterministic, theta-periodic dyadic sine field ``eta(u, z)``.

    The octave amplitudes are normalised so the triangle-inequality bound on
    every spatial derivative is at most ``MAX_NOISE_GRADIENT``.  With
    $a_k = A 2^{-k}$ and $f_k = 2^k$, each octave contributes $A f_k$ to the
    derivative, so the bound is $4 A \\max(1/\\bar r, 0.13)$.  Keeping that below
    1.0 preserves injectivity of the displacement and prevents fold-overs.
    """
    period = 2.0 * math.pi * rbar
    phases_u = rng.uniform(0.0, 2.0 * math.pi, size=4)
    phases_z = rng.uniform(0.0, 2.0 * math.pi, size=4)

    gradient_per_amplitude = 4.0 * max(1.0 / rbar, 0.13)
    amplitude_base = float(base_amplitude)
    gradient_bound = amplitude_base * gradient_per_amplitude
    if gradient_bound > MAX_NOISE_GRADIENT:
        amplitude_base *= MAX_NOISE_GRADIENT / gradient_bound

    def eta(u: np.ndarray | float, z: np.ndarray | float):
        u_arr = np.asarray(u, dtype=np.float64)
        z_arr = np.asarray(z, dtype=np.float64)
        theta = u_arr / rbar
        du = np.zeros_like(theta)
        dz = np.zeros_like(theta)
        for k in range(4):
            freq = float(2**k)
            amplitude = amplitude_base * (2.0 ** (-k))
            phase = freq * theta + phases_u[k] + 0.11 * freq * z_arr
            du += amplitude * np.sin(phase)
            dz += amplitude * np.cos(
                freq * theta + phases_z[k] + 0.13 * freq * z_arr
            )
        return du, dz

    return eta


def _clip_segment_to_rect(
    p0: np.ndarray,
    p1: np.ndarray,
    u_min: float,
    u_max: float,
    z_min: float,
    z_max: float,
) -> tuple[np.ndarray, np.ndarray] | None:
    """Liang-Barsky style clipping for a 2-D segment."""
    x0, y0 = float(p0[0]), float(p0[1])
    x1, y1 = float(p1[0]), float(p1[1])
    dx, dy = x1 - x0, y1 - y0
    t0, t1 = 0.0, 1.0

    for p, q in (
        (-dx, x0 - u_min),
        (dx, u_max - x0),
        (-dy, y0 - z_min),
        (dy, z_max - y0),
    ):
        if abs(p) < 1e-15:
            if q < 0.0:
                return None
            continue
        r = q / p
        if p < 0.0:
            if r > t1:
                return None
            t0 = max(t0, r)
        else:
            if r < t0:
                return None
            t1 = min(t1, r)
    if t1 - t0 <= 1e-12:
        return None
    return (
        np.array([x0 + t0 * dx, y0 + t0 * dy], dtype=np.float64),
        np.array([x0 + t1 * dx, y0 + t1 * dy], dtype=np.float64),
    )


def _ray_tiebreak_direction(
    seed_a: np.ndarray,
    seed_b: np.ndarray,
    third: np.ndarray,
    normal: np.ndarray,
) -> np.ndarray:
    """Choose the normal sign pointing away from the third seed's side of ab."""
    midpoint = 0.5 * (np.asarray(seed_a, dtype=np.float64) + np.asarray(seed_b, dtype=np.float64))
    direction = np.asarray(normal, dtype=np.float64)
    if float(np.dot(direction, np.asarray(third, dtype=np.float64) - midpoint)) >= 0.0:
        direction = -direction
    return direction


def _ridge_segment(
    vor: Voronoi, ridge_index: int, ridge: tuple[int, int]
) -> tuple[np.ndarray, np.ndarray] | None:
    a, b = ridge
    if a >= 0 and b >= 0:
        return np.asarray(vor.vertices[a]), np.asarray(vor.vertices[b])
    if a < 0 and b < 0:
        return None
    finite_index = a if a >= 0 else b
    seed_a, seed_b = vor.points[vor.ridge_points[ridge_index]]
    finite = np.asarray(vor.vertices[finite_index], dtype=np.float64)

    # An unbounded Voronoi ridge is a ray, not a full line.  The defining
    # property is that a point just along the ray is closer to the ridge's two
    # seeds than to any other seed.  A finite vertex can sit far outside the
    # seed cloud, where the "away from the third seed" sign is ambiguous, so
    # evaluate both normal directions against that property and use the third
    # Delaunay seed only as a numerical tie-break.
    seed_tangent = np.asarray(seed_b, dtype=np.float64) - np.asarray(
        seed_a, dtype=np.float64
    )
    seed_tangent /= np.linalg.norm(seed_tangent)
    normal = np.array([-seed_tangent[1], seed_tangent[0]])
    ridge_seeds = vor.ridge_points[ridge_index]
    probe_delta = 1e-4 * max(float(np.ptp(vor.points[:, 0])), 1.0)

    def _direction_margin(direction: np.ndarray) -> float:
        probe = finite + direction * probe_delta
        distances = np.linalg.norm(vor.points - probe, axis=1)
        d_ridge = float(np.min(distances[ridge_seeds]))
        d_other = float(np.min(np.delete(distances, ridge_seeds)))
        return d_other - d_ridge

    margin_normal = _direction_margin(normal)
    margin_flipped = _direction_margin(-normal)
    if abs(margin_normal - margin_flipped) < 1e-12:
        distances = np.linalg.norm(vor.points - finite, axis=1)
        distances[ridge_seeds] = np.inf
        third_seed = vor.points[int(np.argmin(distances))]
        direction = _ray_tiebreak_direction(
            seed_a, seed_b, third_seed, normal
        )
    else:
        direction = normal if margin_normal >= margin_flipped else -normal
    span = 4.0 * float(np.ptp(vor.points[:, 0])) + 1.0
    return finite, finite + direction * span


def _merge_collinear_segments(
    segments: list[tuple[np.ndarray, np.ndarray]],
    tol: float = 1e-6,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Union collinear overlapping fragments from the same periodic ridge."""
    merged_segments: list[tuple[np.ndarray, np.ndarray]] = []
    used = [False] * len(segments)
    for index, (a0, a1) in enumerate(segments):
        if used[index]:
            continue
        used[index] = True
        origin = np.asarray(a0, dtype=np.float64).copy()
        end = np.asarray(a1, dtype=np.float64).copy()
        changed = True
        while changed:
            changed = False
            vector = end - origin
            length = float(np.linalg.norm(vector))
            if length < 1e-12:
                break
            direction = vector / length
            for other_index in range(len(segments)):
                if used[other_index]:
                    continue
                b0, b1 = segments[other_index]
                perpendicular = max(
                    abs(
                        direction[0] * (point[1] - origin[1])
                        - direction[1] * (point[0] - origin[0])
                    )
                    for point in (b0, b1)
                )
                if perpendicular > tol:
                    continue
                t0 = float(np.dot(np.asarray(b0) - origin, direction))
                t1 = float(np.dot(np.asarray(b1) - origin, direction))
                lo, hi = min(t0, t1), max(t0, t1)
                if hi < -tol or lo > length + tol:
                    continue
                new_lo = min(0.0, lo)
                new_hi = max(length, hi)
                origin = origin + direction * new_lo
                end = origin + direction * (new_hi - new_lo)
                used[other_index] = True
                changed = True
        merged_segments.append((origin, end))
    return merged_segments


def _unwrap_u(u_values: np.ndarray, period: float) -> np.ndarray:
    """Remove 2π-seam jumps from a polyline's u coordinates."""
    values = np.asarray(u_values, dtype=np.float64)
    if len(values) == 0:
        return values.copy()
    out = np.empty_like(values)
    out[0] = values[0]
    for index in range(1, len(values)):
        previous = out[index - 1]
        out[index] = values[index] + period * np.round(
            (previous - values[index]) / period
        )
    return out


def _truncate_polyline_z(
    points: np.ndarray,
    lo: float,
    hi: float,
    *,
    min_length: float,
) -> list[np.ndarray]:
    """Cut a polyline into pieces that stay inside ``lo <= z <= hi``.

    Crossing points are interpolated on the polyline; outside parts are
    discarded.  No point is projected onto the limit line.  A polyline that
    leaves and re-enters becomes several pieces.
    """
    points = np.asarray(points, dtype=np.float64)
    if len(points) < 2:
        return []
    pieces: list[list[np.ndarray]] = []
    current: list[np.ndarray] = []

    def _finish() -> None:
        nonlocal current
        if len(current) >= 2:
            pieces.append(current)
        current = []

    for index in range(len(points) - 1):
        p0 = points[index]
        p1 = points[index + 1]
        z0, z1 = float(p0[1]), float(p1[1])
        if abs(z1 - z0) < 1e-15:
            if lo <= z0 <= hi:
                t0, t1 = 0.0, 1.0
            else:
                t0, t1 = 1.0, 0.0
        else:
            ta = (lo - z0) / (z1 - z0)
            tb = (hi - z0) / (z1 - z0)
            if ta > tb:
                ta, tb = tb, ta
            t0 = max(0.0, ta)
            t1 = min(1.0, tb)
        if t1 <= t0 + 1e-15:
            _finish()
            continue

        q0 = p0 + (p1 - p0) * t0
        q1 = p0 + (p1 - p0) * t1
        if current and float(np.linalg.norm(current[-1] - q0)) <= 1e-9:
            if float(np.linalg.norm(current[-1] - q1)) > 1e-12:
                current.append(q1)
        else:
            _finish()
            if float(np.linalg.norm(q1 - q0)) > 1e-12:
                current = [q0, q1]
        if t1 < 1.0 - 1e-12:
            _finish()

    _finish()
    result: list[np.ndarray] = []
    for piece in pieces:
        array = np.asarray(piece, dtype=np.float64)
        if len(array) < 2:
            continue
        length = float(np.sum(np.linalg.norm(np.diff(array, axis=0), axis=1)))
        if length >= min_length:
            result.append(array)
    return result


# ---------------------------------------------------------------------------
# Sequential rim-seeded crack growth generator
# ---------------------------------------------------------------------------
GROWTH_CLEARANCE_MM = 0.8
GROWTH_MIN_INCIDENCE_DEG = 30.0
GROWTH_MIN_DEPTH_MM = 0.25
_GROWTH_DOWN = -0.5 * math.pi
_GROWTH_MIN_HEADING = _GROWTH_DOWN - math.pi / 3.0
_GROWTH_MAX_HEADING = _GROWTH_DOWN + math.pi / 3.0


@dataclass
class _GrowthTask:
    """Mutable cursor for one FIFO crack-growth front."""

    path_id: int
    heading: float
    traveled: float
    z_limit: float
    budget: float
    level: int
    exempt_path_id: int | None = None
    exempt_origin: np.ndarray | None = None
    branch_spawned: bool = False
    branch_at: int | None = None
    steps: int = 0


def _clamp_heading(heading: float) -> float:
    return min(max(float(heading), _GROWTH_MIN_HEADING), _GROWTH_MAX_HEADING)


def _circular_distance(u: float, v: float, period: float) -> float:
    delta = abs(float(u) - float(v)) % period
    return min(delta, period - delta)


def _periodic_distance(p, q, period: float) -> float:
    du = abs(float(p[0]) - float(q[0])) % period
    du = min(du, period - du)
    return math.hypot(du, float(p[1]) - float(q[1]))


def _poisson_rim_seeds(
    count: int, period: float, min_sep: float, rng: np.random.Generator
) -> list[float]:
    """Draw ``count`` rim angles with a hard circular Poisson separation."""
    if count <= 0:
        return []
    if count * min_sep >= period:
        min_sep = period / (count + 1.0)
    seeds: list[float] = []
    attempts = 0
    limit = max(2000, count * 300)
    while len(seeds) < count and attempts < limit:
        candidate = float(rng.uniform(0.0, period))
        if all(_circular_distance(candidate, other, period) >= min_sep for other in seeds):
            seeds.append(candidate)
        attempts += 1
    while len(seeds) < count:
        if not seeds:
            seeds.append(0.0)
            continue
        ordered = sorted(seeds)
        best_index = 0
        best_gap = -1.0
        for index, value in enumerate(ordered):
            following = ordered[(index + 1) % len(ordered)]
            gap = (following - value) % period
            if gap > best_gap:
                best_gap = gap
                best_index = index
        seeds.append(
            (ordered[best_index] + 0.5 * best_gap) % period
        )
    return [float(value) for value in seeds[:count]]


def _unwrap_growth_segment(a, b, period: float) -> tuple[np.ndarray, np.ndarray]:
    first = np.asarray(a, dtype=np.float64).copy()
    second = np.asarray(b, dtype=np.float64).copy()
    delta = float(second[0] - first[0])
    if delta > 0.5 * period:
        second[0] -= period
    elif delta < -0.5 * period:
        second[0] += period
    return first, second


def _project_point_on_segment(p, a, b) -> tuple[float, np.ndarray]:
    ab = b - a
    denom = float(np.dot(ab, ab))
    if denom < 1e-18:
        return 0.0, a.copy()
    t = float(np.dot(p - a, ab) / denom)
    t = min(max(t, 0.0), 1.0)
    return t, a + t * ab


def _point_segment_distance(p, a, b) -> tuple[float, float, np.ndarray]:
    t, q = _project_point_on_segment(p, a, b)
    return float(np.linalg.norm(p - q)), t, q


def _segment_contact(a, b, c, d) -> tuple[float, float, float, np.ndarray]:
    """Closest/intersection contact from candidate ``ab`` onto segment ``cd``.

    Returns ``(distance, t_on_ab, u_on_cd, contact_on_cd)``.
    """
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    c = np.asarray(c, dtype=np.float64)
    d = np.asarray(d, dtype=np.float64)
    r = b - a
    s = d - c
    ca = c - a
    denom = float(r[0] * s[1] - r[1] * s[0])
    if abs(denom) > 1e-12:
        t = float((ca[0] * s[1] - ca[1] * s[0]) / denom)
        u = float((ca[0] * r[1] - ca[1] * r[0]) / denom)
        if -1e-9 <= t <= 1.0 + 1e-9 and -1e-9 <= u <= 1.0 + 1e-9:
            t = min(max(t, 0.0), 1.0)
            u = min(max(u, 0.0), 1.0)
            return 0.0, t, u, c + u * s

    best_distance = math.inf
    best_t = 1.0
    best_u = 0.0
    best_point = c.copy()

    u_start, q_start = _project_point_on_segment(a, c, d)
    distance = float(np.linalg.norm(a - q_start))
    if distance < best_distance:
        best_distance, best_t, best_u, best_point = distance, 0.0, u_start, q_start

    u_end, q_end = _project_point_on_segment(b, c, d)
    distance = float(np.linalg.norm(b - q_end))
    if distance < best_distance:
        best_distance, best_t, best_u, best_point = distance, 1.0, u_end, q_end

    t_start, q_start = _project_point_on_segment(c, a, b)
    distance = float(np.linalg.norm(c - q_start))
    if distance < best_distance:
        best_distance, best_t, best_u, best_point = distance, t_start, 0.0, c.copy()

    t_end, q_end = _project_point_on_segment(d, a, b)
    distance = float(np.linalg.norm(d - q_end))
    if distance < best_distance:
        best_distance, best_t, best_u, best_point = distance, t_end, 1.0, d.copy()

    return best_distance, best_t, best_u, best_point


def _acute_angle_deg(first, second) -> float:
    a = np.asarray(first, dtype=np.float64)
    b = np.asarray(second, dtype=np.float64)
    norm_a = float(np.linalg.norm(a))
    norm_b = float(np.linalg.norm(b))
    if norm_a < 1e-12 or norm_b < 1e-12:
        return 0.0
    cosine = abs(float(np.dot(a, b)) / (norm_a * norm_b))
    return math.degrees(math.acos(min(max(cosine, -1.0), 1.0)))


def _segment_outside_circle(
    first: np.ndarray,
    second: np.ndarray,
    center: np.ndarray,
    radius: float,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Return the portions of a segment outside a circular exemption zone."""
    first = np.asarray(first, dtype=np.float64)
    second = np.asarray(second, dtype=np.float64)
    center = np.asarray(center, dtype=np.float64)
    vector = second - first
    length_sq = float(np.dot(vector, vector))
    if length_sq < 1e-18:
        if float(np.linalg.norm(first - center)) <= radius:
            return []
        return [(first.copy(), second.copy())]

    offset = first - center
    quadratic_b = 2.0 * float(np.dot(offset, vector))
    quadratic_c = float(np.dot(offset, offset)) - radius * radius
    discriminant = quadratic_b * quadratic_b - 4.0 * length_sq * quadratic_c
    inside_first = float(np.linalg.norm(first - center)) <= radius
    if discriminant <= 0.0:
        return [] if inside_first else [(first.copy(), second.copy())]

    root = math.sqrt(discriminant)
    t_low = (-quadratic_b - root) / (2.0 * length_sq)
    t_high = (-quadratic_b + root) / (2.0 * length_sq)
    if t_low > t_high:
        t_low, t_high = t_high, t_low
    lower = max(0.0, t_low)
    upper = min(1.0, t_high)
    if upper <= lower:
        return [] if inside_first else [(first.copy(), second.copy())]
    pieces: list[tuple[np.ndarray, np.ndarray]] = []
    if lower > 1e-9:
        pieces.append((first.copy(), first + vector * lower))
    if upper < 1.0 - 1e-9:
        pieces.append((first + vector * upper, second.copy()))
    return pieces


def _first_growth_collision(
    paths: Sequence[Sequence[np.ndarray]],
    path_id: int,
    a: np.ndarray,
    b: np.ndarray,
    *,
    period: float,
    r_clear: float,
    exempt_path_id: int | None = None,
    exempt_origin: np.ndarray | None = None,
    exempt_radius: float = 0.0,
) -> dict | None:
    """Return the earliest clearance contact along ``a -> b``, or ``None``."""
    best: dict | None = None
    midpoint = 0.5 * (np.asarray(a) + np.asarray(b))
    for other_id, points in enumerate(paths):
        count = len(points)
        if count < 2:
            continue
        for segment_index in range(count - 1):
            if other_id == path_id and segment_index == count - 2:
                continue
            c = np.asarray(points[segment_index], dtype=np.float64)
            d = np.asarray(points[segment_index + 1], dtype=np.float64)

            shift = round(
                (float(midpoint[0]) - 0.5 * float(c[0] + d[0])) / period
            ) * period
            shifted_c = c + np.array([shift, 0.0])
            shifted_d = d + np.array([shift, 0.0])
            full = shifted_d - shifted_c
            full_length_sq = float(np.dot(full, full))
            if full_length_sq < 1e-18:
                continue

            if (
                exempt_path_id is not None
                and other_id == exempt_path_id
                and exempt_origin is not None
            ):
                full_distance, full_t, _, _ = _segment_contact(
                    a, b, shifted_c, shifted_d
                )
                if full_distance <= 1e-7 and full_t > 1e-6:
                    # The exemption zone forgives proximity, never a real
                    # crossing of the parent crack away from the shared origin.
                    subsegments = [(shifted_c, shifted_d)]
                else:
                    subsegments = _segment_outside_circle(
                        shifted_c,
                        shifted_d,
                        exempt_origin,
                        exempt_radius,
                    )
            else:
                subsegments = [(shifted_c, shifted_d)]
            if not subsegments:
                continue

            for sub_c, sub_d in subsegments:
                distance, candidate_t, _, contact = _segment_contact(
                    a, b, sub_c, sub_d
                )
                if distance > r_clear + 1e-9:
                    continue
                contact_u = float(
                    np.dot(contact - shifted_c, full) / full_length_sq
                )
                contact_u = min(max(contact_u, 0.0), 1.0)
                tangent = full
                if float(np.linalg.norm(tangent)) < 1e-12:
                    continue
                free_end = (
                    (contact_u <= 1e-6 and segment_index == 0)
                    or (
                        contact_u >= 1.0 - 1e-6
                        and segment_index == count - 2
                    )
                )
                record = {
                    "distance": distance,
                    "t": candidate_t,
                    "path_id": other_id,
                    "segment_index": segment_index,
                    "hit": contact.copy(),
                    "hit_local": contact - np.array([shift, 0.0]),
                    "tangent": tangent,
                    "free_end": free_end,
                }
                if (
                    best is None
                    or record["t"] < best["t"] - 1e-12
                    or (
                        abs(record["t"] - best["t"]) <= 1e-12
                        and record["distance"] < best["distance"]
                    )
                ):
                    best = record
    return best


def _subdivide_path(
    path: list[np.ndarray], segment_index: int, point: np.ndarray
) -> None:
    if segment_index < 0 or segment_index >= len(path) - 1:
        return
    point = np.asarray(point, dtype=np.float64)
    if float(np.linalg.norm(path[segment_index] - point)) <= 1e-9:
        return
    if float(np.linalg.norm(path[segment_index + 1] - point)) <= 1e-9:
        return
    path.insert(segment_index + 1, point.copy())


def _probe_clearance(
    point: np.ndarray, paths: Sequence[Sequence[np.ndarray]], period: float
) -> float:
    best = math.inf
    for points in paths:
        count = len(points)
        if count < 2:
            continue
        for segment_index in range(count - 1):
            c = np.asarray(points[segment_index], dtype=np.float64)
            d = np.asarray(points[segment_index + 1], dtype=np.float64)
            shift = round(
                (float(point[0]) - 0.5 * float(c[0] + d[0])) / period
            ) * period
            distance, _, _ = _point_segment_distance(
                point,
                c + np.array([shift, 0.0]),
                d + np.array([shift, 0.0]),
            )
            best = min(best, distance)
    return best


def _branch_heading(
    origin: np.ndarray,
    heading: float,
    rng: np.random.Generator,
    paths: Sequence[Sequence[np.ndarray]],
    period: float,
    r_clear: float,
    outgoing_heading: float | None = None,
) -> float | None:
    angle = math.radians(float(rng.uniform(30.0, 45.0)))
    signs = (-1.0, 1.0)
    if outgoing_heading is not None:
        turn = (float(outgoing_heading) - float(heading) + math.pi) % (
            2.0 * math.pi
        ) - math.pi
        outward = -1.0 if turn > 0.0 else 1.0
        signs = (outward, -outward)
    options: list[tuple[float, float]] = []
    for sign in signs:
        candidate = float(heading) + sign * angle
        if candidate < _GROWTH_MIN_HEADING - 1e-9:
            continue
        if candidate > _GROWTH_MAX_HEADING + 1e-9:
            continue
        probe = origin + np.array(
            [math.cos(candidate), math.sin(candidate)], dtype=np.float64
        ) * max(3.0 * r_clear, 1.0)
        options.append((_probe_clearance(probe, paths, period), candidate))
    if not options:
        return None
    options.sort(key=lambda item: item[0], reverse=True)
    if len(options) > 1 and abs(options[0][0] - options[1][0]) < 1e-9:
        return options[int(rng.integers(0, 2))][1]
    return options[0][1]


def _densify_growth_polyline(points: np.ndarray, step: float) -> np.ndarray:
    points = np.asarray(points, dtype=np.float64)
    if len(points) < 2:
        return points.copy()
    output: list[np.ndarray] = [points[0].copy()]
    for first, second in zip(points[:-1], points[1:]):
        length = float(np.linalg.norm(second - first))
        count = max(1, int(math.ceil(length / max(step, 1e-9))))
        for index in range(1, count + 1):
            output.append(first + (second - first) * (index / count))
    return np.asarray(output, dtype=np.float64)


def generate_crack_growth_paths(
    params: dict,
    rng: np.random.Generator,
    *,
    subdivide_step: float | None = None,
) -> list[np.ndarray]:
    """Grow a rim-seeded crack network with stop-on-hit T-junctions.

    The graph is built in unrolled ``(u, z)`` space.  Candidate segments are
    tested against every committed segment, including periodic copies, and
    snap to the earliest contact point when the arrival angle is at least 30
    degrees.  The hit segment receives a shared vertex at the contact point.
    """
    period = float(params["period"])
    W = max(float(params["W"]), MIN_SEAM_WIDTH_MM)
    H = max(float(params["H"]), 1e-9)
    severity = float(params.get("S", 0.0))
    wall_z_max = float(params["wall_z_max"])
    z_wall_lo = float(params["z_wall_lo"])
    r_clear = W + GROWTH_CLEARANCE_MM
    # u is arc length, so the angular rule Δθ >= (W + 1.5) / rbar becomes a
    # minimum u separation of W + 1.5 millimetres.
    min_separation_u = W + 1.5
    count = max(int(params["N"]), 1)

    seeds = _poisson_rim_seeds(count, period, min_separation_u, rng)
    z_start = wall_z_max + 0.35 * W
    paths: list[list[np.ndarray]] = []
    tasks: deque[_GrowthTask] = deque()
    junction_records: list[dict] = []
    params["_growth_junctions"] = junction_records

    stub_length = 0.5 * W
    for u in seeds:
        delta = float(rng.uniform(-0.15, 0.15))
        z_limit = max(z_wall_lo, wall_z_max - H * (1.0 + delta))
        heading = _clamp_heading(
            _GROWTH_DOWN + math.radians(float(rng.uniform(-25.0, 25.0)))
        )
        start = np.array([u, z_start], dtype=np.float64)
        # A short rim stub guarantees every one of the N(S) primary trunks
        # survives filtering.  Adjacent seeds are separated by more than
        # R_clear, so the stubs cannot collude near the lip.
        stub = start + np.array([0.0, -stub_length], dtype=np.float64)
        paths.append([start, stub])
        budget = 1.2 * H
        max_steps = max(2, int(math.ceil(budget / (1.5 * W))))
        will_branch = float(rng.random()) < 0.15 * severity
        branch_at = (
            int(rng.integers(1, max_steps))
            if will_branch and max_steps > 1
            else None
        )
        tasks.append(
            _GrowthTask(
                path_id=len(paths) - 1,
                heading=heading,
                traveled=stub_length,
                z_limit=z_limit,
                budget=budget,
                level=0,
                branch_at=branch_at,
                steps=1,
            )
        )

    while tasks:
        task = tasks.popleft()
        path = paths[task.path_id]
        start = path[-1].copy()
        moved = False
        terminal = False

        max_attempts = (
            1 if task.level == 1 and task.steps == 0 else 4
        )
        for attempt in range(max_attempts):
            if attempt == 0 and task.steps == 0:
                candidate_heading = _clamp_heading(task.heading)
            else:
                jitter_deg = 55.0 if attempt == 0 else 70.0
                candidate_heading = _clamp_heading(
                    task.heading
                    + math.radians(
                        float(rng.uniform(-jitter_deg, jitter_deg))
                    )
                )

            remaining = task.budget - task.traveled
            if remaining <= 1e-9:
                terminal = True
                break
            step = min(float(rng.uniform(1.5 * W, 3.0 * W)), remaining)
            if step < 0.35 * W:
                terminal = True
                break

            candidate = start + np.array(
                [math.cos(candidate_heading), math.sin(candidate_heading)],
                dtype=np.float64,
            ) * step

            if candidate[1] < task.z_limit:
                delta_z = float(candidate[1] - start[1])
                if delta_z >= -1e-12:
                    terminal = True
                    break
                t_limit = (task.z_limit - start[1]) / delta_z
                if t_limit <= 1e-9:
                    terminal = True
                    break
                candidate = start + t_limit * (candidate - start)
                step = float(np.linalg.norm(candidate - start))
                if step < 0.2 * W:
                    terminal = True
                    break

            collision = _first_growth_collision(
                paths,
                task.path_id,
                start,
                candidate,
                period=period,
                r_clear=r_clear,
                exempt_path_id=task.exempt_path_id,
                exempt_origin=task.exempt_origin,
                exempt_radius=(
                    1.10 * r_clear / math.sin(math.radians(30.0))
                    if task.exempt_path_id is not None
                    else 0.0
                ),
            )

            if collision is None:
                path.append(candidate)
                task.traveled += step
                task.heading = candidate_heading
                task.steps += 1
                moved = True
                if (
                    candidate[1] <= task.z_limit + 1e-9
                    or task.traveled >= task.budget - 1e-9
                ):
                    terminal = True
                break

            if collision["free_end"]:
                # A free crack end has no segment to subdivide; resampling
                # avoids a head-on T-T pairing that would read as a Y node.
                continue
            if collision["distance"] > 1e-7:
                # A proximity near-miss has no point on the hit segment that
                # lies on the candidate travel vector.  Snapping to the
                # closest point would invent a short oblique connector that
                # can cross another crack, so resample instead.
                continue

            arrival = _acute_angle_deg(
                collision["hit"] - start, collision["tangent"]
            )
            if arrival >= GROWTH_MIN_INCIDENCE_DEG - 1e-9:
                if float(np.linalg.norm(collision["hit"] - start)) > 1e-9:
                    path.append(collision["hit"].copy())
                    task.traveled += float(
                        np.linalg.norm(collision["hit"] - start)
                    )
                junction_records.append(
                    {
                        "point": [
                            float(collision["hit"][0] % period),
                            float(collision["hit"][1]),
                        ],
                        "kind": "T",
                        "path": task.path_id,
                        "parent": int(collision["path_id"]),
                        "angle": float(arrival),
                        "parent_kink_deg": 0.0,
                    }
                )
                _subdivide_path(
                    paths[collision["path_id"]],
                    int(collision["segment_index"]),
                    collision["hit_local"],
                )
                moved = True
                terminal = True
                break
            # Grazing approach: resample the heading up to three more times.

        if (
            moved
            and not terminal
            and task.level == 0
            and not task.branch_spawned
            and task.branch_at is not None
            and task.steps >= task.branch_at
            and len(path) >= 3
        ):
            origin = path[-2].copy()
            incoming = path[-2] - path[-3]
            outgoing = path[-1] - path[-2]
            incoming_heading = math.atan2(
                float(incoming[1]), float(incoming[0])
            )
            outgoing_heading = math.atan2(
                float(outgoing[1]), float(outgoing[0])
            )
            kink = abs(
                (incoming_heading - outgoing_heading + math.pi)
                % (2.0 * math.pi)
                - math.pi
            )
            if (
                kink <= math.radians(39.0)
                and origin[1] < wall_z_max - 0.5 * W
            ):
                branch_heading = _branch_heading(
                    origin,
                    incoming_heading,
                    rng,
                    paths,
                    period,
                    r_clear,
                    outgoing_heading=outgoing_heading,
                )
                if branch_heading is not None:
                    paths.append([origin.copy()])
                    departure = _acute_angle_deg(
                        np.array(
                            [
                                math.cos(branch_heading),
                                math.sin(branch_heading),
                            ]
                        ),
                        np.array(
                            [
                                math.cos(incoming_heading),
                                math.sin(incoming_heading),
                            ]
                        ),
                    )
                    junction_records.append(
                        {
                            "point": [
                                float(origin[0] % period),
                                float(origin[1]),
                            ],
                            "kind": "Y",
                            "path": len(paths) - 1,
                            "parent": task.path_id,
                            "angle": float(departure),
                            "parent_kink_deg": float(math.degrees(kink)),
                        }
                    )
                    tasks.append(
                        _GrowthTask(
                            path_id=len(paths) - 1,
                            heading=branch_heading,
                            traveled=0.0,
                            z_limit=task.z_limit,
                            budget=0.5 * H,
                            level=1,
                            exempt_path_id=task.path_id,
                            exempt_origin=origin.copy(),
                        )
                    )
                    task.branch_spawned = True

        if moved and not terminal:
            tasks.append(task)

    final_step = (
        float(subdivide_step)
        if subdivide_step is not None
        else 0.5 * W
    )
    final_step = max(final_step, 1e-6)
    result: list[np.ndarray] = []
    index_mapping: dict[int, int] = {}
    for old_index, path in enumerate(paths):
        if len(path) < 2:
            continue
        dense = _densify_growth_polyline(np.asarray(path), final_step)
        if len(dense) < 2:
            continue
        dense[:, 0] = np.mod(dense[:, 0], period)
        index_mapping[old_index] = len(result)
        result.append(dense)

    remapped_records: list[dict] = []
    for record in junction_records:
        path_index = index_mapping.get(int(record["path"]))
        if path_index is None:
            continue
        record = dict(record)
        record["path"] = path_index
        if record.get("parent") is not None:
            record["parent"] = index_mapping.get(
                int(record["parent"]), int(record["parent"])
            )
        remapped_records.append(record)
    params["_growth_junctions"] = remapped_records
    return result


# ---------------------------------------------------------------------------
# Growth-graph audit helpers
# ---------------------------------------------------------------------------
def _growth_segments(
    paths: Sequence[Sequence[np.ndarray]], period: float
) -> list[dict]:
    segments: list[dict] = []
    for path_index, path in enumerate(paths):
        points = np.asarray(path, dtype=np.float64)
        for segment_index in range(len(points) - 1):
            a, b = _unwrap_growth_segment(
                points[segment_index], points[segment_index + 1], period
            )
            length = float(np.linalg.norm(b - a))
            if length < 1e-12:
                continue
            segments.append(
                {
                    "path": path_index,
                    "index": segment_index,
                    "a": a,
                    "b": b,
                    "mid": 0.5 * (a + b),
                    "length": length,
                }
            )
    return segments


def _point_segment_distance_periodic(
    point: np.ndarray, segment: dict, period: float
) -> tuple[float, float, np.ndarray]:
    shift = round(
        (float(point[0]) - float(segment["mid"][0])) / period
    ) * period
    return _point_segment_distance(
        point,
        segment["a"] + np.array([shift, 0.0]),
        segment["b"] + np.array([shift, 0.0]),
    )


def _proper_crossing(a, b, c, d, eps: float = 1e-9) -> bool:
    def orient(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    o1 = orient(a, b, c)
    o2 = orient(a, b, d)
    o3 = orient(c, d, a)
    o4 = orient(c, d, b)
    return (
        ((o1 > eps and o2 < -eps) or (o1 < -eps and o2 > eps))
        and ((o3 > eps and o4 < -eps) or (o3 < -eps and o4 > eps))
    )


def _growth_junctions(
    paths: Sequence[Sequence[np.ndarray]],
    segments: Sequence[dict],
    period: float,
    tol: float = 1e-6,
) -> list[dict]:
    records: list[dict] = []
    for path_index, path in enumerate(paths):
        points = np.asarray(path, dtype=np.float64)
        if len(points) < 2:
            continue
        for kind, endpoint_index in (("Y", 0), ("T", len(points) - 1)):
            point = points[endpoint_index]
            candidates: list[dict] = []
            for segment in segments:
                if segment["path"] == path_index:
                    if endpoint_index == 0 and segment["index"] == 0:
                        continue
                    if (
                        endpoint_index == len(points) - 1
                        and segment["index"] == len(points) - 2
                    ):
                        continue
                distance, _, _ = _point_segment_distance_periodic(
                    point, segment, period
                )
                if distance <= tol:
                    candidates.append(segment)
            if not candidates:
                continue

            hit_segment = None
            if kind == "Y":
                # The departure angle is measured against the parent segment
                # that arrives at the branch origin, not against a sibling
                # segment that leaves it in a different direction.
                for segment in candidates:
                    if segment["path"] == path_index:
                        continue
                    if (
                        _periodic_distance(point, segment["b"], period)
                        <= tol * 10.0
                    ):
                        hit_segment = segment
                        break
            if hit_segment is None:
                for segment in candidates:
                    if segment["path"] != path_index:
                        hit_segment = segment
                        break
            if hit_segment is None:
                hit_segment = candidates[0]
            if kind == "T":
                tangent = point - points[-2]
            else:
                tangent = points[1] - point
            hit_tangent = hit_segment["b"] - hit_segment["a"]
            records.append(
                {
                    "point": np.mod(point, period),
                    "kind": kind,
                    "path": path_index,
                    "angle": _acute_angle_deg(tangent, hit_tangent),
                    "segment": hit_segment,
                }
            )

    groups: list[dict] = []
    for record in records:
        group = None
        for candidate in groups:
            if (
                _periodic_distance(record["point"], candidate["point"], period)
                <= tol * 10.0
            ):
                group = candidate
                break
        if group is None:
            groups.append({"point": record["point"].copy(), "records": [record]})
        else:
            group["records"].append(record)

    for group in groups:
        point = group["point"]
        directions: list[np.ndarray] = []
        for segment in segments:
            for first, second in ((segment["a"], segment["b"]),):
                shift = round(
                    (float(point[0]) - float(segment["mid"][0])) / period
                ) * period
                shifted_first = first + np.array([shift, 0.0])
                shifted_second = second + np.array([shift, 0.0])
                if (
                    _periodic_distance(
                        point - np.array([shift, 0.0]), shifted_first, period
                    )
                    <= tol * 10.0
                ):
                    direction = shifted_second - shifted_first
                elif (
                    _periodic_distance(
                        point - np.array([shift, 0.0]), shifted_second, period
                    )
                    <= tol * 10.0
                ):
                    direction = shifted_first - shifted_second
                else:
                    continue
                norm = float(np.linalg.norm(direction))
                if norm > 1e-12:
                    directions.append(direction / norm)
        max_angle = 0.0
        for first_index, first in enumerate(directions):
            for second in directions[first_index + 1 :]:
                cosine = float(np.dot(first, second))
                angle = math.degrees(
                    math.acos(min(max(cosine, -1.0), 1.0))
                )
                max_angle = max(max_angle, angle)
        group["max_angle_deg"] = max_angle
        group["t_like"] = max_angle >= 140.0
        group["incidence_deg"] = [
            record["angle"]
            for record in group["records"]
            if record["kind"] == "T"
        ]
        group["departure_deg"] = [
            record["angle"]
            for record in group["records"]
            if record["kind"] == "Y"
        ]
    return groups


def _growth_junctions_from_metadata(
    paths: Sequence[Sequence[np.ndarray]],
    records: Sequence[dict],
    period: float,
    tol: float = 1e-6,
) -> list[dict]:
    """Group generation-time junction records into audit nodes."""
    valid = [
        record
        for record in records
        if 0 <= int(record["path"]) < len(paths)
        and len(paths[int(record["path"])]) >= 2
    ]
    groups: list[dict] = []
    for record in valid:
        point = np.array(
            [
                float(record["point"][0]) % period,
                float(record["point"][1]),
            ],
            dtype=np.float64,
        )
        group = None
        for candidate in groups:
            if _periodic_distance(point, candidate["point"], period) <= tol * 10.0:
                group = candidate
                break
        if group is None:
            groups.append({"point": point, "records": []})
            group = groups[-1]
        group["records"].append(record)

    for group in groups:
        t_like = False
        incidence: list[float] = []
        departure: list[float] = []
        for record in group["records"]:
            if record["kind"] == "T":
                t_like = True
                incidence.append(float(record["angle"]))
            else:
                if float(record.get("parent_kink_deg", 90.0)) <= 40.0:
                    t_like = True
                departure.append(float(record["angle"]))
        group["t_like"] = t_like
        group["max_angle_deg"] = 180.0 if t_like else 120.0
        group["incidence_deg"] = incidence
        group["departure_deg"] = departure
    return groups


def _tortuosity_values(
    paths: Sequence[Sequence[np.ndarray]],
    junctions: Sequence[dict],
    period: float,
) -> list[float]:
    values: list[float] = []
    for path in paths:
        points = np.asarray(path, dtype=np.float64)
        if len(points) < 2:
            continue
        unwrapped = points.copy()
        unwrapped[:, 0] = _unwrap_u(points[:, 0], period)
        split_indices = {0, len(points) - 1}
        for junction in junctions:
            for index, point in enumerate(points):
                if _periodic_distance(point, junction["point"], period) <= 1e-6:
                    split_indices.add(index)
        ordered = sorted(split_indices)
        for first_index, second_index in zip(ordered, ordered[1:]):
            if second_index - first_index < 1:
                continue
            piece = unwrapped[first_index : second_index + 1]
            if len(piece) < 2:
                continue
            chord = float(np.linalg.norm(piece[-1] - piece[0]))
            if chord < 1e-9:
                continue
            arc = float(
                np.sum(np.linalg.norm(np.diff(piece, axis=0), axis=1))
            )
            values.append(arc / chord)
    return values


def analyze_growth_paths(
    paths: Sequence[Sequence[np.ndarray]], params: dict
) -> dict:
    """Measure planarity, clearance, junction and tortuosity invariants."""
    period = float(params["period"])
    W = float(params["W"])
    r_clear = W + GROWTH_CLEARANCE_MM
    # A 10% numeric margin covers the discrete geodesic offset between a
    # branch and its parent at the nominal 30-degree exemption boundary.
    r_exempt = 1.10 * r_clear / math.sin(math.radians(30.0))
    segments = _growth_segments(paths, period)
    metadata = params.get("_growth_junctions") or []
    if metadata:
        junctions = _growth_junctions_from_metadata(paths, metadata, period)
    else:
        junctions = _growth_junctions(paths, segments, period)
    junction_points = [group["point"] for group in junctions]

    crossings = 0
    clearance_violations = 0
    minimum_clearance = math.inf
    shared_tol = 1e-6

    pair_radius = r_clear + 2.0 * max(
        (segment["length"] for segment in segments), default=0.0
    ) + 1e-6
    pair_indices: set[tuple[int, int]] = set()
    if segments:
        mids = np.asarray([segment["mid"] for segment in segments])
        tiled = np.vstack(
            [
                mids + np.array([shift * period, 0.0])
                for shift in (-1, 0, 1)
            ]
        )
        tree = cKDTree(tiled)
        for index, midpoint in enumerate(mids):
            for neighbour in tree.query_ball_point(midpoint, pair_radius):
                other = int(neighbour) % len(segments)
                if other == index:
                    continue
                pair_indices.add((min(index, other), max(index, other)))

    for first_index, second_index in sorted(pair_indices):
        first = segments[first_index]
        second = segments[second_index]
        if first["path"] == second["path"]:
            mean_step = max(
                0.5 * (first["length"] + second["length"]), 1e-6
            )
            skip_span = 2 + int(math.ceil(r_clear / mean_step))
            if abs(first["index"] - second["index"]) <= skip_span:
                continue
        shift = round(
            (float(first["mid"][0]) - float(second["mid"][0])) / period
        ) * period
        c = second["a"] + np.array([shift, 0.0])
        d = second["b"] + np.array([shift, 0.0])
        distance, t_first, _, contact = _segment_contact(
            first["a"], first["b"], c, d
        )
        first_contact = first["a"] + t_first * (first["b"] - first["a"])
        shared = False
        for point in (first["a"], first["b"]):
            for other in (c, d):
                if _periodic_distance(point, other, period) <= shared_tol:
                    shared = True
                    break
            if shared:
                break
        if shared:
            continue
        if _proper_crossing(first["a"], first["b"], c, d):
            crossings += 1
        exempt = any(
            min(
                _periodic_distance(first_contact, junction_point, period),
                _periodic_distance(contact, junction_point, period),
            )
            <= r_exempt
            for junction_point in junction_points
        )
        if exempt:
            continue
        minimum_clearance = min(minimum_clearance, distance)
        if distance < r_clear - shared_tol:
            clearance_violations += 1

    t_junctions = sum(1 for group in junctions if group["t_like"])
    y_junctions = len(junctions) - t_junctions
    incidence = [
        angle
        for group in junctions
        for angle in group["incidence_deg"]
    ]
    departure = [
        angle
        for group in junctions
        for angle in group["departure_deg"]
    ]
    tortuosity = _tortuosity_values(paths, junctions, period)

    return {
        "paths": len(paths),
        "segments": len(segments),
        "junctions": len(junctions),
        "t_junctions": int(t_junctions),
        "y_junctions": int(y_junctions),
        "t_junction_ratio": (
            float(t_junctions) / float(len(junctions))
            if junctions
            else 1.0
        ),
        "crossings": int(crossings),
        "clearance_violations": int(clearance_violations),
        "min_clearance": (
            float(minimum_clearance)
            if math.isfinite(minimum_clearance)
            else None
        ),
        "min_incidence_deg": float(min(incidence)) if incidence else None,
        "min_departure_deg": float(min(departure)) if departure else None,
        "tortuosity_median": (
            float(np.median(tortuosity)) if tortuosity else 0.0
        ),
        "tortuosity_p05": (
            float(np.percentile(tortuosity, 5)) if tortuosity else 0.0
        ),
        "tortuosity_values": [float(value) for value in tortuosity],
    }


def generate_crack_paths(
    params: dict,
    rng: np.random.Generator,
    *,
    subdivide_step: float | None = None,
    generator: str = "growth",
) -> list[np.ndarray]:
    """Drop-in generator seam: growth (default) or legacy Voronoi."""
    if generator == "growth":
        return generate_crack_growth_paths(
            params, rng, subdivide_step=subdivide_step
        )
    if generator == "voronoi":
        return generate_crack_voronoi_paths(
            params, rng, subdivide_step=subdivide_step
        )
    raise ValueError("generator must be either 'growth' or 'voronoi'")


def generate_crack_voronoi_paths(
    params: dict,
    rng: np.random.Generator,
    *,
    subdivide_step: float | None = None,
) -> list[np.ndarray]:
    """Legacy periodic-Voronoi crack generator in unrolled ``(u, z)`` space."""
    period = float(params["period"])
    z_min = float(params["z_min"])
    z_max = float(params["z_max"])
    N = max(int(params["N"]), 1)
    W = float(params["W"])
    H = float(params["H"])

    half_width = 0.5 * period
    seeds = np.column_stack(
        (
            rng.uniform(0.0, period, size=N),
            rng.uniform(z_min, z_max, size=N),
        )
    )

    # Tile horizontally for periodicity.  The periodic copies create enough
    # neighbours for the central tile; unbounded top/bottom ridges are clipped
    # below instead of being bounded with ghost seeds (which would create a
    # large number of spurious interior ridges).
    tiled = []
    for shift in (-1, 0, 1):
        shifted = seeds.copy()
        shifted[:, 0] += shift * period
        tiled.append(shifted)
    all_seeds = np.vstack(tiled)

    vor = Voronoi(all_seeds)

    # Mean seed spacing drives the noise amplitude.  Draw the noise phases
    # before the per-ridge jitter so the main stream stays in the same order.
    spacing = math.sqrt(max(period * H, 1e-9) / max(N, 1))
    eta = _make_noise(params["rbar"], 0.15 * spacing, rng)
    step = subdivide_step if subdivide_step is not None else 0.5 * W
    z_wall_lo = float(params["z_wall_lo"])
    z_wall_hi = float(params["z_wall_hi"])

    # Build true Voronoi ridge fragments.  Every ridge, finite or unbounded,
    # must have a central-tile seed; otherwise the 3-tile strip end bends the
    # ridge and produces a phantom copy in the central tile.
    segments: list[tuple[np.ndarray, np.ndarray]] = []
    for ridge_index, ridge in enumerate(vor.ridge_vertices):
        seg = _ridge_segment(vor, ridge_index, tuple(ridge))
        if seg is None:
            continue
        p0, p1 = seg
        finite_ridge = ridge[0] >= 0 and ridge[1] >= 0
        seed_pair = vor.points[vor.ridge_points[ridge_index]]
        has_central_seed = bool(
            np.any((seed_pair[:, 0] >= 0.0) & (seed_pair[:, 0] < period))
        )
        if not has_central_seed:
            continue

        # F15b: move each terminal ALONG its ridge by clipping the raw ridge
        # at a per-terminal limit.  The terminal therefore never leaves the
        # true Voronoi line.
        delta_bottom = rng.uniform(-0.1 * H, 0.1 * H)
        delta_top = rng.uniform(-0.1 * H, 0.1 * H)
        limit_lo = z_min + delta_bottom
        limit_hi = z_max + delta_top

        if finite_ridge:
            # A finite ridge can cross the u=0 seam; keeping every periodic
            # copy's central fragment preserves both sides of that junction.
            shifts = (-1, 0, 1)
        else:
            # A ray has one representative: the copy whose finite vertex sits
            # in the central tile.
            reference_u = p0[0]
            shifts = (-int(math.floor(reference_u / period)),)

        for shift in shifts:
            shifted0 = p0.copy()
            shifted1 = p1.copy()
            shifted0[0] += shift * period
            shifted1[0] += shift * period
            if not finite_ridge and not (0.0 <= shifted0[0] < period):
                continue
            clipped = _clip_segment_to_rect(
                shifted0, shifted1, 0.0, period, limit_lo, limit_hi
            )
            if clipped is None:
                continue
            q0, q1 = clipped
            if np.linalg.norm(q1 - q0) < 1e-9:
                continue
            segments.append((q0, q1))

    # Keeping all three shifts can recover two overlapping copies of the same
    # finite ridge in the central tile.  Union collinear overlapping fragments
    # so the duplicate does not become a second crack / apparent T-junction.
    segments = _merge_collinear_segments(segments)

    # Deduplicate central-tile fragments (the periodic tiling creates copies).
    unique: dict[tuple[int, int, int, int], tuple[np.ndarray, np.ndarray]] = {}
    for q0, q1 in segments:
        if (q0[0], q0[1]) > (q1[0], q1[1]):
            q0, q1 = q1, q0
        key = (
            int(round(q0[0] * 1e6)),
            int(round(q0[1] * 1e6)),
            int(round(q1[0] * 1e6)),
            int(round(q1[1] * 1e6)),
        )
        unique.setdefault(key, (q0, q1))
    ordered = [unique[key] for key in sorted(unique)]

    paths: list[np.ndarray] = []
    for q0, q1 in ordered:
        length = float(np.linalg.norm(q1 - q0))
        count = max(1, int(math.ceil(length / max(step, 1e-6))))
        ts = np.linspace(0.0, 1.0, count + 1)
        raw = q0[None, :] + ts[:, None] * (q1 - q0)[None, :]

        # Unwrap u before noise/truncation so a seam crossing cannot create a
        # long false chord through the tile.
        raw[:, 0] = _unwrap_u(np.mod(raw[:, 0], period), period)
        du, dz = eta(raw[:, 0], raw[:, 1])
        perturbed = raw + np.column_stack((du, dz))

        # F15a: truncate where the noisy path leaves the wall range.  Outside
        # parts are discarded; no point is projected onto a horizontal line.
        for piece in _truncate_polyline_z(
            perturbed, z_wall_lo, z_wall_hi, min_length=W
        ):
            piece[:, 0] = np.mod(piece[:, 0], period)
            if len(piece) >= 2:
                paths.append(piece)

    return paths


# ---------------------------------------------------------------------------
# Radially projected paths and watertight cutters
# ---------------------------------------------------------------------------
def project_crack_paths(
    paths: Sequence[np.ndarray],
    manifold: mf.Manifold,
    params: dict,
    mesh: trimesh.Trimesh,
) -> tuple[list[list[dict]], float, float]:
    """Project ``(u, z)`` polylines onto the exterior with radial ray casts.

    Returns ``(projected_paths, in_band_miss_fraction, total_miss_fraction)``.
    Only misses whose ``z`` lies inside the trauma band count towards the
    envelope check; out-of-band misses still split the path but are expected
    when jitter or noise moves a terminal slightly past the band.
    """
    rbar = float(params["rbar"])
    z_min = float(params["z_min"])
    z_max = float(params["z_max"])
    wall_z_max = float(params["wall_z_max"])
    center = np.asarray(mesh.bounding_box.centroid, dtype=np.float64)
    cx, cy = float(center[0]), float(center[1])
    ray_length = 2.0 * float(np.max(mesh.extents)) + 10.0

    projected_paths: list[list[dict]] = []
    total_points = 0
    misses = 0
    band_points = 0
    band_misses = 0
    single_hits = 0
    global_median_wall = float(params.get("median_two_hit_wall", 1.0))

    for path in paths:
        current: list[dict] = []
        for u, z in path:
            total_points += 1
            in_band = z_min <= float(z) <= z_max
            if in_band:
                band_points += 1
            theta = float(u) / rbar
            direction = np.array([math.cos(theta), math.sin(theta), 0.0])
            ray_z = float(z)
            if ray_z > wall_z_max:
                # Rim-bound points deliberately overshoot; cast just below the
                # horizontal rim plane so the cutter pierces the lip without
                # creating coplanar faces on the top surface.
                ray_z = wall_z_max - 0.05
            start = np.array([cx, cy, ray_z], dtype=np.float64)
            end = start + direction * ray_length
            hits = manifold.ray_cast(
                tuple(start.tolist()), tuple(end.tolist())
            )
            if not hits:
                misses += 1
                if in_band:
                    band_misses += 1
                if len(current) >= 1:
                    projected_paths.append(current)
                current = []
                continue

            hits = sorted(hits, key=lambda hit: hit.distance)
            farthest = hits[-1]
            position = start + direction * (float(farthest.distance) * ray_length)
            normal = np.asarray(farthest.normal, dtype=np.float64)
            norm = float(np.linalg.norm(normal))
            if norm < 1e-12:
                normal = direction.copy()
            else:
                normal /= norm
            if float(np.dot(normal, direction)) < 0.0:
                normal = -normal

            if len(hits) >= 2:
                wall = (float(farthest.distance) - float(hits[-2].distance)) * ray_length
                single_hit = False
            else:
                # F13: a one-hit ray has no inner-wall thickness.  Use the
                # path's median two-hit thickness (filled in below), falling
                # back to the global two-hit median.
                wall = global_median_wall
                single_hit = True
                single_hits += 1
            wall = max(float(wall), 0.2)

            current.append(
                {
                    "p": position,
                    "n": normal,
                    "t": wall,
                    "u": float(u),
                    "z": float(z),
                    "single_hit": single_hit,
                }
            )
        if len(current) >= 1:
            projected_paths.append(current)

    # Fill any residual single-hit points from their own path's median
    # two-hit wall thickness, with the global median as a fallback.
    for path in projected_paths:
        two_hit_walls = [p["t"] for p in path if not p["single_hit"]]
        path_median = (
            float(np.median(two_hit_walls))
            if two_hit_walls
            else global_median_wall
        )
        for point in path:
            if point["single_hit"]:
                point["t"] = max(float(path_median), 0.2)

    in_band_miss_fraction = (
        band_misses / band_points if band_points else 0.0
    )
    total_miss_fraction = misses / total_points if total_points else 1.0
    params["single_hit_points"] = single_hits
    params["ray_miss_fraction"] = in_band_miss_fraction
    params["ray_miss_fraction_total"] = total_miss_fraction

    if in_band_miss_fraction > 0.05:
        raise ValueError(
            "The input is not a vessel that the cylindrical parameterisation "
            f"supports: {in_band_miss_fraction:.1%} of in-band crack projection "
            "rays missed the mesh (limit 5%)"
        )

    return projected_paths, in_band_miss_fraction, total_miss_fraction


def _batch_add(parts: Sequence[mf.Manifold]) -> mf.Manifold:
    parts = [part for part in parts if not part.is_empty()]
    if not parts:
        return mf.Manifold()
    return mf.Manifold.batch_boolean(parts, mf.OpType.Add)


def _densify_projected_paths(
    projected_paths: Sequence[Sequence[dict]], step: float
) -> list[list[dict]]:
    """Resample projected path points to a maximum spacing."""
    densified: list[list[dict]] = []
    for path in projected_paths:
        if not path:
            continue
        if len(path) == 1:
            densified.append([dict(point) for point in path])
            continue
        output: list[dict] = [dict(path[0])]
        for first, second in zip(path[:-1], path[1:]):
            p0 = np.asarray(first["p"], dtype=np.float64)
            p1 = np.asarray(second["p"], dtype=np.float64)
            length = float(np.linalg.norm(p1 - p0))
            count = max(1, int(math.ceil(length / max(step, 1e-9))))
            for index in range(1, count + 1):
                fraction = index / count
                p = p0 + (p1 - p0) * fraction
                n = np.asarray(first["n"], dtype=np.float64) * (
                    1.0 - fraction
                ) + np.asarray(second["n"], dtype=np.float64) * fraction
                norm = float(np.linalg.norm(n))
                if norm < 1e-12:
                    n = np.asarray(second["n"], dtype=np.float64)
                else:
                    n = n / norm
                output.append(
                    {
                        "p": p,
                        "n": n,
                        "t": float(first["t"])
                        + (float(second["t"]) - float(first["t"])) * fraction,
                        "u": float(first.get("u", 0.0))
                        + (float(second.get("u", 0.0)) - float(first.get("u", 0.0)))
                        * fraction,
                        "z": float(first.get("z", 0.0))
                        + (float(second.get("z", 0.0)) - float(first.get("z", 0.0)))
                        * fraction,
                        "single_hit": bool(
                            first.get("single_hit", False)
                            and second.get("single_hit", False)
                        ),
                    }
                )
        densified.append(output)
    return densified


def _vein_point_groups(
    projected_paths: Sequence[Sequence[dict]], W: float
) -> list[list[dict]]:
    """Split projected paths into printable runs with a legal vein depth.

    Depth is ``d_i = min(0.75 W, 0.5 t_i, t_i - 0.8 mm)``.  Points whose depth
    falls below ``0.25 mm`` are omitted, which splits the polyline and prevents
    a cutter sphere from becoming tangent to the outer ceramic surface.
    """
    width = float(W)
    radius = 0.5 * width
    groups: list[list[dict]] = []
    step = 0.5 * width
    for path in _densify_projected_paths(projected_paths, step):
        current: list[dict] = []
        for point in path:
            thickness = float(point["t"])
            depth = min(
                0.75 * width,
                0.5 * thickness,
                thickness - GROWTH_CLEARANCE_MM,
            )
            if depth < GROWTH_MIN_DEPTH_MM - 1e-9:
                if current:
                    groups.append(current)
                    current = []
                continue
            center = np.asarray(point["p"], dtype=np.float64) - (
                depth - radius
            ) * np.asarray(point["n"], dtype=np.float64)
            current.append(
                {
                    "p": np.asarray(point["p"], dtype=np.float64),
                    "n": np.asarray(point["n"], dtype=np.float64),
                    "t": thickness,
                    "depth": float(depth),
                    "center": center,
                }
            )
        if current:
            groups.append(current)
    return groups


def _build_vein_cutter(
    projected_paths: Sequence[Sequence[dict]],
    W: float,
    rng: np.random.Generator,
    *,
    per_path: bool,
) -> mf.Manifold:
    """Build inset-sphere vein cutters with one of two deterministic orders.

    Every sphere receives a seeded random rotation before translation.  Shared
    junction points reuse one sphere per unique centre.  Consecutive spheres
    overlap (the path step is at most ``W/2`` and the radius is ``W/2``), so
    they are unioned directly; building convex hulls from already-overlapping
    spheres creates shared faces and kiss edges.  A hull is added only when a
    consecutive-centre gap exceeds the sphere diameter.  Points whose vein
    depth is below 0.25 mm are omitted by ``_vein_point_groups``, splitting the
    cutter into independently manifold runs.
    """
    radius = 0.5 * float(W)
    sphere_cache: dict[tuple[float, float, float], tuple[mf.Manifold, np.ndarray]] = {}
    path_solids: list[mf.Manifold] = []
    global_gap_hulls: list[mf.Manifold] = []

    for group in _vein_point_groups(projected_paths, W):
        spheres: list[tuple[mf.Manifold, np.ndarray, tuple[float, float, float]]] = []
        for point in group:
            center = point["center"]
            key = (
                round(float(center[0]), 6),
                round(float(center[1]), 6),
                round(float(center[2]), 6),
            )
            cached = sphere_cache.get(key)
            if cached is None:
                rotation = rng.uniform(0.0, 360.0, size=3)
                # A sub-0.3% radius jitter prevents exactly tangent sphere
                # surfaces at overlapping junctions, which binary STL would
                # otherwise turn into kiss edges.
                sphere_radius = radius * (
                    1.0 + rng.uniform(-0.002, 0.002)
                )
                sphere = (
                    mf.Manifold.sphere(
                        sphere_radius,
                        circular_segments=RECOMMENDED_CIRCULAR_SEGMENTS,
                    )
                    .rotate(tuple(rotation.tolist()))
                    .translate(tuple(center.tolist()))
                )
                cached = (sphere, center)
                sphere_cache[key] = cached
            spheres.append((cached[0], cached[1], key))

        path_gap_hulls: list[mf.Manifold] = []
        for (first, first_center, _), (second, second_center, _) in zip(
            spheres, spheres[1:]
        ):
            if float(np.linalg.norm(first_center - second_center)) > 2.0 * radius:
                path_gap_hulls.append((first + second).hull())

        if per_path:
            unique = {key: sphere for sphere, _center, key in spheres}
            path_solids.append(
                _batch_add(list(unique.values()) + path_gap_hulls)
            )
        else:
            global_gap_hulls.extend(path_gap_hulls)

    if per_path:
        return _batch_add(path_solids)
    parts = [sphere for sphere, _center in sphere_cache.values()]
    parts.extend(global_gap_hulls)
    return _batch_add(parts)


def build_vein_cutter(
    projected_paths: Sequence[Sequence[dict]],
    W: float,
    rng: np.random.Generator,
) -> mf.Manifold:
    """Public vein-cutter entry point (global unique-sphere union)."""
    return _build_vein_cutter(projected_paths, W, rng, per_path=False)


def build_ribbon_cutter(
    projected_paths: Sequence[Sequence[dict]],
    W: float,
    rng: np.random.Generator,
) -> mf.Manifold:
    """Build through-wall slab hull chains for ribbon mode.

    Slabs share the same depth and surface offset, so neighbouring hulls would
    otherwise have coplanar inner/outer faces.  A seeded small rotation about
    the slab normal plus a sub-millimetre centre/depth jitter de-aligns those
    faces without changing the through-wall intent.
    """
    parts: list[mf.Manifold] = []
    thickness = max(0.2, 0.15 * float(W))
    max_angle_deg = 0.5
    jitter = 1e-3 * float(W)

    for path in projected_paths:
        if len(path) < 2:
            continue
        previous_tangent: np.ndarray | None = None
        previous_binormal: np.ndarray | None = None
        slabs: list[mf.Manifold] = []

        for index, point in enumerate(path):
            p = point["p"]
            n = point["n"]
            if index == 0:
                tangent = path[1]["p"] - p
            elif index == len(path) - 1:
                tangent = p - path[-2]["p"]
            else:
                tangent = path[index + 1]["p"] - path[index - 1]["p"]
            tangent = tangent - n * float(np.dot(tangent, n))
            length = float(np.linalg.norm(tangent))
            if length < 1e-6:
                if previous_tangent is None:
                    continue
                tangent = previous_tangent
                binormal = previous_binormal
            else:
                tangent = tangent / length
                binormal = np.cross(tangent, n)
                binormal_norm = float(np.linalg.norm(binormal))
                if binormal_norm < 1e-6:
                    if previous_binormal is None:
                        continue
                    binormal = previous_binormal
                else:
                    binormal = binormal / binormal_norm
            previous_tangent = tangent
            previous_binormal = binormal

            angle = math.radians(rng.uniform(-max_angle_deg, max_angle_deg))
            cos_angle, sin_angle = math.cos(angle), math.sin(angle)
            slab_tangent = cos_angle * tangent + sin_angle * binormal
            slab_binormal = -sin_angle * tangent + cos_angle * binormal

            depth = float(point["t"]) + 1.0 + rng.uniform(-jitter, jitter)
            center = (
                p
                + n * ((1.0 - depth) / 2.0)
                + slab_tangent * rng.uniform(-jitter, jitter)
            )
            matrix = np.column_stack(
                [slab_tangent, slab_binormal, n, center]
            ).astype(np.float64)
            slab = mf.Manifold.cube(
                (thickness, float(W), depth), center=True
            ).transform(matrix)
            slabs.append(slab)

        if len(slabs) == 1:
            parts.append(slabs[0])
        for first, second in zip(slabs, slabs[1:]):
            parts.append((first + second).hull())

    return _batch_add(parts)


# ---------------------------------------------------------------------------
# CSG, debris swap and export
# ---------------------------------------------------------------------------
def _shares_face_region(target: mf.Manifold, crumb: mf.Manifold) -> bool:
    """True when unioning the crumb merges it into an existing component."""
    if target.is_empty() or crumb.is_empty():
        return False
    before = len(target.decompose())
    after = len((target + crumb).decompose())
    return after < before


def swap_debris(
    ceramic: mf.Manifold,
    gold: mf.Manifold,
    min_volume: float = DEBRIS_VOLUME_MM3,
    stats: dict | None = None,
) -> tuple[mf.Manifold, mf.Manifold]:
    """Move sub-threshold components into the other material, never delete.

    A crumb may only move across materials when it shares a face region with
    the destination, i.e. unioning it reduces the destination's component
    count.  A crumb that only touches at an edge or point is left in its
    original material and counted in ``stats["debris_unmoved"]``; this avoids
    creating new kissing edges.
    """
    ceramic_parts = ceramic.decompose() if not ceramic.is_empty() else []
    gold_parts = gold.decompose() if not gold.is_empty() else []

    ceramic_keep = [part for part in ceramic_parts if part.volume() >= min_volume]
    ceramic_move = [part for part in ceramic_parts if part.volume() < min_volume]
    gold_keep = [part for part in gold_parts if part.volume() >= min_volume]
    gold_move = [part for part in gold_parts if part.volume() < min_volume]

    new_ceramic = _batch_add(ceramic_keep)
    new_gold = _batch_add(gold_keep)
    debris_unmoved = 0

    # A crumb cannot share a face with another component of its *own* material:
    # if it did, decompose() would already have returned them as one component.
    for crumb in gold_move:
        if _shares_face_region(new_ceramic, crumb):
            new_ceramic = new_ceramic + crumb
        else:
            # Leave the isolated crumb in its original material.
            new_gold = new_gold + crumb
            debris_unmoved += 1

    for crumb in ceramic_move:
        if _shares_face_region(new_gold, crumb):
            new_gold = new_gold + crumb
        else:
            new_ceramic = new_ceramic + crumb
            debris_unmoved += 1

    if stats is not None:
        stats["debris_unmoved"] = debris_unmoved
    return new_ceramic, new_gold


def _collapse_edge(
    mesh: trimesh.Trimesh, keep: int, remove: int
) -> trimesh.Trimesh | None:
    """Collapse a single short edge and drop the degenerate triangles."""
    faces = np.asarray(mesh.faces, dtype=np.int64).copy()
    faces[faces == remove] = keep
    keep_mask = (
        (faces[:, 0] != faces[:, 1])
        & (faces[:, 1] != faces[:, 2])
        & (faces[:, 2] != faces[:, 0])
    )
    faces = faces[keep_mask]
    if len(faces) == 0:
        return None
    used = np.unique(faces)
    remap = np.full(len(mesh.vertices), -1, dtype=np.int64)
    remap[used] = np.arange(len(used), dtype=np.int64)
    return trimesh.Trimesh(
        vertices=np.asarray(mesh.vertices[used], dtype=np.float64),
        faces=remap[faces],
        process=False,
    )


def _repair_stl_slivers(
    mesh: trimesh.Trimesh,
    *,
    max_iterations: int = 20,
    length_limit: float = 1e-5,
) -> trimesh.Trimesh:
    """Collapse sub-10-nanometre sliver edges that STL float32 would break.

    Manifold's float64 CSG can leave tiny sliver edges at cut boundaries.  A
    binary STL is float32, and the loader's position merge can turn those
    slivers into edges used by four faces.  Collapsing only edges shorter than
    ``length_limit``, and only when the mesh remains watertight, volume-valid
    and volume-conserving within 1e-6, removes the artifact without deleting
    printable faces.
    """
    if len(mesh.faces) == 0:
        return mesh
    bad = _stl_bad_edge_count(mesh)
    if bad == 0:
        return mesh

    raw_volume = abs(float(mesh.volume))
    current = mesh
    for _ in range(max_iterations):
        edges = current.edges_unique
        if len(edges) == 0:
            break
        lengths = np.linalg.norm(
            current.vertices[edges[:, 0]] - current.vertices[edges[:, 1]],
            axis=1,
        )
        order = np.argsort(lengths, kind="stable")
        accepted = None
        for index in order:
            if float(lengths[index]) > length_limit:
                break
            keep, remove = (int(value) for value in edges[index])
            candidate = _collapse_edge(current, keep, remove)
            if candidate is None:
                continue
            if not candidate.is_watertight or not candidate.is_volume:
                continue
            if raw_volume > 1e-9 and abs(
                abs(float(candidate.volume)) - raw_volume
            ) > 1e-6 * raw_volume:
                continue
            candidate_bad = _stl_bad_edge_count(candidate)
            if candidate_bad < bad:
                accepted = (candidate, candidate_bad)
                break
        if accepted is None:
            break
        current, bad = accepted
        if bad == 0:
            break
    return current


def _export_trimesh(manifold: mf.Manifold) -> trimesh.Trimesh:
    """Convert and repair tiny CSG slivers before STL/3MF export."""
    return _repair_stl_slivers(manifold_to_trimesh(manifold))


def _write_stl(
    manifold: mf.Manifold,
    path: str | Path,
    mesh: trimesh.Trimesh | None = None,
) -> None:
    mesh = mesh if mesh is not None else _export_trimesh(manifold)
    data = trimesh.exchange.stl.export_stl(mesh)
    Path(path).write_bytes(data)


def export_kintsugi_stl(
    ceramic: mf.Manifold,
    gold: mf.Manifold | None,
    ceramic_path: str | Path,
    gold_path: str | Path,
    ceramic_mesh: trimesh.Trimesh | None = None,
    gold_mesh: trimesh.Trimesh | None = None,
) -> dict:
    """Write the ceramic STL and, when present, the complementary gold STL."""
    ceramic_path = Path(ceramic_path)
    gold_path = Path(gold_path)
    _write_stl(ceramic, ceramic_path, ceramic_mesh)

    if gold is None:
        # Make sure a seam from an earlier run cannot be paired with this body.
        gold_path.unlink(missing_ok=True)
        return {"ceramic_path": ceramic_path, "gold_path": None}

    _write_stl(gold, gold_path, gold_mesh)
    return {"ceramic_path": ceramic_path, "gold_path": gold_path}


def _mesh_xml(parent: ET.Element, mesh: trimesh.Trimesh) -> None:
    mesh_element = ET.SubElement(parent, f"{{{CORE_NS}}}mesh")
    vertices_element = ET.SubElement(mesh_element, f"{{{CORE_NS}}}vertices")
    for x, y, z in np.asarray(mesh.vertices, dtype=np.float64):
        ET.SubElement(
            vertices_element,
            f"{{{CORE_NS}}}vertex",
            {"x": f"{x:.9g}", "y": f"{y:.9g}", "z": f"{z:.9g}"},
        )
    triangles_element = ET.SubElement(mesh_element, f"{{{CORE_NS}}}triangles")
    for a, b, c in np.asarray(mesh.faces, dtype=np.int64):
        ET.SubElement(
            triangles_element,
            f"{{{CORE_NS}}}triangle",
            {"v1": str(int(a)), "v2": str(int(b)), "v3": str(int(c))},
        )


def export_kintsugi_3mf(
    ceramic: mf.Manifold,
    gold: mf.Manifold | None,
    path: str | Path,
    ceramic_mesh: trimesh.Trimesh | None = None,
    gold_mesh: trimesh.Trimesh | None = None,
) -> Path:
    """Write a hand-authored 3MF with one build item and component parts."""
    path = Path(path)
    root = ET.Element(
        f"{{{CORE_NS}}}model",
        {"unit": "millimeter", "xml:lang": "en-US"},
    )
    ET.SubElement(root, f"{{{CORE_NS}}}metadata", {"name": "Title"}).text = (
        "Kintsugi Assembly"
    )
    resources = ET.SubElement(root, f"{{{CORE_NS}}}resources")

    parent = ET.SubElement(resources, f"{{{CORE_NS}}}object", {"id": "1", "type": "model"})
    components = ET.SubElement(parent, f"{{{CORE_NS}}}components")

    ceramic_obj = ET.SubElement(
        resources,
        f"{{{CORE_NS}}}object",
        {"id": "2", "type": "model", "name": "CeramicBody"},
    )
    _mesh_xml(
        ceramic_obj,
        ceramic_mesh if ceramic_mesh is not None else _export_trimesh(ceramic),
    )
    ET.SubElement(components, f"{{{CORE_NS}}}component", {"objectid": "2"})

    if gold is not None:
        gold_obj = ET.SubElement(
            resources,
            f"{{{CORE_NS}}}object",
            {"id": "3", "type": "model", "name": "GoldSeams"},
        )
        _mesh_xml(
            gold_obj,
            gold_mesh if gold_mesh is not None else _export_trimesh(gold),
        )
        ET.SubElement(components, f"{{{CORE_NS}}}component", {"objectid": "3"})

    build = ET.SubElement(root, f"{{{CORE_NS}}}build")
    ET.SubElement(build, f"{{{CORE_NS}}}item", {"objectid": "1"})

    model_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)

    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<Types xmlns="{CT_NS}">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
        "</Types>"
    )
    relationships = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<Relationships xmlns="{REL_NS}">'
        '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
        'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
        "</Relationships>"
    )

    def _write(archive: zipfile.ZipFile, name: str, data: bytes) -> None:
        info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o600 << 16
        archive.writestr(info, data)

    with zipfile.ZipFile(path, "w") as archive:
        _write(archive, "[Content_Types].xml", content_types.encode("utf-8"))
        _write(archive, "_rels/.rels", relationships.encode("utf-8"))
        _write(archive, "3D/3dmodel.model", model_bytes)

    return path


# ---------------------------------------------------------------------------
# Top-level generation
# ---------------------------------------------------------------------------
def generate_kintsugi_mesh(
    input_path: str | Path,
    output_dir: str | Path,
    R: float,
    mode: str = "ribbon",
    seed: int = 42,
    seam_width: float | None = None,
    output_3mf_path: str | Path | None = None,
    generator: str = "growth",
) -> dict:
    """Fracture a vessel mesh into a ceramic body and complementary gold seams.

    Returns a result dictionary with paths, volumes, triangle counts, the
    resolved parameter table and stage timings.
    """
    started = time.perf_counter()
    timings: dict[str, float] = {}

    R = float(R)
    severity = compute_severity(R)
    if mode not in ("vein", "ribbon"):
        raise ValueError("mode must be either 'vein' or 'ribbon'")
    if generator not in ("growth", "voronoi"):
        raise ValueError("generator must be either 'growth' or 'voronoi'")
    if seam_width is not None and float(seam_width) < MIN_SEAM_WIDTH_MM:
        raise ValueError(
            f"seam_width must be at least {MIN_SEAM_WIDTH_MM} mm, "
            f"got {seam_width}"
        )

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ceramic_path = output_dir / "ceramic_body.stl"
    gold_path = output_dir / "gold_seams.stl"
    three_mf_path = Path(output_3mf_path) if output_3mf_path is not None else None

    validate_started = time.perf_counter()
    validation = validate_and_load_mesh(input_path, severity)
    mesh, manifold = validation
    params = compute_parameters(
        severity,
        mesh,
        manifold=manifold,
        seam_width=seam_width,
        probe=validation.probe,
    )
    params["mode"] = mode
    params["generator"] = generator
    params["seed"] = int(seed)
    timings["validate"] = time.perf_counter() - validate_started

    input_volume = float(manifold.volume())

    if severity == 0.0:
        # Wealthy pass-through: the validated input is the ceramic body.
        export_started = time.perf_counter()
        ceramic_trimesh = mesh
        ceramic_bytes = trimesh.exchange.stl.export_stl(ceramic_trimesh)
        ceramic_path.write_bytes(ceramic_bytes)
        gold_path.unlink(missing_ok=True)
        if three_mf_path is not None:
            three_mf_path.parent.mkdir(parents=True, exist_ok=True)
            export_kintsugi_3mf(manifold, None, three_mf_path)
        timings["export"] = time.perf_counter() - export_started
        timings["total"] = time.perf_counter() - started
        return {
            "ceramic_path": str(ceramic_path),
            "gold_path": None,
            "three_mf_path": str(three_mf_path) if three_mf_path else None,
            "volumes": {
                "input": input_volume,
                "ceramic": float(ceramic_trimesh.volume),
                "gold": 0.0,
                "pre_swap_ceramic": float(ceramic_trimesh.volume),
                "pre_swap_gold": 0.0,
            },
            "triangle_counts": {
                "ceramic": int(len(ceramic_trimesh.faces)),
                "gold": 0,
            },
            "num_cracks": 0,
            "cutter_attempts": 0,
            "cutter_variants": 0,
            "guard_evaluations": 0,
            "debris_unmoved": 0,
            "parameters": params,
            "timings": timings,
        }

    rng = np.random.default_rng(int(seed))

    graph_started = time.perf_counter()
    paths = generate_crack_paths(params, rng, generator=generator)
    timings["crack_graph"] = time.perf_counter() - graph_started

    projection_started = time.perf_counter()
    projected_paths, miss_fraction, total_miss_fraction = project_crack_paths(
        paths, manifold, params, mesh
    )
    timings["projection"] = time.perf_counter() - projection_started
    params["ray_miss_fraction"] = miss_fraction
    params["ray_miss_fraction_total"] = total_miss_fraction

    cutter_elapsed = 0.0
    csg_elapsed = 0.0
    swap_elapsed = 0.0
    cutter_attempts = 0
    cutter_variants_used = 0
    guard_evaluations = 0
    debris_stats: dict[str, int] = {}
    last_bad = (0, 0)
    ceramic_before = gold_before = None
    ceramic = gold = None
    ceramic_export_mesh = gold_export_mesh = None

    # F1 guard: the input mesh is never perturbed.  Only the cutter is
    # rebuilt, with a different deterministic sub-seed, while both booleans
    # continue to use the same cutter so complementarity is preserved.  For
    # vein mode, two deterministic union orders are tried within each attempt
    # before spending a new sub-seed; this avoids random retries at junctions.
    for attempt in range(3):
        cutter_attempts = attempt + 1
        cutter_started = time.perf_counter()
        if mode == "vein":
            cutter_rng = np.random.default_rng([int(seed), 0xC07, attempt])
            state = cutter_rng.bit_generator.state
            cutters = [
                _build_vein_cutter(
                    projected_paths, params["W"], cutter_rng, per_path=False
                )
            ]
            cutter_rng.bit_generator.state = state
            cutters.append(
                _build_vein_cutter(
                    projected_paths, params["W"], cutter_rng, per_path=True
                )
            )
        else:
            cutter_rng = np.random.default_rng([int(seed), 0xC07, attempt])
            cutters = [
                build_ribbon_cutter(projected_paths, params["W"], cutter_rng)
            ]
        cutter_elapsed += time.perf_counter() - cutter_started

        attempt_clean = False
        for variant_index, cutter in enumerate(cutters, start=1):
            csg_started = time.perf_counter()
            if cutter.is_empty():
                ceramic_before = manifold
                gold_before = mf.Manifold()
            else:
                ceramic_before = manifold - cutter
                gold_before = manifold ^ cutter
            csg_elapsed += time.perf_counter() - csg_started

            swap_started = time.perf_counter()
            debris_stats = {}
            ceramic, gold = swap_debris(
                ceramic_before, gold_before, stats=debris_stats
            )
            swap_elapsed += time.perf_counter() - swap_started

            guard_evaluations += 1
            ceramic_export_mesh = _export_trimesh(ceramic)
            gold_export_mesh = _export_trimesh(gold)
            last_bad = (
                _stl_bad_edge_count(ceramic_export_mesh),
                _stl_bad_edge_count(gold_export_mesh),
            )
            if last_bad == (0, 0):
                cutter_variants_used = variant_index
                attempt_clean = True
                break
        if attempt_clean:
            break
    else:
        raise RuntimeError(
            "Round-trip guard failed after "
            f"{cutter_attempts} cutter attempts: ceramic has "
            f"{last_bad[0]} bad edges, gold has {last_bad[1]} bad edges; "
            "no output files were written"
        )

    timings["cutter"] = cutter_elapsed
    timings["csg"] = csg_elapsed
    timings["debris_swap"] = swap_elapsed
    params["cutter_attempts"] = cutter_attempts
    params["cutter_variants"] = cutter_variants_used
    params["guard_evaluations"] = guard_evaluations
    params["debris_unmoved"] = debris_stats.get("debris_unmoved", 0)

    export_started = time.perf_counter()
    export_kintsugi_stl(
        ceramic,
        gold,
        ceramic_path,
        gold_path,
        ceramic_mesh=ceramic_export_mesh,
        gold_mesh=gold_export_mesh,
    )
    if three_mf_path is not None:
        three_mf_path.parent.mkdir(parents=True, exist_ok=True)
        export_kintsugi_3mf(
            ceramic,
            gold,
            three_mf_path,
            ceramic_mesh=ceramic_export_mesh,
            gold_mesh=gold_export_mesh,
        )
    timings["export"] = time.perf_counter() - export_started
    timings["total"] = time.perf_counter() - started

    ceramic_trimesh = ceramic_export_mesh
    gold_trimesh = gold_export_mesh
    params.pop("_growth_junctions", None)

    return {
        "ceramic_path": str(ceramic_path),
        "gold_path": str(gold_path),
        "three_mf_path": str(three_mf_path) if three_mf_path else None,
        "volumes": {
            "input": input_volume,
            "ceramic": float(ceramic.volume()),
            "gold": float(gold.volume()),
            "pre_swap_ceramic": float(ceramic_before.volume()),
            "pre_swap_gold": float(gold_before.volume()),
        },
        "triangle_counts": {
            "ceramic": int(len(ceramic_trimesh.faces)),
            "gold": int(len(gold_trimesh.faces)),
        },
        "num_cracks": int(len(projected_paths)),
        "cutter_attempts": int(params.get("cutter_attempts", 0)),
        "cutter_variants": int(params.get("cutter_variants", 0)),
        "guard_evaluations": int(params.get("guard_evaluations", 0)),
        "debris_unmoved": int(params.get("debris_unmoved", 0)),
        "parameters": params,
        "timings": timings,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fracture a vessel mesh into a Kintsugi ceramic/gold assembly."
    )
    parser.add_argument("input", type=Path, help="Input .stl or .obj vessel mesh")
    parser.add_argument("-o", "--output-dir", type=Path, default=Path("output"))
    parser.add_argument(
        "-R",
        "--income-ratio",
        type=float,
        default=0.5,
        help="Income ratio R; R >= 1.0 yields a pristine body",
    )
    parser.add_argument("--mode", choices=("vein", "ribbon"), default="ribbon")
    parser.add_argument(
        "--generator",
        choices=("growth", "voronoi"),
        default="growth",
        help="Crack generator (growth is the default; voronoi is legacy)",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--seam-width", type=float, default=None)
    parser.add_argument(
        "--3mf",
        dest="three_mf",
        action="store_true",
        help="Also write kintsugi_assembly.3mf",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    three_mf = (
        args.output_dir / "kintsugi_assembly.3mf" if args.three_mf else None
    )
    result = generate_kintsugi_mesh(
        args.input,
        args.output_dir,
        R=args.income_ratio,
        mode=args.mode,
        seed=args.seed,
        seam_width=args.seam_width,
        output_3mf_path=three_mf,
        generator=args.generator,
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Ceramic: {result['ceramic_path']}")
        print(f"Gold:    {result['gold_path'] or '(pristine, no gold seam)'}")
        if result["three_mf_path"]:
            print(f"3MF:     {result['three_mf_path']}")
        print(
            "Volumes: "
            f"input={result['volumes']['input']:.3f} mm^3, "
            f"ceramic={result['volumes']['ceramic']:.3f} mm^3, "
            f"gold={result['volumes']['gold']:.3f} mm^3"
        )
        print(f"Cracks:  {result['num_cracks']}")
        print(f"Total:   {result['timings']['total']:.2f} s")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
