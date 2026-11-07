"""Bundled sample models used by the web GUI and sample generator."""

from __future__ import annotations

from pathlib import Path

import manifold3d as mf
import numpy as np
import trimesh


def _manifold_to_trimesh(manifold: mf.Manifold) -> trimesh.Trimesh:
    mesh = manifold.to_mesh64()
    return trimesh.Trimesh(
        vertices=np.array(mesh.vert_properties[:, :3], dtype=np.float64, copy=True),
        faces=np.array(mesh.tri_verts, dtype=np.int64, copy=True),
        process=False,
    )


def tea_bowl(circular_segments: int = 96) -> mf.Manifold:
    """90 x 90 x 60 mm bowl with a 3 mm wall and solid base."""
    profile = [
        (0.0, 0.0),
        (45.0, 0.0),
        (45.0, 60.0),
        (42.0, 60.0),
        (42.0, 3.0),
        (0.0, 3.0),
    ]
    return mf.Manifold.revolve(
        mf.CrossSection([profile]), circular_segments=circular_segments
    )


def small_vase(circular_segments: int = 96) -> mf.Manifold:
    """Tapered 50 x 50 x 70 mm vase with a 2.5 mm wall."""
    profile = [
        (0.0, 0.0),
        (25.0, 0.0),
        (20.0, 70.0),
        (17.5, 70.0),
        (22.5, 3.0),
        (0.0, 3.0),
    ]
    return mf.Manifold.revolve(
        mf.CrossSection([profile]), circular_segments=circular_segments
    )


def thin_cylinder(circular_segments: int = 96) -> mf.Manifold:
    """Cylinder with a 1.2 mm wall tapering to 0.7 mm at the rim.

    The 50 x 50 x 70 mm vessel deliberately exercises the sub-0.25 mm vein
    cutter omission band: the upper wall cannot hold the 0.8 mm backing rule.
    """
    profile = [
        (0.0, 0.0),
        (25.0, 0.0),
        (25.0, 70.0),
        (24.3, 70.0),
        (23.8, 3.0),
        (0.0, 3.0),
    ]
    return mf.Manifold.revolve(
        mf.CrossSection([profile]), circular_segments=circular_segments
    )


def create_thin_cylinder_preset(circular_segments: int = 96) -> mf.Manifold:
    """Compatibility alias for the synthetic thin-wall preset builder."""
    return thin_cylinder(circular_segments)


def benchy_style_boat() -> mf.Manifold:
    """A deliberately non-vessel boat/cabin shape used to demonstrate rejection."""
    hull = mf.Manifold.hull_points(
        [
            (-32.0, -14.0, 0.0),
            (32.0, -14.0, 0.0),
            (32.0, 14.0, 0.0),
            (-32.0, 14.0, 0.0),
            (-24.0, -10.0, 18.0),
            (24.0, -10.0, 18.0),
            (24.0, 10.0, 18.0),
            (-24.0, 10.0, 18.0),
        ]
    )
    cabin = mf.Manifold.cube((22.0, 18.0, 22.0), center=True).translate((4.0, 0.0, 29.0))
    chimney = mf.Manifold.cylinder(
        12.0, 3.0, 3.0, circular_segments=24
    ).translate((-14.0, 0.0, 36.0))
    return mf.Manifold.batch_boolean([hull, cabin, chimney], mf.OpType.Add)


PRESETS = [
    {
        "id": "tea_bowl",
        "name": "Japanese Tea Bowl",
        "description": "90 mm hand-thrown tea bowl with a 3 mm wall.",
        "filename": "tea_bowl.stl",
    },
    {
        "id": "benchy",
        "name": "3D Benchy",
        "description": "Classic calibration boat (non-vessel; rejected by fracture).",
        "filename": "benchy.stl",
    },
    {
        "id": "vase",
        "name": "Small Vase",
        "description": "Tapered 70 mm vase with a 2.5 mm wall.",
        "filename": "vase.stl",
    },
    {
        "id": "thin_cylinder",
        "name": "Thin-Wall Cylinder",
        "description": "70 mm cylinder with a 1.2 mm wall tapering to 0.7 mm.",
        "filename": "thin_cylinder.stl",
    },
]


_BUILDERS = {
    "tea_bowl": tea_bowl,
    "benchy": benchy_style_boat,
    "vase": small_vase,
    "thin_cylinder": thin_cylinder,
}


def ensure_presets(directory: str | Path) -> list[dict]:
    """Create any missing bundled preset STL files and return metadata."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for preset in PRESETS:
        path = directory / preset["filename"]
        if not path.exists():
            mesh = _manifold_to_trimesh(_BUILDERS[preset["id"]]())
            path.write_bytes(trimesh.exchange.stl.export_stl(mesh))
    return [
        {
            **preset,
            "mesh_url": f"/presets/{preset['filename']}",
        }
        for preset in PRESETS
    ]


def preset_path(preset_id: str, directory: str | Path) -> Path:
    ensure_presets(directory)
    for preset in PRESETS:
        if preset["id"] == preset_id:
            return Path(directory) / preset["filename"]
    raise KeyError(preset_id)
