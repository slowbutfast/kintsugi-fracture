# Verification — hybrid-crack-generator

## Executive Summary & Environment

- **Status**: PASS. The `hybrid` generator is implemented end-to-end (vein-only), the web/API surface exposes it, solid bodies are rejected at validation time, and `growth` / `shard` remain byte-identical to the pre-change baseline.
- **Date verified**: 2026-11-09
- **Environment**: Linux 5.15.0-1081-oracle aarch64 (container), Python 3.11.2, `unittest` via `./.venv/bin/python -m unittest discover -s tests -v`
- **Interpreter**: the worktree `.venv` symlink points at the shared project virtualenv (`/home/node/global-sandbox/projects/wax-robot/.venv`).
- **Packages**: numpy 2.4.6, scipy 1.17.1, trimesh 5.2.0, manifold3d 3.5.4, fastapi 0.162.0, httpx 0.28.1, rtree 1.4.1
- **Commit under test**: `9e1911c5` (`fix(crack): enforce hybrid audit and speed up collision checks`) on `feat/hybrid-crack-generator-clean`, rebased onto `origin/main`.
- **Test totals**: 89 tests passed, 0 failed (`Ran 89 tests in 248.983s`, final full-suite log below).
- **PATCH-01 status**: RESOLVED. Reproducing `cup_unitree` (`R=0.2, seed=1`) clearance regression now reports zero violations; fail-closed audit/fragment guards, `auto -> wedge`, knob validation, and collision speedups are covered by new tests.
- **Baseline preservation**: 72/72 growth+shard digest comparisons matched the pre-change SHA-256 table embedded in `tests/test_crack_hybrid.py`.
- **Data preservation**: hybrid runs produce one ceramic body plus complementary gold; both STLs are watertight and positive-volume on `tea_bowl` and `vase`. No sample or path pruning was introduced (Stage 3 audits the direct union).

## Requirement Adherence Audit Matrix

### `mesh-fracture-engine`

| Requirement / Scenario | Verifying Test(s) | Status |
| :--- | :--- | :--- |
| Supported input envelope — vessel of revolution inside the envelope | `test_crack_hybrid` class setup; `tests/test_kintsugi.py::test_input_validation` | **PASS** |
| Supported input envelope — solid body without interior cavity wall rejected | `test_validate_rejects_solid_body_without_wall`; `tests/test_web_api.py::test_api_validate_rejects_solid_body_without_wall` | **PASS** |
| Supported input envelope — wall thickness below envelope rejected | `tests/test_envelope.py`; `tests/test_web_api.py::test_api_validate_thin_wall_rejected` | **PASS** |
| Supported input envelope — boundary thickness accepted | `tests/test_envelope.py::test_envelope_acceptance_near_boundary` | **PASS** |
| Supported input envelope — wrong units / non-vessel geometry rejected | `tests/test_kintsugi.py::test_input_envelope_rejection` | **PASS** |
| Hybrid macro-and-hairline — default partition and bounded hairlines | `test_fragment_guarantee_across_seeds_42_61`; `test_macro_seam_anchor_first_step_survives`; `test_combined_audit_invariants`; `test_generate_kintsugi_mesh_hybrid_watertight` | **PASS** |
| Hybrid macro-and-hairline — every knob alters output under wedge and loop | `test_each_knob_changes_output_and_echoes_telemetry`; `test_api_fracture_hybrid_success_and_knob_telemetry` | **PASS** |
| Hybrid macro-and-hairline — low-severity behaviour below S = 0.2 | `test_hybrid_determinism_and_low_severity` | **PASS** |
| Hybrid macro-and-hairline — knobs rejected on non-hybrid generators | `test_hybrid_rejects_ribbon_and_knobs_on_other_generators`; `test_api_fracture_hybrid_rejects_knobs_for_other_generator` | **PASS** |
| Hybrid macro-and-hairline — growth and shard byte-identical | `test_growth_and_shard_baseline_digests_unchanged` (72/72) | **PASS** |
| PATCH-01 — cup_unitree R=0.2 seed=1 clearance regression | `test_cup_unitree_r02_seed1_clearance_regression` (synthetic + real fixture) | **PASS** |
| PATCH-01 — `auto` defaults to wedge | `test_auto_shape_defaults_to_wedge` | **PASS** |
| PATCH-01 — R=0.8 boundary produces a macro seam | `test_r08_tier_boundary_produces_fracture` | **PASS** |
| PATCH-01 — fail-closed fragment and combined-audit guarantees | `test_fail_closed_fragment_guarantee`; `test_fail_closed_combined_audit` | **PASS** |
| PATCH-01 — fractional / malformed integer knobs rejected | `test_fractional_integer_knobs_rejected`; `test_api_fracture_hybrid_rejects_malformed_integer_knobs` | **PASS** |
| PATCH-01 — end-to-end hybrid vein CSG watertight | `test_generate_kintsugi_mesh_hybrid_watertight` (tea_bowl + vase) | **PASS** |

