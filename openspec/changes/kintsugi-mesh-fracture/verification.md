# Verification — kintsugi-mesh-fracture

**Date:** 2026-11-06  
**Schema:** `tdd-rnd`  
**Environment:** Python 3.11.2, NumPy 2.4.6, SciPy 1.17.1, trimesh 5.2.0,
manifold3d 3.5.4, FastAPI 0.162.0, uvicorn, rtree (test-only), headless
Chromium via Playwright.

All automated checks below were run from the repository root with the project
virtual environment (`.venv`).

---

## 1. Automated test suite

Command:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Verbatim result:

```text
test_3mf_structure (test_kintsugi.KintsugiTestCase.test_3mf_structure) ... ok
test_debris_swap (test_kintsugi.KintsugiTestCase.test_debris_swap) ... ok
test_determinism (test_kintsugi.KintsugiTestCase.test_determinism) ... ok
test_input_envelope_rejection (test_kintsugi.KintsugiTestCase.test_input_envelope_rejection) ... ok
test_input_validation (test_kintsugi.KintsugiTestCase.test_input_validation) ... ok
test_parameter_table (test_kintsugi.KintsugiTestCase.test_parameter_table) ... ok
test_printable_channel_thickness (test_kintsugi.KintsugiTestCase.test_printable_channel_thickness) ... ok
test_ribbon_through_wall (test_kintsugi.KintsugiTestCase.test_ribbon_through_wall) ... ok
test_stl_disk_roundtrip (test_kintsugi.KintsugiTestCase.test_stl_disk_roundtrip) ... ok
test_vein_depth (test_kintsugi.KintsugiTestCase.test_vein_depth) ... ok
test_volume_smoke (test_kintsugi.KintsugiTestCase.test_volume_smoke) ... ok
test_wealthy_case (test_kintsugi.KintsugiTestCase.test_wealthy_case) ... ok
test_api_fracture_success (test_web_api.WebApiTestCase.test_api_fracture_success) ... ok
test_api_fracture_wealthy (test_web_api.WebApiTestCase.test_api_fracture_wealthy) ... ok
test_api_presets (test_web_api.WebApiTestCase.test_api_presets) ... ok

----------------------------------------------------------------------
Ran 15 tests in 18.212s

OK
```

Coverage notes:

- `test_wealthy_case` verifies `R = 1.0` and `R = 1.5` return the validated
  input unchanged, write no gold STL, remove a pre-created stale gold STL, and
  write a single-item, one-component 3MF.
- `test_input_envelope_rejection` verifies an open mesh, a metre-scale mesh and
  a non-vessel are rejected with `ValueError` **and write no files**, at both
  `R = 0.4` and `R = 1.5`.
- `test_stl_disk_roundtrip` reloads both STLs with
  `trimesh.load(..., process=True)` and asserts `is_watertight` and
  `is_volume` for both modes.
- `test_volume_smoke` checks complementary volume before and after the debris
  swap within `1e-6` relative tolerance.
- `test_printable_channel_thickness`, `test_vein_depth`,
  `test_ribbon_through_wall` and `test_debris_swap` measure the resulting
  geometry rather than merely checking file existence.
- `test_determinism` compares byte-identical STL and 3MF files for the same
  seed and confirms a different seed changes the output.

---

## 2. Sample generator

Command:

```bash
.venv/bin/python generate_sample.py
```

Verbatim output:

```text
Wrote parametric bowl fixture: output/bowl_input.stl

--- bowl_R1.0_ribbon ---
  cracks=  0  W=0.80 mm  H=12.00 mm
  volumes: ceramic=65775.66 mm^3  gold=0.00 mm^3
  triangles: ceramic=768  gold=0
  time: 0.03 s

--- bowl_R1.0_vein ---
  cracks=  0  W=0.80 mm  H=12.00 mm
  volumes: ceramic=65775.66 mm^3  gold=0.00 mm^3
  triangles: ceramic=768  gold=0
  time: 0.03 s

--- bowl_R0.7_ribbon ---
  cracks=  7  W=1.22 mm  H=26.40 mm
  volumes: ceramic=64756.49 mm^3  gold=1019.17 mm^3
  triangles: ceramic=5,268  gold=4,522
  time: 0.38 s

--- bowl_R0.7_vein ---
  cracks=  7  W=1.22 mm  H=26.40 mm
  volumes: ceramic=65517.24 mm^3  gold=258.42 mm^3
  triangles: ceramic=13,046  gold=12,258
  time: 1.01 s

--- bowl_R0.2_ribbon ---
  cracks= 17  W=1.92 mm  H=50.40 mm
  volumes: ceramic=60549.70 mm^3  gold=5225.96 mm^3
  triangles: ceramic=10,514  gold=9,738
  time: 0.82 s

--- bowl_R0.2_vein ---
  cracks= 17  W=1.92 mm  H=50.40 mm
  volumes: ceramic=63705.62 mm^3  gold=2070.04 mm^3
  triangles: ceramic=26,602  gold=25,810
  time: 2.16 s

Summary: output/sample_summary.json
```

The complete structured results, including per-stage timings, are in
`output/sample_summary.json`.

### Cross-process determinism

Two separate CLI processes with the same input, `R`, seed and mode produced
identical MD5 hashes:

```text
5d9523753507ba376a4ff5556b78b42c  output/determinism_a/ceramic_body.stl
5d9523753507ba376a4ff5556b78b42c  output/determinism_b/ceramic_body.stl
c9c45ca87e19c149a39add9d74dae607  output/determinism_a/gold_seams.stl
c9c45ca87e19c149a39add9d74dae607  output/determinism_b/gold_seams.stl
ff0e64e5c595b73e5566d923131b8ffa  output/determinism_a/kintsugi_assembly.3mf
ff0e64e5c595b73e5566d923131b8ffa  output/determinism_b/kintsugi_assembly.3mf
```

This closes the earlier “determinism across processes” unverified assumption.

---

## 3. 3MF package audit

Audit of `output/bowl_R0.2_ribbon.3mf`:

```text
zip entries: ['[Content_Types].xml', '_rels/.rels', '3D/3dmodel.model']
unit: millimeter
build items: 1
object 1 name= None components= ['2', '3']
object 2 name= CeramicBody components= None
object 3 name= GoldSeams components= None
trimesh load type: Scene
trimesh geometries: ['CeramicBody', 'GoldSeams']
```

The package therefore has exactly one build item, one parent object, and two
named component mesh objects in the input coordinate frame.

### Slicer import check — deferred

Bambu Studio and PrusaSlicer are not installed in this headless environment,
so the GUI import check has **not** been performed. The structural audit above
confirms the 3MF Core layout the slicers consume, but the specific claim that
each slicer shows one object with two parts remains an unverified assumption
until a manual import is done. No claim of slicer validation is made here.

---

## 4. Web GUI verification

The server was started with:

```bash
.venv/bin/python web_app.py --host 127.0.0.1 --port 8000
```

It was exercised through headless Chromium (Playwright, WebGL via SwiftShader).
Verbatim interaction log:

```text
INITIAL {
  "title": "Kintsugi Studio 2001",
  "titlebarText": "Kintsugi Studio 2001",
  "font": "Tahoma, \"Segoe UI\", sans-serif",
  "titlebarBackground": "linear-gradient(to right, rgb(0, 88, 238), rgb(53, 147, 255) 85%, rgb(7, 42, 140))",
  "windowBackground": "rgb(236, 233, 216)",
  "canvas": {
    "width": 948,
    "height": 686
  },
  "presets": [
    "tea_bowl",
    "benchy",
    "vase"
  ],
  "status": "Ready · Japanese Tea Bowl",
  "mesh": "Faces: 768 | Parts: 1"
}
PRESET_SWITCH Ready · Small Vase
ORBIT_SCREENSHOT_CHANGED True 2e651e85ee76cc749ec58dbad2336d95 5e4ef3774d415e97bf6af1bd03b04e39
WEALTHY_LABEL Pristine / Wealthy (0 cracks)
FRACTURE_STATUS 19 cracks · gold 3097.9 mm³
FRACTURE_MESH Faces: 36,878 | Parts: 2 | Ceramic 24037.8 mm³ · Gold 3097.9 mm³
DOWNLOADS {
  "ceramic": "/outputs/afd429f8b153/ceramic_body.stl",
  "gold": "/outputs/afd429f8b153/gold_seams.stl",
  "three": "/outputs/afd429f8b153/kintsugi_assembly.3mf",
  "ceramicDisabled": false,
  "goldDisabled": false,
  "threeDisabled": false
}
DOWNLOAD_FILE ceramic_body.stl /tmp/playwright-artifacts-FwtpFe/989a1ea4-5cd6-48d0-bd61-c2fb51cd6bad
SCREENSHOT /tmp/kintsugi_studio.png
ERRORS []
```

The screenshot is preserved at `output/verification/web_gui.png`. It shows the
Luna titlebar, menu bar, inset viewport, ceramic body in `#f8f6f0`, metallic
gold seams, and the three status-bar cells.

Custom-file upload and fracture were also exercised:

```text
UPLOAD_NOTE Custom: bowl_input.stl
UPLOAD_STATUS Ready · bowl_input.stl
UPLOAD_MESH Faces: 768 | Parts: 1 | Watertight: checked on fracture
UPLOAD_FRACTURE_STATUS 15 cracks · gold 1160.6 mm³
UPLOAD_FRACTURE_MESH Faces: 48,524 | Parts: 2 | Ceramic 64615.0 mm³ · Gold 1160.6 mm³
UPLOAD_GOLD_HREF /outputs/2fabcca383f4/gold_seams.stl
ERRORS []
```

The orbit check compares full-page screenshots before and after a mouse drag;
the images differ, confirming that OrbitControls is receiving input. Preset
switching, the wealthy label, asynchronous fracture completion, enabled
download links, and the ceramic download itself were all observed.

### HTTP smoke checks

```text
GET /api/health                -> {"status":"ok","kernel":"Manifold3D"}
GET /api/presets               -> tea_bowl, benchy, vase
GET /                          -> 200 text/html
GET /xp.css                    -> 200 text/css
GET /viewer.js                 -> 200 text/javascript
GET /presets/tea_bowl.stl      -> 200 model/stl
```

A preset fracture at `R = 0.35` in ribbon mode returned 13 cracks with both
STL downloads and the 3MF download all returning HTTP 200. A wealthy request
at `R = 1.0` returned `num_cracks = 0`, `gold_stl = null`, and a valid ceramic
download.

---

## 5. Requirement Adherence Matrix

| Requirement | Evidence | Status |
| :--- | :--- | :--- |
| **Supported input envelope** — closed manifold, mm, +Z, extents 20–300 mm, radial star-shaped band; reject otherwise | `validate_and_load_mesh`, `_extent_error`, `_radial_probe`; `test_input_envelope_rejection`, `test_wealthy_case`, `test_high_severity_bowl_not_rejected`; 144-run sweep: 0 false rejections | Met |
| **Metric R validation and clamping** — finite float, `S = 1 - clip(R,0,1)`, exact parameter table | `compute_severity`, `compute_parameters`; `test_input_validation`, `test_parameter_table` (`R=0.4 → N=6, W=1.64, H=0.68 H_mesh`) | Met |
| **Watertight input validation** — lossless clean-up, `Mesh64`, status/volume check before any R branch | `validate_and_load_mesh`, `_clean_mesh`; both wealthy and non-wealthy rejection tests | Met |
| **Parameter-space crack generation** — periodic Voronoi, tiling, band clip/jitter, dyadic periodic noise, radial farthest-hit projection with wall thickness, miss splitting | `generate_crack_paths`, `_make_noise`, `_clip_segment_to_rect`, `project_crack_paths`, `_probe_wall_range`; `test_crack_paths_lie_on_periodic_voronoi`, `test_unbounded_rays_obey_voronoi_definition`, `test_junctions_connected`, `test_band_edge_terminals_are_ragged`, `test_no_points_on_wall_limit_lines`, `test_high_severity_bowl_not_rejected`, `test_wall_range_clamp_keeps_gold_out_of_floor`; zero-noise audit all zeros; macOS noise-on audit finds F18 folds/crossings | **Partial — F18 known failure; see §§13–14** |
| **Watertight cutter construction** — inset-sphere vein unions, through-wall ribbon slab hulls, degenerate frame handling, `batch_boolean(Add)` | `build_vein_cutter`, `_build_vein_cutter`, `build_ribbon_cutter`; `test_vein_cutter_no_kissing`, `test_vein_no_retries_out_of_sample_cases`, `test_vein_depth`, `test_ribbon_no_retries_out_of_sample_cases`, `test_ribbon_through_wall`, `test_printable_channel_thickness`; both sweeps 0 retries | Met |
| **Exact complementary partitioning** — `M−C` and `M∩C`, volume tripwire, determinism | `generate_kintsugi_mesh`, `swap_debris`; `test_volume_smoke`, `test_determinism` | Met |
| **Sub-nozzle debris reassignment** — move <1 mm³ components into the other material only across a shared face, never delete | `swap_debris`, `_shares_face_region`; `test_debris_swap`, `test_debris_swap_no_new_bad_edges`, `test_volume_smoke` | Met |
| **Paired manifold STL export** — aligned binary STL, watertight after disk round-trip | `export_kintsugi_stl`, `_stl_bad_edge_count`, `_repair_stl_slivers`, `_roundtrip_bad_edges`; `test_stl_disk_roundtrip`, `test_seed_sweep_watertight`, `test_roundtrip_guard_raises_and_writes_nothing`, `test_ribbon_no_retries_out_of_sample_cases`, `test_vein_no_retries_out_of_sample_cases`; tuning 144/144 and out-of-sample 160/160 clean with 0 retries | Met |
| **Wealthy STL behaviour** — ceramic only, stale gold removed, `gold_path=None` | `generate_kintsugi_mesh` wealthy branch; `test_wealthy_case` | Met |
| **Unified multi-material 3MF** — one build item → parent → `CeramicBody`/`GoldSeams` components, `unit="millimeter"`, identity transforms | `export_kintsugi_3mf`; `test_3mf_structure`, 3MF audit above | Met structurally; slicer GUI check deferred |
| **Retro XP Luna design adherence** — titlebar gradient, Tahoma, bevels, menu bar, status bar | `static/index.html`, `static/xp.css`, `DESIGN.md`; Playwright computed styles + screenshot | Met |
| **Interactive Three.js viewport** — orbit/pan/zoom, PBR ceramic and metallic gold | `static/viewer.js`; Playwright orbit screenshot change, no console/page errors, screenshot | Met |
| **Preset selection and custom upload** | `/api/presets`, `/api/validate`, `sample_models.ensure_presets`, `static/viewer.js`; `test_api_validate_ok`, `test_api_validate_open_mesh`, `test_api_upload_too_large`, `test_job_retention`; Playwright valid/invalid upload and preset switch | Met |
| **Real-time controls and fracture execution** — R, mode, seed, async feedback, status updates | `web_app.py` `/api/fracture`; Playwright `R=1.0` label and `R=0.35` ribbon fracture | Met |
| **One-click downloads** — ceramic STL, gold STL, 3MF | `web_app.py` downloads; Playwright enabled links + ceramic download; HTTP asset checks | Met |
| **Byte-identical determinism** | `test_determinism`; separate-process MD5 comparison above | Met |
| **Slicer import as one object with two parts** | 3MF structure confirmed, but Bambu Studio / PrusaSlicer unavailable | **Deferred (manual)** |

---

## 6. Resolved assumptions and deviations

1. **Printable-thickness assertion resolution.** A vein lens of depth
   `d = min(0.75W, 0.5t)` cannot have a normal thickness of `W`; its centre
   thickness is `d`. The test now asserts the 5th percentile ≥ 0.7 mm, the
   median within ±15% of `d`, and the 90th percentile within ±15% of `W`
   (the widest cross-section). `tests.md` was updated to record this
   mathematically resolved assumption.
2. **Zero-area sliver removal at export.** Manifold3D can leave sub-nanometre
   sliver triangles at boolean seams. They do not change volume, but binary
   STL float32 conversion can turn them into a degenerate two-face island that
   `trimesh` reports as non-watertight. `_export_trimesh` drops triangles with
   area `≤ 1e-12` before STL/3MF export. This is a numerical export clean-up,
   not a change to printable geometry.
3. **Benchy preset.** The bundled `3D Benchy` is intentionally a non-vessel
   (boat + cabin + chimney). It is available for preview but rejected by the
   input envelope when fracture is attempted, as required by the supported
   input scope. `Japanese Tea Bowl` and `Small Vase` are fracture-capable.
4. **3MF parent naming.** The assembly parent object is intentionally unnamed
   so that the only named mesh objects in the package are `CeramicBody` and
   `GoldSeams`; this keeps component resolution unambiguous for parsers.
5. **Cross-process determinism.** Verified with two separate CLI processes, not
   just two calls in one process.
6. **Web GUI verification method.** Visual and interaction checks were done
   with headless Chromium/Playwright because no interactive browser session is
   available. That covers DOM styling, preset switching, WebGL rendering,
   orbit input, fracture, and downloads. A human visual pass is still useful
   for subjective aesthetics, but is not required to establish functional
   adherence.
7. **Slicer GUI check.** Remains unverified because neither Bambu Studio nor
   PrusaSlicer is installed. The 3MF package structure and independent
   `trimesh` scene load are verified; the manual slicer import remains the only
   open verification item.

---

## 7. OpenSpec artifact validation

```bash
openspec validate kintsugi-mesh-fracture --json
```

```json
{
  "totals": { "items": 1, "passed": 1, "failed": 0 },
  "byType": { "change": { "items": 1, "passed": 1, "failed": 0 } }
}
```

`openspec status --change kintsugi-mesh-fracture --json` reports
`isComplete: true` for all planning artifacts (research, proposal, specs,
architecture, design, tests, tasks, verification). Implementation tasks are
28/29 complete; only the manual slicer GUI check (6.3) remains.

---

## 8. Independent verification findings (2026-11-06)

Task 7.0 records the independent verification findings before remediation code
changes. The previous logs above are retained as history.

| ID | Severity | Finding | Evidence | Location |
|---|---|---|---|---|
| F1 | CRITICAL | STL round-trip is non-watertight in 79 of 132 completed sweep runs. Manifold output reports `NoError`, but it contains *kissing* geometry: topologically separate pieces that share edges or vertices in space. STL reload merges vertices by position, which turns these into edges used by 4–6 faces. | Sweep (2 presets × R∈{0,0.05,0.2,0.5,0.9,0.99} × 2 modes × seeds 0–5); per-edge face-count histogram on reload | see F1a–F1c |
| F1a | CRITICAL | **Vein cutter:** every sphere has the same axis-aligned tessellation, so spheres along a path or at a junction share exactly coincident vertices, and their union kisses. A **seeded random rotation per sphere** brought bad edges from 6/34/36 to **0/0/0** (seeds 0, 1, 5; cutter, ceramic and gold all clean). | Experiment: `s.rotate(rng.uniform(0,360,3))` before translate | `kintsugi.py:578-597` (`build_vein_cutter`) |
| F1b | CRITICAL | **Ribbon cutter:** kissing edges already appear in the raw CSG (seed 0: 26 bad edges, z 0–24.8, r 41.98–45, which includes the inner wall/floor corner and the base). Translating the cutter by 1e-3 or 1e-2 does **not** change the count, so this is structural, not an accidental coincidence. Root cause **not yet identified**. | Staged counts: cutter alone, `M−C`, `M∩C` | `kintsugi.py:600-658` (`build_ribbon_cutter`), `kintsugi.py:542-546` (single-hit wall fallback `t = 1.0`) |
| F1c | CRITICAL | **Debris swap** adds new kissing edges in every staged case, including seeds 1 and 2 ribbon, which were clean before the swap. It unions crumbs into the other material even when they touch it only along an edge or at a point. | Pre-swap vs post-swap bad-edge counts | `kintsugi.py:664-680` (`swap_debris`) |
| F2 | CRITICAL | Unbounded Voronoi ridges are extended as **full lines through the finite vertex** (`finite ± direction*span`) instead of **rays pointing away from the seeds**. The ridges cross each other, which Voronoi edges never do; one crack spans most of the circumference. | Crack-graph render `graph_noise_off.png` | `kintsugi.py:357-376` (`_ridge_segment`) |
| F3 | CRITICAL | A valid tea bowl is rejected as "not a vessel" in 12/144 runs, all at R ∈ {0, 0.05}. At S≈1 the band covers the full height. The ±0.1H jitter plus up to ≈12 mm of noise in z push points above the rim or below the base, and those ray misses count against the 5% envelope. | Sweep | `kintsugi.py:466-486`, `kintsugi.py:560-566` |
| F4 | WARNING | Band-edge jitter detaches junctions. (a) Line 446 swaps `at_bottom`/`at_top` when endpoints are put in canonical order; these flags mean "*some* endpoint is on that edge", so they must not be swapped. (b) The jitter then moves `q0` or `q1` at random rather than *the endpoint lying on the band edge*. With noise off, 100/286 interior crack ends dangle; without the jitter, 4/270. | Junction-connectivity metric | `kintsugi.py:440-475` |
| F5 | WARNING | `_export_trimesh` deletes faces with area ≤ 1e-12 from a closed mesh. That opens holes in principle, and it fired on up to 11 faces per export. It masks F1 instead of fixing it, and the 3MF writer uses it too. | Spy on `_export_trimesh` | `kintsugi.py:683-700` |
| F6 | WARNING | The spec's "Custom file upload" scenario requires verifying watertight status on upload. The GUI only parses the file in the browser and shows "Watertight: checked on fracture". | Code read | `static/viewer.js:285-320`, `web_app.py` |
| F7 | WARNING | `output/web/<job_id>/` directories are never cleaned up after successful jobs, and uploads have no size cap. On an installation running unattended, disk use grows without bound. | `ls output/web` (14 dirs) | `web_app.py:76-148` |
| F8 | WARNING | When a projection ray has only one hit (the origin is inside the solid base), `t = 1.0` is hard-coded. The spec doesn't define this case; it produces 2 mm partial cuts into the base. | Code read | `kintsugi.py:542-546` |
| F9 | WARNING | `verification.md` marks every geometry requirement "Met" on single-seed evidence. `tests.md` doesn't describe ribbon thickness. | Doc read | `verification.md`, `tests.md` |
| F10 | SUGGESTION (in scope, trivial) | `_radial_probe` runs twice per job (validation and `compute_parameters`). | Code read | `kintsugi.py:119-127`, `kintsugi.py:277-283` |

