## MODIFIED Requirements

### Requirement: Supported input envelope
The system SHALL accept only inputs inside a declared envelope and SHALL reject everything else with a `ValueError` rather than producing degraded geometry. The envelope is: a closed, orientable 2-manifold triangle mesh; units of millimetres; +Z up; all bounding-box extents within $[20, 300]\text{ mm}$; a radially star-shaped exterior across the full wall range `[wall_z_min, wall_z_max]` (meaning every radial ray cast from the vertical axis through the bounding-box XY centre, at any $z \in [\text{wall\_z\_min}, \text{wall\_z\_max}]$, hits the outer surface); an open-top vessel interior cavity wall (`has_wall == True` in `_probe_wall_range`, meaning at least one horizontal probe slice $z$ has $\ge 95\%$ of its radial rays hitting two walls); and a 5th-percentile two-hit wall thickness $p_5 \ge 1.6\text{ mm}$ measured along inward surface normals across the full wall range `[wall_z_min, wall_z_max]`. Local vein groove depth $d_i = \min(0.75\,W, 0.5\,t_i)$ at each cutter point preserves nominal local ceramic backing $t_i - d_i \ge 0.5\,t_i$ everywhere ($\ge 0.8\text{ mm}$ wherever local $t_i \ge 1.6\text{ mm}$). This envelope requirement SHALL apply uniformly at validation time (`validate_and_load_mesh` and `POST /api/validate`) and across all fracture modes (`vein` and `ribbon`) and generators (`growth`, `shard`, `hybrid`, and `voronoi`).

#### Scenario: Vessel of revolution inside the envelope
- **WHEN** a watertight tea bowl STL with extents $90 \times 90 \times 60\text{ mm}$, `has_wall == True`, and wall thickness $p_5 \ge 1.6\text{ mm}$ across the wall range is loaded
- **THEN** the system accepts it and proceeds to crack generation

#### Scenario: Solid body without interior cavity wall rejected
- **WHEN** a closed solid mesh without an interior vessel cavity (`has_wall == False` in `_probe_wall_range`, such as a solid cylinder or solid block where no horizontal slice has $\ge 95\%$ two-wall hits) is passed to `validate_and_load_mesh` or `POST /api/validate`
- **THEN** the system raises a `ValueError` (and `/api/validate` returns `valid: false`) stating that the input mesh has no interior cavity wall and that only open-top single-wall vessels are supported

#### Scenario: Vessel with wall thickness below ceramic envelope
- **WHEN** a mesh with 5th-percentile normal wall thickness $p_5 < 1.6\text{ mm}$ across `[wall_z_min, wall_z_max]` is loaded (e.g. `thin_cylinder` fixture with wall thickness $0.7\text{--}1.2\text{ mm}$)
- **THEN** the system raises a `ValueError` stating the measured wall thickness $p_5$ and that input vessels must have $p_5 \ge 1.6\text{ mm}$ to guarantee safe ceramic backing

#### Scenario: Vessel at ceramic envelope boundary
- **WHEN** a mesh with normal wall thickness tested near the boundary (e.g. $p_5 \approx 1.7\text{ mm}$) is loaded
- **THEN** the system accepts it and proceeds to crack generation

#### Scenario: Wrong units or scale
- **WHEN** a mesh with any bounding-box extent outside $[20, 300]\text{ mm}$ is loaded (e.g. a model authored in metres, extents $0.09$)
- **THEN** the system raises a `ValueError` naming the offending extent and the expected millimetre range

#### Scenario: Non-vessel geometry
- **WHEN** more than $5\%$ of the radial probe rays across the wall range miss the mesh (e.g. a Benchy, or a mesh far off the Z axis)
- **THEN** the system raises a `ValueError` stating that the input is not a vessel the cylindrical parameterisation supports

## ADDED Requirements

### Requirement: Hybrid macro-and-hairline crack generation
The system SHALL support a two-stage hybrid fracture generator (`generator="hybrid"`) in `generate_kintsugi_mesh`, `generate_crack_paths`, and `generate_hybrid_crack_paths(params, rng, *, subdivide_step=None)` that combines Stage-1 shard through-fractures with Stage-2 growth interior hairlines into a single planar crack graph in unrolled `(u, z)` space before projecting and carving once in `vein` mode (producing a visual/topological partition of the exterior wall surface while `ceramic_body.stl` remains a single connected solid).

- **Vein-Only Mode Enforcement**: `generator="hybrid"` SHALL be restricted to `mode="vein"` and SHALL raise a `ValueError` when invoked with `mode="ribbon"`.
- **Severity Threshold & Low-Severity Behaviour (`S < 0.2`)**:
  - For $S = 1 - \text{clip}(R, 0, 1) < 0.2$ ($R > 0.8$) with `through_count="auto"` and `hairline_count="auto"`, `generate_hybrid_crack_paths` SHALL return `[]` (`through_count = 0`, `hairline_count = 0`, `num_fragments = 1`), matching `shard`. If the caller explicitly overrides `through_count >= 1` or `hairline_count >= 1` when $0 < S < 0.2$, Stage 1 SHALL use the lowest shard tier baselines (`harmonic = 0.015`, `kink_deg = 4.0`, `tilt_deg = 14.0`).
