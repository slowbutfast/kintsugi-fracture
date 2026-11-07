## Executive Summary & Environment

- **Status**: PASS including PATCH-01. Every automated requirement gate is green: 43/43 unit tests, 200/200 held-out growth-audit seeds with zero crossings and zero clearance violations, a 160/160 watertight growth-mode sweep with zero cutter retries, a 12-panel labelled visual contact sheet, and an empty-gold reproduction that writes no gold file and reports `seams_omitted: true`.
- **Date verified**: 2026-11-07
- **Environment**: Linux 5.15.0-1081-oracle-aarch64 (aarch64, Neoverse-N1) / Python 3.11.2 (`/home/node/.../keen-heron/.venv/bin/python`, symlinked to the project virtualenv) / `unittest` via `python -m unittest discover -s tests -v`
- **Packages**: numpy 2.4.6, scipy 1.17.1, trimesh 5.2.0, manifold3d 3.5.4, fastapi 0.162.0, httpx 0.28.1, rtree 1.4.1
- **Source fingerprint**: `09da3a5e157d6eb1` (PATCH-01 working tree; report `reports/test-report-dcbc9ce0e762-Linux-aarch64.json`)
- **Data preservation**: input volume is conserved by the ceramic+gold complement in every sweep run; no samples were dropped. The 160-sample sweep reports `clean=160`, `nonwatertight=0`, `errors=0`, `cutter_attempts={"1": 160}`.

## Requirement Adherence Audit Matrix

