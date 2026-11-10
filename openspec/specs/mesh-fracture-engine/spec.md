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

### Requirement: 3MF package input
The system SHALL load a `.3mf` input into one flattened millimetre mesh before the supported input envelope is checked. It SHALL use only the Python standard library (`zipfile`, `xml.etree`) plus the existing numpy/trimesh dependencies. The reader SHALL:

1. Locate the root model through the package relationship in `_rels/.rels` (`http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel`), falling back to `3D/3dmodel.model` when that relationship is absent.
2. Require exactly one `<build><item>`.
3. Resolve objects recursively from that item:
   - mesh objects contribute their `<vertices>` and `<triangles>`;
   - component objects contribute their referenced objects, each under its own `transform`;
   - a component with a Production-extension `p:path` SHALL resolve its `objectid` inside that package part, not by bare id across parts.
4. Compose transforms (component transforms nested inside the build-item transform). Each transform is a 3MF row-major 4×3 affine, with the translation in the last three values.
5. Convert coordinates to millimetres from the root model's `unit` attribute (`micron` 0.001, `millimeter` 1, `centimeter` 10, `inch` 25.4, `foot` 304.8, `meter` 1000; default `millimeter`).
6. Ignore materials, colours, textures, thumbnails and metadata.
7. Return a single `trimesh.Trimesh` with `process=False`, so no merging or repair happens before `_clean_mesh` runs inside validation.

The existing input envelope (closed solid, millimetre extents within [20, 300], vessel, wall thickness) SHALL then apply unchanged.

The reader SHALL treat the package as untrusted. It SHALL read each entry through a bounded read that stops at the entry's declared size (an honest entry never decompresses to more) and at the remaining decompressed-size budget of 512 MiB for the package, and SHALL NOT decompress an entry in full before checking its size. Any error the zip layer raises for a damaged or unsupported entry SHALL surface as a `ValueError`, never as another exception type, so that callers report an invalid model and not a server error.

The reader SHALL raise a `ValueError` naming the problem when:
- the file is not a ZIP;
- an entry is damaged: it fails its CRC, its compressed stream is corrupt, its header understates its real size, or it uses an unsupported compression method;
- the decompressed package exceeds the 512 MiB budget;
- no root model can be found;
- the build has zero or more than one item;
- a referenced object, part or `p:path` target is missing or points outside the package;
- any reachable object has a `type` other than `model`;
- the `unit` value is unknown;
- component nesting exceeds 16 levels or contains a cycle;
- no triangles are reachable;
- the package is our own Kintsugi assembly, meaning the reachable mesh objects are exactly those named `CeramicBody` and `GoldSeams`.

#### Scenario: Single-object core 3MF loads in millimetres
- **WHEN** a 3MF whose root model has `unit="millimeter"`, one build item, and one mesh object containing a closed bowl is passed to `validate_and_load_mesh`
- **THEN** the loaded mesh has the same vertex positions and face count as the source object, and validation proceeds exactly as for the equivalent STL

#### Scenario: Metre unit and transforms are applied
- **WHEN** a 3MF with `unit="meter"` places the bowl through a build-item transform (translation) and a component transform (rotation)
- **THEN** the flattened mesh equals the bowl with both transforms composed and coordinates multiplied by 1000, within 1e-6 mm

#### Scenario: Production-extension part resolved by path
- **WHEN** the root model's single object is a component with `p:path="/3D/Objects/object_1.model"` and `objectid="1"`, while the root model also defines an unrelated object with id `1`
- **THEN** the reader loads the mesh from `/3D/Objects/object_1.model`, not the root object with the same id

#### Scenario: Multiple build items rejected
- **WHEN** a 3MF has two build items
- **THEN** a `ValueError` states that only single-object 3MF files are supported and reports the item count

#### Scenario: Non-model object type rejected
- **WHEN** a reachable object has `type="support"` or `type="other"`
- **THEN** a `ValueError` names the object id and its type

#### Scenario: Kintsugi assembly rejected
- **WHEN** the input is a `kintsugi_assembly.3mf` produced by `export_kintsugi_3mf`
- **THEN** a `ValueError` states that the file is already a Kintsugi output and asks for the original model

#### Scenario: Malformed package rejected
- **WHEN** the input is not a ZIP, has no root model, references a missing object, uses an unknown unit, or contains a component cycle
- **THEN** a `ValueError` names the specific problem, and no partial mesh is returned

#### Scenario: Entry whose header understates its size
- **WHEN** a package of about 200 KB declares a 1,000-byte model part in its zip header but the part's compressed stream expands to 200 MiB
- **THEN** a `ValueError` states that the part is corrupt, and the reader decompresses only about the declared size (peak memory does not grow by the real size)

#### Scenario: Damaged or unsupported entry rejected as an invalid model
- **WHEN** a model part has a corrupt deflate stream, a wrong CRC, or an unsupported compression method
- **THEN** a `ValueError` names the part and says it is corrupt or unsupported, and `POST /api/validate` answers `valid: false` with that detail instead of an HTTP 500

#### Scenario: Honest oversized package rejected
- **WHEN** a package's parts really decompress to more than the 512 MiB budget
- **THEN** a `ValueError` states that the package is too large when uncompressed

