#!/usr/bin/env python3
"""Render the 12-case growth-mode Kintsugi verification contact sheet.

Rows are the two supported ceramic models (Japanese Tea Bowl and Tall Vase) at
R = 0.0, 0.2 and 0.5 with two seeds each.  Columns are a perspective side view,
a top rim view and an isolated gold-seam view.

The rasteriser below is a self-contained pure-numpy z-buffer implementation
adapted from ``tools/render.py``.  That module has top-level argparse side
effects, so it must not be imported here.

Usage:
    .venv/bin/python tools/spike_contact_sheet.py [--output PATH]
        [--repo PATH] [--panel-px INT]
"""

from __future__ import annotations

import argparse
import math
import struct
import sys
import tempfile
import zlib
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = "reports/contact_sheet.png"
DEFAULT_PANEL_PX = 340

BACKGROUND = (30, 34, 44)
CERAMIC = (235, 230, 218)
GOLD = (230, 175, 40)

# One title-bar colour per contact-sheet row so rows are distinguishable.
ROW_TITLE_COLORS = [
    (0, 88, 238),      # Luna blue
    (0, 120, 215),     # lighter blue
    (112, 192, 64),    # XP green
    (230, 138, 0),     # XP warning amber
]

COLUMNS = [
    ("side", -60.0, 20.0),
    ("top", -60.0, 70.0),
    ("gold", -60.0, 20.0),
]

_MODEL_CASES = (
    ("TEA BOWL", "tea_bowl", "tea_bowl"),
    ("TALL VASE", "vase", "small_vase"),
)

# 2 supported ceramic models x 3 severities x 2 seeds = 12 rendered cases.
CASES = [
    {
        "label": f"{label} R={ratio:g} S{seed}",
        "preset": preset,
        "builder": builder,
        "R": ratio,
        "seed": seed,
    }
    for label, preset, builder in _MODEL_CASES
    for ratio in (0.0, 0.2, 0.5)
    for seed in (0, 1)
]


# 5x7 bitmap font used for row labels on the contact sheet.
_FONT: dict[str, tuple[str, ...]] = {
    " ": ("00000",) * 7,
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
}


def _draw_text(
    image: np.ndarray,
    text: str,
    x: int,
    y: int,
    *,
    scale: int = 2,
    color=(255, 255, 255),
) -> None:
    height, width, _ = image.shape
    for character in text.upper():
        glyph = _FONT.get(character)
        if glyph is None:
            x += 4 * scale
            continue
        for row_index, row in enumerate(glyph):
            for column_index, bit in enumerate(row):
                if bit != "1":
                    continue
                x0 = x + column_index * scale
                y0 = y + row_index * scale
                x1 = min(width, x0 + scale)
                y1 = min(height, y0 + scale)
                if 0 <= x0 < x1 and 0 <= y0 < y1:
                    image[y0:y1, x0:x1] = color
        x += 6 * scale


# ---------------------------------------------------------------------------
# Minimal PNG writer (RGB8, no external dependencies)
# ---------------------------------------------------------------------------
def write_png(path: str | Path, image: np.ndarray) -> None:
    height, width, _ = image.shape
    raw = b"".join(
        b"\x00" + image[y].astype(np.uint8).tobytes() for y in range(height)
    )

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(
        b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    )
    png += chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")
    Path(path).write_bytes(png)


# ---------------------------------------------------------------------------
# CPU z-buffer rasteriser
# ---------------------------------------------------------------------------
def camera(az: float, el: float, center: np.ndarray, dist: float):
    az, el = math.radians(az), math.radians(el)
    eye = center + dist * np.array(
        [
            math.cos(el) * math.cos(az),
            math.cos(el) * math.sin(az),
            math.sin(el),
        ]
    )
    forward = center - eye
    forward /= np.linalg.norm(forward)
    right = np.cross(forward, [0.0, 0.0, 1.0])
    right /= np.linalg.norm(right)
    up = np.cross(right, forward)
    return eye, forward, right, up


