# OpenCode Orchestration Handoff: OpenSpec Change 'kintsugi-mesh-fracture' — Round 3 Remediation (F14–F17)

You are the orchestration agent for OpenSpec change `kintsugi-mesh-fracture`, running in OpenCode. Execute this round with the **`openspec-apply-sub`** skill, which delegates the implementation tasks to `spec-coder-sub`.

Round 2 (F11–F13) landed and was independently confirmed:
- 30/30 tests pass;
- a fresh 160-run sweep on seeds 300–307 is clean, with 1 retry;
- 0 of 5,622 unbounded rays violate the Voronoi definition;
- no gold reaches the floor at R=0.

With the ray bug fixed, two crack-graph defects that it had been hiding became measurable. Two cleanup items also came out of the review. This round fixes all four. The previous handoff is preserved as `handoff-round1.md`, for reference only.

## 0. Before writing any code: record the findings

1. Add `verification.md §11 — Third independent verification findings (2026-11-06)` containing the findings table in §1 below, verbatim, plus a `### Round-3 remediation log` subsection for entries.
2. In the `verification.md §5` matrix, downgrade these rows to `Partial` and cite §11:
   - "Periodic Voronoi network";
   - "Unbounded ridges are rays";
   - "Band-edge terminations are not flat";
   - "Perturbed points stay on the wall".
3. In `research.md`:
   - **Verified facts:** add the F14 strip-end distortion mechanism and the F16 repair frequency.
   - **Superseded claims:** add "requiring a central seed only for rays is sufficient", and add that "Clamp to `max(z_min, z_wall,lo) + W/2`" is superseded by truncation at the wall range (F15).

## 1. Findings to fix (ground truth)

All numbers come from the reviewer's runs against `kintsugi.py` as of 15:36 on 2026-11-06 (md5 `852aaf6c8f91a031b0e8dfb5593a89ff`).

| ID | Severity | Finding | Evidence | Location |
|---|---|---|---|---|
| F14 | CRITICAL | **Phantom ridges from the strip ends.** `generate_crack_paths` requires a central-tile seed only for rays. Finite ridges are kept for all three shifts even when both seeds sit in tile −1 or tile +1. Near the ends of the 3-tile strip the diagram is not periodic: those ridges are bent by the neighbours that would sit one tile further out. The shift then drops the bent copy into the central tile, where it overlaps or crosses real ridges. Example: tea bowl, S=0.6, seed 76, ridge 25 (two tile +1 seeds) runs to (770, −677) and duplicates the real ridge 34, ending 0.2 mm past the true vertex. | Measured with noise, jitter and clamp off, against a 9-tile ground truth over 200 seeds. Seeds emitting a path that is not on the periodic diagram: tea bowl S=0.6 **4**, S=1.0 **33**; vase S=0.6 **26**, S=1.0 **114**. Reviewer-tested fix: change `:592` to `if not has_central_seed: continue`. That gave **0/200 phantom and 0 dangling junctions** on both presets at S ∈ {0.6, 1.0}. | `kintsugi.py:584-593` |
| F15a | CRITICAL | **The clamp flattens crack ends onto straight lines and creates crossings.** `compute_parameters` clamps z to `[max(z_min, z_wall,lo) + W/2, min(z_max, z_wall,hi) − W/2]`, so the clamp applies at the band edge as well as the wall range. Every downward band-edge jitter is projected back onto one horizontal line, which violates the existing scenario "Band-edge terminations are not flat". The clamp also acts on subdivided points one by one, so chords crossing the line cut corners, and neighbouring cracks squeezed onto the same line tangle. | Path points lying exactly on a clamp line: 5.5–7.8% mean, 16.7% max. Crossing seeds with the clamp on vs off (noise and jitter off): tea bowl S=0.6 **4 vs 0**, S=1.0 **22 vs 2**; vase S=0.6 **18 vs 2** (the remaining 2s are F14). Full pipeline with noise off (`tools/crack_graph_audit.py`): crossing seeds tea bowl 7 / 26, vase 24 / **76** of 200 at S = 0.6 / 1.0. Visible as horizontal runs in the 2-D graph render. | `kintsugi.py:140-146`, `:674-687` |
| F15b | WARNING | **Band-edge jitter tilts whole ridges.** The jitter adds a vertical offset to the clipped endpoint, so the straight segment from the interior Voronoi vertex rotates and can cross a neighbour. | With F14 fixed and the clamp off: crossing seeds tea bowl 1/200 (S=0.6, seed 175) and 1/200 (S=1.0, seed 43); vase 0/200 (S=0.6) and 2/200 (S=1.0, seeds 153 and 174). | `kintsugi.py:652-661` |
| F16 | WARNING | **The sliver repair carries real load and runs 4 times per material.** It is a valid fix: float32 spacing near 100 mm is about 7.6e-6 mm, so edges under 1e-5 mm cannot survive binary STL anyway. But it is not a rare corner case. `_export_trimesh` is called separately for the guard (`:1409-1410`), the STL write (`:1137`), the 3MF write (`:1204`, `:1213`) and the triangle counts (`:1441-1442`), and each candidate collapse does a full STL export and reload. | Fresh sweep: 142 of 964 exported meshes (15%) needed a repair, 4 repairs failed and fell back to a retry. Run time: median 1.4 s, max **27.4 s**. | `kintsugi.py:209-213`, `:1131-1139`, `:1180-1215`, `:1404-1443` |
| F17 | SUGGESTION | **Tie-break points the wrong way.** When both normal directions score the same within 1e-12, the code points the ray *toward* the third seed. The correct rule points it away from the third seed's side of edge ab, i.e. `dot(direction, c − midpoint(a, b)) < 0`. The code also measures from `finite` rather than from the midpoint. In practice this branch never runs. | Code inspection. | `kintsugi.py:528-534` |