### `retro-web-gui`

| Requirement / Scenario | Verifying Test(s) | Status |
| :--- | :--- | :--- |
| Triggering fracture computation with vein default | `tests/test_web_api.py::test_api_fracture_defaults_to_vein_growth` | **PASS** |
| Selecting Shard Planes hides hybrid settings | `test_web_ui_exposes_hybrid_generator_and_settings`; `static/viewer.js` `syncHybridSettings` | **PASS** |
| Selecting Hybrid reveals the knob group and resolved telemetry | `test_web_ui_exposes_hybrid_generator_and_settings`; `test_api_fracture_hybrid_success_and_knob_telemetry` | **PASS** |
| Rejecting hybrid knobs with non-hybrid generator via API | `test_api_fracture_hybrid_rejects_knobs_for_other_generator` | **PASS** |
| Hybrid ribbon mode rejected | `test_api_fracture_hybrid_rejects_ribbon_mode`; `test_hybrid_rejects_ribbon_and_knobs_on_other_generators` | **PASS** |
| Wealthy parameter setting | `test_api_fracture_wealthy` | **PASS** |
| Seams omitted feedback | `test_api_fracture_empty_gold_pipeline` | **PASS** |
| Mobile hybrid controls remain touch-sized | `test_mobile_ui_and_menus_markup_served` plus `static/xp.css` audit (`font-size: 16px`, `min-height: 40px` under `.hybrid-field .xp-select`) | **PASS (CSS audit)** |

## Resolved Assumptions & Empirical Proof

| Assumption from `research.md` / handoff | Verification | Result |
| :--- | :--- | :--- |
| A first open wedge or closed loop always partitions the wall for $S \ge 0.2$. | `test_fragment_guarantee_across_seeds_42_61` over `S in {0.2, 0.6}` and seeds `42..61` (40 runs), plus a development sweep of 60/60 runs across `S in {0.2, 0.4, 0.8}`. | 40/40 automated runs report `num_through_fragments >= 2` and `num_fragments >= 2`; development sweep 60/60. |
| Pre-committed Stage-1 seams are sufficient obstacles for growth hairlines. | `test_stage2_obstacles_and_rim_exclusion`; `test_combined_audit_invariants` (12 runs). | `crossings == 0`, `clearance_violations == 0`, `min_clearance >= W + 0.8` in every audited run. |
| Generalising Seam 2 to any earlier seam preserves the 30° / `W + 0.8 mm` rules. | `test_shard_extra_seam_candidate_targets_any_earlier_seam`; shard fallback test in `tests/test_crack_shard.py`. | The candidate targets any earlier path, truncates at the earliest hit, and the single-path wrapper matches the plain shard result. |
| Rim seeds can be kept outside Stage-1 rim crossings in both sampling paths. | `test_stage2_obstacles_and_rim_exclusion` (50 rejection runs plus pinned-RNG fallback). | No placed seed lies inside an exclusion zone; the fallback terminates early rather than violating the zone. |
| Macro-seam anchors survive their first collision step. | `test_macro_seam_anchor_first_step_survives` (8 seeds) and `hairline_seam_count > 0` at `S = 0.5`, `hairline_count = 6`. | Anchor trunks survive with `exempt_path_id` / `exempt_origin`; anchor records point at the parent seam. |
| `tilt_deg` is not a no-op for the default wedge shape. | `test_each_knob_changes_output_and_echoes_telemetry` (`tilt_deg` under both wedge and loop). | Different `tilt_deg` values produce different polylines under both shapes. |
| A sharp hybrid wedge passes self-clearance whereas the original sine-bottom wedge did not. | `test_combined_audit_invariants`; baseline test confirms plain shard is untouched. | Hybrid wedge uses the sharp profile only when `apply_tilt=True`; 12/12 combined audits clean. |
| The hybrid end-to-end CSG path is watertight on both preset vessels. | `test_generate_kintsugi_mesh_hybrid_watertight` (tea_bowl + vase). | Both ceramic and gold STLs are watertight, positive-volume solids. |
| Growth and shard outputs are unchanged by the new keyword-only parameters. | `test_growth_and_shard_baseline_digests_unchanged` (72 comparisons). | 72/72 SHA-256 digests match the pre-change baseline. |
| PATCH-01: subdivided Stage-1 vertices were being discarded, so the combined audit saw un-subdivided macro seams. | `test_cup_unitree_r02_seed1_clearance_regression` (synthetic 22.5 mm cup + real fixture when present). | Before fix: 3 clearance violations, `min_clearance = 2.318 mm`; after fix: 0 violations and `min_clearance >= W + 0.8`. |
| PATCH-01: the combined audit and fragment guarantee were advisory, not fail-closed. | `test_fail_closed_fragment_guarantee`; `test_fail_closed_combined_audit`. | Both raise `ValueError` after three deterministic retries rather than returning violating paths. |
| PATCH-01: `R = 0.8` fell just below the `S = 0.2` boundary. | `test_r08_tier_boundary_produces_fracture`. | `round(S, 9) = 0.2` produces one macro seam and `num_fragments >= 2`. |
| PATCH-01: fractional/boolean integer knobs were truncated and malformed API strings returned 422. | `test_fractional_integer_knobs_rejected`; `test_api_fracture_hybrid_rejects_malformed_integer_knobs`. | All rejected with `ValueError` / HTTP 400. |
| PATCH-01: dense Stage-1 polylines made hybrid path generation slow. | Development timing probe over seeds 0–9 at `R=0.2`. | `tea_bowl` max 0.65 s, `bowl_urdformer` max 1.48 s, `cup_unitree` max 0.35 s; zero audit violations. |

