"""Dependency-free 3MF package reader.

``load_3mf`` turns a ``.3mf`` file into one flattened millimetre
``trimesh.Trimesh`` that the normal input envelope (``kintsugi.validate_and_load_mesh``)
then checks like any STL.  It uses only ``zipfile`` and ``xml.etree``:
trimesh's own 3MF loader imports ``networkx`` and ``lxml``, which are not
declared dependencies and are absent on Vercel.

Supported: one build item, mesh objects, nested components with transforms,
Production-extension ``p:path`` references to other model parts, and the
``unit`` attribute.  Materials, colours, textures and metadata are ignored.
Anything the engine cannot represent faithfully (several build items,
support/other object types, slicer modifier or negative volumes, our own
exported assembly) is rejected with a specific ``ValueError``.

The package is untrusted input: sizes are capped, part names are normalised
and may not contain ``..``, and any XML part with a ``<!DOCTYPE`` is refused
before parsing (which removes entity-expansion attacks without needing
``defusedxml``).
"""

from __future__ import annotations

import lzma
import math
import posixpath
import xml.etree.ElementTree as ET
import zipfile
import zlib
from pathlib import Path

import numpy as np
import trimesh

CORE_NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
PROD_NS = "http://schemas.microsoft.com/3dmanufacturing/production/2015/06"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

DEFAULT_ROOT_PART = "3D/3dmodel.model"
RELS_PART = "_rels/.rels"

#: Millimetres per model unit, from the 3MF Core Specification.
UNIT_FACTORS = {
    "micron": 0.001,
    "millimeter": 1.0,
    "centimeter": 10.0,
    "inch": 25.4,
    "foot": 304.8,
    "meter": 1000.0,
}

MAX_UNCOMPRESSED_BYTES = 512 * 1024 * 1024
MAX_CONFIG_BYTES = 8 * 1024 * 1024
MAX_VERTICES = 5_000_000
MAX_TRIANGLES = 5_000_000
MAX_COMPONENT_DEPTH = 16

KINTSUGI_PART_NAMES = frozenset({"CeramicBody", "GoldSeams"})

#: Values the slicers use for a plain, printable model part.  Anything else
#: (modifier, negative volume, support blocker/enforcer) is rejected.
_PLAIN_VOLUME_TYPES = {"", "ModelPart"}
_PLAIN_SUBTYPES = {"", "normal_part"}


def _tag(name: str) -> str:
    return f"{{{CORE_NS}}}{name}"


class _Object:
    __slots__ = ("object_id", "type", "name", "vertices", "faces", "components")

    def __init__(self, object_id: str, type: str, name: str | None) -> None:
        self.object_id = object_id
        self.type = type
        self.name = name
        self.vertices: np.ndarray | None = None
        self.faces: np.ndarray | None = None
        self.components: list[tuple[str, str | None, np.ndarray]] = []


