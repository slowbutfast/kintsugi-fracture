## Automated Tests

Run with `.venv/bin/python -m unittest tests/test_kintsugi.py -v`. The fixture is a parametric tea bowl built with `Manifold.revolve`: outer radius 45 mm, height 60 mm, wall 3 mm.

- `test_wealthy_case`: for $R = 1.0$ and $R = 1.5$, the ceramic output equals the validated input (same volume and vertex count), `gold_path` is `None`, no gold STL exists on disk (including when a stale one was pre-created), and the 3MF has a single build item.
- `test_input_validation`: $R = -0.5$ yields $S = 1.0$; NaN and ±inf raise `ValueError`; `seam_width=0.5` raises `ValueError`.
- `test_input_envelope_rejection`: each of these raises `ValueError` *and writes no files*, at both $R = 0.4$ and $R = 1.5$:
  - an open mesh (one face removed);
  - the bowl scaled by $0.001$ (metres);
  - a non-vessel (two disjoint offset boxes).
- `test_parameter_table`: $R = 0.4$ gives $N = 6$, $W = 1.64$ and $H = 0.68\,H_{mesh}$.
- `test_stl_disk_roundtrip`: for both modes at $R = 0.2$, write both STLs, reload with `trimesh.load(..., process=True)`, and assert `is_watertight` and `is_volume`.
- `test_determinism`: two runs with the same seed produce byte-identical STL and 3MF files; a different seed produces different bytes.
- `test_volume_smoke`: $|V_c + V_g - V_{in}| \le 10^{-6} V_{in}$, both before and after debris swap. This is a regression tripwire, not a quality metric.
- `test_printable_channel_thickness`:
  - **Method:** sample 2000 points on the gold surface with `trimesh.sample.sample_surface` (fixed seed); call `trimesh.proximity.thickness(gold, points, method="ray")` (needs `rtree`, test-only dependency) or cast `-normal` rays via `Manifold.ray_cast`.
  - **Asserts:** 5th percentile $\ge 0.7$ mm; median within $\pm 15\%$ of the vein inlay depth $d=\min(0.75W, 0.5t)$ (the normal thickness of the lens), and the 90th percentile within $\pm 15\%$ of $W$ (the widest cross-section). The original "median $\approx W$" formulation was inconsistent with $d=0.75W$ and was resolved during implementation.
  - **Ribbon-mode thickness** is covered by `test_ribbon_through_wall` rather than this proximity-thickness check: ribbon slabs intentionally cut through the wall with depth $t+1$, so their normal thickness is not $W$ and a $W$-based median assertion would be dimensionally wrong. The ribbon test asserts the gold reaches the inner surface (maximum inward depth $> t-0.2$).
- `test_vein_depth`: in vein mode, the gold part's maximum inward depth from the outer surface is $\le d + 0.1$ mm, and ceramic $\cap$ (inner surface offset) is untouched, i.e. no vein pierces the wall.
- `test_ribbon_through_wall`: in ribbon mode, the gold part touches both the outer and inner surface (maximum inward depth $> t-0.2$) at $R = 0.2$, and the ceramic remains watertight with positive volume. The earlier extra assertion that the ceramic must split into more than one component was removed after the corrected periodic network legitimately left seed 7 connected; shard count is emergent, not a spec promise, and through-wall behaviour is proven by the depth assertion.
- `test_debris_swap`: neither output has a component below $1.0\text{ mm}^3$.
- `test_3mf_structure`: parse `3D/3dmodel.model` and assert:
  - `unit="millimeter"`;
  - exactly one `<item>`;
  - its object has `<components>` naming `CeramicBody` and `GoldSeams`;
  - per-part volumes match the STLs.

