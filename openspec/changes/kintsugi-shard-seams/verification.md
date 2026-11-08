# Verification: `kintsugi-shard-seams`

## Executive Summary & Environment

- **Change**: Add the opt-in `generator="shard"` tilted shard-plane fracture spike.
- **Status**: Automated implementation and verification tasks `1.1`–`5.2` are complete. Visual sign-off (`5.3`) and the human default-generator decision (`5.4`) remain intentionally unchecked.
- **Default preserved**: `generator="growth"` remains the default; `"voronoi"` remains available. `"shard"` is restricted to `mode="vein"`.
- **Baseline commit**: `fd2b16e` (`docs(openspec): add kintsugi-shard-seams specs and OpenCode handoff`).
- **Files changed**:
  - `kintsugi.py`
  - `tools/spike_contact_sheet.py`
  - `tests/test_crack_shard.py` (new)
  - `reports/contact_sheet_shard.png` (rendered artifact)
  - `openspec/changes/kintsugi-shard-seams/tasks.md`
  - `openspec/changes/kintsugi-shard-seams/verification.md` (this file)
  - `openspec/changes/kintsugi-shard-seams/patch.md` (clean-pass ledger)
  - `openspec/specs/mesh-fracture-engine/spec.md` (synced delta requirement)

| Environment item | Value |
| :--- | :--- |
| OS / platform | Linux 5.15.0-1081-oracle aarch64 (glibc 2.36) |
| Python | 3.11.2 (`./.venv/bin/python`) |
| NumPy | 2.4.6 |
| Trimesh | 5.2.0 |
| FastAPI | 0.162.0 |
| Manifold3D | project-pinned build from the existing `.venv` |
| Test runner | `unittest` (no new dependencies installed) |

## Requirement Adherence Audit Matrix

Each row maps a requirement/scenario in `specs/mesh-fracture-engine/spec.md` to the test that verifies it.

| Spec requirement / scenario | Verifying test(s) | Result |
| :--- | :--- | :--- |
| **Shard-plane crack generation** dispatch supports `growth`, `shard`, `voronoi`; default stays `growth` | `test_generate_kintsugi_mesh_shard_mode_watertight_and_ribbon_guard`; full regression suite | PASS |
| **Open rim-to-rim wedge seam generation and exact truncation** — no flat-run shelves, raw endpoints ≤ 0.35 W above rim, projected endpoints land on upper lip | `test_open_wedge_seam_exact_truncation_and_rim_landing` | PASS |
| **Closed tilted loop seam generation and drift bridge closure** — periodic closure ≤ 1e-6, strict band containment, cyclic audit clearance, wedge fallback below 5° tilt | `test_closed_loop_drift_bridge_closure_and_cyclic_clearance` | PASS |
| **Two-seam verified intersection and shared T-junction** — in-band hit, ≥ 30° arrival, exact shared vertex, `_growth_junctions` metadata, clearance ≥ W + 0.8 mm | `test_two_seam_verified_intersection_and_fallback` (success branch, all two-path seeds) | PASS |
| **Deterministic single-seam fallback when no valid intersection exists** — exactly 16 candidate draws then `[Seam 1]` | `test_two_seam_verified_intersection_and_fallback` (mocked candidate stream, asserts 16 calls and no metadata) | PASS |
| **Closed-loop cyclic clearance and quadrant sub-arc tortuosity** — cyclic adjacency across `u = 0 ≡ P`, 4 quadrants in 2D `(u, z)`, finite τ ≥ 1.05, median increases as R decreases | `test_closed_loop_drift_bridge_closure_and_cyclic_clearance`; `test_closed_loop_quadrant_subarc_tortuosity` | PASS |
| **Generator dispatch and vein-mode scope enforcement** — `shard` + `ribbon` raises `ValueError`; `shard` + `vein` dispatches | `test_generate_kintsugi_mesh_shard_mode_watertight_and_ribbon_guard`; full regression | PASS |
| **API fracture endpoint error handling** — HTTP 200 for `shard`+`vein`, HTTP 400 with explanatory detail for `shard`+`ribbon` | `test_api_fracture_shard_mode_validation` | PASS |
| **End-to-end Manifold3D watertight carving** (Tea Bowl and Tall Vase) | `test_generate_kintsugi_mesh_shard_mode_watertight_and_ribbon_guard` | PASS |
| **Contact-sheet tooling** — `--generator {growth,shard,both}`, generator forwarding, shard default output | `tools/spike_contact_sheet.py --generator shard --output reports/contact_sheet_shard.png` | PASS (12/12 cells) |

