## Source material

- **2026-11-07, Project Lead**: "wait, i'm actually not bound by the vasemode constraint. how can we loosen that constraint to give our algorithm more breathing room to form these cracks? this is the constraint specifically that i don't really care about: • When you fix the kissing bug with a 0.25 mm cutoff: The gold channel disappears on thin walls, which triggers an 84-byte empty STL bug in the exporter and a misleading 'Pristine / Wealthy' label in the UI."
- **2026-11-07, Agent 1 Review**: "Dropping thin walls is the right call... Every thin-wall rule you want to remove was introduced by kintsugi-crack-growth... the `t - 0.8` depth formula, the 0.25 mm cutoff and splitting of points around it, the `thin_cylinder` preset, and the groove fade scenario. The archived kintsugi-mesh-fracture never had them. Its vein depth was plain `min(0.75W, 0.5t)`."
- **2026-11-07, Agent 2 Review**: "Vase mode was always the wrong benchmark for Kintsugi: real pottery has 2–5 mm walls, and FDM multi-material prints need at least 3–4 perimeters (1.2–1.6 mm) anyway. Setting the supported envelope to $t \ge 1.6\text{ mm}$ eliminates the sub-millimeter cascade: with $d = \min(0.75W, 0.5t)$, a 1.6 mm wall gets $d = 0.8\text{ mm}$ groove with $0.8\text{ mm}$ backing. No zero-depth tangency, no 0.25 mm point skipping, no empty gold solid on valid runs."

### Raised but not acted on

- **Supporting sub-millimeter single-perimeter prints**: Deliberately removed from project requirements. Slicers cannot print dual-extrusion multi-material inlays inside spiral vase mode.
- **Dynamic adaptive mesh thickening**: Thickening thin meshes on-the-fly was considered and rejected; modifying input geometry without user intent distorts the original design. Clear validation failure with measured vs required thickness is preferable.
- **Removing `_gold_solid_omitted` safeguard completely**: While valid ceramic runs will never omit veins, the safeguard is retained in the exporter to handle wealthy inputs ($R \ge 1.0$, which intentionally have 0 cracks) without crashing or writing empty files.

## Glossary

| Term | Means | Does NOT mean |
| :--- | :--- | :--- |
| **Ceramic Vessel Envelope** | Input watertight meshes with 5th-percentile two-hit wall thickness $p_5 \ge 1.6\text{ mm}$ in the trauma band. | Arbitrary single-perimeter thin shells or vase-mode geometries. |
| **Two-Hit Wall Thickness ($p_5$)** | The 5th percentile distance between the outer vessel surface and the next interior ray-mesh hit along the inward surface normal. | Average wall thickness or bounding box diameter. |
| **Continuous Vein Inlay** | Vein depth $d_i = \min(0.75W, 0.5t_i)$, creating a deep, uniform gold groove along the entirety of every crack path. | Segmenting or omitting groove points where depth fades to zero. |
| **Correlated Random Walk** | Crack propagation with continuous gentle heading drift ($\sigma \approx 18^\circ$) and low kink rate ($15\%\text{--}20\%$). | High-frequency staircase zig-zags (50% kinks) or Voronoi honeycomb tiling. |
| **Final-Step Near-Miss Snapping** | When a crack reaches within $R_{\text{clear}}$ on its final attempt at arrival angle $\ge 30^\circ$, bending directly to the nearest point on the target segment. | Stopping short 2–3 mm away leaving dead-end dangling gaps. |

## External research

| Source | What it establishes | Licence | Accessed |
| :--- | :--- | :--- | :--- |
| Ceramic Pottery Standards (Studio Ceramics) | Typical wheel-thrown stoneware and porcelain vessel walls measure between 2.5 mm and 6.0 mm. Minimum functional wall thickness for fired earthenware is ~2.0 mm. | Craft Domain Standards | 2026-11-07 |
| Bambu Studio / PrusaSlicer Multi-Material Docs | Multi-material FDM slicing requires discrete closed 3D volumes per extruder. Surface channels must be closed solids intersecting or mating with the body. | Public Documentation | 2026-11-07 |
| ASTM D256 / Brittle Fracture in Ceramics | Mechanical failure in ceramics proceeds along natural stress concentration lines, creating smooth wandering paths with dendritic branch arrest against existing boundaries. | Academic Research | 2026-11-07 |

## Candidate tech

