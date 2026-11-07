# OpenCode Orchestration Handoff: OpenSpec Change 'kintsugi-mesh-fracture' — Verification Remediation

You are the orchestration agent for OpenSpec change `kintsugi-mesh-fracture`, running in OpenCode.
Your primary directive is to execute the **remediation task group (## 7 in `tasks.md`)** using the **`openspec-apply-sub`** skill, which delegates task implementation to the `spec-coder-sub` subagent.

The change was implemented and its 15 tests pass, but an independent verification (`/openspec-verify-change`, 2026-11-06) showed that the suite only tests seed 7. Across a 144-run sweep, only **53 runs produced STLs that reload watertight**, and 12 runs falsely rejected a valid bowl. Your job is to fix those defects **test-first** and to **record every finding, decision and result in the OpenSpec artifacts as you go**, not only at the end.

## 0. Before writing any code: record the findings

Do this first, as task 7.0, so the artifacts reflect reality before any patch lands:

1. Append the remediation task group in §6 below to `openspec/changes/kintsugi-mesh-fracture/tasks.md` verbatim, as `## 7. Verification Remediation`.
2. In `verification.md`:
   - Add a section `## 8. Independent verification findings (2026-11-06)` that copies the findings table in §1 below.
   - In the Requirement Adherence Matrix (§5 of that file), change the status of these rows from `Met` to `**Failing — see §8**`: *Parameter-space crack generation*, *Watertight cutter construction*, *Paired manifold STL export*, *Supported input envelope*, *Preset selection and custom upload*.
   - Do not delete the previous logs. They are history.
3. In `research.md`:
   - Under `## Superseded claims`, add: "Single-seed geometry tests are sufficient evidence of watertight output. Superseded: a 144-run sweep showed 37% clean."
   - Add the verified facts from §1 (root causes) to `## Verified facts`, with today's date and how each was verified.

## 1. Findings to fix (ground truth)

Every number below was reproduced on this machine with `.venv` (manifold3d 3.5.4, trimesh 5.2.0).

| ID | Severity | Finding | Evidence | Location |
|---|---|---|---|---|
| F1 | CRITICAL | STL round-trip is non-watertight in 79 of 132 completed sweep runs. Manifold output reports `NoError`, but it contains *kissing* geometry: topologically separate pieces that share edges or vertices in space. STL reload merges vertices by position, which turns these into edges used by 4–6 faces. | Sweep (2 presets × R∈{0,0.05,0.2,0.5,0.9,0.99} × 2 modes × seeds 0–5); per-edge face-count histogram on reload | see F1a–F1c |
| F1a | CRITICAL | **Vein cutter:** every sphere has the same axis-aligned tessellation, so spheres along a path or at a junction share exactly coincident vertices, and their union kisses. A **seeded random rotation per sphere** brought bad edges from 6/34/36 to **0/0/0** (seeds 0, 1, 5; cutter, ceramic and gold all clean). | Experiment: `s.rotate(rng.uniform(0,360,3))` before translate | `kintsugi.py:578-597` (`build_vein_cutter`) |
| F1b | CRITICAL | **Ribbon cutter:** kissing edges already appear in the raw CSG (seed 0: 26 bad edges, z 0–24.8, r 41.98–45, which includes the inner wall/floor corner and the base). Translating the cutter by 1e-3 or 1e-2 does **not** change the count, so this is structural, not an accidental coincidence. Root cause **not yet identified**. | Staged counts: cutter alone, `M−C`, `M∩C` | `kintsugi.py:600-658` (`build_ribbon_cutter`), `kintsugi.py:542-546` (single-hit wall fallback `t = 1.0`) |
| F1c | CRITICAL | **Debris swap** adds new kissing edges in every staged case, including seeds 1 and 2 ribbon, which were clean before the swap. It unions crumbs into the other material even when they touch it only along an edge or at a point. | Pre-swap vs post-swap bad-edge counts | `kintsugi.py:664-680` (`swap_debris`) |
| F2 | CRITICAL | Unbounded Voronoi ridges are extended as **full lines through the finite vertex** (`finite ± direction*span`) instead of **rays pointing away from the seeds**. The ridges cross each other, which Voronoi edges never do; one crack spans most of the circumference. | Crack-graph render `graph_noise_off.png` | `kintsugi.py:357-376` (`_ridge_segment`) |
| F3 | CRITICAL | A valid tea bowl is rejected as "not a vessel" in 12/144 runs, all at R ∈ {0, 0.05}. At S≈1 the band covers the full height. The ±0.1H jitter plus up to ≈12 mm of noise in z push points above the rim or below the base, and those ray misses count against the 5% envelope. | Sweep | `kintsugi.py:466-486`, `kintsugi.py:560-566` |
| F4 | WARNING | Band-edge jitter detaches junctions. (a) Line 446 swaps `at_bottom`/`at_top` when endpoints are put in canonical order; these flags mean "*some* endpoint is on that edge", so they must not be swapped. (b) The jitter then moves `q0` or `q1` at random rather than *the endpoint lying on the band edge*. With noise off, 100/286 interior crack ends dangle; without the jitter, 4/270. | Junction-connectivity metric | `kintsugi.py:440-475` |
| F5 | WARNING | `_export_trimesh` deletes faces with area ≤ 1e-12 from a closed mesh. That opens holes in principle, and it fired on up to 11 faces per export. It masks F1 instead of fixing it, and the 3MF writer uses it too. | Spy on `_export_trimesh` | `kintsugi.py:683-700` |
| F6 | WARNING | The spec's "Custom file upload" scenario requires verifying watertight status on upload. The GUI only parses the file in the browser and shows "Watertight: checked on fracture". | Code read | `static/viewer.js:285-320`, `web_app.py` |
| F7 | WARNING | `output/web/<job_id>/` directories are never cleaned up after successful jobs, and uploads have no size cap. On an installation running unattended, disk use grows without bound. | `ls output/web` (14 dirs) | `web_app.py:76-148` |
| F8 | WARNING | When a projection ray has only one hit (the origin is inside the solid base), `t = 1.0` is hard-coded. The spec doesn't define this case; it produces 2 mm partial cuts into the base. | Code read | `kintsugi.py:542-546` |
| F9 | WARNING | `verification.md` marks every geometry requirement "Met" on single-seed evidence. `tests.md` doesn't describe ribbon thickness. | Doc read | `verification.md`, `tests.md` |
| F10 | SUGGESTION (in scope, trivial) | `_radial_probe` runs twice per job (validation and `compute_parameters`). | Code read | `kintsugi.py:119-127`, `kintsugi.py:277-283` |

**Out of scope for this handoff.** Record each under `research.md → Raised but not acted on` with a reason:
- Re-anchoring the noise octaves to seed spacing. This changes the artistic look; it needs sign-off from the artist.
- Vendoring three.js locally. It needs a network fetch and is a new asset.
- Slicer GUI import (task 6.3). It's manual, and the slicers aren't installed.

## 2. Target Context Map

| File Path | Target Lines | Modification Summary |
|---|---|---|
| `kintsugi.py` | `L357-L376` | **F2:** `_ridge_segment`. For an unbounded ridge, return a segment from the finite vertex along a single ray. The direction is perpendicular to the seed pair, with its sign chosen so it points away from the midpoint of `vor.points` (same rule as `scipy.spatial.voronoi_plot_2d`). |
| `kintsugi.py` | `L440-L475` | **F4:** Stop swapping `at_bottom`/`at_top` on canonicalisation. Per endpoint, compute `on_edge = abs(q[1]-z_min)<1e-9 or abs(q[1]-z_max)<1e-9` and jitter **only** endpoints that are on the edge. Never move an interior endpoint (a Voronoi vertex). |
| `kintsugi.py` | `L477-L489` | **F3:** After perturbation, clamp `z` into `[z_lo + m, z_hi − m]`, with `z_lo`/`z_hi` the mesh Z bounds and margin `m = 0.5*W`. Pass the mesh Z bounds through `params` (add `z_mesh_lo`, `z_mesh_hi` in `compute_parameters`). |
| `kintsugi.py` | `L496-L568` | **F3:** In `project_crack_paths`, misses still split the path, but only misses at `z ∈ [z_min, z_max]` (the band) count towards the 5% envelope fraction. Return both fractions. **F8:** When there's exactly one hit, set `t` to the distance from the ray origin to that hit, capped at `0.5 * rbar`. Record that a single hit occurred in a counter returned in `params`. |
| `kintsugi.py` | `L578-L597` | **F1a:** Before `translate`, rotate each sphere by Euler angles drawn from a dedicated `np.random.default_rng([seed, 0xC07])` stream (a sub-seed, so the crack graph's random stream is unchanged). The signature becomes `build_vein_cutter(projected_paths, W, rng)`. |
| `kintsugi.py` | `L600-L658` | **F1b:** Investigate first (task 7.4), then fix. Expected candidates, in order: (i) consecutive slabs, or slabs from different paths at a shared junction, that are identical or coplanar; (ii) slab faces coplanar with the bowl's planar floor and base at z=0 and z=3 (the bad edges include z=0.0 and r=41.98, the inner corner); (iii) the F8 fallback. Same treatment as vein: a sub-seeded tiny rotation about the slab's own normal axis, plus a length jitter of ≤ 1e-3·W. Prove the fix with staged bad-edge counts. |
| `kintsugi.py` | `L664-L680` | **F1c:** `swap_debris` moves a crumb only when the union reduces the target's component count by one, i.e. the crumb shares a face region with the target. Check it with `(target + crumb).decompose()` and compare component counts. Otherwise move it into the material it *does* share a face with. If neither applies (an isolated crumb), leave it where it is and add it to a `debris_unmoved` count. Volume must still be conserved within 1e-6. |
| `kintsugi.py` | `L683-L700` | **F5:** Remove the face deletion. `_export_trimesh` becomes a pure conversion. If F1 is fixed properly, it's no longer needed. |
| `kintsugi.py` | `L703-L726` and `L916-L935` | **F1 guard:** Add `_roundtrip_bad_edges(manifold) -> int`. It serialises to binary STL in memory, reloads with `trimesh.load(..., file_type="stl", process=True)`, and counts edges used by ≠2 faces. In `generate_kintsugi_mesh`, after the swap and **before writing**, assert 0 for both outputs. On failure, retry the cutter build up to 3 times with sub-seed `[seed, 0xC07, attempt]`, which keeps the input untouched and both booleans on the same cutter, so complementarity holds. If it still fails, raise `RuntimeError` and write no files. Record `cutter_attempts` in the result dict. |
| `kintsugi.py` | `L116-L127`, `L270-L283` | **F10:** `validate_and_load_mesh` returns probe results (or caches them on a small dataclass), and `compute_parameters` reuses them instead of probing again. |
| `web_app.py` | `[NEW]` route, near `L76` | **F6:** `POST /api/validate` (multipart file). It runs `kintsugi.validate_and_load_mesh(path, S=0.0)` in a temporary directory and returns `{"valid": bool, "detail": str, "extents": [...], "volume": float}`. The temp dir is always removed. |
| `web_app.py` | `L76-L148` | **F7:** Reject uploads over 50 MB with 413 (stream with a byte counter). Add a retention sweep that runs before each new job: delete `OUTPUT_DIR/*` job directories older than `KINTSUGI_JOB_TTL_S` seconds (env var, default 3600) and keep at most `KINTSUGI_MAX_JOBS` (default 50, oldest removed first). |
| `static/viewer.js` | `L285-L320` | **F6:** After the browser-side parse, `POST /api/validate` and set the mesh status to `Watertight ✓` or `Not a valid closed solid: <detail>`. Disable the fracture button while the upload is invalid. Use the existing status-bar and well styles only; no new visual tokens. |
| `tests/test_kintsugi.py` | `[NEW]` tests | `test_seed_sweep_watertight`, `test_high_severity_bowl_not_rejected`, `test_voronoi_ridges_do_not_cross`, `test_junctions_connected`, `test_vein_cutter_no_kissing`, `test_debris_swap_no_new_bad_edges`, `test_roundtrip_guard_raises_and_writes_nothing` (see §5). |
| `tests/test_web_api.py` | `[NEW]` tests | `test_api_validate_ok`, `test_api_validate_open_mesh`, `test_api_upload_too_large`, `test_job_retention`. |
| `tools/sweep.py` | `[NEW]` | Copy from `/tmp/claude-1001/-home-node-global-sandbox-projects-wax-robot/9bbab440-a7fe-4db6-b307-75b743311db4/scratchpad/sweep.py`. Add argparse (`--presets`, `--ratios`, `--modes`, `--seeds`) and a JSON summary written to `output/verification/sweep.json`. |
| `tools/render.py` | `[NEW]` | Copy from `/tmp/claude-1001/-home-node-global-sandbox-projects-wax-robot/9bbab440-a7fe-4db6-b307-75b743311db4/scratchpad/render.py` (offline z-buffer to PNG; red squares mark non-manifold edges; title bar is green or red for watertight). The default output dir is `output/verification/renders/`. |
| `openspec/changes/kintsugi-mesh-fracture/specs/mesh-fracture-engine/spec.md` | append scenarios | See §3, "Spec edits". |
| `openspec/changes/kintsugi-mesh-fracture/specs/multi-material-export/spec.md` | append scenarios | See §3, "Spec edits". |
| `openspec/changes/kintsugi-mesh-fracture/specs/retro-web-gui/spec.md` | edit "Custom file upload" | Name `/api/validate` as the mechanism. Add retention and size-limit scenarios. |
| `openspec/changes/kintsugi-mesh-fracture/{architecture,tests,tasks,research,verification}.md` | various | Documentation obligations in §7. |

## 3. Technical & Architectural Boundaries

**In-scope decisions (do not relitigate):**
- A single validated input `Manifold`. Both booleans use **the same cutter**. **Never perturb the input mesh.** Perturbing or rotating the *cutter* is allowed, because complementarity is preserved.
- All randomness is seeded. Each new random stream (cutter rotation, retries) uses its own sub-seed `np.random.default_rng([seed, TAG, ...])`, so the crack graph stays the same and only the cutter's tessellation changes. Determinism must stay byte-identical across processes.
- Debris is never deleted; total volume is conserved within 1e-6.
- `Manifold.ray_cast` only; no `rtree` at runtime.
- The wealthy-state behaviour (no gold STL, stale file removed) is unchanged.

**Spec edits.** Add these as new `#### Scenario:` blocks under the existing requirements, in WHEN/THEN form. Keep `openspec validate --strict` green after every edit.
- *Parameter-space crack generation*:
  - "Unbounded ridges are rays": no two ridge segments intersect except at shared endpoints.
  - "Perturbed points stay on the mesh": every perturbed z lies within `[z_lo + W/2, z_hi − W/2]`.
  - "Junction ends are never jittered": only endpoints on the band edge move.
  - "Only in-band misses count towards the envelope".
  - "Single-hit wall thickness": define the F8 rule.
- *Watertight cutter construction*:
  - "Cutter primitives are de-aligned": a seeded per-primitive rotation, so the cutter has 0 non-manifold edges after a position-merging round trip.
- *Paired manifold STL export*:
  - "Round-trip guard": 0 edges used by ≠2 faces after binary-STL reload; up to 3 cutter retries; otherwise `RuntimeError` and no files.
  - "Seed robustness": the sweep test passes.
- *Sub-nozzle debris reassignment*:
  - "Crumbs merge only across a shared face"; otherwise they stay and are counted.
- *Model preset selection and custom upload* (web GUI): `/api/validate` on upload, 413 above 50 MB, job retention by TTL and count.

**Hard exclusions / no-go:**
- Do NOT modify `.env`, `.env.*`, or credential files.
- Do NOT add dependencies. Everything needed (`numpy`, `scipy`, `trimesh`, `manifold3d`, `fastapi`, `rtree` for tests) is already present. No matplotlib or PIL; `tools/render.py` writes PNGs with `zlib`.
- Do NOT loosen thresholds to make tests pass: the 5% miss limit, 1 mm³ debris, the 1e-6 volume check, 0.7 mm thickness.
- Do NOT edit any test to change its seed away from a failing case.
- Do NOT touch the noise-field design (`_make_noise` amplitudes and frequencies) or `DESIGN.md` tokens.
- Do NOT modify code outside the Target Context Map without a task covering it.
- Do NOT archive the change or run `openspec specs apply` unless §7 step 6 is fully green.

## 4. Visual & UI Design Specifications

UI impact is limited to the upload status text and the fracture button's disabled state (F6). Reuse the existing tokens from `DESIGN.md` and `design.md`:
- **Theme:** Windows XP Luna Retro Minimalist.
- **Tokens:** primary `#0058ee`, surface `#ece9d8`, text `#222222` / muted `#555555`, success `#3e8e18`, error `#e81123`.
- **States:** valid → status text in success colour with `Watertight ✓`; invalid → error colour with the server's `detail`; fracture button uses the existing `disabled` styling. No new components, no new CSS variables.

## 5. Test Scaffolding & Verification Commands

- **Primary test runner:** `.venv/bin/python -m unittest discover -s tests -v`
- **Sweep (evidence, not a unit test):** `.venv/bin/python tools/sweep.py --presets tea_bowl vase --ratios 0 0.05 0.2 0.5 0.9 0.99 --modes ribbon vein --seeds 0 1 2 3 4 5`
- **Renders:** `.venv/bin/python tools/render.py . output/verification/renders`
- **Spec validation:** `openspec validate kintsugi-mesh-fracture --strict --json`

**TDD requirement.** Task 7.1 MUST add the failing tests below and run them, and you must paste the failing output into `verification.md §8` *before* touching `kintsugi.py`. Expected initial state: every new engine test fails except the guard test, which can't run until the guard exists. That one fails with `AttributeError`.

| New test | Asserts | Fixture |
|---|---|---|
| `test_seed_sweep_watertight` | For tea_bowl × R∈{0, 0.2} × both modes × seeds {0,1,2,3}: no exception, and both STLs reload with `is_watertight and is_volume` and 0 edges used by ≠2 faces. Keep it under ~120 s; the full sweep lives in `tools/`. | `presets/` bowl or `tests/fixtures.py` bowl |
| `test_high_severity_bowl_not_rejected` | R=0, seeds 0–5, both modes: no `ValueError`. | bowl |
| `test_voronoi_ridges_do_not_cross` | With `_make_noise` patched to zero, for seeds 0–9 no two segments of `generate_crack_paths` intersect except at shared endpoints. Use exact 2-D segment intersection in unrolled u, handling the period. | params from bowl |
| `test_junctions_connected` | Noise patched to zero, seeds 0–19: every endpoint farther than 1e-6 from both band edges has another endpoint within 1e-6. The current code fails 100/286. | params from bowl |
| `test_vein_cutter_no_kissing` | For seeds 0, 1, 5: the vein cutter has 0 bad edges after `_roundtrip_bad_edges`, and so do `M−C` and `M∩C`. | bowl |
| `test_debris_swap_no_new_bad_edges` | Seeds 0–2, ribbon, R=0.2: bad edges after the swap ≤ bad edges before (and both 0 after the full fix). | bowl |
| `test_roundtrip_guard_raises_and_writes_nothing` | Monkeypatch the cutter builder to return two cubes that share an edge. `generate_kintsugi_mesh` raises `RuntimeError`, and the output dir has no files. | bowl |
| `test_api_validate_ok` / `test_api_validate_open_mesh` | 200 with `valid: true`; 200 with `valid: false` and a detail mentioning "closed solid". | fixtures |
| `test_api_upload_too_large` | A 51 MB body returns 413. | synthetic bytes |
| `test_job_retention` | With `KINTSUGI_MAX_JOBS=2`, after 3 jobs only 2 job directories remain. | bowl |

## 6. Implementation Task Checklist

Append this to `tasks.md` as `## 7. Verification Remediation`, and tick boxes only when the step genuinely ran and passed:

- [ ] 7.0 Record the findings: add `verification.md §8` with the findings table, downgrade the affected matrix rows, and update `research.md` (superseded claim, verified root-cause facts, out-of-scope items)
- [ ] 7.1 Scaffold all failing tests in §5; paste the failing run into `verification.md §8`
- [ ] 7.2 Copy `sweep.py` and `render.py` into `tools/`; run the baseline sweep and renders; record the baseline counts (expect about 53/144 clean, 12 false rejections) in `verification.md §8`
- [ ] 7.3 Fix F2 (Voronoi rays) and F4 (junction jitter); `test_voronoi_ridges_do_not_cross` and `test_junctions_connected` pass
- [ ] 7.4 Fix F3 (z clamp, in-band miss accounting) and F8 (single-hit wall rule); `test_high_severity_bowl_not_rejected` passes
- [ ] 7.5 Fix F1a (seeded sphere rotation); `test_vein_cutter_no_kissing` passes
- [ ] 7.6 Investigate F1b with staged bad-edge counts (cutter alone, `M−C`, `M∩C`) and bad-edge locations. Write the root cause, with numbers, into `research.md → Verified facts` *before* fixing; then fix it
- [ ] 7.7 Fix F1c (face-sharing debris merge); `test_debris_swap_no_new_bad_edges` passes; volume check still within 1e-6
- [ ] 7.8 Remove the F5 face deletion; add the F1 round-trip guard with cutter-only retries; `test_roundtrip_guard_raises_and_writes_nothing` and `test_seed_sweep_watertight` pass
- [ ] 7.9 F10: drop the duplicate radial probe; `test_determinism` still byte-identical (rerun the cross-process MD5 check)
- [ ] 7.10 F6 and F7: `/api/validate`, upload size cap, job retention, viewer upload status; web API tests pass
- [ ] 7.11 Update the specs (§3 spec edits), `architecture.md` (§7 obligations) and `tests.md`; `openspec validate --strict` is green
- [ ] 7.12 Run the full suite, the full 144-run sweep and the renders; record the verbatim results and before/after comparison in `verification.md §8`; restore matrix rows to `Met` only where the evidence supports it

## 7. Documentation Obligations (do these while you work, not at the end)

1. **After each fix task (7.3–7.10)**, append a dated entry to `verification.md §8 → Remediation log`:
   - the finding ID;
   - root cause in one or two sentences;
   - the change made, with `file:line`;
   - the test(s) that now pass, with verbatim output;
   - the before/after metric (bad-edge count, dangling ends, rejections).
2. **`architecture.md`:**
   - Add **Decision 7: Cutter de-alignment and round-trip guard**: why the cutter, never the input, is perturbed; the sub-seed scheme; the retry limit; why STL position-merging is the reference check.
   - Update Decision 4 for the face-sharing merge rule.
   - Update the mermaid diagram with a "Round-trip guard (retry cutter ≤3)" node between the debris swap and export.
3. **`tests.md`:**
   - Document every new test with the asserts from §5.
   - Add ribbon-mode thickness to the printable-thickness entry. If you decide not to test it, say why.
   - Add `tools/sweep.py` and `tools/render.py` under Manual Verification, with their exact commands.
4. **`research.md`:**
   - Verified facts: Manifold symbolic-perturbation output can kiss; vein sphere alignment is the cause; the F1b root cause once found.
   - Superseded claims: single-seed sufficiency; and "debris swap is safe by union".
   - Raised but not acted on: the noise-octave scale and three.js vendoring, each with its reason.
5. **`verification.md` matrix:** every row cites test names and, for geometry rows, the sweep result. Single-seed evidence is no longer enough to mark a geometry row "Met".
6. **Finish:**
   - Every 7.x box is ticked.
   - The full sweep shows **144/144 runs either clean or rejected only for a documented, legitimate envelope reason**. Target: 0 non-watertight and 0 false rejections.
   - The test suite is green and `openspec validate --strict` is green.
   - Then run `openspec-verify-change`. Only if it reports no CRITICAL issues (6.3, the manual slicer check, may remain open and be noted), stop and report back. **Do not archive.**

## 8. Post-Implementation & Verification Obligations

When `spec-coder-sub` finishes:
1. Verify that every checkbox in `tasks.md` §7 is `- [x]`, and that each one is backed by a log entry in `verification.md §8`.
2. Data preservation: confirm `presets/*.stl` are unchanged (MD5 before and after) and that `output/` sample artefacts are regenerated, not hand-edited.
3. Ensure `verification.md` contains: Executive Summary & Environment; the Requirement Adherence Audit Matrix mapping every spec scenario (old and new) to its verifying test; Resolved Assumptions & Empirical Proof; a Nomenclature & Code Symbol Audit (new symbols: `_roundtrip_bad_edges`, `cutter_attempts`, `debris_unmoved`, `/api/validate`, `KINTSUGI_JOB_TTL_S`, `KINTSUGI_MAX_JOBS`); and verbatim execution logs (tests, sweep JSON summary, render list).
4. Run verification with `openspec-verify-change`.
5. Do **not** run `openspec specs apply` or archive. Hand back to the user for review together with the renders in `output/verification/renders/`.