## Resolved Assumptions & Empirical Proof

1. **Primitive 1 selection**: `rng.uniform() < 0.5` selects Primitive B (closed loop); otherwise Primitive A (wedge). If the loop cannot achieve a ≥ 5° tilt inside the height cap, the generator deterministically emits the wedge instead. Verified by the narrow-wall branch of `test_closed_loop_drift_bridge_closure_and_cyclic_clearance`.
2. **Severity mapping**: `S = 1 - clip(R, 0, 1)`. `S < 0.2` returns zero seams. The three configured bands use harmonic amplitudes `0.015/0.035/0.060 × Δz_wall`, record the specified kink angles `4°/8°/14°` in `_shard_severity_config`, and target tortuosity ranges `[1.05,1.10]`, `[1.08,1.20]`, `[1.12,1.35]`. The loop kink walk does **not** sample an angular Gaussian directly: it uses a severity-scaled vertical step amplitude (`_shard_kink_amplitude`) with anti-correlated paired increments (see assumption 5). This is a documented approximation, not a literal implementation of `δ_j ~ N(0, σ_θ²)`. Measured closed-loop medians were 1.050 / 1.103 / 1.154 / 1.174 for `S = 0.3 / 0.5 / 0.8 / 1.0`, inside the target bands (S = 0.3 sits at the floor).
3. **Exact wedge truncation**: Wedge polylines are cut via `_truncate_polyline_z(raw, wall_z_min + 0.5W, wall_z_max + 0.35W, min_length=3W)`. No `np.clip` is used on vertical seam coordinates.
4. **Loop closure and capping**: The linear drift bridge `kink_i = w_i - i/(N-1)(w_{N-1}-w_0)` forces `z(0) = z(P)`. All loop offsets are scaled to 0.98 of the available half-height so vertices stay strictly inside `[wall_z_min + 0.6W, wall_z_max - 0.6W]`. Kink amplitude is capped at `0.10 A_avail`.
5. **Tortuosity / kink mechanism**: To satisfy both the `0.10 A_avail` kink cap and the τ ≥ 1.05 floor, the kink walk uses anti-correlated paired increments (`delta_{2k+1} = -delta_{2k}`) with a severity-scaled vertical amplitude. This preserves the required `w_i = Σ delta_j` bridge construction while producing crystalline step kinks instead of a smooth ring, but it is a deliberate approximation of the literal angular Gaussian kink variance (`δ_j ~ N(0, σ_θ²)` with σ_θ = 4°/8°/14°); the `kink_deg` values are retained as band metadata and are not sampled as angles. Closed loops are split into four equal quadrant sub-arcs in 2D `(u, z)` and the floor is enforced. The test confirms finite τ ≥ 1.05 for R ∈ {0.5, 0.2, 0.0} and strictly increasing medians as R decreases.
6. **Seam 2 target band**: Candidate rim-to-seam wedges target points deeper than the rim, using `min(wall_z_max - W, wall_z_max - 0.25 Δz_wall) - 0.15W`. This is still strictly inside the spec band `[wall_z_min + W, wall_z_max - W]`, while guaranteeing a non-exempt segment span so `analyze_growth_paths` reports a finite clearance sample.
7. **Arrival angle at existing vertices**: When a shared junction lands on an existing Seam 1 vertex, both incident tangents are checked. The minimum incident angle must be ≥ 30°, and that minimum is recorded in `_growth_junctions`. This prevents accepting a candidate whose angle passes against only one side of the vertex.
8. **Single-loop finite clearance**: A lone, finely sampled closed loop has every same-path candidate pair inside the adjacency skip span, so the pair audit would otherwise return `min_clearance = None`. When that happens, the audit measures the first non-skipped cyclic neighbour (`index + skip_span + 1` modulo segment count), which yields a meaningful finite self-clearance across `u = 0 ≡ P` without weakening the violation checks.
9. **Seam 2 determinism**: Up to exactly 16 candidate draws are attempted in fixed order. If none pass the in-band intersection, angle, insertion, metadata, and clearance gates, the generator returns `[Seam 1]` and leaves `params["_growth_junctions"] == []`. The contact sheet shows 2 seams for both seed-0 cells and deterministic 1-seam fallback for both seed-1 cells at each severity.
10. **No frontend/dependency changes**: `static/` and dependency files were not modified.

