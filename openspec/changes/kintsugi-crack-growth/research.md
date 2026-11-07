## Source material

- **2026-11-07, Project Lead**: "I don't need super precise accuracy on 100% of objects right now since this is just mostly a prototype. However I do care a lot about the visual accuracy and aesthetics... I find the gold seams, lightning-like cracks in conventional objects very aesthetically pleasing... prioritize aesthetics over 100% accuracy of crack generation."
- **2026-11-07, Agent 1 Review**: "In a Voronoi diagram every junction is a Y with roughly 120° between branches, and every crack is a cell boundary. That's the honeycomb look, and no amount of noise turns it into fracture. What I'd build is sequential crack growth with stop-on-hit... Check every new segment against all existing segments, including their copies one circumference to either side. When a crack hits another crack, it stops there and the hit point becomes a shared junction. That gives the T-junctions real ceramic shows."
- **2026-11-07, Agent 2 Review**: "The F18 fix flattened the cracks: The cap is always hit, so the noise amplitude is now a flat 1.35 mm for every vessel and severity... the cracks are now almost straight Voronoi polygon edges with about one seam-width of wiggle, closer to a polygon tiling than to fractured ceramic... I'd prototype a cylindrical branching process with recursive jaggedness first."

### Raised but not acted on

- **Dijkstra Shortest Path on Mesh Graph**: Proposed as a graph search alternative. Deliberately rejected because it requires adding `networkx` (violating standing no-new-dependencies rule), and paths staircase along coarse facet edges depending on triangle resolution.
- **Unconstrained Midpoint Displacement**: Proposed as fractal curve generator. Deliberately rejected because midpoint displacement of individual curves does not check or prevent separate branches from colliding and self-crossing.
- **Spiral Vase Mode Dual-Material Inlays**: Investigated for slicing. Deliberately set aside because true spiral vase mode in Bambu Studio / PrusaSlicer prints a single uninterrupted perimeter contour and rejects multi-material toolhead switching. The project targets thin-wall standard mode (2–3 perimeters) instead.

## Glossary

| Term | Means | Does NOT mean |
| :--- | :--- | :--- |
| **Sequential Crack Growth** | Iterative ray/segment propagation in unrolled $(\theta, z)$ space from rim impact seeds downward. | A static tessellation or space-partitioning grid. |
| **Stop-on-Hit** | Terminating a propagating crack segment at the point of collision with any existing segment, creating a T-junction. | Letting curves cross and attempting to resolve crossings in post-processing. |
| **T-Junction** | A three-way intersection where a propagating crack terminates perpendicular or acute to an existing crack line (characteristic of physical brittle fracture). | A Voronoi Y-junction where three edges meet at symmetric ~120° angles (characteristic of foam or soap bubbles). |
| **Vein Inlay Mode** | Carving shallow surface channels (depth $\le \text{wall} - 0.8\text{ mm}$) filled with gold without cutting through the vessel wall. | Through-body slicing that cuts the vessel into detached floating shards. |
| **Tortuosity** | The ratio of curve arc length to end-to-end chord length ($\frac{L}{\|\mathbf{p}_b - \mathbf{p}_a\|}$). | A topological fractal dimension estimation. |

## External research

| Source | What it establishes | Licence | Accessed |
| :--- | :--- | :--- | :--- |
| Prusa Knowledge Base: Spiral Vase | Single-perimeter continuous extrusion toolpath incompatible with multi-material toolhead switching. | Public Documentation | 2026-11-07 |
| Prusa Knowledge Base: Multi-Material 3MF | 3MF files containing multiple objects/components map to separate extruder assignments. | Public Documentation | 2026-11-07 |
| Discrete Crack Growth in Brittle Solids | Physical fracture exhibits progressive propagation, dendritic branching, and arrest at existing boundaries (T-junctions). | Academic domain knowledge | 2026-11-07 |

## Candidate tech

