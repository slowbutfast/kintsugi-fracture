# mesh-fracture-engine Specification

## Purpose
TBD - created by archiving change kintsugi-mesh-fracture. Update Purpose after archive.
## Requirements
### Requirement: Supported input envelope
The system SHALL accept only inputs inside a declared envelope and SHALL reject everything else with a `ValueError` rather than producing degraded geometry. The envelope is: a closed, orientable 2-manifold triangle mesh; units of millimetres; +Z up; all bounding-box extents within $[20, 300]\text{ mm}$; a radially star-shaped exterior across the full wall range `[wall_z_min, wall_z_max]` (meaning every radial ray cast from the vertical axis through the bounding-box XY centre, at any $z \in [\text{wall\_z\_min}, \text{wall\_z\_max}]$, hits the outer surface); and a 5th-percentile two-hit wall thickness $p_5 \ge 1.6\text{ mm}$ measured along inward surface normals across the full wall range `[wall_z_min, wall_z_max]`. This envelope requirement SHALL apply uniformly across all fracture modes (`vein` and `ribbon`).

#### Scenario: Vessel of revolution inside the envelope
- **WHEN** a watertight tea bowl STL with extents $90 \times 90 \times 60\text{ mm}$ and wall thickness $p_5 \ge 1.6\text{ mm}$ across the wall range is loaded
- **THEN** the system accepts it and proceeds to crack generation

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

### Requirement: Metric R validation and clamping
The system SHALL validate the input income ratio $R$ as a finite float and compute severity $S = 1.0 - \text{clip}(R, 0.0, 1.0)$. All fracture parameters SHALL be pure functions of $S$ and the validated mesh:

| Parameter | Definition |
| :--- | :--- |
| Seed count | $N(S) = \lfloor 2 + 8S \rfloor$ primary rim trunks |
| Seam width | $W(S) = 0.8 + 1.4S$ mm (overridable via `seam_width`, which SHALL be rejected below $0.8$ mm) |
| Trauma penetration depth | $H(S) = H_{wall} \cdot (0.2 + 0.8S)$, measured downwards from `wall_z_max` |
| Ribbon depth | $D_i = t_i + 1.0$ mm, where $t_i$ is local normal wall thickness at path point $i$ |
| Vein inlay depth | $d_i = \min(0.75\,W,\ 0.5\,t_i)$, continuously along each crack without point omissions |

#### Scenario: Valid inequality metric
- **WHEN** $R = 0.4$ is provided
- **THEN** system computes severity $S = 0.6$, seed count $N = \lfloor 6.8 \rfloor = 6$, and seam width $W = 1.64\text{ mm}$

#### Scenario: Wealthy threshold
- **WHEN** $R \ge 1.0$ is provided (e.g., $R = 1.0$ or $R = 1.5$)
- **THEN** system returns severity $S = 0.0$, generating zero fractures and retaining the validated input mesh

#### Scenario: Negative metric
- **WHEN** $R < 0.0$ is provided
- **THEN** system clamps $R$ to $0.0$, yielding maximum severity $S = 1.0$

#### Scenario: Non-finite metric
- **WHEN** $R$ is NaN or infinity
- **THEN** system raises a `ValueError` with an explanatory message

#### Scenario: Ceramic vessel backing guarantee in vein mode
- **WHEN** a vein inlay is carved on any valid vessel with local normal wall thickness $t_i$ and seam width $W \in [0.8, 2.2]\text{ mm}$
- **THEN** vein cutter depth $d_i$ is $\min(0.75W, 0.5t_i)$, preserving nominal ceramic backing $t_i - d_i \ge 0.5t_i$ everywhere, $\ge 0.8\text{ mm}$ wherever $t_i \ge 1.6\text{ mm}$, and minimum depth $\ge 0.6\text{ mm}$ without cutter point omissions

#### Scenario: Empty gold solid defensive safeguard
- **WHEN** an uncarved pass occurs ($R \ge 1.0$) or the complementary gold boolean has zero triangles
- **THEN** the system SHALL not write `gold_seams.stl`, SHALL omit `GoldSeams` from the 3MF container, SHALL unlink any stale gold STL from an earlier run, and SHALL return `gold_path: None`, `seams_omitted: true`, `num_cracks: 0`, `volumes.gold: 0.0`, and `triangle_counts.gold: 0`