### Measured closed-loop tortuosity (independent orchestrator audit)

Sampled across 12 seeds per band with the bowl fixture; values are per-quadrant arc/chord ratios from `_tortuosity_values`:

| Severity S | Target band | Measured min | Measured median | Measured max |
| :--- | :--- | :--- | :--- | :--- |
| 0.3 | `[1.05, 1.10]` | 1.050 | 1.050 | 1.073 |
| 0.5 | `[1.08, 1.20]` | 1.069 | 1.103 | 1.142 |
| 0.8 | `[1.12, 1.35]` | 1.096 | 1.154 | 1.202 |
| 1.0 | `[1.12, 1.35]` | 1.118 | 1.174 | 1.233 |

The median is inside every target band. The per-value minimum can sit below the band on high-severity runs; the spec's floor is the hard constraint and is met everywhere.

### Independent orchestrator re-run

The orchestration agent re-ran the suites after the implementation report, without changing implementation code:

- `./.venv/bin/python -m unittest tests.test_crack_shard -v` → `Ran 6 tests in 249.368s`, `OK`.
- `./.venv/bin/python -m unittest discover -s tests -p "test_*.py" -v` → `Ran 63 tests in 497.826s`, `OK`.
- `openspec validate --all --strict` → 4 passed, 0 failed.

## Nomenclature Audit

| Term / symbol | Meaning in this change | Confirmed |
| :--- | :--- | :--- |
| **Reserve R** | Inequality reserve metric; `R ∈ [0,1]` | Yes — never used as roughness |
| **Severity S** | `S = 1 - clip(R, 0, 1)`; higher S = more damage | Yes |
| **Primitive A** | Open Rim-to-Rim Wedge Seam, exact `_truncate_polyline_z` truncation | Yes |
| **Primitive B** | Closed Tilted Loop Seam with drift-bridge closure and height capping | Yes |
| **Seam 1 / Seam 2** | Primary seam and optional verified rim-to-seam T-junction seam | Yes |
| **`params["_growth_junctions"]`** | T-junction metadata consumed by `_growth_junctions_from_metadata` (`point`, `kind`, `path`, `angle`) | Yes |
| **Quadrant sub-arc tortuosity** | Arc/chord over four 2D `(u, z)` sub-arcs for closed loops | Yes |
| **Shard-like seam layout** | Surface inlay curves, not physically severed 3D shards | Yes — `mode="ribbon"` rejected |
| **`generate_shard_crack_paths`** | Public shard seam entry point matching the engine dispatch signature | Yes |
| **`_shard_loop_path` / `_shard_wedge_path`** | Primitive B / Primitive A builders | Yes |
| **`_shard_second_seam_candidate`** | One deterministic Seam 2 candidate draw | Yes |
| **`generator="shard"`** | Opt-in generator value; `growth` remains default | Yes |

## Landed Tech Footprint & Patterns

