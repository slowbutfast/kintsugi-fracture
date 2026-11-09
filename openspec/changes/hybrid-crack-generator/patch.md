# Patch Log — `hybrid-crack-generator`

### [PATCH-01] Enforce Audit & Fragment Guarantees, Default Auto Shape to Wedge, Accelerate Collision Checks, and Fix OpenSpec Hygiene
- **Date**: 2026-11-09 19:50:00 UTC
- **Feedback Source**: Code Review (PR #9 — Agent 1 & Agent 2 Reviews)
- **Reported Issue**:
  1. **Critical — Combined audit & fragment guarantees are not enforced (`kintsugi.py:3381-3452`)**: `cup_unitree` at `R=0.2, seed=1` produces `audit_clearance_violations = 3` (`min_clearance = 2.32 mm < 2.72 mm`), yet `generate_hybrid_crack_paths` returns the violating paths instead of retrying or raising `ValueError`. Similarly, if `through_fragments < 2` after 3 retries, it falls through silently.
  2. **Important — `through_shape="auto"` picks 50/50 loop vs wedge (`kintsugi.py:3252-3253`)**: A closed loop does not reach the rim; owner confirmed `through_shape="auto"` should default to `"wedge"` so default hybrid fractures always have an edge-reaching rim-to-rim break.
  3. **Important — 16× path generation slowdown (`kintsugi.py:2681`, `kintsugi.py:1171`)**: On `bowl_urdformer` at `R=0.2`, hybrid takes `12.9 s` (`4.9 s` in `_shard_first_intersection` and `6.2 s` in `_first_growth_collision`) because Stage-1 seams are densely sampled (`0.25 * W`) with no segment bounding-box pre-filter.
  4. **Important — OpenSpec artifact & spec-sync state**: `architecture.md`, `design.md`, and `tests.md` were missing on the PR branch, and `openspec/specs/mesh-fracture-engine/spec.md` and `openspec/specs/retro-web-gui/spec.md` were synced prematurely before archiving.
  5. **Nits**:
     - `R = 0.8` gives `S = 1 - 0.8 = 0.19999999999999996 < 0.20` due to IEEE-754 float subtraction (`kintsugi.py:3105, 3343`).
     - Fractional integer knobs (e.g. `through_count=2.5`) are silently truncated by `int(...)` in `_validate_hybrid_options` (`kintsugi.py:3028-3045`), and non-numeric strings in `web_app.py:181-186` return FastAPI `422` instead of `400`.
     - Leftover `if bool(wall_probe.get("has_wall", True)):` guard at `kintsugi.py:543` is always true after the line 536 raise.
     - `_count_wall_fragments` (`kintsugi.py:3157-3234`) leaves the lower `wall_z_min` boundary open so hairlines reaching `wall_z_min` overcount regions that the vessel floor still joins.
     - Rename `test_fragment_guarantee_across_holdout_seeds` to `test_fragment_guarantee_across_seeds_42_61`, record commit SHA and verbatim test timing/commands in `verification.md`, and remove temporary `pr9` / `mainclean` worktrees.
- **Root Cause**:
  1. In `generate_crack_growth_paths` (`kintsugi.py:1764, 1867`), when Stage-2 hairlines T-junction onto Stage-1 seams, `_subdivide_path` inserts the shared vertex into `paths[:base_offset]`, which is then discarded when `generate_crack_growth_paths` returns only `result` (the new hairlines), so `generate_hybrid_crack_paths` (`kintsugi.py:3422`) audits the un-subdivided `stage1` list; additionally, `_growth_seam_anchors` (`kintsugi.py:1363-1428`) and rim stubs (`kintsugi.py:1508-1533`) do not check clearance against non-parent Stage-1 seams/junctions, and `generate_hybrid_crack_paths` does not retry Stage 2 or raise `ValueError` on non-zero audit violations.
  2. `_shard_first_intersection` and `_first_growth_collision` evaluate `_segment_contact` in Python for every segment pair without a fast 2D bounding-box reject, and Stage-1 polylines are sampled at `0.25 * W` before Stage 2 runs.
- **Target Files**: `kintsugi.py, web_app.py, static/index.html, static/viewer.js, tests/test_crack_hybrid.py, tests/test_web_api.py, openspec/specs/mesh-fracture-engine/spec.md, openspec/specs/retro-web-gui/spec.md, openspec/changes/hybrid-crack-generator/architecture.md, openspec/changes/hybrid-crack-generator/design.md, openspec/changes/hybrid-crack-generator/tests.md, openspec/changes/hybrid-crack-generator/verification.md, openspec/changes/hybrid-crack-generator/tasks.md`
- **Expected Resolution**:
  - `cup_unitree` (`R=0.2, seed=1`) and a synthetic cup regression fixture pass `analyze_growth_paths` with `crossings == 0` and `clearance_violations == 0`, and `generate_hybrid_crack_paths` raises `ValueError` if retries ever fail `through_fragments >= 2` or the combined audit.
  - `through_shape="auto"` deterministically selects `"wedge"`.
  - Hybrid path generation on `tea_bowl` / `bowl_urdformer` at `R=0.2` completes in `< 1.5 s`, while all 72 `growth`/`shard` SHA-256 baseline digests remain 100% unchanged.
  - `openspec status --change hybrid-crack-generator` shows all artifacts complete, `openspec/specs/` is clean against `origin/main`, and all unit + API tests pass.
- **Status**: RESOLVED (2026-11-09)
- **Resolution**:
  - Propagated subdivided Stage-1 polylines back through `params["_updated_initial_paths"]`, so the combined audit sees every Stage-2 T-junction vertex.
  - Added anchor clearance against junction points and non-parent seams, rim-stub clearance checks, and fail-closed Stage-2 retries.
  - Stage 1 now raises `ValueError` after three retries when `S >= 0.20` and `through_fragments < 2`; the combined audit raises on crossings/clearance failure after three retries.
  - `through_shape="auto"` now deterministically selects `"wedge"` and records `through_shape_requested`.
  - Added conservative 2D bounding-box prefilters to `_first_growth_collision` and `_shard_first_intersection`, plus coarser hybrid-only Stage-1 extra-seam sampling. `bowl_urdformer` at `R=0.2` now runs in ~1.47 s max over seeds 0–9 (median ~0.86 s), with zero audit violations.
  - Rounded hybrid severity to 9 decimals (`R=0.8` resolves to `S=0.2`), rejected booleans/fractional/malformed integer knobs, and changed `web_app.py` knob fields to strings so malformed values return HTTP 400.
  - Kept the bottom raster row connected for combined fragment counting and removed the dead `has_wall` guard.
  - Reverted the premature `openspec/specs/` sync, restored `architecture.md`, `design.md`, `tests.md`, and removed the temporary `pr9` / `mainclean` worktrees.
  - Reproducing regression: synthetic 22.5 mm-radius cup at `R=0.2, seed=1` previously reported 3 clearance violations; it now reports 0. The real `cup_unitree` fixture is also checked when present.
