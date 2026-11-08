## ADDED Requirements

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