| Capability | Requirement & Scenario | Verification Method / Test File | Status |
| :--- | :--- | :--- | :--- |
| `mesh-fracture-engine` | **Metric R validation and clamping**<br>`#### Scenario: Valid inequality metric` | `tests/test_kintsugi.py::test_input_validation`; `test_parameter_table` (`N=6`, `W=1.64`, `H=0.68*60`) | **PASS** |
| `mesh-fracture-engine` | **Metric R validation and clamping**<br>`#### Scenario: Wealthy threshold` | `tests/test_kintsugi.py::test_wealthy_case`; `test_web_api.py::test_api_fracture_wealthy` | **PASS** |
| `mesh-fracture-engine` | **Metric R validation and clamping**<br>`#### Scenario: Negative metric` | `tests/test_kintsugi.py::test_input_validation` (`compute_severity(-0.5) == 1.0`) | **PASS** |
| `mesh-fracture-engine` | **Metric R validation and clamping**<br>`#### Scenario: Non-finite metric` | `tests/test_kintsugi.py::test_input_validation` (NaN / ±inf raise `ValueError`) | **PASS** |
| `mesh-fracture-engine` | **Metric R validation and clamping**<br>`#### Scenario: Thin-wall ceramic clearance in vein mode` | `tests/test_kintsugi.py::test_vein_depth_and_kissing_prevention`; `test_thin_wall_model_manifold`; `tools/growth_audit.py` min-clearance | **PASS** |
| `mesh-fracture-engine` | **Metric R validation and clamping**<br>`#### Scenario: Sub-millimetre thin wall cutter omission` | `tests/test_kintsugi.py::test_vein_depth_and_kissing_prevention` (two split groups, `d >= 0.25`, `t=1.0/0.9` omitted); `test_thin_wall_model_manifold` | **PASS** |
| `mesh-fracture-engine` | **Metric R validation and clamping**<br>`#### Scenario: Empty gold solid` | `tests/test_kintsugi.py::test_empty_gold_solid_omits_file_and_warns` (thin_cylinder, R=0.62, seed=620); `output/verification/thin_cylinder_empty_gold/summary.json` | **PASS** |
| `mesh-fracture-engine` | **Parameter-space crack generation**<br>`#### Scenario: Rim-seeded crack growth` | `tests/test_kintsugi.py::test_growth_rim_seeding_and_penetration`; `tools/growth_audit.py` (200 seeds) | **PASS** |
| `mesh-fracture-engine` | **Parameter-space crack generation**<br>`#### Scenario: Growth budgets and jittered penetration` | `tests/test_kintsugi.py::test_growth_rim_seeding_and_penetration` (`std(terminals) > 0.5 mm`, `ptp > 0.5 mm`) | **PASS** |
| `mesh-fracture-engine` | **Parameter-space crack generation**<br>`#### Scenario: Stop-on-hit collision and first-hit forward snapping` | `tests/test_kintsugi.py::test_growth_paths_planar_and_tjunc`; `_forward_t_junction`; generation-time junction metadata; `tools/growth_audit.py` | **PASS** |
| `mesh-fracture-engine` | **Parameter-space crack generation**<br>`#### Scenario: Grazing approach resolution` | `tests/test_kintsugi.py::test_growth_paths_planar_and_tjunc` (`min_incidence_deg >= 30`); audit min incidence `30.7°` | **PASS** |
| `mesh-fracture-engine` | **Parameter-space crack generation**<br>`#### Scenario: Secondary dendritic branching and junction exemption` | `tests/test_kintsugi.py::test_growth_paths_planar_and_tjunc` (`min_departure_deg >= 30`); 2–3 branches/trunk; lateral angles up to 85°; `_segment_outside_circle`; T/Y distribution reported without a pass gate | **PASS** |
| `mesh-fracture-engine` | **Parameter-space crack generation**<br>`#### Scenario: Deterministic growth order` | `tests/test_kintsugi.py::test_determinism` (byte-identical STL/3MF for repeated seed) | **PASS** |
| `mesh-fracture-engine` | **Parameter-space crack generation**<br>`#### Scenario: Shipped growth graph is planar` | `tests/test_kintsugi.py::test_growth_paths_planar_and_tjunc`; `tools/growth_audit.py` `cross=0` for all 1,600 preset×severity×seed runs across seed ranges 0–199 and 300–499 | **PASS** |
| `mesh-fracture-engine` | **Parameter-space crack generation**<br>`#### Scenario: Radial projection takes the exterior hit and clamps rim overshoot` | `tests/test_kintsugi.py::test_seed_sweep_watertight`, `test_stl_disk_roundtrip`; rim-clamping code path in `project_crack_paths` exercised by every growth render | **PASS** |
| `mesh-fracture-engine` | **Parameter-space crack generation**<br>`#### Scenario: Ray miss` | `tests/test_kintsugi.py::test_input_envelope_rejection`; `test_vessel_without_wall_range_rejected`; 160/160 sweep clean | **PASS** |
| `mesh-fracture-engine` | **Parameter-space crack generation**<br>`#### Scenario: Perturbed points are truncated at the wall` | `tests/test_kintsugi.py::test_growth_rim_seeding_and_penetration`; `test_wall_range_clamp_keeps_gold_out_of_floor`; 160/160 sweep clean | **PASS** |
| `retro-web-gui` | **Real-time parameter controls and fracture execution**<br>`#### Scenario: Triggering fracture computation with vein default` | `tests/test_web_api.py::test_api_fracture_defaults_to_vein_growth` (`parameters.mode == "vein"`, `parameters.generator == "growth"`); `static/index.html` radio `value="vein" checked` | **PASS** |
| `retro-web-gui` | **Real-time parameter controls and fracture execution**<br>`#### Scenario: Wealthy parameter setting` | `tests/test_web_api.py::test_api_fracture_wealthy`; `tests/test_kintsugi.py::test_wealthy_case` | **PASS** |

## Resolved Assumptions & Empirical Proof

