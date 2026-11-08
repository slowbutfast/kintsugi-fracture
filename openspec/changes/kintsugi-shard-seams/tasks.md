## 1. Test Scaffolding (TDD)

- [x] 1.1 Create `tests/test_crack_shard.py` with failing test `test_open_wedge_seam_exact_truncation_and_rim_landing` verifying that open rim-to-rim wedge seams have no flat-run shelves (no two consecutive points within $1\text{e-}6$ mm of bounds), raw endpoints extend above `wall_z_max` by $\le 0.35W$, and projected 3D endpoints land on the upper rim lip ($z \ge \text{wall\_z\_max} - 0.5W$).
- [x] 1.2 Add failing test `test_closed_loop_drift_bridge_closure_and_cyclic_clearance` in `tests/test_crack_shard.py` verifying that closed loop seams satisfy `_periodic_distance(path[0], path[-1], period) <= 1e-6` via linear drift bridge, remain strictly within $[\text{wall\_z\_min} + 0.6W, \text{wall\_z\_max} - 0.6W]$, fall back to Primitive A (Wedge) if available wall height forces $\alpha < 5^\circ$, and pass `analyze_growth_paths` with cyclic segment skip across $u=0 \equiv P$.
- [x] 1.3 Add failing test `test_two_seam_verified_intersection_and_fallback` in `tests/test_crack_shard.py` verifying that for $S \ge 0.35$, when 2 paths are returned, Seam 2 terminates at an exact shared T-junction vertex on Seam 1 inside $[\text{wall\_z\_min} + W, \text{wall\_z\_max} - W]$ at arrival angle $\ge 30^\circ$, `params["_growth_junctions"]` records the junction metadata, `analyze_growth_paths` passes with clearance $\ge W + 0.8\text{ mm}$, and the generator deterministically falls back to `[Seam 1]` if 16 candidate draws fail.
- [x] 1.4 Add failing test `test_closed_loop_quadrant_subarc_tortuosity` in `tests/test_crack_shard.py` verifying that `_tortuosity_values` splits closed periodic loops into 4 quadrant sub-arcs in 2D $(u, z)$ space, producing finite tortuosity values satisfying $\tau \ge 1.05$ across $R \in \{0.5, 0.2, 0.0\}$ ($S \in \{0.5, 0.8, 1.0\}$) with median tortuosity increasing monotonically as $R$ decreases from $0.5$ to $0.0$.
- [x] 1.5 Add failing test `test_generate_kintsugi_mesh_shard_mode_watertight_and_ribbon_guard` in `tests/test_crack_shard.py` verifying that `generate_kintsugi_mesh(..., mode="vein", generator="shard")` produces watertight ceramic and gold meshes with zero bad edges on Tea Bowl and Tall Vase, and raises `ValueError` when invoked with `mode="ribbon"`.
- [x] 1.6 Add failing test `test_api_fracture_shard_mode_validation` in `tests/test_crack_shard.py` verifying that `POST /api/fracture` accepts `generator=shard` in `mode=vein`, and returns HTTP status 400 Bad Request when called with `generator=shard` and `mode=ribbon`.

## 2. Closed-Loop Audit & Tortuosity Helpers

- [x] 2.1 Update `analyze_growth_paths` in `kintsugi.py` (`L1996-L2002`) so paths that are closed periodic loops (`_periodic_distance(path[0], path[-1], period) <= 1e-6`) compute adjacent segment skip span cyclically (`min(diff, n_path_segs - diff) <= skip_span`).
- [x] 2.2 Update `_tortuosity_values` in `kintsugi.py` (`L1912-L1948`) so closed periodic loops without split junctions are split into 4 equal quadrant sub-arcs ($\Delta u = P / 4$) in 2D $(u, z)$ space before computing arc over chord, enforcing the engine floor $\tau \ge 1.05$.

## 3. Shard-Plane Generator Implementation

- [x] 3.1 Implement `generate_shard_crack_paths(params: dict, rng: np.random.Generator, *, subdivide_step: float | None = None) -> list[np.ndarray]` in `kintsugi.py` (`L2080-L2110`) supporting Primitive A (Wedge with `_truncate_polyline_z`) and Primitive B (Loop with linear drift bridge closure and height capping).
- [x] 3.2 Implement candidate Seam 2 evaluation ($\le 16$ deterministic draws), arrival-angle check ($\ge 30^\circ$), shared T-junction vertex insertion, `params["_growth_junctions"]` metadata recording, `analyze_growth_paths` clearance gate ($\ge W + 0.8\text{ mm}$), and single-seam fallback in `generate_shard_crack_paths`.
- [x] 3.3 Wire `generate_crack_paths` (`L2089-L2106`) to dispatch `generator == "shard"` to `generate_shard_crack_paths`. Update `generate_kintsugi_mesh` (`L3018-L3022`) to validate `generator in ("growth", "shard", "voronoi")` and raise `ValueError` if `generator == "shard"` and `mode != "vein"`. Update CLI argument parser in `kintsugi.py` (`L3270-L3276`).

## 4. Contact Sheet Comparison Tooling

- [x] 4.1 Update `tools/spike_contact_sheet.py` (`L45-L70, L370-L400, L420-L505`) to accept `--generator {growth,shard,both}`, pass `generator` into `generate_kintsugi_mesh`, and default output to `reports/contact_sheet_shard.png` for `shard`.
- [x] 4.2 Render `reports/contact_sheet_shard.png` via `.venv/bin/python tools/spike_contact_sheet.py --generator shard --output reports/contact_sheet_shard.png` and verify all 12 cells complete cleanly.

## 5. Verification & Empirical Audit

- [x] 5.1 Run `.venv/bin/python -m unittest tests/test_crack_shard.py -v` and the full regression suite `.venv/bin/python -m unittest discover -s tests -p "test_*.py" -v`, verifying 100% pass rate and zero regressions.
- [x] 5.2 Populate `verification.md` with Requirement Adherence Matrix, resolved assumptions, contact sheet comparison summary, and verbatim execution logs.
- [ ] 5.3 Perform visual inspection of `reports/contact_sheet_shard.png` side-by-side with `reports/contact_sheet.png` across all 12 cells.
- [ ] 5.4 Human review and decision on future default generator (`growth` vs `shard`).
