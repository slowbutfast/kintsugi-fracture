# Surgical Patch Handoff: OpenSpec Change 'kintsugi-crack-growth' [PATCH-01]

## 1. Executive Objective & Diagnostic Feedback
- **Change Name**: `kintsugi-crack-growth`
- **Patch ID**: `PATCH-01`
- **Objective**: Fix empty-gold file generation on thin walls, resolve the near-miss collision gap by projecting forward into clean shared T-junctions, tune dendritic branching morphology (correlated heading walk, sideways branch angles), and update spec documentation.
- **Feedback & Diagnostic Trace**:
  ```
  Blocker 1 (Thin-wall empty gold STL):
  thin_cylinder in vein mode at R = 0.62, seed 620:
  - result reports num_cracks: 5;
  - gold volume is 0.0 and gold has 0 triangles;
  - an 84-byte, zero-triangle gold_seams.stl is written;
  - Exporter only skips gold file when it is None, not when it is an empty solid (0 triangles).
  
  Blocker 2 & Warning 1 (Near-misses stop short creating rain streaks):
  - In kintsugi.py:1265, when a candidate segment comes within clearance R_clear, it resamples 3 times and stops short without intersecting.
  - Cracks stop 3 mm short of each other instead of joining.
  - Branching is artificially suppressed (max 1 branch, 0.15*S prob, ±60° heading bound prevents sideways linking).
  - T-junction ratio 80% gate shaped the look and suppressed branching.
  ```
- **Root Cause Analysis**:
  1. `export_kintsugi_stl` and `export_kintsugi_3mf` only test `gold is None`. When `gold.is_empty()` or `len(gold_export_mesh.faces) == 0`, a degenerate 84-byte STL is generated.
  2. Proximity check resampled heading instead of continuing along trajectory to form an intersection when arrival angle $\ge 30^\circ$.
  3. `_GrowthTask` allowed only 1 branch per crack at rate $0.15 \cdot S$, and heading limits `_GROWTH_MIN_HEADING` / `_GROWTH_MAX_HEADING` were clamped to $\pm 60^\circ$ of straight down, preventing horizontal cross-fissures.

## 2. Strict Target Context Map
| File Path (relative to repo root) | Target Lines | Modification Summary |
|---|---|---|
| `kintsugi.py` | L2545–L2565 | In `export_kintsugi_stl`, treat `gold is None or gold.is_empty() or (gold_mesh is not None and len(gold_mesh.faces) == 0)` as omitted: unlink stale gold path, write no gold STL, return `gold_path: None`. |
| `kintsugi.py` | L2590–L2625 | In `export_kintsugi_3mf`, if gold solid is empty or has 0 faces, export only the single ceramic component. |
| `kintsugi.py` | L2810–L2850 | In `generate_kintsugi_mesh`, when gold mesh has 0 triangles or `gold.is_empty()`, set `gold = None`, `seams_omitted: True`, and `num_cracks: 0`. |
| `kintsugi.py` | L725–L735 | Expand heading limits for branch segments up to $\pm 85^\circ$ from straight down (`_GROWTH_DOWN \pm math.radians(85)`), allowing horizontal connecting fissures. |
| `kintsugi.py` | L1155–L1180 | Allow multiple branches per trunk (up to 2–3) driven by severity $S$ (e.g. branch check per step with probability $0.30 \cdot S$). |
| `kintsugi.py` | L1240–L1300 | Update collision handling: when entering clearance $R_{\text{clear}}$ at arrival angle $\ge 30^\circ$, project forward to intersect the existing segment and snap to form a shared subdivided T-junction. Resample only on grazing approaches ($< 30^\circ$). |
| `tools/growth_audit.py` | L200–L250 | Change the 80% T-ratio from a failing gate into an informational reported distribution (report T vs Y count without asserting $> 0.80$). |
| `tools/spike_contact_sheet.py` | L300–L350 | Add row labels (`Tea Bowl R=0`, `Tea Bowl R=0.2`, `Tall Vase R=0.2`, `Thin Cylinder R=0.5`) to contact sheet images. |
| `openspec/changes/kintsugi-crack-growth/specs/mesh-fracture-engine/spec.md` | L40–L65 | Reconcile spec with forward-projection T-junction snapping and empty-gold omission behavior. |
| `tests/test_kintsugi.py` | L1120+ | Add `test_empty_gold_solid_omits_file_and_warns` on `thin_cylinder` at $R=0.62$, seed 620 in vein mode. |

## 3. Blast Radius & Invariant Guardrails
- **STRICT BLAST RADIUS**: Modify ONLY the lines and files specified in the Target Context Map.
- **FORBIDDEN**:
  - Do NOT refactor `_build_vein_cutter`, `swap_debris`, or the core CSG kernel.
  - Do NOT allow tangent cutter contacts ($d \to 0$); preserve the $d < 0.25\text{ mm}$ omission cutoff.
  - Do NOT compromise watertightness or zero-crossing guarantees.
- **INVARIANTS TO PRESERVE**: All 42 existing unit tests MUST continue to pass, plus the new thin-wall reproduction test.

## 4. Visual & UI Impact
- Status: 3D procedural crack morphology update.
- Produces organic Kintsugi branching with connecting horizontal fissures and sharp T-junctions, eliminating the parallel "rain streak" look.
- Zero change to the Windows XP Luna web frontend styling.

## 5. Reproduction & Verification Protocol
1. **Reproduce First**:
   ```bash
   .venv/bin/python -c "from kintsugi import generate_kintsugi_mesh, KintsugiParameters; import sample_models, tempfile, pathlib; p = sample_models.create_thin_cylinder_preset(); tmp = pathlib.Path(tempfile.mkdtemp()); res = generate_kintsugi_mesh(p, KintsugiParameters(income_ratio=0.62, mode='vein', seed=620), tmp/'c.stl', tmp/'g.stl', tmp/'a.3mf'); assert (tmp/'g.stl').exists() and (tmp/'g.stl').stat().st_size == 84, 'Expected 84-byte empty gold STL'"
   ```
2. **Apply Minimal Fix**: Implement targeted fixes in `kintsugi.py`, `growth_audit.py`, and `specs/`.
3. **Verify Fix**: Confirm the test passes and `gold_seams.stl` is not created when 0 triangles exist.
4. **Full Regression Suite**:
   ```bash
   .venv/bin/python -m unittest discover -s tests -v
   ```

## 6. Surgical Patch Checklist
- [ ] P01.1 Scaffold reproducing test `test_empty_gold_solid_omits_file_and_warns` in `tests/test_kintsugi.py`.
- [ ] P01.2 Fix empty gold STL/3MF export in `kintsugi.py`, returning `gold_path: None`, `seams_omitted: True`, and `num_cracks: 0`.
- [ ] P01.3 Update forward collision snapping in `kintsugi.py` to project forward into shared T-junctions when arrival angle $\ge 30^\circ$.
- [ ] P01.4 Tune crack morphology in `kintsugi.py`: correlated heading walk, allow multiple branches (up to 2–3) and sideways angles (up to $\pm 85^\circ$).
- [ ] P01.5 Update `growth_audit.py` to report junction distributions without gating on 80% T-ratio, and regenerate contact sheet with labelled rows.
- [ ] P01.6 Update `specs/mesh-fracture-engine/spec.md` to match forward collision snapping and empty gold omission.
- [ ] P01.7 Run reproducing test and full test suite (`.venv/bin/python -m unittest discover -s tests -v`) verifying 100% clean pass.
- [ ] P01.8 Update `verification.md` and mark PATCH-01 resolved in `patch.md`.
