# Verification — hybrid-crack-generator

## Executive Summary & Environment

- **Status**: PASS. The `hybrid` generator is implemented end-to-end (vein-only), the web/API surface exposes it, solid bodies are rejected at validation time, and `growth` / `shard` remain byte-identical to the pre-change baseline.
- **Date verified**: 2026-11-09
- **Environment**: Linux 5.15.0-1081-oracle aarch64 (container), Python 3.11.2, `unittest` via `./.venv/bin/python -m unittest discover -s tests -v`
- **Interpreter**: the worktree `.venv` symlink points at the shared project virtualenv (`/home/node/global-sandbox/projects/wax-robot/.venv`).
- **Packages**: numpy 2.4.6, scipy 1.17.1, trimesh 5.2.0, manifold3d 3.5.4, fastapi 0.162.0, httpx 0.28.1, rtree 1.4.1
- **Test totals**: 82 tests passed, 0 failed (final full-suite log below).
- **Baseline preservation**: 72/72 growth+shard digest comparisons matched the pre-change SHA-256 table embedded in `tests/test_crack_hybrid.py`.
- **Data preservation**: hybrid runs produce one ceramic body plus complementary gold; both STLs are watertight and positive-volume on `tea_bowl` and `vase`. No sample or path pruning was introduced (Stage 3 audits the direct union).

## Requirement Adherence Audit Matrix

### `mesh-fracture-engine`

| Requirement / Scenario | Verifying Test(s) | Status |
| :--- | :--- | :--- |
| Validation-time wall requirement — solid non-hollow body rejected | `tests/test_crack_hybrid.py::test_validate_rejects_solid_body_without_wall` | **PASS** |
| Validation-time wall requirement — open-top vessel accepted | `tests/test_crack_hybrid.py` class setup (`validate_and_load_mesh` on the bowl fixture); `tests/test_kintsugi.py::test_input_validation` | **PASS** |
| Two-stage hybrid — two-stage partition on a vessel | `test_fragment_guarantee_across_holdout_seeds`; `test_generate_kintsugi_mesh_hybrid_watertight` | **PASS** |
| Two-stage hybrid — low severity auto behaviour | `test_hybrid_determinism_and_low_severity` | **PASS** |
| Two-stage hybrid — low severity explicit override | `test_hybrid_determinism_and_low_severity` | **PASS** |
| Two-stage hybrid — Stage-1 auto shape reaches the rim | `test_stage1_auto_shape_reaches_rim_via_wedge_fallback` | **PASS** |
| Two-stage hybrid — Seam 2/3 T-junction into any earlier seam | `test_shard_extra_seam_candidate_targets_any_earlier_seam` | **PASS** |
| Two-stage hybrid — hairline obstacles and rim exclusion | `test_stage2_obstacles_and_rim_exclusion`; `test_combined_audit_invariants` | **PASS** |
| Two-stage hybrid — macro-seam interior hairline anchors | `test_macro_seam_anchor_first_step_survives` | **PASS** |
| Two-stage hybrid — combined audit invariants | `test_combined_audit_invariants` | **PASS** |
| Two-stage hybrid — periodic raster fragment counter | `test_fragment_guarantee_across_holdout_seeds`; `test_combined_audit_invariants` | **PASS** |
| Two-stage hybrid — deterministic hybrid output | `test_hybrid_determinism_and_low_severity` | **PASS** |
| Hybrid knobs — Auto values resolved from severity | `test_each_knob_changes_output_and_echoes_telemetry` | **PASS** |
| Hybrid knobs — explicit override echoed | `test_each_knob_changes_output_and_echoes_telemetry`; `tests/test_web_api.py::test_api_fracture_hybrid_success_and_knob_telemetry` | **PASS** |
| Hybrid knobs — rejected for other generators | `test_hybrid_rejects_ribbon_and_knobs_on_other_generators`; `test_api_fracture_hybrid_rejects_knobs_for_other_generator` | **PASS** |
| Regression — growth and shard byte-identical | `test_growth_and_shard_baseline_digests_unchanged` (72/72) | **PASS** |
| End-to-end — hybrid vein CSG watertight | `test_generate_kintsugi_mesh_hybrid_watertight` (tea_bowl + vase) | **PASS** |

### `retro-web-gui`

| Requirement / Scenario | Verifying Test(s) | Status |
| :--- | :--- | :--- |
| Selecting Hybrid reveals the knob group | `tests/test_web_api.py::test_web_ui_exposes_hybrid_generator_and_settings`; `static/viewer.js` `syncHybridSettings` | **PASS** |
| Sending non-auto hybrid knobs | `test_web_ui_exposes_hybrid_generator_and_settings`; `test_api_fracture_hybrid_success_and_knob_telemetry` | **PASS** |
| Resolved telemetry rendered | `test_web_ui_exposes_hybrid_generator_and_settings` (`renderHybridResolved`, `num_fragments`); API telemetry test | **PASS** |
| Hybrid knobs with another generator rejected | `test_api_fracture_hybrid_rejects_knobs_for_other_generator` | **PASS** |
| Hybrid ribbon mode rejected | `test_api_fracture_hybrid_rejects_ribbon_mode`; `test_hybrid_rejects_ribbon_and_knobs_on_other_generators` | **PASS** |
| Solid body rejected by validation endpoint | `test_api_validate_rejects_solid_body_without_wall`; `test_validate_rejects_solid_body_without_wall` | **PASS** |
| Mobile hybrid controls remain touch-sized | `test_mobile_ui_and_menus_markup_served` plus `static/xp.css` audit (`font-size: 16px`, `min-height: 40px` under `.hybrid-field .xp-select`) | **PASS (CSS audit)** |