| Assumption from research.md | How Verified in Code/Tests | Result / Value | Volatility |
| :--- | :--- | :--- | :--- |
| Random-walk heading with step size 1.5W–3W and cutter subdivision ≤ W/2 does not trigger Manifold3D boolean crashes. | Full 160-sample held-out sweep (`tools/sweep_out_of_sample.py --generator growth`) over 2 presets × 5 ratios × 2 modes × 8 seeds. | `clean=160`, `nonwatertight=0`, `errors=0`, `cutter_attempts={"1":160}`, `cutter_variants={"1":160}`. Median runtime 1.03 s, max 4.35 s. | stable |
| Thin-wall printing with 0.8 mm remaining ceramic is physically leak-proof on standard FDM. | Geometric verification only: `thin_cylinder` R=0.0 3MF reloads as one object with two parts (`CeramicBody`, `GoldSeams`), both watertight; ceramic volume 15,669.12 mm³ vs input 15,683.05 mm³ (99.91% retained); gold volume 13.93 mm³. Slicer GUI unavailable in this environment. | **Partially verified** (geometry + container). Print toolpath check deferred (see deferrals). | decays (printer/profile dependent) |
| R_exempt = (W + 0.8) / sin θ prevents newborn branches colliding with parents without hiding crossings. | Initial contact-based exemption allowed a branch to run parallel to a parent beyond the circle. Replaced by `_segment_outside_circle` clipping plus an actual-intersection override; both 200-seed audits now `clear=0`, `cross=0`. | `min_clearance=2.440 mm` vs `R_clear=2.44 mm` at S=0.6; `3.000 mm` vs `3.00 mm` at S=1.0. | stable |
| Median arc/chord tortuosity ≥ 1.05 is achievable with a correlated random walk plus lateral branches. | `tests/test_kintsugi.py::test_growth_tortuosity_floor`; both 200-seed audits. | Per-row medians: 1.076, 1.062, 1.079, 1.051; overall median 1.065; p05 1.000 in all rows. | stable |
| A unified nearest-contact snap inside R_clear is sufficient to form T-junctions. | Initial near-miss handling stopped short and created parallel rain streaks. Growth now projects the candidate travel vector forward to the first safe intersection, snaps to it, and subdivides the hit segment; grazing or unsafe projections resample/stop. | Audit: 0 crossings, 0 clearance violations over 1,600 runs (two 200-seed ranges × 4 rows). | stable |

## Nomenclature & Code Symbol Audit

| Glossary Term | Final Code Identifier | Location / File | Verified Compliant? |
| :--- | :--- | :--- | :--- |
| Sequential Crack Growth | `generate_crack_growth_paths` | `kintsugi.py` | Yes |
| Legacy Voronoi generator | `generate_crack_voronoi_paths` | `kintsugi.py` | Yes |
| Drop-in generator seam | `generate_crack_paths(..., generator="growth"|"voronoi")` | `kintsugi.py` | Yes |
| Stop-on-Hit / shared vertex subdivision | `_first_growth_collision`, `_forward_t_junction`, `_subdivide_path` | `kintsugi.py` | Yes |
| Junction Exemption Zone | `_segment_outside_circle`, `exempt_radius` | `kintsugi.py` | Yes |
| Growth graph audit | `analyze_growth_paths`, `tools/growth_audit.py` | `kintsugi.py`, `tools/` | Yes |
| Vein Inlay Mode | `_build_vein_cutter`, `_vein_point_groups` | `kintsugi.py` | Yes |
| Zero-depth kissing prevention | `GROWTH_MIN_DEPTH_MM = 0.25`, `_vein_point_groups` omission | `kintsugi.py` | Yes |
| Empty-gold omission | `_gold_solid_omitted`, `seams_omitted` | `kintsugi.py` | Yes |
| Labelled contact sheet | `_draw_text`, `_FONT`, `CASES` labels | `tools/spike_contact_sheet.py` | Yes |
| FastAPI fracture route | `POST /api/fracture` with form fields `mode`, `generator` | `web_app.py` | Yes |
| Thin-wall calibration vessel | `thin_cylinder` preset | `sample_models.py` | Yes |

## Landed Tech Footprint & Patterns