| Adopted pattern / package | Implementation file(s) | Verification command / suite |
| :--- | :--- | :--- |
| Severity-to-parameter table ($S$, harmonics, seam count) | `kintsugi.py` (`_shard_severity_config`) | `test_closed_loop_quadrant_subarc_tortuosity`; regression suite |
| Exact boundary truncation (`_truncate_polyline_z`, no `np.clip`) | `kintsugi.py` (`_shard_wedge_path`, `_shard_second_seam_candidate`) | `test_open_wedge_seam_exact_truncation_and_rim_landing` |
| Linear drift bridge + height-capped amplitude | `kintsugi.py` (`_shard_loop_path`) | `test_closed_loop_drift_bridge_closure_and_cyclic_clearance` |
| Verified first intersection, shared T-junction, metadata exemption | `kintsugi.py` (`_shard_first_intersection`, `_shard_second_seam_candidate`, `generate_shard_crack_paths`) | `test_two_seam_verified_intersection_and_fallback` |
| Cyclic adjacency + quadrant sub-arc tortuosity | `kintsugi.py` (`analyze_growth_paths`, `_tortuosity_values`, `_is_closed_periodic_path`) | `test_closed_loop_drift_bridge_closure_and_cyclic_clearance`; `test_closed_loop_quadrant_subarc_tortuosity` |
| Generator dispatch and vein-mode guard | `kintsugi.py` (`generate_crack_paths`, `generate_kintsugi_mesh`, `_build_parser`); `web_app.py` (existing exception boundary) | `test_generate_kintsugi_mesh_shard_mode_watertight_and_ribbon_guard`; `test_api_fracture_shard_mode_validation` |
| Pure-numpy contact-sheet rasteriser (no new dependency) | `tools/spike_contact_sheet.py` | `--generator shard` render (12/12 cells) |

## Invalidated Hypotheses & Mid-Build Adjustments

| Original belief | What proved wrong | Final resolution | Rationale |
| :--- | :--- | :--- | :--- |
| `np.clip` on `z` is enough to keep seam curves in the wall band | Clamping creates flat-run horizontal shelves at the rim/floor (defect F15a) | Route every open wedge through `_truncate_polyline_z` with exact interpolated crossings | Preserves oblique rim landings and avoids shelf artifacts |
| Two non-touching closed loops must look like horizontal barrel rings | A tilted plane already produces a height-varying closed loop | Both tilted loops and intersecting wedges are valid primitives; amplitude is capped and wedge fallback is used below 5° | Matches the design's shard-plane aesthetic without horizontal stripes |
| A literal Gaussian kink walk (`δ_j ~ N(0, σ_θ²)`) will satisfy both the containment cap and τ ≥ 1.05 | Independent Gaussian increments accumulate drift and either breach the cap or flatten the loop | Use anti-correlated paired increments with a severity-scaled amplitude; retain `kink_deg` as band metadata | Meets containment and tortuosity; documented as an approximation |
| A lone closed loop naturally yields a finite `min_clearance` | Every same-path segment pair falls inside the cyclic adjacency skip span | When no pair sample exists, measure the first non-skipped cyclic neighbour | Keeps the audit informative without weakening violation checks |
| Any paired seam intersection is acceptable | A candidate can graze Seam 1 at a shallow angle or land at a vertex with two incident tangents | Check the minimum incident tangent angle (≥ 30°), truncate at the first in-band hit, and insert a shared vertex | Produces clean T-junctions and prevents grazing overlaps |

## Implementation-Discovered Deferrals

- **Side-by-side visual sign-off**:
  - **Reason**: Requires human judgement of the rendered `reports/contact_sheet_shard.png` against `reports/contact_sheet.png`; task 5.3 remains unchecked by design. The automated render and growth baseline are prepared for that review.
- **Default-generator decision**:
  - **Reason**: Task 5.4 is a product decision (`growth` vs `shard`); `growth` remains the default in this change.
- **Secondary hairline branches and 3rd shard plane**:
  - **Reason**: Deferred to Stage 2 per `research.md`; Stage 1 proves the two primary seam primitives and the verified T-junction.
- **Through-wall `ribbon` mode for closed loops**:
  - **Reason**: A closed loop in ribbon mode would disconnect the ceramic body; Stage 1 rejects `generator="shard"` with `mode="ribbon"`.
- **Literal angular kink Gaussian**:
  - **Reason**: The current calibrated vertical-amplitude approximation meets the containment and tortuosity constraints; replacing it with a literal angular Gaussian is left to a follow-up if the visual review requires it.

## Verbatim Execution Logs

### 1. Targeted TDD suite

Command:

```bash
./.venv/bin/python -m unittest tests.test_crack_shard -v
```

```text
test_api_fracture_shard_mode_validation (tests.test_crack_shard.CrackShardTestCase.test_api_fracture_shard_mode_validation) ... /home/node/.local/share/opencode/worktree/fffe954eb04701865d9ff532e39b2c85f865ef3f/swift-dolphin/.venv/lib/python3.11/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
  from starlette.testclient import TestClient as TestClient  # noqa
ok
test_closed_loop_drift_bridge_closure_and_cyclic_clearance (tests.test_crack_shard.CrackShardTestCase.test_closed_loop_drift_bridge_closure_and_cyclic_clearance) ... ok
test_closed_loop_quadrant_subarc_tortuosity (tests.test_crack_shard.CrackShardTestCase.test_closed_loop_quadrant_subarc_tortuosity) ... ok
test_generate_kintsugi_mesh_shard_mode_watertight_and_ribbon_guard (tests.test_crack_shard.CrackShardTestCase.test_generate_kintsugi_mesh_shard_mode_watertight_and_ribbon_guard) ... ok
test_open_wedge_seam_exact_truncation_and_rim_landing (tests.test_crack_shard.CrackShardTestCase.test_open_wedge_seam_exact_truncation_and_rim_landing) ... ok
test_two_seam_verified_intersection_and_fallback (tests.test_crack_shard.CrackShardTestCase.test_two_seam_verified_intersection_and_fallback) ... ok

----------------------------------------------------------------------
Ran 6 tests in 243.482s

OK
```

### 2. Contact-sheet render

Command:

```bash
./.venv/bin/python tools/spike_contact_sheet.py --generator shard --output reports/contact_sheet_shard.png
```

```text
reports/contact_sheet_shard.png
[shard] TEA BOWL R=0 S0 | cracks=2 ceramic_faces=38260 gold_faces=37496
[shard] TEA BOWL R=0 S1 | cracks=1 ceramic_faces=32278 gold_faces=31522
[shard] TEA BOWL R=0.2 S0 | cracks=2 ceramic_faces=36254 gold_faces=35486
[shard] TEA BOWL R=0.2 S1 | cracks=1 ceramic_faces=38182 gold_faces=37414
[shard] TEA BOWL R=0.5 S0 | cracks=2 ceramic_faces=43376 gold_faces=42600
[shard] TEA BOWL R=0.5 S1 | cracks=1 ceramic_faces=40052 gold_faces=39292
[shard] TALL VASE R=0 S0 | cracks=2 ceramic_faces=28134 gold_faces=27370
[shard] TALL VASE R=0 S1 | cracks=1 ceramic_faces=14964 gold_faces=14208
[shard] TALL VASE R=0.2 S0 | cracks=2 ceramic_faces=26200 gold_faces=25436
[shard] TALL VASE R=0.2 S1 | cracks=1 ceramic_faces=17776 gold_faces=17016
[shard] TALL VASE R=0.5 S0 | cracks=2 ceramic_faces=33634 gold_faces=32866
[shard] TALL VASE R=0.5 S1 | cracks=1 ceramic_faces=21166 gold_faces=20402
```

Result: **12/12 cells rendered, zero `ERROR` lines**, no blank/error panels. Six cells use the deterministic two-seam T-junction path and six use the deterministic single-seam fallback (`seed=1` for each preset/severity pair).

Comparison summary (growth baseline rendered with `./.venv/bin/python tools/spike_contact_sheet.py --generator growth --output reports/contact_sheet.png`): the shard sheet uses the same 2-preset × 3-severity × 2-seed matrix, renderer, camera, and palette as the growth sheet. Side-by-side inspection shows the intended contrast: growth produces 7–20 fine rim-seeded cracks per cell, while shard produces 1–2 macroscopic seams that partition the exterior into 2–3 regions. The `seed=0` cells show the verified two-seam T-junction layout; the `seed=1` cells show the deterministic single-seam fallback. The single-seam wedge's u-span can reach `0.55 * period` (> 180°), so in the gold-only side view its visible trough can read as a shallow near-horizontal line even though both rim endpoints are present on the far side. This is geometrically within the Stage 1 spec but is flagged for the human visual sign-off (task 5.3) as a visual-quality consideration. No pixel-level aesthetic pass/fail is asserted here.