### Requirement: Watertight input mesh validation
The system SHALL validate the input mesh before any branching on $R$, including the wealthy pass-through, and SHALL construct exactly one `manifold3d.Manifold` from it using `Mesh64` (float64) so no precision is lost in conversion. Repair SHALL be limited to lossless clean-up (merging duplicate vertices, removing degenerate faces, making winding consistent); the system SHALL NOT fill holes or otherwise invent geometry.

#### Scenario: Pristine manifold STL loaded
- **WHEN** a valid watertight STL file is loaded
- **THEN** system merges duplicate vertices, fixes winding, builds a `manifold3d.Manifold` from `Mesh64`, and verifies `status() == Error.NoError` and `volume() > 0`

#### Scenario: Non-manifold or open input
- **WHEN** a mesh with boundary edges, non-manifold edges, or non-positive volume is loaded, at any value of $R$
- **THEN** system raises a `ValueError` indicating the input mesh is not a valid closed solid, and writes no output files

### Requirement: Parameter-space crack generation
The system SHALL generate the crack network in an unrolled cylindrical parameter space $(u, z)$, where $u = \theta \cdot \bar r$ and $\bar r$ is the mean outer radius across the trauma band. Cracks SHALL be grown sequentially from rim-seeded impact points with stop-on-hit collision handling, and then projected onto the exterior surface by radial ray casting against the input `Manifold` (`Manifold.ray_cast`).

#### Scenario: Rim-seeded crack growth
- **WHEN** severity $S > 0$ and `--generator growth` is active
- **THEN** system initiates $N(S)$ primary crack trunks at angular locations along the upper rim at $z \ge \text{wall\_z\_max}$ spaced by minimum angular clearance $\Delta \theta \ge \frac{W + 1.5\text{ mm}}{\bar r}$ and propagates them downwards taking steps in $[1.5W, 3.0W]$ with random-walk heading constrained within $\pm 85^\circ$ of straight down, using a correlated random walk with $15\%\text{--}20\%$ sharp kink probability and Gaussian $\sigma \approx 18^\circ$ heading drift

#### Scenario: Growth budgets and jittered penetration
- **WHEN** a crack trunk or branch advances
- **THEN** growth terminates when: (a) it hits an existing crack under stop-on-hit, (b) its current $z$ reaches below the per-trunk jittered penetration limit $z_{\text{limit}} = \text{wall\_z\_max} - H(S) \cdot (1 + \delta)$ with $\delta \sim U(-0.15, +0.15)$, or (c) its total arc length reaches its assigned length budget ($L_{\text{trunk}} = 1.2 \cdot H(S)$, $L_{\text{branch}} = 0.5 \cdot H(S)$)

#### Scenario: Stop-on-hit collision with forward snapping and final attempt bend
- **WHEN** a candidate segment advancing from $\mathbf{p}_a$ toward $\mathbf{p}_b$ approaches within distance $R_{\text{clear}} = W + 0.8\text{ mm}$ of any committed segment (including virtual periodic copies shifted by $\pm 2\pi\bar r$, and earlier non-adjacent segments of the same crack)
- **THEN** if arrival incidence angle is $\ge 30^\circ$, system projects travel vector forward to intersect the hit segment, snaps to that intersection, terminates growth, and subdivides the hit segment there with a shared vertex; if forward extension fails or is unsafe, on the final attempt the system bends the advancing step onto the nearest point of the hit segment (provided arrival angle $\ge 30^\circ$ and bend is collision-free) to eliminate stopping short

#### Scenario: Grazing approach resolution
- **WHEN** an advancing segment approaches an existing segment within $R_{\text{clear}}$ at an arrival angle $< 30^\circ$
- **THEN** the system resamples the candidate heading up to 3 times to achieve an angle $\ge 30^\circ$; if all attempts fail, growth terminates at the previous committed point $\mathbf{p}_a$, leaving a free end with at least $W + 0.8\text{ mm}$ clearance

#### Scenario: Secondary dendritic branching and junction exemption
- **WHEN** a crack trunk propagates through the trauma band
- **THEN** it may spawn up to 2–3 child branches per trunk (severity-driven, maximum 1 level of branching) at a per-step probability of approximately $0.15 \cdot S$ spaced by at least 6 steps, departing at $30^\circ\text{--}45^\circ$ for acute whiskers or up to $85^\circ$ for lateral connecting fissures, toward the side with greater angular clearance. Within a junction exemption radius $R_{\text{exempt}} = \frac{W + 0.8\text{ mm}}{\sin \theta_{\text{branch}}}$ of the branch origin, proximity checks against the parent segment are ignored

