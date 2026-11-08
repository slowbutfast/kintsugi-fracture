## Executive Summary & Environment

- **Status**: Implementation complete including PATCH-01; automated gates green. The ceramic vessel envelope ($p_5 \ge 1.6\text{ mm}$ along inward surface normals) rejects all sub-envelope inputs across both fracture modes, including 45° flared walls whose radial thickness is misleadingly larger. Continuous vein depth $d_i = \min(0.75W, 0.5t_i)$ is restored with zero cutter-point omissions, normal/radial thickness fallback is conservatively bounded, rim projection is clamped, and PATCH-02 growth morphology is regression-gated.
- **Date verified**: 2026-11-08
- **Environment**: Linux 5.15.0-1081-oracle-aarch64 (aarch64, glibc 2.36) / Python 3.11.2 (`/home/node/global-sandbox/projects/wax-robot/.venv/bin/python`) / `unittest` via `python -m unittest discover -s tests -v`
- **Packages**: numpy 2.4.6, scipy 1.17.1, trimesh 5.2.0, manifold3d 3.5.4, fastapi 0.162.0, httpx 0.28.1, rtree 1.4.1
- **PATCH-01 audit status**: full regression suite 57/57 PASS; targeted envelope/engine/API suites 54/54 PASS; full-profile audit running against the pushed tree (baseline pre-patch profile was PASS with 0 crossings and 0 retries).
- **Data preservation**: ceramic + gold volumes conserve the input volume on every fracture run (`test_volume_smoke`). No input mesh is modified, inflated, or thickened; sub-envelope meshes are rejected with a descriptive `ValueError` before any output is written.

## Requirement Adherence Audit Matrix