| Adopted Pattern / Package | Implementation File(s) | Verification Command / Suite |
| :--- | :--- | :--- |
| Rim-seeded FIFO growth with bounded random-walk heading | `kintsugi.py` (`generate_crack_growth_paths`, `_GrowthTask`) | `tests/test_kintsugi.py::test_growth_rim_seeding_and_penetration`, `test_growth_tortuosity_floor` |
| Periodic seam wrapping (±2πr̄) and periodic copy collision checks | `kintsugi.py` (`period`, shifted segment evaluation) | `tests/test_kintsugi.py::test_growth_paths_planar_and_tjunc`; growth audit 1,600 runs |
| Stop-on-hit forward projection and shared-vertex subdivision | `kintsugi.py` (`_first_growth_collision`, `_forward_t_junction`, `_subdivide_path`) | `test_growth_paths_planar_and_tjunc`; 1,600 audit runs with 0 crossings |
| Correlated heading walk, 2–3 branches per trunk, lateral 30–85° linkers | `kintsugi.py` (`_GrowthTask`, `_branch_heading`) | `test_growth_tortuosity_floor`; audit median tortuosity 1.065 |
| Junction exemption clipping | `kintsugi.py` (`_segment_outside_circle`) | audit clearance 0 violations over 1,600 runs |
| Vein depth formula and sub-0.25 mm omission | `kintsugi.py` (`_vein_point_groups`) | `test_vein_depth_and_kissing_prevention`, `test_thin_wall_model_manifold` |
| Empty-gold file/3MF omission | `kintsugi.py` (`_gold_solid_omitted`, `export_kintsugi_stl`, `export_kintsugi_3mf`) | `test_empty_gold_solid_omits_file_and_warns` |
| Thin-wall vessel fixture | `sample_models.py` (`thin_cylinder`, `create_thin_cylinder_preset`) | `test_thin_wall_model_manifold`, empty-gold repro |
| Growth audit tool (T/Y informational, not gated) | `tools/growth_audit.py` | `python tools/growth_audit.py --seeds 300-499` |
| Labelled contact sheet renderer (pure numpy z-buffer, no new deps) | `tools/spike_contact_sheet.py` | `python tools/spike_contact_sheet.py --output output/spike/contact_sheet.png` |
| Full report integration and renders | `tools/test_report.py` | `python tools/test_report.py run --profile full --renders` |
| Generator CLI switch | `tools/sweep_out_of_sample.py`, `kintsugi.py` CLI | 160-sample growth sweep |
| Vein Inlay default in XP GUI | `static/index.html`, `static/viewer.js`, `static/xp.css`, `web_app.py` | `tests/test_web_api.py::test_api_fracture_defaults_to_vein_growth` |

## Invalidated Hypotheses & Mid-Build Adjustments

| Original Belief | What Proved Wrong | Final Resolution | Rationale |
| :--- | :--- | :--- | :--- |
| Any contact within `R_clear` can be snapped to the closest point on the hit segment. | For a near miss, the closest point is not on the candidate travel vector; the resulting oblique connector could cross another crack. PATCH-01 also showed the prior conservative behaviour left disconnected parallel “rain streaks”. | Project the candidate travel vector forward to its intersection with the hit segment, bounded to `max(2·step, 4·R_clear)` and revalidated against other segments; snap/subdivide at that shared vertex. Grazing or unsafe projections resample, then stop at the last committed point. | Preserves planarity while forming the T-junctions the spec requires. |
| Exempting an entire parent segment within `R_exempt` of the branch origin is safe. | A long parent segment containing the origin was fully exempt, letting the child run parallel to the parent beyond the exemption circle. | Clip the parent segment to its portion outside the exemption circle; always honour an actual intersection even inside the circle. | Exemption forgives proximity, never a real crossing. |
| The 80% T-junction ratio gate should be a pass/fail requirement. | The gate shaped the morphology and suppressed branching; PATCH-01 review found the generator produced parallel streaks and too few junctions. | Remove the T-ratio from the growth-audit gate; report T/Y distribution informationally. Allow 2–3 branches per trunk at ~0.22·S, with 30–45° whiskers and up to 85° lateral linkers. | T/Y remains reported (1.000 T-like in the current metadata) but no longer dictates generation. |
| A single branch per trunk and a 32° heading jitter were enough. | Median tortuosity fell and the morphology lacked lateral cross-links. | Use a correlated heading walk (50% sharp ±80° kinks, otherwise inertia σ=20°) and 2–3 branches per trunk. | Median tortuosity 1.051–1.079 per audit row; visible lateral links in the contact sheet. |
| An empty gold manifold is safe to export as a zero-triangle STL. | `export_kintsugi_stl` checked only `gold is None`; `thin_cylinder` at R=0.62, seed=620 produced an 84-byte, 0-triangle `gold_seams.stl`. | Treat `gold is None`, `gold.is_empty()`, `num_tri()==0`, or a zero-face export mesh as omitted: unlink any stale STL, omit `GoldSeams` from the 3MF, and report `seams_omitted: true`, `num_cracks: 0`. | No degenerate file can be mistaken for a printable seam. |
| A nominal `R_exempt` boundary is numerically sufficient. | Discrete geodesic offsets produced 2.99 mm clearance at a 3.00 mm trigger. | Apply a 1.10× numeric margin to `R_exempt` (still conservative relative to the 30° lower bound). | Eliminates boundary-straddling false violations; documented in code. |
| Geometric post-hoc junction inference is enough for audit angles. | Shared vertices with several incident paths caused the wrong parent segment to be selected. | Record generation-time junction metadata (`_growth_junctions`) and use it for incidence/departure metrics. | Honest measurement of the actual parent and arrival angles. |