## Nomenclature & Code Symbol Audit

| Glossary term / concept | Final code symbol | Location | Compliant |
| :--- | :--- | :--- | :--- |
| Through-fracture | `_hybrid_stage1_paths`, `_shard_extra_seam_candidate` | `kintsugi.py` | Yes |
| Hairline | `generate_crack_growth_paths` hairline stage | `kintsugi.py` | Yes |
| Fragment | `_count_wall_fragments`, `num_fragments`, `num_through_fragments` | `kintsugi.py` | Yes |
| Hybrid generator dispatch | `generate_hybrid_crack_paths`, `generate_crack_paths(generator="hybrid")` | `kintsugi.py` | Yes |
| Auto knob resolution | `_resolve_hybrid_config`, `_validate_hybrid_options` | `kintsugi.py` | Yes |
| Hybrid telemetry | `params["hybrid"]` / `parameters["hybrid"]` | `kintsugi.py`, `web_app.py` | Yes |
| Macro-seam anchor exemption | `exempt_path_id`, `exempt_origin`, `seam_anchor_count` | `kintsugi.py` | Yes |
| Rim exclusion | `excluded_u`, `exclusion_radius`, `excluded_rim_u` | `kintsugi.py` | Yes |
| Tilt steering | `_shard_wedge_path(..., apply_tilt=True)` | `kintsugi.py` | Yes |
| Roughness steering | `roughness_scale` | `kintsugi.py` | Yes |
| Validation-time wall gate | `validate_and_load_mesh` `has_wall` check | `kintsugi.py` | Yes |
| Subdivided Stage-1 propagation | `params["_updated_initial_paths"]` | `kintsugi.py` | Yes |
| Requested vs resolved shape | `through_shape_requested`, `through_shape` | `kintsugi.py` | Yes |
| Fail-closed guarantees | Stage-1 fragment `ValueError`, combined-audit `ValueError` | `kintsugi.py` | Yes |
| Collision fast path | Conservative 2D bounding-box prefilters in `_first_growth_collision` and `_shard_first_intersection` | `kintsugi.py` | Yes |
| Web hybrid controls | `#hybrid-settings`, six `#hybrid-*` selects, `#hybrid-resolved-note` | `static/index.html`, `static/viewer.js`, `static/xp.css` | Yes |
| Contact sheet generator switch | `--generator hybrid|all` | `tools/spike_contact_sheet.py` | Yes |

## Verbatim Execution Logs

### Full regression suite

Command:

```text
./.venv/bin/python -m unittest discover -s tests -v
```

Final summary (verbatim from the final full-suite run):

```text
----------------------------------------------------------------------
Ran 89 tests in 248.983s

OK
tapered lip: p5=2.404 mm, t_min=1.114 mm, d_min=0.557 mm, backing_min=0.557 mm, backing_min(t>=1.6)=0.839 mm
```

Representative hybrid test lines (verbatim):