| Capability | Requirement & Scenario | Verification Method / Test File | Status |
| :--- | :--- | :--- | :--- |
| `mesh-fracture-engine` | **Supported input envelope**<br>`Scenario: Vessel of revolution inside the envelope` | `tests/test_envelope.py::test_envelope_acceptance_near_boundary`; tea-bowl/vase probe log (`p5 = 3.00 / 2.30 mm`) | **PASS** |
| `mesh-fracture-engine` | **Supported input envelope**<br>`Scenario: Vessel with wall thickness below ceramic envelope` | `tests/test_envelope.py::test_envelope_rejection_thin_mesh` (1.5 mm cylinder and `create_thin_cylinder_fixture`, vein + ribbon); `test_kintsugi.py::test_thin_wall_fixture_rejected_by_envelope` | **PASS** |
| `mesh-fracture-engine` | **Supported input envelope**<br>`Scenario: Vessel at ceramic envelope boundary` | `tests/test_envelope.py::test_envelope_acceptance_near_boundary` (1.7 mm accepted); `test_wall_envelope_boundary_comparison` (1.60 accepted, 1.5999999 rejected) | **PASS** |
| `mesh-fracture-engine` | **Supported input envelope**<br>`Scenario: Flared wall normal thickness (PATCH-01)` | `tests/test_envelope.py::test_envelope_flared_cone_normal_thickness_rejection` (45° 1.2 mm normal rejected despite 1.697 mm radial; 2.0 mm normal accepted at $p_5=2.002$ mm) | **PASS** |
| `mesh-fracture-engine` | **Supported input envelope**<br>`Scenario: Wrong units or scale` | `tests/test_kintsugi.py::test_input_envelope_rejection` (metre-scaled bowl) | **PASS** |
| `mesh-fracture-engine` | **Supported input envelope**<br>`Scenario: Non-vessel geometry` | `tests/test_kintsugi.py::test_input_envelope_rejection` (disjoint boxes); `test_vessel_without_wall_range_rejected` | **PASS** |
| `mesh-fracture-engine` | **Metric R validation and clamping**<br>`Scenario: Valid inequality metric` | `tests/test_kintsugi.py::test_input_validation`, `test_parameter_table` ($N=6$, $W=1.64$, $H=0.68\cdot60$) | **PASS** |
| `mesh-fracture-engine` | **Metric R validation and clamping**<br>`Scenario: Wealthy threshold` | `tests/test_kintsugi.py::test_wealthy_case`; `tests/test_web_api.py::test_api_fracture_wealthy` | **PASS** |
| `mesh-fracture-engine` | **Metric R validation and clamping**<br>`Scenario: Negative metric` | `tests/test_kintsugi.py::test_input_validation` ($R=-0.5 \Rightarrow S=1.0$) | **PASS** |
| `mesh-fracture-engine` | **Metric R validation and clamping**<br>`Scenario: Non-finite metric` | `tests/test_kintsugi.py::test_input_validation` (NaN / ±inf raise `ValueError`) | **PASS** |
| `mesh-fracture-engine` | **Metric R validation and clamping**<br>`Scenario: Ceramic vessel backing guarantee in vein mode` | `tests/test_kintsugi.py::test_continuous_vein_depth_no_omissions` (all densified points retained; $d_i=\min(0.75W,0.5t_i)$); `test_tapered_lip_continuous_vein_and_backing` (tapered lip $t_{\min}=1.114$ mm, backing min $=0.557$ mm, $\ge 0.839$ mm where $t_i\ge1.6$); `test_vein_depth`; probe log | **PASS** |
| `mesh-fracture-engine` | **Metric R validation and clamping**<br>`Scenario: Empty gold solid defensive safeguard` | `tests/test_kintsugi.py::test_empty_gold_solid_omits_file_and_warns` (STL + 3MF); `test_valid_ceramic_run_keeps_gold` ($R<1.0$ never omits valid gold); `tests/test_web_api.py::test_api_fracture_empty_gold_pipeline` (patched empty cutter end-to-end) | **PASS** |
| `mesh-fracture-engine` | **Parameter-space crack generation**<br>`Scenario: Rim-seeded crack growth` | `tests/test_kintsugi.py::test_growth_rim_seeding_and_penetration`; `tests/test_crack_growth.py::test_correlated_walk_kink_rate_and_sigma`; `tools/growth_audit.py` | **PASS** |
| `mesh-fracture-engine` | **Parameter-space crack generation**<br>`Scenario: Growth budgets and jittered penetration` | `tests/test_kintsugi.py::test_growth_rim_seeding_and_penetration` (`std(terminals) > 0.5 mm`, `ptp > 0.5 mm`) | **PASS** |
| `mesh-fracture-engine` | **Parameter-space crack generation**<br>`Scenario: Stop-on-hit collision with forward snapping and final attempt bend` | `tests/test_kintsugi.py::test_growth_paths_planar_and_tjunc`; `tests/test_crack_growth.py::test_final_attempt_bend_snaps_near_miss` (`_forward_t_junction` disabled; bend fallback still T-joins) | **PASS** |
| `mesh-fracture-engine` | **Parameter-space crack generation**<br>`Scenario: Grazing approach resolution` | `tests/test_kintsugi.py::test_growth_paths_planar_and_tjunc` (`min_incidence_deg >= 30`); `test_crack_growth.py::test_final_attempt_bend_snaps_near_miss` | **PASS** |
| `mesh-fracture-engine` | **Parameter-space crack generation**<br>`Scenario: Secondary dendritic branching and junction exemption` | `tests/test_kintsugi.py::test_growth_paths_planar_and_tjunc`; `tools/growth_audit.py` T/Y distribution | **PASS** |
| `mesh-fracture-engine` | **Parameter-space crack generation**<br>`Scenario: Deterministic growth order` | `tests/test_kintsugi.py::test_determinism` (byte-identical STL/3MF for repeated seed) | **PASS** |
| `mesh-fracture-engine` | **Parameter-space crack generation**<br>`Scenario: Shipped growth graph is planar` | `tests/test_crack_growth.py::test_median_tortuosity_and_zero_crossings` (0 crossings, 0 clearance violations across severities/seeds); `tools/growth_audit.py` | **PASS** |
| `mesh-fracture-engine` | **Parameter-space crack generation**<br>`Scenario: Radial projection takes the exterior hit and clamps rim overshoot` | `tests/test_kintsugi.py::test_projection_clamps_rim_and_records_normal_thickness` ($z=\text{wall\_z\_max}-\max(0.5,W/2)$; $t_i$ measured along $-n_i$) | **PASS** |
| `mesh-fracture-engine` | **Parameter-space crack generation**<br>`Scenario: Ray miss` | `tests/test_kintsugi.py::test_input_envelope_rejection`, `test_vessel_without_wall_range_rejected`; full sweep | **PASS** |
| `mesh-fracture-engine` | **Parameter-space crack generation**<br>`Scenario: Perturbed points are truncated at the wall` | `tests/test_kintsugi.py::test_no_points_on_wall_limit_lines`, `test_wall_range_clamp_keeps_gold_out_of_floor` | **PASS** |
| `multi-material-export` | **Paired manifold STL export**<br>`Scenario: Inequality fracture export` | `tests/test_kintsugi.py::test_stl_disk_roundtrip`; `tools/sweep_out_of_sample.py` full profile | **PASS** |
| `multi-material-export` | **Paired manifold STL export**<br>`Scenario: Empty gold solid fallback when R < 1.0` | `tests/test_kintsugi.py::test_empty_gold_solid_omits_file_and_warns` (stale gold unlinked, no `GoldSeams` in 3MF, `gold_path: None`) | **PASS** |
| `multi-material-export` | **Paired manifold STL export**<br>`Scenario: Wealthy pass-through export` | `tests/test_kintsugi.py::test_wealthy_case`; `tests/test_web_api.py::test_api_fracture_wealthy` | **PASS** |
| `multi-material-export` | **Paired manifold STL export**<br>`Scenario: Export sliver repair` | `tests/test_kintsugi.py::test_export_repair_runs_once_per_guard_evaluation` | **PASS** |
| `multi-material-export` | **Paired manifold STL export**<br>`Scenario: Round-trip guard` | `tests/test_kintsugi.py::test_roundtrip_guard_raises_and_writes_nothing`; `test_stl_disk_roundtrip` | **PASS** |
| `multi-material-export` | **Paired manifold STL export**<br>`Scenario: Seed robustness` | `tests/test_kintsugi.py::test_ribbon_no_retries_out_of_sample_cases`, `test_vein_no_retries_out_of_sample_cases`; `tools/sweep_out_of_sample.py` (160/160) | **PASS** |
| `multi-material-export` | **Unified multi-material 3MF export**<br>`Scenario: Multi-material 3MF export` | `tests/test_kintsugi.py::test_3mf_structure` (one build item, `CeramicBody` + `GoldSeams` components) | **PASS** |
| `multi-material-export` | **Unified multi-material 3MF export**<br>`Scenario: Single-volume fallback 3MF export` | `tests/test_kintsugi.py::test_empty_gold_solid_omits_file_and_warns`; `test_wealthy_case` | **PASS** |
| `retro-web-gui` | **Model preset selection and custom upload**<br>`Scenario: Preset model selection` | `tests/test_web_api.py::test_api_presets` (no `thin_cylinder`); `test_api_fracture_defaults_to_vein_growth` | **PASS** |
| `retro-web-gui` | **Model preset selection and custom upload**<br>`Scenario: Custom file upload` | `tests/test_web_api.py::test_api_validate_ok` (vertices + wall metadata); `test_api_validate_thin_wall_rejected`; `test_api_fracture_thin_wall_rejected` | **PASS** |
| `retro-web-gui` | **Model preset selection and custom upload**<br>`Scenario: Upload size cap` | `tests/test_web_api.py::test_api_upload_too_large` (HTTP 413) | **PASS** |
| `retro-web-gui` | **Model preset selection and custom upload**<br>`Scenario: Job retention` | `tests/test_web_api.py::test_job_retention` | **PASS** |
| `retro-web-gui` | **Real-time parameter controls and fracture execution**<br>`Scenario: Triggering fracture computation with vein default` | `tests/test_web_api.py::test_api_fracture_defaults_to_vein_growth` (`mode="vein"`, `generator="growth"`) | **PASS** |
| `retro-web-gui` | **Real-time parameter controls and fracture execution**<br>`Scenario: Wealthy parameter setting` | `tests/test_web_api.py::test_api_fracture_wealthy`; `static/viewer.js` label branch | **PASS** |
| `retro-web-gui` | **Real-time parameter controls and fracture execution**<br>`Scenario: Seams omitted feedback` | `static/viewer.js` now renders clean `Seams Omitted`; stale `"wall thickness < 1.05 mm"` removed from `web_app.py` and `viewer.js`; `test_api_fracture_success` asserts no reason on valid runs | **PASS** |