- **Stage 1 — Through-Fractures (Macro Seams)**:
  - For $S \ge 0.2$ (or explicit `through_count >= 1` with $S > 0$), Stage 1 SHALL generate $1$ to $3$ macro shard seams (`through_count`).
  - When `through_shape` is `"auto"` or `"wedge"`, Seam 1 SHALL be an open rim-to-rim wedge (`_shard_wedge_path`) whose endpoints both reach the upper rim boundary ($z \ge \text{wall\_z\_max}$). When `through_shape` is `"loop"`, Seam 1 SHALL attempt a closed periodic tilted loop (`_shard_loop_path`, which stays strictly inside the wall band and does not reach the rim), falling back to `"wedge"` if wall height forces tilt $< 5^\circ$ (recording both `through_shape_requested` and resolved `through_shape` in `parameters["hybrid"]`).
  - `tilt_deg` ($5.0\text{--}30.0^\circ$) SHALL steer **both** primitives: for `"loop"` it sets the loop plane inclination angle; for `"wedge"` it steers the wedge nadir depth within $[\text{wall\_z\_min} + 0.18\,\Delta z_{\text{wall}}, \text{wall\_z\_max} - 0.20\,\Delta z_{\text{wall}}]$ and the longitudinal nadir skew parameter along the wedge span so changing `tilt_deg` deterministically changes wedge geometry.
  - Each subsequent macro seam $k \in \{2, \dots, \text{through\_count}\}$ SHALL be selected from up to 16 deterministic rim-to-seam wedge candidates (`_shard_extra_seam_candidate`) targeting an earlier macro seam $0 \dots k-1$, truncated at the earliest intersection across *all* existing macro seams inside $[\text{wall\_z\_min} + W, \text{wall\_z\_max} - W]$ with arrival angle $\ge 30^\circ$ against all incident segments at the hit point, rim endpoint separation $\ge 1.5 (W + 0.8\text{ mm})$, and `analyze_growth_paths` reporting `crossings == 0` and `min_clearance >= W + 0.8` mm. If no valid candidate is found within 16 tries for seam $k$, Stage 1 SHALL retain the $k-1$ verified macro seams.
- **Stage 2 — Interior Hairlines (Growth Stage)**:
  - `hairline_count` ($0\text{--}10$) defines the number of primary Stage-2 hairline trunks (`level=0` growth tasks, each of which may spawn standard child branches). Its `auto` default SHALL follow the named tier table: `0` for $S < 0.20$, `3` for $0.20 \le S < 0.35$, `5` for $0.35 \le S < 0.70$, and `7` for $S \ge 0.70$.
  - When resolved `hairline_count > 0`, Stage 2 SHALL invoke `generate_crack_growth_paths` with the Stage-1 macro seams and junctions pre-committed into `paths` and `params["_growth_junctions"]`.
  - Target primary hairline trunks SHALL be split into `n_seam_target = hairline_count // 2` macro-seam interior anchors and `n_rim_target = hairline_count - n_seam_target` upper-rim seeds:
    - Each macro-seam interior anchor SHALL pick a vertex on a Stage-1 seam inside $[\text{wall\_z\_min} + 1.5 W, \text{wall\_z\_max} - 1.5 W]$ at distance $\ge 2 (W + 0.8\text{ mm})$ from existing junctions/endpoints, choose a downward-compatible departure heading (`_clamp_heading` within $\pm 85^\circ$ of straight down) that forms an acute angle in $[60^\circ, 85^\circ]$ (and $\ge 45^\circ$ after clamping) with the parent macro seam tangent, record a shared `"T"` junction, and enqueue a `_GrowthTask` with `exempt_path_id` set to the parent macro seam's path index and `exempt_origin` set to the anchor vertex so the initial steps do not self-collide with the parent macro seam. Any anchor slot that cannot be placed (e.g. on the upper arch of a loop where downward headings cannot clear $45^\circ$) SHALL fall back to `n_rim_target`.
    - Upper-rim hairline seeds SHALL be placed by `_poisson_rim_seeds` keeping at least $1.5 (W + 0.8\text{ mm})$ circular distance in $u$ from every Stage-1 rim endpoint across **both** random rejection sampling and the largest-gap fallback (giving up unplaceable seeds rather than placing any seed inside an exclusion zone).
  - Pre-committed Stage-1 seams SHALL act as obstacles in `_first_growth_collision`, causing approaching hairlines to either snap into a verified $\ge 30^\circ$ T-junction on a macro seam and terminate, or stop inside the fragment with clearance $\ge W + 0.8\text{ mm}$.
  - `roughness` ($0.5\text{--}2.0$) SHALL scale Stage-1 harmonic/kink amplitudes and Stage-2 per-step angular heading deltas before `_clamp_heading` clamps the resulting heading to $\pm 85^\circ$ of straight down (preserving step length and step count).