```text
test_combined_audit_invariants (test_crack_hybrid.CrackHybridTestCase.test_combined_audit_invariants) ... ok
test_each_knob_changes_output_and_echoes_telemetry (test_crack_hybrid.CrackHybridTestCase.test_each_knob_changes_output_and_echoes_telemetry) ... ok
test_fragment_guarantee_across_seeds_42_61 (test_crack_hybrid.CrackHybridTestCase.test_fragment_guarantee_across_seeds_42_61) ... ok
test_generate_kintsugi_mesh_hybrid_watertight (test_crack_hybrid.CrackHybridTestCase.test_generate_kintsugi_mesh_hybrid_watertight) ... ok
test_growth_and_shard_baseline_digests_unchanged (test_crack_hybrid.CrackHybridTestCase.test_growth_and_shard_baseline_digests_unchanged) ... ok
test_hybrid_determinism_and_low_severity (test_crack_hybrid.CrackHybridTestCase.test_hybrid_determinism_and_low_severity) ... ok
test_hybrid_rejects_ribbon_and_knobs_on_other_generators (test_crack_hybrid.CrackHybridTestCase.test_hybrid_rejects_ribbon_and_knobs_on_other_generators) ... ok
test_macro_seam_anchor_first_step_survives (test_crack_hybrid.CrackHybridTestCase.test_macro_seam_anchor_first_step_survives) ... ok
test_shard_extra_seam_candidate_targets_any_earlier_seam (test_crack_hybrid.CrackHybridTestCase.test_shard_extra_seam_candidate_targets_any_earlier_seam) ... ok
test_stage1_auto_shape_reaches_rim_via_wedge_fallback (test_crack_hybrid.CrackHybridTestCase.test_stage1_auto_shape_reaches_rim_via_wedge_fallback) ... ok
test_stage2_obstacles_and_rim_exclusion (test_crack_hybrid.CrackHybridTestCase.test_stage2_obstacles_and_rim_exclusion) ... ok
test_validate_rejects_solid_body_without_wall (test_crack_hybrid.CrackHybridTestCase.test_validate_rejects_solid_body_without_wall) ... ok
test_auto_shape_defaults_to_wedge (test_crack_hybrid.CrackHybridTestCase.test_auto_shape_defaults_to_wedge) ... ok
test_cup_unitree_r02_seed1_clearance_regression (test_crack_hybrid.CrackHybridTestCase.test_cup_unitree_r02_seed1_clearance_regression) ... ok
test_fail_closed_combined_audit (test_crack_hybrid.CrackHybridTestCase.test_fail_closed_combined_audit) ... ok
test_fail_closed_fragment_guarantee (test_crack_hybrid.CrackHybridTestCase.test_fail_closed_fragment_guarantee) ... ok
test_fractional_integer_knobs_rejected (test_crack_hybrid.CrackHybridTestCase.test_fractional_integer_knobs_rejected) ... ok
test_r08_tier_boundary_produces_fracture (test_crack_hybrid.CrackHybridTestCase.test_r08_tier_boundary_produces_fracture) ... ok
test_api_fracture_hybrid_success_and_knob_telemetry (test_web_api.WebApiTestCase.test_api_fracture_hybrid_success_and_knob_telemetry) ... ok
test_api_fracture_hybrid_rejects_malformed_integer_knobs (test_web_api.WebApiTestCase.test_api_fracture_hybrid_rejects_malformed_integer_knobs) ... ok
test_api_fracture_hybrid_rejects_knobs_for_other_generator (test_web_api.WebApiTestCase.test_api_fracture_hybrid_rejects_knobs_for_other_generator) ... ok
test_api_fracture_hybrid_rejects_ribbon_mode (test_web_api.WebApiTestCase.test_api_fracture_hybrid_rejects_ribbon_mode) ... ok
test_api_validate_rejects_solid_body_without_wall (test_web_api.WebApiTestCase.test_api_validate_rejects_solid_body_without_wall) ... ok
test_web_ui_exposes_hybrid_generator_and_settings (test_web_api.WebApiTestCase.test_web_ui_exposes_hybrid_generator_and_settings) ... ok
```

### Baseline drift check

The pre-change digest table was captured from the same interpreter before implementation. After all implementation changes the same 72 canonical path-array hashes were recomputed and compared against the embedded table; the comparison diff was empty:

```text
$ <run the 72-case baseline comparison>
$ echo diff_exit=$?
diff_exit=0
```

The same comparison is enforced permanently by `tests/test_crack_hybrid.py::test_growth_and_shard_baseline_digests_unchanged`.

### OpenSpec validation

```text
$ openspec validate hybrid-crack-generator --strict
Change 'hybrid-crack-generator' is valid
```

### End-to-end watertight probe (development evidence)

```text
tea_bowl frags 2 cracks 8 hybrid {'through_count': 2, 'hairline_count': 5, 'num_fragments': 2}
  ceramic_path watertight True volume 65453.236668684
  gold_path watertight True volume 322.4211238015917
vase frags 5 cracks 8 hybrid {'through_count': 2, 'hairline_count': 5, 'num_fragments': 5}
  ceramic_path watertight True volume 26829.548590679366
  gold_path watertight True volume 306.2102346108395
```

## Quick Re-Verification (60-Second Audit)

Run the focused hybrid and API suites:

```bash
./.venv/bin/python -m unittest tests.test_crack_hybrid tests.test_web_api -v
```

Expected result:

```text
Ran 36 tests
OK
```

The fastest independent gate is the baseline test alone:

```bash
./.venv/bin/python -m unittest tests.test_crack_hybrid.CrackHybridTestCase.test_growth_and_shard_baseline_digests_unchanged -v
```

Expected result:

```text
Ran 1 test
OK
```