**Design palette note (WARNING)**: `design.md` names a light inspection palette (`#F6F2EA` background, `#D4AF37` gold, `#7A6F5D` wall markers), but the existing `tools/spike_contact_sheet.py` rasteriser uses its established dark background (`#1E222C`) and lighter ceramic/gold values. Stage 1 intentionally kept the existing renderer palette so the growth baseline and shard sheet remain directly comparable; restyling both sheets is deferred to the visual sign-off rather than silently changing the baseline.

### 3. Full regression suite

Command:

```bash
./.venv/bin/python -m unittest discover -s tests -p "test_*.py" -v
```

```text
/home/node/.local/share/opencode/worktree/fffe954eb04701865d9ff532e39b2c85f865ef3f/swift-dolphin/.venv/lib/python3.11/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
  from starlette.testclient import TestClient as TestClient  # noqa
test_correlated_walk_kink_rate_and_sigma (test_crack_growth.CrackGrowthRegressionTestCase.test_correlated_walk_kink_rate_and_sigma)
20% sharp kinks; every non-kink step drifts with sigma = 18 degrees. ... ok
test_final_attempt_bend_snaps_near_miss (test_crack_growth.CrackGrowthRegressionTestCase.test_final_attempt_bend_snaps_near_miss)
With forward projection disabled, the final-attempt bend still T-joins. ... ok
test_median_tortuosity_and_zero_crossings (test_crack_growth.CrackGrowthRegressionTestCase.test_median_tortuosity_and_zero_crossings) ... ok
test_api_fracture_shard_mode_validation (test_crack_shard.CrackShardTestCase.test_api_fracture_shard_mode_validation) ... ok
test_closed_loop_drift_bridge_closure_and_cyclic_clearance (test_crack_shard.CrackShardTestCase.test_closed_loop_drift_bridge_closure_and_cyclic_clearance) ... ok
test_closed_loop_quadrant_subarc_tortuosity (test_crack_shard.CrackShardTestCase.test_closed_loop_quadrant_subarc_tortuosity) ... ok
test_generate_kintsugi_mesh_shard_mode_watertight_and_ribbon_guard (test_crack_shard.CrackShardTestCase.test_generate_kintsugi_mesh_shard_mode_watertight_and_ribbon_guard) ... ok
test_open_wedge_seam_exact_truncation_and_rim_landing (test_crack_shard.CrackShardTestCase.test_open_wedge_seam_exact_truncation_and_rim_landing) ... ok
test_two_seam_verified_intersection_and_fallback (test_crack_shard.CrackShardTestCase.test_two_seam_verified_intersection_and_fallback) ... ok
test_envelope_acceptance_near_boundary (test_envelope.CeramicEnvelopeTestCase.test_envelope_acceptance_near_boundary) ... ok
test_envelope_flared_cone_normal_thickness_rejection (test_envelope.CeramicEnvelopeTestCase.test_envelope_flared_cone_normal_thickness_rejection) ... ok
test_envelope_rejection_thin_mesh (test_envelope.CeramicEnvelopeTestCase.test_envelope_rejection_thin_mesh) ... ok
test_wall_envelope_boundary_comparison (test_envelope.CeramicEnvelopeTestCase.test_wall_envelope_boundary_comparison) ... ok
test_3mf_structure (test_kintsugi.KintsugiTestCase.test_3mf_structure) ... ok
test_band_edge_terminals_are_ragged (test_kintsugi.KintsugiTestCase.test_band_edge_terminals_are_ragged) ... ok
test_continuous_vein_depth_no_omissions (test_kintsugi.KintsugiTestCase.test_continuous_vein_depth_no_omissions) ... ok
test_crack_paths_lie_on_periodic_voronoi (test_kintsugi.KintsugiTestCase.test_crack_paths_lie_on_periodic_voronoi) ... ok
test_debris_swap (test_kintsugi.KintsugiTestCase.test_debris_swap) ... ok
test_debris_swap_no_new_bad_edges (test_kintsugi.KintsugiTestCase.test_debris_swap_no_new_bad_edges) ... ok
test_determinism (test_kintsugi.KintsugiTestCase.test_determinism) ... ok
test_empty_gold_solid_omits_file_and_warns (test_kintsugi.KintsugiTestCase.test_empty_gold_solid_omits_file_and_warns) ... ok
test_export_repair_runs_once_per_guard_evaluation (test_kintsugi.KintsugiTestCase.test_export_repair_runs_once_per_guard_evaluation) ... ok
test_growth_paths_planar_and_tjunc (test_kintsugi.KintsugiTestCase.test_growth_paths_planar_and_tjunc) ... ok
test_growth_rim_seeding_and_penetration (test_kintsugi.KintsugiTestCase.test_growth_rim_seeding_and_penetration) ... ok
test_growth_tortuosity_floor (test_kintsugi.KintsugiTestCase.test_growth_tortuosity_floor) ... ok
test_high_severity_bowl_not_rejected (test_kintsugi.KintsugiTestCase.test_high_severity_bowl_not_rejected) ... ok
test_input_envelope_rejection (test_kintsugi.KintsugiTestCase.test_input_envelope_rejection) ... ok
test_input_validation (test_kintsugi.KintsugiTestCase.test_input_validation) ... ok
test_junctions_connected (test_kintsugi.KintsugiTestCase.test_junctions_connected) ... ok
test_no_points_on_wall_limit_lines (test_kintsugi.KintsugiTestCase.test_no_points_on_wall_limit_lines) ... ok
test_noise_field_gradient_bounded_and_no_crossings (test_kintsugi.KintsugiTestCase.test_noise_field_gradient_bounded_and_no_crossings) ... ok
test_parameter_table (test_kintsugi.KintsugiTestCase.test_parameter_table) ... ok
test_printable_channel_thickness (test_kintsugi.KintsugiTestCase.test_printable_channel_thickness) ... ok
test_projection_clamps_rim_and_records_normal_thickness (test_kintsugi.KintsugiTestCase.test_projection_clamps_rim_and_records_normal_thickness) ... ok
test_projection_takes_min_and_bounds_normal_miss (test_kintsugi.KintsugiTestCase.test_projection_takes_min_and_bounds_normal_miss) ... ok
test_ray_tiebreak_direction (test_kintsugi.KintsugiTestCase.test_ray_tiebreak_direction) ... ok
test_ribbon_no_retries_out_of_sample_cases (test_kintsugi.KintsugiTestCase.test_ribbon_no_retries_out_of_sample_cases) ... ok
test_ribbon_through_wall (test_kintsugi.KintsugiTestCase.test_ribbon_through_wall) ... ok
test_roundtrip_guard_raises_and_writes_nothing (test_kintsugi.KintsugiTestCase.test_roundtrip_guard_raises_and_writes_nothing) ... ok
test_seed_sweep_watertight (test_kintsugi.KintsugiTestCase.test_seed_sweep_watertight) ... ok
test_stl_disk_roundtrip (test_kintsugi.KintsugiTestCase.test_stl_disk_roundtrip) ... ok
test_tapered_lip_continuous_vein_and_backing (test_kintsugi.KintsugiTestCase.test_tapered_lip_continuous_vein_and_backing) ... ok
test_thin_wall_fixture_rejected_by_envelope (test_kintsugi.KintsugiTestCase.test_thin_wall_fixture_rejected_by_envelope) ... ok
test_unbounded_rays_obey_voronoi_definition (test_kintsugi.KintsugiTestCase.test_unbounded_rays_obey_voronoi_definition) ... ok
test_valid_ceramic_run_keeps_gold (test_kintsugi.KintsugiTestCase.test_valid_ceramic_run_keeps_gold) ... ok
test_vein_cutter_no_kissing (test_kintsugi.KintsugiTestCase.test_vein_cutter_no_kissing) ... ok
test_vein_depth (test_kintsugi.KintsugiTestCase.test_vein_depth) ... ok
test_vein_no_retries_out_of_sample_cases (test_kintsugi.KintsugiTestCase.test_vein_no_retries_out_of_sample_cases) ... ok
test_vessel_without_wall_range_rejected (test_kintsugi.KintsugiTestCase.test_vessel_without_wall_range_rejected) ... ok
test_volume_smoke (test_kintsugi.KintsugiTestCase.test_volume_smoke) ... ok
test_wall_range_clamp_keeps_gold_out_of_floor (test_kintsugi.KintsugiTestCase.test_wall_range_clamp_keeps_gold_out_of_floor) ... ok
test_wealthy_case (test_kintsugi.KintsugiTestCase.test_wealthy_case) ... ok
test_api_fracture_defaults_to_vein_growth (test_web_api.WebApiTestCase.test_api_fracture_defaults_to_vein_growth) ... ok
test_api_fracture_empty_gold_pipeline (test_web_api.WebApiTestCase.test_api_fracture_empty_gold_pipeline) ... ok
test_api_fracture_success (test_web_api.WebApiTestCase.test_api_fracture_success) ... ok
test_api_fracture_thin_wall_rejected (test_web_api.WebApiTestCase.test_api_fracture_thin_wall_rejected) ... ok
test_api_fracture_wealthy (test_web_api.WebApiTestCase.test_api_fracture_wealthy) ... ok
test_api_presets (test_web_api.WebApiTestCase.test_api_presets) ... ok
test_api_upload_too_large (test_web_api.WebApiTestCase.test_api_upload_too_large) ... ok
test_api_validate_ok (test_web_api.WebApiTestCase.test_api_validate_ok) ... ok
test_api_validate_open_mesh (test_web_api.WebApiTestCase.test_api_validate_open_mesh) ... ok
test_api_validate_thin_wall_rejected (test_web_api.WebApiTestCase.test_api_validate_thin_wall_rejected) ... ok
test_job_retention (test_web_api.WebApiTestCase.test_job_retention) ... ok

----------------------------------------------------------------------
Ran 63 tests in 491.886s

OK
tapered lip: p5=2.404 mm, t_min=1.114 mm, d_min=0.557 mm, backing_min=0.557 mm, backing_min(t>=1.6)=0.839 mm
```

