## Source material

- **2026-11-07, Project Lead**: "I don't need super precise accuracy on 100% of objects right now since this is just mostly a prototype. However I do care a lot about the visual accuracy and aesthetics... I find the gold seams, lightning-like cracks in conventional objects very aesthetically pleasing... prioritize aesthetics over 100% accuracy of crack generation."
- **2026-11-07, Agent 1 Review (Round 1)**: "In a Voronoi diagram every junction is a Y-junction and every crack is a cell boundary. That's the honeycomb look, and no amount of noise turns it into fracture. What I'd build is sequential crack growth with stop-on-hit... Check every new segment against all existing segments, including their copies one circumference to either side. When a crack hits another crack, it stops there and the hit point becomes a shared junction."
- **2026-11-07, Agent 2 Review (Round 1)**: "The F18 fix flattened the cracks: The cap is always hit, so the noise amplitude is now a flat 1.35 mm for every vessel and severity... the cracks are now almost straight Voronoi polygon edges with about one seam-width of wiggle, closer to a polygon tiling than to fractured ceramic... I'd prototype a cylindrical branching process with recursive jaggedness first."
- **2026-11-07, Agent 1 & 2 Review (Round 2)**: "A zero-depth groove is the kissing bug again... At d = 0 the sphere sits outside the vessel touching at a single point... drop any point below minimum depth (d < 0.25 mm) from the cutter... Define the clearance trigger radius as W + 0.8 mm and provide an exemption zone for parent branches... Reconcile TDD task order so hard invariants are scaffolded first."

### Raised but not acted on

- **Dijkstra Shortest Path on Mesh Graph**: Proposed as a graph search alternative. Deliberately rejected because it requires adding `networkx` (violating standing no-new-dependencies rule), and paths staircase along coarse facet edges depending on triangle resolution.
- **Unconstrained Midpoint Displacement**: Proposed as fractal curve generator. Deliberately rejected because midpoint displacement of individual curves does not check or prevent separate branches from colliding and self-crossing.
- **Voronoi in the Web GUI**: Considered exposing a legacy Voronoi dropdown in the GUI. Deliberately rejected: Voronoi is retained strictly as an internal CLI/test flag (`--generator voronoi`) during transition, not as a permanent user-facing product surface.

## Glossary

| Term | Means | Does NOT mean |
| :--- | :--- | :--- |
| **Sequential Crack Growth** | Iterative segment propagation in unrolled $(\theta, z)$ space from rim impact seeds downward. | A static tessellation or space-partitioning grid. |
| **Stop-on-Hit** | Snapping a candidate segment to the earliest collision point on an existing segment, splitting the hit segment with a new shared vertex. | Merely stopping nearby without a shared vertex (which risks kissing edges). |
| **Junction Exemption Zone** | A local circular radius $R_{\text{exempt}} = \frac{W + 0.8\text{ mm}}{\sin \theta}$ around a branch origin or T-junction where proximity checks against the parent/incident segments are ignored. | An unconstrained region where cracks can freely cross. |
| **T-Junction** | A three-way intersection where a propagating crack terminates into an existing crack line, with the existing line meeting at $\ge 140^\circ$ and the arriving segment meeting at $\ge 30^\circ$. | A trivalent Voronoi Y-junction where three cell boundaries meet. |
| **Vein Inlay Mode** | Carving surface channels leaving $\ge 0.8\text{ mm}$ ceramic backing, omitting cutter points where $d < 0.25\text{ mm}$ to prevent tangent contact. | Letting groove depth fade to zero and creating tangent non-manifold edges. |
| **Tortuosity** | The ratio of curve arc length to end-to-end chord length ($\frac{L}{\|\mathbf{p}_b - \mathbf{p}_a\|}$), measured per junction-to-junction segment. | An abstract box-counting fractal dimension estimation. |

## External research

