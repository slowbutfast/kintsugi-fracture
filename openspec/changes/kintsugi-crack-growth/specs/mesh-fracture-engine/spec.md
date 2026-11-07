## MODIFIED Requirements

### Requirement: Metric R validation and clamping
The system SHALL validate the input income ratio $R$ as a finite float and compute severity $S = 1.0 - \text{clip}(R, 0.0, 1.0)$. All fracture parameters SHALL be pure functions of $S$ and the validated mesh:

| Parameter | Definition |
| :--- | :--- |
| Seed count | $N(S) = \lfloor 2 + 8S \rfloor$ primary rim trunks |
| Seam width | $W(S) = 0.8 + 1.4S$ mm (overridable via `seam_width`, which SHALL be rejected below $0.8$ mm) |
| Trauma penetration depth | $H(S) = H_{wall} \cdot (0.2 + 0.8S)$, measured downwards from `wall_z_max` |
| Ribbon depth | $D_i = t_i + 1.0$ mm, where $t_i$ is the local wall thickness at path point $i$ |
| Vein inlay depth | $d_i = \min(0.75\,W,\ 0.5\,t_i,\ t_i - 0.8\text{ mm})$; cutter points with $d_i < 0.25\text{ mm}$ SHALL be omitted from cutter generation |

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

#### Scenario: Thin-wall ceramic clearance in vein mode
- **WHEN** a vein inlay is carved on a vessel with local wall thickness $t_i = 1.2\text{ mm}$ and seam width $W = 1.0\text{ mm}$
- **THEN** the vein cutter depth $d_i$ is clamped to $\min(0.75, 0.6, 0.4) = 0.4\text{ mm}$, preserving at least $0.8\text{ mm}$ of ceramic backing

#### Scenario: Sub-millimetre thin wall cutter omission
- **WHEN** local wall thickness at a path point is $t_i \le 1.0\text{ mm}$ yielding $d_i < 0.25\text{ mm}$ (e.g. $t_i = 0.9\text{ mm} \implies d_i = 0.1\text{ mm}$)
- **THEN** that path point is omitted from cutter solid generation, splitting the cutter polyline and terminating the channel cleanly without creating tangent non-manifold contact

### Requirement: Parameter-space crack generation
The system SHALL generate the crack network in an unrolled cylindrical parameter space $(u, z)$, where $u = \theta \cdot \bar r$ and $\bar r$ is the mean outer radius across the trauma band. Cracks SHALL be grown sequentially from rim-seeded impact points with stop-on-hit collision handling, and then projected onto the exterior surface by radial ray casting against the input `Manifold` (`Manifold.ray_cast`).

#### Scenario: Rim-seeded crack growth
- **WHEN** severity $S > 0$ and `--generator growth` is active
- **THEN** system initiates $N(S)$ primary crack trunks at angular locations along the upper rim at $z \ge \text{wall\_z\_max}$ spaced by minimum angular clearance $\Delta \theta \ge \frac{W + 1.5\text{ mm}}{\bar r}$ and propagates them downwards taking steps in $[1.5W, 3.0W]$ with random-walk heading constrained within $\pm 60^\circ$ of straight down

#### Scenario: Growth budgets and jittered penetration
- **WHEN** a crack trunk or branch advances
- **THEN** growth terminates when: (a) it hits an existing crack under stop-on-hit, (b) its current $z$ reaches below the per-trunk jittered penetration limit $z_{\text{limit}} = \text{wall\_z\_max} - H(S) \cdot (1 + \delta)$ with $\delta \sim U(-0.15, +0.15)$, or (c) its total arc length reaches its assigned length budget ($L_{\text{trunk}} = 1.2 \cdot H(S)$, $L_{\text{branch}} = 0.5 \cdot H(S)$)

#### Scenario: Stop-on-hit collision and first-hit snapping
- **WHEN** a candidate segment advancing from $\mathbf{p}_a$ toward $\mathbf{p}_b$ approaches within distance $R_{\text{clear}} = W + 0.8\text{ mm}$ of any committed segment (including virtual periodic copies shifted by $\pm 2\pi\bar r$, and earlier non-adjacent segments of the same crack)
- **THEN** the system identifies the earliest contact point $\mathbf{p}_{\text{hit}}$ along the travel vector; if the arrival incidence angle is $\ge 30^\circ$, the advancing end snaps to $\mathbf{p}_{\text{hit}}$, terminates growth, and subdivides the hit segment at $\mathbf{p}_{\text{hit}}$ so the vertex is explicitly shared by both polylines

#### Scenario: Grazing approach resolution
- **WHEN** an advancing segment approaches an existing segment within $R_{\text{clear}}$ at an arrival angle $< 30^\circ$
- **THEN** the system resamples the candidate heading up to 3 times to achieve an angle $\ge 30^\circ$; if all attempts fail, growth terminates at the previous committed point $\mathbf{p}_a$, leaving a free end with at least $W + 0.8\text{ mm}$ clearance

#### Scenario: Secondary dendritic branching and junction exemption
- **WHEN** a crack trunk propagates through the trauma band
- **THEN** it spawns a child branch with probability $0.15 \cdot S$ per step (maximum 1 level of branching) departing at an acute angle $[30^\circ, 45^\circ]$ toward the side with greater angular clearance within the $\pm 60^\circ$ cone; within a junction exemption radius $R_{\text{exempt}} = \frac{W + 0.8\text{ mm}}{\sin \theta_{\text{branch}}}$ of the branch origin, proximity checks against the parent segment are ignored

#### Scenario: Deterministic growth order
- **WHEN** multiple cracks grow
- **THEN** crack segments advance in deterministic order (FIFO queue in spawn order, one step per turn) with seeded random numbers, ensuring identical graph topology across repeated runs

#### Scenario: Shipped growth graph is planar
- **WHEN** crack paths are generated under the growth generator
- **THEN** no two path segments intersect except at shared junction vertices across all seeds and severities; stop-on-hit guarantees planarity by construction

#### Scenario: Radial projection takes the exterior hit and clamps rim overshoot
- **WHEN** a parameter-space point $(u, z)$ is projected
- **THEN** if $z \ge \text{wall\_z\_max}$, the ray is cast at $z = \text{wall\_z\_max} - 0.05\text{ mm}$ to guarantee hitting the exterior lip; otherwise the ray is cast from the axis at height $z$ outward along $\theta = u / \bar r$; the farthest hit is taken as exterior surface point $p_i$ with outward normal $n_i$, and local wall thickness $t_i$ is recorded as the distance to the preceding hit along the ray

#### Scenario: Ray miss
- **WHEN** a projection ray returns no hits
- **THEN** that path point is dropped and the path is split at that point; only misses whose $z$ lies inside the trauma band $[z_{\text{limit,min}}, \text{wall\_z\_max}]$ count towards the $5\%$ envelope, and the input-envelope `ValueError` is raised only when that in-band fraction exceeds $5\%$

#### Scenario: Perturbed points are truncated at the wall
- **WHEN** a polyline leaves the wall range
- **THEN** it is cut where $z$ leaves $[z_{wall,lo} + 0.5W,\ \text{wall\_z\_max} + 0.5W]$: the crossing point is interpolated exactly, outside parts are discarded, and kept pieces have at least two points and length $\ge W$