class _Package:
    """An opened 3MF zip with lazily parsed model parts."""

    def __init__(self, archive: zipfile.ZipFile) -> None:
        self.archive = archive
        self._roots: dict[str, ET.Element] = {}
        self._objects: dict[str, dict[str, _Object]] = {}
        self._consumed = 0  # decompressed bytes read so far, across all parts

    # -- raw access --------------------------------------------------------
    def _read_bounded(self, name: str, limit: int) -> bytes | None:
        """Decompress an entry, never reading past its declared size or ``limit``.

        Returns ``None`` when an honest entry is larger than ``limit``.  A zip's
        declared sizes are attacker-controlled, but an honest entry never
        decompresses to *more* than its declared size, so that is the cut-off
        (``zipfile`` also truncates at it, which turns an understated header
        into a CRC failure).  Reading a bounded number of bytes, instead of
        ``archive.read(name)``, stops a small file from inflating gigabytes
        before that check can happen.  Every error the zip layer can raise for
        a damaged or unsupported entry becomes a ``ValueError`` (the API
        reports those as an invalid model, not a 500).
        """
        limit = max(limit, 0)
        try:
            declared = self.archive.getinfo(name).file_size
            cap = min(limit, declared)
            with self.archive.open(name) as handle:
                data = handle.read(cap + 1)
        except KeyError:
            raise ValueError(
                f"3MF part '{name}' was not found in the package"
            ) from None
        except (
            zipfile.BadZipFile,
            zlib.error,
            lzma.LZMAError,
            EOFError,
            NotImplementedError,
            RuntimeError,
            OSError,
        ) as exc:
            raise ValueError(
                f"3MF part '{name}' is corrupt or uses an unsupported zip "
                f"feature: {exc}"
            ) from exc
        # ``data`` can only exceed ``cap`` when the limit is below the declared
        # size, i.e. an honest entry that is simply too big.
        return None if len(data) > cap else data

    def _remaining(self) -> int:
        return MAX_UNCOMPRESSED_BYTES - self._consumed

    def read(self, name: str) -> bytes:
        """Read a part the geometry needs; over the package budget is an error."""
        data = self._read_bounded(name, self._remaining())
        if data is None:
            raise ValueError(
                "3MF package is too large when uncompressed (more than "
                f"{MAX_UNCOMPRESSED_BYTES / (1024 * 1024):.0f} MB decompressed, "
                f"while reading '{name}')"
            )
        self._consumed += len(data)
        return data

    def read_optional(self, name: str, limit: int) -> bytes | None:
        """Read a hint-only part (vendor config); ``None`` if over ``limit``."""
        data = self._read_bounded(name, min(limit, self._remaining()))
        if data is not None:
            self._consumed += len(data)
        return data

    def has(self, name: str) -> bool:
        return name in self.archive.namelist()

    # -- XML parts ---------------------------------------------------------
    def xml_root(self, name: str) -> ET.Element:
        cached = self._roots.get(name)
        if cached is not None:
            return cached
        data = self.read(name)
        root = _parse_xml(data, name)
        self._roots[name] = root
        return root

    def objects(self, part: str) -> dict[str, _Object]:
        cached = self._objects.get(part)
        if cached is not None:
            return cached
        root = self.xml_root(part)
        table: dict[str, _Object] = {}
        resources = root.find(_tag("resources"))
        if resources is not None:
            for element in resources.findall(_tag("object")):
                parsed = _parse_object(element, part)
                table[parsed.object_id] = parsed
        self._objects[part] = table
        return table


def _parse_xml(data: bytes, name: str) -> ET.Element:
    if data.startswith((b"\xff\xfe", b"\xfe\xff", b"\x00\x00\xfe\xff", b"\xff\xfe\x00\x00")):
        raise ValueError(f"3MF part '{name}' must be UTF-8 encoded XML")
    if b"<!doctype" in data.lower():
        raise ValueError(
            f"3MF part '{name}' contains a DOCTYPE declaration, which is not allowed"
        )
    try:
        return ET.fromstring(data)
    except ET.ParseError as exc:
        raise ValueError(f"3MF part '{name}' is not valid XML: {exc}") from exc


def _normalise_part(target: str, *, what: str) -> str:
    """Turn a package target ('/3D/x.model') into an archive member name."""
    if not target or "\\" in target:
        raise ValueError(f"invalid 3MF {what} path {target!r}")
    stripped = target.lstrip("/")
    segments = stripped.split("/")
    if ".." in segments or not stripped or "" in segments:
        raise ValueError(
            f"3MF {what} path {target!r} must stay inside the package "
            "(no '..' or empty segments)"
        )
    return posixpath.normpath(stripped)


def _parse_transform(text: str | None, where: str) -> np.ndarray:
    """3MF's 12 values -> 4x4 row-vector matrix (``p' = [x y z 1] @ M``)."""
    matrix = np.eye(4, dtype=np.float64)
    if text is None or not text.strip():
        return matrix
    try:
        values = [float(token) for token in text.split()]
    except ValueError:
        raise ValueError(f"3MF transform on {where} is not numeric: {text!r}") from None
    if len(values) != 12 or not all(math.isfinite(v) for v in values):
        raise ValueError(
            f"3MF transform on {where} must have 12 finite values, got {text!r}"
        )
    array = np.asarray(values, dtype=np.float64)
    matrix[:3, :3] = array[:9].reshape(3, 3)
    matrix[3, :3] = array[9:]
    return matrix


