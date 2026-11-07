"""Shared test fixtures: a parametric tea bowl and deliberately invalid inputs."""

from __future__ import annotations

import numpy as np
import trimesh
import manifold3d as mf


def manifold_to_trimesh(manifold: mf.Manifold) -> trimesh.Trimesh:
    """Convert a Manifold to a Trimesh without any repair."""
    mesh = manifold.to_mesh64()
    vertices = np.array(mesh.vert_properties[:, :3], dtype=np.float64, copy=True)
    faces = np.array(mesh.tri_verts, dtype=np.int64, copy=True)
    return trimesh.Trimesh(vertices=vertices, faces=faces, process=False)


def bowl_manifold(circular_segments: int = 96) -> mf.Manifold:
    """A 90 x 90 x 60 mm tea bowl with a 3 mm wall and 3 mm solid base."""
    profile = [
        (0.0, 0.0),
        (45.0, 0.0),
        (45.0, 60.0),
        (42.0, 60.0),
        (42.0, 3.0),
        (0.0, 3.0),
    ]
    cross_section = mf.CrossSection([profile])
    return mf.Manifold.revolve(cross_section, circular_segments=circular_segments)


def write_stl(mesh: trimesh.Trimesh, path) -> None:
    data = trimesh.exchange.stl.export_stl(mesh)
    with open(path, "wb") as handle:
        handle.write(data)


def write_bowl(path) -> None:
    write_stl(manifold_to_trimesh(bowl_manifold()), path)


def write_open_bowl(path) -> None:
    mesh = manifold_to_trimesh(bowl_manifold())
    open_mesh = trimesh.Trimesh(
        vertices=mesh.vertices.copy(),
        faces=mesh.faces[:-1].copy(),
        process=False,
    )
    write_stl(open_mesh, path)


def write_metre_bowl(path) -> None:
    mesh = manifold_to_trimesh(bowl_manifold())
    metre = mesh.copy()
    metre.apply_scale(0.001)
    write_stl(metre, path)


def write_non_vessel(path) -> None:
    """Two disjoint 30 x 20 x 40 mm boxes separated by a 20 mm gap."""
    left = mf.Manifold.cube((30.0, 20.0, 40.0), center=True).translate((-25.0, 0.0, 20.0))
    right = mf.Manifold.cube((30.0, 20.0, 40.0), center=True).translate((25.0, 0.0, 20.0))
    combined = mf.Manifold.batch_boolean([left, right], mf.OpType.Add)
    write_stl(manifold_to_trimesh(combined), path)


def write_solid_cylinder(path) -> None:
    """A closed 60 x 60 x 60 mm solid with no wall (one radial hit)."""
    cylinder = mf.Manifold.cylinder(
        60.0, 30.0, 30.0, circular_segments=64
    ).translate((0.0, 0.0, 0.0))
    write_stl(manifold_to_trimesh(cylinder), path)
