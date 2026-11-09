# Surgical Patch Handoff: OpenSpec Change 'hybrid-crack-generator' [PATCH-01]

## 1. Executive Objective & Diagnostic Feedback
- **Change Name**: `hybrid-crack-generator`
- **Patch ID**: `PATCH-01`
- **Target Worktree / Branch**: `/home/node/.local/share/opencode/worktree/fffe954eb04701865d9ff532e39b2c85f865ef3f/eager-narwhal` (`feat/hybrid-crack-generator-clean` -> `origin/feat/hybrid-crack-generator`, PR #9)
- **Objective**: Enforce fail-closed combined audit and fragment guarantees (fixing the `cup_unitree` `R=0.2, seed=1` clearance defect), default `through_shape="auto"` to `"wedge"`, accelerate `_shard_first_intersection` and `_first_growth_collision` via 2D bounding-box pre-filtering, restore missing OpenSpec artifacts, revert the premature `openspec/specs/` sync, and resolve reviewer nits.
- **Feedback & Diagnostic Trace**:
  ```text
  1. [Critical - kintsugi.py:3412-3452] The combined audit runs, but its result is never enforced.
     Reproduction: cup_unitree, R = 0.2, seed = 1, every knob on Auto -> audit_clearance_violations = 3, min_clearance = 2.32 mm (< W + 0.8 = 2.72 mm).
  2. [Critical - kintsugi.py:3381-3398] After 3 retries, if through_fragments < 2, generation silently continues instead of raising ValueError.
  3. [Owner Decision - kintsugi.py:3252-3253] through_shape="auto" currently picks 50/50 loop vs wedge; change auto to always select "wedge" so default hybrid fractures always reach the rim.
  4. [Important - kintsugi.py:2681, 1171] Path generation is ~16x slower than growth on bowl_urdformer at R=0.2 (12.9 s vs 0.79 s) due to dense Stage-1 polylines and unindexed Python segment-contact loops in _shard_first_intersection and _first_growth_collision.
  5. [Important - openspec/] architecture.md, design.md, and tests.md are missing on the PR branch, and openspec/specs/{mesh-fracture-engine,retro-web-gui}/spec.md were synced prematurely before archive.
  6. [Nits]
     - R = 0.8 gives S = 1 - 0.8 = 0.19999999999999996 < 0.20 in hybrid config/dispatch (round S to 9 decimals in hybrid).
     - Fractional integer knobs (through_count=2.5) are silently truncated by int(...), and web_app.py returns 422 instead of 400 on non-numeric knob strings.
     - Leftover `if bool(wall_probe.get("has_wall", True)):` at kintsugi.py:543 is dead code after the line 536 raise.
     - _count_wall_fragments leaves the bottom row (z_min) open so hairlines touching wall_z_min split regions that the floor still joins (keep a 1-row connected floor strip at row 0 for combined fragment counting or only let through-fractures split the bottom boundary).
     - Rename test_fragment_guarantee_across_holdout_seeds -> test_fragment_guarantee_across_seeds_42_61 and update verification.md with commit SHA and verbatim test output.
  ```
- **Root Cause Analysis**:
  1. **Missing subdivided Stage-1 vertices & anchor/stub clearance**: When Stage-2 hairlines T-junction onto a Stage-1 seam inside `generate_crack_growth_paths` (`kintsugi.py:1764`), `_subdivide_path` inserts the shared vertex into `paths[collision["path_id"]]` (`paths[:base_offset]`). However, `generate_crack_growth_paths` (`kintsugi.py:1867`) discards `paths[:base_offset]` and returns only `result` (the new hairlines), so `generate_hybrid_crack_paths` (`kintsugi.py:3422`) constructs `combined` from the **un-subdivided** `stage1` list! Without the shared vertex on the Stage-1 polyline, `analyze_growth_paths` does not recognize the T-junction as incident and flags a clearance violation. In addition, `_growth_seam_anchors` (`kintsugi.py:1363-1428`) does not check that candidate anchor vertices are at least `2.0 * r_clear` away from existing junctions and other Stage-1 seams, and rim stubs (`kintsugi.py:1508-1533`) do not check `_first_growth_collision` against `initial_paths`.
  2. **O(N*M) Python segment distance calls**: `_shard_first_intersection` and `_first_growth_collision` call `_segment_contact` on every segment pair without a fast scalar bounding-box check (`abs(dx) > r_clear` / `abs(dz) > r_clear`).

## 2. Strict Target Context Map
| File Path (relative to repo root) | Target Lines | Modification Summary |
|---|---|---|
| `kintsugi.py` | `L535-L560` | Remove the redundant `if bool(wall_probe.get("has_wall", True)):` wrapper at `L543` after the `L536` `ValueError` raise. |
| `kintsugi.py` | `L1171-L1275` | In `_first_growth_collision`, add a fast scalar bounding-box pre-filter before calling `_segment_contact`: compute `seg_z_lo = min(a[1], b[1]) - r_clear`, `seg_z_hi = max(a[1], b[1]) + r_clear`, and skip any obstacle segment `(c, d)` where `max(c[1], d[1]) < seg_z_lo or min(c[1], d[1]) > seg_z_hi`, or where periodic `u` interval distance exceeds `r_clear` (keeping exact results identical while skipping >95% of Python calls). |
| `kintsugi.py` | `L1363-L1429` | In `_growth_seam_anchors`, require each candidate anchor point `points[index]` to have periodic distance `>= 2.0 * r_clear` from all existing junction points (`params.get("_growth_junctions")`) and from all segments of other paths (`path_idx != path_index`), and verify that a test step of length `1.5 * W` along `heading` passes `_first_growth_collision` with `exempt_path_id=path_index, exempt_origin=point`. |
| `kintsugi.py` | `L1508-L1534`, `L1862-L1895` | In `generate_crack_growth_paths`: when `base_offset > 0`, skip any rim seed whose `[start, stub]` collides with `paths[:base_offset]` in `_first_growth_collision`; at function exit (`L1866`), store the subdivided pre-committed paths in `params["_updated_initial_paths"] = [np.asarray(paths[i], dtype=np.float64) for i in range(base_offset)]` so `generate_hybrid_crack_paths` uses the Stage-1 polylines that include all shared Stage-2 T-junction vertices. |
| `kintsugi.py` | `L2681-L2735` | In `_shard_first_intersection`, add a fast scalar `z` and periodic `u` bounding-box pre-filter before `_segment_contact`. |
| `kintsugi.py` | `L3001-L3136` | In `_validate_hybrid_options`, reject booleans and fractional floats/strings for `through_count` and `hairline_count` (e.g. if `isinstance(raw, float) and not raw.is_integer()`, or `str(raw)` contains `.` / fails strict int parsing, raise `ValueError`). In `_resolve_hybrid_config`, use `S = round(float(params.get("S", 0.0)), 9)` so `R=0.8` resolves to `S=0.2`. |
| `kintsugi.py` | `L3157-L3235` | In `_count_wall_fragments`, add keyword `close_floor: bool = False`; when `close_floor=True` (used for combined `num_fragments` when hairlines are present, since `wall_z_min` is joined by the solid vessel floor while shard nadirs stay `>= wall_z_min + 0.18 * H`), keep row `0` (`z = wall_z_min`) unblocked by Stage-2 hairlines so dead-ending floor hairlines do not artificially inflate `num_fragments` to 11–13. |
| `kintsugi.py` | `L3237-L3460` | In `_hybrid_stage1_paths`: change `if shape == "auto": shape = "wedge"` (and record `config["through_shape_requested"] = str(config["through_shape"])`). In `generate_hybrid_crack_paths`: use `severity = round(float(params.get("S", 0.0)), 9)`; after 3 Stage-1 retries, if `severity >= 0.20 and through_fragments < 2`, raise `ValueError("Hybrid Stage 1 failed to partition wall into >= 2 fragments")`; in Stage 2, wrap `generate_crack_growth_paths` + `analyze_growth_paths` in up to 3 deterministic retries using `stage1_updated = params.get("_updated_initial_paths", stage1)`, and if `int(stats["crossings"]) > 0 or int(stats["clearance_violations"]) > 0 or (stats.get("min_clearance") is not None and float(stats["min_clearance"]) < r_clear - 1e-6)`, raise `ValueError("Hybrid combined crack graph failed clearance/crossing audit")`. |
| `web_app.py` | `L180-L205` | Change `through_count`, `tilt_deg`, `hairline_count`, `hairline_reach`, and `roughness` form parameters from `int | None` / `float | None` to `str | None = Form(default=None)` so malformed strings (e.g. `through_count="abc"` or `"2.5"`) reach `_validate_hybrid_options` and return `HTTP 400` instead of FastAPI `422`. |
| `tests/test_crack_hybrid.py` | `L1-L520` | Rename `test_fragment_guarantee_across_holdout_seeds` to `test_fragment_guarantee_across_seeds_42_61`; add `test_cup_unitree_r02_seed1_clearance_regression` (synthetic cup matching `cup_unitree` dimensions/wall profile at `R=0.2, seed=1` + real `cup_unitree.stl` if present), `test_r08_tier_boundary_produces_fracture`, `test_fractional_integer_knobs_rejected`, and `test_auto_shape_defaults_to_wedge`. |
| `tests/test_web_api.py` | `L180-L260` | Add test verifying `POST /api/fracture` with `generator="hybrid"` and `through_count="abc"` or `through_count="2.5"` returns `HTTP 400`. |
| `openspec/specs/mesh-fracture-engine/spec.md`, `openspec/specs/retro-web-gui/spec.md` | Full file | Revert premature spec sync (`git checkout origin/main -- openspec/specs/`) so `openspec/specs/` stays untouched until archive. |
| `openspec/changes/hybrid-crack-generator/{architecture.md,design.md,tests.md,patch.md,tasks.md,verification.md}` | Full file | Ensure `architecture.md`, `design.md`, `tests.md`, and `patch.md` are present on the PR branch, mark `P01.1–P01.4` `[x]` in `tasks.md`, mark `PATCH-01` `RESOLVED` in `patch.md`, and update `verification.md` with the tested commit SHA and verbatim test output. |

## 3. Blast Radius & Invariant Guardrails
- **STRICT BLAST RADIUS**: Modify ONLY the files and line ranges in the Target Context Map on the PR #9 branch.
- **FORBIDDEN**:
  - Do NOT alter the 72 pre-change SHA-256 baseline digests for `generator="growth"` or `generator="shard"`. Note: keep `_first_growth_collision` and `_shard_first_intersection` bounding-box pre-filters strictly conservative (`min - r_clear - 1e-6`, `max + r_clear + 1e-6`) so they never change which segment is hit or the floating-point arithmetic on candidate segments within `r_clear`.
  - Do NOT modify `.env` or credential files.
  - Do NOT use seeds in reserved hold-out ranges (`300–399` and `>= 600`).
- **INVARIANTS TO PRESERVE**: All 72 `growth`/`shard` baseline digests and all existing unit/API tests MUST pass 100%.

## 4. Visual & UI Impact
- In `static/index.html` / `static/viewer.js`, ensure `#hybrid-through-shape` option `auto` is labelled `Auto (Rim-to-Rim Wedge)` matching the confirmed `"wedge"` default. No CSS or layout changes.

## 5. Reproduction & Verification Protocol
1. **Reproduce First**:
   Run `./.venv/bin/python -m unittest tests.test_crack_hybrid tests.test_web_api -v` after adding the `cup_unitree` (`R=0.2, seed=1`) clearance assertion, `R=0.8` boundary assertion, `through_shape="auto" -> "wedge"` assertion, and fractional/malformed knob `HTTP 400` assertions. Confirm they fail before the fix.
2. **Apply Minimal Fix**: Apply the targeted edits in `kintsugi.py`, `web_app.py`, `static/index.html`, and `openspec/`.
3. **Verify Fix & Speedup**:
   - Re-run `./.venv/bin/python -m unittest tests.test_crack_hybrid tests.test_web_api -v` and confirm 100% pass.
   - Verify path generation time on `tea_bowl` (and `bowl_urdformer` / `cup_unitree` if present in `/tmp/claude-1001/-home-node-global-sandbox-projects-wax-robot/9bbab440-a7fe-4db6-b307-75b743311db4/scratchpad/demo/`) at `R=0.2` is `< 1.5 s` and passes `analyze_growth_paths` with `0` violations across seeds `0..9`.
4. **Full Regression Suite**:
   Run `./.venv/bin/python -m unittest discover -s tests -v` and `openspec validate "hybrid-crack-generator" --strict`.

## 6. Surgical Patch Checklist
- [ ] P01.1 Add reproducing tests in `tests/test_crack_hybrid.py` and `tests/test_web_api.py` and confirm failure.
- [ ] P01.2 Apply minimal fixes in `kintsugi.py` and `web_app.py` (subdivided Stage-1 propagation, anchor/stub clearance, fail-closed audit/fragment retries + `ValueError`, `auto -> wedge`, bounding-box pre-filter speedup, `S` rounding at `R=0.8`, strict int/string knob validation, floor-aware `_count_wall_fragments`, dead `has_wall` guard removal).
- [ ] P01.3 Restore `architecture.md`, `design.md`, `tests.md`, `patch.md` on the PR branch, revert `openspec/specs/` to `origin/main`, and remove temporary `pr9` / `mainclean` worktrees.
- [ ] P01.4 Run `./.venv/bin/python -m unittest discover -s tests -v` and `openspec validate "hybrid-crack-generator" --strict`, update `verification.md` and `patch.md` (`RESOLVED`), and mark `tasks.md` checkboxes `[x]`.