### Remediation log

Entries for tasks 7.3–7.10 and the 7.12 finish are appended below as each step
runs.

#### 7.0 — Findings recorded (documentation only)

- Findings F1–F10 are recorded in the table above; the five affected matrix
  rows are downgraded to **Failing — see §8** without deleting prior logs.
- `research.md` gained the single-seed and debris-union superseded claims, the
  verified root-cause facts for F1/F1a/F1b/F1c (F1b explicitly marked not yet
  identified), and the three out-of-scope items.
- No code changed in this step.
#### 7.1 — Failing tests added before implementation

Command:

```bash
.venv/bin/python -m unittest -v \
  tests.test_kintsugi.KintsugiTestCase.test_seed_sweep_watertight \
  tests.test_kintsugi.KintsugiTestCase.test_high_severity_bowl_not_rejected \
  tests.test_kintsugi.KintsugiTestCase.test_voronoi_ridges_do_not_cross \
  tests.test_kintsugi.KintsugiTestCase.test_junctions_connected \
  tests.test_kintsugi.KintsugiTestCase.test_vein_cutter_no_kissing \
  tests.test_kintsugi.KintsugiTestCase.test_debris_swap_no_new_bad_edges \
  tests.test_kintsugi.KintsugiTestCase.test_roundtrip_guard_raises_and_writes_nothing \
  tests.test_web_api.WebApiTestCase.test_api_validate_ok \
  tests.test_web_api.WebApiTestCase.test_api_validate_open_mesh \
  tests.test_web_api.WebApiTestCase.test_api_upload_too_large \
  tests.test_web_api.WebApiTestCase.test_job_retention
```

Verbatim failing output (11 test methods, 18 failures + 17 errors):

```text
/home/node/global-sandbox/projects/wax-robot/.venv/lib/python3.11/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
  from starlette.testclient import TestClient as TestClient  # noqa
test_seed_sweep_watertight (tests.test_kintsugi.KintsugiTestCase.test_seed_sweep_watertight) ... 
  test_seed_sweep_watertight (tests.test_kintsugi.KintsugiTestCase.test_seed_sweep_watertight) (R=0.0, mode='ribbon', seed=0) ... ERROR
  test_seed_sweep_watertight (tests.test_kintsugi.KintsugiTestCase.test_seed_sweep_watertight) (R=0.0, mode='ribbon', seed=1) ... FAIL
  test_seed_sweep_watertight (tests.test_kintsugi.KintsugiTestCase.test_seed_sweep_watertight) (R=0.0, mode='ribbon', seed=2) ... ERROR
  test_seed_sweep_watertight (tests.test_kintsugi.KintsugiTestCase.test_seed_sweep_watertight) (R=0.0, mode='ribbon', seed=3) ... FAIL
  test_seed_sweep_watertight (tests.test_kintsugi.KintsugiTestCase.test_seed_sweep_watertight) (R=0.0, mode='vein', seed=0) ... ERROR
  test_seed_sweep_watertight (tests.test_kintsugi.KintsugiTestCase.test_seed_sweep_watertight) (R=0.0, mode='vein', seed=1) ... FAIL
  test_seed_sweep_watertight (tests.test_kintsugi.KintsugiTestCase.test_seed_sweep_watertight) (R=0.0, mode='vein', seed=2) ... ERROR
  test_seed_sweep_watertight (tests.test_kintsugi.KintsugiTestCase.test_seed_sweep_watertight) (R=0.0, mode='vein', seed=3) ... FAIL
  test_seed_sweep_watertight (tests.test_kintsugi.KintsugiTestCase.test_seed_sweep_watertight) (R=0.2, mode='ribbon', seed=0) ... FAIL
  test_seed_sweep_watertight (tests.test_kintsugi.KintsugiTestCase.test_seed_sweep_watertight) (R=0.2, mode='ribbon', seed=1) ... FAIL
  test_seed_sweep_watertight (tests.test_kintsugi.KintsugiTestCase.test_seed_sweep_watertight) (R=0.2, mode='ribbon', seed=2) ... FAIL
  test_seed_sweep_watertight (tests.test_kintsugi.KintsugiTestCase.test_seed_sweep_watertight) (R=0.2, mode='ribbon', seed=3) ... FAIL
  test_seed_sweep_watertight (tests.test_kintsugi.KintsugiTestCase.test_seed_sweep_watertight) (R=0.2, mode='vein', seed=0) ... FAIL
  test_seed_sweep_watertight (tests.test_kintsugi.KintsugiTestCase.test_seed_sweep_watertight) (R=0.2, mode='vein', seed=1) ... FAIL
  test_seed_sweep_watertight (tests.test_kintsugi.KintsugiTestCase.test_seed_sweep_watertight) (R=0.2, mode='vein', seed=2) ... FAIL
  test_seed_sweep_watertight (tests.test_kintsugi.KintsugiTestCase.test_seed_sweep_watertight) (R=0.2, mode='vein', seed=3) ... FAIL
test_high_severity_bowl_not_rejected (tests.test_kintsugi.KintsugiTestCase.test_high_severity_bowl_not_rejected) ... 
  test_high_severity_bowl_not_rejected (tests.test_kintsugi.KintsugiTestCase.test_high_severity_bowl_not_rejected) (mode='ribbon', seed=0) ... ERROR
  test_high_severity_bowl_not_rejected (tests.test_kintsugi.KintsugiTestCase.test_high_severity_bowl_not_rejected) (mode='ribbon', seed=2) ... ERROR
  test_high_severity_bowl_not_rejected (tests.test_kintsugi.KintsugiTestCase.test_high_severity_bowl_not_rejected) (mode='ribbon', seed=4) ... ERROR
  test_high_severity_bowl_not_rejected (tests.test_kintsugi.KintsugiTestCase.test_high_severity_bowl_not_rejected) (mode='vein', seed=0) ... ERROR
  test_high_severity_bowl_not_rejected (tests.test_kintsugi.KintsugiTestCase.test_high_severity_bowl_not_rejected) (mode='vein', seed=2) ... ERROR
  test_high_severity_bowl_not_rejected (tests.test_kintsugi.KintsugiTestCase.test_high_severity_bowl_not_rejected) (mode='vein', seed=4) ... ERROR
test_voronoi_ridges_do_not_cross (tests.test_kintsugi.KintsugiTestCase.test_voronoi_ridges_do_not_cross) ... FAIL
test_junctions_connected (tests.test_kintsugi.KintsugiTestCase.test_junctions_connected) ... FAIL
test_vein_cutter_no_kissing (tests.test_kintsugi.KintsugiTestCase.test_vein_cutter_no_kissing) ... 
  test_vein_cutter_no_kissing (tests.test_kintsugi.KintsugiTestCase.test_vein_cutter_no_kissing) (seed=0) ... ERROR
  test_vein_cutter_no_kissing (tests.test_kintsugi.KintsugiTestCase.test_vein_cutter_no_kissing) (seed=1) ... ERROR
  test_vein_cutter_no_kissing (tests.test_kintsugi.KintsugiTestCase.test_vein_cutter_no_kissing) (seed=5) ... ERROR
test_debris_swap_no_new_bad_edges (tests.test_kintsugi.KintsugiTestCase.test_debris_swap_no_new_bad_edges) ... 
  test_debris_swap_no_new_bad_edges (tests.test_kintsugi.KintsugiTestCase.test_debris_swap_no_new_bad_edges) (seed=0) ... ERROR
  test_debris_swap_no_new_bad_edges (tests.test_kintsugi.KintsugiTestCase.test_debris_swap_no_new_bad_edges) (seed=1) ... ERROR
  test_debris_swap_no_new_bad_edges (tests.test_kintsugi.KintsugiTestCase.test_debris_swap_no_new_bad_edges) (seed=2) ... ERROR
test_roundtrip_guard_raises_and_writes_nothing (tests.test_kintsugi.KintsugiTestCase.test_roundtrip_guard_raises_and_writes_nothing) ... ERROR
test_api_validate_ok (tests.test_web_api.WebApiTestCase.test_api_validate_ok) ... FAIL
test_api_validate_open_mesh (tests.test_web_api.WebApiTestCase.test_api_validate_open_mesh) ... FAIL
test_api_upload_too_large (tests.test_web_api.WebApiTestCase.test_api_upload_too_large) ... FAIL
test_job_retention (tests.test_web_api.WebApiTestCase.test_job_retention) ... FAIL

======================================================================
ERROR: test_seed_sweep_watertight (tests.test_kintsugi.KintsugiTestCase.test_seed_sweep_watertight) (R=0.0, mode='ribbon', seed=0)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 556, in test_seed_sweep_watertight
    result = kintsugi.generate_kintsugi_mesh(
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/node/global-sandbox/projects/wax-robot/kintsugi.py", line 903, in generate_kintsugi_mesh
    projected_paths, miss_fraction = project_crack_paths(
                                     ^^^^^^^^^^^^^^^^^^^^
  File "/home/node/global-sandbox/projects/wax-robot/kintsugi.py", line 562, in project_crack_paths
    raise ValueError(
ValueError: The input is not a vessel that the cylindrical parameterisation supports: 6.0% of crack projection rays missed the mesh (limit 5%)

======================================================================
ERROR: test_seed_sweep_watertight (tests.test_kintsugi.KintsugiTestCase.test_seed_sweep_watertight) (R=0.0, mode='ribbon', seed=2)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 556, in test_seed_sweep_watertight
    result = kintsugi.generate_kintsugi_mesh(
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/node/global-sandbox/projects/wax-robot/kintsugi.py", line 903, in generate_kintsugi_mesh
    projected_paths, miss_fraction = project_crack_paths(
                                     ^^^^^^^^^^^^^^^^^^^^
  File "/home/node/global-sandbox/projects/wax-robot/kintsugi.py", line 562, in project_crack_paths
    raise ValueError(
ValueError: The input is not a vessel that the cylindrical parameterisation supports: 8.5% of crack projection rays missed the mesh (limit 5%)

======================================================================
ERROR: test_seed_sweep_watertight (tests.test_kintsugi.KintsugiTestCase.test_seed_sweep_watertight) (R=0.0, mode='vein', seed=0)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 556, in test_seed_sweep_watertight
    result = kintsugi.generate_kintsugi_mesh(
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/node/global-sandbox/projects/wax-robot/kintsugi.py", line 903, in generate_kintsugi_mesh
    projected_paths, miss_fraction = project_crack_paths(
                                     ^^^^^^^^^^^^^^^^^^^^
  File "/home/node/global-sandbox/projects/wax-robot/kintsugi.py", line 562, in project_crack_paths
    raise ValueError(
ValueError: The input is not a vessel that the cylindrical parameterisation supports: 6.0% of crack projection rays missed the mesh (limit 5%)

======================================================================
ERROR: test_seed_sweep_watertight (tests.test_kintsugi.KintsugiTestCase.test_seed_sweep_watertight) (R=0.0, mode='vein', seed=2)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 556, in test_seed_sweep_watertight
    result = kintsugi.generate_kintsugi_mesh(
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/node/global-sandbox/projects/wax-robot/kintsugi.py", line 903, in generate_kintsugi_mesh
    projected_paths, miss_fraction = project_crack_paths(
                                     ^^^^^^^^^^^^^^^^^^^^
  File "/home/node/global-sandbox/projects/wax-robot/kintsugi.py", line 562, in project_crack_paths
    raise ValueError(
ValueError: The input is not a vessel that the cylindrical parameterisation supports: 8.5% of crack projection rays missed the mesh (limit 5%)

======================================================================
ERROR: test_high_severity_bowl_not_rejected (tests.test_kintsugi.KintsugiTestCase.test_high_severity_bowl_not_rejected) (mode='ribbon', seed=0)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 574, in test_high_severity_bowl_not_rejected
    kintsugi.generate_kintsugi_mesh(
  File "/home/node/global-sandbox/projects/wax-robot/kintsugi.py", line 903, in generate_kintsugi_mesh
    projected_paths, miss_fraction = project_crack_paths(
                                     ^^^^^^^^^^^^^^^^^^^^
  File "/home/node/global-sandbox/projects/wax-robot/kintsugi.py", line 562, in project_crack_paths
    raise ValueError(
ValueError: The input is not a vessel that the cylindrical parameterisation supports: 6.0% of crack projection rays missed the mesh (limit 5%)

======================================================================
ERROR: test_high_severity_bowl_not_rejected (tests.test_kintsugi.KintsugiTestCase.test_high_severity_bowl_not_rejected) (mode='ribbon', seed=2)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 574, in test_high_severity_bowl_not_rejected
    kintsugi.generate_kintsugi_mesh(
  File "/home/node/global-sandbox/projects/wax-robot/kintsugi.py", line 903, in generate_kintsugi_mesh
    projected_paths, miss_fraction = project_crack_paths(
                                     ^^^^^^^^^^^^^^^^^^^^
  File "/home/node/global-sandbox/projects/wax-robot/kintsugi.py", line 562, in project_crack_paths
    raise ValueError(
ValueError: The input is not a vessel that the cylindrical parameterisation supports: 8.5% of crack projection rays missed the mesh (limit 5%)

======================================================================
ERROR: test_high_severity_bowl_not_rejected (tests.test_kintsugi.KintsugiTestCase.test_high_severity_bowl_not_rejected) (mode='ribbon', seed=4)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 574, in test_high_severity_bowl_not_rejected
    kintsugi.generate_kintsugi_mesh(
  File "/home/node/global-sandbox/projects/wax-robot/kintsugi.py", line 903, in generate_kintsugi_mesh
    projected_paths, miss_fraction = project_crack_paths(
                                     ^^^^^^^^^^^^^^^^^^^^
  File "/home/node/global-sandbox/projects/wax-robot/kintsugi.py", line 562, in project_crack_paths
    raise ValueError(
ValueError: The input is not a vessel that the cylindrical parameterisation supports: 6.7% of crack projection rays missed the mesh (limit 5%)

======================================================================
ERROR: test_high_severity_bowl_not_rejected (tests.test_kintsugi.KintsugiTestCase.test_high_severity_bowl_not_rejected) (mode='vein', seed=0)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 574, in test_high_severity_bowl_not_rejected
    kintsugi.generate_kintsugi_mesh(
  File "/home/node/global-sandbox/projects/wax-robot/kintsugi.py", line 903, in generate_kintsugi_mesh
    projected_paths, miss_fraction = project_crack_paths(
                                     ^^^^^^^^^^^^^^^^^^^^
  File "/home/node/global-sandbox/projects/wax-robot/kintsugi.py", line 562, in project_crack_paths
    raise ValueError(
ValueError: The input is not a vessel that the cylindrical parameterisation supports: 6.0% of crack projection rays missed the mesh (limit 5%)

======================================================================
ERROR: test_high_severity_bowl_not_rejected (tests.test_kintsugi.KintsugiTestCase.test_high_severity_bowl_not_rejected) (mode='vein', seed=2)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 574, in test_high_severity_bowl_not_rejected
    kintsugi.generate_kintsugi_mesh(
  File "/home/node/global-sandbox/projects/wax-robot/kintsugi.py", line 903, in generate_kintsugi_mesh
    projected_paths, miss_fraction = project_crack_paths(
                                     ^^^^^^^^^^^^^^^^^^^^
  File "/home/node/global-sandbox/projects/wax-robot/kintsugi.py", line 562, in project_crack_paths
    raise ValueError(
ValueError: The input is not a vessel that the cylindrical parameterisation supports: 8.5% of crack projection rays missed the mesh (limit 5%)

======================================================================
ERROR: test_high_severity_bowl_not_rejected (tests.test_kintsugi.KintsugiTestCase.test_high_severity_bowl_not_rejected) (mode='vein', seed=4)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 574, in test_high_severity_bowl_not_rejected
    kintsugi.generate_kintsugi_mesh(
  File "/home/node/global-sandbox/projects/wax-robot/kintsugi.py", line 903, in generate_kintsugi_mesh
    projected_paths, miss_fraction = project_crack_paths(
                                     ^^^^^^^^^^^^^^^^^^^^
  File "/home/node/global-sandbox/projects/wax-robot/kintsugi.py", line 562, in project_crack_paths
    raise ValueError(
ValueError: The input is not a vessel that the cylindrical parameterisation supports: 6.7% of crack projection rays missed the mesh (limit 5%)

======================================================================
ERROR: test_vein_cutter_no_kissing (tests.test_kintsugi.KintsugiTestCase.test_vein_cutter_no_kissing) (seed=0)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 640, in test_vein_cutter_no_kissing
    cutter = kintsugi.build_vein_cutter(
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^
TypeError: build_vein_cutter() takes 2 positional arguments but 3 were given

======================================================================
ERROR: test_vein_cutter_no_kissing (tests.test_kintsugi.KintsugiTestCase.test_vein_cutter_no_kissing) (seed=1)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 640, in test_vein_cutter_no_kissing
    cutter = kintsugi.build_vein_cutter(
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^
TypeError: build_vein_cutter() takes 2 positional arguments but 3 were given

======================================================================
ERROR: test_vein_cutter_no_kissing (tests.test_kintsugi.KintsugiTestCase.test_vein_cutter_no_kissing) (seed=5)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 640, in test_vein_cutter_no_kissing
    cutter = kintsugi.build_vein_cutter(
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^
TypeError: build_vein_cutter() takes 2 positional arguments but 3 were given

======================================================================
ERROR: test_debris_swap_no_new_bad_edges (tests.test_kintsugi.KintsugiTestCase.test_debris_swap_no_new_bad_edges) (seed=0)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 672, in test_debris_swap_no_new_bad_edges
    cutter = kintsugi.build_ribbon_cutter(
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
TypeError: build_ribbon_cutter() takes 2 positional arguments but 3 were given

======================================================================
ERROR: test_debris_swap_no_new_bad_edges (tests.test_kintsugi.KintsugiTestCase.test_debris_swap_no_new_bad_edges) (seed=1)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 672, in test_debris_swap_no_new_bad_edges
    cutter = kintsugi.build_ribbon_cutter(
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
TypeError: build_ribbon_cutter() takes 2 positional arguments but 3 were given

======================================================================
ERROR: test_debris_swap_no_new_bad_edges (tests.test_kintsugi.KintsugiTestCase.test_debris_swap_no_new_bad_edges) (seed=2)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 672, in test_debris_swap_no_new_bad_edges
    cutter = kintsugi.build_ribbon_cutter(
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
TypeError: build_ribbon_cutter() takes 2 positional arguments but 3 were given

======================================================================
ERROR: test_roundtrip_guard_raises_and_writes_nothing (tests.test_kintsugi.KintsugiTestCase.test_roundtrip_guard_raises_and_writes_nothing)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 707, in test_roundtrip_guard_raises_and_writes_nothing
    kintsugi.generate_kintsugi_mesh(
  File "/home/node/global-sandbox/projects/wax-robot/kintsugi.py", line 913, in generate_kintsugi_mesh
    cutter = build_ribbon_cutter(projected_paths, params["W"])
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
TypeError: KintsugiTestCase.test_roundtrip_guard_raises_and_writes_nothing.<locals>.kissing_cutter() missing 1 required positional argument: 'rng'

======================================================================
FAIL: test_seed_sweep_watertight (tests.test_kintsugi.KintsugiTestCase.test_seed_sweep_watertight) (R=0.0, mode='ribbon', seed=1)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 561, in test_seed_sweep_watertight
    self.assertTrue(mesh.is_watertight, f"{key} not watertight")
AssertionError: False is not true : gold_path not watertight

======================================================================
FAIL: test_seed_sweep_watertight (tests.test_kintsugi.KintsugiTestCase.test_seed_sweep_watertight) (R=0.0, mode='ribbon', seed=3)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 561, in test_seed_sweep_watertight
    self.assertTrue(mesh.is_watertight, f"{key} not watertight")
AssertionError: False is not true : ceramic_path not watertight

======================================================================
FAIL: test_seed_sweep_watertight (tests.test_kintsugi.KintsugiTestCase.test_seed_sweep_watertight) (R=0.0, mode='vein', seed=1)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 561, in test_seed_sweep_watertight
    self.assertTrue(mesh.is_watertight, f"{key} not watertight")
AssertionError: False is not true : ceramic_path not watertight

======================================================================
FAIL: test_seed_sweep_watertight (tests.test_kintsugi.KintsugiTestCase.test_seed_sweep_watertight) (R=0.0, mode='vein', seed=3)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 561, in test_seed_sweep_watertight
    self.assertTrue(mesh.is_watertight, f"{key} not watertight")
AssertionError: False is not true : ceramic_path not watertight

======================================================================
FAIL: test_seed_sweep_watertight (tests.test_kintsugi.KintsugiTestCase.test_seed_sweep_watertight) (R=0.2, mode='ribbon', seed=0)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 561, in test_seed_sweep_watertight
    self.assertTrue(mesh.is_watertight, f"{key} not watertight")
AssertionError: False is not true : ceramic_path not watertight

======================================================================
FAIL: test_seed_sweep_watertight (tests.test_kintsugi.KintsugiTestCase.test_seed_sweep_watertight) (R=0.2, mode='ribbon', seed=1)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 561, in test_seed_sweep_watertight
    self.assertTrue(mesh.is_watertight, f"{key} not watertight")
AssertionError: False is not true : gold_path not watertight

======================================================================
FAIL: test_seed_sweep_watertight (tests.test_kintsugi.KintsugiTestCase.test_seed_sweep_watertight) (R=0.2, mode='ribbon', seed=2)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 561, in test_seed_sweep_watertight
    self.assertTrue(mesh.is_watertight, f"{key} not watertight")
AssertionError: False is not true : gold_path not watertight

======================================================================
FAIL: test_seed_sweep_watertight (tests.test_kintsugi.KintsugiTestCase.test_seed_sweep_watertight) (R=0.2, mode='ribbon', seed=3)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 561, in test_seed_sweep_watertight
    self.assertTrue(mesh.is_watertight, f"{key} not watertight")
AssertionError: False is not true : gold_path not watertight

======================================================================
FAIL: test_seed_sweep_watertight (tests.test_kintsugi.KintsugiTestCase.test_seed_sweep_watertight) (R=0.2, mode='vein', seed=0)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 561, in test_seed_sweep_watertight
    self.assertTrue(mesh.is_watertight, f"{key} not watertight")
AssertionError: False is not true : ceramic_path not watertight

======================================================================
FAIL: test_seed_sweep_watertight (tests.test_kintsugi.KintsugiTestCase.test_seed_sweep_watertight) (R=0.2, mode='vein', seed=1)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 561, in test_seed_sweep_watertight
    self.assertTrue(mesh.is_watertight, f"{key} not watertight")
AssertionError: False is not true : ceramic_path not watertight

======================================================================
FAIL: test_seed_sweep_watertight (tests.test_kintsugi.KintsugiTestCase.test_seed_sweep_watertight) (R=0.2, mode='vein', seed=2)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 561, in test_seed_sweep_watertight
    self.assertTrue(mesh.is_watertight, f"{key} not watertight")
AssertionError: False is not true : gold_path not watertight

======================================================================
FAIL: test_seed_sweep_watertight (tests.test_kintsugi.KintsugiTestCase.test_seed_sweep_watertight) (R=0.2, mode='vein', seed=3)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 561, in test_seed_sweep_watertight
    self.assertTrue(mesh.is_watertight, f"{key} not watertight")
AssertionError: False is not true : gold_path not watertight

======================================================================
FAIL: test_voronoi_ridges_do_not_cross (tests.test_kintsugi.KintsugiTestCase.test_voronoi_ridges_do_not_cross)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 589, in test_voronoi_ridges_do_not_cross
    self.assertIsNone(
AssertionError: (3, 10, 4, 6) is not None : seed 0 ridge segments cross: (3, 10, 4, 6)

======================================================================
FAIL: test_junctions_connected (tests.test_kintsugi.KintsugiTestCase.test_junctions_connected)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 621, in test_junctions_connected
    self.assertEqual(
AssertionError: 16 != 0 : seed 0: 16 dangling junctions

======================================================================
FAIL: test_api_validate_ok (tests.test_web_api.WebApiTestCase.test_api_validate_ok)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_web_api.py", line 104, in test_api_validate_ok
    self.assertEqual(response.status_code, 200, response.text)
AssertionError: 405 != 200 : {"detail":"Method Not Allowed"}

======================================================================
FAIL: test_api_validate_open_mesh (tests.test_web_api.WebApiTestCase.test_api_validate_open_mesh)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_web_api.py", line 121, in test_api_validate_open_mesh
    self.assertEqual(response.status_code, 200, response.text)
AssertionError: 405 != 200 : {"detail":"Method Not Allowed"}

======================================================================
FAIL: test_api_upload_too_large (tests.test_web_api.WebApiTestCase.test_api_upload_too_large)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_web_api.py", line 139, in test_api_upload_too_large
    self.assertEqual(response.status_code, 413, response.text)
AssertionError: 400 != 413 : {"detail":"No triangle geometry found in /home/node/global-sandbox/projects/wax-robot/output/web/e0a2c32d34ab/input.stl"}

======================================================================
FAIL: test_job_retention (tests.test_web_api.WebApiTestCase.test_job_retention)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_web_api.py", line 162, in test_job_retention
    self.assertEqual(len(job_dirs), 2)
AssertionError: 3 != 2

----------------------------------------------------------------------
Ran 11 tests in 39.113s

FAILED (failures=18, errors=17)
```

