#!/usr/bin/env python3
"""Render 2-D (u, z) crack graphs with band edges and wall limits.

Usage: .venv/bin/python tools/render_crack_graph.py [repo_root] [out_dir]
"""

from __future__ import annotations

import argparse
import struct
import sys
import unittest.mock
import zlib
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
import kintsugi  # noqa: E402


def _zero_noise(rbar, base_amplitude, rng):
    def eta(u, z):
        zeros = np.zeros_like(np.asarray(u, dtype=np.float64))
        return zeros, zeros.copy()

    return eta


def _write_png(path: Path, image: np.ndarray) -> None:
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
    path.write_bytes(png)


def render_case(preset: str, S: float, seed: int, out: Path) -> Path:
    path = REPO / "presets" / f"{preset}.stl"
    mesh, manifold = kintsugi.validate_and_load_mesh(path, 0.0)
    params = kintsugi.compute_parameters(S, mesh, manifold=manifold)
    with unittest.mock.patch.object(kintsugi, "_make_noise", _zero_noise):
        paths = kintsugi.generate_crack_paths(
            params, np.random.default_rng(seed)
        )

    period = float(params["period"])
    z_values = [
        float(params["z_min"]),
        float(params["z_max"]),
        float(params["wall_z_min"]),
        float(params["wall_z_max"]),
        float(params["z_wall_lo"]),
        float(params["z_wall_hi"]),
    ]
    z_lo = min(z_values) - 0.05 * (max(z_values) - min(z_values) + 1.0)
    z_hi = max(z_values) + 0.05 * (max(z_values) - min(z_values) + 1.0)
    width, height = 900, 460
    image = np.full((height, width, 3), 245, dtype=np.uint8)

    def to_pixel(u: float, z: float) -> tuple[int, int]:
        x = int(np.clip(u / period, 0.0, 1.0) * (width - 1))
        y = int(np.clip((z_hi - z) / (z_hi - z_lo), 0.0, 1.0) * (height - 1))
        return x, y

    def draw_hline(z: float, color: tuple[int, int, int]) -> None:
        _, y = to_pixel(0.0, z)
        image[max(0, y - 1) : y + 2, :] = color

    draw_hline(float(params["z_min"]), (130, 130, 210))
    draw_hline(float(params["z_max"]), (130, 130, 210))
    draw_hline(float(params["z_wall_lo"]), (40, 140, 60))
    draw_hline(float(params["z_wall_hi"]), (40, 140, 60))

    for path in paths:
        for a, b in zip(path[:-1], path[1:]):
            if abs(a[0] - b[0]) > 0.5 * period:
                continue
            for t in np.linspace(0.0, 1.0, 50):
                point = a + t * (b - a)
                x, y = to_pixel(float(point[0]), float(point[1]))
                image[max(0, y - 1) : y + 2, max(0, x - 1) : x + 2] = (
                    35,
                    35,
                    35,
                )

    target = out / f"crack_graph_{preset}_S{S}_seed{seed}.png"
    _write_png(target, image)
    return target


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", nargs="?", default=str(REPO))
    parser.add_argument(
        "out",
        nargs="?",
        default=str(REPO / "output" / "verification" / "renders_round3"),
    )
    args = parser.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rendered = [
        render_case("tea_bowl", 1.0, 1, out),
        render_case("tea_bowl", 0.6, 76, out),
    ]
    for path in rendered:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
