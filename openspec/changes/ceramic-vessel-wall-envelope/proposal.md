## Why

The engine previously attempted to support sub-millimeter vase-mode vessels ($t < 1.0\text{ mm}$), which created a cascade of failure modes: groove depths faded toward zero, tangent cutter spheres triggered non-manifold kissing-edge defects, and applying a $0.25\text{ mm}$ cutoff omitted all vein cutter points on thin walls, resulting in 84-byte empty gold STL files and misleading UI labels. Furthermore, single-perimeter spiral vase mode cannot physically support multi-material inlays on FDM slicers.

Dropping the vase-mode constraint and restricting the supported input envelope to real ceramic vessels (two-hit wall thickness 5th percentile $p_5 \ge 1.6\text{ mm}$ along inward surface normals across the wall range) ensures that nominal ceramic backing is $\ge 0.5 \cdot t_i$ everywhere and $\ge 0.8\text{ mm}$ wherever $t_i \ge 1.6\text{ mm}$ under $d_i = \min(0.75W, 0.5t_i)$. This eliminates the thin-wall point-omission cause, restores bold, continuous gold veins, and cleans up the artifact and test suites.

Additionally, key morphology refinements (15–20% kink rate, Gaussian $\sigma \approx 18^\circ$ drift, and final-attempt near-miss snapping) were merged to `main` in PATCH-02 (`f77406d`); this change formally codifies them in the main specification and establishes regression tests.

## What Changes

- **BREAKING**: Enforce a strict ceramic vessel envelope in `validate_and_load_mesh`: input watertight meshes must have 5th-percentile two-hit wall thickness $p_5 \ge 1.6\text{ mm}$, measured along inward surface normals across the full wall range `[wall_z_min, wall_z_max]` (independent of $R$). Meshes below this threshold are cleanly rejected with a descriptive `ValueError` across all fracture modes (both `vein` and `ribbon`).
- Restore the classical, continuous vein depth formula $d_i = \min(0.75W, 0.5t_i)$. For any point where $t_i \ge 1.6\text{ mm}$, backing is guaranteed $\ge 0.8\text{ mm}$. Minimum depth for valid ceramic inputs is $\min(0.75 \times 0.8, 0.5 \times 1.6) = 0.6\text{ mm}$, avoiding tangency.
- Clamp rim crack projection to `wall_z_max - max(0.5, W/2)` to avoid the thin tapered lip of rounded rims where $0.5t$ could otherwise narrow.
- Remove cutter point omission logic (`d < 0.25 mm` dropping) and polyline splitting (`_vein_point_groups`), producing continuous, unbroken gold inlay solids along every crack path.
- Remove `thin_cylinder` from user-facing presets (`presets/thin_cylinder.stl`, `sample_models.PRESETS`, `/api/presets`); retain it strictly as an internal negative test fixture in `sample_models.py`.
- Clean up stale UI text in `viewer.js:410` (removing "wall thickness < 1.05 mm" fallback) and clean up `seams_omitted_reason` in `web_app.py`.
- Formally document and add regression test coverage for PATCH-02 growth morphology: final-attempt near-miss snapping directly to target segments at arrival angle $\ge 30^\circ$, 15–20% sharp kink probability, and Gaussian $\sigma \approx 18^\circ$ heading drift.
- Reconcile `multi-material-export` specification with defensive empty-gold handling: define the fallback contract when $R < 1.0$ but the gold solid boolean is empty (e.g. extreme ray misses), ensuring `gold_seams.stl` is not written and `3MF` packages only `CeramicBody`.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `mesh-fracture-engine`: Update `Supported input envelope` to mandate two-hit normal wall thickness $p_5 \ge 1.6\text{ mm}$ over `[wall_z_min, wall_z_max]`; update `Metric R validation and clamping` to specify continuous vein depth $d_i = \min(0.75W, 0.5t_i)$ and rim lip clamping; update `Parameter-space crack generation` to document final-attempt near-miss snapping and 15–20% kink rate while retaining all original projection scenarios.
- `multi-material-export`: Update `Paired manifold STL export` and `Unified multi-material 3MF export` to specify the empty-gold fallback contract when $R < 1.0$.
- `retro-web-gui`: Update `Model preset selection and custom upload` (removing `thin_cylinder` from presets and surfacing $p_5$ validation rejection) and `Real-time parameter controls and fracture execution` (displaying "Pristine / Wealthy (0 cracks)" strictly when $R \ge 1.0$).

## Impact

- **Core Engine (`kintsugi.py`)**: `validate_and_load_mesh` preflight normal-based wall thickness check; `_build_vein_cutter` continuous swept hulls without point omission; rim clamp adjustment.
- **Model Library & Presets (`sample_models.py`, `presets/`)**: Delete `presets/thin_cylinder.stl`; remove `thin_cylinder` from `PRESETS`; retain `create_thin_cylinder_fixture` as a negative test helper.
- **Web API & GUI (`web_app.py`, `static/viewer.js`)**: Clean error propagation for sub-1.6 mm meshes; remove stale "wall thickness < 1.05 mm" string.
- **Test & Audit Tools (`test_report.py`, `spike_contact_sheet.py`, `sweep_out_of_sample.py`)**: Update sweeps and contact sheets to replace `thin_cylinder` with supported ceramic presets.
- **Dependencies**: No new dependencies (maintains strict zero-new-dependencies policy with `trimesh`, `manifold3d`, `scipy`, `numpy`).