### Metrics & Data Invariants

| Metric / invariant | Before | After | Delta / observation |
| :--- | :--- | :--- | :--- |
| Automated test count | 57 pre-existing | 63 total (57 + 6 new) | 0 pre-existing tests removed or skipped |
| `test_crack_growth` baseline | 3/3 pass | 3/3 pass | No growth-generator regression |
| `test_kintsugi` suite | pass | pass | No parameter, projection, cutter, or export regression |
| `test_envelope` suite | pass | pass | Wall-envelope rejection unchanged |
| `test_web_api` suite | pass | pass | HTTP 400/200 behavior unchanged for existing modes |
| Presets | `presets/tea_bowl.stl`, `presets/vase.stl` | unchanged | No asset rewrite or deletion |
| Default generator | `growth` | `growth` | No behavior change unless `generator="shard"` is explicit |
| Vein-mode watertightness (shard) | n/a | Tea Bowl + Tall Vase: `is_watertight`, `is_volume`, zero bad edges | New end-to-end coverage |
| Contact-sheet matrix | growth only | shard 12/12 cells + growth baseline | Same 2 presets × 3 severities × 2 seeds |

## 60-Second Re-Verification

Fast smoke command (open wedge truncation + closed-loop closure/cyclic clearance; runs in ~1 s):

```bash
./.venv/bin/python -m unittest \
  tests.test_crack_shard.CrackShardTestCase.test_open_wedge_seam_exact_truncation_and_rim_landing \
  tests.test_crack_shard.CrackShardTestCase.test_closed_loop_drift_bridge_closure_and_cyclic_clearance -v
```

Full re-verification:

```bash
./.venv/bin/python -m unittest tests.test_crack_shard -v
./.venv/bin/python -m unittest discover -s tests -p "test_*.py" -v
./.venv/bin/python tools/spike_contact_sheet.py --generator shard --output reports/contact_sheet_shard.png
```
