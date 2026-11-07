# Kintsugi Fracture

A generative mesh-fracture engine that turns a closed vessel mesh (a bowl, a vase) into a two-part, multi-material 3D-printable **kintsugi** assembly. An income-ratio metric `R` drives the fracture:

- `R ≥ 1` leaves the vessel pristine.
- Lower `R` means more cracks, wider gold seams and a taller damaged band.

The engine writes `ceramic_body.stl` and `gold_seams.stl`. Optionally it also writes a single 3MF with both parts as components of one object.

## How it works

1. **Validate** the input: a closed solid, in millimetres, Z up, each extent 20–300 mm, and radial probe rays must hit it.
2. **Derive parameters** from severity `S = 1 − R`:
   - seed count `N = ⌊2 + 8S⌋`;
   - seam width `W = 0.8 + 1.4S` mm;
   - band height `H = H_mesh·(0.2 + 0.8S)`.
3. **Crack graph:** a periodic Voronoi diagram in unrolled cylindrical space `(u = θ·r̄, z)`. Every point lies on the true periodic diagram before noise. A θ-periodic noise field then roughens the cracks. Paths are cut where they leave the vessel's wall range, so the solid floor is never touched.
4. **Project** each crack point onto the exterior surface by radial ray casting, recording the local wall thickness.
5. **Cutter:**
   - *vein* mode uses inset spheres, a partial-depth groove;
   - *ribbon* mode uses through-wall slab hulls, separating the shards.
6. **Exact CSG** with [manifold3d](https://github.com/elalish/manifold): `ceramic = M − C`, `gold = M ∩ C`.
7. **Debris swap:** crumbs under 1 mm³ move into the other material. Nothing is deleted.
8. **Round-trip guard:** both outputs must reload from binary STL with zero non-manifold edges. Sub-10 nm CSG slivers are repaired first. Otherwise the cutter is rebuilt on a new sub-seed, up to 3 times, before a `RuntimeError` with no files written.

Output is deterministic: the same input, `R`, mode and seed give byte-identical files across processes.

## Setup

Requires Python 3.11.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
```

## Usage

**CLI**

```bash
.venv/bin/python kintsugi.py presets/tea_bowl.stl -o output/demo -R 0.2 --mode ribbon --seed 7 --3mf
```

Options: `-R/--income-ratio` (default 0.5), `--mode vein|ribbon`, `--seed`, `--seam-width`, `--3mf`, `--json`.

**Python**

```python
import kintsugi
result = kintsugi.generate_kintsugi_mesh("presets/vase.stl", "output/vase", R=0.3, mode="vein", seed=1)
```

**Web GUI** (a Windows XP-styled viewer built on Three.js and FastAPI)

```bash
.venv/bin/python web_app.py --host 127.0.0.1 --port 8000
```

**Samples**

```bash
.venv/bin/python generate_sample.py
```

## Tests and verification

Day to day, tests run on a workstation and come back to the VPS as a standard report. See **[TESTING.md](TESTING.md)**:

```bash
.venv/bin/python tools/test_report.py run [--profile full]   # workstation
.venv/bin/python tools/test_report.py check report.txt      # VPS: does it apply, and what passed?
```

The individual commands:

```bash
.venv/bin/python -m unittest discover -s tests -v          # 36 tests
.venv/bin/python tools/crack_graph_audit.py --seeds 200      # graph on the true periodic Voronoi; 0 crossings
.venv/bin/python tools/noise_fold_audit.py                   # noise-field folding (0.0% fold area on presets)
.venv/bin/python tools/sweep.py --presets tea_bowl vase --ratios 0 0.05 0.2 0.5 0.9 0.99 --modes ribbon vein --seeds 0 1 2 3 4 5
.venv/bin/python tools/sweep_out_of_sample.py --presets tea_bowl vase --ratios 0.15 0.3 0.45 0.65 0.85 --modes ribbon vein --seeds 500 501 502 503 504 505 506 507
.venv/bin/python tools/render_remediation.py . output/verification/renders_round3
```

## Status

The design, specs and full verification history live in [`openspec/changes/kintsugi-mesh-fracture/`](openspec/changes/kintsugi-mesh-fracture/). See `verification.md` §8, §10, §11 and §12 for each review round.

Verified on held-out seeds:
- 36/36 tests pass;
- the 160-run sweeps are clean with 0 cutter retries;
- the crack graph has 0 phantom ridges and 0 crossings;
- no gold reaches the floor;
- output is byte-identical across processes.

**Status of tracked items** (`tasks.md` §10 and task 6.3):

| ID | Status | Note |
|---|---|---|
| F18 | Addressed (PATCH-01) | Preset fold rate 0.0%. Small-radius vector-field Jacobian proof gap and aesthetic flattening under Voronoi are superseded by `kintsugi-crack-growth`. |
| F19 | Addressed (PATCH-01) | Cracks reach the lip at high severity. Lip refinement superseded by rim-seeded growth in `kintsugi-crack-growth`. |
| F20 | Closed | `guard_evaluations` field documented and asserted in API tests. |
| 10.4 | Closed | Documented decision: tool defaults to loopback `127.0.0.1`; network deployments use reverse proxies for payload caps. |
| 6.3 | Manual | Import the 3MF into Bambu Studio and PrusaSlicer and confirm it loads as one object with two parts. |
