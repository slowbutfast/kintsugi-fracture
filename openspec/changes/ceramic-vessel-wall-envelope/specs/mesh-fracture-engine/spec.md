## MODIFIED Requirements

### Requirement: Supported input envelope
The system SHALL accept only inputs inside a declared envelope and SHALL reject everything else with a `ValueError` rather than producing degraded geometry. The envelope is: a closed, orientable 2-manifold triangle mesh; units of millimetres; +Z up; all bounding-box extents within $[20, 300]\text{ mm}$; a radially star-shaped exterior within the trauma band (meaning every radial ray cast from the vertical axis through the bounding-box XY centre, at any $z$ in the trauma band, hits the outer surface); and a 5th-percentile two-hit wall thickness $p_5 \ge 1.6\text{ mm}$ within the trauma band.

#### Scenario: Vessel of revolution inside the envelope
- **WHEN** a watertight tea bowl STL with extents $90 \times 90 \times 60\text{ mm}$ and wall thickness $\ge 2.0\text{ mm}$ is loaded
- **THEN** the system accepts it and proceeds to crack generation

#### Scenario: Vessel with wall thickness below ceramic envelope
- **WHEN** a mesh with 5th-percentile two-hit wall thickness $p_5 < 1.6\text{ mm}$ within the trauma band is loaded (e.g. `thin_cylinder` with wall thickness $0.7\text{--}1.2\text{ mm}$)
- **THEN** the system raises a `ValueError` stating the measured wall thickness $p_5$ and that input vessels must have $p_5 \ge 1.6\text{ mm}$ to guarantee safe ceramic backing

#### Scenario: Vessel at ceramic envelope boundary
- **WHEN** a mesh with 5th-percentile two-hit wall thickness $p_5 = 1.6\text{ mm}$ within the trauma band is loaded
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
| Seed count | $N(S) = \lfloor 2 + 8S \rfloor$ primary rim trunks |
| Seam width | $W(S) = 0.8 + 1.4S$ mm (overridable via `seam_width`, which SHALL be rejected below $0.8$ mm) |
| Trauma penetration depth | $H(S) = H_{wall} \cdot (0.2 + 0.8S)$, measured downwards from `wall_z_max` |
| Ribbon depth | $D_i = t_i + 1.0$ mm, where $t_i$ is the local wall thickness at path point $i$ |
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
- **WHEN** a vein inlay is carved on any valid vessel ($t_i \ge 1.6\text{ mm}$) with seam width $W = 1.0\text{ mm}$
- **THEN** vein cutter depth $d_i$ is $\min(0.75, 0.5t_i)$, preserving nominal ceramic backing $t_i - d_i \ge 0.5t_i \ge 0.8\text{ mm}$ without cutter point omissions

#### Scenario: Empty gold solid defensive safeguard
- **WHEN** an uncarved pass occurs ($R \ge 1.0$) or the complementary gold boolean has zero triangles
- **THEN** the system SHALL not write `gold_seams.stl`, SHALL omit `GoldSeams` from the 3MF container, SHALL unlink any stale gold STL from an earlier run, and SHALL return `gold_path: None`, `seams_omitted: true`, `num_cracks: 0`, `volumes.gold: 0.0`, and `triangle_counts.gold: 0`

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