#### Scenario: Deterministic growth order
- **WHEN** multiple cracks grow
- **THEN** crack segments advance in deterministic order (FIFO queue in spawn order, one step per turn) with seeded random numbers, ensuring identical graph topology across repeated runs

#### Scenario: Shipped growth graph is planar
- **WHEN** crack paths are generated under the growth generator
- **THEN** no two path segments intersect except at shared junction vertices across all seeds and severities; stop-on-hit guarantees planarity by construction

#### Scenario: Radial projection takes the exterior hit and clamps rim overshoot
- **WHEN** a parameter-space point $(u, z)$ is projected
- **THEN** if $z \ge \text{wall\_z\_max}$, the ray is cast at $z = \text{wall\_z\_max} - \max(0.5, W/2)\text{ mm}$ to guarantee hitting the exterior lip below any rounded rim taper; otherwise the ray is cast from the axis at height $z$ outward along $\theta = u / \bar r$; the farthest hit is taken as exterior surface point $p_i$ with outward normal $n_i$, and local normal wall thickness $t_i$ is recorded as the distance along the inward surface normal $-n_i$ to the next interior hit

#### Scenario: Ray miss
- **WHEN** a projection ray returns no hits
- **THEN** that path point is dropped and the path is split at that point; only misses whose $z$ lies inside the wall range $[\text{wall\_z\_min}, \text{wall\_z\_max}]$ count towards the $5\%$ envelope, and the input-envelope `ValueError` is raised only when that in-range fraction exceeds $5\%$

#### Scenario: Perturbed points are truncated at the wall
- **WHEN** a polyline leaves the wall range
- **THEN** it is cut where $z$ leaves $[z_{wall,lo} + 0.5W,\ \text{wall\_z\_max} + 0.5W]$: the crossing point is interpolated exactly, outside parts are discarded, and kept pieces have at least two points and length $\ge W$

### Requirement: Watertight cutter solid construction
The system SHALL build the cutter as a union of convex hulls of consecutive cross-sections along each crack path, combined with a single `Manifold.batch_boolean(parts, OpType.Add)`, using `circular_segments = 16` for spheres.

#### Scenario: Vein mode cutter construction
- **WHEN** `mode="vein"` is selected
- **THEN** system places spheres of radius $W/2$ centred at $p_i - (d_i - W/2)\,n_i$, so each groove is exactly $d_i$ deep and never pierces the wall, and unions consecutive overlapping spheres directly (using `(sphere_i + sphere_{i+1}).hull()` only when their centre gap exceeds the sphere diameter)

#### Scenario: Ribbon mode through-wall cutter construction
- **WHEN** `mode="ribbon"` is selected
- **THEN** at each path point system builds a slab spanned by the binormal $b_i = \text{normalize}(T_i \times n_i)$ (width $W$) and the inward normal $-n_i$ (from $0.5$ mm outside $p_i$ to $D_i - 0.5$ mm inside it), with $T_i$ the central-difference path tangent projected onto the surface tangent plane, and joins consecutive slabs with `(slab_i + slab_{i+1}).hull()`

#### Scenario: Degenerate frame
- **WHEN** the projected tangent $T_i$ has length below $10^{-6}$ mm (duplicate or cusped points)
- **THEN** the frame from $i-1$ is reused, and the point is dropped if it is the first point of a path

#### Scenario: Cutter primitives are de-aligned
- **WHEN** a cutter is built from repeated spheres or slabs
- **THEN** each unique vein sphere receives a seeded rotation and a $\le 0.2\%$ radius jitter and overlapping consecutive spheres are unioned directly (a hull is used only when the centre gap exceeds the sphere diameter); ribbon slabs receive a seeded $\pm 0.5^\circ$ normal-axis rotation and $\le 10^{-3}W$ depth/centre jitter. Tiny export slivers are collapsed only when the mesh stays watertight, positive-volume and within $10^{-6}$ volume, so the cutter has zero non-manifold edges after a position-merging binary-STL round trip

