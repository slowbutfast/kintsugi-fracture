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


# ---------------------------------------------------------------------------
# 3MF package builder (used by tests.test_mesh_formats and tests.test_web_api)
# ---------------------------------------------------------------------------
import zipfile
import xml.etree.ElementTree as ET

CORE_NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
PROD_NS = "http://schemas.microsoft.com/3dmanufacturing/production/2015/06"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
MODEL_REL = "http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"

ET.register_namespace("", CORE_NS)
ET.register_namespace("p", PROD_NS)


def transform_string(matrix) -> str:
    """Serialise a 4x4 row-vector matrix (``p' = [x y z 1] @ M``) as 3MF's 12 values."""
    matrix = np.asarray(matrix, dtype=np.float64)
    return " ".join(repr(float(value)) for value in matrix[:, :3].reshape(-1))


def translation_matrix(x: float, y: float, z: float) -> np.ndarray:
    matrix = np.eye(4)
    matrix[3, :3] = (x, y, z)
    return matrix


def rotation_z_matrix(degrees: float) -> np.ndarray:
    """Row-vector rotation about +Z (counter-clockwise looking down -Z)."""
    angle = np.radians(degrees)
    cos, sin = np.cos(angle), np.sin(angle)
    matrix = np.eye(4)
    matrix[0, :2] = (cos, sin)
    matrix[1, :2] = (-sin, cos)
    return matrix


def apply_row_matrix(vertices, matrix) -> np.ndarray:
    vertices = np.asarray(vertices, dtype=np.float64)
    homogeneous = np.hstack([vertices, np.ones((len(vertices), 1))])
    return (homogeneous @ np.asarray(matrix, dtype=np.float64))[:, :3]


def mesh_object(object_id, mesh, *, name=None, type="model") -> dict:
    return {"id": str(object_id), "type": type, "name": name, "mesh": mesh}


def component_object(object_id, components, *, name=None, type="model") -> dict:
    """``components``: dicts with ``objectid`` and optional ``path``/``transform`` (4x4)."""
    return {
        "id": str(object_id),
        "type": type,
        "name": name,
        "components": components,
    }


def _object_xml(parent, spec: dict) -> None:
    attrs = {"id": spec["id"]}
    if spec.get("type") is not None:
        attrs["type"] = spec["type"]
    if spec.get("name"):
        attrs["name"] = spec["name"]
    element = ET.SubElement(parent, f"{{{CORE_NS}}}object", attrs)
    if "mesh" in spec:
        mesh_el = ET.SubElement(element, f"{{{CORE_NS}}}mesh")
        vertices_el = ET.SubElement(mesh_el, f"{{{CORE_NS}}}vertices")
        for x, y, z in np.asarray(spec["mesh"].vertices, dtype=np.float64):
            ET.SubElement(
                vertices_el,
                f"{{{CORE_NS}}}vertex",
                {"x": repr(float(x)), "y": repr(float(y)), "z": repr(float(z))},
            )
        triangles_el = ET.SubElement(mesh_el, f"{{{CORE_NS}}}triangles")
        for a, b, c in np.asarray(spec["mesh"].faces):
            ET.SubElement(
                triangles_el,
                f"{{{CORE_NS}}}triangle",
                {"v1": str(int(a)), "v2": str(int(b)), "v3": str(int(c))},
            )
    else:
        components_el = ET.SubElement(element, f"{{{CORE_NS}}}components")
        for comp in spec["components"]:
            comp_attrs = {"objectid": str(comp["objectid"])}
            if comp.get("path"):
                comp_attrs[f"{{{PROD_NS}}}path"] = comp["path"]
            if comp.get("transform") is not None:
                comp_attrs["transform"] = transform_string(comp["transform"])
            ET.SubElement(components_el, f"{{{CORE_NS}}}component", comp_attrs)


def _model_bytes(objects, *, unit, build_items=None) -> bytes:
    root_attrs = {"xml:lang": "en-US"}
    if unit:
        root_attrs["unit"] = unit
    root = ET.Element(f"{{{CORE_NS}}}model", root_attrs)
    resources = ET.SubElement(root, f"{{{CORE_NS}}}resources")
    for spec in objects:
        _object_xml(resources, spec)
    build = ET.SubElement(root, f"{{{CORE_NS}}}build")
    for item in build_items or []:
        item_attrs = {"objectid": str(item["objectid"])}
        if item.get("transform") is not None:
            item_attrs["transform"] = transform_string(item["transform"])
        ET.SubElement(build, f"{{{CORE_NS}}}item", item_attrs)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def build_3mf(
    path,
    *,
    objects,
    build_items,
    unit="millimeter",
    extra_parts=None,
    root_part="3D/3dmodel.model",
    with_rels=True,
    rels_target=None,
    extra_files=None,
    compression=zipfile.ZIP_DEFLATED,
) -> None:
    """Write a 3MF package.

    ``objects`` live in the root part.  ``extra_parts`` maps part names (e.g.
    ``3D/Objects/o.model``) to object lists.  ``extra_files`` maps archive
    names to raw bytes and is applied last, so it can add vendor config parts
    or override a generated part with hostile content.
    """
    files: dict[str, bytes] = {
        "[Content_Types].xml": (
            '<?xml version="1.0" encoding="UTF-8"?>'
            f'<Types xmlns="{CT_NS}">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
            "</Types>"
        ).encode("utf-8")
    }
    if with_rels:
        target = rels_target or f"/{root_part}"
        files["_rels/.rels"] = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            f'<Relationships xmlns="{REL_NS}">'
            f'<Relationship Target="{target}" Id="rel0" Type="{MODEL_REL}"/>'
            "</Relationships>"
        ).encode("utf-8")
    files[root_part] = _model_bytes(objects, unit=unit, build_items=build_items)
    for name, part_objects in (extra_parts or {}).items():
        files[name] = _model_bytes(part_objects, unit=unit)
    files.update(extra_files or {})
    with zipfile.ZipFile(path, "w", compression) as archive:
        for name, data in files.items():
            archive.writestr(name, data)


def write_bowl_3mf(path, *, unit="millimeter", scale=1.0) -> trimesh.Trimesh:
    """Single-object, single-item core 3MF of the fixture bowl; returns the source mesh."""
    mesh = manifold_to_trimesh(bowl_manifold())
    if scale != 1.0:
        mesh = mesh.copy()
        mesh.apply_scale(scale)
    build_3mf(
        path,
        objects=[mesh_object(1, mesh, name="Bowl")],
        build_items=[{"objectid": 1}],
        unit=unit,
    )
    return mesh