- **Stage 3 — Combined Audit & Raster Fragment Count (`num_fragments`)**:
  - The union of Stage-1 and Stage-2 paths SHALL pass `analyze_growth_paths` directly (without silent path pruning) with `crossings == 0`, `clearance_violations == 0`, `min_clearance >= W + 0.8` mm (measured across non-incident segments outside the adjacent-segment `skip_span` and recorded `"T"`/`"Y"` junction exemption neighborhoods), and minimum junction angle $\ge 30^\circ$.
  - `num_fragments` (for the combined graph) and `num_through_fragments` (for Stage-1 macro seams alone) SHALL be computed by `_count_wall_fragments(paths, params)`, which rasterises segments inflated to half-width $0.5\,W$ on a $0.25\text{ mm}$ grid over $[0, \text{period}) \times [\text{wall\_z\_min}, \text{wall\_z\_max}]$ (periodic in $u$, bounded in $z$) and counts 4-connected free-wall components whose area is at least $2\%$ of total free wall area. For $S \ge 0.2$, both `num_through_fragments` and `num_fragments` SHALL be $\ge 2$.
  - `generate_kintsugi_mesh` SHALL report `num_fragments` at the top level of the returned dictionary and echo `through_count`, `through_shape`, `through_shape_requested`, `tilt_deg`, `hairline_count`, `hairline_rim_count`, `hairline_seam_count`, `hairline_reach`, `roughness`, `num_through_fragments`, and `num_fragments` in `parameters["hybrid"]`.
- **Hybrid Knobs and Fail-Fast Validation**:
  - Passing any non-`None` hybrid knob (`through_count`, `through_shape`, `tilt_deg`, `hairline_count`, `hairline_reach`, `roughness`) when `generator != "hybrid"`, or passing an out-of-range knob value, SHALL raise a `ValueError` (`HTTP 400` in the Web API).

#### Scenario: Default hybrid generation partitions the wall surface and grows bounded hairlines
- **WHEN** `generate_kintsugi_mesh` or `generate_crack_paths` is called with `generator="hybrid"`, `mode="vein"`, and $R \in [0.0, 0.8]$ ($S \ge 0.2$) with all hybrid knobs at `auto`
- **THEN** Stage 1 produces $1\text{--}3$ macro seams starting with an edge-reaching rim-to-rim wedge, Stage 2 grows both rim-seeded and seam-anchored interior hairlines that survive their first step via `exempt_path_id`/`exempt_origin` and terminate inside fragments or at verified $\ge 30^\circ$ T-junctions, `analyze_growth_paths` reports `crossings == 0` and `min_clearance >= W + 0.8` mm, and the result reports raster-verified `num_fragments >= 2`, `num_through_fragments >= 2`, and `parameters["hybrid"]`

#### Scenario: Every hybrid knob demonstrably alters output paths under default and loop shapes
- **WHEN** `generate_crack_paths` is called with `generator="hybrid"`, $R = 0.45$, and a fixed seed while varying each knob individually (`through_count` $1 \text{ vs } 3$, `through_shape` `"wedge" \text{ vs } "loop"`, `tilt_deg` $10.0 \text{ vs } 28.0$ under both `"wedge"` and `"loop"`, `hairline_count` $0 \text{ vs } 6$, `hairline_reach` $0.25 \text{ vs } 0.95$, and `roughness` $0.5 \text{ vs } 1.8$)
- **THEN** each knob change produces distinct crack polylines and echoes the exact resolved override in `parameters["hybrid"]`

#### Scenario: Low-severity hybrid behaviour below S = 0.2
- **WHEN** `generate_crack_paths` is called with `generator="hybrid"`, $R = 0.85$ ($S = 0.15 < 0.2$), and all hybrid knobs at `auto`
- **THEN** the generator returns `[]` with `num_fragments == 1` and `through_count == 0`, matching `shard`

#### Scenario: Hybrid knobs rejected on non-hybrid generators
- **WHEN** any hybrid knob (`through_count`, `through_shape`, `tilt_deg`, `hairline_count`, `hairline_reach`, or `roughness`) is provided while `generator` is `"growth"`, `"shard"`, or `"voronoi"`
- **THEN** the system raises a `ValueError` stating that hybrid parameters are only valid when `generator="hybrid"`

#### Scenario: Existing growth and shard generators remain byte-identical to pre-change SHA-256 digests
- **WHEN** `generate_crack_paths` is run with `generator="growth"` or `generator="shard"` across `tea_bowl` and `vase` at $R \in \{0.2, 0.3, 0.35, 0.65, 0.75, 0.8\}$ and seeds `42, 43, 44`
- **THEN** the returned polylines match the pre-change SHA-256 baseline digests byte-for-byte