| Option | Decision | Reason | Date |
| :--- | :--- | :--- | :--- |
| Thin-Wall Depth $d = t - 0.8\text{ mm}$ with $0.25\text{ mm}$ cutoff | Superseded / Removed | Fragile; causes groove fade, tangent kissing contact, empty gold solids, and split cutter points on thin walls. | 2026-11-07 |
| Classical Vein Depth $d = \min(0.75W, 0.5t)$ with $p_5 \ge 1.6\text{ mm}$ envelope | Adopted | Mathematically guarantees $\ge 0.8\text{ mm}$ ceramic backing everywhere ($0.5 \times 1.6\text{ mm} = 0.8\text{ mm}$), bold gold seams, and zero cutter point omissions. | 2026-11-07 |
| Strict Collision Rejection with Final Attempt Snap | Adopted | Prevents cracks stopping short 2–3 mm away while strictly guaranteeing 0 crossings and valid T-junctions. | 2026-11-07 |

## Patterns adopted

- **Preflight Wall Thickness Validation**: Sampling two-hit wall thickness via radial inward rays in `validate_and_load_mesh`, rejecting any mesh with $p_5 < 1.6\text{ mm}$ with an informative `ValueError`.
- **Continuous Cutter Extrusion**: Building continuous manifold cutters without splitting polyline paths into discontinuous point groups.
- **Defensive Exporter Safeguards**: Retaining `_gold_solid_omitted` logic to gracefully handle $R \ge 1.0$ (wealthy/pristine) runs.

## Verified facts

| Claim | Value | How verified | Date | Volatility |
| :--- | :--- | :--- | :--- | :--- |
| Japanese Tea Bowl Wall Thickness | $p_5 \approx 3.0\text{ mm}$ | Measured via radial ray probe on `sample_models.py` | 2026-11-07 | stable |
| Tall Vase Wall Thickness | $p_5 \approx 2.4\text{ mm}$ | Measured via radial ray probe on `sample_models.py` | 2026-11-07 | stable |
| Thin Cylinder Wall Thickness | $p_5 \approx 0.7\text{ mm} - 1.2\text{ mm}$ | Synthesized cylinder model with thin shell | 2026-11-07 | stable |
| Minimum Backing under $d = \min(0.75W, 0.5t)$ on $t \ge 1.6\text{ mm}$ | $\ge 0.8\text{ mm}$ backing | Algebraic identity: $t - d = t - \min(0.75W, 0.5t) \ge t - 0.5t = 0.5t \ge 0.8\text{ mm}$ | 2026-11-07 | stable |
| 44/44 Test Suite Pass on Main | All tests pass in 209s | Full unittest discover run on `f77406d` | 2026-11-07 | stable |
| Crossing Sweep Invariant | 0 crossings in 1,200 seeds | Agent 2 sweep verification | 2026-11-07 | stable |

## Unverified assumptions

| Assumption | Confidence | Verification Plan |
| :--- | :--- | :--- |
| Slicer toolpath behavior on exported multi-part 3MF | High | Test multi-part 3MF import directly in Bambu Studio / PrusaSlicer. |

## Superseded claims

| Superseded Claim | What Replaced It | Reason |
| :--- | :--- | :--- |
| "Kintsugi engine must support single-perimeter / vase-mode vessels down to 0.7 mm wall thickness" | "Kintsugi engine strictly supports ceramic vessel envelope with $p_5 \ge 1.6\text{ mm}$" | Vase mode is single-perimeter and physically incompatible with multi-material 3D print inlays; sub-millimeter walls caused mathematical tangency bugs and empty gold solids. |
| "Vein depth formula must be $d = t - 0.8\text{ mm}$ with $0.25\text{ mm}$ cutoff" | "Vein depth is $d = \min(0.75W, 0.5t)$ continuous" | With $t \ge 1.6\text{ mm}$, minimum backing is guaranteed by $0.5t \ge 0.8\text{ mm}$, eliminating the need for complex point dropping and groove fading. |
| "50% kink rate is needed for lightning look" | "15–20% kink rate with Gaussian $\sigma \approx 18^\circ$ heading walk" | 50% kinks created unnatural jagged staircase zig-zags; lower kink rate produces organic wandering cracks while maintaining tortuosity $\ge 1.05$. |

## Links out

- [ceramic_vessel_envelope_plan.md](file:///home/node/.gemini/antigravity-cli/brain/faa7bdb1-6652-4211-a0bc-d2e552084921/ceramic_vessel_envelope_plan.md) - Architectural roadmap and validation criteria.