def _parse_object(element: ET.Element, part: str) -> _Object:
    object_id = element.get("id")
    if object_id is None:
        raise ValueError(f"3MF object without an id in '{part}'")
    parsed = _Object(object_id, element.get("type") or "model", element.get("name"))

    mesh = element.find(_tag("mesh"))
    if mesh is not None:
        vertices_el = mesh.find(_tag("vertices"))
        triangles_el = mesh.find(_tag("triangles"))
        vertex_elements = [] if vertices_el is None else vertices_el.findall(_tag("vertex"))
        triangle_elements = [] if triangles_el is None else triangles_el.findall(_tag("triangle"))
        if len(vertex_elements) > MAX_VERTICES:
            raise ValueError(
                f"3MF object {object_id} has too many vertices "
                f"({len(vertex_elements)} > {MAX_VERTICES})"
            )
        if len(triangle_elements) > MAX_TRIANGLES:
            raise ValueError(
                f"3MF object {object_id} has too many triangles "
                f"({len(triangle_elements)} > {MAX_TRIANGLES})"
            )
        try:
            vertices = np.array(
                [
                    (float(v.get("x")), float(v.get("y")), float(v.get("z")))
                    for v in vertex_elements
                ],
                dtype=np.float64,
            ).reshape(-1, 3)
            faces = np.array(
                [
                    (int(t.get("v1")), int(t.get("v2")), int(t.get("v3")))
                    for t in triangle_elements
                ],
                dtype=np.int64,
            ).reshape(-1, 3)
        except (TypeError, ValueError):
            raise ValueError(
                f"3MF object {object_id} in '{part}' has a vertex or triangle "
                "with a missing or non-numeric attribute"
            ) from None
        if not np.all(np.isfinite(vertices)):
            raise ValueError(f"3MF object {object_id} has non-finite vertex coordinates")
        if len(faces) and (faces.min() < 0 or faces.max() >= len(vertices)):
            bad = int(faces.max() if faces.max() >= len(vertices) else faces.min())
            raise ValueError(
                f"3MF object {object_id} has a triangle that references vertex "
                f"{bad}, but the object only has {len(vertices)} vertices"
            )
        parsed.vertices = vertices
        parsed.faces = faces

    components = element.find(_tag("components"))
    if components is not None:
        for component in components.findall(_tag("component")):
            target = component.get("objectid")
            if target is None:
                raise ValueError(f"3MF component without an objectid in object {object_id}")
            path = component.get(f"{{{PROD_NS}}}path")
            transform = _parse_transform(
                component.get("transform"), f"a component of object {object_id}"
            )
            parsed.components.append((target, path, transform))
    return parsed


def _find_root_part(package: _Package) -> str:
    candidate = DEFAULT_ROOT_PART
    if package.has(RELS_PART):
        rels = _parse_xml(package.read(RELS_PART), RELS_PART)
        for rel in rels.iter(f"{{{REL_NS}}}Relationship"):
            if (rel.get("Type") or "").endswith("/3dmodel"):
                candidate = _normalise_part(rel.get("Target") or "", what="root model")
                break
    if not package.has(candidate):
        raise ValueError(
            f"3MF package has no root model (expected '{candidate}')"
        )
    return candidate


def _reject_slicer_modifiers(package: _Package) -> None:
    """Refuse vendor-config modifier / negative volumes (kept out of core XML)."""
    for name in package.archive.namelist():
        lowered = name.lower()
        if not (lowered.startswith("metadata/") and lowered.endswith(".config")):
            continue
        data = package.read_optional(name, MAX_CONFIG_BYTES)
        if data is None:
            continue  # over the size limit: a hint we do not need to trust
        if b"<!doctype" in data.lower():
            continue  # never parsed, never trusted; the config is only a hint
        try:
            root = ET.fromstring(data)
        except ET.ParseError:
            continue
        for element in root.iter():
            subtype = element.get("subtype")
            key = element.get("key")
            value = element.get("value")
            flagged = None
            if subtype is not None and subtype not in _PLAIN_SUBTYPES:
                flagged = subtype
            elif key == "volume_type" and value is not None and value not in _PLAIN_VOLUME_TYPES:
                flagged = value
            elif key == "subtype" and value is not None and value not in _PLAIN_SUBTYPES:
                flagged = value
            if flagged is not None:
                raise ValueError(
                    "3MF contains slicer modifier or negative volumes "
                    f"({flagged!r} in {name}); only plain model parts are supported"
                )