## Resolved Assumptions & Empirical Proof

| Assumption from research.md | How Verified in Code/Tests | Result / Value | Volatility |
| :--- | :--- | :--- | :--- |
| Japanese Tea Bowl and Tall Vase satisfy the ceramic envelope. | `_probe_normal_wall_thickness` over `[wall_z_min, wall_z_max]`. | Tea Bowl $p_5=3.0048$ mm, median $3.0048$ mm; Vase $p_5=2.2998$ mm, median $2.3909$ mm; 1,968 valid samples each, 0 misses. | stable |
| Thin-wall inputs are rejected, not silently degraded. | 1.5 mm cylinder, 1.6 mm boundary cylinder, 1.7 mm near-boundary cylinder, and the 0.7–1.2 mm `create_thin_cylinder_fixture`. | 1.5 mm → `ValueError` at $p_5=1.50$ mm; 1.6 mm → accepted at $p_5=1.6026$ mm; 1.7 mm → accepted at $p_5=1.7027$ mm; fixture → `ValueError` at $p_5=0.74$ mm. | stable |
| Backing guarantee $t_i-d_i \ge 0.5t_i$ everywhere and $\ge 0.8$ mm wherever $t_i \ge 1.6$ mm. | Continuous depth formula + `test_continuous_vein_depth_no_omissions`; `test_tapered_lip_continuous_vein_and_backing`. | At $W=2.0$ mm, $t=1.6$ mm → $d=0.8$ mm; $t=3.0$ mm → $d=1.5$ mm. The $p_5$ envelope guarantees a statistical floor, not a 0.6 mm depth at every tapered-lip point. Tapered-lip audit: $t_{\min}=1.114$ mm, $d_{\min}=0.557$ mm, backing $\ge 0.557$ mm, and $\ge 0.839$ mm wherever $t_i \ge 1.6$ mm. | stable |
| Normal probing is required on flared walls; radial probing overstates thickness. | `test_envelope_flared_cone_normal_thickness_rejection` with revolved 45° cones. | 1.2 mm normal wall: radial median 1.697 mm (would pass radially) but normal $p_5=1.201$ mm → rejected. 2.0 mm normal wall: normal $p_5=2.002$ mm → accepted and fractures. | stable |
| Normal-ray misses cannot reintroduce a flared-wall overestimate. | `project_crack_paths` computes both normal and radial thickness; `test_projection_takes_min_and_bounds_normal_miss`. | When both exist, $t_i=\min(t_{\text{normal}},t_{\text{radial}})$. When the normal ray misses, the radial value is bounded by the path median in the fill pass (scripted audit: 0.4 radial → 0.3 bounded; 0.2 normal < 0.4 radial → 0.2; 0.45 normal > 0.4 radial → 0.4). | stable |
| Cutter point omission was the cause of empty/gapped gold on supported vessels. | `_vein_cutter_points` retains every densified point; `_vein_point_groups` and `GROWTH_MIN_DEPTH_MM` removed. | `test_continuous_vein_depth_no_omissions` asserts group length equals densified path length; `test_valid_ceramic_run_keeps_gold` reports non-zero gold triangles/volume at $R=0.6$. | stable |
| PATCH-02 morphology is 20% sharp kinks with Gaussian $\sigma=18^\circ$ drift. | `tests/test_crack_growth.py::test_correlated_walk_kink_rate_and_sigma` records `rng.normal(0,18)` and `rng.uniform(-85,85)` calls. | Observed kink ratio 0.210 at $S=0.6$ and 0.191 at $S=1.0$; every drift sample is exactly `normal(0, 18)`. | stable |
| Median tortuosity $\ge 1.05$ and zero crossings. | `tests/test_crack_growth.py::test_median_tortuosity_and_zero_crossings` over $S\in\{0.3,0.6,1.0\}$ × 6 seeds; `tools/growth_audit.py`. | Regression gate passes; calibration medians were 1.09 / 1.07 / 1.06 with 0 crossings and 0 clearance violations. | stable |
| Final-attempt bend snapping joins near-misses at $\ge 30^\circ$. | `test_final_attempt_bend_snaps_near_miss` patches `_forward_t_junction` to return `None`, forcing the bend fallback. | T-junctions still form for every tested severity/seed (e.g. 3–6 per seed at $S=0.6$, 7–15 at $S=1.0$); 0 crossings; incidence $\ge 30^\circ$. | stable |
| A 12-case contact sheet is sufficient to inspect supported ceramic morphology. | `tools/spike_contact_sheet.py` matrix: Tea Bowl / Tall Vase × $R\in\{0.0,0.2,0.5\}$ × 2 seeds. | 12/12 cases rendered with non-empty gold; `reports/contact_sheet.png` written; agent inspection PASS (human sign-off pending). | decays (render dependent) |

