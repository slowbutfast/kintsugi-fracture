"""Offline verification renders: z-buffer rasteriser -> PNG, no GUI deps.

Usage: python render.py <repo_root> <out_dir>
"""
import argparse, sys, zlib, struct, math, tempfile
from collections import Counter
from pathlib import Path
import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("repo", nargs="?", default=".", help="Repository root")
parser.add_argument(
    "out",
    nargs="?",
    default="output/verification/renders",
    help="Output directory for PNG renders",
)
args = parser.parse_args()
repo, out = Path(args.repo), Path(args.out)
sys.path.insert(0, str(repo))
import kintsugi, trimesh  # noqa: E402

out.mkdir(parents=True, exist_ok=True)
W_PX, H_PX = 520, 520


def write_png(path, img):
    h, w, _ = img.shape
    raw = b"".join(b"\x00" + img[y].astype(np.uint8).tobytes() for y in range(h))
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")
    Path(path).write_bytes(png)


def camera(az, el, center, dist):
    az, el = math.radians(az), math.radians(el)
    eye = center + dist * np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
    f = center - eye; f /= np.linalg.norm(f)
    r = np.cross(f, [0, 0, 1.0]); r /= np.linalg.norm(r)
    u = np.cross(r, f)
    return eye, f, r, u


def render(meshes, markers=(), az=-60, el=25, title_bar=None):
    """meshes: list of (trimesh, rgb). markers: (N,3) points drawn as red squares."""
    allv = np.vstack([m.vertices for m, _ in meshes])
    center = (allv.min(0) + allv.max(0)) / 2
    radius = np.linalg.norm(allv.max(0) - allv.min(0)) / 2
    eye, f, r, u = camera(az, el, center, radius * 3.2)
    fov = 1.0 / math.tan(math.radians(20))
    light = -f * 0.6 + u * 0.6 + r * 0.3; light /= np.linalg.norm(light)

    def proj(p):
        d = p - eye
        z = d @ f
        x = (d @ r) / z * fov; y = (d @ u) / z * fov
        return np.stack([(x + 1) * W_PX / 2, (1 - y) * H_PX / 2, z], -1)

    img = np.zeros((H_PX, W_PX, 3)); img[:] = (30, 34, 44)
    zb = np.full((H_PX, W_PX), np.inf)
    for mesh, rgb in meshes:
        tri = mesh.vertices[mesh.faces]
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        nn = np.linalg.norm(n, axis=1); ok = nn > 0
        n[ok] /= nn[ok, None]
        shade = 0.25 + 0.75 * np.abs(n @ light)
        P = proj(tri.reshape(-1, 3)).reshape(-1, 3, 3)
        for t in range(len(P)):
            if not ok[t]:
                continue
            p = P[t]
            if np.any(p[:, 2] <= 0):
                continue
            x0, x1 = int(max(0, np.floor(p[:, 0].min()))), int(min(W_PX - 1, np.ceil(p[:, 0].max())))
            y0, y1 = int(max(0, np.floor(p[:, 1].min()))), int(min(H_PX - 1, np.ceil(p[:, 1].max())))
            if x0 > x1 or y0 > y1:
                continue
            xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            (ax, ay, az_), (bx, by, bz), (cx, cy, cz) = p
            den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
            if abs(den) < 1e-12:
                continue
            w0 = ((by - cy) * (xs - cx) + (cx - bx) * (ys - cy)) / den
            w1 = ((cy - ay) * (xs - cx) + (ax - cx) * (ys - cy)) / den
            w2 = 1 - w0 - w1
            inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
            if not inside.any():
                continue
            z = w0 * az_ + w1 * bz + w2 * cz
            sub = zb[y0:y1 + 1, x0:x1 + 1]
            upd = inside & (z < sub)
            sub[upd] = z[upd]
            img[y0:y1 + 1, x0:x1 + 1][upd] = np.array(rgb) * shade[t]
    if len(markers):
        M = proj(np.asarray(markers))
        for x, y, _ in M:
            xi, yi = int(x), int(y)
            img[max(0, yi - 3):yi + 4, max(0, xi - 3):xi + 4] = (255, 40, 40)
    if title_bar is not None:
        img[:6, :] = title_bar
    return img


def bad_edge_points(stl_path):
    m = trimesh.load(stl_path, process=True)
    cnt = Counter(map(tuple, m.edges_sorted))
    bad = [e for e, v in cnt.items() if v != 2]
    return m.vertices[np.array(bad).ravel()] if bad else np.zeros((0, 3)), m


