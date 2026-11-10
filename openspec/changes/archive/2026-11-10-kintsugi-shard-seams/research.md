## Source material

- **2026-11-08, Project Lead**: "What if instead of trying to sort of deterministically evaluate the object and try to create the fractures based on some calculation, what if we try to approximate the fractures by creating like one or two planes that are a little offset from level that slice through whatever object we're trying to make, and then we use those two planes to divide the object into two or three different objects, and then we try to stitch them together, but then as we stitch them together, we add some like cracks and veins and whatnot to make the fractures like a little more rugged and more random looking, and then with those new sort of shapes as we combine the two or three pieces of the original object together, we can take those like seams and then use those seams as the inlay points for the sort of gold fractures if that makes sense."
- **2026-11-08, Project Lead**: "since this is a prototype, I'm OK with simplifying the problem in the sense of making the inputs for this algorithm a little more constrained so that we don't have to overgeneralize this fracture-generating algorithm. and by that i mean that if it only works on pretty basic geometries, that's OK too."
- **2026-11-08, Agent 1 Initial Plan**: "One simplification: we don't need to actually split and restitch the mesh. If you cut M into pieces and union them back, you get M again. The only thing that carries over is the line where the roughened cut surface meets the outside of the wall. So we generate that line directly and skip the meshes. For a roughly round wall, the cut line in that map is just $z(u) = z_0 + \bar{r} \cdot \tan\alpha \cdot \cos(u/\bar{r} - \phi)$. Add noise on top and it plugs into the existing `generate_crack_paths` hook as `generator='shard'`."
- **2026-11-08, Agent 2 Initial Review**: "This is a promising visual generator experiment, especially as an opt-in comparison against rim growth. Distinguish shard-like seam layout from actual ceramic shards. Surface inlay curves don't split the vessel's solid interior; '2–4 macroscopic shards' should describe the visual regions the seams imply... Keep `growth` as the default and make `shard` a generator-only spike."
- **2026-11-08, Agent 1 & Agent 2 Follow-Up Review**:
  - Reconcile $R$ vs $S$ semantics: In this engine, $R \in [0, 1]$ is the inequality reserve metric and $S = 1 - \text{clip}(R, 0, 1)$ is severity/damage. $R = 0$ is the most broken vessel ($S = 1.0$), while $R \ge 1.0$ is the untouched wealthy case ($S = 0$) with 0 seams. As $R$ decreases (or $S$ increases), roughness and seam count increase.
  - Fit generator signature to the pipeline: `generate_crack_paths(params, rng, *, subdivide_step=None, generator="growth")` dispatches using a `params` dict and an `rng`. Top-level caller is `generate_kintsugi_mesh(...)`. Retain `"voronoi"` alongside `"growth"` and `"shard"`.
  - Fix loop closure via linear drift bridge ($kink_i = w_i - \frac{i}{N - 1}(w_{N-1} - w_0)$) and cap loop vertical amplitude before generation so steep tilts on short walls fall back to wedges rather than flattening into horizontal stripes.
  - Record `_growth_junctions` metadata in `params["_growth_junctions"]` for any inserted T-junction so `analyze_growth_paths` applies the exemption radius $r_{\text{exempt}} = 1.10 r_{\text{clear}} / \sin 30^\circ$ and avoids false clearance failures.
  - Tortuosity floor is $\ge 1.05$ (matching existing growth engine floor), measured in 2D $(u, z)$ space across quadrant sub-arcs.
  - API endpoint `POST /api/fracture` accepts `generator="shard"` in `mode="vein"`, and returns HTTP 400 if invoked with `mode="ribbon"`.

### Raised but not acted on

- **3D Boolean Mesh Slicing & Re-stitching**: Considered physically cutting the input `Manifold` with 3D planes, roughening the interior cut faces, and unioning the pieces back together. Deliberately rejected because unioning complementary halves is a geometric identity on the solid body ($M_1 \cup M_2 = M$) and only the exterior seam curve survives in `vein` mode, while extra 3D CSG passes would introduce coplanar and kissing-face risks.
- **Secondary Hairline Branches & 3rd Plane Cascade in Stage 1**: Deferred out of the initial spike. The spike first proves the visual quality and geometric invariants of the two primary seam primitives (open rim-to-rim wedge and closed tilted loop) plus a verified 2-seam T-junction on the side-by-side contact sheet.
- **Through-Wall Ribbon Mode for Closed Loops**: A closed circumferential loop in `ribbon` mode would sever the ceramic vessel into two disconnected solid components held together only by gold. Stage 1 scopes `generator="shard"` to `mode="vein"` (surface inlay grooves) and raises `ValueError` if paired with `mode="ribbon"`.

