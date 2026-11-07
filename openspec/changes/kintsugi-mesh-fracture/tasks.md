## 1. Test Scaffolding (TDD)

- [x] 1.1 Build the parametric bowl fixture (`Manifold.revolve`) and scaffold failing tests for R validation, the parameter table, and the wealthy state (no gold STL, stale-file removal)
- [x] 1.2 Scaffold failing tests for input-envelope rejection (open mesh, metre units, non-vessel) at both wealthy and non-wealthy R
- [x] 1.3 Scaffold failing tests for STL disk round-trip, volume smoke check, determinism (byte-identical files), and both modes
- [x] 1.4 Scaffold failing tests for printable thickness (sampled ray thickness), vein depth, ribbon through-wall, debris swap, and 3MF component structure
- [x] 1.5 Scaffold failing API integration tests in `tests/test_web_api.py` for presets, fracture execution, and wealthy handling

## 2. Dependencies & Core Mesh Foundation

- [x] 2.1 Create `requirements.txt` with `numpy`, `scipy`, `trimesh`, `manifold3d>=3.5`, `fastapi`, `uvicorn`, `python-multipart` and `requirements-dev.txt` with `rtree` (thickness test only)
- [x] 2.2 Implement `trimesh_to_manifold` / `manifold_to_trimesh` via `Mesh64` / `to_mesh64`
- [x] 2.3 Implement `validate_and_load_mesh`: lossless clean-up, Manifold status and volume check, units/extents envelope check; runs before any branch on R
- [x] 2.4 Implement `compute_parameters(S, mesh)` → $N, W, H, Z_{trauma}$, plus radial probing for $\bar r$ and the ray-miss envelope check

## 3. Fracture Graph & Solid Cutter Pipeline

- [x] 3.1 Implement the θ-periodic dyadic sine field $\eta(u, z)$
- [x] 3.2 Implement the periodic Voronoi graph in $(u, z)$: tiling, central-ridge selection, band clipping with jittered terminations, junction merging
- [x] 3.3 Implement subdivision, perturbation, and `Manifold.ray_cast` projection (farthest hit, wall thickness $t$, miss splitting)
- [x] 3.4 Implement the vein cutter (inset spheres, consecutive hulls)
- [x] 3.5 Implement the ribbon cutter (surface frame, $W \times (t + 1)$ slabs, consecutive hulls, degenerate-frame handling)
- [x] 3.6 Implement dual CSG against the single validated Manifold and the bidirectional debris swap

## 4. Multi-Material Export & Sample Generator

- [x] 4.1 Implement `export_kintsugi_stl` (binary STL pair; wealthy: ceramic only, stale gold removed)
- [x] 4.2 Implement `export_kintsugi_3mf` with hand-written 3MF Core XML (one item → components)
- [x] 4.3 Implement the top-level `generate_kintsugi_mesh` (returns paths, volumes, triangle counts, timings) and the CLI entrypoint
- [x] 4.4 Implement `generate_sample.py` for $R \in \{1.0, 0.7, 0.2\}$ × both modes with timing output

## 5. Retro Windows XP Web GUI & API

- [x] 5.1 Implement FastAPI backend in `web_app.py` exposing `/api/presets`, `/api/fracture`, and static file mounting
- [x] 5.2 Bundle preset sample models in `presets/` (Japanese Tea Bowl, Benchy, Small Vase)
- [x] 5.3 Implement `static/index.html` with Windows XP Luna window chrome, menu bar, sidebar controls, and status bar
- [x] 5.4 Implement `static/xp.css` strictly conforming to design tokens in `DESIGN.md`
- [x] 5.5 Implement `static/viewer.js` with Three.js orbit viewport, PBR ceramic and metallic gold shaders, and asynchronous API calls

## 6. Verification & Empirical Audit

- [x] 6.1 Run the full test suite (`test_kintsugi.py` and `test_web_api.py`) and record results
- [x] 6.2 Run the sample generator; record timings and triangle counts in `verification.md`
- [ ] 6.3 Do the slicer import check (Bambu Studio and PrusaSlicer) and record whether the 3MF loads as one object with two parts
- [x] 6.4 Verify local web app interaction at `http://localhost:8000` (Luna styling, orbit navigation, preset switching, downloads)
- [x] 6.5 Populate `verification.md` with the Requirement Adherence Matrix, resolved assumptions, and verbatim logs

## 7. Verification Remediation

- [x] 7.0 Record the findings: add `verification.md §8` with the findings table, downgrade the affected matrix rows, and update `research.md` (superseded claim, verified root-cause facts, out-of-scope items)
- [x] 7.1 Scaffold all failing tests in §5; paste the failing run into `verification.md §8`
- [x] 7.2 Copy `sweep.py` and `render.py` into `tools/`; run the baseline sweep and renders; record the baseline counts (expect about 53/144 clean, 12 false rejections) in `verification.md §8`
- [x] 7.3 Fix F2 (Voronoi rays) and F4 (junction jitter); `test_voronoi_ridges_do_not_cross` and `test_junctions_connected` pass
- [x] 7.4 Fix F3 (z clamp, in-band miss accounting) and F8 (single-hit wall rule); `test_high_severity_bowl_not_rejected` passes
- [x] 7.5 Fix F1a (seeded sphere rotation); `test_vein_cutter_no_kissing` passes
- [x] 7.6 Investigate F1b with staged bad-edge counts (cutter alone, `M−C`, `M∩C`) and bad-edge locations. Write the root cause, with numbers, into `research.md → Verified facts` *before* fixing; then fix it
- [x] 7.7 Fix F1c (face-sharing debris merge); `test_debris_swap_no_new_bad_edges` passes; volume check still within 1e-6
- [x] 7.8 Remove the F5 face deletion; add the F1 round-trip guard with cutter-only retries; `test_roundtrip_guard_raises_and_writes_nothing` and `test_seed_sweep_watertight` pass
- [x] 7.9 F10: drop the duplicate radial probe; `test_determinism` still byte-identical (rerun the cross-process MD5 check)
- [x] 7.10 F6 and F7: `/api/validate`, upload size cap, job retention, viewer upload status; web API tests pass
- [x] 7.11 Update the specs (§3 spec edits), `architecture.md` (§7 obligations) and `tests.md`; `openspec validate --strict` is green
- [x] 7.12 Run the full suite, the full 144-run sweep and the renders; record the verbatim results and before/after comparison in `verification.md §8`; restore matrix rows to `Met` only where the evidence supports it