def load_3mf(path: str | Path) -> trimesh.Trimesh:
    """Load a ``.3mf`` file as one flattened millimetre ``trimesh.Trimesh``."""
    try:
        archive = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError) as exc:
        raise ValueError(f"not a valid 3MF (ZIP) package: {exc}") from exc
    with archive:
        # A cheap early reject for honest oversize packages.  The headers can
        # lie, so the real guard is the bounded read in _Package._read_bounded.
        total = sum(info.file_size for info in archive.infolist())
        if total > MAX_UNCOMPRESSED_BYTES:
            raise ValueError(
                "3MF package is too large when uncompressed "
                f"({total / (1024 * 1024):.0f} MB; limit "
                f"{MAX_UNCOMPRESSED_BYTES / (1024 * 1024):.0f} MB)"
            )
        return _load_from_archive(archive)


def _load_from_archive(archive: zipfile.ZipFile) -> trimesh.Trimesh:
    package = _Package(archive)
    root_part = _find_root_part(package)
    root = package.xml_root(root_part)

    unit = root.get("unit") or "millimeter"
    if unit not in UNIT_FACTORS:
        raise ValueError(
            f"unknown 3MF unit {unit!r}; expected one of {', '.join(UNIT_FACTORS)}"
        )

    build = root.find(_tag("build"))
    items = [] if build is None else build.findall(_tag("item"))
    if not items:
        raise ValueError("3MF has no build item to load")
    if len(items) != 1:
        raise ValueError(
            "Only single-object 3MF files are supported; this file has "
            f"{len(items)} build items"
        )
    item = items[0]
    item_id = item.get("objectid")
    if item_id is None:
        raise ValueError("3MF build item has no objectid")
    start = _parse_transform(item.get("transform"), "the build item")

    vertex_blocks: list[np.ndarray] = []
    face_blocks: list[np.ndarray] = []
    names: set[str] = set()
    totals = {"vertices": 0, "triangles": 0}

    def walk(part: str, object_id: str, matrix: np.ndarray, depth: int, chain: frozenset) -> None:
        if depth > MAX_COMPONENT_DEPTH:
            raise ValueError(
                f"3MF component nesting is deeper than {MAX_COMPONENT_DEPTH} levels"
            )
        key = (part, object_id)
        if key in chain:
            raise ValueError(f"3MF component cycle detected at object {object_id}")
        obj = package.objects(part).get(object_id)
        if obj is None:
            raise ValueError(f"3MF object {object_id} not found in '{part}'")
        if obj.type != "model":
            raise ValueError(
                f"3MF object {object_id} has type {obj.type!r}; "
                "only objects of type 'model' are supported"
            )
        if obj.vertices is not None and obj.faces is not None:
            if obj.name:
                names.add(obj.name)
            totals["vertices"] += len(obj.vertices)
            totals["triangles"] += len(obj.faces)
            if totals["vertices"] > MAX_VERTICES or totals["triangles"] > MAX_TRIANGLES:
                raise ValueError(
                    "3MF flattens to too many triangles "
                    f"(limit {MAX_TRIANGLES} triangles / {MAX_VERTICES} vertices)"
                )
            homogeneous = np.hstack([obj.vertices, np.ones((len(obj.vertices), 1))])
            moved = (homogeneous @ matrix)[:, :3]
            faces = obj.faces
            if np.linalg.det(matrix[:3, :3]) < 0.0:
                faces = faces[:, [0, 2, 1]]  # a mirror flips winding; keep it outward
            vertex_blocks.append(moved)
            face_blocks.append(faces)
        for target, path, transform in obj.components:
            child_part = (
                part if path is None else _normalise_part(path, what="component")
            )
            if child_part != part and not package.has(child_part):
                raise ValueError(
                    f"3MF part '{child_part}' referenced by object {object_id} "
                    "was not found in the package"
                )
            walk(child_part, target, transform @ matrix, depth + 1, chain | {key})

    walk(root_part, item_id, start, 1, frozenset())

    if names == KINTSUGI_PART_NAMES:
        raise ValueError(
            "This file is already a Kintsugi output (CeramicBody + GoldSeams); "
            "upload the original model instead"
        )
    _reject_slicer_modifiers(package)

    if totals["triangles"] == 0:
        raise ValueError("3MF contains no triangles")

    offsets = np.cumsum([0] + [len(block) for block in vertex_blocks[:-1]])
    vertices = np.vstack(vertex_blocks) * UNIT_FACTORS[unit]
    faces = np.vstack([block + offset for block, offset in zip(face_blocks, offsets)])
    return trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