## Glossary

| Term | Means | Does NOT mean |
| :--- | :--- | :--- |
| **Vessel Reserve ($R$) & Severity ($S$)** | $R \in [0, 1]$ measures reserve (inequality); $S = 1 - \text{clip}(R, 0, 1)$ measures fracture severity. $R=0 \implies S=1.0$ (most damaged); $R \ge 1.0 \implies S=0$ (untouched, 0 seams). | $R$ as "roughness". Roughness increases as $S$ increases ($R$ decreases). |
| **Shard-Like Seam Layout** | Surface inlay curves in `(u, z)` that visually partition the exterior vessel wall into 2–3 macroscopic shard-shaped regions while leaving the ceramic body a single solid manifold. | Physically severing the 3D ceramic mesh into disconnected multi-body shards. |
| **Cylindrical Plane-Inspired Curve** | A curve in unrolled `(u, z)` space following $z_{\text{base}}(u) = z_0 + \bar{r}\tan(\alpha)\cos(u/\bar{r} - \phi)$ plus multi-scale roughness, radially projected onto the vessel exterior. | The exact Euclidean 3D intersection of a flat plane with a non-cylindrical (flared or tapered) surface. |
| **Closed Tilted Loop Seam** | A $360^\circ$ periodic curve ($u \in [0, P]$ with $z(0) = z(P)$) generated by a shallowly tilted plane whose full vertical swing stays strictly inside the vessel wall range. | A flat horizontal ring or an open curve with a gap at $u = 0 \equiv P$. |
| **Open Rim-to-Rim Wedge Seam** | A steeply tilted plane curve that enters the upper rim ($z = \text{wall\_z\_max} + 0.35W$), dips into the wall range to a nadir $z_{\text{nadir}}$, and exits back out the upper rim, truncated exactly at the wall boundaries. | A curve clamped horizontally along the rim via `np.clip`. |
| **Quadrant Sub-Arc Tortuosity** | For a closed periodic loop, the arc-to-chord ratio in 2D $(u, z)$ space measured across 4 equal unwrapped quarter-circumference sub-arcs ($\Delta u = P / 4$). | Whole-loop arc length divided by zero 3D chord or inflated unrolled chord. |

## External research

| Source | What it establishes | Licence | Accessed |
| :--- | :--- | :--- | :--- |
| Plane–Cylinder Intersection (Dandelin / Analytic Geometry) | A plane with tilt angle $\alpha$ from horizontal and azimuth $\phi$ intersects a right circular cylinder of radius $\bar{r}$ in an ellipse whose unrolled cylindrical equation is the sinusoid $z(\theta) = z_0 + \bar{r}\tan(\alpha)\cos(\theta - \phi)$. | Classical Mathematics | 2026-11-08 |
| Traditional Kintsugi Craft (Yobitsugi / Hibi) | Classic ceramic drop fractures break a vessel into 2–4 macroscopic shards bounded by sweeping rim-to-rim wedges or circumferential body splits joining at T-junctions. | Craft Domain Knowledge | 2026-11-08 |

## Candidate tech

| Option | Decision | Reason | Date |
| :--- | :--- | :--- | :--- |
| 3D Mesh Plane Splitting + Boolean Reassembly | Rejected | Redundant for surface vein inlay; introduces coplanar face and sliver hazards. | 2026-11-08 |
| `np.clip` Vertical Bounding on Plane Curves | Rejected | Flattens out-of-range excursions into horizontal straight segments along the rim or base (recreating defect F15a). | 2026-11-08 |
| Cylindrical Plane-Inspired Curves + `_truncate_polyline_z` + Verified 1st Intersection | Adopted | Guarantees exact boundary interpolation, periodic closure, zero crossings, and authentic macroscopic shard silhouettes while reusing the existing projection and CSG pipeline. | 2026-11-08 |

## Patterns adopted

- **Exact Boundary Truncation (`_truncate_polyline_z`)**: Reusing `kintsugi.py:775` so open wedge curves crossing `wall_z_max + 0.35W` or `wall_z_min + 0.5W` are linearly interpolated at the exact crossing point without horizontal clamping.
- **Linear Drift Bridge for Loop Closure**: Computing cumulative walk $w_i = \sum_{j=0}^i \delta_j$ and subtracting linear error $kink_i = w_i - \frac{i}{N-1}(w_{N-1} - w_0)$ to enforce $kink_0 == kink_{N-1}$ without distorting walk statistics.
- **Height-Capped Amplitude Allocation**: Bounding $A_{\text{tilt}} + \sum A_k + \text{kink\_bound} \le (\Delta z_{\text{wall}} - 1.2W)/2$ before sampling; falling back to Primitive A (wedge) if available height forces $\alpha < 5^\circ$.
- **Junction Metadata Recording (`params["_growth_junctions"]`)**: Registering inserted T-junctions so `analyze_growth_paths` applies exemption zone $r_{\text{exempt}} = 1.10 r_{\text{clear}} / \sin 30^\circ$, avoiding false clearance failures.
- **Cyclic Adjacency in Graph Audit (`analyze_growth_paths`)**: Accounting for periodic wrap-around index distance `min(|i - j|, N_seg - |i - j|)` on closed loops so adjacent segments meeting at $u = 0 \equiv P$ are not miscounted as clearance violations.