## 2. Target Context Map

| File (relative to repo root) | Lines | Change |
|---|---|---|
| `kintsugi.py` | `L140-L163` (`compute_parameters`) | F15a: replace `z_clamp_lo/hi` with wall-only limits `z_wall_lo = wall_z_min + W/2` and `z_wall_hi = wall_z_max − W/2`. Do not mix in `z_min`/`z_max`. Keep the degenerate fallback (`lo > hi`): a vessel with no usable wall then yields no paths and must raise the existing envelope `ValueError` with a clear message, not silently produce output. |
| `kintsugi.py` | `L493-L538` (`_ridge_segment`) | F17: extract the tie-break into `_ray_tiebreak_direction(seed_a, seed_b, third, normal)`, which returns `normal` or `−normal` so that `dot(dir, third − 0.5*(seed_a + seed_b)) < 0`. Fix the comment. |
| `kintsugi.py` | `L584-L593` (`generate_crack_paths`, ridge filter) | F14: `if not has_central_seed: continue`. Update the comment: it applies to finite ridges and rays alike, and periodic copies with a central seed already cover any ridge that crosses the seam. |
| `kintsugi.py` | `L606-L625` and `L649-L661` (clip and jitter) | F15b: jitter **along the ridge**, not vertically. For each ridge, draw a per-terminal offset `δ ~ U(−0.1H, +0.1H)` and clip the ridge's own true segment against a z limit moved by δ: the bottom terminal against `z_min + δ_bottom`, the top against `z_max + δ_top`. Clip the raw (unclipped) ridge from `_ridge_segment`, not the band-clipped segment, so that extending past the band edge follows the real ridge geometry. A terminal therefore never leaves its ridge line. If the ridge's finite vertex lies inside the moved limit, the terminal stops at the vertex. Keep the current RNG draw order as far as possible, and document any change in the log. |
| `kintsugi.py` | `L674-L687` (`generate_crack_paths`, clamp) | F15a: **truncate instead of clamping.** Split each perturbed polyline wherever z leaves `[z_wall_lo, z_wall_hi]`. Insert the exact interpolated crossing point and drop the outside part. A polyline that leaves and re-enters becomes several paths. Keep a piece only if it has ≥ 2 points and length ≥ W. Remove the per-point `np.clip` on z. |
| `kintsugi.py` | `L1131-L1139`, `L1142-L1160`, `L1180-L1215`, `L1395-L1443` | F16: the guard computes the repaired trimeshes once per attempt (`_export_trimesh(ceramic)` and `_export_trimesh(gold)`) and counts bad edges on them. The meshes from the passing attempt go to `export_kintsugi_stl`, `export_kintsugi_3mf` and the triangle counts, through new optional `ceramic_mesh=` / `gold_mesh=` parameters (or `_from_trimesh` variants). The existing public signatures must keep working. Record `params["guard_evaluations"]`. |
| `tests/test_kintsugi.py` | `L587-L600` | Replace `test_voronoi_ridges_do_not_cross` with `test_crack_paths_lie_on_periodic_voronoi` (§5). Keep the `_first_crossing` helper. |
| `tests/test_kintsugi.py` | `[NEW]` after `L868` | The new tests in §5. |
| `tools/crack_graph_audit.py` | exists (reviewer-supplied) | Crack-graph audit: points off the periodic diagram, crossings, and the fraction of points on clamp lines. Do not change its metrics. You may update `_clamp_fraction`'s line list if the param names change, but the lines it checks must stay the band edges ±W/2 and the wall range ±W/2. |
| `openspec/changes/kintsugi-mesh-fracture/specs/mesh-fracture-engine/spec.md` | `L59-L97` | The scenario edits in §3. |
| `openspec/changes/kintsugi-mesh-fracture/specs/multi-material-export/spec.md` | `L39-L49` | "Export sliver repair": add a single repair per material per guard evaluation, with the repaired mesh reused for every export. |
| `openspec/changes/kintsugi-mesh-fracture/{verification,research,architecture,tests,tasks}.md` | — | The documentation obligations in §7. |

