## Source material

- **2026-11-07, Project Lead**: "wait, i'm actually not bound by the vasemode constraint. how can we loosen that constraint to give our algorithm more breathing room to form these cracks? this is the constraint specifically that i don't really care about: • When you fix the kissing bug with a 0.25 mm cutoff: The gold channel disappears on thin walls, which triggers an 84-byte empty STL bug in the exporter and a misleading 'Pristine / Wealthy' label in the UI."
- **2026-11-07, Agent 1 Review**: "Separating this into its own change is right now that kintsugi-crack-growth is archived... The wall check must be over [wall_z_min, wall_z_max] independent of R. Thickness must be measured along the inward surface normal rather than radially to avoid flared-wall overestimation. The backing guarantee is: backing >= 0.5*t everywhere, and >= 0.8 mm wherever t >= 1.6 mm. The growth morphology already shipped in PATCH-02, so tasks should be regression tests. Copy back the three missing scenarios."
- **2026-11-07, Agent 2 Review**: "Strict OpenSpec validation passes... The p5 threshold does not guarantee 0.8 mm backing at every outlier point, so state the guarantee precisely. Include a delta for multi-material-export to reconcile the empty-gold fallback when R < 1.0. Make preset migration explicit and correct domain references (ASTM D256 is plastics impact, replace with brittle ceramic fracture mechanics)."

### Raised but not acted on

- **Supporting sub-millimeter single-perimeter prints**: Deliberately removed from project requirements. Slicers cannot print dual-extrusion multi-material inlays inside spiral vase mode.
- **Dynamic adaptive mesh thickening**: Thickening thin meshes on-the-fly was considered and rejected; modifying input geometry without user intent distorts the original design. Clear validation failure with measured vs required thickness is preferable.
- **Requiring absolute minimum thickness $t_{min} \ge 1.6\text{ mm}$ instead of 5th percentile**: Considered, but rejected because mesh artifacts (e.g., sharp corners, chamfered rim points) produce local geometric singularities. $p_5 \ge 1.6\text{ mm}$ over the wall range rejects thin-walled vessels robustly without rejecting valid pottery with tapered rims.

## Glossary

| Term | Means | Does NOT mean |
| :--- | :--- | :--- |
| **Ceramic Vessel Envelope** | Watertight input meshes with 5th-percentile two-hit wall thickness $p_5 \ge 1.6\text{ mm}$ measured along inward surface normals across `[wall_z_min, wall_z_max]`. | Arbitrary single-perimeter thin shells or vase-mode geometries. |
| **Normal Wall Thickness ($t_{\text{normal}}$)** | The distance between the outer vessel surface hit and the interior ray-mesh hit along the inward surface normal. | Horizontal radial distance along the XY plane (which overstates thickness on flared walls by $1/\cos\theta$). |
| **Wall Range (`[wall_z_min, wall_z_max]`)** | The Z-interval of the vessel exterior wall determined by `_probe_wall_range`, independent of fracture parameters or income ratio $R$. | The R-dependent trauma band $H(S)$. |
| **Continuous Vein Inlay** | Vein depth $d_i = \min(0.75W, 0.5t_i)$, creating a deep, uniform gold groove along the entirety of every crack path without omitting cutter points. | Segmenting or omitting groove points where depth fades toward zero. |
| **Final-Step Near-Miss Snapping** | When a crack reaches within $R_{\text{clear}}$ on its final attempt at arrival angle $\ge 30^\circ$, bending directly to the nearest point on the target segment. | Stopping short 2–3 mm away leaving dead-end dangling gaps. |

## External research