### Requirement: Exact complementary boolean partitioning
The system SHALL compute both outputs from the identical validated input `Manifold` $M$ and a single cutter $C$: $M_{ceramic} = M \setminus C$ and $M_{gold} = M \cap C$.

#### Scenario: Complementary volume partitioning (smoke check)
- **WHEN** $M$ and $C$ are evaluated
- **THEN** $|\text{Vol}(M_{ceramic}) + \text{Vol}(M_{gold}) - \text{Vol}(M)| \le 10^{-6} \cdot \text{Vol}(M)$. This holds by construction and is asserted only to detect kernel or conversion regressions, not as evidence of print quality.

#### Scenario: Determinism
- **WHEN** `generate_kintsugi_mesh` is run twice with the same input, $R$, `seed` and `mode`
- **THEN** both runs produce byte-identical output files; all randomness flows from a single `numpy.random.default_rng(seed)`

### Requirement: Shard-plane crack generation
The system SHALL support an opt-in shard-plane fracture generator (`generator="shard"`) alongside `"growth"` (default) and legacy `"voronoi"` in `generate_kintsugi_mesh` and `generate_crack_paths(params, rng, *, subdivide_step=None, generator="growth")`, synthesizing cylindrical plane-inspired 2D seam curves in unwrapped `(u, z)` space (`u` in `[0, period]`, `period = 2*pi*rbar`) and feeding them into `project_crack_paths`, `_build_vein_cutter`, and `Manifold3D` boolean carving.

In Stage 1:
- `generator="shard"` SHALL be restricted to `mode="vein"` and SHALL raise a `ValueError` when invoked with `mode="ribbon"`. The Web API (`POST /api/fracture`) SHALL return `HTTP 400 Bad Request` with an explanatory message when this combination is requested.
- **Metric Mapping**: Generation SHALL be governed by severity $S = 1 - \text{clip}(R, 0, 1)$, where $R$ is the vessel reserve metric. Fracture roughness, seam count, harmonic amplitudes, and kink variance SHALL be configured according to $S$:
  - $S < 0.2$ ($R > 0.8$): 0 seams (unbroken vessel).
  - $0.2 \le S < 0.35$ ($0.65 < R \le 0.8$): 1 seam, Primitive 1 (50% Wedge, 50% Loop when wall height permits), harmonics $A_{2,3} = 0.015\,\Delta z_{\text{wall}}$, kink $\sigma_\theta = 4^\circ$, sub-arc tortuosity $\tau \in [1.05, 1.10]$.
  - $0.35 \le S < 0.70$ ($0.30 < R \le 0.65$): 1 or 2 seams (attempt Seam 2), Primitive 1 (50% Wedge, 50% Loop when wall height permits), harmonics $A_{2,3} = 0.035\,\Delta z_{\text{wall}}$, kink $\sigma_\theta = 8^\circ$, sub-arc tortuosity $\tau \in [1.08, 1.20]$.
  - $0.70 \le S \le 1.0$ ($0.0 \le R \le 0.30$): 2 seams (attempt Seam 2), Primitive 1 (50% Wedge, 50% Loop when wall height permits), harmonics $A_{2,3} = 0.060\,\Delta z_{\text{wall}}$, kink $\sigma_\theta = 14^\circ$, sub-arc tortuosity $\tau \in [1.12, 1.35]$.
