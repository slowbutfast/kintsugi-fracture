# Surgical Patch Handoff: OpenSpec Change 'ceramic-vessel-wall-envelope' [PATCH-01]

## 1. Executive Objective & Diagnostic Feedback
- **Change Name**: `ceramic-vessel-wall-envelope`
- **Patch ID**: `PATCH-01`
- **Objective**: Implement flared-wall accept/reject test fixtures to verify normal vs radial probing, bound ray-miss fallbacks, test tapered lips, add tolerance to float volume comparisons, and verify the empty-gold pipeline end-to-end.
- **Feedback & Diagnostic Trace**:
  ```
  1. Nothing tests a flared wall: The main reason to measure along the normal is that a horizontal ray
     overstates thickness on a flared wall, so a 1.2 mm wall at 45° reads as ~1.7 mm and gets accepted.
     Need a revolved cone fixture pair:
     - 45° flare with 1.2 mm normal thickness (≈1.7 mm radially): MUST reject.
     - 45° flare with 2.0 mm normal thickness (≈2.8 mm radially): MUST accept with p5 ≈ 2.0.
  2. Conservative fallback in project_crack_paths: If inward normal ray misses, code falls back
     to radial thickness. Keep the radial value and take min(t_normal, t_radial) so an overestimate
     is never introduced.
  3. Tapered-lip fixture: Add a tapered-lip fixture (e.g. 2.4 mm body tapering to 1.0 mm over top 3 mm)
     that passes p5; run vein mode on it, assert gold is continuous and watertight, and report
     minimum carved depth and backing.
  4. Exact backing guarantee wording: State that nominal backing is >= 0.5 * t_i everywhere, and
     >= 0.8 mm wherever t_i >= 1.6 mm.
  5. Exact float compare in _gold_solid_omitted: abs(gold_mesh.volume) <= 0.0 should use a tolerance
     around 1e-6 mm³.
  6. Empty-gold test pipeline coverage: Patch _build_vein_cutter to return empty manifold to verify
     seams_omitted and gold_path: None end-to-end through generate_kintsugi_mesh and /api/fracture.
  7. Task 2.3 notes: Clarify sweep_out_of_sample.py verified with no change needed.
  ```
- **Root Cause Analysis**: Current test fixtures are vertical cylinders where normal and radial thicknesses coincide; without a flared-wall test, regressions to radial probing would pass unnoticed. The percentile guarantee was overgeneralized in docstrings to "everywhere".

## 2. Strict Target Context Map

| File Path (relative to repo root) | Target Lines | Modification Summary |
|---|---|---|
| `tests/test_envelope.py` | `L15–L85` | Add `_flared_cone` fixture helper and `test_envelope_flared_cone_normal_thickness_rejection` (1.2 mm normal rejected, 2.0 mm accepted with $p_5 \approx 2.0\text{ mm}$). |
| `tests/test_kintsugi.py` | `L1200–L1250` | Add tapered-lip fixture test: verify continuous watertight gold solid and record minimum carved depth ($d_{\text{min}}$) and minimum backing ($t - d$). |
| `tests/test_web_api.py` | `L90–L130` | Add end-to-end pipeline test patching `_build_vein_cutter` to return empty manifold; assert `seams_omitted: True`, `gold_path: None`, and `volumes.gold: 0.0`. |
| `kintsugi.py` | `L2210–L2230` | In `project_crack_paths`, if normal ray cast misses or is unclosed, bound fallback: $t_i = \min(t_{\text{radial\_hit}}, t_{\text{normal\_fallback}})$ to prevent flared wall overestimation. |
| `kintsugi.py` | `L2425–L2440` | In `_gold_solid_omitted`, use tolerance `abs(gold_mesh.volume) <= 1e-6` and `len(gold_mesh.faces) == 0`. |
| `kintsugi.py` | `L2330–L2350` | Update docstrings for `_vein_cutter_points` and backing guarantee to state: nominal backing $\ge 0.5 \cdot t_i$ everywhere, and $\ge 0.8\text{ mm}$ wherever $t_i \ge 1.6\text{ mm}$. |
| `openspec/changes/ceramic-vessel-wall-envelope/tasks.md` | `L34–L42` | Track Patch 01 tasks. |
| `openspec/changes/ceramic-vessel-wall-envelope/patch.md` | `L1–L30` | Update PATCH-01 status upon completion. |
| `openspec/changes/ceramic-vessel-wall-envelope/verification.md` | `L180–L240` | Refresh test matrix and exact backing documentation. |

## 3. Blast Radius & Invariant Guardrails
- **STRICT BLAST RADIUS**: Modify ONLY the lines and files specified in the Target Context Map.
- **FORBIDDEN**:
  - Do NOT modify `.env` or credential files.
  - Do NOT modify existing passing tests unless extending assertion coverage.
  - Do NOT alter core CSG algorithms or Voronoi generator.
- **INVARIANTS TO PRESERVE**: All 53 existing unit tests MUST continue to pass; 0 crossings across 1,200 seeds; 0 retries.

## 4. Visual & UI Impact
- **Status: Non-visual patch.** No styling or layout modifications permitted.

## 5. Reproduction & Verification Protocol
1. **Reproduce / Scaffold First**: Run `.venv/bin/python -m unittest tests/test_envelope.py -v`. Confirm new flared-cone tests fail before implementation or pass once implemented.
2. **Apply Minimal Fixes**:
   - Add `_flared_cone` fixture in `tests/test_envelope.py`.
   - Update fallback logic in `kintsugi.py:project_crack_paths`.
   - Add tapered-lip test in `tests/test_kintsugi.py`.
   - Update volume tolerance in `kintsugi.py:_gold_solid_omitted`.
   - Add empty-gold test in `tests/test_web_api.py`.
   - Align docstrings and verification text.
3. **Verify Targeted Tests**: Run `.venv/bin/python -m unittest tests/test_envelope.py tests/test_kintsugi.py tests/test_web_api.py -v`.
4. **Full Regression Suite**: Run `.venv/bin/python -m unittest discover -s tests -v`. Confirm 100% clean passes.

## 6. Surgical Patch Checklist
- [ ] P01.1 Scaffold flared-cone fixture pair in `tests/test_envelope.py`: 1.2 mm normal wall (45° flare) rejected, 2.0 mm accepted
- [ ] P01.2 Apply conservative normal-ray miss fallback $\min(t_{\text{normal}}, t_{\text{radial}})$ in `kintsugi.py`
- [ ] P01.3 Add tapered-lip test fixture and verify continuous gold carving, reporting minimum carved depth and ceramic backing
- [ ] P01.4 In `kintsugi.py`, replace exact float compare in `_gold_solid_omitted` with `1e-6` volume tolerance
- [ ] P01.5 Add end-to-end empty-gold pipeline test in `tests/test_web_api.py` with patched empty cutter
- [ ] P01.6 Update docstrings, `patch.md`, and `verification.md` with exact backing/depth wording and test results