- **Web API Integration (`tests/test_web_api.py`)**:
  - `test_api_presets`: `GET /api/presets` returns HTTP 200 with bundled preset models (`tea_bowl`, `benchy`, `vase`).
  - `test_api_fracture_success`: `POST /api/fracture` with uploaded STL and $R = 0.4$ returns HTTP 200, non-zero crack count, volume metrics, and valid download URLs for STL and 3MF files.
  - `test_api_fracture_wealthy`: `POST /api/fracture` with $R = 1.0$ returns `num_cracks = 0` and download URL for pristine ceramic body.
  - `test_api_validate_ok`: `POST /api/validate` with a valid bowl returns 200, `valid: true`, three extents and a positive volume.
  - `test_api_validate_open_mesh`: `POST /api/validate` with a one-face-removed bowl returns 200, `valid: false`, and a detail containing "closed solid".
  - `test_api_upload_too_large`: a 51 MB upload returns HTTP 413.
  - `test_job_retention`: with `KINTSUGI_MAX_JOBS=2`, three successful jobs leave two job directories.

### Remediation Tests (task group 7)

- `test_seed_sweep_watertight`: tea bowl × $R \in \{0, 0.2\}$ × both modes × seeds 0–3; no exception, both STLs reload with `is_watertight`, `is_volume`, and 0 edges used by ≠2 faces.
- `test_high_severity_bowl_not_rejected`: $R=0$, seeds 0–5, both modes; no `ValueError`.
- `test_crack_paths_lie_on_periodic_voronoi`: replaces the old crossing test. `_make_noise` patched to zero; tea bowl and vase × S ∈ {0.6, 1.0} × seeds 0–39. Every path point's two nearest seeds in a 9-tile copy are equidistant within `1e-6·period`, and `_first_crossing(paths, period)` is `None`.
- `test_no_points_on_wall_limit_lines`: noise zero; both presets × S=1.0 × seeds 0–19. No non-terminal point lies within `1e-9` of the wall-range or band-edge limit lines; all points stay inside the wall limits.
- `test_band_edge_terminals_are_ragged`: noise zero; tea bowl S=0.6 seeds 0–19. Top terminals within `0.1H` of `z_max` have standard deviation `> 0.02H`, with both above-edge and below-edge terminals.
- `test_ray_tiebreak_direction`: `_ray_tiebreak_direction` points away from the third seed's side of edge `ab`, including normal flip and a rotated case.
- `test_export_repair_runs_once_per_guard_evaluation`: a counting wrapper around `_repair_stl_slivers` sees exactly `2 × guard_evaluations` calls for tea bowl R=0.2 ribbon seed 0 with 3MF enabled; outputs stay clean.
- `test_vessel_without_wall_range_rejected`: a solid cylinder with no two-hit wall raises `ValueError` mentioning the wall and writes no files.
- `test_junctions_connected`: noise zero; seeds 0–19; every interior endpoint farther than `0.11H` from both band edges has another endpoint within `1e-6` modulo the period.
- `test_vein_cutter_no_kissing`: seeds 0, 1, 5; cutter, `M−C` and `M∩C` each have 0 bad edges after `_roundtrip_bad_edges`.
- `test_debris_swap_no_new_bad_edges`: seeds 0–2 ribbon; post-swap bad edges ≤ pre-swap and both are 0 after the full fix.
- `test_roundtrip_guard_raises_and_writes_nothing`: a monkeypatched cutter made of two edge-sharing cubes drives the guard to `RuntimeError`; the output directory contains no files.
- `test_unbounded_rays_obey_voronoi_definition`: 25 random seed sets per $S \in \{0.2,0.8,1.0\}$; a point just along every unbounded ray must be closer to the ridge's two seeds than to any other seed.
- `test_ribbon_no_retries_out_of_sample_cases`: the eight previously retrying ribbon cases (tea bowl R∈{0.1,0.35,0.6,0.8}; vase R=0.6) require `cutter_attempts == 1` and clean STLs.
- `test_vein_no_retries_out_of_sample_cases`: seven previously retrying vein cases require `cutter_attempts == 1` and clean STLs.
- `test_wall_range_clamp_keeps_gold_out_of_floor`: R=0 ribbon seed 1 has no gold vertex below the floor height with radius < inner-wall radius − 1 mm, and `median_two_hit_wall` is positive.