| Source | What it establishes | Licence | Accessed |
| :--- | :--- | :--- | :--- |
| [Prusa Knowledge Base: Spiral Vase](https://help.prusa3d.com/article/layers-and-perimeters_1748?product=cw1) | Single-perimeter continuous extrusion toolpath; multi-material toolhead switching is not standard in spiral vase mode. | Public Documentation | 2026-11-07 |
| [Prusa Knowledge Base: Multi-Material 3MF](https://help.prusa3d.com/article/importing-multi-material-model_121191?product=mmu1) | 3MF files containing multiple objects/components map to separate extruder assignments. | Public Documentation | 2026-11-07 |
| Discrete Crack Growth in Brittle Solids | Physical fracture exhibits progressive propagation, dendritic branching, and arrest at existing boundaries (T-junctions). | Academic domain knowledge | 2026-11-07 |

## Candidate tech

| Option | Decision | Reason | Date |
| :--- | :--- | :--- | :--- |
| SciPy Voronoi + Sine Noise Field | Superseded | Inherently produces trivalent honeycomb cell boundaries. While PATCH-01 achieved 0.0% folds on presets, bounding the noise flattened amplitude to 1.35 mm on presets, destroying organic crack character, and it carries a small-radius ($r_{bar} \le 12\text{ mm}$) Jacobian proof gap. | 2026-11-07 |
| NetworkX Mesh Graph Dijkstra | Rejected | Adds external dependency; staircases along facet edges of coarse meshes. | 2026-11-07 |
| Midpoint Displacement Alone | Rejected | Cannot prevent separate branches from crossing without global collision graph. | 2026-11-07 |
| Rim-Seeded Growth with Stop-on-Hit | Adopted | Guarantees zero crossings by construction; produces natural T-junctions, lightning morphology, and organic tortuosity. | 2026-11-07 |

## Patterns adopted

- **Cylindrical Unrolling with Periodic Seam Wrapping**: Evaluating segments in $(\theta, z)$ coordinates and checking collisions against virtual copies shifted by $\pm 2\pi\bar{r}$.
- **Drop-in Generator Seam**: Keeping `generate_crack_paths(params, rng) -> list[np.ndarray]` as the contract feeding `project_crack_paths` and `_build_vein_cutter`.
- **Cutter Depth Cutoff ($d \ge 0.25\text{ mm}$)**: Omission of sub-threshold cutter points to completely prevent tangent kissing-edge contact.
- **Aesthetic Floor Gating**: Measuring median tortuosity ($\ge 1.05$) to prevent regressions to straight lines, alongside visual contact sheet inspection.

## Verified facts

| Claim | Value | How verified | Date | Volatility |
| :--- | :--- | :--- | :--- | :--- |
| Voronoi produces honeycomb cell tiles | Resembles bathroom tile grout | Geometric inspection of 2D Voronoi polygons | 2026-11-07 | stable |
| PATCH-01 noise amplitude cap | 1.35 mm on tested presets | Inspected `kintsugi.py:445` scaling logic | 2026-11-07 | stable |
| PATCH-01 preset sweeps | 0.0% folds, 0 crossings on presets | Tested audit and sweep runs | 2026-11-07 | stable |
| Voronoi small-radius fold gap | det(I+J) < 0 at $r_{bar} \le 12\text{ mm}$ | Measured by Agent 2 direct evaluation | 2026-11-07 | stable |
| Spiral vase slicer behavior | Single outline, incompatible with multi-material inlays | Verified against PrusaSlicer documentation | 2026-11-07 | stable |

## Unverified assumptions

| Assumption | Confidence | Cost to check |
| :--- | :--- | :--- |
| Random-walk heading with step size $1.5W\text{–}3W$ and cutter subdivision $\le W/2$ does not trigger Manifold3D boolean crashes | High | Implement prototype spike and run Manifold3D CSG boolean sweep |
| Thin-wall printing with 0.8 mm remaining ceramic is physically leak-proof on standard FDM | Medium | Slicer toolpath preview and test print |

## Superseded claims

- **Superseded**: "Crack wiggles must come from a continuous 2D displacement field $\eta(u, z)$ applied to straight lines."
  - *Why wrong*: Coupling wiggle to a displacement vector field creates a Jacobian whose determinant folds whenever $|\nabla \eta| > 1.0$, linking jaggedness directly to crossings.
  - *Replacement*: Cracks are grown segment-by-segment with local random-walk angular deviations; tortuosity is generated along the path without perturbing the surrounding space.
- **Superseded**: "Spiral vase mode is compatible with dual-material 3MF inlays."
  - *Why wrong*: Spiral vase mode forbids retracts and extruder changes.
  - *Replacement*: Target standard thin-wall mode (2–3 perimeters) with vein inlays.
- **Superseded**: "Groove depth can fade continuously to 0.0 mm on thin walls."
  - *Why wrong*: Depth $d \to 0$ places cutter spheres tangent to the outer mesh surface, creating non-manifold kissing edges in Manifold3D CSG.
  - *Replacement*: Groove points with $d < 0.25\text{ mm}$ are omitted from cutter generation, terminating the channel cleanly.

## Links out

- [kintsugi-mesh-fracture Archive](file:///home/node/global-sandbox/projects/wax-robot/openspec/changes/archive/2026-11-07-kintsugi-mesh-fracture/)
- [Main Mesh Fracture Engine Spec](file:///home/node/global-sandbox/projects/wax-robot/openspec/specs/mesh-fracture-engine/spec.md)
- [Main Retro Web GUI Spec](file:///home/node/global-sandbox/projects/wax-robot/openspec/specs/retro-web-gui/spec.md)