## PATCH-01 Resolution

- **Status**: **RESOLVED** on 2026-11-07.
- **Blocker 1 — empty gold STL**: Reproduced on `thin_cylinder` at R=0.62, seed=620: the old exporter wrote an 84-byte, zero-triangle `gold_seams.stl`. Fixed in `_gold_solid_omitted` / `export_kintsugi_stl` / `export_kintsugi_3mf` / `generate_kintsugi_mesh`. The new reproduction test asserts no gold file, no `GoldSeams` in the 3MF, `gold_path: None`, `seams_omitted: true`, `num_cracks: 0`, and zero gold triangles.
- **Blocker 2 — near-miss rain streaks**: Replaced stop-short resampling with bounded forward projection to the hit segment (`_forward_t_junction`). The projected segment is revalidated against all cracks; only grazing (<30°) or unsafe projections resample. Shared T-junctions are subdivided at the projected intersection.
- **Morphology tuning**: Heading limits expanded to ±85° from straight down; the walk is now correlated (mostly inertia, with 50% sharp kinks); trunks allow 2–3 branches at ~0.22·S with 30–45° whiskers and up to 85° lateral linkers. The contact sheet shows connected lateral fissures instead of parallel streaks.
- **Audit gate removal**: `tools/growth_audit.py` no longer fails on an 80% T-ratio. T/Y distribution remains reported as an informational morphology metric.
- **Contact sheet**: Rows are labelled (`TEA BOWL R=0`, `TEA BOWL R=0.2`, `TALL VASE R=0.2`, `THIN CYLINDER R=0.5`); the thin-cylinder row intentionally shows the empty-gold omission.
- **Evidence**:
  - `tests/test_kintsugi.py::test_empty_gold_solid_omits_file_and_warns`
  - `output/verification/thin_cylinder_empty_gold/summary.json`
  - `output/verification/growth_audit.json`
  - `output/verification/growth_audit_seeds_0_199.json`
  - `output/verification/sweep_out_of_sample_patch01.json`
  - `output/spike/contact_sheet.png` / `reports/contact_sheet.png`

## Implementation-Discovered Deferrals

- **Deferred Item**: Bambu Studio / PrusaSlicer GUI import and toolpath backing check for the `thin_cylinder` assembly.
  - **Reason**: Neither slicer CLI nor GUI is installed in this environment (`which bambu-studio prusa-slicer PrusaSlicer` returned nothing).
  - **Evidence completed**: `output/verification/thin_cylinder_slicer/kintsugi_assembly.3mf` reloads as one object with two components; both STLs are watertight; ceramic retains 15,669.12 / 15,683.05 mm³ (99.91%) and gold fills 13.93 mm³. The empty-gold reproduction at R=0.62 is separately recorded in `output/verification/thin_cylinder_empty_gold/`. Manual slicer import remains a human workstation step.
- **Deferred Item**: Physical print leak test on a standard FDM 2-perimeter profile.
  - **Reason**: Requires hardware and a slicer profile.
  - **Evidence completed**: Geometric backing and manifold checks above.
- **Scheduled Deprecation**: Legacy Voronoi is retained only as the internal `--generator voronoi` CLI/test flag. It is not exposed in the web GUI. Remove it after two consecutive green growth-mode full profiles and one release of comparative A/B audits. Target: next change after `kintsugi-crack-growth`.

