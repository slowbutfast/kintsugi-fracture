## Why

For a generative robotic art installation exploring economic disparity, pristine 3D vessel meshes (closed, millimetre-scale, roughly rotationally symmetric) must be algorithmically fractured into organic "Wabi-Sabi / Kintsugi" assemblies scaled by an income ratio variable $R$. The system must produce physically printable, perfectly aligned multi-material geometry (ceramic body and gold seam) suitable for immediate 3D slicing without boolean glitches, non-manifold errors, or slicer import failures.

## What Changes

- Add a standalone, production-ready computational geometry script `kintsugi.py` providing the `generate_kintsugi_mesh` API and CLI.
- Implement metric-driven fracture scaling where $R \ge 1.0$ returns pristine meshes, and $R < 1.0$ scales crack density, width, and trauma band height inversely with $(1.0 - R)$.
- Validate inputs against a declared envelope (closed manifold, mm units, +Z up, vessel shape) before any branching, and reject anything outside it.
- Implement periodic Voronoi crack generation in unrolled cylindrical space $(u = \theta\bar r, z)$ with exterior projection via `Manifold.ray_cast`, eliminating wall-hopping on thin-walled pottery.
- Implement watertight cutter solid construction using consecutive convex hulls (`(cross_section_i + cross_section_{i+1}).hull()`) via `manifold3d`.
- Implement single-manifold dual CSG execution: `ceramic = input - cutter` and `gold = input ^ cutter`, guaranteeing exact geometric complementarity.
- Swap sub-threshold debris ($< 1.0\text{ mm}^3$) from either output into the other material, conserving volume.
- Export complementary STL pairs and a single-object, two-component 3MF. The wealthy state writes no gold STL.
- Provide a parametric sample generation script `generate_sample.py` and comprehensive test suite `tests/test_kintsugi.py`.
- Add `DESIGN.md` visual identity specification conforming to the Google `design.md` token and prose format.
- Add a local retro 2000s Windows XP GUI (`web_app.py`, `static/index.html`, `static/xp.css`, `static/viewer.js`) powered by FastAPI and Three.js with bundled preset models and interactive 3D inspection.

## Capabilities

### New Capabilities
- `mesh-fracture-engine`: Input validation, metric $R$ clamping, noise-warped periodic Voronoi crack generation, convex-hull cutter construction, and direct Manifold3D CSG boolean operations.
- `multi-material-export`: Post-processing shard filtering, STL disk export, and multi-volume 3MF assembly packaging.
- `retro-web-gui`: Zero-build Windows XP Luna-styled local desktop web interface with real-time Three.js 3D viewport, preloaded sample models, live parameter controls, and one-click slicer downloads, governed by `DESIGN.md`.

### Modified Capabilities
*(None - this is a greenfield module)*

## Impact

- Adds runtime dependencies: `trimesh`, `manifold3d>=3.5`, `numpy`, `scipy`, `fastapi`, `uvicorn`, `python-multipart`. Dev-only: `rtree`.
- Arbitrary non-vessel meshes (e.g. Benchy) are explicitly unsupported in ribbon through-wall mode, but supported in vein mode or via preset mesh bounds.
- Exports standard binary STL files and `.3mf` files consumable by any modern 3D slicer.
- Self-contained CLI, Python API, and local Web GUI server running at `http://localhost:8000`.