## 8. Second Verification Remediation

- [x] 8.0 Record round-2 findings in `verification.md §10`, `research.md` and the matrix; append the out-of-sample sweep tool
- [x] 8.1 Scaffold failing tests for Voronoi-definition ray orientation, zero ribbon retries on out-of-sample cases, and wall-range/base-slot prevention; paste the failing run into `verification.md §10`
- [x] 8.2 Fix F11: orient unbounded rays by the Voronoi distance definition (third-seed tie-break) and verify each ray against that definition
- [x] 8.3 Fix F12: repair tiny CSG sliver edges at export time (watertight/volume preserving) and require zero retries on the 160-run out-of-sample sweep
- [x] 8.4 Fix F13: clamp to the two-hit wall Z range and use median two-hit wall thickness for any residual single-hit ray; assert gold stays out of the floor
- [x] 8.5 Remove dead debris branches, document the upload-cap spool caveat, tighten the ribbon wall-region assertion, update specs/architecture/tests/research, run both sweeps and renders, restore matrix, validate, and hand back without archiving

## 9. Third Verification Remediation

- [x] 9.0 Record the findings (§0): `verification.md §11`, matrix downgrades, `research.md` facts and superseded claims
- [x] 9.1 Scaffold the §5 tests; paste the failing run into `verification.md §11`. Run `tools/crack_graph_audit.py` and both previous sweeps for the baseline, and record them verbatim
- [x] 9.2 Fix F14 (central seed required for every ridge). Re-run the audit and record the phantom and crossing counts. They will not reach zero until F15 is done, so record the change
- [x] 9.3 Fix F15b (jitter along the ridge by per-terminal clip limits); `test_band_edge_terminals_are_ragged` passes
- [x] 9.4 Fix F15a (wall-only limits, truncation instead of clamp, wall-range rejection); `test_no_points_on_wall_limit_lines`, `test_crack_paths_lie_on_periodic_voronoi`, `test_wall_range_clamp_keeps_gold_out_of_floor` and `test_high_severity_bowl_not_rejected` pass
- [x] 9.5 Fix F17 (`_ray_tiebreak_direction`); `test_ray_tiebreak_direction` and `test_unbounded_rays_obey_voronoi_definition` pass
- [x] 9.6 Fix F16 (single repair per guard evaluation, reused for STL, 3MF and counts); `test_export_repair_runs_once_per_guard_evaluation` passes; report the sweep's median and max run time before and after
- [x] 9.7 Update the specs (§3), `architecture.md`, `tests.md` and `research.md` (§7); `openspec validate --strict` is green
- [x] 9.8 Run the full suite, the audit (target all zeros), all three sweeps, the cross-process determinism MD5 check, the renders and `generate_sample.py`. Record everything verbatim in `verification.md §11`, then restore matrix rows to `Met` only where the evidence supports it

## 10. Open Items (from the round-3 independent verification, `verification.md §13`)

- [x] 10.1 Fix F18: bound the noise field's Lipschitz constant below 1 (target ≤ 0.7) so the displacement cannot fold; add a noise-on planarity test; `tools/noise_fold_audit.py` reports 0.0% fold area and 0 crossings; review renders for aesthetics. (Note: Small-radius vector-field Jacobian proof gap and aesthetic flattening under Voronoi are superseded by the follow-on `kintsugi-crack-growth` change).
- [x] 10.2 Decide and implement F19: let rim-bound cracks break through the rim (overshoot truncation plus clamped projection) without reintroducing kissing edges; re-run all sweeps on new held-out seeds. (Note: Flat rim-lip artifact refinement superseded by rim-seeded growth in `kintsugi-crack-growth`).
- [x] 10.3 F20: log the `web_app.py` `guard_evaluations` change and cover it with an API test assertion
- [x] 10.4 Decide whether to enforce a true request-size limit (ASGI middleware or proxy) or keep the documented caveat: Closed as documented architectural decision. The tool is designed as a local loopback utility (`127.0.0.1`); production network deployments will enforce upload size limits at the reverse-proxy layer (e.g. Cloudflare / Nginx).

## Patch 01: Remediate F18 noise folding, F19 rim break-through, and F20 API assertion

- [x] P01.1 Scaffold reproducing test for noise-on crossings and fold area
- [x] P01.2 Apply minimal targeted fix in `kintsugi.py` (`_make_noise` Lipschitz bound <= 0.7, rim overshoot)
- [x] P01.3 Add `guard_evaluations` assertion in `tests/test_web_api.py`
- [x] P01.4 Remove `KNOWN_OPEN = {"noise_fold": "F18"}` in `tools/test_report.py`
- [x] P01.5 Verify reproduction test passes and run full regression suite
- [x] P01.6 Update `verification.md` and mark PATCH-01 resolved in `patch.md`