## Empirical Execution Logs & Evidence

### Full regression suite (TDD green phase)

```text
$ .venv/bin/python -m unittest discover -s tests -v
...
----------------------------------------------------------------------
Ran 43 tests in 206.182s

OK
```

### Full verification profile with contact sheet

```text
$ .venv/bin/python tools/test_report.py run --profile full --renders
=== KINTSUGI TEST REPORT v1 ===
overall: PASS
created_utc: 2026-11-07T16:57:26Z
profile: full
fingerprint: 09da3a5e157d6eb1
host: Linux-5.15.0-1081-oracle-aarch64 | Neoverse-N1 | python 3.11.2
packages: numpy=2.4.6 scipy=1.17.1 trimesh=5.2.0 manifold3d=3.5.4 fastapi=0.162.0 httpx=0.28.1 rtree=1.4.1
suite unit: PASS ran=43 passed=43 failed=0 errors=0 skipped=0 time=207.8s
suite growth_audit: PASS seeds=200 crossings=0 clearance=0 T-ratio=1.000 tort=1.065 errors=0 time=355.7s
suite crack_graph_audit: PASS rows=4 phantom=0 crossing=0 clamp_max=0.0% time=15.6s
suite sweep: PASS total=160 clean=160 nonwatertight=0 errors=0 retries=0 median=1.03s time=226.8s
suite noise_fold: PASS fold_max=0.0% max_grad=0.70 crossing_seeds=0/1200 time=22.9s
suite renders: PASS path=reports/contact_sheet.png bytes=83967 time=95.7s
=== END KINTSUGI TEST REPORT ===
```

### Growth audit on held-out seeds 300–499

```text
$ .venv/bin/python tools/growth_audit.py --presets tea_bowl vase \
    --severities 0.6 1.0 --seeds 300-499 --output output/verification/growth_audit.json
    tea_bowl S=0.6  seeds=200  cross=0  clear=0  min_clear=2.445 min_inc=32.0 T-ratio=1.000 T/Y=1080/0 tort=1.076/1.000 err=0
    tea_bowl S=1    seeds=200  cross=0  clear=0  min_clear=3.000 min_inc=30.7 T-ratio=1.000 T/Y=2648/0 tort=1.062/1.000 err=0
        vase S=0.6  seeds=200  cross=0  clear=0  min_clear=2.449 min_inc=30.7 T-ratio=1.000 T/Y=1163/0 tort=1.079/1.000 err=0
        vase S=1    seeds=200  cross=0  clear=0  min_clear=3.002 min_inc=31.4 T-ratio=1.000 T/Y=2494/0 tort=1.051/1.000 err=0
growth audit PASS: seeds=200 rows=4 crossings=0 clearance=0 min_clear=2.445 T-ratio=1.000 tort=1.065 errors=0
```

### Growth audit on the low seed range 0–199

```text
$ .venv/bin/python tools/growth_audit.py --presets tea_bowl vase \
    --severities 0.6 1.0 --seeds 0-199 --output output/verification/growth_audit_seeds_0_199.json
    tea_bowl S=0.6  seeds=200  cross=0  clear=0  min_clear=2.440 min_inc=31.0 T-ratio=1.000 T/Y=1074/0 tort=1.082/1.000 err=0
    tea_bowl S=1    seeds=200  cross=0  clear=0  min_clear=3.001 min_inc=30.2 T-ratio=1.000 T/Y=2534/0 tort=1.062/1.000 err=0
        vase S=0.6  seeds=200  cross=0  clear=0  min_clear=2.442 min_inc=30.7 T-ratio=1.000 T/Y=1145/0 tort=1.077/1.000 err=0
        vase S=1    seeds=200  cross=0  clear=0  min_clear=3.000 min_inc=30.3 T-ratio=1.000 T/Y=2539/0 tort=1.055/1.000 err=0
growth audit PASS: seeds=200 rows=4 crossings=0 clearance=0 min_clear=2.440 T-ratio=1.000 tort=1.066 errors=0
```

### 160-sample held-out sweep (growth generator)

