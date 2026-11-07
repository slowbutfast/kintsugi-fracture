## MODIFIED Requirements

### Requirement: Metric R validation and clamping
The system SHALL validate the input income ratio $R$ as a finite float and compute severity $S = 1.0 - \text{clip}(R, 0.0, 1.0)$. All fracture parameters SHALL be pure functions of $S$ and the validated mesh:

| Parameter | Definition |
| :--- | :--- |
| Seed count | $N(S) = \lfloor 2 + 8S \rfloor$ |
| Seam width | $W(S) = 0.8 + 1.4S$ mm (overridable via `seam_width`, which SHALL be rejected below $0.8$ mm) |
| Trauma band height | $H(S) = H_{mesh} \cdot (0.2 + 0.8S)$, centred on the bounding-box Z midpoint and clipped to the mesh Z extent |
| Ribbon depth | $D_i = t_i + 1.0$ mm, where $t_i$ is the local wall thickness at path point $i$ |
| Vein inlay depth | $d_i = \min(0.75\,W,\ 0.5\,t_i,\ \max(0.2,\ t_i - 0.8\text{ mm}))$ (ensuring at least $0.8\text{ mm}$ of ceramic wall backing is preserved) |

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
- **THEN** the vein cutter depth $d_i$ is clamped to $\le 1.2 - 0.8 = 0.4\text{ mm}$, preserving at least $0.8\text{ mm}$ of ceramic backing

### Requirement: Parameter-space crack generation
The system SHALL generate the crack network in an unrolled cylindrical parameter space $(u, z)$, where $u = \theta \cdot \bar r$ and $\bar r$ is the mean outer radius across the trauma band. Cracks SHALL be grown sequentially from rim-seeded impact points with stop-on-hit collision handling, and then projected onto the exterior surface by radial ray casting against the input `Manifold` (`Manifold.ray_cast`).

#### Scenario: Rim-seeded crack growth
- **WHEN** severity $S > 0$
- **THEN** system initiates $N(S)$ primary crack trunks at random angular locations along the upper rim at $z \ge \text{wall\_z\_max}$ and grows them downwards into the trauma band taking discrete steps $\ge W/2$ with random-walk heading changes

#### Scenario: Stop-on-hit collision into T-junctions
- **WHEN** a growing crack segment approaches within distance $W$ of any existing crack segment (including virtual periodic copies shifted by $\pm 2\pi\bar r$)
- **THEN** the advancing segment stops at the intersection point, terminating growth and creating a shared T-junction vertex with zero crossing paths

#### Scenario: Secondary dendritic branching
- **WHEN** a crack trunk propagates through the trauma band
- **THEN** it spawns child branches with probability proportional to severity $S$, departing at acute branching angles between $30^\circ$ and $45^\circ$ to prevent razor-thin ceramic wedges

#### Scenario: Shipped crack graph is planar
- **WHEN** crack paths are generated under either generator option
- **THEN** no two path segments intersect except at shared junction vertices across all seeds and severities; stop-on-hit guarantees planarity by construction

#### Scenario: Radial projection takes the exterior hit and records wall thickness
- **WHEN** a parameter-space point $(u, z)$ is projected
- **THEN** system casts a ray from the axis at height $z$ outward along $\theta = u / \bar r$, takes the **farthest** hit as the exterior surface point $p_i$ with outward normal $n_i$, and records local wall thickness $t_i$ as the distance from $p_i$ to the preceding hit along the ray

#### Scenario: Ray miss
- **WHEN** a projection ray returns no hits
- **THEN** that path point is dropped and the path is split at that point; only misses whose $z$ lies inside the trauma band $[z_{min}, z_{max}]$ count towards the $5\%$ envelope, and the input-envelope `ValueError` is raised only when that in-band fraction exceeds $5\%$

#### Scenario: Perturbed points are truncated at the wall
- **WHEN** a polyline leaves the wall range
- **THEN** it is cut where $z$ leaves $[z_{wall,lo} + W/2,\ z_{wall,hi} + W/2]$: the crossing point is interpolated exactly, outside parts are discarded, and kept pieces have at least two points and length $\ge W$