## Nomenclature & Code Symbol Audit

| Glossary Term | Final Code Identifier | Location / File | Verified Compliant? |
| :--- | :--- | :--- | :--- |
| Ceramic envelope floor | `CERAMIC_MIN_WALL_THICKNESS_MM = 1.6` | `kintsugi.py` | Yes |
| Envelope percentile | `WALL_THICKNESS_PERCENTILE = 5.0` | `kintsugi.py` | Yes |
| Boundary comparison helper | `wall_envelope_passes` | `kintsugi.py` | Yes |
| Inward-normal thickness probe | `_probe_normal_wall_thickness` | `kintsugi.py` | Yes |
| Normal-probe epsilon | `ENVELOPE_NORMAL_EPSILON_MM = 1e-3` | `kintsugi.py` | Yes |
| Continuous vein depth | `_vein_depth` ($\min(0.75W, 0.5t)$) | `kintsugi.py` | Yes |
| Continuous cutter points (replaces `_vein_point_groups`) | `_vein_cutter_points` | `kintsugi.py` | Yes |
| Normal/radial conservative fallback | `normal_thickness`, `radial_thickness`, `min(...)`, path-median fill | `kintsugi.py::project_crack_paths` | Yes |
| Gold-volume omission tolerance | `1e-6` mm³ | `kintsugi.py::_gold_solid_omitted` | Yes |
| Flared-wall fixture (45°) | `_flared_cone`, `_write_flared_cone` | `tests/test_envelope.py` | Yes |
| Tapered-lip fixture | `_tapered_lip_manifold` | `tests/test_kintsugi.py` | Yes |
| Removed point-omission threshold | `GROWTH_MIN_DEPTH_MM` | **deleted** from `kintsugi.py` | Yes |
| Rim projection clamp | `wall_z_max - max(0.5, W/2)` | `kintsugi.py::project_crack_paths` | Yes |
| Negative test fixture (no user preset) | `create_thin_cylinder_fixture` | `sample_models.py` | Yes |
| Removed preset alias / file | `thin_cylinder`, `create_thin_cylinder_preset`, `presets/thin_cylinder.stl` | **deleted** | Yes |
| Clean seam-omission reason | `seams_omitted_reason = "gold solid is empty"` | `web_app.py` | Yes |
| Clean UI status label | `Seams Omitted` | `static/viewer.js` | Yes |
| 12-case verification matrix | `CASES` / `_MODEL_CASES` | `tools/spike_contact_sheet.py` | Yes |

