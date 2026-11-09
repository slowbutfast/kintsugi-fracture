## Automated Tests

- `./.venv/bin/python -m unittest tests.test_crack_hybrid -v`:
  - **Pre-Change Baseline SHA-256 Regression for `growth` and `shard`**: Verifies that `generate_crack_paths` with `generator="growth"` and `generator="shard"` matches the pre-change SHA-256 polyline digests byte-for-byte across `tea_bowl` and `vase` at $R \in \{0.2, 0.3, 0.35, 0.65, 0.75, 0.8\}$ (covering tier boundaries) and seeds `42, 43, 44`.
  - **Determinism**: Verifies that calling `generate_crack_paths(..., generator="hybrid")` and `generate_kintsugi_mesh(..., generator="hybrid", mode="vein")` twice with identical `(input_path, R, seed, hybrid_options)` returns byte-identical polylines, STL outputs, and `parameters["hybrid"]` across seeds outside the reserved hold-out ranges (`300–399` and `>= 600`).
  - **Wall Surface Partition / Raster Fragment Guarantee (`num_fragments >= 2`)**: Verifies across seeds `42..61` at $R \in \{0.2, 0.5, 0.75\}$ ($S \in \{0.25, 0.5, 0.8\}$) on `tea_bowl` and `vase` that `generate_hybrid_crack_paths` always produces `num_through_fragments >= 2` and `num_fragments >= 2` via the `0.25 mm` periodic `(u, z)` raster connected-component check, and returns `[]` with `num_fragments == 1` when $R = 0.85$ ($S = 0.15 < 0.2$) and knobs are `auto`.
  - **Combined Graph Audit Invariants**: Verifies that for all tested `(model, R, seed)` combinations, `analyze_growth_paths(paths, params)` reports `crossings == 0`, `clearance_violations == 0`, `min_clearance >= W + 0.8 - 1e-6`, and `min_junction_angle_deg >= 30.0 - 1e-6` without silent path pruning.
  - **Every Hybrid Knob Alters Output Paths Under Supported Shapes**: Verifies at fixed `(model, R=0.45, seed=42)` that varying each of the 6 knobs individually (`through_count` `1` vs `3`, `through_shape` `"wedge"` vs `"loop"`, `tilt_deg` `10.0` vs `28.0` under both `"wedge"` and `"loop"`, `hairline_count` `0` vs `6`, `hairline_reach` `0.25` vs `0.95`, and `roughness` `0.5` vs `1.8`) produces distinct crack polylines and echoes the resolved values in `parameters["hybrid"]`.
  - **Stage-2 Seam-Anchored Hairline Survival & Rim Exclusions**: Verifies that seam-anchored hairlines enqueued with `exempt_path_id` and `exempt_origin` survive their first step without self-colliding (`hairline_seam_count > 0` on `tea_bowl` and `vase`), and that `_poisson_rim_seeds` respects `excluded_u` in both rejection sampling and the largest-gap fallback.
  - **Fail-Fast Validation on Non-Hybrid Generators & Out-of-Range Knobs**: Verifies that passing any hybrid knob (`through_count`, `through_shape`, `tilt_deg`, `hairline_count`, `hairline_reach`, `roughness`) when `generator != "hybrid"`, passing `mode="ribbon"` with `generator="hybrid"`, or passing out-of-range knob values raises `ValueError`.
  - **Solid Body Rejection (`has_wall=False`)**: Verifies that `validate_and_load_mesh` raises `ValueError` on a watertight solid cylinder with no interior cavity (`has_wall=False` in `_probe_wall_range`).
- `./.venv/bin/python -m unittest tests.test_web_api -v`:
  - Verifies that `POST /api/fracture` with `generator="hybrid"` and `mode="vein"` returns `HTTP 200` with `num_fragments >= 2` and `parameters.hybrid` populated.
  - Verifies that `POST /api/fracture` with `generator="hybrid"` and explicit knob overrides echoes the overridden values in `parameters.hybrid`.
  - Verifies that `POST /api/fracture` with `generator="growth"` or `"shard"` plus any hybrid form field returns `HTTP 400 Bad Request`.
  - Verifies that `POST /api/fracture` with `generator="hybrid"` and `mode="ribbon"` returns `HTTP 400 Bad Request`.
  - Verifies that `POST /api/validate` on a solid non-hollow mesh (`has_wall=False`) returns `HTTP 200` with `valid: false` and an interior-cavity error detail.

## Manual Verification

- **Hybrid Generator Selection & UI Panel**:
  - **WHEN** the user opens `http://localhost:8000` and selects `Hybrid — macro shards + interior hairlines` in `#generator-select` (or `Mode -> Hybrid` in the menu bar)
  - **THEN** the `#hybrid-settings` fieldset becomes visible, `Vein Inlay` is selected, `Ribbon (Through-Wall)` is disabled, and `#generator-note` updates to `"Macro shard fractures + interior hairlines (Vein Inlay surface partition)."`
- **Fracture Execution & Auto Resolved Telemetry**:
  - **WHEN** the user leaves all 6 hybrid controls on `Auto`, sets `R = 0.35`, and clicks `⚡ FRACTURE MESH`
  - **THEN** the 3D viewport renders a vessel with 2–3 long rim-to-rim / T-junction macro gold seams plus shorter interior branching gold hairlines, and `#hybrid-resolved-note` displays the resolved values and surface fragment count (`num_fragments >= 2`).
- **Contact Sheet Visual Comparison**:
  - **WHEN** the developer runs `./.venv/bin/python tools/spike_contact_sheet.py --generator hybrid`
  - **THEN** a contact sheet PNG is generated showing deterministic hybrid fractures across the severity sweep for side-by-side comparison with `growth` and `shard`.