| Source | What it establishes | Licence | Accessed |
| :--- | :--- | :--- | :--- |
| Lawn, B. R., *Fracture of Brittle Solids*, Cambridge University Press | Physical brittle fracture mechanics: propagation along maximum tensile stress, dendritic branching, and perpendicular/obtuse crack arrest against pre-existing free surfaces (T-junctions). | Academic Reference | 2026-11-07 |
| Dikomitou, M., *Ceramic Technology and Production*, UCL PhD Thesis | Archaeological analysis of pottery wall thickness: hand-built and wheel-thrown ceramic vessels typically exhibit wall thickness between 2.5 mm and 6.0 mm; 1.6 mm represents an aggressive lower bound for durable fired ceramics. | Academic Research | 2026-11-07 |
| [Prusa Knowledge Base: Modeling with 3D Printing in Mind](https://help.prusa3d.com/article/modeling-with-3d-printing-in-mind_164135) | Multiple perimeters are required for solid, watertight walls. Thin features below 1.2–1.6 mm require single-perimeter slicing, incompatible with multi-material toolhead switching. | Public Documentation | 2026-11-07 |
| [Bambu Studio Multi-Material Documentation](https://wiki.bambulab.com/en/software/bambu-studio) | Multi-material FDM slicing requires discrete closed 3D volumes per extruder. Surface channels must be closed solids intersecting or mating with the body. | Public Documentation | 2026-11-07 |

## Candidate tech

| Option | Decision | Reason | Date |
| :--- | :--- | :--- | :--- |
| Radial Wall Probing | Superseded | Radial rays measure horizontal distance, overstating true wall thickness on flared walls by $1/\cos(\text{flare})$ (e.g. at $45^\circ$, 1.2 mm wall reads as 1.7 mm and falsely passes). | 2026-11-07 |
| Inward Normal Wall Probing | Adopted | Accurately measures true orthogonal wall thickness at exterior hit locations, aligning with cutter penetration direction. | 2026-11-07 |
| Thin-Wall Depth $d = t - 0.8\text{ mm}$ with $0.25\text{ mm}$ cutoff | Superseded / Removed | Fragile; causes groove fade, tangent kissing contact, empty gold solids, and split cutter points on thin walls. | 2026-11-07 |
| Classical Vein Depth $d = \min(0.75W, 0.5t)$ with $p_5 \ge 1.6\text{ mm}$ envelope | Adopted | Guarantees nominal ceramic backing $\ge 0.5 \cdot t_i$ everywhere, and $\ge 0.8\text{ mm}$ wherever $t_i \ge 1.6\text{ mm}$, with bold gold seams and zero cutter point omissions. | 2026-11-07 |

## Patterns adopted

- **Preflight Normal Wall Thickness Validation**: Sampling two-hit wall thickness via inward surface normal rays in `validate_and_load_mesh` across `[wall_z_min, wall_z_max]`, rejecting meshes with $p_5 < 1.6\text{ mm}$ with an informative `ValueError`.
- **Continuous Cutter Extrusion**: Building continuous manifold cutters without splitting polyline paths into discontinuous point groups.
- **Rim Lip Projection Clamping**: Clamping crack projection at $z = \text{wall\_z\_max} - \max(0.5, W/2)$ to avoid tapered rim lip geometry.
- **Defensive Exporter Safeguards**: Retaining `_gold_solid_omitted` logic in `multi-material-export` to handle wealthy runs ($R \ge 1.0$) and unforeseen boolean voids cleanly.

## Verified facts

| Claim | Value | How verified | Date | Volatility |
| :--- | :--- | :--- | :--- | :--- |
| Japanese Tea Bowl Wall Thickness | $p_5 \approx 3.0\text{ mm}$ | Measured via normal ray probe on `sample_models.py` | 2026-11-07 | stable |
| Tall Vase Wall Thickness | $p_5 \approx 2.4\text{ mm}$ | Measured via normal ray probe on `sample_models.py` | 2026-11-07 | stable |
| Thin Cylinder Synthetic Shell Thickness | $p_5 \approx 0.7\text{--}1.2\text{ mm}$ | Authored geometry parameters in `sample_models.py` | 2026-11-07 | stable |
| Backing Relationship under $d = \min(0.75W, 0.5t)$ | Backing $\ge 0.5 \cdot t_i$; $\ge 0.8\text{ mm}$ when $t_i \ge 1.6\text{ mm}$ | Algebraic identity: $t_i - d_i \ge t_i - 0.5t_i = 0.5t_i$. When $t_i \ge 1.6\text{ mm}$, $0.5t_i \ge 0.8\text{ mm}$. | 2026-11-07 | stable |
| True Minimum Cutter Depth on Supported Envelope | $0.6\text{ mm}$ | For $W \in [0.8, 2.2]\text{ mm}$ and $t_i \ge 1.6\text{ mm}$, $\min(0.75 \times 0.8, 0.5 \times 1.6) = \min(0.6, 0.8) = 0.6\text{ mm}$. | 2026-11-07 | stable |
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
| "Wall thickness can be sampled radially across trauma band" | "Wall thickness must be sampled along inward surface normals across the R-independent wall range `[wall_z_min, wall_z_max]`" | Radial rays overstate thickness on flared walls; trauma band depends on R and is unavailable during `/api/validate`. |
| "Vein depth formula must be $d = t - 0.8\text{ mm}$ with $0.25\text{ mm}$ cutoff" | "Vein depth is $d = \min(0.75W, 0.5t)$ continuous" | With ceramic envelope, nominal backing $\ge 0.5 \cdot t_i$ is preserved everywhere, eliminating point dropping and groove fading. |
| "p5 >= 1.6 mm guarantees 0.8 mm backing everywhere" | "Nominal backing is $\ge 0.5 \cdot t_i$ everywhere, and $\ge 0.8\text{ mm}$ wherever $t_i \ge 1.6\text{ mm}$" | A 5th percentile allows up to 5% of samples below the threshold (e.g. at the lip). |

## Links out

- [ceramic_vessel_envelope_plan.md](file:///home/node/.gemini/antigravity-cli/brain/faa7bdb1-6652-4211-a0bc-d2e552084921/ceramic_vessel_envelope_plan.md) - Architectural roadmap and validation criteria.