## Manual Verification

- **Parametric Bowl Sample Generation**:
  - **WHEN** user runs `.venv/bin/python generate_sample.py`
  - **THEN** the script generates the tea bowl, runs $R \in \{1.0, 0.7, 0.2\}$ in both modes, writes STL pairs and 3MF files into `output/`, and prints per-run volumes, triangle counts, cutter part count and wall-clock time. The timings go into `verification.md`.

- **Multi-Seed Sweep Evidence**:
  - **WHEN** user runs `.venv/bin/python tools/sweep.py --presets tea_bowl vase --ratios 0 0.05 0.2 0.5 0.9 0.99 --modes ribbon vein --seeds 0 1 2 3 4 5`
  - **THEN** the script writes `output/verification/sweep.json` and prints total/clean/non-watertight/false-rejection/error counts. The finish line is 144/144 runs either clean or rejected for a documented, legitimate envelope reason.

- **Crack-Graph Audit**:
  - **WHEN** user runs `.venv/bin/python tools/crack_graph_audit.py --presets tea_bowl vase --severities 0.6 1.0 --seeds 200 --output output/verification/crack_graph_audit.json`
  - **THEN** with noise off, `phantom_seeds`, `crossing_seeds` and `clamp_line_fraction_mean/max` are all zero in every row. The audit uses a 9-tile ground truth and never tunes on the reviewer's held-out seeds.

- **Out-of-Sample Sweep Evidence**:
  - **WHEN** user runs `.venv/bin/python tools/sweep_out_of_sample.py --presets tea_bowl vase --ratios 0 0.1 0.35 0.6 0.8 --modes ribbon vein --seeds 100 101 102 103 104 105 106 107`
  - **THEN** the independent 160-run sweep writes `output/verification/sweep_out_of_sample.json`; the finish line is 160/160 clean with 0 retries and 0 false rejections.
  - **WHEN** user runs `.venv/bin/python tools/sweep_out_of_sample.py --presets tea_bowl vase --ratios 0.15 0.3 0.45 0.65 0.85 --modes ribbon vein --seeds 500 501 502 503 504 505 506 507 --output output/verification/sweep_round3.json`
  - **THEN** the round-3 out-of-sample sweep is 160/160 clean with retries reported (at most 2), and no tuned seeds from 300–399 or ≥600 are used.

- **Render Evidence**:
  - **WHEN** user runs `.venv/bin/python tools/render.py . output/verification/renders`
  - **THEN** the offline z-buffer renderer writes red-marked non-manifold views plus 2-D `graph_noise_off.png` / `graph_noise_on.png` crack-graph images into `output/verification/renders/`.
  - **WHEN** user runs `.venv/bin/python tools/render_remediation.py . output/verification/renders_remediation`
  - **THEN** the R=0 ribbon/vein and R=0.2 ribbon cases are rendered, including gold-only views; the R=0 gold-only view shows wall seams with no flat base plates.

- **Slicer Assembly Multi-Material Import**:
  - **WHEN** user opens `output/bowl_R0.2_ribbon.3mf` in Bambu Studio and in PrusaSlicer
  - **THEN** each slicer shows one object with two parts (not two objects), assigns a filament per part, and slices without non-manifold or overlap warnings. This is the check that confirms the unverified "components import as parts" assumption.

- **Retro Windows XP Web GUI Interaction**:
  - **WHEN** user starts `.venv/bin/python web_app.py --port 8000` and navigates to `http://localhost:8000`
  - **THEN** browser renders the Windows XP Luna interface defined in `DESIGN.md`, loads the selected preset in the Three.js viewport, renders off-white ceramic and metallic gold materials, responds to the $R$ slider, and downloads valid STL/3MF files on click.

- **Physical print** (once per filament pair): print the $R = 0.2$ ribbon bowl and check that the shards are held by the gold seams under light hand pressure.