```json
{
  "total": 160,
  "counts": {"ok": 160},
  "clean": 160,
  "nonwatertight": 0,
  "errors": 0,
  "cutter_attempts": {"1": 160},
  "cutter_variants": {"1": 160},
  "run_time_median_s": 1.0182810742408037,
  "run_time_max_s": 4.322233031503856
}
```

### Thin-wall 3MF structural audit (R=0.0, seed=0)

```json
{
  "result": {
    "num_cracks": 18,
    "seams_omitted": false,
    "cutter_attempts": 1,
    "cutter_variants": 1,
    "triangle_counts": {"ceramic": 4652, "gold": 3868},
    "volumes": {
      "input": 15683.053137730956,
      "ceramic": 15669.12377927447,
      "gold": 13.929358456486405,
      "pre_swap_ceramic": 15669.12377927447,
      "pre_swap_gold": 13.929358456486405
    }
  },
  "ceramic_watertight": true,
  "gold_watertight": true,
  "3mf_has_ceramic": true,
  "3mf_has_gold": true,
  "3mf_component_count": 2
}
```

### Empty-gold reproduction (thin_cylinder, R=0.62, seed=620)

```json
{
  "result": {
    "gold_path": null,
    "num_cracks": 0,
    "seams_omitted": true,
    "cutter_attempts": 1,
    "cutter_variants": 1,
    "triangle_counts": {"ceramic": 768, "gold": 0},
    "volumes": {
      "input": 15683.053137730956,
      "ceramic": 15683.053137730956,
      "gold": 0.0,
      "pre_swap_ceramic": 15683.053137730956,
      "pre_swap_gold": 0.0
    }
  },
  "gold_file_exists": false,
  "ceramic_watertight": true,
  "3mf_has_ceramic": true,
  "3mf_has_gold": false,
  "3mf_component_count": 1
}
```

### Agent Visual Inspection Notes — `output/spike/contact_sheet.png`

- **Date inspected**: 2026-11-07
- **Method**: The 12-panel PNG was rendered by `tools/spike_contact_sheet.py` and inspected directly. The `reports/contact_sheet.png` copy is produced by the full profile. All four rows carry bitmap labels and the thin-cylinder row is R=0.5.
- **Result**: **AGENT REVIEW — PASS (human sign-off pending)**. Primary trunks originate at the rim and cascade downwards; whisker fissures and lateral 30–85° linkers connect adjacent cracks, eliminating the parallel “rain streak” look. No Voronoi honeycomb cell tiling is visible. The tea-bowl top view shows gold seam entries at the lip without a flat horizontal shelf. The thin-cylinder R=0.5 row intentionally shows the empty-gold omission: no gold channel and no gold facet, matching the `seams_omitted` behaviour. Task 2.4 remains open for a human reviewer to confirm this against reference Kintsugi morphology.

### TDD red-phase record

The original five invariant tests were added before implementation and failed as expected with `AttributeError` for `generate_crack_growth_paths` / `_vein_point_groups` and `AssertionError` for the missing `thin_cylinder` builder. For PATCH-01, `test_empty_gold_solid_omits_file_and_warns` was added first and failed with `KeyError: 'seams_omitted'` before the exporter fix; it now passes.

## Quick Re-Verification (60-Second Audit)

```bash
# 1) Growth + empty-gold invariants (about 25 s)
.venv/bin/python -m unittest \
  tests.test_kintsugi.KintsugiTestCase.test_growth_paths_planar_and_tjunc \
  tests.test_kintsugi.KintsugiTestCase.test_growth_tortuosity_floor \
  tests.test_kintsugi.KintsugiTestCase.test_growth_rim_seeding_and_penetration \
  tests.test_kintsugi.KintsugiTestCase.test_empty_gold_solid_omits_file_and_warns -v

# 2) Short held-out audit (about 15 s)
.venv/bin/python tools/growth_audit.py \
  --presets tea_bowl vase --severities 0.6 1.0 --seeds 0-10 \
  --output /tmp/growth_audit_smoke.json
```

Expected output:

```text
Ran 4 tests ... OK
growth audit PASS: seeds=11 rows=4 crossings=0 clearance=0 ... errors=0
```