- **Open Rim-to-Rim Wedge Seam**: When generating an open wedge seam, the generator SHALL construct a curve that enters at the upper rim ($z = \text{wall\_z\_max} + 0.35W$), dips to a deterministic interior nadir $z_{\text{nadir}} \in [\text{wall\_z\_min} + 0.18\,\Delta z_{\text{wall}}, \text{wall\_z\_max} - 0.20\,\Delta z_{\text{wall}}]$, and exits back through the upper rim, truncating the curve at exact wall-band boundary crossings via `_truncate_polyline_z(raw, wall_z_min + 0.5*W, wall_z_max + 0.35*W, min_length=3.0*W)`. Truncated seams SHALL NOT contain flat-run ledges (no two consecutive points within $1\text{e-}6$ mm of truncation bounds).
- **Closed Tilted Loop Seam**: When generating a closed loop seam, the generator SHALL construct a periodic curve over $u \in [0, P]$ combining baseline tilt $z_{\text{base}}(u) = z_0 + \bar{r}\tan(\alpha)\cos(u/\bar{r} - \phi)$, periodic Fourier harmonics ($k \in \{2, 3\}$), and a linear drift bridge kink walk ($kink_i = w_i - \frac{i}{N-1}(w_{N-1} - w_0)$) so that $z(0) = z(P)$ within $1\text{e-}6$ mm. The curve amplitudes SHALL be capped before sampling to fit strictly inside $[\text{wall\_z\_min} + 0.6*W, \text{wall\_z\_max} - 0.6*W]$; if available height forces tilt angle $\alpha < 5^\circ$, the generator SHALL select Primitive A (Wedge) instead of generating a flat horizontal ring.
- **Two-Seam Verified Intersection and Fallback**: When $S \ge 0.35$, the generator SHALL evaluate up to 16 deterministic candidate second seams originating as open wedges from the rim. It SHALL accept the first candidate that intersects Seam 1 inside $[\text{wall\_z\_min} + W, \text{wall\_z\_max} - W]$ at an arrival angle $\ge 30^\circ$ and passes `analyze_growth_paths` with `min_clearance >= W + 0.8` mm after inserting a shared T-junction vertex into Seam 1, truncating Seam 2 at the intersection, and appending a T-junction record to `params["_growth_junctions"]`. If no candidate meets these conditions within 16 tries, the generator SHALL deterministically fall back to returning `[Seam 1]`.
- **Closed-Loop Audit and Tortuosity**: For closed periodic loops where `_periodic_distance(path[0], path[-1], period) <= 1e-6`, `analyze_growth_paths` SHALL compute adjacent segment skip span cyclically (`min(diff, n_path_segs - diff) <= skip_span`), and `_tortuosity_values` SHALL split loops without junctions into 4 equal quadrant sub-arcs ($\Delta u = P / 4$) in 2D $(u, z)$ space before evaluating arc over chord, enforcing $\tau \ge 1.05$.

#### Scenario: Open rim-to-rim wedge seam generation and exact truncation
- **WHEN** `generate_shard_crack_paths` generates an open rim-to-rim wedge seam on a vessel with `wall_z_min`, `wall_z_max`, and vein width $W$
- **THEN** the seam is truncated at exact wall-band crossings without flat-run horizontal shelves (no two consecutive vertices with $z$ within $1\text{e-}6$ of the boundary), raw endpoints lie above `wall_z_max` within $0.35 * W$, and the projected 3D endpoints land on the upper rim lip ($z \ge \text{wall\_z\_max} - 0.5 * W$)

#### Scenario: Closed tilted loop seam generation and drift bridge closure
- **WHEN** `generate_shard_crack_paths` generates a closed tilted loop seam over $u \in [0, P]$
- **THEN** the loop endpoints satisfy `_periodic_distance(path[0], path[-1], period) <= 1e-6` via linear drift bridge correction, every vertex stays within $[\text{wall\_z\_min} + 0.6*W, \text{wall\_z\_max} - 0.6*W]$, and `analyze_growth_paths` reports zero self-intersections and `min_clearance >= W + 0.8` mm across the periodic boundary

#### Scenario: Two-seam verified intersection and shared T-junction
- **WHEN** `generate_shard_crack_paths` is called with $S \ge 0.35$ and a candidate second seam intersects Seam 1 inside $[\text{wall\_z\_min} + W, \text{wall\_z\_max} - W]$ at an arrival angle $\ge 30^\circ$ with non-incident clearance $\ge W + 0.8$ mm
- **THEN** Seam 2 is truncated at that first intersection point, Seam 1 contains an exact matching shared junction vertex (`_periodic_distance <= 1e-6`), `params["_growth_junctions"]` contains the T-junction metadata, and `analyze_growth_paths` reports zero illegal crossings and `min_clearance >= W + 0.8` mm

#### Scenario: Deterministic single-seam fallback when no valid intersection exists
- **WHEN** `generate_shard_crack_paths` is called with $S \ge 0.35$ and none of the 16 deterministic candidate second seams produce a valid intersection satisfying wall-band, arrival-angle, and clearance constraints
- **THEN** the generator deterministically falls back to returning Seam 1 alone without unverified overlapping or floating non-intersecting second seams

