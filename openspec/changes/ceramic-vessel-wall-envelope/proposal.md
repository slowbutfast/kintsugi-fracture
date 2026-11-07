## Why

The engine previously attempted to support sub-millimeter vase-mode vessels ($t < 1.0\text{ mm}$), which created a severe cascade of failure modes: groove depths faded to zero, tangent cutter spheres triggered non-manifold kissing-edge defects, and applying a $0.25\text{ mm}$ cutoff omitted all vein cutter points on thin walls, resulting in 84-byte empty gold STL files and misleading UI labels. Furthermore, single-perimeter spiral vase mode cannot physically support multi-material inlays on FDM slicers. Dropping the vase-mode constraint and restricting the supported input envelope to real ceramic vessels ($p_5 \ge 1.6\text{ mm}$) mathematically guarantees nominal ceramic backing $\ge 0.8\text{ mm}$ everywhere under $d = \min(0.75W, 0.5t)$, permanently eliminating cutter point omissions and empty-gold bugs while restoring bold, continuous gold veins.

## What Changes

- **BREAKING**: Enforce a strict ceramic vessel envelope in `validate_and_load_mesh`: input watertight meshes must have 5th-percentile two-hit wall thickness $p_5 \ge 1.6\text{ mm}$ within the trauma band. Meshes below this threshold (such as `thin_cylinder` at 0.7–1.2 mm) are cleanly rejected with a clear `ValueError`.
- Restore the classical, continuous vein depth formula $d_i = \min(0.75W, 0.5t_i)$. On all supported meshes ($t \ge 1.6\text{ mm}$), nominal ceramic backing $t_i - d_i \ge 0.5t_i \ge 0.8\text{ mm}$ is guaranteed by construction without any groove fade.
- Remove cutter point omission logic (`d < 0.25 mm` dropping) and polyline splitting (`_vein_point_groups`), producing continuous, unbroken gold inlay solids along the entirety of every crack path.
- Refine crack growth collision handling: on the final attempt of an advancing step that arrives within clearance $R_{\text{clear}}$ at arrival angle $\ge 30^\circ$, snap the step directly onto the nearest point of the hit segment, eliminating 2–3 mm dangling stopping-short gaps.
- Standardize crack growth morphology to a correlated random walk with 15–20% sharp kink probability and Gaussian $\sigma \approx 18^\circ$ heading drift, avoiding staircase zig-zags while preserving median tortuosity $\ge 1.05$.
- Retain `_gold_solid_omitted` in exporter and `seams_omitted` in web API as general defensive safeguards for wealthy inputs ($R \ge 1.0$), ensuring the UI labels pristine runs accurately.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `mesh-fracture-engine`: Update `Supported input envelope` to mandate two-hit wall thickness $p_5 \ge 1.6\text{ mm}$; update `Metric R validation and clamping` to specify continuous vein depth $d_i = \min(0.75W, 0.5t_i)$; update `Parameter-space crack generation` for final-step near-miss snapping and 15–20% kink rate.
- `retro-web-gui`: Update `Fracture execution controls` to report ceramic wall thickness rejection errors in the UI, and display "Pristine / Wealthy (0 cracks)" strictly when $R \ge 1.0$.

## Impact

- **Core Engine (`kintsugi.py`)**: `validate_and_load_mesh` preflight wall thickness check; `_build_vein_cutter` simplified to continuous manifold solids without point dropping; `_grow_cracks` final-step near-miss snapping.
- **Model Library (`sample_models.py`)**: `thin_cylinder` moved to negative validation test suite; boundary model at $t = 1.6\text{ mm}$ added.
- **Web API & GUI (`web_app.py`, `static/viewer.js`)**: Clean error propagation for sub-1.6 mm meshes; accurate status reporting.
- **Dependencies**: No new dependencies (maintains strict zero-new-dependencies policy with `trimesh`, `manifold3d`, `scipy`, `numpy`).