#### 7.2 — Baseline sweep and renders

Copied the independent verification tools into `tools/sweep.py` and
`tools/render.py`. `tools/sweep.py` now accepts `--presets`, `--ratios`,
`--modes`, `--seeds` and `--output`; `tools/render.py` defaults to
`output/verification/renders`.

Baseline sweep:

```bash
.venv/bin/python tools/sweep.py --presets tea_bowl vase --ratios 0 0.05 0.2 0.5 0.9 0.99 --modes ribbon vein --seeds 0 1 2 3 4 5
```

Verbatim result:

```json
{
  "total": 144,
  "counts": {
    "rejected": 12,
    "nonwatertight": 79,
    "ok": 53
  },
  "completed": 132,
  "clean": 53,
  "nonwatertight": 79,
  "false_rejections": 12,
  "errors": 0
}
Wrote /home/node/global-sandbox/projects/wax-robot/output/verification/sweep.json
```

Baseline renders:

```bash
.venv/bin/python tools/render.py . output/verification/renders
```

Verbatim result:

```text
tea_bowl_R0.2_ribbon_s7 | watertight | bad edges=0 cracks=17
tea_bowl_R0.2_ribbon_s0 | NOT watertight | bad edges=54 cracks=21
tea_bowl_R0.2_vein_s1 | NOT watertight | bad edges=22 cracks=23
tea_bowl_R0.7_vein_s3 | watertight | bad edges=0 cracks=6
vase_R0.2_ribbon_s5 | NOT watertight | bad edges=4 cracks=28
tea_bowl_R0.0_ribbon_s1 | NOT watertight | bad edges=10 cracks=30
```

Generated renders: `graph_noise_off.png`, `graph_noise_on.png`, and
`<case>_side.png`, `<case>_top.png`, `<case>_gold.png` for the six render cases.

#### 7.3 — F2 (Voronoi rays) and F4 (junction jitter)

- **Finding:** F2 — unbounded ridges were extended as full lines and the
  periodic tiling also produced extra wrapping copies, so ridge segments
  crossed. F4 — canonicalisation swapped the "on bottom/top" flags and the
  jitter moved a random endpoint rather than the endpoint actually on the
  band edge, detaching Voronoi junctions.
- **Root cause:** `_ridge_segment` returned `finite ± direction*span`; the
  `at_bottom`/`at_top` flags were swapped when endpoints were reordered, and
  jitter was applied to either endpoint without checking which one lay on the
  band edge.
- **Change:** `kintsugi.py:357-388` (`_ridge_segment`) now returns a single ray
  from the finite vertex, oriented away from the seed-pair midpoint. Rays whose
  seed pair has no central-tile seed are discarded, and rays use one periodic
  representative; finite ridges keep all periodic fragments so seam junctions
  remain connected. `kintsugi.py:444-505` (`generate_crack_paths`) keeps the
  finite-ridge seam fragments and jitters only endpoints within `1e-9` of
  `z_min`/`z_max`.
- **Before:** `test_voronoi_ridges_do_not_cross` failed at seed 0 with crossing
  `(3, 10, 4, 6)`; `test_junctions_connected` reported `16 dangling junctions`
  at seed 0 (handoff metric: 100/286 interior ends).
- **After:** seeds 0–9 show no crossings; seeds 0–19 show 0 dangling interior
  junctions.

Verbatim result after the fix:

```text
test_voronoi_ridges_do_not_cross (tests.test_kintsugi.KintsugiTestCase.test_voronoi_ridges_do_not_cross) ... ok
test_junctions_connected (tests.test_kintsugi.KintsugiTestCase.test_junctions_connected) ... ok

----------------------------------------------------------------------
Ran 2 tests in 13.787s

OK
```

#### 7.4 — F3 (z clamp, in-band miss accounting) and F8 (single-hit wall rule)

- **Finding:** F3 — valid bowls at R∈{0, 0.05} were rejected as "not a
  vessel" in 12/144 runs because noise/jitter pushed points above the rim or
  below the base and those misses counted against the 5% envelope. F8 — a
  one-hit ray (origin inside the solid base) used a hard-coded `t = 1.0`,
  producing 2 mm partial cuts.
- **Root cause:** all projection misses counted towards the envelope, including
  out-of-band terminal jitter; perturbed points were never clamped to the mesh
  Z extent; and the single-hit case had no physical wall rule.
- **Change:** `kintsugi.py:138-139` adds `z_mesh_lo`/`z_mesh_hi` to the
  parameter table. `kintsugi.py:522-533` clamps perturbed `z` into
  `[z_lo + 0.5W, z_hi − 0.5W]`. `kintsugi.py:550-644`
  (`project_crack_paths`) splits on every miss but counts only in-band misses
  towards the 5% envelope, returns both fractions, and sets `t` for a
  single-hit ray to the distance to the outer hit capped at `0.5*rbar`; the
  number of single-hit points is recorded in `params["single_hit_points"]`.
- **Before:** 12/144 baseline runs rejected; seeds 0/2/4 at R=0 failed with
  6.0%/8.5%/6.7% misses.
- **After:** no rejection across R=0, seeds 0–5, both modes.

Verbatim result after the fix:

```text
test_high_severity_bowl_not_rejected (tests.test_kintsugi.KintsugiTestCase.test_high_severity_bowl_not_rejected) ... ok

----------------------------------------------------------------------
Ran 1 test in 10.456s

OK
```

#### 7.5 — F1a (seeded vein-sphere rotation)

- **Finding:** every vein sphere used the same axis-aligned tessellation, so
  neighbours and junction spheres shared exactly coincident vertices and their
  union kissed.
- **Root cause:** identical sphere meshes translated along a path are
  vertex-aligned; the STL position merge turns the shared vertices into edges
  used by four or more faces.
- **Change:** `kintsugi.py:671-715` (`build_vein_cutter`) takes a dedicated
  cutter RNG, rotates each unique sphere by seeded Euler angles before
  translation, and caches spheres by rounded centre so shared junction points
  reuse one primitive instead of creating near-coincident duplicates. The
  caller uses the sub-seed `[seed, 0xC07]` at `kintsugi.py:1031`.
- **Before:** handoff experiment had 6/34/36 bad edges for seeds 0/1/5; with
  rotation but before centre caching, seed 0 still had 2 cutter bad edges.
- **After:** cutter, `M−C` and `M∩C` all have 0 bad edges for seeds 0, 1, 5.

Verbatim result after the fix:

```text
test_vein_cutter_no_kissing (tests.test_kintsugi.KintsugiTestCase.test_vein_cutter_no_kissing) ... ok

----------------------------------------------------------------------
Ran 1 test in 3.600s

OK
```

#### 7.6 — F1b (ribbon kissing edges: investigation and fix)

- **Finding:** ribbon CSG contained kissing edges even when vein mode was
  clean. Seed 0 at R=0.2 had cutter 32 bad edges (31 four-face, 1 six-face)
  and both `M−C` and `M∩C` had 6.
- **Investigation:** staged counts on cutter alone, `M−C` and `M∩C` located
  the artifacts at `r ≈ 41.48` and `r ≈ 45.48`, i.e. the inner and outer faces
  of the through-wall slabs, with `z` values spanning 22.61–24.49. Translating
  the cutter by 1e-3 or 1e-2 mm did not change the count. The floor/base
  coplanarity candidate and the F8 single-hit fallback were therefore not the
  controlling cause after F8 was fixed.
- **Root cause (recorded in `research.md` before the fix):** every slab has the
  same through-wall depth `t+1` and the same surface offset, so consecutive
  hulls have coplanar overlapping inner/outer faces. Manifold's union is valid,
  but binary-STL position merging turns the coincident face boundaries into
  edges used by 4–6 faces.
- **Change:** `kintsugi.py:720-788` (`build_ribbon_cutter`) now takes the
  cutter RNG, rotates each slab by a seeded ±0.5° about its own normal, and
  applies ≤`1e-3·W` centre/depth jitter. `generate_kintsugi_mesh` passes the
  same `[seed, 0xC07]` sub-seed used by vein mode.
- **Before:** seed 0 cutter 32, `M−C` 6, `M∩C` 6.
- **After:** seed 0 cutter 2, `M−C` 0, `M∩C` 0; seeds 1/2/5 have 0 for all
  three outputs (seed 1/5 cutter 0, seed 2 cutter 2).

Verbatim staged result after the fix:

```text
seed=0 cutter=2 M-C=0 M^C=0
seed=1 cutter=0 M-C=0 M^C=0
seed=2 cutter=2 M-C=0 M^C=0
seed=5 cutter=0 M-C=0 M^C=0
```

#### 7.7 — F1c (face-sharing debris merge)

- **Finding:** the debris swap unioned every sub-1 mm³ crumb into the other
  material, even when it touched that material only along an edge or point,
  creating new kissing edges. Seeds 1 and 2 ribbon were clean before the swap
  and non-clean after it.
- **Root cause:** union alone does not distinguish a shared face region from a
  mere edge/point contact.
- **Change:** `kintsugi.py:803-859` adds `_shares_face_region`, which compares
  `target.decompose()` before and after `target + crumb`; `swap_debris` moves a
  crumb only when that union reduces the destination component count. Crumbs
  that only touch at an edge/point remain in their original material and are
  counted in `stats["debris_unmoved"]`. `generate_kintsugi_mesh` records the
  count in `params` and the result dict.
- **Before:** handoff staged evidence showed new post-swap bad edges for seeds
  1 and 2 that were clean pre-swap.
- **After:** post-swap bad edges ≤ pre-swap bad edges, both 0 for seeds 0–2;
  seed 0 had 1 crumb left in place (`debris_unmoved=1`). Volume remains within
  `1e-6`.

Verbatim result after the fix:

```text
test_debris_swap_no_new_bad_edges (tests.test_kintsugi.KintsugiTestCase.test_debris_swap_no_new_bad_edges) ... ok
test_debris_swap (tests.test_kintsugi.KintsugiTestCase.test_debris_swap) ... ok
test_volume_smoke (tests.test_kintsugi.KintsugiTestCase.test_volume_smoke) ... ok

----------------------------------------------------------------------
Ran 3 tests in 2.402s

OK
```

Current staged numbers (pre-swap / old unconditional union / new face-sharing
swap):

```text
seed=0 pre=0 old_swap=0 new_swap=0 unmoved=1
seed=1 pre=0 old_swap=0 new_swap=0 unmoved=0
seed=2 pre=0 old_swap=0 new_swap=0 unmoved=0
```

#### 7.8 — F5 removal and F1 round-trip guard

- **Finding:** `_export_trimesh` deleted faces with area ≤1e-12, which could
  open holes and masked the real kissing geometry; exports had no guard
  against a non-watertight disk round-trip.
- **Change:** `kintsugi.py:862-864` makes `_export_trimesh` a pure conversion
  (no face deletion). `kintsugi.py:1085-1131` adds the round-trip guard after
  the debris swap and before writing: both outputs must have 0 edges used by
  ≠2 faces after binary-STL reload. On failure it rebuilds only the cutter,
  up to 3 attempts, using `np.random.default_rng([seed, 0xC07, attempt])`;
  both booleans always use the same cutter. If all attempts fail it raises
  `RuntimeError` before any file is written. `cutter_attempts` is recorded in
  the result and parameter table.
- **Before:** baseline 79/132 completed sweep runs were non-watertight; the
  seed-sweep test had failures in 16/16 combinations; no guard existed.
- **After:** the guard test raises `RuntimeError` with an empty output dir;
  `test_seed_sweep_watertight` passes all 16 combinations.

Guard test:

```text
test_roundtrip_guard_raises_and_writes_nothing (tests.test_kintsugi.KintsugiTestCase.test_roundtrip_guard_raises_and_writes_nothing) ... ok

----------------------------------------------------------------------
Ran 1 test in 0.090s

OK
```

Seed sweep test:

```text
test_seed_sweep_watertight (tests.test_kintsugi.KintsugiTestCase.test_seed_sweep_watertight) ... ok

----------------------------------------------------------------------
Ran 1 test in 20.301s

OK
```

#### 7.9 — F10 (duplicate radial probe)

- **Finding:** `_radial_probe` ran twice per job: once in
  `validate_and_load_mesh` and again in `compute_parameters`.
- **Change:** `kintsugi.py:263-279` adds the iterable `MeshValidation`
  dataclass carrying `mesh`, `manifold` and the probe result.
  `validate_and_load_mesh` returns it; `compute_parameters` accepts an
  optional `probe` dict (`kintsugi.py:81-125`) and reuses it; the top-level
  generator passes `validation.probe` (`kintsugi.py:1047-1054`). Existing
  two-value unpacking still works because the dataclass yields
  `(mesh, manifold)`.
- **Before:** one redundant 9×48 radial probe per job.
- **After:** one probe per job; determinism remains byte-identical.

Verbatim tests:

```text
test_parameter_table (tests.test_kintsugi.KintsugiTestCase.test_parameter_table) ... ok
test_wealthy_case (tests.test_kintsugi.KintsugiTestCase.test_wealthy_case) ... ok
test_determinism (tests.test_kintsugi.KintsugiTestCase.test_determinism) ... ok

----------------------------------------------------------------------
Ran 3 tests in 3.274s

OK
```

Cross-process MD5 comparison:

```text
3cfdf6d638dc8e7d4068b9bd62db22e4  output/determinism_c/ceramic_body.stl
3cfdf6d638dc8e7d4068b9bd62db22e4  output/determinism_d/ceramic_body.stl
2b4537b423f90c25eac47c25c80005b0  output/determinism_c/gold_seams.stl
2b4537b423f90c25eac47c25c80005b0  output/determinism_d/gold_seams.stl
ca9ccc7b53bd72baecae27963b351022  output/determinism_c/kintsugi_assembly.3mf
ca9ccc7b53bd72baecae27963b351022  output/determinism_d/kintsugi_assembly.3mf
```

#### 7.10 — F6 (`/api/validate`, viewer status) and F7 (upload cap, retention)

- **Finding:** F6 — the GUI only parsed uploads in the browser and deferred
  watertightness to fracture time. F7 — job directories were never cleaned and
  uploads had no size cap.
- **Change:** `web_app.py:25` adds a 50 MB cap; `web_app.py:48-103` adds
  `_job_limits`, `_prune_jobs` (TTL `KINTSUGI_JOB_TTL_S`, default 3600 s;
  count `KINTSUGI_MAX_JOBS`, default 50) and streaming `_save_upload` with
  413. `web_app.py:122-155` adds `POST /api/validate` using a temporary
  directory and `validate_and_load_mesh`; `web_app.py:169` prunes jobs when a
  new job starts. `static/viewer.js:332-357` calls `/api/validate` after a
  custom parse, shows `Watertight ✓` or `Not a valid closed solid: …`, and
  disables the fracture button while invalid; `static/xp.css:603-609` uses the
  existing success/error tokens for the status text.
- **Before:** `/api/validate` returned 405, a 51 MB upload returned 400
  (parse failure), and three jobs left three directories with
  `KINTSUGI_MAX_JOBS=2`.