CERAMIC, GOLD = (24, 24, 27), (230, 175, 40)
GREEN, RED = (60, 170, 60), (220, 50, 50)
cases = [
    ("tea_bowl", 0.2, "ribbon", 7),   # the seed the test suite uses
    ("tea_bowl", 0.2, "ribbon", 0),
    ("tea_bowl", 0.2, "vein", 1),
    ("tea_bowl", 0.7, "vein", 3),
    ("vase", 0.2, "ribbon", 5),
    ("tea_bowl", 0.0, "ribbon", 1),
]
summary = []
for preset, R, mode, seed in cases:
    name = f"{preset}_R{R}_{mode}_s{seed}"
    with tempfile.TemporaryDirectory() as d:
        try:
            res = kintsugi.generate_kintsugi_mesh(repo / "presets" / f"{preset}.stl", d, R=R, mode=mode, seed=seed)
        except ValueError as e:
            summary.append((name, "ValueError", str(e)[:90])); continue
        bc, cer = bad_edge_points(res["ceramic_path"])
        bg, gold = bad_edge_points(res["gold_path"])
        n_bad = (len(bc) + len(bg)) // 2
        ok = cer.is_watertight and gold.is_watertight
        bar = GREEN if ok else RED
        for view, (az, el) in {"side": (-60, 20), "top": (-60, 70)}.items():
            img = render([(cer, CERAMIC), (gold, GOLD)], np.vstack([bc, bg]), az, el, bar)
            write_png(out / f"{name}_{view}.png", img)
        # gold only, so through-wall seams and kissing edges are visible
        write_png(out / f"{name}_gold.png", render([(gold, GOLD)], bg, -60, 20, bar))
        summary.append((name, "watertight" if ok else "NOT watertight", f"bad edges={n_bad} cracks={res['num_cracks']}"))

# 2-D crack graph in (u, z): dangling interior ends marked red
mesh, man = kintsugi.validate_and_load_mesh(repo / "presets" / "tea_bowl.stl", 0.8)
p = kintsugi.compute_parameters(0.8, mesh, manifold=man)
noise0 = lambda rbar, a, rng: (lambda u, z: (np.zeros_like(np.asarray(u, float)),) * 2)
real_noise = kintsugi._make_noise
for label, use_noise in (("graph_noise_off", False), ("graph_noise_on", True)):
    kintsugi._make_noise = real_noise if use_noise else noise0
    paths = kintsugi.generate_crack_paths(
        p, np.random.default_rng(3), generator="voronoi"
    )
    P = p["period"]; Hh = 300; Ww = 900
    img = np.zeros((Hh, Ww, 3)); img[:] = (245, 243, 236)
    zlo, zhi = p["z_min"] - 0.2 * p["H"], p["z_max"] + 0.2 * p["H"]
    to_px = lambda q: (q[0] / P * (Ww - 1), (1 - (q[1] - zlo) / (zhi - zlo)) * (Hh - 1))
    for zz, col in ((p["z_min"], (150, 150, 220)), (p["z_max"], (150, 150, 220)), (0, (0, 0, 0)), (60, (0, 0, 0))):
        y = int(to_px((0, zz))[1])
        if 0 <= y < Hh: img[y, :] = col
    for path in paths:
        for a, b in zip(path[:-1], path[1:]):
            if abs(a[0] - b[0]) > P / 2: continue
            for t in np.linspace(0, 1, 40):
                x, y = to_px(a + t * (b - a)); img[int(y) - 1:int(y) + 1, int(x) - 1:int(x) + 1] = (40, 40, 40)
    ends = np.array([q for path in paths for q in (path[0], path[-1])])
    for i, e in enumerate(ends):
        du = np.abs(ends[:, 0] - e[0]); du = np.minimum(du, P - du)
        dist = np.hypot(du, ends[:, 1] - e[1]); dist[i] = 1e9
        near_edge = min(abs(e[1] - p["z_min"]), abs(e[1] - p["z_max"])) < 0.11 * p["H"]
        col = (60, 160, 60) if dist.min() < 1e-3 else ((150, 150, 150) if near_edge else (230, 30, 30))
        x, y = to_px(e); img[max(0, int(y) - 4):int(y) + 5, max(0, int(x) - 4):int(x) + 5] = col
    write_png(out / f"{label}.png", img)
kintsugi._make_noise = real_noise

for row in summary:
    print(*row, sep=" | ")