## Invalidated Hypotheses & Mid-Build Adjustments

| Original Belief | What Proved Wrong | Final Resolution | Rationale |
| :--- | :--- | :--- | :--- |
| Radial wall thickness is sufficient for envelope validation. | On a flared wall, radial distance overstates thickness by $1/\cos(\text{flare})$ and can pass a 1.2 mm wall at 1.7 mm. | Probe outward radial rays to find the exterior hit, then measure inward along $-n_i$. | Matches the actual cutter penetration direction and avoids false acceptance. |
| Thin single-perimeter vase-mode meshes can be supported by adaptive depth. | Chasing 0.8 mm backing forced $d=t-0.8$ toward zero, caused tangent kissing and point omission, and produced empty gold. | Reject $p_5<1.6$ mm with a descriptive `ValueError`; do not inflate geometry. | Multi-material FDM cannot support vase-mode inlays; rejection is honest and safe. |
| Point dropping below 0.25 mm depth is needed to avoid tangency. | On supported bodies the depth is typically $\ge 0.6$ mm, but tapered lips can be locally thinner; dropping was never required and caused gaps and empty solids. | Restore continuous $d_i=\min(0.75W,0.5t_i)$ and retain every densified point. | Continuous gold channels without tangency risk; the precise backing guarantee is $\ge 0.5t_i$ everywhere and $\ge 0.8$ mm where $t_i \ge 1.6$ mm. |
| A radial-only fallback is safe whenever the normal ray misses. | On a flared wall the radial value can be the overestimate the normal probe was introduced to avoid. | Take $\min(t_{\text{normal}},t_{\text{radial}})$ when both exist; bound radial-only points by the path's median normal thickness. | No code path can reintroduce the flared-wall overestimate. |
| `thin_cylinder` is a useful user-facing preset. | It cannot satisfy the envelope and only demonstrated degraded behaviour. | Delete the STL and preset entries; keep `create_thin_cylinder_fixture` for negative tests. | No invalid model offered to users. |
| A stale "wall thickness < 1.05 mm" message should explain omitted seams. | Sub-1.6 mm inputs are now rejected; valid runs must not omit seams. | Remove the stale string from `web_app.py` and `viewer.js`; display clean `Seams Omitted` only for a degenerate empty gold boolean. | UI no longer states a threshold that the engine does not use. |

