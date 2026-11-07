## ADDED Requirements

### Requirement: Supported input envelope
The system SHALL accept only inputs inside a declared envelope and SHALL reject everything else with a `ValueError` rather than producing degraded geometry. The envelope is: a closed, orientable 2-manifold triangle mesh; units of millimetres; +Z up; all bounding-box extents within $[20, 300]\text{ mm}$; and a radially star-shaped exterior within the trauma band, meaning every radial ray cast from the vertical axis through the bounding-box XY centre, at any $z$ in the trauma band, hits the outer surface.

#### Scenario: Vessel of revolution inside the envelope
- **WHEN** a watertight tea bowl STL with extents $90 \times 90 \times 60\text{ mm}$ is loaded
- **THEN** the system accepts it and proceeds to crack generation

#### Scenario: Wrong units or scale
- **WHEN** a mesh with any bounding-box extent outside $[20, 300]\text{ mm}$ is loaded (e.g. a model authored in metres, extents $0.09$)
- **THEN** the system raises a `ValueError` naming the offending extent and the expected millimetre range

#### Scenario: Non-vessel geometry
- **WHEN** more than $5\%$ of the radial probe rays in the trauma band miss the mesh (e.g. a Benchy, or a mesh far off the Z axis)
- **THEN** the system raises a `ValueError` stating that the input is not a vessel the cylindrical parameterisation supports

### Requirement: Metric R validation and clamping
The system SHALL validate the input income ratio $R$ as a finite float and compute severity $S = 1.0 - \text{clip}(R, 0.0, 1.0)$. All fracture parameters SHALL be pure functions of $S$ and the validated mesh:

| Parameter | Definition |
| :--- | :--- |
| Seed count | $N(S) = \lfloor 2 + 8S \rfloor$ |
| Seam width | $W(S) = 0.8 + 1.4S$ mm (overridable via `seam_width`, which SHALL be rejected below $0.8$ mm) |
| Trauma band height | $H(S) = H_{mesh} \cdot (0.2 + 0.8S)$, centred on the bounding-box Z midpoint and clipped to the mesh Z extent |
| Ribbon depth | $D_i = t_i + 1.0$ mm, where $t_i$ is the local wall thickness at path point $i$ (see crack generation) |
| Vein inlay depth | $d_i = \min(0.75\,W,\ 0.5\,t_i)$ |

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

### Requirement: Watertight input mesh validation
The system SHALL validate the input mesh before any branching on $R$, including the wealthy pass-through, and SHALL construct exactly one `manifold3d.Manifold` from it using `Mesh64` (float64) so no precision is lost in conversion. Repair SHALL be limited to lossless clean-up (merging duplicate vertices, removing degenerate faces, making winding consistent); the system SHALL NOT fill holes or otherwise invent geometry.

#### Scenario: Pristine manifold STL loaded
- **WHEN** a valid watertight STL file is loaded
- **THEN** system merges duplicate vertices, fixes winding, builds a `manifold3d.Manifold` from `Mesh64`, and verifies `status() == Error.NoError` and `volume() > 0`

#### Scenario: Non-manifold or open input
- **WHEN** a mesh with boundary edges, non-manifold edges, or non-positive volume is loaded, at any value of $R$
- **THEN** system raises a `ValueError` indicating the input mesh is not a valid closed solid, and writes no output files

### Requirement: Parameter-space crack generation
The system SHALL generate the crack network in an unrolled cylindrical parameter space $(u, z)$, where $u = \theta \cdot \bar r$ and $\bar r$ is the mean outer radius across the trauma band, so that distances in parameter space approximate arc length on the vessel. Crack paths SHALL then be projected onto the exterior surface by radial ray casting against the input `Manifold` (`Manifold.ray_cast`).