def _draw_title_bar(image: np.ndarray, color) -> None:
    if color is None:
        return
    bar_height = max(4, image.shape[0] // 56)
    image[:bar_height, :] = color


def render(
    meshes,
    az: float = -60.0,
    el: float = 20.0,
    size: int = DEFAULT_PANEL_PX,
    title_bar=None,
    label: str | None = None,
) -> np.ndarray:
    """Render ``[(trimesh, rgb), ...]`` into a square RGB image."""
    size = max(1, int(size))
    image = np.empty((size, size, 3), dtype=np.float64)
    image[:] = BACKGROUND

    if meshes:
        all_vertices = np.vstack([m.vertices for m, _ in meshes])
        center = (all_vertices.min(0) + all_vertices.max(0)) / 2.0
        radius = np.linalg.norm(all_vertices.max(0) - all_vertices.min(0)) / 2.0
        if not np.isfinite(radius) or radius <= 0.0:
            radius = 1.0
        eye, forward, right, up = camera(az, el, center, radius * 3.2)
        fov = 1.0 / math.tan(math.radians(20.0))
        light = -forward * 0.6 + up * 0.6 + right * 0.3
        light /= np.linalg.norm(light)

        def project(points: np.ndarray) -> np.ndarray:
            delta = points - eye
            z = delta @ forward
            x = (delta @ right) / z * fov
            y = (delta @ up) / z * fov
            return np.stack(
                [(x + 1.0) * size / 2.0, (1.0 - y) * size / 2.0, z], -1
            )

        zbuffer = np.full((size, size), np.inf)
        for mesh, rgb in meshes:
            vertices = np.asarray(mesh.vertices, dtype=np.float64)
            faces = np.asarray(mesh.faces)
            if len(faces) == 0:
                continue
            triangles = vertices[faces]
            normals = np.cross(
                triangles[:, 1] - triangles[:, 0],
                triangles[:, 2] - triangles[:, 0],
            )
            lengths = np.linalg.norm(normals, axis=1)
            valid = lengths > 0.0
            if not valid.any():
                continue
            normals[valid] /= lengths[valid, None]
            shade = 0.25 + 0.75 * np.abs(normals @ light)
            projected = project(triangles.reshape(-1, 3)).reshape(-1, 3, 3)
            for index in range(len(projected)):
                if not valid[index]:
                    continue
                triangle = projected[index]
                if np.any(triangle[:, 2] <= 0.0):
                    continue
                x0 = int(max(0, np.floor(triangle[:, 0].min())))
                x1 = int(min(size - 1, np.ceil(triangle[:, 0].max())))
                y0 = int(max(0, np.floor(triangle[:, 1].min())))
                y1 = int(min(size - 1, np.ceil(triangle[:, 1].max())))
                if x0 > x1 or y0 > y1:
                    continue
                xs, ys = np.meshgrid(
                    np.arange(x0, x1 + 1) + 0.5,
                    np.arange(y0, y1 + 1) + 0.5,
                )
                (ax, ay, az_), (bx, by, bz), (cx, cy, cz) = triangle
                den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
                if abs(den) < 1e-12:
                    continue
                w0 = (
                    (by - cy) * (xs - cx) + (cx - bx) * (ys - cy)
                ) / den
                w1 = (
                    (cy - ay) * (xs - cx) + (ax - cx) * (ys - cy)
                ) / den
                w2 = 1.0 - w0 - w1
                inside = (w0 >= 0.0) & (w1 >= 0.0) & (w2 >= 0.0)
                if not inside.any():
                    continue
                z = w0 * az_ + w1 * bz + w2 * cz
                sub = zbuffer[y0 : y1 + 1, x0 : x1 + 1]
                update = inside & (z < sub)
                sub[update] = z[update]
                image[y0 : y1 + 1, x0 : x1 + 1][update] = (
                    np.array(rgb, dtype=np.float64) * shade[index]
                )

    _draw_title_bar(image, title_bar)
    if label:
        bar_height = max(4, image.shape[0] // 56)
        header_bottom = min(
            image.shape[0], bar_height + max(16, image.shape[0] // 18)
        )
        image[bar_height:header_bottom, :] = (18, 22, 30)
        label_scale = max(
            1,
            min(
                2,
                (image.shape[1] - 12) // max(1, 6 * len(label)),
            ),
        )
        _draw_text(
            image,
            label,
            6,
            bar_height + 3,
            scale=label_scale,
            color=(255, 255, 255),
        )
    return image


# ---------------------------------------------------------------------------
# Sample-model helpers
# ---------------------------------------------------------------------------
def _manifold_to_trimesh(manifold, trimesh):
    """Convert a manifold3d Manifold (or pass through a Trimesh) to Trimesh."""
    if not hasattr(manifold, "to_mesh64"):
        return manifold
    mesh = manifold.to_mesh64()
    return trimesh.Trimesh(
        vertices=np.array(
            mesh.vert_properties[:, :3], dtype=np.float64, copy=True
        ),
        faces=np.array(mesh.tri_verts, dtype=np.int64, copy=True),
        process=False,
    )


def _write_manifold_stl(manifold, trimesh, path: Path) -> Path:
    mesh = _manifold_to_trimesh(manifold, trimesh)
    path.write_bytes(trimesh.exchange.stl.export_stl(mesh))
    return path


def _load_mesh(trimesh, path: str | Path):
    loaded = trimesh.load(str(path), process=True)
    if isinstance(loaded, trimesh.Scene):
        loaded = loaded.dump(concatenate=True)
    return loaded


def _preset_stl(sample_models, trimesh, repo: Path, case, work: Path) -> Path:
    path = repo / "presets" / f"{case['preset']}.stl"
    if path.exists():
        return path
    builder = getattr(sample_models, case.get("builder") or "", None)
    if builder is None:
        raise FileNotFoundError(f"Preset mesh not found: {path}")
    return _write_manifold_stl(
        builder(), trimesh, work / f"{case['preset']}.stl"
    )


# ---------------------------------------------------------------------------
# Contact-sheet generation
# ---------------------------------------------------------------------------
def _generate_case(
    kintsugi,
    sample_models,
    trimesh,
    repo: Path,
    case: dict,
    panel_px: int,
    title_color,
):
    with tempfile.TemporaryDirectory(prefix="kintsugi_spike_") as temp:
        work = Path(temp)
        input_path = _preset_stl(sample_models, trimesh, repo, case, work)

        output_dir = work / "out"
        result = kintsugi.generate_kintsugi_mesh(
            input_path,
            output_dir,
            R=case["R"],
            mode="vein",
            seed=case["seed"],
            generator="growth",
        )

        ceramic = _load_mesh(trimesh, result["ceramic_path"])
        if ceramic is None or len(ceramic.faces) == 0:
            raise ValueError("ceramic body STL is empty")

        gold_path = result.get("gold_path")
        gold = _load_mesh(trimesh, gold_path) if gold_path else None
        if gold is not None and len(gold.faces) == 0:
            gold = None

        full_meshes = [(ceramic, CERAMIC)]
        if gold is not None:
            full_meshes.append((gold, GOLD))
        gold_meshes = [(gold, GOLD)] if gold is not None else []

        panels = []
        for view, az, el in COLUMNS:
            meshes = gold_meshes if view == "gold" else full_meshes
            panels.append(
                render(
                    meshes,
                    az,
                    el,
                    panel_px,
                    title_color,
                    label=case["label"],
                )
            )

        info = {
            "label": case["label"],
            "num_cracks": int(result.get("num_cracks", 0)),
            "ceramic_faces": int(len(ceramic.faces)),
            "gold_faces": int(len(gold.faces)) if gold is not None else 0,
        }
        return panels, info


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"Output PNG path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--repo",
        default=str(REPO),
        help="Repository root (default: parent of this script)",
    )
    parser.add_argument(
        "--panel-px",
        type=int,
        default=DEFAULT_PANEL_PX,
        help=f"Panel edge length in pixels (default: {DEFAULT_PANEL_PX})",
    )
    args = parser.parse_args(argv)

    repo = Path(args.repo).expanduser().resolve()
    panel_px = max(64, int(args.panel_px))

    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    import kintsugi  # noqa: E402
    import sample_models  # noqa: E402
    import trimesh  # noqa: E402

    try:
        sample_models.ensure_presets(repo / "presets")
    except Exception as exc:  # pragma: no cover - defensive
        print(
            f"warning: could not ensure bundled presets: {exc}",
            file=sys.stderr,
        )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    row_count, column_count = len(CASES), len(COLUMNS)
    sheet = np.zeros(
        (row_count * panel_px, column_count * panel_px, 3), dtype=np.float64
    )
    summaries = []

    for row_index, case in enumerate(CASES):
        title_color = ROW_TITLE_COLORS[row_index % len(ROW_TITLE_COLORS)]
        try:
            panels, info = _generate_case(
                kintsugi,
                sample_models,
                trimesh,
                repo,
                case,
                panel_px,
                title_color,
            )
        except Exception as exc:  # keep the full contact-sheet matrix
            info = {
                "label": case["label"],
                "error": f"{type(exc).__name__}: {exc}",
            }
            blank = render(
                [],
                size=panel_px,
                title_bar=title_color,
                label=case["label"],
            )
            panels = [blank.copy() for _ in COLUMNS]

        summaries.append(info)
        y0 = row_index * panel_px
        for column_index, panel in enumerate(panels):
            x0 = column_index * panel_px
            sheet[
                y0 : y0 + panel_px, x0 : x0 + panel_px
            ] = panel

    write_png(output, sheet)
    print(output)
    for info in summaries:
        if info.get("error"):
            print(f"{info['label']} | ERROR {info['error']}")
        else:
            print(
                f"{info['label']} | cracks={info['num_cracks']}"
                f" ceramic_faces={info['ceramic_faces']}"
                f" gold_faces={info['gold_faces']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