## 3. Technical & Architectural Boundaries

**In-scope decisions (do not relitigate):**
- The crack graph SHALL be a subset of the true periodic Voronoi diagram of the seeds before noise is applied. Every stage except the noise field (tiling, filtering, clipping, jitter, truncation) must keep points on that diagram. That makes the no-crossing property structural rather than tested-in.
- The noise field is unchanged. It is position-only, so shared junctions move identically.
- The wall range comes from `_probe_wall_range` (two-hit fraction ≥ 0.95). Do not change the probe or its threshold.
- The sliver repair stays as designed. The 1e-5 mm limit, the watertight, volume-valid and 1e-6 volume conditions, and the guard's 3 attempts are all unchanged. F16 is about when it runs, not what it does.
- All randomness is seeded. The cross-process determinism check must stay byte-identical. The crack graphs will change, so sample MD5s will change. That is expected: regenerate the samples and record the new MD5s.
- Never perturb the input mesh. Debris is never deleted. The wealthy-case behaviour is unchanged.

**Spec edits** (keep `openspec validate kintsugi-mesh-fracture --strict` green after each one):
- *Periodic Voronoi network*: replace "keeps ridges whose midpoint lies in the central tile" with "keeps only ridges (finite or unbounded) with at least one seed in the central tile, and shifts finite ridges by ±period to recover seam-crossing fragments". Add: "every emitted point lies on the periodic Voronoi diagram of the seeds before noise".
- *Unbounded ridges are rays*: state the tie-break rule correctly (away from the third seed's side of edge ab).
- *Band-edge terminations are not flat*: the terminal is moved **along its ridge** by clipping the ridge at a per-terminal limit `z_edge + δ`, with `δ ~ U(−0.1H, 0.1H)`. A terminal that reaches a Voronoi vertex first stops there.
- *Perturbed points stay on the wall*: rewrite as truncation. Polylines are cut where z leaves `[z_wall,lo + W/2, z_wall,hi − W/2]`, outside parts are discarded, and no point is projected onto the limit. No non-terminal path point lies on a horizontal limit line.
- Add the scenario *Crack graph is planar*: with the noise field zero, no two path segments intersect except at shared endpoints, for both presets at S ∈ {0.6, 1.0}.

**Hard exclusions / no-go:**
- Do NOT modify `.env`, `.env.*` or credential files.
- Do NOT add dependencies.
- Do NOT loosen thresholds or tolerances: the 5% miss limit, 1 mm³ debris, the 1e-6 volume check, 0.7 mm thickness, the 1e-5 repair limit, or the 1e-6·period on-diagram tolerance in the audit.
- Do NOT change seeds in existing tests. `test_ribbon_no_retries_out_of_sample_cases`, `test_vein_no_retries_out_of_sample_cases` and `test_wall_range_clamp_keeps_gold_out_of_floor` must still pass unchanged. If F14 or F15 makes one of them fail, that is a finding: log it, find the cause, and fix the cause.
- Do NOT touch `_make_noise`, `_probe_wall_range`, the cutter builders or `DESIGN.md`.
- Do NOT tune on seeds 300–399 or ≥ 600. The reviewer holds those out. Use the seed sets in §5.
- Do NOT archive, and do NOT run `openspec specs apply`.

## 4. Visual & UI Design Specifications

**Status: Non-visual / engine-only.** No web GUI, CSS or component changes. Do NOT touch `static/` or `DESIGN.md`.

## 5. Test Scaffolding & Verification Commands

- **Test runner:** `.venv/bin/python -m unittest discover -s tests -v`. pytest is not installed; do not add it.
- **Crack-graph audit:** `.venv/bin/python tools/crack_graph_audit.py --presets tea_bowl vase --severities 0.6 1.0 --seeds 200 --output output/verification/crack_graph_audit.json`
- **Tuning sweep:** `.venv/bin/python tools/sweep.py --presets tea_bowl vase --ratios 0 0.05 0.2 0.5 0.9 0.99 --modes ribbon vein --seeds 0 1 2 3 4 5`
- **Previous out-of-sample sweep:** `.venv/bin/python tools/sweep_out_of_sample.py --presets tea_bowl vase --ratios 0 0.1 0.35 0.6 0.8 --modes ribbon vein --seeds 100 101 102 103 104 105 106 107`
- **New out-of-sample sweep:** `.venv/bin/python tools/sweep_out_of_sample.py --presets tea_bowl vase --ratios 0.15 0.3 0.45 0.65 0.85 --modes ribbon vein --seeds 500 501 502 503 504 505 506 507 --output output/verification/sweep_round3.json`
- **Renders:** `.venv/bin/python tools/render_remediation.py . output/verification/renders_round3`. Also add 2-D `(u, z)` crack-graph PNGs for tea bowl S=1.0 seed 1 and S=0.6 seed 76, with the band edges and wall limits drawn as lines.
- **Spec validation:** `openspec validate kintsugi-mesh-fracture --strict --json`

**Expected baseline from the audit tool, before any fix:** crossing seeds tea bowl 7 / 26 and vase 24 / 76 at S = 0.6 / 1.0. Clamp-line points: 4–8% mean, ≤ 16.7% max. The phantom count reads 200/200 everywhere, because the clamp and the vertical jitter also put points off the diagram; the isolated F14 numbers are in §1. **Target after all fixes: 0 phantom, 0 crossing and 0.0% clamp-line points in all four rows.**

**TDD requirement.** Task 9.1 MUST add the tests below and run them, and you must paste the failing output into `verification.md §11` before touching `kintsugi.py`.

| New test | Asserts | Expected before the fix |
|---|---|---|
| `test_crack_paths_lie_on_periodic_voronoi` (replaces `test_voronoi_ridges_do_not_cross`) | `_make_noise` patched to zero. Tea bowl and vase × S ∈ {0.6, 1.0} × seeds 0–39. (a) Every path point's two nearest seeds in a 9-tile copy are equidistant within 1e-6·period. (b) `_first_crossing(paths, period) is None`. Rebuild the seeds from the same rng in the same draw order as `tools/crack_graph_audit.py`. Keep it under ~90 s. | Fails (F14, F15) |
| `test_no_points_on_wall_limit_lines` | Noise zero. Both presets × S=1.0 × seeds 0–19. No non-terminal point lies within 1e-9 of `wall_z_min + W/2`, `wall_z_max − W/2`, `z_min ± W/2` or `z_max ± W/2`. All points satisfy `z_wall_lo − 1e-9 ≤ z ≤ z_wall_hi + 1e-9`. | Fails (F15a) |
| `test_band_edge_terminals_are_ragged` | Noise zero, tea bowl, S=0.6, seeds 0–19. Over terminals within 0.1H of z_max, the standard deviation of z is > 0.02H, and both above-edge and below-edge terminals occur. | Fails (one-sided) |
| `test_ray_tiebreak_direction` | `_ray_tiebreak_direction(a=(0,0), b=(2,0), third=(1,1), normal=(0,1))` returns `(0,−1)`. With the normal flipped, it still returns `(0,−1)`. Also one rotated case. | `AttributeError` |
| `test_export_repair_runs_once_per_guard_evaluation` | Wrap `kintsugi._repair_stl_slivers` with a counting mock (`wraps=`). For tea bowl R=0.2, ribbon, seed 0, with the 3MF on, the call count == `2 × result["parameters"]["guard_evaluations"]`. Output files are still clean. | Fails (4 calls per material) |
| `test_vessel_without_wall_range_rejected` | A solid cylinder fixture (no two-hit range) raises `ValueError` mentioning the wall, and writes no files. | Decide during 9.1. If it already passes, note that and keep it. |

## 6. Implementation Task Checklist

Append this to `tasks.md` as `## 9. Third Verification Remediation`. Tick a box only when its step genuinely ran and passed.

- [ ] 9.0 Record the findings (§0): `verification.md §11`, matrix downgrades, `research.md` facts and superseded claims
- [ ] 9.1 Scaffold the §5 tests; paste the failing run into `verification.md §11`. Run `tools/crack_graph_audit.py` and both previous sweeps for the baseline, and record them verbatim
- [ ] 9.2 Fix F14 (central seed required for every ridge). Re-run the audit and record the phantom and crossing counts. They will not reach zero until F15 is done, so record the change
- [ ] 9.3 Fix F15b (jitter along the ridge by per-terminal clip limits); `test_band_edge_terminals_are_ragged` passes
- [ ] 9.4 Fix F15a (wall-only limits, truncation instead of clamp, wall-range rejection); `test_no_points_on_wall_limit_lines`, `test_crack_paths_lie_on_periodic_voronoi`, `test_wall_range_clamp_keeps_gold_out_of_floor` and `test_high_severity_bowl_not_rejected` pass
- [ ] 9.5 Fix F17 (`_ray_tiebreak_direction`); `test_ray_tiebreak_direction` and `test_unbounded_rays_obey_voronoi_definition` pass
- [ ] 9.6 Fix F16 (single repair per guard evaluation, reused for STL, 3MF and counts); `test_export_repair_runs_once_per_guard_evaluation` passes; report the sweep's median and max run time before and after
- [ ] 9.7 Update the specs (§3), `architecture.md`, `tests.md` and `research.md` (§7); `openspec validate --strict` is green
- [ ] 9.8 Run the full suite, the audit (target all zeros), all three sweeps, the cross-process determinism MD5 check, the renders and `generate_sample.py`. Record everything verbatim in `verification.md §11`, then restore matrix rows to `Met` only where the evidence supports it

## 7. Documentation Obligations (do these while you work, not at the end)

1. **After each fix task (9.2–9.6)**, append a dated entry to `verification.md §11 → Round-3 remediation log`:
   - the finding ID;
   - the root cause in one or two sentences;
   - the change, with `file:line`;
   - the tests that now pass, with verbatim output;
   - the before/after metric (audit row, call count, run time).
2. **`architecture.md`:**
   - **Decision 2 (periodic Voronoi):** add the central-seed rule for all ridges, the 3-tile strip-end distortion it prevents, and the invariant "every pre-noise point lies on the periodic diagram".
   - **Decision 7:** the repair runs once per guard evaluation and its result is reused, plus the measured repair frequency (15% of meshes).
   - Add a short "Crack terminals" note: per-terminal clip limits along the ridge, and truncation at the wall range. Explain why projecting points onto a line breaks planarity.
3. **`tests.md`:**
   - Document each new test with its asserts.
   - Replace the `test_voronoi_ridges_do_not_cross` entry.
   - Add `tools/crack_graph_audit.py` under Manual Verification, with its exact command and the target of zero.
4. **`research.md`:** add to Verified facts:
   - the F14 mechanism (seed 76, ridges 25 and 34);
   - the clamp-on vs clamp-off crossing table;
   - the 15% repair frequency.
5. **Finish when all of these hold:**
   - every 9.x box is ticked;
   - the test suite is green;
   - `openspec validate --strict` is green;
   - the audit is all zeros;
   - the tuning sweep shows 144/144 clean with no false rejections;
   - both out-of-sample sweeps show 160/160 clean, with retries reported and ≤ 2 per sweep;
   - determinism is byte-identical across processes.

   Then run `openspec-verify-change`. Task 6.3 (manual slicer check) may stay open. **Do not archive.**

## 8. Post-Implementation & Verification Obligations

When `spec-coder-sub` finishes:
1. Every `tasks.md §9` box is `- [x]`, and each is backed by a log entry in `verification.md §11`.
2. Data preservation:
   - `presets/*.stl` MD5s are unchanged: `benchy 4e386f38b9c125faafa1052f724c169f`, `tea_bowl b2a95e5a23ddadbac9d8871da9de28ee`, `vase c7aad0e6e4d95cfa40278f6bb142dc71`.
   - `output/` samples are regenerated by `generate_sample.py`, never edited by hand.
3. `verification.md §11` contains:
   - Executive Summary & Environment;
   - the Requirement Adherence Matrix, with every scenario (old, edited and new) mapped to its test plus the audit or sweep evidence;
   - Resolved Assumptions & Empirical Proof;
   - a Nomenclature & Code Symbol Audit (new or renamed symbols: `_ray_tiebreak_direction`, `z_wall_lo` / `z_wall_hi`, `guard_evaluations`, plus any truncation helper);
   - verbatim logs: tests, audit table, sweep summaries, timing, MD5s and the render list.
4. Run `openspec-verify-change`.
5. Do **not** run `openspec specs apply` and do not archive. Hand back for review with:
   - `output/verification/renders_round3/`;
   - the 2-D graph PNGs;
   - `output/verification/crack_graph_audit.json`.