#### Scenario: Closed-loop cyclic clearance and quadrant sub-arc tortuosity
- **WHEN** `analyze_growth_paths` and `_tortuosity_values` evaluate a closed periodic loop seam with $S \in [0.2, 1.0]$
- **THEN** segment adjacency is evaluated cyclically across the $u=0 \equiv P$ wrap point without false clearance violations, and `_tortuosity_values` evaluates 2D $(u, z)$ arc-length over chord-length across 4 quadrant sub-arcs ($\Delta u = P / 4$) producing finite tortuosity values satisfying $\tau \ge 1.05$

#### Scenario: Generator dispatch and vein-mode scope enforcement
- **WHEN** `generate_kintsugi_mesh` is called with `generator="shard"` and `mode="ribbon"`
- **THEN** the system raises a `ValueError` stating that `generator="shard"` is only supported with `mode="vein"` in Stage 1, while `mode="vein"` dispatches successfully through `generate_crack_paths` to `generate_shard_crack_paths`

#### Scenario: API fracture endpoint error handling
- **WHEN** a client sends `POST /api/fracture` with form fields `generator=shard` and `mode=ribbon`
- **THEN** the Web API returns HTTP status 400 Bad Request with an error detail indicating that `generator="shard"` is restricted to `vein` mode

### Requirement: Validation-time vessel wall requirement

`validate_and_load_mesh` SHALL reject any input whose radial wall probe finds no horizontal slice with at least 95% two-hit radial samples (`has_wall == False`) by raising a `ValueError` that states the input has no usable wall. This rejection SHALL occur during validation, before any crack generation, so solid bodies with no interior cavity never reach the fracture stage.

#### Scenario: Solid non-hollow body rejected at validation
- **WHEN** a closed solid cylinder with no interior cavity is passed to `validate_and_load_mesh`
- **THEN** the function raises a `ValueError` whose message states that the input has no usable wall, and no crack paths or output files are produced

#### Scenario: Open-top vessel with a measurable wall accepted
- **WHEN** a watertight open-top bowl with a two-hit radial wall across its wall range is passed to `validate_and_load_mesh`
- **THEN** validation succeeds and the returned probe reports `has_wall == True`

### Requirement: Hybrid two-stage crack generation

The system SHALL support an opt-in `generator="hybrid"` in `generate_crack_paths` and `generate_kintsugi_mesh`. Hybrid SHALL run only in `mode="vein"` and SHALL raise a `ValueError` for `mode="ribbon"`. It SHALL implement two stages in `generate_hybrid_crack_paths`:

1. **Through-fracture stage.** Generate between one and three shard-style macro seams. The first seam is a rim-to-rim wedge or a closed tilted loop. Each later seam T-junctions into any earlier macro seam and is truncated at the earliest intersection across all existing macro seams. The through-fracture set SHALL partition the unrolled wall into at least two fragments whenever $S \ge 0.2$.
2. **Hairline stage.** Run `generate_crack_growth_paths` with the stage-1 seams pre-committed as obstacle paths and with rim seeds excluded around every stage-1 rim crossing. Hairlines SHALL either T-junction into a through-fracture or dead-end inside a fragment. A configured number of hairlines SHALL start at interior macro-seam anchors whose first growth task sets `exempt_path_id` and `exempt_origin` so the first step does not collide with the parent seam.

The combined Stage-1 and Stage-2 path set SHALL be validated directly with `analyze_growth_paths(paths, params)` without silently pruning paths. The result SHALL report `num_through_fragments` and `num_fragments` from `_count_wall_fragments`.

#### Scenario: Two-stage partition on a vessel
- **WHEN** `generate_hybrid_crack_paths` is called at $S \ge 0.2$ on a supported vessel
- **THEN** it returns a combined path set with at least one stage-1 through-fracture, `num_through_fragments >= 2`, and `num_fragments >= 2`

#### Scenario: Low severity auto behaviour
- **WHEN** $S < 0.2$ and both `through_count` and `hairline_count` are `auto`
- **THEN** `generate_hybrid_crack_paths` returns an empty path list, reports `through_count = 0`, `hairline_count = 0`, and `num_fragments = 1`

#### Scenario: Low severity explicit override
- **WHEN** $0 < S < 0.2$ and `through_count >= 1` or `hairline_count >= 1` is supplied explicitly
- **THEN** Stage 1 uses the lowest shard tier baselines (`harmonic = 0.015`, `kink_deg = 4.0`, `tilt_deg = 14.0`) instead of returning an empty path list