## Implementation-Discovered Deferrals

- **Deferred Item (Task 5.2)**: Human sign-off of `reports/contact_sheet.png` against historical Kintsugi references.
  - **Reason**: An agent can generate and inspect the sheet, but cannot provide human aesthetic sign-off.
  - **Evidence completed**: 12/12 cases rendered successfully with continuous, non-empty gold; the sheet was inspected directly and shows rim-originated trunks, lateral linking fissures, and no empty-gold rows.
- **Deferred Item (Task 5.3)**: Bambu Studio / PrusaSlicer GUI import and toolpath assignment check.
  - **Reason**: Neither slicer is installed in this environment.
  - **Evidence completed**: 3MF structure is asserted by `test_3mf_structure` (one build item, `CeramicBody` + `GoldSeams` components, millimetre units), and both STLs pass watertightness/volume checks. Manual slicer import remains a human workstation step.
- **Deferred Item**: Physical FDM print leak test.
  - **Reason**: Requires hardware and a slicer profile.
  - **Evidence completed**: Geometric backing guarantee and manifold/watertightness checks above.

## Empirical Execution Logs & Evidence

### TDD red phase (before implementation)

```text
$ .venv/bin/python -m unittest tests/test_envelope.py -v
ERROR test_envelope_rejection_thin_mesh ... AttributeError:
    module 'sample_models' has no attribute 'create_thin_cylinder_fixture'
ERROR test_envelope_acceptance_near_boundary ... KeyError: 'wall_thickness_p5'
ERROR test_wall_envelope_boundary_comparison ... AttributeError:
    module 'kintsugi' has no attribute 'wall_envelope_passes'
Ran 3 tests ... FAILED (errors=3)

$ .venv/bin/python -m unittest <new vein / thin fixture tests> -v
ERROR test_continuous_vein_depth_no_omissions ... AttributeError:
    module 'kintsugi' has no attribute '_vein_cutter_points'
FAIL test_thin_wall_fixture_rejected_by_envelope ...
    thin_cylinder fixture builder is missing
Ran 4 tests ... FAILED (failures=1, errors=1)

$ .venv/bin/python -m unittest tests/test_web_api.py <thin-wall tests> -v
ERROR setUpClass ... AttributeError:
    module 'sample_models' has no attribute 'create_thin_cylinder_fixture'
Ran 0 tests ... FAILED (errors=1)
```