## Verified facts

| Claim | Value | How verified | Date | Volatility |
| :--- | :--- | :--- | :--- | :--- |
| `generate_crack_paths` dispatcher seam | `kintsugi.py:2089` accepts `generator` keyword, takes `params` and `rng`, and returns `list[np.ndarray]` | Direct inspection of `kintsugi.py:2089-2106` | 2026-11-08 | stable |
| `generate_kintsugi_mesh` generator validation | `kintsugi.py:3020` accepts `("growth", "voronoi")` and forwards `generator` | Direct inspection of `kintsugi.py:3018-3022` | 2026-11-08 | stable |
| `analyze_growth_paths` same-path skip logic | `kintsugi.py:1996-2002` checks `abs(first["index"] - second["index"]) <= skip_span` linearly without cyclic modulo | Direct inspection of `kintsugi.py:1996-2002` | 2026-11-08 | stable |
| `analyze_growth_paths` junction exemption | `kintsugi.py:1963-1967, 2024-2033` uses `params["_growth_junctions"]` to exempt contacts within $r_{\text{exempt}} = 1.10 r_{\text{clear}} / \sin 30^\circ$ | Direct inspection of `kintsugi.py:1950-2035` | 2026-11-08 | stable |
| `_tortuosity_values` closed-loop behavior | `kintsugi.py:1912-1947` unrolls `u` into 2D $(u, z)$ and skips pieces with chord $< 10^{-9}$ | Direct inspection of `kintsugi.py:1912-1947` | 2026-11-08 | stable |
| Ceramic envelope backing guarantee | $p_5 \ge 1.6\text{ mm}$ inward-normal wall thickness preserves $t_i - d_i \ge 0.5\,t_i$ everywhere and $\ge 0.8\text{ mm}$ wherever $t_i \ge 1.6\text{ mm}$ | Verified in `ceramic-vessel-wall-envelope` (`c55356a`) | 2026-11-08 | stable |

## Unverified assumptions

| Assumption | Confidence | Verification Plan |
| :--- | :--- | :--- |
| Visual read of cylindrical plane-inspired curves on flared `tea_bowl` and tapered `vase` | High | Render 12-case side-by-side contact sheet (`growth` vs `shard`) via `tools/spike_contact_sheet.py` and inspect visually. |
| Severity-to-parameter table yields sub-arc tortuosity $\ge 1.05$ across seeds | High | Verify empirically across 50 seeds in `tests/test_crack_shard.py`. |

## Superseded claims

| Superseded Claim | What Replaced It | Reason |
| :--- | :--- | :--- |
| "R is roughness and R=0 is smooth baseline" | "R is reserve, S = 1 - R is severity; R=0 (S=1.0) is the most broken/rugged stoneware vessel, and R>=1.0 (S=0) is untouched" | Corrected R vs S semantics in accordance with existing engine definition. |
| "generate_shard_crack_paths takes mesh, severity, roughness, seed" | "generate_shard_crack_paths takes params, rng, *, subdivide_step=None" | Standardizes signature to match generate_crack_paths dispatcher in kintsugi.py:2089. |
| "Two non-touching closed loops must look like horizontal barrel rings" | "A tilted plane already makes a height-varying closed loop; both non-touching loops and intersecting wedge/loop seams are valid visual options" | Agent 2 review correction: tilt angle $\alpha$ creates vertical undulation even without intersections. |
| "Single-valued $z(u)$ plus `np.clip` prevents all crossings and keeps curves in bounds" | "Single-valued $z(u)$ prevents self-crossing of one curve; cross-seam collisions require verified intersection check and boundary clipping requires `_truncate_polyline_z`" | `np.clip` creates horizontal flat segments, and distinct curves can cross unless explicitly checked and truncated. |

## Links out

- [shard_plane_fracture_plan.md](file:///home/node/.gemini/antigravity-cli/brain/faa7bdb1-6652-4211-a0bc-d2e552084921/shard_plane_fracture_plan.md) - Technical design and Stage 1 spike specification.