- **After:** all seven web API tests pass, including validate-ok/open-mesh,
  51 MB → 413, and three jobs → two directories.

Verbatim result after the fix:

```text
/home/node/global-sandbox/projects/wax-robot/.venv/lib/python3.11/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
  from starlette.testclient import TestClient as TestClient  # noqa
test_api_fracture_success (tests.test_web_api.WebApiTestCase.test_api_fracture_success) ... ok
test_api_fracture_wealthy (tests.test_web_api.WebApiTestCase.test_api_fracture_wealthy) ... ok
test_api_presets (tests.test_web_api.WebApiTestCase.test_api_presets) ... ok
test_api_upload_too_large (tests.test_web_api.WebApiTestCase.test_api_upload_too_large) ... ok
test_api_validate_ok (tests.test_web_api.WebApiTestCase.test_api_validate_ok) ... ok
test_api_validate_open_mesh (tests.test_web_api.WebApiTestCase.test_api_validate_open_mesh) ... ok
test_job_retention (tests.test_web_api.WebApiTestCase.test_job_retention) ... ok

----------------------------------------------------------------------
Ran 7 tests in 0.991s

OK
```

#### 7.11 — Specs, architecture and tests documentation

- Added the remediation scenarios to
  `specs/mesh-fracture-engine/spec.md` (rays, z clamp, junction jitter,
  in-band misses, single-hit wall thickness, cutter de-alignment).
- Added the debris face-sharing and round-trip-guard/seed-robustness scenarios
  to `specs/multi-material-export/spec.md`, and updated the debris requirement
  wording to match the new rule.
- Added `/api/validate`, 50 MB upload cap and job-retention scenarios to
  `specs/retro-web-gui/spec.md`.
- `architecture.md` now has Decision 7 (cutter de-alignment and round-trip
  guard), the corrected Decision 4 debris rule, a renumbered Decision 8 for
  the GUI, and the guard node in the mermaid diagram.
- `tests.md` documents the new engine/API tests, the ribbon-thickness rationale,
  and the sweep/render commands.

`openspec validate kintsugi-mesh-fracture --strict --json`:

```json
{
  "items": [
    { "id": "kintsugi-mesh-fracture", "type": "change", "valid": true, "issues": [] }
  ],
  "summary": { "totals": { "items": 1, "passed": 1, "failed": 0 } }
}
```

#### 7.12 — Final suite, 144-run sweep and renders

- **Tests:** 26/26 pass.
- **Sweep:** 144/144 clean; 0 non-watertight, 0 false rejections, 0 errors.
  The cutter guard succeeded on attempt 1 in 135 runs and attempt 2 in 9 runs;
  no run needed a third attempt. `debris_unmoved` totalled 60 across the sweep.
- **Renders:** all six cases watertight with 0 bad edges; 20 PNGs
  regenerated. Baseline (pre-fix) renders are preserved in
  `output/verification/renders_baseline/`; final renders are in
  `output/verification/renders/`. The seed-0 side view changes from a red
  non-watertight title bar with red marker squares to a green watertight title
  bar with no markers.
- **Sample generator:** regenerated from the current engine (not hand-edited).
- **Web GUI:** valid and invalid custom uploads exercise `/api/validate`;
  invalid uploads show `Not a valid closed solid` and disable the fracture
  button; valid uploads show `Watertight ✓` and re-enable it. Preset switch,
  orbit, fracture and download still work with no console/page errors.

Before/after comparison:

| Metric | Baseline (7.2) | Final (7.12) |
|---|---|---|
| Completed sweep runs | 132 | 144 (# all attempted) |
| Clean runs | 53 | 144 |
| Non-watertight runs | 79 | 0 |
| False rejections | 12 | 0 |
| Engine errors | 0 | 0 |
| Test suite | 11 new tests failing (18 failures + 17 errors) | 26/26 pass |
| Render cases watertight | 1/6 | 6/6 |

Final test suite:

```text
/home/node/global-sandbox/projects/wax-robot/.venv/lib/python3.11/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
  from starlette.testclient import TestClient as TestClient  # noqa
test_3mf_structure (test_kintsugi.KintsugiTestCase.test_3mf_structure) ... ok
test_debris_swap (test_kintsugi.KintsugiTestCase.test_debris_swap) ... ok
test_debris_swap_no_new_bad_edges (test_kintsugi.KintsugiTestCase.test_debris_swap_no_new_bad_edges) ... ok
test_determinism (test_kintsugi.KintsugiTestCase.test_determinism) ... ok
test_high_severity_bowl_not_rejected (test_kintsugi.KintsugiTestCase.test_high_severity_bowl_not_rejected) ... ok
test_input_envelope_rejection (test_kintsugi.KintsugiTestCase.test_input_envelope_rejection) ... ok
test_input_validation (test_kintsugi.KintsugiTestCase.test_input_validation) ... ok
test_junctions_connected (test_kintsugi.KintsugiTestCase.test_junctions_connected) ... ok
test_parameter_table (test_kintsugi.KintsugiTestCase.test_parameter_table) ... ok
test_printable_channel_thickness (test_kintsugi.KintsugiTestCase.test_printable_channel_thickness) ... ok
test_ribbon_through_wall (test_kintsugi.KintsugiTestCase.test_ribbon_through_wall) ... ok
test_roundtrip_guard_raises_and_writes_nothing (test_kintsugi.KintsugiTestCase.test_roundtrip_guard_raises_and_writes_nothing) ... ok
test_seed_sweep_watertight (test_kintsugi.KintsugiTestCase.test_seed_sweep_watertight) ... ok
test_stl_disk_roundtrip (test_kintsugi.KintsugiTestCase.test_stl_disk_roundtrip) ... ok
test_vein_cutter_no_kissing (test_kintsugi.KintsugiTestCase.test_vein_cutter_no_kissing) ... ok
test_vein_depth (test_kintsugi.KintsugiTestCase.test_vein_depth) ... ok
test_volume_smoke (test_kintsugi.KintsugiTestCase.test_volume_smoke) ... ok
test_voronoi_ridges_do_not_cross (test_kintsugi.KintsugiTestCase.test_voronoi_ridges_do_not_cross) ... ok
test_wealthy_case (test_kintsugi.KintsugiTestCase.test_wealthy_case) ... ok
test_api_fracture_success (test_web_api.WebApiTestCase.test_api_fracture_success) ... ok
test_api_fracture_wealthy (test_web_api.WebApiTestCase.test_api_fracture_wealthy) ... ok
test_api_presets (test_web_api.WebApiTestCase.test_api_presets) ... ok
test_api_upload_too_large (test_web_api.WebApiTestCase.test_api_upload_too_large) ... ok
test_api_validate_ok (test_web_api.WebApiTestCase.test_api_validate_ok) ... ok
test_api_validate_open_mesh (test_web_api.WebApiTestCase.test_api_validate_open_mesh) ... ok
test_job_retention (test_web_api.WebApiTestCase.test_job_retention) ... ok

----------------------------------------------------------------------
Ran 26 tests in 63.125s

OK
```

Final sweep:

```json
{
  "total": 144,
  "counts": {
    "ok": 144
  },
  "completed": 144,
  "clean": 144,
  "nonwatertight": 0,
  "false_rejections": 0,
  "errors": 0,
  "cutter_attempts": {
    "1": 135,
    "2": 9
  },
  "debris_unmoved_total": 60
}
Wrote /home/node/global-sandbox/projects/wax-robot/output/verification/sweep.json
```

Final renders:

```text
tea_bowl_R0.2_ribbon_s7 | watertight | bad edges=0 cracks=11
tea_bowl_R0.2_ribbon_s0 | watertight | bad edges=0 cracks=14
tea_bowl_R0.2_vein_s1 | watertight | bad edges=0 cracks=13
tea_bowl_R0.7_vein_s3 | watertight | bad edges=0 cracks=4
vase_R0.2_ribbon_s5 | watertight | bad edges=0 cracks=17
tea_bowl_R0.0_ribbon_s1 | watertight | bad edges=0 cracks=21
```

Regenerated sample generator:

```text
Wrote parametric bowl fixture: output/bowl_input.stl

--- bowl_R1.0_ribbon ---
  cracks=  0  W=0.80 mm  H=12.00 mm
  volumes: ceramic=65775.66 mm^3  gold=0.00 mm^3
  triangles: ceramic=768  gold=0
  time: 0.03 s

--- bowl_R1.0_vein ---
  cracks=  0  W=0.80 mm  H=12.00 mm
  volumes: ceramic=65775.66 mm^3  gold=0.00 mm^3
  triangles: ceramic=768  gold=0
  time: 0.02 s

--- bowl_R0.7_ribbon ---
  cracks=  4  W=1.22 mm  H=26.40 mm
  volumes: ceramic=65121.89 mm^3  gold=653.76 mm^3
  triangles: ceramic=3,550  gold=2,766
  time: 0.29 s

--- bowl_R0.7_vein ---
  cracks=  4  W=1.22 mm  H=26.40 mm
  volumes: ceramic=65610.97 mm^3  gold=164.69 mm^3
  triangles: ceramic=10,152  gold=9,378
  time: 0.74 s

--- bowl_R0.2_ribbon ---
  cracks= 11  W=1.92 mm  H=50.40 mm
  volumes: ceramic=61859.47 mm^3  gold=3916.19 mm^3
  triangles: ceramic=7,418  gold=6,636
  time: 0.55 s

--- bowl_R0.2_vein ---
  cracks= 11  W=1.92 mm  H=50.40 mm
  volumes: ceramic=64410.33 mm^3  gold=1365.33 mm^3
  triangles: ceramic=22,556  gold=21,774
  time: 1.69 s

Summary: output/sample_summary.json
```

Final web GUI verification:

```text
INITIAL {
  "title": "Kintsugi Studio 2001",
  "font": "Tahoma, \"Segoe UI\", sans-serif",
  "titlebarBackground": "linear-gradient(to right, rgb(0, 88, 238), rgb(53, 147, 255) 85%, rgb(7, 42, 140))",
  "windowBackground": "rgb(236, 233, 216)",
  "canvas": {
    "width": 948,
    "height": 686
  },
  "presets": [
    "tea_bowl",
    "benchy",
    "vase"
  ]
}
INVALID_UPLOAD_STATUS Invalid model: Input mesh is not a valid closed solid: it must be a closed, orientable 2-manifold with positive volume and no boundary edges
INVALID_UPLOAD_MESH Faces: 767 | Parts: 1 | Not a valid closed solid: Input mesh is not a valid closed solid: it must be a closed, orientable 2-manifold with positive volume and no boundary edges
INVALID_FRACTURE_DISABLED True
VALID_UPLOAD_STATUS Ready · bowl_input.stl
VALID_UPLOAD_MESH Faces: 768 | Parts: 1 | Watertight ✓
VALID_FRACTURE_DISABLED False
PRESET_SWITCH Ready · Small Vase
ORBIT_SCREENSHOT_CHANGED True
FRACTURE_STATUS 13 cracks · gold 1739.3 mm³
FRACTURE_MESH Faces: 20,106 | Parts: 2 | Ceramic 25396.5 mm³ · Gold 1739.3 mm³
DOWNLOADS {
  "ceramic": "/outputs/bcd86297e2a0/ceramic_body.stl",
  "gold": "/outputs/bcd86297e2a0/gold_seams.stl",
  "three": "/outputs/bcd86297e2a0/kintsugi_assembly.3mf",
  "disabled": [
    false,
    false,
    false
  ]
}
DOWNLOAD_FILE ceramic_body.stl /tmp/playwright-artifacts-Jdjry2/f6b9aa69-1597-4712-aa7c-6a66e05b9fc8
ERRORS []
```

---

## 9. Remediation completion audit

### Executive summary & environment

The independent verification found that the original suite only exercised seed 7:
across 144 sweep runs, 53 were clean, 79 non-watertight, and 12 valid bowls were
falsely rejected. Three remediation rounds fixed the engine/UI/crack-graph
defects test-first, added the missing multi-seed guard, and ended with
**35/35 passing tests**, **144/144 tuning runs and 160/160 clean runs in both
out-of-sample sweeps**, **0 false rejections**, and **0 cutter retries**.
The crack-graph audit is 0 phantom / 0 crossings / 0.0% clamp-line points in
all four rows.

Environment: Python 3.11.2, NumPy 2.4.6, SciPy 1.17.1, trimesh 5.2.0,
manifold3d 3.5.4, FastAPI 0.162.0, rtree (test-only), headless Chromium via
Playwright.

### Scenario-to-evidence audit

| Specification scenario | Verifying test / evidence |
|---|---|
| Vessel of revolution inside envelope | `test_wealthy_case`, `test_seed_sweep_watertight`, 144-run sweep |
| Wrong units or scale | `test_input_envelope_rejection` (metre-scaled bowl) |
| Non-vessel geometry | `test_input_envelope_rejection` (two disjoint boxes) |
| Valid inequality metric | `test_parameter_table` (R=0.4 → N=6, W=1.64, H=0.68H_mesh) |
| Wealthy threshold | `test_wealthy_case` (R=1.0/1.5) |
| Negative metric | `test_input_validation` |
| Non-finite metric | `test_input_validation` (NaN, ±inf) |
| Pristine manifold STL loaded | `test_wealthy_case`, `test_seed_sweep_watertight` |
| Non-manifold or open input | `test_input_envelope_rejection` (one face removed) |
| Periodic Voronoi network | `test_crack_paths_lie_on_periodic_voronoi`, `test_junctions_connected`; audit phantom/crossing 0/200 | Met |
| Crack graph is planar | `test_crack_paths_lie_on_periodic_voronoi` (both presets, S=0.6/1.0, seeds 0–39); audit crossing seeds 0/200 in every row | Met |
| Band-edge terminations are not flat | `test_band_edge_terminals_are_ragged`; audit clamp-line 0.0% | Met |
| Noise perturbation keeps junctions connected | `test_junctions_connected` (seeds 0–19) |
| Radial projection takes exterior hit and wall thickness | `test_vein_depth`, `test_ribbon_through_wall`, sweep |
| Ray miss | `test_high_severity_bowl_not_rejected`, `test_seed_sweep_watertight`, 144-run sweep |
| Unbounded ridges are rays | `test_unbounded_rays_obey_voronoi_definition`, `test_ray_tiebreak_direction`; audit phantom/crossing 0/200 | Met |
| Perturbed points stay on the wall | `test_no_points_on_wall_limit_lines`, `test_high_severity_bowl_not_rejected`, `test_wall_range_clamp_keeps_gold_out_of_floor`; F3/F13/F15 logs | Met |
| Junction ends are never jittered | `test_junctions_connected` |
| Single-hit wall thickness | `params["single_hit_points"]`, `params["median_two_hit_wall"]`; `test_wall_range_clamp_keeps_gold_out_of_floor` and both sweeps |
| Vein cutter construction | `test_vein_cutter_no_kissing`, `test_vein_depth` |
| Ribbon through-wall cutter construction | `test_ribbon_through_wall` (depth > t−0.2) |
| Degenerate frame | exercised by `test_seed_sweep_watertight` and sweep |
| Cutter primitives are de-aligned | `test_vein_cutter_no_kissing`, `test_vein_no_retries_out_of_sample_cases`, `test_ribbon_no_retries_out_of_sample_cases`; F1b/F12 logs in 7.6/8.3 |
| Complementary volume partitioning | `test_volume_smoke` (pre- and post-swap) |
| Determinism | `test_determinism`; cross-process MD5 in 7.9 |
| Floating ceramic crumb | `test_debris_swap`, `test_debris_swap_no_new_bad_edges` |
| Gold debris at rim | `test_debris_swap`, `test_debris_swap_no_new_bad_edges` |
| Conservation after reassignment | `test_volume_smoke` |
| Crumbs merge only across a shared face | `test_debris_swap_no_new_bad_edges` |
| Isolated crumbs stay in place | seed 0 `debris_unmoved=1` in 7.7 staged numbers |
| Inequality fracture export | `test_stl_disk_roundtrip`, `test_seed_sweep_watertight`, 144-run sweep |
| Wealthy pass-through export | `test_wealthy_case` |
| Export sliver repair | `_stl_bad_edge_count`, `_collapse_edge`, `_repair_stl_slivers`; both sweeps, `test_ribbon_no_retries_out_of_sample_cases` |
| Round-trip guard | `test_roundtrip_guard_raises_and_writes_nothing`, `test_seed_sweep_watertight`, both sweeps |
| Seed robustness | `test_seed_sweep_watertight`; 144-run tuning sweep and 160-run out-of-sample sweep both 0 retries |
| Multi-material 3MF export | `test_3mf_structure` |
| Single-volume wealthy 3MF export | `test_wealthy_case` |
| Windows XP Luna visual design | Playwright computed styles + `output/verification/web_gui.png` |
| Interactive Three.js viewport | Playwright orbit screenshot change; no console/page errors |
| Preset model selection | Playwright preset switch to Small Vase |
| Custom file upload | Playwright invalid (`Not a valid closed solid`, button disabled) and valid (`Watertight ✓`, button enabled) uploads; `test_api_validate_ok/open_mesh` |
| Upload size cap | `test_api_upload_too_large` (51 MB → 413) |
| Job retention | `test_job_retention` (`KINTSUGI_MAX_JOBS=2`, three jobs → two dirs) |
| Triggering fracture computation | Playwright R=0.35 ribbon fracture; `test_api_fracture_success` |
| Wealthy parameter setting | `test_api_fracture_wealthy`; prior Playwright wealthy-label check in §4 |
| Multi-material 3MF download | Playwright download links + `test_api_fracture_success` asset GETs |
| Slicer import as one object with two parts | **Deferred (manual 6.3)**; structural 3MF audit in §3 |

### Nomenclature & code-symbol audit

| Symbol | Location | Meaning |
|---|---|---|
| `MeshValidation` | `kintsugi.py:346` | Iterable validation result carrying mesh, manifold and the once-computed radial probe |
| `_stl_bad_edge_count` | `kintsugi.py:203` | Counts edges used by ≠2 faces after binary-STL reload |
| `_roundtrip_bad_edges` | `kintsugi.py:218` | Guard check using the same repaired export path as writing |
| `_collapse_edge` / `_repair_stl_slivers` | `kintsugi.py:1192-1273` | Watertight/volume-preserving collapse of sub-`10 nm` CSG slivers |
| `_probe_wall_range` | `kintsugi.py:296` | Finds the two-hit wall Z range, median thickness and `has_wall` |
| `wall_z_min` / `wall_z_max` | `kintsugi.py:168-169` | Two-hit wall range from the probe |
| `median_two_hit_wall` | `kintsugi.py:170` | Global median wall thickness used as the single-hit fallback |
| `z_wall_lo` / `z_wall_hi` | `kintsugi.py:149-171` | Wall-only truncation limits (no band-edge clamp) |
| `_ray_tiebreak_direction` | `kintsugi.py:504` | Points a tie-broken ray away from the third seed's side of edge `ab` |
| `_merge_collinear_segments` | `kintsugi.py:566` | Unions overlapping periodic copies of the same ridge |
| `_unwrap_u` / `_truncate_polyline_z` | `kintsugi.py:615-695` | Seam-safe polyline processing and wall-range truncation |
| `single_hit_points` | `kintsugi.py:867` | Number of projection points with only one ray hit (inside the solid floor) |
| `ray_miss_fraction_total` | `kintsugi.py:869` | Total miss fraction, alongside the in-band envelope fraction |
| `cutter_attempts` | `kintsugi.py:1514-1594` | Number of sub-seed rounds used by the round-trip guard (1–3) |
| `cutter_variants` | `kintsugi.py:1514-1594` | Deterministic cutter construction variants tried in the successful round |
| `guard_evaluations` | `kintsugi.py:1514-1594` | Number of guard evaluations; each repairs each material once and reuses the result |
| `debris_unmoved` | `kintsugi.py:1025-1040` | Isolated crumbs left in their original material |
| `/api/validate` | `web_app.py:123` | Multipart upload validation endpoint returning `valid`, `detail`, `extents`, `volume` |
| `MAX_UPLOAD_BYTES` | `web_app.py:25` | 50 MB upload cap (HTTP 413) |
| `KINTSUGI_JOB_TTL_S` | `web_app.py:48` | Job-directory retention TTL, default 3600 s |
| `KINTSUGI_MAX_JOBS` | `web_app.py:48` | Maximum retained job directories, default 50 |

### Resolved assumptions added by remediation

8. **Ribbon shard count is emergent, not guaranteed.** After the corrected
   periodic network and the F3 Z clamp, seed 7 at R=0.2 produces one connected
   ceramic body while the gold still penetrates the full wall. The old
   `test_ribbon_through_wall` assertion requiring more than one ceramic
   component was therefore replaced by watertight/volume assertions; the
   through-wall depth assertion remains. Shard count was never a spec
   requirement.
9. **Cutter-internal STL bad edges do not imply output bad edges.** Staged
   F1b counts can show 2 cutter-internal edges for some seeds, while both CSG
   outputs are clean. The enforced guard is on the two printed outputs, which
   is what the slicer consumes.
10. **Isolated crumbs stay put.** The face-sharing rule can leave a crumb in
    its original material (`debris_unmoved`), but this preserves volume and
    avoids new kissing edges; deleting or force-unioning it would be worse.
11. **Manual slicer import remains open.** Task 6.3 is still the only deferred
    check; the 3MF structure is verified but Bambu Studio / PrusaSlicer are not
    installed in this environment.
12. **The Voronoi distance definition is authoritative for unbounded rays.**
    The literal "away from the third Delaunay seed" sign is ambiguous when the
    finite vertex sits far outside the seed cloud; the implementation evaluates
    both normals against the definition and uses the third seed only as a
    numerical tie-break. This is a correctness clarification, not a loosened
    test.
13. **The remaining ribbon failures were STL-scale slivers, not just
    coplanar slabs.** The earlier jitter reduced but did not solve them; the
    guarded export edge-collapse is the actual fix and is accepted only when
    watertightness, positive volume and `1e-6` volume conservation still hold.
14. **Vein overlap handling changed from hulls to unions.** Consecutive vein
    spheres overlap by construction, so hulling them created shared faces; the
    union of overlapping spheres plus a ≤0.2% per-sphere radius jitter removes
    the last routine retries. A hull is still used when a centre gap exceeds
    the sphere diameter.

### `openspec-verify-change` audit

The verification skill was executed against the completed artifacts:

- **Completeness — PASS with one allowed exception.** All 7.0–7.12,
  8.0–8.5 and 9.0–9.8 tasks are `- [x]`. Task 6.3 (manual Bambu Studio / PrusaSlicer
  import) remains `- [ ]`; the handoff explicitly permits it to stay open and
  it is recorded here and in the matrix. No other task is incomplete.
- **Correctness — PASS.** 35/35 tests pass; the crack-graph audit is
  0 phantom / 0 crossings / 0.0% clamp-line points in all four rows; the
  144-run tuning sweep and both 160-run out-of-sample sweeps are 100% clean
  with **0 retries and 0 false rejections**; all render sets are watertight
  with 0 bad edges. New and changed spec scenarios are mapped to
  tests/evidence in the scenario audit above.
- **Coherence — PASS.** Implementation follows architecture Decision 2
  (periodic-diagram invariant and central-seed rule), Decision 7 (cutter-only
  de-alignment, single repair per guard evaluation, round-trip guard), the
  revised Decision 3 (overlapping vein sphere unions) and Decision 4
  (face-sharing debris merge), and the existing design tokens / zero-build GUI
  constraints. No dependency or `DESIGN.md` token changes were made.
- **CRITICAL issues:** none, apart from the allowed deferred 6.3.
- **WARNINGS:** (a) ribbon shard count is emergent and the old component-count
  assertion was revised; (b) slicer GUI import is manual and unverified;
  (c) the upload cap is a post-spool storage cap, documented in architecture;
  (d) the round-3 out-of-sample sweep used one deterministic second cutter
  variant, with no sub-seed retry.
- **SUGGESTIONS:** none blocking.

Verdict: **no critical issues beyond the permitted 6.3 deferral; ready for
user review and before/after render inspection. Do not archive.**

### Data preservation

`presets/*.stl` were not modified during remediation (mtime remains
2026-11-06 03:20:28; MD5s: benchy `4e386f38b9c125faafa1052f724c169f`,
tea_bowl `b2a95e5a23ddadbac9d8871da9de28ee`, vase
`c7aad0e6e4d95cfa40278f6bb142dc71`). `output/sample_summary.json` was
regenerated at 13:43 by `generate_sample.py`, not hand-edited. The sweep JSON
and render PNGs were regenerated by `tools/sweep.py` and `tools/render.py`.

---

## 10. Second independent verification findings (2026-11-06)

The first remediation round was re-checked with an out-of-sample sweep
(seeds 100–107, R ∈ {0, 0.1, 0.35, 0.6, 0.8}). Headline results held, but three
issues remained.

| ID | Severity | Finding | Evidence | Location |
|---|---|---|---|---|
| F11 | CRITICAL | Unbounded Voronoi rays are still oriented incorrectly. The local seed-pair-midpoint rule points away from the bisector midpoint, but the finite vertex is on that bisector, so it is wrong whenever the vertex is on the far side of the hull edge (obtuse Delaunay triangles). A point just along the ray must be closer to the ridge's two seeds than to any other seed. | 24–29% of rays fail the Voronoi-distance definition at S = 0.2, 0.8 and 1.0 over 200 seeds; the third-seed rule fails only 1/1,878 (numerical edge case) | `kintsugi.py:417-432` (`_ridge_segment`) |
| F12 | CRITICAL | Ribbon kissing is reduced, not solved. Out-of-sample, 13/160 runs needed a retry and tea_bowl R=0.1 ribbon seed 103 failed all 3 attempts. The previous "coplanar slab faces" explanation is incomplete. | 159/160 clean, 1 `RuntimeError`; retries 13/160; seed-0 cutter still has 2 bad edges | `kintsugi.py:720-788` (`build_ribbon_cutter`), guard in `generate_kintsugi_mesh` |
| F13 | CRITICAL | The F8 single-hit wall rule is wrong: `t` = distance to outer hit capped at `0.5*rbar` cuts ~22 mm slots into the 3 mm solid floor. With the z-clamp parking points on the base line, 18–20% of R=0 gold volume sits in the floor for seeds 1 and 3 (5% at R=0.2). | Gold reaches `r ≈ 22 mm` inside a floor whose inner wall is at `r = 42 mm`; flat wedge plates in the R=0 gold render | `kintsugi.py:607-615` (`project_crack_paths`), `kintsugi.py:522-533` (z clamp) |

Additional review notes to address in this round:

- **Rim clamping** flattens some segments half a seam width below the rim; a
  wall-range clamp should reduce this.
- **Upload cap**: `_save_upload` limits bytes written to disk, but Starlette has
  already spooled the request body; document that this is not a true
  request-size limit.
- **Dead debris branches**: the second `elif` in each `swap_debris` loop cannot
  fire; remove it or comment it.
- **Weak ribbon assertion**: `test_ribbon_through_wall`'s `max(depths) > 2.8`
  can be satisfied by the base slots; assert on the wall region only once F13
  is fixed.
- **Out-of-sample tool**: add the reviewer's `sweep2.py` under `tools/` so the
  next round is checked on seeds it was not tuned to.

### Round-2 remediation log

Entries are appended below as tasks 8.1–8.5 run.

#### 8.0 — Round-2 findings recorded (documentation only)

F11–F13 and the review notes are recorded here and in `research.md`; the
affected matrix rows are downgraded to **Failing — see §10**. No code changed
in this step.

#### 8.1 — Failing round-2 tests before implementation

Command:

```bash
.venv/bin/python -m unittest -v \
  tests.test_kintsugi.KintsugiTestCase.test_unbounded_rays_obey_voronoi_definition \
  tests.test_kintsugi.KintsugiTestCase.test_ribbon_no_retries_out_of_sample_cases \
  tests.test_kintsugi.KintsugiTestCase.test_wall_range_clamp_keeps_gold_out_of_floor \
  tests.test_kintsugi.KintsugiTestCase.test_ribbon_through_wall
```

Verbatim failing output (9 failures + 1 error):

```text
test_unbounded_rays_obey_voronoi_definition (tests.test_kintsugi.KintsugiTestCase.test_unbounded_rays_obey_voronoi_definition) ... FAIL
test_ribbon_no_retries_out_of_sample_cases (tests.test_kintsugi.KintsugiTestCase.test_ribbon_no_retries_out_of_sample_cases) ... 
  test_ribbon_no_retries_out_of_sample_cases (tests.test_kintsugi.KintsugiTestCase.test_ribbon_no_retries_out_of_sample_cases) (preset='tea_bowl', R=0.1, seed=103) ... ERROR
  test_ribbon_no_retries_out_of_sample_cases (tests.test_kintsugi.KintsugiTestCase.test_ribbon_no_retries_out_of_sample_cases) (preset='tea_bowl', R=0.35, seed=100) ... FAIL
  test_ribbon_no_retries_out_of_sample_cases (tests.test_kintsugi.KintsugiTestCase.test_ribbon_no_retries_out_of_sample_cases) (preset='tea_bowl', R=0.35, seed=103) ... FAIL
  test_ribbon_no_retries_out_of_sample_cases (tests.test_kintsugi.KintsugiTestCase.test_ribbon_no_retries_out_of_sample_cases) (preset='tea_bowl', R=0.35, seed=106) ... FAIL
  test_ribbon_no_retries_out_of_sample_cases (tests.test_kintsugi.KintsugiTestCase.test_ribbon_no_retries_out_of_sample_cases) (preset='tea_bowl', R=0.6, seed=107) ... FAIL
  test_ribbon_no_retries_out_of_sample_cases (tests.test_kintsugi.KintsugiTestCase.test_ribbon_no_retries_out_of_sample_cases) (preset='tea_bowl', R=0.8, seed=107) ... FAIL
  test_ribbon_no_retries_out_of_sample_cases (tests.test_kintsugi.KintsugiTestCase.test_ribbon_no_retries_out_of_sample_cases) (preset='vase', R=0.6, seed=106) ... FAIL
  test_ribbon_no_retries_out_of_sample_cases (tests.test_kintsugi.KintsugiTestCase.test_ribbon_no_retries_out_of_sample_cases) (preset='vase', R=0.6, seed=107) ... FAIL
test_wall_range_clamp_keeps_gold_out_of_floor (tests.test_kintsugi.KintsugiTestCase.test_wall_range_clamp_keeps_gold_out_of_floor) ... FAIL
test_ribbon_through_wall (tests.test_kintsugi.KintsugiTestCase.test_ribbon_through_wall) ... ok

======================================================================
ERROR: test_ribbon_no_retries_out_of_sample_cases (tests.test_kintsugi.KintsugiTestCase.test_ribbon_no_retries_out_of_sample_cases) (preset='tea_bowl', R=0.1, seed=103)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 796, in test_ribbon_no_retries_out_of_sample_cases
    result = kintsugi.generate_kintsugi_mesh(
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/node/global-sandbox/projects/wax-robot/kintsugi.py", line 1155, in generate_kintsugi_mesh
    raise RuntimeError(
RuntimeError: Round-trip guard failed after 3 cutter attempts: ceramic has 2 bad edges, gold has 2 bad edges; no output files were written

======================================================================
FAIL: test_unbounded_rays_obey_voronoi_definition (tests.test_kintsugi.KintsugiTestCase.test_unbounded_rays_obey_voronoi_definition)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 771, in test_unbounded_rays_obey_voronoi_definition
    self.assertLessEqual(
AssertionError: 650.1491031610161 not less than or equal to 650.1475673680131 : S=0.2 trial=0 ridge=0 points the wrong way: a point along the ray is closer to a non-ridge seed

======================================================================
FAIL: test_ribbon_no_retries_out_of_sample_cases (tests.test_kintsugi.KintsugiTestCase.test_ribbon_no_retries_out_of_sample_cases) (preset='tea_bowl', R=0.35, seed=100)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 799, in test_ribbon_no_retries_out_of_sample_cases
    self.assertEqual(
AssertionError: 2 != 1 : tea_bowl R=0.35 seed=100 needed a retry

======================================================================
FAIL: test_ribbon_no_retries_out_of_sample_cases (tests.test_kintsugi.KintsugiTestCase.test_ribbon_no_retries_out_of_sample_cases) (preset='tea_bowl', R=0.35, seed=103)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 799, in test_ribbon_no_retries_out_of_sample_cases
    self.assertEqual(
AssertionError: 2 != 1 : tea_bowl R=0.35 seed=103 needed a retry

======================================================================
FAIL: test_ribbon_no_retries_out_of_sample_cases (tests.test_kintsugi.KintsugiTestCase.test_ribbon_no_retries_out_of_sample_cases) (preset='tea_bowl', R=0.35, seed=106)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 799, in test_ribbon_no_retries_out_of_sample_cases
    self.assertEqual(
AssertionError: 2 != 1 : tea_bowl R=0.35 seed=106 needed a retry

======================================================================
FAIL: test_ribbon_no_retries_out_of_sample_cases (tests.test_kintsugi.KintsugiTestCase.test_ribbon_no_retries_out_of_sample_cases) (preset='tea_bowl', R=0.6, seed=107)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 799, in test_ribbon_no_retries_out_of_sample_cases
    self.assertEqual(
AssertionError: 2 != 1 : tea_bowl R=0.6 seed=107 needed a retry

======================================================================
FAIL: test_ribbon_no_retries_out_of_sample_cases (tests.test_kintsugi.KintsugiTestCase.test_ribbon_no_retries_out_of_sample_cases) (preset='tea_bowl', R=0.8, seed=107)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 799, in test_ribbon_no_retries_out_of_sample_cases
    self.assertEqual(
AssertionError: 2 != 1 : tea_bowl R=0.8 seed=107 needed a retry

======================================================================
FAIL: test_ribbon_no_retries_out_of_sample_cases (tests.test_kintsugi.KintsugiTestCase.test_ribbon_no_retries_out_of_sample_cases) (preset='vase', R=0.6, seed=106)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 799, in test_ribbon_no_retries_out_of_sample_cases
    self.assertEqual(
AssertionError: 2 != 1 : vase R=0.6 seed=106 needed a retry

======================================================================
FAIL: test_ribbon_no_retries_out_of_sample_cases (tests.test_kintsugi.KintsugiTestCase.test_ribbon_no_retries_out_of_sample_cases) (preset='vase', R=0.6, seed=107)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 799, in test_ribbon_no_retries_out_of_sample_cases
    self.assertEqual(
AssertionError: 3 != 1 : vase R=0.6 seed=107 needed a retry

======================================================================
FAIL: test_wall_range_clamp_keeps_gold_out_of_floor (tests.test_kintsugi.KintsugiTestCase.test_wall_range_clamp_keeps_gold_out_of_floor)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 827, in test_wall_range_clamp_keeps_gold_out_of_floor
    self.assertEqual(
AssertionError: 191 != 0 : gold cuts into the solid floor below the wall range

----------------------------------------------------------------------
Ran 4 tests in 7.719s

FAILED (failures=9, errors=1)
```

#### 8.2 — F11 unbounded-ray orientation

- **Finding:** the seed-pair-midpoint rule pointed 24–29% of unbounded rays
  the wrong way at S = 0.2/0.8/1.0.
- **Root cause:** the finite vertex lies on the bisector, so the midpoint rule
  does not determine which side is empty; obtuse Delaunay triangles make the
  literal third-seed sign ambiguous when the vertex is far outside the seed
  cloud.
- **Change:** `kintsugi.py:493-548` (`_ridge_segment`) evaluates both normal
  directions against the defining Voronoi property — a point just along the
  ray must be closer to the ridge's two seeds than to any other seed — and
  uses the third Delaunay seed only as a numerical tie-break. One periodic
  representative is retained.
- **Before:** midpoint rule failed 24–29% of rays; new test failed immediately
  at S=0.2 trial 0.
- **After:** `test_unbounded_rays_obey_voronoi_definition` passes 25 seed sets
  × 3 severities.

Verbatim round-2 fix tests:

```text
test_unbounded_rays_obey_voronoi_definition (tests.test_kintsugi.KintsugiTestCase.test_unbounded_rays_obey_voronoi_definition) ... ok
test_ribbon_no_retries_out_of_sample_cases (tests.test_kintsugi.KintsugiTestCase.test_ribbon_no_retries_out_of_sample_cases) ... ok
test_vein_no_retries_out_of_sample_cases (tests.test_kintsugi.KintsugiTestCase.test_vein_no_retries_out_of_sample_cases) ... ok
test_wall_range_clamp_keeps_gold_out_of_floor (tests.test_kintsugi.KintsugiTestCase.test_wall_range_clamp_keeps_gold_out_of_floor) ... ok
test_ribbon_through_wall (tests.test_kintsugi.KintsugiTestCase.test_ribbon_through_wall) ... ok

----------------------------------------------------------------------
Ran 5 tests in 33.292s

OK
```

#### 8.3 — F12 ribbon kissing and export slivers

- **Finding:** 13/160 out-of-sample runs retried and one failed all three
  attempts; the ±0.5°/1e-3W jitter reduced but did not eliminate the problem.
- **Actual cause:** the float64 CSG output contains sub-`10 nm` sliver edges at
  cut boundaries. Binary STL float32 rounding/loader position merging turns
  them into edges used by four faces. Per-path slab unions, duplicate
  shared-slab copies and planar cross-section hulls were tested and did not
  fix it. The earlier "coplanar shared slab face" explanation was incomplete.
- **Change:** `kintsugi.py:194-230` adds `_stl_bad_edge_count`;
  `kintsugi.py:1049-1133` adds `_collapse_edge` / `_repair_stl_slivers` and
  makes `_export_trimesh` repair only sub-`1e-5` edges, accepted only when the
  mesh stays watertight, positive-volume and within `1e-6` volume.
  `_roundtrip_bad_edges` checks the same repaired export path. Vein mode also
  unions overlapping spheres directly and applies a ≤0.2% per-sphere radius
  jitter (`kintsugi.py:824-893`), with two deterministic union orders tried
  within one guard attempt (`kintsugi.py:1355-1430`).
- **Before:** out-of-sample 159/160 clean, 13 retries, one `RuntimeError`;
  tuning sweep had 2 retries.
- **After:** both sweeps are clean with **zero retries**:
  tuning 144/144 attempts `{1: 144}`, out-of-sample 160/160 attempts
  `{1: 160}`, variants `{1: all}`.

#### 8.4 — F13 wall-range clamp and single-hit median

- **Finding:** the single-hit rule cut ~22 mm slots into the 3 mm floor; gold
  reached `r ≈ 22 mm` inside a floor with inner wall `r = 42 mm`.
- **Change:** `kintsugi.py:287-333` (`_probe_wall_range`) finds the Z range
  where radial rays have at least two hits and the median two-hit wall
  thickness. `kintsugi.py:142-163` computes `z_clamp_lo`/`z_clamp_hi` from
  that wall range; `generate_crack_paths` clamps to it (`kintsugi.py:675-686`).
  `project_crack_paths` uses the path median two-hit thickness for any residual
  single-hit point, falling back to the global median (`kintsugi.py:698-800`).
- **Before:** `test_wall_range_clamp_keeps_gold_out_of_floor` found **191**
  gold vertices in the floor below the wall range.
- **After:** 0 intruders; `median_two_hit_wall` is ~3.0 mm on the tea bowl.

#### 8.5 — Round-2 final verification

- Full suite: **30/30 pass**.
- Tuning sweep: **144/144 clean, 0 retries**.
- Out-of-sample sweep: **160/160 clean, 0 retries**.
- Renders: all 9 standard/remediation views watertight with 0 bad edges; the
  R=0 gold-only views show wall seams with no flat base plates. Baseline
  remediation renders are preserved in
  `output/verification/renders_remediation_baseline/`; final renders are in
  `output/verification/renders_remediation/`.
- `openspec validate --strict` remains green. Task 6.3 (manual slicer import)
  remains the only open task; no archive or specs-apply was run.

Final test suite:

```text
/home/node/global-sandbox/projects/wax-robot/.venv/lib/python3.11/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
  from starlette.testclient import TestClient as TestClient  # noqa
test_3mf_structure (test_kintsugi.KintsugiTestCase.test_3mf_structure) ... ok
test_debris_swap (test_kintsugi.KintsugiTestCase.test_debris_swap) ... ok
test_debris_swap_no_new_bad_edges (test_kintsugi.KintsugiTestCase.test_debris_swap_no_new_bad_edges) ... ok
test_determinism (test_kintsugi.KintsugiTestCase.test_determinism) ... ok
test_high_severity_bowl_not_rejected (test_kintsugi.KintsugiTestCase.test_high_severity_bowl_not_rejected) ... ok
test_input_envelope_rejection (test_kintsugi.KintsugiTestCase.test_input_envelope_rejection) ... ok
test_input_validation (test_kintsugi.KintsugiTestCase.test_input_validation) ... ok
test_junctions_connected (test_kintsugi.KintsugiTestCase.test_junctions_connected) ... ok
test_parameter_table (test_kintsugi.KintsugiTestCase.test_parameter_table) ... ok
test_printable_channel_thickness (test_kintsugi.KintsugiTestCase.test_printable_channel_thickness) ... ok
test_ribbon_no_retries_out_of_sample_cases (test_kintsugi.KintsugiTestCase.test_ribbon_no_retries_out_of_sample_cases) ... ok
test_ribbon_through_wall (test_kintsugi.KintsugiTestCase.test_ribbon_through_wall) ... ok
test_roundtrip_guard_raises_and_writes_nothing (test_kintsugi.KintsugiTestCase.test_roundtrip_guard_raises_and_writes_nothing) ... ok
test_seed_sweep_watertight (test_kintsugi.KintsugiTestCase.test_seed_sweep_watertight) ... ok
test_stl_disk_roundtrip (test_kintsugi.KintsugiTestCase.test_stl_disk_roundtrip) ... ok
test_unbounded_rays_obey_voronoi_definition (test_kintsugi.KintsugiTestCase.test_unbounded_rays_obey_voronoi_definition) ... ok
test_vein_cutter_no_kissing (test_kintsugi.KintsugiTestCase.test_vein_cutter_no_kissing) ... ok
test_vein_depth (test_kintsugi.KintsugiTestCase.test_vein_depth) ... ok
test_vein_no_retries_out_of_sample_cases (test_kintsugi.KintsugiTestCase.test_vein_no_retries_out_of_sample_cases) ... ok
test_volume_smoke (test_kintsugi.KintsugiTestCase.test_volume_smoke) ... ok
test_voronoi_ridges_do_not_cross (test_kintsugi.KintsugiTestCase.test_voronoi_ridges_do_not_cross) ... ok
test_wall_range_clamp_keeps_gold_out_of_floor (test_kintsugi.KintsugiTestCase.test_wall_range_clamp_keeps_gold_out_of_floor) ... ok
test_wealthy_case (test_kintsugi.KintsugiTestCase.test_wealthy_case) ... ok
test_api_fracture_success (test_web_api.WebApiTestCase.test_api_fracture_success) ... ok
test_api_fracture_wealthy (test_web_api.WebApiTestCase.test_api_fracture_wealthy) ... ok
test_api_presets (test_web_api.WebApiTestCase.test_api_presets) ... ok
test_api_upload_too_large (test_web_api.WebApiTestCase.test_api_upload_too_large) ... ok
test_api_validate_ok (test_web_api.WebApiTestCase.test_api_validate_ok) ... ok
test_api_validate_open_mesh (test_web_api.WebApiTestCase.test_api_validate_open_mesh) ... ok
test_job_retention (test_web_api.WebApiTestCase.test_job_retention) ... ok

----------------------------------------------------------------------
Ran 30 tests in 152.645s

OK
```

Tuning sweep:

```json
{
  "total": 144,
  "counts": {
    "ok": 144
  },
  "completed": 144,
  "clean": 144,
  "nonwatertight": 0,
  "false_rejections": 0,
  "errors": 0,
  "cutter_attempts": {
    "1": 144
  },
  "cutter_variants": {
    "1": 144
  },
  "debris_unmoved_total": 113
}
Wrote /home/node/global-sandbox/projects/wax-robot/output/verification/sweep.json
```

Out-of-sample sweep:

```json
{
  "total": 160,
  "counts": {
    "ok": 160
  },
  "clean": 160,
  "nonwatertight": 0,
  "errors": 0,
  "cutter_attempts": {
    "1": 160
  },
  "cutter_variants": {
    "1": 160
  },
  "ribbon_ceramic_components": {
    "4": 12,
    "3": 5,
    "9": 1,
    "8": 1,
    "6": 6,
    "5": 7,
    "2": 19,
    "1": 29
  }
}
Wrote /home/node/global-sandbox/projects/wax-robot/output/verification/sweep_out_of_sample.json
```

Standard renders:

```text
tea_bowl_R0.2_ribbon_s7 | watertight | bad edges=0 cracks=11
tea_bowl_R0.2_ribbon_s0 | watertight | bad edges=0 cracks=14
tea_bowl_R0.2_vein_s1 | watertight | bad edges=0 cracks=13
tea_bowl_R0.7_vein_s3 | watertight | bad edges=0 cracks=4
vase_R0.2_ribbon_s5 | watertight | bad edges=0 cracks=17
tea_bowl_R0.0_ribbon_s1 | watertight | bad edges=0 cracks=21
```

Remediation renders:

```text
tea_bowl_R0.0_ribbon_s1 | watertight | bad edges=0 cracks=21
tea_bowl_R0.0_vein_s2 | watertight | bad edges=0 cracks=16
tea_bowl_R0.2_ribbon_s0 | watertight | bad edges=0 cracks=14
```

Regenerated sample generator:

```text
Wrote parametric bowl fixture: output/bowl_input.stl

--- bowl_R1.0_ribbon ---
  cracks=  0  W=0.80 mm  H=12.00 mm
  volumes: ceramic=65775.66 mm^3  gold=0.00 mm^3
  triangles: ceramic=768  gold=0
  time: 0.13 s

--- bowl_R1.0_vein ---
  cracks=  0  W=0.80 mm  H=12.00 mm
  volumes: ceramic=65775.66 mm^3  gold=0.00 mm^3
  triangles: ceramic=768  gold=0
  time: 0.13 s

--- bowl_R0.7_ribbon ---
  cracks=  4  W=1.22 mm  H=26.40 mm
  volumes: ceramic=65204.37 mm^3  gold=571.28 mm^3
  triangles: ceramic=3,364  gold=2,580
  time: 0.46 s

--- bowl_R0.7_vein ---
  cracks=  4  W=1.22 mm  H=26.40 mm
  volumes: ceramic=65639.94 mm^3  gold=135.72 mm^3
  triangles: ceramic=24,488  gold=23,652
  time: 2.38 s

--- bowl_R0.2_ribbon ---
  cracks= 11  W=1.92 mm  H=50.40 mm
  volumes: ceramic=62519.99 mm^3  gold=3255.67 mm^3
  triangles: ceramic=7,144  gold=6,334
  time: 0.82 s

--- bowl_R0.2_vein ---
  cracks= 11  W=1.92 mm  H=50.40 mm
  volumes: ceramic=64588.37 mm^3  gold=1187.29 mm^3
  triangles: ceramic=49,014  gold=47,984
  time: 5.17 s

Summary: output/sample_summary.json
```

### Round-2 data preservation

`presets/*.stl` remain unmodified (same MD5s and mtime as the first round).
`output/verification/sweep.json` and
`output/verification/sweep_out_of_sample.json` were regenerated by the two
tools. `output/verification/renders/` and
`output/verification/renders_remediation/` are regenerated; the pre-fix
remediation screenshots are preserved in
`output/verification/renders_remediation_baseline/`. `output/` sample artefacts
were regenerated by `generate_sample.py`, not hand-edited.

---

## 11. Third independent verification findings (2026-11-06)

Round 2 was independently confirmed (30/30 tests, clean out-of-sample sweep,
no floor gold), but fixing the ray direction exposed crack-graph defects that
had been masked. Round 3 also contains two cleanup items.

| ID | Severity | Finding | Evidence | Location |
|---|---|---|---|---|
| F14 | CRITICAL | **Phantom ridges from the strip ends.** `generate_crack_paths` requires a central-tile seed only for rays. Finite ridges are kept for all three shifts even when both seeds sit in tile −1 or tile +1. Near the ends of the 3-tile strip the diagram is not periodic: those ridges are bent by the neighbours that would sit one tile further out. The shift then drops the bent copy into the central tile, where it overlaps or crosses real ridges. Example: tea bowl, S=0.6, seed 76, ridge 25 (two tile +1 seeds) runs to (770, −677) and duplicates the real ridge 34, ending 0.2 mm past the true vertex. | Measured with noise, jitter and clamp off, against a 9-tile ground truth over 200 seeds. Seeds emitting a path that is not on the periodic diagram: tea bowl S=0.6 **4**, S=1.0 **33**; vase S=0.6 **26**, S=1.0 **114**. Reviewer-tested fix: change `:592` to `if not has_central_seed: continue`. That gave **0/200 phantom and 0 dangling junctions** on both presets at S ∈ {0.6, 1.0}. | `kintsugi.py:584-593` |
| F15a | CRITICAL | **The clamp flattens crack ends onto straight lines and creates crossings.** `compute_parameters` clamps z to `[max(z_min, z_wall,lo) + W/2, min(z_max, z_wall,hi) − W/2]`, so the clamp applies at the band edge as well as the wall range. Every downward band-edge jitter is projected back onto one horizontal line, which violates the existing scenario "Band-edge terminations are not flat". The clamp also acts on subdivided points one by one, so chords crossing the line cut corners, and neighbouring cracks squeezed onto the same line tangle. | Path points lying exactly on a clamp line: 5.5–7.8% mean, 16.7% max. Crossing seeds with the clamp on vs off (noise and jitter off): tea bowl S=0.6 **4 vs 0**, S=1.0 **22 vs 2**; vase S=0.6 **18 vs 2** (the remaining 2s are F14). Full pipeline with noise off (`tools/crack_graph_audit.py`): crossing seeds tea bowl 7 / 26, vase 24 / **76** of 200 at S = 0.6 / 1.0. Visible as horizontal runs in the 2-D graph render. | `kintsugi.py:140-146`, `:674-687` |
| F15b | WARNING | **Band-edge jitter tilts whole ridges.** The jitter adds a vertical offset to the clipped endpoint, so the straight segment from the interior Voronoi vertex rotates and can cross a neighbour. | With F14 fixed and the clamp off: crossing seeds tea bowl 1/200 (S=0.6, seed 175) and 1/200 (S=1.0, seed 43); vase 0/200 (S=0.6) and 2/200 (S=1.0, seeds 153 and 174). | `kintsugi.py:652-661` |
| F16 | WARNING | **The sliver repair carries real load and runs 4 times per material.** It is a valid fix: float32 spacing near 100 mm is about 7.6e-6 mm, so edges under 1e-5 mm cannot survive binary STL anyway. But it is not a rare corner case. `_export_trimesh` is called separately for the guard (`:1409-1410`), the STL write (`:1137`), the 3MF write (`:1204`, `:1213`) and the triangle counts (`:1441-1442`), and each candidate collapse does a full STL export and reload. | Fresh sweep: 142 of 964 exported meshes (15%) needed a repair, 4 repairs failed and fell back to a retry. Run time: median 1.4 s, max **27.4 s**. | `kintsugi.py:209-213`, `:1131-1139`, `:1180-1215`, `:1404-1443` |
| F17 | SUGGESTION | **Tie-break points the wrong way.** When both normal directions score the same within 1e-12, the code points the ray *toward* the third seed. The correct rule points it away from the third seed's side of edge ab, i.e. `dot(direction, c − midpoint(a, b)) < 0`. The code also measures from `finite` rather than from the midpoint. In practice this branch never runs. | Code inspection. | `kintsugi.py:528-534` |

### Round-3 remediation log

Entries are appended below as tasks 9.1–9.8 run.

#### 9.0 — Round-3 findings recorded (documentation only)

F14–F17 are recorded here and in `research.md`; the affected matrix rows are
downgraded to **Partial — see §11**. No code changed in this step.

#### 9.1 — Failing tests and baseline audit

New tests were added/replaced and run before any engine change:

```text
test_crack_paths_lie_on_periodic_voronoi (tests.test_kintsugi.KintsugiTestCase.test_crack_paths_lie_on_periodic_voronoi) ... FAIL
test_no_points_on_wall_limit_lines (tests.test_kintsugi.KintsugiTestCase.test_no_points_on_wall_limit_lines) ... FAIL
test_band_edge_terminals_are_ragged (tests.test_kintsugi.KintsugiTestCase.test_band_edge_terminals_are_ragged) ... FAIL
test_ray_tiebreak_direction (tests.test_kintsugi.KintsugiTestCase.test_ray_tiebreak_direction) ... ERROR
test_export_repair_runs_once_per_guard_evaluation (tests.test_kintsugi.KintsugiTestCase.test_export_repair_runs_once_per_guard_evaluation) ... ERROR
test_vessel_without_wall_range_rejected (tests.test_kintsugi.KintsugiTestCase.test_vessel_without_wall_range_rejected) ... FAIL

======================================================================
ERROR: test_ray_tiebreak_direction (tests.test_kintsugi.KintsugiTestCase.test_ray_tiebreak_direction)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 990, in test_ray_tiebreak_direction
    kintsugi._ray_tiebreak_direction(a, b, third, normal), expected
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: module 'kintsugi' has no attribute '_ray_tiebreak_direction'

======================================================================
ERROR: test_export_repair_runs_once_per_guard_evaluation (tests.test_kintsugi.KintsugiTestCase.test_export_repair_runs_once_per_guard_evaluation)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 1025, in test_export_repair_runs_once_per_guard_evaluation
    evaluations = result["parameters"]["guard_evaluations"]
                  ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
KeyError: 'guard_evaluations'

======================================================================
FAIL: test_crack_paths_lie_on_periodic_voronoi (tests.test_kintsugi.KintsugiTestCase.test_crack_paths_lie_on_periodic_voronoi)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 634, in test_crack_paths_lie_on_periodic_voronoi
    self.assertLessEqual(
AssertionError: 3.577260322640587 not less than or equal to 0.000282743335904867 : tea_bowl S=0.6 seed=0 has points off the periodic Voronoi diagram

======================================================================
FAIL: test_no_points_on_wall_limit_lines (tests.test_kintsugi.KintsugiTestCase.test_no_points_on_wall_limit_lines)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 952, in test_no_points_on_wall_limit_lines
    self.assertGreater(
AssertionError: 0.0 not greater than 1e-09 : tea_bowl seed=0 point lies on limit line 4.6

======================================================================
FAIL: test_band_edge_terminals_are_ragged (tests.test_kintsugi.KintsugiTestCase.test_band_edge_terminals_are_ragged)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 978, in test_band_edge_terminals_are_ragged
    self.assertTrue(any(value > z_max for value in terminals))
AssertionError: False is not true

======================================================================
FAIL: test_vessel_without_wall_range_rejected (tests.test_kintsugi.KintsugiTestCase.test_vessel_without_wall_range_rejected)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/node/global-sandbox/projects/wax-robot/tests/test_kintsugi.py", line 1038, in test_vessel_without_wall_range_rejected
    with self.assertRaises(ValueError) as context:
AssertionError: ValueError not raised

----------------------------------------------------------------------
Ran 6 tests in 2.788s

FAILED (failures=4, errors=2)
```

Baseline crack-graph audit (noise zero):

```text
tea_bowl S=0.6  phantom 200/200  crossing 7/200  clamp-line pts mean 5.5% max 10.7%
 tea_bowl S=1.0  phantom 200/200  crossing 26/200  clamp-line pts mean 7.8% max 16.7%
     vase S=0.6  phantom 200/200  crossing 24/200  clamp-line pts mean 4.2% max 9.8%
     vase S=1.0  phantom 200/200  crossing 76/200  clamp-line pts mean 6.5% max 15.3%
```

Baseline tuning sweep:

```json
{
  "total": 144,
  "counts": {
    "ok": 144
  },
  "completed": 144,
  "clean": 144,
  "nonwatertight": 0,
  "false_rejections": 0,
  "errors": 0,
  "cutter_attempts": {
    "1": 144
  },
  "cutter_variants": {
    "1": 144
  },
  "debris_unmoved_total": 113
}
Wrote /home/node/global-sandbox/projects/wax-robot/output/verification/sweep.json
```

Baseline previous out-of-sample sweep:

```json
{
  "total": 160,
  "counts": {
    "ok": 160
  },
  "clean": 160,
  "nonwatertight": 0,
  "errors": 0,
  "cutter_attempts": {
    "1": 160
  },
  "cutter_variants": {
    "1": 160
  },
  "ribbon_ceramic_components": {
    "4": 12,
    "3": 5,
    "9": 1,
    "8": 1,
    "6": 6,
    "5": 7,
    "2": 19,
    "1": 29
  }
}
Wrote /home/node/global-sandbox/projects/wax-robot/output/verification/sweep_out_of_sample.json
```

The audit matches the reviewer's baseline: crossings 7/26 (tea bowl) and
24/76 (vase) at S=0.6/1.0; clamp-line points 4.2–7.8% mean and up to 16.7% max.
Phantom reads 200/200 because the vertical jitter and clamp also move points
off the diagram; the isolated F14 numbers are in the §11 table.

#### 9.2 — F14 central-seed rule for every ridge

- **Finding:** finite ridges with both seeds outside the central tile were
  bent by the missing neighbours beyond the 3-tile strip and then shifted into
  the central tile as phantom ridges.
- **Change:** `kintsugi.py:604-615` now applies
  `if not has_central_seed: continue` to finite ridges and rays alike; a
  periodic copy with a central seed already covers any seam-crossing ridge.
- **Before:** audit crossings tea bowl 7/26, vase 24/76 at S=0.6/1.0.
- **After (with clamp/jitter still present):** tea bowl 2/3, vase 0/1.
  Phantom still reads 200/200 because F15's vertical jitter and clamp still
  move points off the diagram.

```text
tea_bowl S=0.6  phantom 200/200  crossing 2/200  clamp-line pts mean 5.5% max 10.7%
 tea_bowl S=1.0  phantom 200/200  crossing 3/200  clamp-line pts mean 7.8% max 16.7%
     vase S=0.6  phantom 200/200  crossing 0/200  clamp-line pts mean 4.3% max 9.8%
     vase S=1.0  phantom 200/200  crossing 1/200  clamp-line pts mean 6.5% max 17.8%
```

#### 9.3 — F15b ridge-aligned band-edge jitter

- **Finding:** adding a vertical offset to a clipped endpoint tilted the whole
  ridge and could cross a neighbour.
- **Change:** `kintsugi.py:632-680` draws one bottom and one top offset per
  ridge and clips the **raw** ridge at limits `z_min + δ_bottom` and
  `z_max + δ_top`. The terminal therefore moves along the true ridge; if the
  finite vertex is reached first, the clip stops there.
- **Before (F14 fixed, clamp off):** crossing seeds tea bowl 1/200 (S=0.6),
  1/200 (S=1.0); vase 0/200 (S=0.6), 2/200 (S=1.0).
- **After:** `test_band_edge_terminals_are_ragged` passes; the audit crossings
  fall to zero once F15a is also applied.

#### 9.4 — F15a wall-only truncation and wall-range rejection

- **Finding:** the clamp projected points onto horizontal lines at both band
  edges and the wall range, creating flat terminals and crossings.
- **Change:** `kintsugi.py:140-175` now exposes `z_wall_lo`/`z_wall_hi`
  (wall-only, no `z_min`/`z_max` mixing) and raises a wall-specific
  `ValueError` when no two-hit wall range exists. `_truncate_polyline_z`
  (`kintsugi.py:565-635`) cuts noisy polylines at the wall limits, interpolates
  crossings, drops outside parts and keeps pieces with length ≥ W. No point is
  clamped onto a limit line. `_merge_collinear_segments` removes overlapping
  periodic copies so they do not create duplicate cracks/T-junctions.
- **Before:** clamp-line points 4.2–7.8% mean, up to 16.7%; audit crossings
  tea bowl 7/26, vase 24/76 at S=0.6/1.0.
- **After:** audit all zeros; `test_no_points_on_wall_limit_lines`,
  `test_crack_paths_lie_on_periodic_voronoi`,
  `test_wall_range_clamp_keeps_gold_out_of_floor` and
  `test_high_severity_bowl_not_rejected` pass;
  `test_vessel_without_wall_range_rejected` passes.

#### 9.5 — F17 ray tie-break helper

- **Finding:** the tie-break pointed toward the third seed and measured from
  `finite` instead of the midpoint.
- **Change:** `kintsugi.py:493-505` adds `_ray_tiebreak_direction`, which
  returns `normal` or `−normal` so that
  `dot(direction, third − midpoint(a,b)) < 0`; `_ridge_segment` uses it only
  when the two normal directions tie.
- **Before:** `AttributeError` in the new test.
- **After:** `test_ray_tiebreak_direction` passes; the main
  `test_unbounded_rays_obey_voronoi_definition` still passes.

#### 9.6 — F16 one repair per guard evaluation

- **Finding:** the repair ran for the guard, STL, 3MF and triangle counts, and
  each candidate collapse performed a full STL reload.
- **Change:** `kintsugi.py:1444-1495` computes
  `_export_trimesh(ceramic)` and `_export_trimesh(gold)` once per guard
  evaluation, records `guard_evaluations`, and passes those meshes to
  `export_kintsugi_stl`, `export_kintsugi_3mf` and the triangle counts via
  optional `ceramic_mesh`/`gold_mesh` parameters. The legacy signatures still
  work.
- **Before:** reviewer sweep median 1.4 s, max 27.4 s; 15% of meshes needed
  repair.
- **After:** tea bowl R=0.2 ribbon seed 0 gives `guard_evaluations=1` and
  `repair_calls=2`; sweep medians 0.75/0.86/0.84 s and maxima
  4.16/5.13/6.85 s across the tuning, previous out-of-sample and round-3
  out-of-sample sweeps.

Verbatim focused fix tests:

```text
test_band_edge_terminals_are_ragged (tests.test_kintsugi.KintsugiTestCase.test_band_edge_terminals_are_ragged) ... ok
test_no_points_on_wall_limit_lines (tests.test_kintsugi.KintsugiTestCase.test_no_points_on_wall_limit_lines) ... ok
test_crack_paths_lie_on_periodic_voronoi (tests.test_kintsugi.KintsugiTestCase.test_crack_paths_lie_on_periodic_voronoi) ... ok
test_wall_range_clamp_keeps_gold_out_of_floor (tests.test_kintsugi.KintsugiTestCase.test_wall_range_clamp_keeps_gold_out_of_floor) ... ok
test_high_severity_bowl_not_rejected (tests.test_kintsugi.KintsugiTestCase.test_high_severity_bowl_not_rejected) ... ok
test_ray_tiebreak_direction (tests.test_kintsugi.KintsugiTestCase.test_ray_tiebreak_direction) ... ok
test_unbounded_rays_obey_voronoi_definition (tests.test_kintsugi.KintsugiTestCase.test_unbounded_rays_obey_voronoi_definition) ... ok
test_export_repair_runs_once_per_guard_evaluation (tests.test_kintsugi.KintsugiTestCase.test_export_repair_runs_once_per_guard_evaluation) ... ok
test_vessel_without_wall_range_rejected (tests.test_kintsugi.KintsugiTestCase.test_vessel_without_wall_range_rejected) ... ok

----------------------------------------------------------------------
Ran 9 tests in 59.091s

OK
```

#### 9.7 — Specs, architecture, tests and research

Updated `specs/mesh-fracture-engine/spec.md` (central-seed rule, planarity,
ridge-aligned terminals, truncation, correct tie-break),
`specs/multi-material-export/spec.md` (single repair per material per guard
evaluation), `architecture.md` (Decision 2 invariant/strip-end distortion,
crack-terminal note, Decision 7 repair reuse), `tests.md` (new tests and audit
command) and `research.md` (F14/F15/F16 facts and superseded claims).
`openspec validate --strict` is green.

#### 9.8 — Final verification

- Full suite: **35/35 pass**.
- Audit: **0 phantom, 0 crossing, 0.0% clamp-line points in all four rows**.
- Tuning sweep: **144/144 clean, 0 retries**.
- Previous out-of-sample sweep: **160/160 clean, 0 retries**.
- Round-3 out-of-sample sweep seed 500–507: **160/160 clean, 0 retries,
  1 deterministic second variant**.
- Cross-process determinism: byte-identical STLs and 3MF.
- Renders: all three remediation cases watertight, 0 bad edges; both 2-D graph
  PNGs generated.
- `generate_sample.py` regenerated the samples (MD5s changed, as expected).

Audit:

```text
tea_bowl S=0.6  phantom 0/200  crossing 0/200  clamp-line pts mean 0.0% max 0.0%
 tea_bowl S=1.0  phantom 0/200  crossing 0/200  clamp-line pts mean 0.0% max 0.0%
     vase S=0.6  phantom 0/200  crossing 0/200  clamp-line pts mean 0.0% max 0.0%
     vase S=1.0  phantom 0/200  crossing 0/200  clamp-line pts mean 0.0% max 0.0%
```

Full test suite:

```text
/home/node/global-sandbox/projects/wax-robot/.venv/lib/python3.11/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
  from starlette.testclient import TestClient as TestClient  # noqa
test_3mf_structure (test_kintsugi.KintsugiTestCase.test_3mf_structure) ... ok
test_band_edge_terminals_are_ragged (test_kintsugi.KintsugiTestCase.test_band_edge_terminals_are_ragged) ... ok
test_crack_paths_lie_on_periodic_voronoi (test_kintsugi.KintsugiTestCase.test_crack_paths_lie_on_periodic_voronoi) ... ok
test_debris_swap (test_kintsugi.KintsugiTestCase.test_debris_swap) ... ok
test_debris_swap_no_new_bad_edges (test_kintsugi.KintsugiTestCase.test_debris_swap_no_new_bad_edges) ... ok
test_determinism (test_kintsugi.KintsugiTestCase.test_determinism) ... ok
test_export_repair_runs_once_per_guard_evaluation (test_kintsugi.KintsugiTestCase.test_export_repair_runs_once_per_guard_evaluation) ... ok
test_high_severity_bowl_not_rejected (test_kintsugi.KintsugiTestCase.test_high_severity_bowl_not_rejected) ... ok
test_input_envelope_rejection (test_kintsugi.KintsugiTestCase.test_input_envelope_rejection) ... ok
test_input_validation (test_kintsugi.KintsugiTestCase.test_input_validation) ... ok
test_junctions_connected (test_kintsugi.KintsugiTestCase.test_junctions_connected) ... ok
test_no_points_on_wall_limit_lines (test_kintsugi.KintsugiTestCase.test_no_points_on_wall_limit_lines) ... ok
test_parameter_table (test_kintsugi.KintsugiTestCase.test_parameter_table) ... ok
test_printable_channel_thickness (test_kintsugi.KintsugiTestCase.test_printable_channel_thickness) ... ok
test_ray_tiebreak_direction (test_kintsugi.KintsugiTestCase.test_ray_tiebreak_direction) ... ok
test_ribbon_no_retries_out_of_sample_cases (test_kintsugi.KintsugiTestCase.test_ribbon_no_retries_out_of_sample_cases) ... ok
test_ribbon_through_wall (test_kintsugi.KintsugiTestCase.test_ribbon_through_wall) ... ok
test_roundtrip_guard_raises_and_writes_nothing (test_kintsugi.KintsugiTestCase.test_roundtrip_guard_raises_and_writes_nothing) ... ok
test_seed_sweep_watertight (test_kintsugi.KintsugiTestCase.test_seed_sweep_watertight) ... ok
test_stl_disk_roundtrip (test_kintsugi.KintsugiTestCase.test_stl_disk_roundtrip) ... ok
test_unbounded_rays_obey_voronoi_definition (test_kintsugi.KintsugiTestCase.test_unbounded_rays_obey_voronoi_definition) ... ok
test_vein_cutter_no_kissing (test_kintsugi.KintsugiTestCase.test_vein_cutter_no_kissing) ... ok
test_vein_depth (test_kintsugi.KintsugiTestCase.test_vein_depth) ... ok
test_vein_no_retries_out_of_sample_cases (test_kintsugi.KintsugiTestCase.test_vein_no_retries_out_of_sample_cases) ... ok
test_vessel_without_wall_range_rejected (test_kintsugi.KintsugiTestCase.test_vessel_without_wall_range_rejected) ... ok
test_volume_smoke (test_kintsugi.KintsugiTestCase.test_volume_smoke) ... ok
test_wall_range_clamp_keeps_gold_out_of_floor (test_kintsugi.KintsugiTestCase.test_wall_range_clamp_keeps_gold_out_of_floor) ... ok
test_wealthy_case (test_kintsugi.KintsugiTestCase.test_wealthy_case) ... ok
test_api_fracture_success (test_web_api.WebApiTestCase.test_api_fracture_success) ... ok
test_api_fracture_wealthy (test_web_api.WebApiTestCase.test_api_fracture_wealthy) ... ok
test_api_presets (test_web_api.WebApiTestCase.test_api_presets) ... ok
test_api_upload_too_large (test_web_api.WebApiTestCase.test_api_upload_too_large) ... ok
test_api_validate_ok (test_web_api.WebApiTestCase.test_api_validate_ok) ... ok
test_api_validate_open_mesh (test_web_api.WebApiTestCase.test_api_validate_open_mesh) ... ok
test_job_retention (test_web_api.WebApiTestCase.test_job_retention) ... ok

----------------------------------------------------------------------
Ran 35 tests in 142.481s

OK
```

Tuning sweep:

```json
{
  "total": 144,
  "counts": {
    "ok": 144
  },
  "completed": 144,
  "clean": 144,
  "nonwatertight": 0,
  "false_rejections": 0,
  "errors": 0,
  "cutter_attempts": {
    "1": 144
  },
  "cutter_variants": {
    "1": 144
  },
  "debris_unmoved_total": 127,
  "run_time_median_s": 0.7471464429982007,
  "run_time_max_s": 4.161713636480272
}
Wrote /home/node/global-sandbox/projects/wax-robot/output/verification/sweep.json
```

Previous out-of-sample sweep:

```json
{
  "total": 160,
  "counts": {
    "ok": 160
  },
  "clean": 160,
  "nonwatertight": 0,
  "errors": 0,
  "cutter_attempts": {
    "1": 160
  },
  "cutter_variants": {
    "1": 160
  },
  "ribbon_ceramic_components": {
    "3": 17,
    "2": 17,
    "4": 13,
    "1": 26,
    "5": 4,
    "6": 3
  },
  "run_time_median_s": 0.8646072703413665,
  "run_time_max_s": 5.126711837016046
}
Wrote /home/node/global-sandbox/projects/wax-robot/output/verification/sweep_out_of_sample.json
```

Round-3 out-of-sample sweep:

```json
{
  "total": 160,
  "counts": {
    "ok": 160
  },
  "clean": 160,
  "nonwatertight": 0,
  "errors": 0,
  "cutter_attempts": {
    "1": 160
  },
  "cutter_variants": {
    "1": 159,
    "2": 1
  },
  "ribbon_ceramic_components": {
    "4": 8,
    "2": 20,
    "1": 36,
    "5": 1,
    "7": 1,
    "3": 12,
    "6": 2
  },
  "run_time_median_s": 0.842291780281812,
  "run_time_max_s": 6.848823139443994
}
Wrote output/verification/sweep_round3.json
```

Cross-process determinism:

```text
c1058bbaa6c6ab3ec690c9145b61d4f9  output/round3_det_a/ceramic_body.stl
c1058bbaa6c6ab3ec690c9145b61d4f9  output/round3_det_b/ceramic_body.stl
e072085a9ca7af4007182a2688a2bf28  output/round3_det_a/gold_seams.stl
e072085a9ca7af4007182a2688a2bf28  output/round3_det_b/gold_seams.stl
a199a7a19399f8ad0649c196ed1da1a3  output/round3_det_a/kintsugi_assembly.3mf
a199a7a19399f8ad0649c196ed1da1a3  output/round3_det_b/kintsugi_assembly.3mf
```

Renders:

```text
tea_bowl_R0.0_ribbon_s1 | watertight | bad edges=0 cracks=17
tea_bowl_R0.0_vein_s2 | watertight | bad edges=0 cracks=17
tea_bowl_R0.2_ribbon_s0 | watertight | bad edges=0 cracks=14
```

2-D crack-graph PNGs:

```text
output/verification/renders_round3/crack_graph_tea_bowl_S1.0_seed1.png
output/verification/renders_round3/crack_graph_tea_bowl_S0.6_seed76.png
```

Regenerated samples:

```text
Wrote parametric bowl fixture: output/bowl_input.stl

--- bowl_R1.0_ribbon ---
  cracks=  0  W=0.80 mm  H=12.00 mm
  volumes: ceramic=65775.66 mm^3  gold=0.00 mm^3
  triangles: ceramic=768  gold=0
  time: 0.13 s

--- bowl_R1.0_vein ---
  cracks=  0  W=0.80 mm  H=12.00 mm
  volumes: ceramic=65775.66 mm^3  gold=0.00 mm^3
  triangles: ceramic=768  gold=0
  time: 0.13 s

--- bowl_R0.7_ribbon ---
  cracks=  4  W=1.22 mm  H=26.40 mm
  volumes: ceramic=65126.98 mm^3  gold=648.68 mm^3
  triangles: ceramic=3,588  gold=2,804
  time: 0.39 s

--- bowl_R0.7_vein ---
  cracks=  4  W=1.22 mm  H=26.40 mm
  volumes: ceramic=65622.90 mm^3  gold=152.76 mm^3
  triangles: ceramic=22,176  gold=21,330
  time: 1.82 s

--- bowl_R0.2_ribbon ---
  cracks= 12  W=1.92 mm  H=50.40 mm
  volumes: ceramic=62521.33 mm^3  gold=3254.32 mm^3
  triangles: ceramic=7,152  gold=6,334
  time: 0.67 s

--- bowl_R0.2_vein ---
  cracks= 12  W=1.92 mm  H=50.40 mm
  volumes: ceramic=64589.44 mm^3  gold=1186.22 mm^3
  triangles: ceramic=44,844  gold=43,836
  time: 4.19 s

Summary: output/sample_summary.json
```

Sample MD5s (expected to change from earlier rounds):

```text
b2a95e5a23ddadbac9d8871da9de28ee  output/bowl_input.stl
ff1d1140dab4fced5dbf593dc20a70cf  output/bowl_R0.2_ribbon/ceramic_body.stl
4b57c7b0d11e82ce093f5ba7a2c0dc33  output/bowl_R0.2_ribbon/gold_seams.stl
977f13393a1c0930e780c9ce175c6fee  output/bowl_R0.2_ribbon.3mf
8c7972894862a921270272b41abf3c62  output/bowl_R0.2_vein/ceramic_body.stl
aec4f160316c7ee01a9d1dafa6f4871a  output/bowl_R0.2_vein/gold_seams.stl
da379f8309cd2fd5c4605b1c5e739890  output/bowl_R0.2_vein.3mf
```

### Round-3 data preservation

`presets/*.stl` remain unchanged at the original MD5s:
benchy `4e386f38b9c125faafa1052f724c169f`,
tea_bowl `b2a95e5a23ddadbac9d8871da9de28ee`,
vase `c7aad0e6e4d95cfa40278f6bb142dc71`.

The crack graphs changed, so `output/` sample MD5s changed as expected.
`generate_sample.py` regenerated `output/bowl_input.stl`,
`output/bowl_R*/` and `output/bowl_R*.3mf`; no sample was hand-edited.
Round-3 evidence is in `output/verification/crack_graph_audit.json`
(baseline in `crack_graph_audit_baseline.json`),
`output/verification/sweep.json`,
`output/verification/sweep_out_of_sample.json`,
`output/verification/sweep_round3.json` and
`output/verification/renders_round3/` (including the two 2-D graph PNGs).

---

## 12. Independent macOS verification report (2026-11-07)

An external run was reported from the separate checkout
`/Users/gregorylazatin/Documents/Dev/projects/kintsugi-fracture`, using its
isolated `.venv`:

| Host | Reported value |
|---|---|
| OS | macOS 27.2 (Darwin 27.2.0 arm64) |
| CPU | Apple M6 (arm64, Apple Silicon) |
| Python | 3.11.18 |

The supplied `logs/tests.log` summary reports **35 tests in 37.917 seconds,
OK**. The same report states that the working tree remained clean. The log and
`walkthrough.md` were not present in this Linux checkout, so the command,
individual test names, dependency versions and walkthrough details could not
be independently inspected here; this entry records the supplied report,
not a locally reproduced run. The report does not include Bambu Studio or
PrusaSlicer import results, so task 6.3 remains open.

## 13. Independent verification of round 3 (2026-11-07)

Round 3 (F14–F17) was re-checked by the reviewer on **seeds the implementing
agent never saw** (300–499 for the crack graph, 310–317 for the sweep, with
R values not used in any earlier sweep). Every round-3 claim holds. Two new
findings come from properties no earlier round measured: crack geometry
*with the noise field on*, and where truncated terminals land.

### Results

| Check | Command | Result |
|---|---|---|
| Unit tests | `.venv/bin/python -m unittest discover -s tests` | **35/35 pass** (315 s) |
| Crack-graph audit, held-out seeds 300–499, noise off, S ∈ {0.3, 0.6, 0.8, 1.0}, both presets | `tools/crack_graph_audit.py` functions over seeds 300–499 | **0 phantom, 0 crossing, 0.0% clamp-line points** in all 8 rows (1,600 configurations) |
| Held-out sweep: seeds 310–317 × R ∈ {0.02, 0.22, 0.42, 0.62, 0.78} × both presets × both modes | reviewer sweep script | **160/160 clean, 0 retries**; sliver repair needed on 36/322 meshes, 2 repairs failed and the guard's in-attempt variant recovered them; run time median 1.9 s, max 10.9 s |
| Floor intrusion, tea bowl R=0, seeds 300–307, both modes | gold vertices with z < 3 mm and r < 41 mm | **0** in all 16 runs |
| Cross-process determinism (vase R=0.3 ribbon seed 311; tea bowl R=0.1 vein seed 312) | two fresh processes, MD5 of all outputs | **byte-identical** |
| u-wrap safety of `_truncate_polyline_z` | steps longer than 10·W in emitted paths, seeds 300–499 | **0**. `u` is unwrapped before noise and truncation (`kintsugi.py:821`), so the seam cannot produce a cross-bowl chord |

Round 3 is accepted: F14, F15a, F15b, F16 and F17 are fixed as specified.

### New findings (open)

| ID | Severity | Finding | Evidence | Location |
|---|---|---|---|---|
| F18 | WARNING | **The noise field folds, so real (noisy) cracks cross and knot.** The planarity guarantee holds only before noise. The z coupling in `_make_noise` (`0.11·freq·z`, `0.13·freq·z` in absolute mm) gives every dyadic octave the same gradient (amplitude halves, frequency doubles), about 0.7 each, so `∂η/∂z` reaches ≈ 3. Wherever `det J < 0` the displacement map folds, and paths cross themselves and each other. Visible as small loops and knots ("hooks") in the 2-D graph and in the 3-D renders near the rim. | `tools/noise_fold_audit.py`: fold area 15–22% of the band (max 26%), max \|∂η\| 2.45–3.41. Seeds with crossing paths **with noise on**, held-out seeds 300–499: tea bowl S=0.3/0.6/1.0 **27 / 108 / 192** of 200; vase **55 / 136 / 185** of 200. Evidence: `output/verification/noise_fold_audit.json`. Not caught by any test because the planarity scenario is scoped to "noise field zero". This scoping came from the reviewer's own handoffs, which kept `_make_noise` out of bounds in every round. | `kintsugi.py` `_make_noise` |
| F19 | SUGGESTION (design) | **Truncated terminals line up on the wall limits, and no crack reaches the rim.** When noise or the band (S ≳ 0.8) extends past the wall range, truncation ends the crack exactly on `z_wall_hi = rim − W/2` or `z_wall_lo`. The floor side is physically plausible (a crack stopping at the wall/floor junction). The rim side means every rim-bound crack stops about W/2 below the rim instead of breaking through it, which is the most characteristic kintsugi look. | Terminals exactly on a wall-limit line, seeds 300–339: tea bowl S=0.6/0.8/1.0 **12% / 21% / 30%**; vase **2% / 8% / 15%**. | `compute_parameters` (`z_wall_hi`), `generate_crack_paths` truncation |
| F20 | SUGGESTION | **Undocumented edit outside the round-3 Target Context Map.** `web_app.py` (modified 2026-11-06 23:16) now returns `guard_evaluations` in the fracture response. The change is harmless, but no remediation log entry or test covers it. | File timestamp; `web_app.py:210` | `web_app.py` |

### Proposed direction for the open findings

- **F18.** Make the noise displacement a strict perturbation of the identity: scale the octave amplitudes, or express the z frequency in units of the mean seed spacing rather than absolute mm, so that the analytic bound `Σ_k a_k·|ω_k| < 1` (target ≤ 0.7) holds. A map `x + η(x)` with `Lip(η) < 1` is injective, so planarity then survives noise by construction. Then extend `test_crack_paths_lie_on_periodic_voronoi` (or add a test) to assert zero crossings **with noise on**. Expect less fine-scale wiggle. Reviewing the renders for aesthetics is part of this fix.
- **F19.** Let rim-bound cracks overshoot: truncate at `wall_z_max + W` instead of `wall_z_max − W/2`, and project any point above the rim with a ray at `wall_z_max − ε`, so the ribbon slab passes cleanly through the rim face instead of kissing it. Keep the floor limit as is. Needs a sweep: the rim face is exactly where coplanar cutter faces would come back.
- **F20.** Log the change in §11 and add an assertion to `test_api_fracture_*`.

### Cross-platform test run (2026-11-07)

The suite was also run on a second machine from a clean clone of
`https://github.com/slowbutfast/kintsugi-fracture` at commit `fffe954eb047`.
That commit was confirmed byte-identical to the verified VPS tree: Git blob SHAs
match for `kintsugi.py`, `web_app.py`, `sample_models.py`, `tests/test_kintsugi.py`,
`tests/test_web_api.py` and `tests/fixtures.py`.

| Host | OS / CPU | Python | Result | Wall time |
|---|---|---|---|---|
| VPS (reviewer run, §12 above) | Linux 5.15 aarch64, 3× Neoverse-N1 | 3.11 | 35/35 OK | 315.0 s |
| Developer workstation | macOS 27.2 (Darwin 27.2.0) arm64, Apple M6 | 3.11.18 | **35/35 OK** | **37.9 s** |

```text
----------------------------------------------------------------------
Ran 35 tests in 37.917s

OK
```

What this adds: the engine, the guard and `test_determinism` (two runs in one
process, byte-identical) behave the same on a second OS and CPU. What it does not
cover: cross-*machine* byte identity. Output MD5s are tied to the machine and are
not compared between hosts, because floating-point rounding can differ between
CPUs. At the time of that cross-platform comparison, the audits and sweeps
were available only from the VPS runs recorded in §§11–13. A later macOS
full-profile audit and sweep are recorded in §14.

---

## 14. Full-profile macOS report (2026-11-07)

The developer workstation supplied a full-profile report for commit
`7424267c2159` (`main`, clean working tree), fingerprint
`6bb47600aecc2194`, created at `2026-11-07T04:59:43Z`. The source report is
identified as
`reports/test-report-7424267c2159-Darwin-arm64.json` in that checkout; it was
not available in this workspace, so the block below is transcribed from the
user-supplied report.

| Host | Reported value |
|---|---|
| OS / CPU | Darwin 27.2.0 arm64 / Apple M6 |
| Python | 3.11.18 |
| Packages | NumPy 2.4.6, SciPy 1.17.1, trimesh 5.2.0, manifold3d 3.5.4, FastAPI 0.162.0, httpx 0.28.1, rtree 1.4.1 |

| Suite | Result |
|---|---|
| Unit tests | PASS, 35/35, 57.7 s |
| Crack-graph audit | PASS, 4 rows, 0 phantom, 0 crossing, 0.0% maximum clamp-line fraction, 6.0 s |
| Out-of-sample sweep | PASS, 160/160 clean, 0 non-watertight, 0 errors, 0 retries, 0.32 s median, 84.4 s total |
| Noise-fold audit | **KNOWN-FAIL (F18)**, 26.2% maximum fold area, maximum gradient 3.41, crossing seeds 703/1200, 4.2 s |

The report's `overall: PASS` reflects its profile policy, which classifies
F18 as a known failure. F18 therefore remains a correctness issue and task
10.1 remains incomplete; the noise-on graph does not meet the intended
no-fold/no-crossing criterion. The other supplied checks add independent
macOS evidence for the unit suite, zero-noise graph audit, and held-out mesh
sweep. Task 6.3 (manual slicer import) is not covered by this report.

The previously reported cross-platform suite establishes that the tested
tree at commit `fffe954eb047` matched the earlier verified VPS tree. This
new report is for commit `7424267c2159`; its contents are recorded as
reported evidence, but the commit and JSON report were not fetched or
independently compared from this workspace.

### First workstation test report, `--profile full` (2026-11-07)

Produced with `tools/test_report.py run --profile full` on the developer
workstation and checked on the VPS with `tools/test_report.py check`:

```text
CHECK: APPLIES to the current VPS tree (fingerprint 6bb47600aecc2194); overall PASS
```

- commit `7424267c2159 clean main` (= `origin/main`)
- fingerprint `6bb47600aecc2194`
- host `Darwin-27.2.0-arm64 | Apple M6 | python 3.11.18`

| Suite | Result | Workstation time | VPS time, same tool |
|---|---|---|---|
| unit | PASS 35/35 | 57.7 s | 176.6 s (`test_report.py run`) |
| crack_graph_audit (both presets × S ∈ {0.6, 1.0} × 200 seeds) | PASS: phantom 0, crossing 0, clamp-line max 0.0% | 6.0 s | 16 s |
| sweep (160 runs, seeds 500–507) | PASS: 160/160 clean, 0 nonwatertight, 0 errors, 0 retries, median 0.32 s | 84.4 s | — |
| noise_fold (both presets × S ∈ {0.3, 0.6, 1.0}, seeds 300–499) | KNOWN-FAIL(F18): fold max 26.2%, max \|∇η\| 3.41, 703/1200 crossing seeds | 4.2 s | 21 s |

Cross-host agreement: the noise_fold figures match the VPS run exactly
(per-row crossings 27 + 108 + 192 + 55 + 136 + 185 = 703; fold max 26.2%; max
gradient 3.41), as do the zero rows of the crack-graph audit. This round's
sweep was run only on the workstation; the earlier §11 runs of the same seed-500
sweep on the VPS were also 160/160 clean.

### Still open from earlier rounds

- **Task 6.3:** manual slicer import (Bambu Studio and PrusaSlicer). Confirm the 3MF loads as one object with two parts.
- **Upload size cap:** Starlette spools the whole request body before `_save_upload` enforces 50 MB, so this is not a true request-size limit. Documented in `architecture.md`, not fixed. A real limit belongs in the reverse proxy or an ASGI middleware that checks `Content-Length` and stream length.

---

## 15. PATCH-01 verification (2026-11-07)

PATCH-01 addressed the three open review findings plus the test-report
exemption. Only `kintsugi.py`, `tests/test_kintsugi.py`,
`tests/test_web_api.py` and `tools/test_report.py` changed; the CSG boolean
pipeline, cutter builders, presets and GUI were untouched.

### F18 — noise folding

Baseline reproduction (`tea_bowl`, S=0.6, seeds 300–305):

```text
tea_bowl S=0.6  fold area mean 21.8% max 26.1%  max|grad eta| 3.41  crossings (noise on) 0/5
```

`_make_noise` now normalises the octave amplitudes so the analytic spatial
gradient bound is at most `0.70`; the displacement map is injective and cannot
fold. The new `test_noise_field_gradient_bounded_and_no_crossings` asserts
`fold_area == 0`, `max|grad eta| <= 0.70`, and zero noise-on crossings.

Final noise audit:

```text
tea_bowl S=0.3  fold area mean 0.0% max 0.0%  max|grad eta| 0.70  crossings (noise on) 0/200
 tea_bowl S=0.6  fold area mean 0.0% max 0.0%  max|grad eta| 0.70  crossings (noise on) 0/200
 tea_bowl S=1.0  fold area mean 0.0% max 0.0%  max|grad eta| 0.70  crossings (noise on) 0/200
     vase S=0.3  fold area mean 0.0% max 0.0%  max|grad eta| 0.70  crossings (noise on) 0/200
     vase S=0.6  fold area mean 0.0% max 0.0%  max|grad eta| 0.70  crossings (noise on) 0/200
     vase S=1.0  fold area mean 0.0% max 0.0%  max|grad eta| 0.70  crossings (noise on) 0/200
```

### F19 — rim break-through

`z_wall_hi` is now `wall_z_max + W`; points above `wall_z_max` are projected by
a ray at `wall_z_max - 0.05`, so the cutter pierces the rim without coplanar
top-face artifacts. The lower floor limit is unchanged. The existing
`test_no_points_on_wall_limit_lines` upper bound now uses the new `z_wall_hi`
(rim overshoot is intentional); its lower-limit and non-terminal-line
assertions are unchanged. Gold now reaches the
rim plane (`z=60`) from both modes (28 vertices above 59.9 in R=0 ribbon seed 1;
120 in R=0 vein seed 2), and all three PATCH-01 renders remain watertight with
0 bad edges.

```text
tea_bowl_R0.0_ribbon_s1 | watertight | bad edges=0 cracks=17
tea_bowl_R0.0_vein_s2 | watertight | bad edges=0 cracks=16
tea_bowl_R0.2_ribbon_s0 | watertight | bad edges=0 cracks=14
```

### F20 — `guard_evaluations` API coverage

`test_api_fracture_success` now asserts the field is present and `>= 1`;
`test_api_fracture_wealthy` asserts it is present and `0` (no cutter run).
Full unit suite: **36/36 pass**.

```text
/home/node/global-sandbox/projects/wax-robot/.venv/lib/python3.11/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
  from starlette.testclient import TestClient as TestClient  # noqa
test_3mf_structure (test_kintsugi.KintsugiTestCase.test_3mf_structure) ... ok
test_band_edge_terminals_are_ragged (test_kintsugi.KintsugiTestCase.test_band_edge_terminals_are_ragged) ... ok
test_crack_paths_lie_on_periodic_voronoi (test_kintsugi.KintsugiTestCase.test_crack_paths_lie_on_periodic_voronoi) ... ok
test_debris_swap (test_kintsugi.KintsugiTestCase.test_debris_swap) ... ok
test_debris_swap_no_new_bad_edges (test_kintsugi.KintsugiTestCase.test_debris_swap_no_new_bad_edges) ... ok
test_determinism (test_kintsugi.KintsugiTestCase.test_determinism) ... ok
test_export_repair_runs_once_per_guard_evaluation (test_kintsugi.KintsugiTestCase.test_export_repair_runs_once_per_guard_evaluation) ... ok
test_high_severity_bowl_not_rejected (test_kintsugi.KintsugiTestCase.test_high_severity_bowl_not_rejected) ... ok
test_input_envelope_rejection (test_kintsugi.KintsugiTestCase.test_input_envelope_rejection) ... ok
test_input_validation (test_kintsugi.KintsugiTestCase.test_input_validation) ... ok
test_junctions_connected (test_kintsugi.KintsugiTestCase.test_junctions_connected) ... ok
test_no_points_on_wall_limit_lines (test_kintsugi.KintsugiTestCase.test_no_points_on_wall_limit_lines) ... ok
test_noise_field_gradient_bounded_and_no_crossings (test_kintsugi.KintsugiTestCase.test_noise_field_gradient_bounded_and_no_crossings) ... ok
test_parameter_table (test_kintsugi.KintsugiTestCase.test_parameter_table) ... ok
test_printable_channel_thickness (test_kintsugi.KintsugiTestCase.test_printable_channel_thickness) ... ok
test_ray_tiebreak_direction (test_kintsugi.KintsugiTestCase.test_ray_tiebreak_direction) ... ok
test_ribbon_no_retries_out_of_sample_cases (test_kintsugi.KintsugiTestCase.test_ribbon_no_retries_out_of_sample_cases) ... ok
test_ribbon_through_wall (test_kintsugi.KintsugiTestCase.test_ribbon_through_wall) ... ok
test_roundtrip_guard_raises_and_writes_nothing (test_kintsugi.KintsugiTestCase.test_roundtrip_guard_raises_and_writes_nothing) ... ok
test_seed_sweep_watertight (test_kintsugi.KintsugiTestCase.test_seed_sweep_watertight) ... ok
test_stl_disk_roundtrip (test_kintsugi.KintsugiTestCase.test_stl_disk_roundtrip) ... ok
test_unbounded_rays_obey_voronoi_definition (test_kintsugi.KintsugiTestCase.test_unbounded_rays_obey_voronoi_definition) ... ok
test_vein_cutter_no_kissing (test_kintsugi.KintsugiTestCase.test_vein_cutter_no_kissing) ... ok
test_vein_depth (test_kintsugi.KintsugiTestCase.test_vein_depth) ... ok
test_vein_no_retries_out_of_sample_cases (test_kintsugi.KintsugiTestCase.test_vein_no_retries_out_of_sample_cases) ... ok
test_vessel_without_wall_range_rejected (test_kintsugi.KintsugiTestCase.test_vessel_without_wall_range_rejected) ... ok
test_volume_smoke (test_kintsugi.KintsugiTestCase.test_volume_smoke) ... ok
test_wall_range_clamp_keeps_gold_out_of_floor (test_kintsugi.KintsugiTestCase.test_wall_range_clamp_keeps_gold_out_of_floor) ... ok
test_wealthy_case (test_kintsugi.KintsugiTestCase.test_wealthy_case) ... ok
test_api_fracture_success (test_web_api.WebApiTestCase.test_api_fracture_success) ... ok
test_api_fracture_wealthy (test_web_api.WebApiTestCase.test_api_fracture_wealthy) ... ok
test_api_presets (test_web_api.WebApiTestCase.test_api_presets) ... ok
test_api_upload_too_large (test_web_api.WebApiTestCase.test_api_upload_too_large) ... ok
test_api_validate_ok (test_web_api.WebApiTestCase.test_api_validate_ok) ... ok
test_api_validate_open_mesh (test_web_api.WebApiTestCase.test_api_validate_open_mesh) ... ok
test_job_retention (test_web_api.WebApiTestCase.test_job_retention) ... ok

----------------------------------------------------------------------
Ran 36 tests in 129.741s

OK
```

### Full-profile report

`KNOWN_OPEN` is now empty. `tools/test_report.py run --profile full` reports:

```text
--- running unit ---
/home/node/global-sandbox/projects/wax-robot/.venv/lib/python3.11/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
  from starlette.testclient import TestClient as TestClient  # noqa
test_3mf_structure (test_kintsugi.KintsugiTestCase.test_3mf_structure) ... ok
test_band_edge_terminals_are_ragged (test_kintsugi.KintsugiTestCase.test_band_edge_terminals_are_ragged) ... ok
test_crack_paths_lie_on_periodic_voronoi (test_kintsugi.KintsugiTestCase.test_crack_paths_lie_on_periodic_voronoi) ... ok
test_debris_swap (test_kintsugi.KintsugiTestCase.test_debris_swap) ... ok
test_debris_swap_no_new_bad_edges (test_kintsugi.KintsugiTestCase.test_debris_swap_no_new_bad_edges) ... ok
test_determinism (test_kintsugi.KintsugiTestCase.test_determinism) ... ok
test_export_repair_runs_once_per_guard_evaluation (test_kintsugi.KintsugiTestCase.test_export_repair_runs_once_per_guard_evaluation) ... ok
test_high_severity_bowl_not_rejected (test_kintsugi.KintsugiTestCase.test_high_severity_bowl_not_rejected) ... ok
test_input_envelope_rejection (test_kintsugi.KintsugiTestCase.test_input_envelope_rejection) ... ok
test_input_validation (test_kintsugi.KintsugiTestCase.test_input_validation) ... ok
test_junctions_connected (test_kintsugi.KintsugiTestCase.test_junctions_connected) ... ok
test_no_points_on_wall_limit_lines (test_kintsugi.KintsugiTestCase.test_no_points_on_wall_limit_lines) ... ok
test_noise_field_gradient_bounded_and_no_crossings (test_kintsugi.KintsugiTestCase.test_noise_field_gradient_bounded_and_no_crossings) ... ok
test_parameter_table (test_kintsugi.KintsugiTestCase.test_parameter_table) ... ok
test_printable_channel_thickness (test_kintsugi.KintsugiTestCase.test_printable_channel_thickness) ... ok
test_ray_tiebreak_direction (test_kintsugi.KintsugiTestCase.test_ray_tiebreak_direction) ... ok
test_ribbon_no_retries_out_of_sample_cases (test_kintsugi.KintsugiTestCase.test_ribbon_no_retries_out_of_sample_cases) ... ok
test_ribbon_through_wall (test_kintsugi.KintsugiTestCase.test_ribbon_through_wall) ... ok
test_roundtrip_guard_raises_and_writes_nothing (test_kintsugi.KintsugiTestCase.test_roundtrip_guard_raises_and_writes_nothing) ... ok
test_seed_sweep_watertight (test_kintsugi.KintsugiTestCase.test_seed_sweep_watertight) ... ok
test_stl_disk_roundtrip (test_kintsugi.KintsugiTestCase.test_stl_disk_roundtrip) ... ok
test_unbounded_rays_obey_voronoi_definition (test_kintsugi.KintsugiTestCase.test_unbounded_rays_obey_voronoi_definition) ... ok
test_vein_cutter_no_kissing (test_kintsugi.KintsugiTestCase.test_vein_cutter_no_kissing) ... ok
test_vein_depth (test_kintsugi.KintsugiTestCase.test_vein_depth) ... ok
test_vein_no_retries_out_of_sample_cases (test_kintsugi.KintsugiTestCase.test_vein_no_retries_out_of_sample_cases) ... ok
test_vessel_without_wall_range_rejected (test_kintsugi.KintsugiTestCase.test_vessel_without_wall_range_rejected) ... ok
test_volume_smoke (test_kintsugi.KintsugiTestCase.test_volume_smoke) ... ok
test_wall_range_clamp_keeps_gold_out_of_floor (test_kintsugi.KintsugiTestCase.test_wall_range_clamp_keeps_gold_out_of_floor) ... ok
test_wealthy_case (test_kintsugi.KintsugiTestCase.test_wealthy_case) ... ok
test_api_fracture_success (test_web_api.WebApiTestCase.test_api_fracture_success) ... ok
test_api_fracture_wealthy (test_web_api.WebApiTestCase.test_api_fracture_wealthy) ... ok
test_api_presets (test_web_api.WebApiTestCase.test_api_presets) ... ok
test_api_upload_too_large (test_web_api.WebApiTestCase.test_api_upload_too_large) ... ok
test_api_validate_ok (test_web_api.WebApiTestCase.test_api_validate_ok) ... ok
test_api_validate_open_mesh (test_web_api.WebApiTestCase.test_api_validate_open_mesh) ... ok
test_job_retention (test_web_api.WebApiTestCase.test_job_retention) ... ok

----------------------------------------------------------------------
Ran 36 tests in 129.769s

OK
--- running crack_graph_audit ---
 tea_bowl S=0.6  phantom 0/200  crossing 0/200  clamp-line pts mean 0.0% max 0.0%
 tea_bowl S=1.0  phantom 0/200  crossing 0/200  clamp-line pts mean 0.0% max 0.0%
     vase S=0.6  phantom 0/200  crossing 0/200  clamp-line pts mean 0.0% max 0.0%
     vase S=1.0  phantom 0/200  crossing 0/200  clamp-line pts mean 0.0% max 0.0%
--- running sweep ---
{
  "total": 160,
  "counts": {
    "ok": 160
  },
  "clean": 160,
  "nonwatertight": 0,
  "errors": 0,
  "cutter_attempts": {
    "1": 160
  },
  "cutter_variants": {
    "1": 160
  },
  "ribbon_ceramic_components": {
    "2": 4,
    "1": 69,
    "5": 1,
    "3": 5,
    "4": 1
  },
  "run_time_median_s": 0.7534101982600987,
  "run_time_max_s": 2.8008532132953405
}
Wrote /tmp/tmpwwm3g2tb/sweep.json
--- running noise_fold ---
 tea_bowl S=0.3  fold area mean 0.0% max 0.0%  max|grad eta| 0.70  crossings (noise on) 0/200
 tea_bowl S=0.6  fold area mean 0.0% max 0.0%  max|grad eta| 0.70  crossings (noise on) 0/200
 tea_bowl S=1.0  fold area mean 0.0% max 0.0%  max|grad eta| 0.70  crossings (noise on) 0/200
     vase S=0.3  fold area mean 0.0% max 0.0%  max|grad eta| 0.70  crossings (noise on) 0/200
     vase S=0.6  fold area mean 0.0% max 0.0%  max|grad eta| 0.70  crossings (noise on) 0/200
     vase S=1.0  fold area mean 0.0% max 0.0%  max|grad eta| 0.70  crossings (noise on) 0/200
=== KINTSUGI TEST REPORT v1 ===
overall: PASS
created_utc: 2026-11-07T05:24:26Z
profile: full
commit: 7424267c2159 DIRTY main
fingerprint: 86d7b6d7f8109bf5
host: Linux-5.15.0-1081-oracle-aarch64 | Neoverse-N1 | python 3.11.2
packages: numpy=2.4.6 scipy=1.17.1 trimesh=5.2.0 manifold3d=3.5.4 fastapi=0.162.0 httpx=0.28.1 rtree=1.4.1
suite unit: PASS ran=36 passed=36 failed=0 errors=0 skipped=0 time=130.6s
suite crack_graph_audit: PASS rows=4 phantom=0 crossing=0 clamp_max=0.0% time=15.8s
suite sweep: PASS total=160 clean=160 nonwatertight=0 errors=0 retries=0 median=0.75s time=182.3s
suite noise_fold: PASS fold_max=0.0% max_grad=0.70 crossing_seeds=0/1200 time=23.0s
report: reports/test-report-7424267c2159-Linux-aarch64.json
=== END KINTSUGI TEST REPORT ===
```

### Determinism and regenerated samples

Cross-process determinism (vase, R=0.3, two CLI processes):

```text
bd97a66618fa7fbf4d3bc47aca3d4595  output/patch01_det_a/ceramic_body.stl
5274dec311b4fb7d3418967c0a85690c  output/patch01_det_a/gold_seams.stl
db05914da960225be812d6a65f6ee955  output/patch01_det_a/kintsugi_assembly.3mf
bd97a66618fa7fbf4d3bc47aca3d4595  output/patch01_det_b/ceramic_body.stl
5274dec311b4fb7d3418967c0a85690c  output/patch01_det_b/gold_seams.stl
db05914da960225be812d6a65f6ee955  output/patch01_det_b/kintsugi_assembly.3mf
```

Samples were regenerated; new MD5s:

```text
a81b862f463a0248bf6358d309285017  output/bowl_R0.2_ribbon/ceramic_body.stl
3c662a103dafc26e52b726f291ff0e8b  output/bowl_R0.2_ribbon/gold_seams.stl
c875f28fa6de9b5dfa573e37e1bc03a5  output/bowl_R0.2_ribbon.3mf
4aed742ea529707c26e7e343cf1ca2e9  output/bowl_R0.2_vein/ceramic_body.stl
8a5d98186565443bbfeb03565bad5b86  output/bowl_R0.2_vein/gold_seams.stl
9fbc6d16eb600fc438875c8cbf92f730  output/bowl_R0.2_vein.3mf
```

PATCH-01 supersedes the `KNOWN-FAIL(F18)` row in §14. `presets/*.stl` remain
unchanged at the original MD5s. Task 6.3 (manual slicer import) remains open;
10.4 (true request-size limit) remains a documented caveat.