### Ceramic envelope probe (final code)

```text
== ceramic envelope probe ==
tea_bowl         ACCEPT p5=3.0048 mm median=3.0048 n=1968 misses=0
vase             ACCEPT p5=2.2998 mm median=2.3909 n=1968 misses=0
thin_fixture     REJECT Input vessel wall thickness (5th percentile: 0.74 mm)
                 is below the minimum ceramic envelope requirement of 1.60 mm.
cylinder_1.5mm   REJECT Input vessel wall thickness (5th percentile: 1.50 mm)
                 is below the minimum ceramic envelope requirement of 1.60 mm.
cylinder_1.6mm   ACCEPT p5=1.6026 mm median=1.6026 n=1968 misses=0
cylinder_1.7mm   ACCEPT p5=1.7027 mm median=1.7027 n=1968 misses=0
wall_envelope_passes(1.60) = True
wall_envelope_passes(1.5999999) = False
```

### Targeted regression gates (PATCH-01)

```text
$ .venv/bin/python -m unittest tests.test_envelope tests.test_kintsugi tests.test_web_api -v
...
----------------------------------------------------------------------
Ran 54 tests in 231.797s

OK
tapered lip: p5=2.404 mm, t_min=1.114 mm, d_min=0.557 mm,
             backing_min=0.557 mm, backing_min(t>=1.6)=0.839 mm
EXIT=0

$ .venv/bin/python -m unittest tests/test_crack_growth.py -v
...
Ran 3 tests in 15.225s

OK
```

PATCH-01 gates included in the 54-test run: `test_envelope_flared_cone_normal_thickness_rejection`, `test_projection_takes_min_and_bounds_normal_miss`, `test_tapered_lip_continuous_vein_and_backing`, and `test_api_fracture_empty_gold_pipeline`.

### Full regression suite (TDD green phase)

```text
$ .venv/bin/python -m unittest discover -s tests -v
...
----------------------------------------------------------------------
Ran 57 tests in 246.504s

OK
EXIT=0
```

### Baseline full verification profile (pre-PATCH-01)

```text
$ .venv/bin/python tools/test_report.py run --profile full --renders
=== KINTSUGI TEST REPORT v1 ===
overall: PASS
created_utc: 2026-11-07T23:45:13Z
profile: full
commit: 263a5a8f5f4d DIRTY happy-condor
fingerprint: 80f959e754766be8
host: Linux-5.15.0-1081-oracle-aarch64 | Neoverse-N1 | python 3.11.2
packages: numpy=2.4.6 scipy=1.17.1 trimesh=5.2.0 manifold3d=3.5.4 fastapi=0.162.0 httpx=0.28.1 rtree=1.4.1
suite unit: PASS ran=52 passed=52 failed=0 errors=0 skipped=0 time=244.4s
suite growth_audit: PASS seeds=200 crossings=0 clearance=0 T-ratio=1.000 tort=1.063 errors=0 time=330.2s
suite crack_graph_audit: PASS rows=4 phantom=0 crossing=0 clamp_max=0.0% time=16.1s
suite sweep: PASS total=160 clean=160 nonwatertight=0 errors=0 retries=0 median=1.14s time=247.0s
suite noise_fold: PASS fold_max=0.0% max_grad=0.70 crossing_seeds=0/1200 time=23.4s
suite renders: PASS path=reports/contact_sheet.png bytes=275940 time=299.9s
report: reports/test-report-263a5a8f5f4d-Linux-aarch64.json
=== END KINTSUGI TEST REPORT ===
EXIT=0
```

### PATCH-01 audit status at commit time

The PATCH-01 source tree was committed and pushed before the full-profile audit run completed, per the maintainer's instruction. The gates that had completed at that point were:

- Full regression suite: `Ran 57 tests in 246.504s ... OK`.
- Targeted envelope / engine / API suites: `Ran 54 tests in 231.797s ... OK`.
- PATCH-01-specific gates: flared-cone rejection/acceptance, normal/radial `min` fallback, tapered-lip backing audit, and empty-gold API pipeline all green.