#### Scenario: Stage-1 auto shape reaches the rim
- **WHEN** `through_shape="auto"` and the generator selects a wedge, or a loop is unavailable and falls back to a wedge
- **THEN** the resulting macro seam is an open wedge whose two endpoints reach the upper rim within the stage-1 truncation bounds

#### Scenario: Seam 2 and Seam 3 T-junction into any earlier seam
- **WHEN** a later macro seam is requested
- **THEN** `_shard_extra_seam_candidate` targets any earlier macro seam, truncates at the earliest hit across all existing macro seams, inserts a shared vertex in the hit seam, and rejects candidates below the 30° arrival angle or `W + 0.8 mm` clearance rules

#### Scenario: Hairline obstacles and rim exclusion
- **WHEN** the hairline stage runs after stage 1
- **THEN** stage-1 seams are present in the growth generator's committed obstacle list, and no rim seed is placed within the exclusion radius of a stage-1 rim crossing in either rejection sampling or the largest-gap fallback

#### Scenario: Macro-seam interior hairline anchors
- **WHEN** `hairline_count >= 2` and a stage-1 macro seam is available
- **THEN** at least one hairline trunk starts at an interior point on a macro seam, its first growth task carries `exempt_path_id`/`exempt_origin` for that seam, and its first step survives collision resolution

#### Scenario: Combined audit invariants
- **WHEN** the union of stage-1 and stage-2 paths is audited
- **THEN** `analyze_growth_paths` reports zero crossings, zero clearance violations, `min_clearance >= W + 0.8 mm`, and every reported junction angle is at least 30°

#### Scenario: Periodic raster fragment counter
- **WHEN** `_count_wall_fragments(paths, params)` rasterises seams at half-width $0.5W$ on a 0.25 mm grid over $[0, period) \times [wall\_z\_min, wall\_z\_max]$
- **THEN** it counts 4-connected free-wall components whose area is at least 2% of the total free area, with periodicity in $u$ and no wrap-around double counting

#### Scenario: Deterministic hybrid output
- **WHEN** `generate_hybrid_crack_paths` is called twice with the same model, $R$, seed, and resolved knobs
- **THEN** both runs produce byte-identical path arrays

### Requirement: Hybrid knob ranges and Auto resolution

The system SHALL accept hybrid-only knobs `through_count` (1–3), `through_shape` (`auto`, `wedge`, `loop`), `tilt_deg` (5–30), `hairline_count` (0–10), `hairline_reach` (0.2–1.0), and `roughness`. Each knob SHALL default to `auto` and resolve from $S = 1 - R$:

| Knob | Auto rule |
| :--- | :--- |
| `through_count` | 1 for $S < 0.35$, 2 for $S < 0.70$, 3 above |
| `through_shape` | 50/50 per seed, with loop falling back to wedge when unavailable |
| `tilt_deg` | Shard tier value 14, 20 or 26 |
| `hairline_count` | 0 for $S < 0.20$, 3 for $S < 0.35$, 5 for $S < 0.70$, 7 above |
| `hairline_reach` | $0.2 + 0.8S$ |
| `roughness` | 1.0 |

The resolved values SHALL be echoed in `parameters["hybrid"]`, together with actual placed counts and `num_through_fragments` / `num_fragments`. Sending a non-`None` hybrid knob with any generator other than `"hybrid"` SHALL raise a `ValueError`.

#### Scenario: Auto values resolved from severity
- **WHEN** `generate_hybrid_crack_paths` runs at $S = 0.5$ with all knobs at `auto`
- **THEN** `parameters["hybrid"]` reports `through_count = 2`, `hairline_count = 5`, `hairline_reach = 0.6`, and a shard-tier `tilt_deg` of 20

#### Scenario: Explicit knob override echoed
- **WHEN** a caller supplies `through_count`, `through_shape`, `tilt_deg`, `hairline_count`, `hairline_reach` or `roughness`
- **THEN** the supplied value is validated against its range, used by generation, and echoed in `parameters["hybrid"]`

#### Scenario: Hybrid knobs rejected for other generators
- **WHEN** a non-`None` hybrid knob is passed with `generator="growth"`, `"shard"` or `"voronoi"`
- **THEN** the system raises a `ValueError` instead of silently ignoring the knob