#### Scenario: Periodic Voronoi network
- **WHEN** severity $S > 0$
- **THEN** system draws $N(S)$ seeds uniformly in $[0, 2\pi\bar r) \times Z_{trauma}$, tiles them at $u \pm 2\pi\bar r$, computes `scipy.spatial.Voronoi` on the tiled set, and keeps only ridges (finite or unbounded) with at least one seed in the central tile. Finite ridges are shifted by $\pm 2\pi\bar r$ to recover seam-crossing fragments, and endpoints that coincide modulo $2\pi\bar r$ are merged so junctions are shared vertices. Every emitted point lies on the periodic Voronoi diagram of the seeds before the noise field is applied

#### Scenario: Band-edge terminations are not flat
- **WHEN** a ridge is cut at the top or bottom of the trauma band
- **THEN** each terminal is moved **along its ridge** by clipping the raw ridge at a per-terminal limit $z_{edge} + \delta$, with $\delta \sim U(-0.1H, +0.1H)$, so crack ends do not line up on a horizontal line. If the ridge's finite Voronoi vertex is reached first, the terminal stops at that vertex

#### Scenario: Crack graph is planar
- **WHEN** the noise field is zero
- **THEN** no two path segments intersect except at shared endpoints, for both presets at $S \in \{0.6, 1.0\}$; every stage except noise (tiling, filtering, clipping, ridge-aligned jitter and wall truncation) keeps points on the true periodic Voronoi diagram

#### Scenario: Noise perturbation keeps junctions connected and seamless
- **WHEN** ridge polylines are perturbed
- **THEN** each ridge is first subdivided to a parameter-space step of at most $W/2$, then displaced by a deterministic noise field $\eta(u, z)$ built from $K = 4$ dyadic octaves (frequency $\propto 2^k$, amplitude $\propto 2^{-k}$, base amplitude $0.15\times$ mean seed spacing). Every angular frequency is an integer multiple of $1/\bar r$ so the field is periodic in $\theta$, and the field depends only on position, so shared junction vertices receive identical displacement

#### Scenario: Radial projection takes the exterior hit and records wall thickness
- **WHEN** a parameter-space point $(u, z)$ is projected
- **THEN** system casts a ray from the axis at height $z$ outward along $\theta = u / \bar r$, takes the **farthest** hit as the exterior surface point $p_i$ with outward normal $n_i$, and records local wall thickness $t_i$ as the distance from $p_i$ to the preceding hit along the ray

#### Scenario: Ray miss
- **WHEN** a projection ray returns no hits
- **THEN** that path point is dropped and the path is split at that point; only misses whose $z$ lies inside the trauma band $[z_{min}, z_{max}]$ count towards the $5\%$ envelope, and the input-envelope `ValueError` is raised only when that in-band fraction exceeds $5\%$

#### Scenario: Unbounded ridges are rays
- **WHEN** a Voronoi ridge is unbounded
- **THEN** it is represented as a single ray starting at the finite Voronoi vertex, with exactly one periodic representative. Its direction is chosen by the Voronoi distance definition: a point just along the ray must be closer to the ridge's two seeds than to any other seed. In the degenerate tie case, the direction points away from the third Delaunay seed's side of edge $ab$, i.e. $\mathrm{dot}(direction, c - \mathrm{midpoint}(a,b)) < 0$

#### Scenario: Perturbed points are truncated at the wall
- **WHEN** the noisy polyline leaves the wall range
- **THEN** it is cut where $z$ leaves
  $[z_{wall,lo} + W/2,\ z_{wall,hi} - W/2]$: the crossing point is
  interpolated exactly, outside parts are discarded, and a polyline that
  leaves and re-enters becomes several paths. No point is projected onto a
  horizontal limit line; a kept piece has at least two points and length $W$

#### Scenario: Junction ends are never jittered
- **WHEN** a band terminal is moved
- **THEN** it moves along its own ridge only; interior Voronoi vertices are not displaced, so shared junctions remain connected

#### Scenario: Single-hit wall thickness
- **WHEN** a radial projection ray has exactly one hit because its origin lies inside the solid base
- **THEN** the local wall thickness $t_i$ is the median two-hit wall thickness of its own path, falling back to the global median two-hit thickness, and the number of such points is recorded for diagnostics

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