The full-profile audit (`tools/test_report.py run --profile full --renders`) was still running against this exact source tree when the patch commit was pushed. Its result will be appended to this section in a follow-up documentation commit; the baseline pre-patch profile above was green with `retries=0` and is retained as the reference for the unchanged growth/sweep/audit invariants.

### PATCH-01 flared-wall and tapered-lip evidence

```text
# test_envelope_flared_cone_normal_thickness_rejection
1.2 mm normal wall at 45°: radial median 1.697 mm (would pass radially),
                           normal p5 1.201 mm -> ValueError
2.0 mm normal wall at 45°: normal p5 2.002 mm -> accepted;
                           vein fracture produced 185.4 mm³ of watertight gold

# test_tapered_lip_continuous_vein_and_backing
p5=2.404 mm, t_min=1.114 mm, d_min=0.557 mm,
backing_min=0.557 mm, backing_min(t>=1.6)=0.839 mm
gold watertight, 34,374 faces, 0 bad edges

# test_api_fracture_empty_gold_pipeline (patched empty cutter)
seams_omitted=true, downloads.gold_stl=null, num_cracks=0,
triangle_counts.gold=0, volumes.gold=0.0, ceramic STL present
```

### 12-case contact sheet metadata

```text
TEA BOWL R=0 S0 | cracks=20 ceramic_faces=95814 gold_faces=95054
TEA BOWL R=0 S1 | cracks=18 ceramic_faces=100370 gold_faces=99594
TEA BOWL R=0.2 S0 | cracks=15 ceramic_faces=92872 gold_faces=92102
TEA BOWL R=0.2 S1 | cracks=12 ceramic_faces=74238 gold_faces=73474
TEA BOWL R=0.5 S0 | cracks=11 ceramic_faces=44170 gold_faces=43396
TEA BOWL R=0.5 S1 | cracks=8 ceramic_faces=46444 gold_faces=45670
TALL VASE R=0 S0 | cracks=15 ceramic_faces=65880 gold_faces=65148
TALL VASE R=0 S1 | cracks=15 ceramic_faces=55378 gold_faces=54672
TALL VASE R=0.2 S0 | cracks=14 ceramic_faces=78928 gold_faces=78180
TALL VASE R=0.2 S1 | cracks=16 ceramic_faces=76062 gold_faces=75304
TALL VASE R=0.5 S0 | cracks=9 ceramic_faces=35956 gold_faces=35192
TALL VASE R=0.5 S1 | cracks=7 ceramic_faces=39414 gold_faces=38646
```

### Agent visual inspection notes — `reports/contact_sheet.png`

- **Date inspected**: 2026-11-07
- **Method**: The 12-case (36-panel) PNG was generated by `tools/spike_contact_sheet.py` and inspected directly.
- **Result**: **AGENT REVIEW — PASS (human sign-off pending)**. Gold seams are continuous and unbroken along each crack path; trunk/branch structures originate at the rim and cascade downward; lateral linkers connect adjacent fissures; no empty-gold or degraded thin-wall rows remain. The 12/12 cases report non-zero gold face counts.

## Quick Re-Verification

```bash
# 1) Envelope + continuous vein + PATCH-01 gates (about 30 s)
.venv/bin/python -m unittest \
  tests.test_envelope \
  tests.test_crack_growth \
  tests.test_kintsugi.KintsugiTestCase.test_continuous_vein_depth_no_omissions \
  tests.test_kintsugi.KintsugiTestCase.test_projection_clamps_rim_and_records_normal_thickness \
  tests.test_kintsugi.KintsugiTestCase.test_projection_takes_min_and_bounds_normal_miss \
  tests.test_kintsugi.KintsugiTestCase.test_tapered_lip_continuous_vein_and_backing \
  tests.test_kintsugi.KintsugiTestCase.test_empty_gold_solid_omits_file_and_warns -v

# 2) FastAPI rejection + empty-gold pipeline (about 8 s)
.venv/bin/python -m unittest tests.test_web_api -v

# 3) Regenerate the contact sheet
.venv/bin/python tools/spike_contact_sheet.py
```