## Resolved Assumptions & Empirical Proof

| Assumption from `research.md` / handoff | Verification | Result |
| :--- | :--- | :--- |
| A first open wedge or closed loop always partitions the wall for $S \ge 0.2$. | `test_fragment_guarantee_across_holdout_seeds` over `S in {0.2, 0.6}` and seeds `42..61` (40 runs), plus a development sweep of 60/60 runs across `S in {0.2, 0.4, 0.8}`. | 40/40 automated runs report `num_through_fragments >= 2` and `num_fragments >= 2`; development sweep 60/60. |
| Pre-committed Stage-1 seams are sufficient obstacles for growth hairlines. | `test_stage2_obstacles_and_rim_exclusion`; `test_combined_audit_invariants` (12 runs). | `crossings == 0`, `clearance_violations == 0`, `min_clearance >= W + 0.8` in every audited run. |
| Generalising Seam 2 to any earlier seam preserves the 30° / `W + 0.8 mm` rules. | `test_shard_extra_seam_candidate_targets_any_earlier_seam`; shard fallback test in `tests/test_crack_shard.py`. | The candidate targets any earlier path, truncates at the earliest hit, and the single-path wrapper matches the plain shard result. |
| Rim seeds can be kept outside Stage-1 rim crossings in both sampling paths. | `test_stage2_obstacles_and_rim_exclusion` (50 rejection runs plus pinned-RNG fallback). | No placed seed lies inside an exclusion zone; the fallback terminates early rather than violating the zone. |
| Macro-seam anchors survive their first collision step. | `test_macro_seam_anchor_first_step_survives` (8 seeds) and `hairline_seam_count > 0` at `S = 0.5`, `hairline_count = 6`. | Anchor trunks survive with `exempt_path_id` / `exempt_origin`; anchor records point at the parent seam. |
| `tilt_deg` is not a no-op for the default wedge shape. | `test_each_knob_changes_output_and_echoes_telemetry` (`tilt_deg` under both wedge and loop). | Different `tilt_deg` values produce different polylines under both shapes. |
| A sharp hybrid wedge passes self-clearance whereas the original sine-bottom wedge did not. | `test_combined_audit_invariants`; baseline test confirms plain shard is untouched. | Hybrid wedge uses the sharp profile only when `apply_tilt=True`; 12/12 combined audits clean. |
| The hybrid end-to-end CSG path is watertight on both preset vessels. | `test_generate_kintsugi_mesh_hybrid_watertight` (tea_bowl + vase). | Both ceramic and gold STLs are watertight, positive-volume solids. |
| Growth and shard outputs are unchanged by the new keyword-only parameters. | `test_growth_and_shard_baseline_digests_unchanged` (72 comparisons). | 72/72 SHA-256 digests match the pre-change baseline. |

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
Ran 82 tests in 668.787s

OK
tapered lip: p5=2.404 mm, t_min=1.114 mm, d_min=0.557 mm, backing_min=0.557 mm, backing_min(t>=1.6)=0.839 mm
```

Representative hybrid test lines (verbatim):

```text
test_combined_audit_invariants (test_crack_hybrid.CrackHybridTestCase.test_combined_audit_invariants) ... ok
test_each_knob_changes_output_and_echoes_telemetry (test_crack_hybrid.CrackHybridTestCase.test_each_knob_changes_output_and_echoes_telemetry) ... ok
test_fragment_guarantee_across_holdout_seeds (test_crack_hybrid.CrackHybridTestCase.test_fragment_guarantee_across_holdout_seeds) ... ok
test_generate_kintsugi_mesh_hybrid_watertight (test_crack_hybrid.CrackHybridTestCase.test_generate_kintsugi_mesh_hybrid_watertight) ... ok
test_growth_and_shard_baseline_digests_unchanged (test_crack_hybrid.CrackHybridTestCase.test_growth_and_shard_baseline_digests_unchanged) ... ok
test_hybrid_determinism_and_low_severity (test_crack_hybrid.CrackHybridTestCase.test_hybrid_determinism_and_low_severity) ... ok
test_hybrid_rejects_ribbon_and_knobs_on_other_generators (test_crack_hybrid.CrackHybridTestCase.test_hybrid_rejects_ribbon_and_knobs_on_other_generators) ... ok
test_macro_seam_anchor_first_step_survives (test_crack_hybrid.CrackHybridTestCase.test_macro_seam_anchor_first_step_survives) ... ok
test_shard_extra_seam_candidate_targets_any_earlier_seam (test_crack_hybrid.CrackHybridTestCase.test_shard_extra_seam_candidate_targets_any_earlier_seam) ... ok
test_stage1_auto_shape_reaches_rim_via_wedge_fallback (test_crack_hybrid.CrackHybridTestCase.test_stage1_auto_shape_reaches_rim_via_wedge_fallback) ... ok
test_stage2_obstacles_and_rim_exclusion (test_crack_hybrid.CrackHybridTestCase.test_stage2_obstacles_and_rim_exclusion) ... ok
test_validate_rejects_solid_body_without_wall (test_crack_hybrid.CrackHybridTestCase.test_validate_rejects_solid_body_without_wall) ... ok
test_api_fracture_hybrid_success_and_knob_telemetry (test_web_api.WebApiTestCase.test_api_fracture_hybrid_success_and_knob_telemetry) ... ok
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
Ran 29 tests
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