| Option | Decision | Reason | Date |
| :--- | :--- | :--- | :--- |
| SciPy Voronoi + Sine Noise Field | Superseded | Inherently produces 120° honeycomb tiles; bounding noise gradient to avoid folding (F18) collapses amplitude to 1.35 mm, flattening cracks. | 2026-11-07 |
| NetworkX Mesh Graph Dijkstra | Rejected | Adds external dependency; staircases along facet edges of coarse meshes. | 2026-11-07 |
| Midpoint Displacement Alone | Rejected | Cannot prevent separate branches from crossing without global collision graph. | 2026-11-07 |
| Rim-Seeded Growth with Stop-on-Hit | Adopted | Guarantees zero crossings by construction; produces natural T-junctions, lightning morphology, and organic tortuosity. | 2026-11-07 |

## Patterns adopted

- **Cylindrical Unrolling with Periodic Seam Wrapping**: Evaluating segments in $(\theta, z)$ coordinates and checking collisions against virtual copies shifted by $\pm 2\pi$. Retained from `kintsugi.py` seam wrapping logic.
- **Drop-in Generator Seam**: Keeping `generate_crack_paths(params, rng) -> list[np.ndarray]` as the contract feeding `project_crack_paths` and `_build_vein_cutter`.
- **Aesthetic Floor Gating**: Measuring median tortuosity ($\ge 1.05$) to prevent regressions to straight lines, while reserving aesthetic sign-off for human/multimodal contact sheets.

## Verified facts

| Claim | Value | How verified | Date | Volatility |
| :--- | :--- | :--- | :--- | :--- |
| Voronoi produces Y-junctions | 100% Y-junctions (~120°) | Mathematical definition of 2D Voronoi vertices | 2026-11-07 | stable |
| PATCH-01 noise amplitude cap | Flat 1.35 mm | Inspected `kintsugi.py:445` scaling logic | 2026-11-07 | stable |
| Unit test suite passing | 36/36 OK | Ran `.venv/bin/python -m unittest discover -s tests -v` | 2026-11-07 | stable |
| Spiral vase slicer behavior | Single outline, no multi-material | Verified against PrusaSlicer / Bambu Studio docs | 2026-11-07 | stable |

## Unverified assumptions

| Assumption | Confidence | Cost to check |
| :--- | :--- | :--- |
| Random-walk heading with step size $\ge W/2$ does not trigger Manifold3D boolean crashes | High | Implement prototype spike and run Manifold3D CSG boolean sweep |
| Thin-wall printing with 0.8 mm remaining ceramic is physically leak-proof on standard FDM | Medium | Physical slicer and test print |

## Superseded claims

- **Superseded**: "Crack wiggles must come from a continuous 2D displacement field $\eta(u, z)$ applied to straight lines."
  - *Why wrong*: Coupling wiggle to a displacement vector field creates a Jacobian whose determinant folds whenever $|\nabla \eta| > 1.0$, linking jaggedness directly to crossings.
  - *Replacement*: Cracks are grown segment-by-segment with local random-walk angular deviations; tortuosity is generated along the path without perturbing the surrounding space.
- **Superseded**: "Spiral vase mode is compatible with dual-material 3MF inlays."
  - *Why wrong*: Spiral vase mode forbids retracts and extruder changes.
  - *Replacement*: Target standard thin-wall mode (2–3 perimeters) with vein inlays.

## Links out

- [kintsugi-mesh-fracture Archive](file:///home/node/global-sandbox/projects/wax-robot/openspec/changes/archive/2026-11-07-kintsugi-mesh-fracture/)
- [Main Mesh Fracture Engine Spec](file:///home/node/global-sandbox/projects/wax-robot/openspec/specs/mesh-fracture-engine/spec.md)
- [Main Retro Web GUI Spec](file:///home/node/global-sandbox/projects/wax-robot/openspec/specs/retro-web-gui/spec.md)
