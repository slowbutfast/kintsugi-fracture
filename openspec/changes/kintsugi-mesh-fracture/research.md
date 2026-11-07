## Source material

> "You are a highly capable 3D graphics and computational geometry expert. Your task is to write a self-contained Python 3 script using the `trimesh` and `numpy` (and optionally `scipy` or `noise` / Perlin) libraries. This script is part of a generative robotic art installation. The objective is to take a pristine, manifold 3D mesh (e.g., a standard .stl or .obj file of a bowl or a Benchy) and algorithmically fracture it to create a 'Wabi-Sabi / Kintsugi' effect. The intensity and density of the fractures must be driven by an external data point representing economic inequality (an income ratio variable `R`). The final script must perform advanced boolean operations to export exactly TWO separate, perfectly aligned manifold STL files that can be imported as a multi-material assembly into a 3D slicing engine: 1. `ceramic_body.stl` - The original model with organic crack channels carved out. 2. `gold_seams.stl` - The exact geometric negative filling those channels, intended to be printed in a gold filament."
— User Handoff Prompt (2026-11-06)

> "The seam geometry needs a precise definition. A ribbon oriented from local surface frames can twist or self-intersect... define how frames are transported along paths, how branches join, and how the cutter is made watertight... Replace 'exact complement' with measurable checks: both outputs watertight, volume sum within a stated tolerance... Define supported inputs: units, closed/watertight requirement, orientation, scale limits... Rework the test plan: measure the resulting geometry."
— Agent 1 Architectural Review (2026-11-06)

> "The perturbation retry loop is borrowed from CGAL and doesn't fit manifold... Its failure mode is non-manifold input, which comes back at Manifold construction. Replace with input check that fails fast: merge_vertices, fix_normals, fill_holes, assert is_volume, build Manifold once... Snapping with nearest.on_surface will jump between inner and outer walls of a thin vessel... Walk in parameter space (θ, z) or Voronoi... Unioning boxes gives slivers; use Manifold.hull on consecutive cross-sections or capsules... Test against meshes written to STL and reloaded... Export a 3MF with two named volumes alongside or instead of STLs."
— Agent 2 Engineering Review (2026-11-06)

### Raised but not acted on

- **Geodesic tracing via potpourri3d**: Suggested as a general mesh fallback. Deliberately not adopted for this initial prototype because potpourri3d introduces C++ geometry build dependencies; cylindrical parameter-space $(\theta, z)$ and raycasting suffice for pottery/vessels while remaining self-contained.
- **In-place vertex perturbation retry**: Discarded completely because Manifold3D fails on topological non-manifoldness, and jittering vertices breaks strict complementarity between ceramic and gold parts.
- **Zero-face STL for $R \ge 1.0$**: Abandoned. trimesh refuses to load one (verified), and slicers likely reject it (unverified). A "minimal marker" was also rejected because it would print as a real gold speck. The wealthy state writes no gold STL.
- **Arbitrary meshes (e.g. Benchy from the source prompt)**: Out of scope. The cylindrical parameterisation only holds for vessels, so non-vessels are rejected by the input envelope check.
- **Noise-octave re-anchoring**: Deferred. Re-anchoring the noise octaves to seed spacing would change the artistic look and needs sign-off from the artist; the remediation keeps `_make_noise` amplitudes and frequencies untouched.
- **Vendoring three.js locally**: Deferred. It would require a new network fetch and a new bundled asset; the GUI continues to use the existing CDN import map.
- **Slicer GUI import (task 6.3)**: Out of scope for remediation. It is a manual Bambu Studio / PrusaSlicer check and those applications are not installed in this headless environment.

## Glossary

| Term | Means | Does NOT mean |
| :--- | :--- | :--- |
| **Kintsugi Assembly** | Two distinct, non-overlapping solids (ceramic body + gold seam) whose spatial union reconstructs the input volume within geometric tolerance. | A single merged mesh with painted vertex colors. |
| **Income Ratio ($R$)** | A float metric ($R = \text{Hometown} / \text{National Median}$). If $R \ge 1.0$, model is pristine. If $R < 1.0$, fracture severity $S = 1.0 - \text{clip}(R, 0.0, 1.0)$ drives crack density and width. | An arbitrary unconstrained parameter that can be negative or infinite without validation. |
| **Trauma Band** | A vertical range along +Z of height $H(S)$, centred on the bounding-box Z midpoint (not the centroid, which sits low in a bowl), where fracture seeds are constrained. | Planar bisecting slices across the model. |
| **Watertight Manifold** | An edge-manifold 2-manifold mesh with zero boundary edges, closed surface, positive volume, and valid Euler characteristic. | Visually closed meshes with overlapping unmerged coplanar faces. |
| **Ribbon Cutter** | A 3D solid made of convex hulls of consecutive slabs, each $W$ wide along the binormal and $t + 1$ mm deep along the inward surface normal, penetrating through the local wall thickness $t$. | A zero-thickness 2D polygonal surface. |
| **Vein Cutter** | A 3D solid made of consecutive sphere hulls (`hull(S_i + S_{i+1})`), with spheres inset so the groove depth is $d = \min(0.75W, 0.5t)$. |
| **Unrolled parameter space** | $(u, z)$ with $u = \theta \bar r$, so parameter distances approximate surface arc length. | Raw $(\theta, z)$, which mixes radians with millimetres. | Flat cylinders with open ends. |

## External Research

| Source | What it establishes | Licence | Accessed |
| :--- | :--- | :--- | :--- |
| **Manifold3D (elalish/manifold)** | Exact, robust CSG kernel using symbolic perturbation. Guarantees watertight manifold outputs without geometric glitches. | Apache 2.0 | 2026-11-06 |
| **Trimesh (mikedh/trimesh)** | Python library for loading, repairing, and exporting triangular meshes (STL, OBJ, 3MF). | MIT | 2026-11-06 |
| **3MF Specification (3MF Consortium)** | Open standard for additive manufacturing supporting multi-material assemblies in a single archive. | Open Standard | 2026-11-06 |

## Candidate tech

| Option | Decision | Reason | Date |
| :--- | :--- | :--- | :--- |
| `manifold3d` | Adopted | 10x-50x faster CSG than CGAL/OpenSCAD; provides exact boolean operations and convex hulls. | 2026-11-06 |
| `trimesh` | Adopted | Standard Python 3D mesh I/O, repairing, and scene export. | 2026-11-06 |
| `scipy` (Voronoi) | Adopted | Voronoi ridge graph in unrolled $(u, z)$ space, made periodic by seed tiling. | 2026-11-06 |
| `lxml` + `networkx` | Rejected | Only needed for trimesh's 3MF exporter, which writes separate build items rather than components. 3MF is hand-written with `zipfile` + `xml.etree`. | 2026-11-06 |
| `Manifold.ray_cast` | Adopted | Native exact ray casting against the validated input; replaces trimesh rays, which need `rtree`. | 2026-11-06 |
| `rtree` | Dev-only | Needed only for `trimesh.proximity.thickness` in the test suite. | 2026-11-06 |
| `potpourri3d` | Rejected | Heavy C++ binary compilation dependency not required for vessel parameterizations. | 2026-11-06 |
| `OpenSCAD` engine | Rejected | Extremely slow, fragile subprocess execution prone to boolean coplanar errors. | 2026-11-06 |

## Patterns adopted

- **Parameter-Space Cylindrical Projection**: Crack graphs generated in unrolled $(u, z)$ space and cast radially outward; the farthest hit is the exterior and the previous hit gives wall thickness. Solves wall-hopping across thin ceramic walls.
- **Consecutive Convex Hull Sweeping**: Forming segments via `(cross_section_i + cross_section_{i+1}).hull()` in Manifold3D. Eliminates gaps and coplanar slivers at acute bends.
- **Single-Manifold Dual CSG**: Constructing a single validated input `Manifold` and taking `M - C` (ceramic) and `M ^ C` (gold) ensuring mathematical complementarity.

## Verified facts

| Claim | Value | How verified | Date | Volatility |
| :--- | :--- | :--- | :--- | :--- |
| `manifold3d` installed in environment | 3.5.4 | Tested import and boolean ops in `.venv` | 2026-11-06 | stable |
| `trimesh.boolean` difference + intersection volume conservation | True ($\text{Vol}_{in} == \text{Vol}_{diff} + \text{Vol}_{inter}$) | Tested with hollow cylinder in Python | 2026-11-06 | stable |
| `manifold3d.Manifold.batch_boolean` union of 30 capsules | Runs in 0.084s, 100% watertight | Benchmarked in Python | 2026-11-06 | stable |
| Trimesh 3MF export requires `lxml` and `networkx` | Verified | Tested export of multi-volume scene | 2026-11-06 | stable |
| Empty STL loading raises Scene object error | Verified | Tested `trimesh.load('empty.stl')` | 2026-11-06 | stable |
| `rtree` not installed; `trimesh` ray queries fail with `No module named 'rtree'` | Verified | `box.ray.intersects_location` in `.venv` | 2026-11-06 | volatile |
| `Manifold.ray_cast(origin, endpoint)` returns all hits sorted, `distance` normalised to $[0, 1]$ along the segment | Verified | Hollow cylinder r=27/30: hits at 0.45, 0.5 of a 60 mm ray | 2026-11-06 | stable |
| `manifold3d` exposes `Mesh64` / `to_mesh64` | Verified | `hasattr` in 3.5.4 | 2026-11-06 | stable |
| trimesh 5.2.0 3MF export writes one `<item>` per geometry, with no `<components>` | Verified | Inspected `3D/3dmodel.model` of a two-geometry scene | 2026-11-06 | volatile |
| 400-capsule `batch_boolean` cutter subtracted from a sphere is deterministic across 5 runs (157,110 tris) | Verified | MD5 of `to_mesh()` buffers, same process | 2026-11-06 | stable |
| Manifold symbolic-perturbation output can still *kiss*: separate output pieces may share edges or vertices in space. Binary-STL reload merges by position, turning kissed edges into edges used by 4–6 faces. | 79/132 completed sweep runs were non-watertight after STL reload | 144-run sweep (2 presets × 6 R values × 2 modes × seeds 0–5), per-edge face-count histogram on reload | 2026-11-06 | stable |
| Vein-mode sphere alignment is the cause of knife-edge kissing: every sphere uses the same axis-aligned tessellation, so path neighbours and junction spheres share coincident vertices. | Seeded per-sphere rotation changed bad-edge counts from 6/34/36 to 0/0/0 for seeds 0, 1, 5 (cutter, `M−C`, `M∩C`) | Staged experiment with `s.rotate(rng.uniform(0, 360, 3))` before translation | 2026-11-06 | stable |
| Ribbon-mode kissing is structural, not an accidental translation coincidence. Seed 0 showed 26 bad edges in the raw CSG, including the inner wall/floor corner and base; translating the cutter by 1e-3 or 1e-2 mm did not change the count. | 26 bad edges at z 0–24.8, r 41.98–45; count invariant under cutter translation | Staged counts on cutter alone, `M−C`, `M∩C`, plus cutter translations | 2026-11-06 | stable |
| Debris swap by unconditional union can add new kissed edges even when the crumbs touch the target only along an edge or at a point. | Seeds 1 and 2 ribbon were clean before the swap and non-clean after it | Pre-swap vs post-swap bad-edge counts | 2026-11-06 | stable |
| Ribbon-mode F1b root cause: every slab has the same through-wall depth `t+1` and the same offset from the surface, so consecutive hulls have coplanar overlapping inner/outer faces. Manifold's union is valid, but binary-STL position merging turns the coincident face boundaries into edges used by 4–6 faces. The pattern appears at `r ≈ 41.48` (inner slab face) and `r ≈ 45.48` (outer slab face), not only at path junctions. | Seed 0 at R=0.2: cutter 32 bad edges (31 four-face, 1 six-face); `M−C` and `M∩C` both 6. The bad-edge `z` values span the band (e.g. 22.61, 23.56, 24.49), and translating the cutter by 1e-3 or 1e-2 mm does not change the count. | Staged counts on cutter, `M−C`, `M∩C`; bad-edge coordinate dump; translation experiment from the handoff | 2026-11-06 | stable |
| A seeded per-slab rotation about the slab normal plus depth/centre jitter of at most `1e-3·W` de-aligns the ribbon slabs enough to remove most coplanar-face artifacts. | With 0.5° rotation and `1e-3·W` jitter, seeds 0/1/2/5 produced `M−C` and `M∩C` bad-edge counts 0/0/0/0; cutter alone fell from 32 to 2 for seed 0. | Standalone staged experiment before applying the fix | 2026-11-06 | stable |
| The **authoritative unbounded-ray rule** is the Voronoi distance definition: a point just along the ray must be closer to the ridge's two seeds than to any other seed. The literal "away from the third Delaunay seed" sign is ambiguous when the finite vertex sits far outside the seed cloud (the third seed can lie on the same side as the valid ray). Evaluate both normals against the distance definition and use the third seed only as a numerical tie-break. | The seed-pair-midpoint rule failed on 24–29% of rays over 200 seeds at S = 0.2, 0.8 and 1.0; the definition-based rule passed the new 200-seed check (the pure third-seed sign was 1/1,878 in the reviewer's check). | Voronoi distance-definition check over 200 seeds | 2026-11-06 | stable |
| **Actual F12 cause:** Manifold's float64 CSG output can contain sub-`1e-5` sliver edges at cut boundaries. Binary STL float32 rounding/loader merging turns those slivers into edges used by 4 faces. Per-path slab unions, duplicate shared-slab copies, and planar cross-section hulls were tested and did **not** remove the problem. An export-time edge-collapse repair, accepted only when the mesh remains watertight, positive-volume and within `1e-6` volume, removed the slivers. Vein mode additionally benefits from unioning overlapping spheres directly (hull only for a >2r gap) with a ≤0.2% per-sphere radius jitter. | Out-of-sample baseline: 159/160 clean, 1 RuntimeError, 13 retries. With collapse repair + vein union/radius jitter: 160/160 clean and attempts `{1: 160}`; the tuning sweep is also 144/144 with attempts `{1: 144}`. | `tools/sweep.py` and `tools/sweep_out_of_sample.py` before/after | 2026-11-06 | stable |
| **F13 wall rule:** single-hit rays occur only in the solid floor, where using the outer-hit distance (even capped at `0.5*rbar`) cuts ~22 mm slots into a 3 mm floor. Clamp crack points to the two-hit wall Z range; for any residual single-hit point use the median two-hit wall thickness of its path, falling back to the global median. | Baseline gold reached `r ≈ 22 mm` inside a floor with inner wall `r = 42 mm`; 18–20% of R=0 gold volume was in the floor for seeds 1/3. | Gold-vertex radius audit and R=0 gold render | 2026-11-06 | stable |
| **F14 strip-end distortion:** a 3-tile seed strip is not periodic at its ends. A finite ridge whose two seeds both lie in the −1 or +1 tile is bent by the missing next tile; shifting that bent copy into the central tile creates a phantom ridge that can overlap a real one. Requiring a central seed for every ridge (not only rays) eliminates the phantom. | Example tea bowl S=0.6 seed 76 ridge 25 (two +1-tile seeds) runs to (770, −677) and duplicates real ridge 34, ending 0.2 mm past the true vertex. Central-seed filter: 0/200 phantom and 0 dangling junctions on both presets at S=0.6/1.0. | 9-tile ground-truth audit | 2026-11-06 | stable |
| **F15a clamp-on vs clamp-off crossings:** projecting each point onto a horizontal clamp line creates new crossings and violates the ragged band-edge scenario. With noise/jitter off, crossing seeds were tea bowl S=0.6 4 vs 0 and S=1.0 22 vs 2; vase S=0.6 18 vs 2 (the residual 2s are F14). Path points on a clamp line were 5.5–7.8% mean, 16.7% max. | Full noise-off audit with clamp on: tea bowl 7/26, vase 24/76 crossing seeds at S=0.6/1.0. | `tools/crack_graph_audit.py` | 2026-11-06 | stable |
| **F16 repair frequency:** sliver repair is valid but common: 142 of 964 exported meshes (15%) needed repair in a fresh sweep, with 4 repairs falling back to a retry. Running it once per guard evaluation and reusing the repaired mesh for STL, 3MF and triangle counts removes redundant work. | Fresh sweep timing: median 1.4 s, max 27.4 s before the reuse change. | Reviewer sweep and call-site audit | 2026-11-06 | stable |

## Unverified assumptions

- **Slicer 3MF components**: Bambu Studio and PrusaSlicer load a 3MF Core object with `<components>` as one object with multiple parts. Checking costs: one manual import per slicer (task 5.3).
- **Zero-face STL rejected by slicers**: likely, but untested. Moot now that the file is not written.
- **Determinism across processes and machines**: verified only within one process; TBB thread count could matter. Checking costs: run `test_determinism` in two separate processes.
- **Slicer adhesion**: Dual extrusion or tool-changing 3D printers assume acceptable mechanical bond between ceramic filament (e.g. PLA) and gold filament (e.g. Silk PLA). Checking costs: physical print test.

## Superseded claims

- **Vertex perturbation retry loop**: Originally planned to jitter vertices randomly upon boolean failure. Superseded because Manifold3D failures are topological, and asymmetric jitter breaks volume complementarity. Replaced with fail-fast input validation.
- **Nearest-surface 3D snapping**: Originally planned to snap 3D noise coordinates with `nearest.on_surface`. Superseded because thin walls cause catastrophic inner/outer wall jumping. Replaced with cylindrical parameter-space projection.

- **"0.5% volume conservation" as a quality gate**: $\text{Vol}(M - C) + \text{Vol}(M \cap C) = \text{Vol}(M)$ is an identity. Kept as a $10^{-6}$ regression tripwire; print quality is gated by thickness, depth and debris tests.
- **Deleting sub-threshold shards**: would break complementarity and leave voids. Replaced by a bidirectional swap into the other material.
- **`fill_holes` during repair**: contradicts the closed-input non-goal and invents geometry. Repair is lossless clean-up only.
- **Single-seed geometry tests are sufficient evidence of watertight output**: Superseded: a 144-run sweep showed only 37% clean. The suite now includes a multi-seed sweep test and the standalone `tools/sweep.py`.
- **Debris swap is safe by union alone**: Superseded. Unioning a crumb that only touches the target at an edge or point creates new kissing edges; remediation requires face-region sharing and otherwise leaves the crumb in place with a counter.
- **Ribbon kissing is caused by coplanar shared slab faces**: Incomplete. Per-path unions, duplicate shared-slab copies and planar cross-section hulls did not eliminate the failures. The controlling mechanism is near-degenerate sliver edges in the float64 CSG output that become non-manifold after binary-STL float32 reload; export-time watertight edge-collapse repair resolves it.
- **A single retry guard is enough for ribbon robustness**: Superseded. Out-of-sample retries were routine (13/160, one 3-attempt failure). The export repair removes the need for retries; the guard remains only as a backstop.
- **Requiring a central seed only for rays is sufficient**: Superseded. Finite ridges with both seeds outside the central tile are distorted by the 3-tile strip ends and produce phantom central ridges. The central-seed rule applies to finite ridges and rays alike.
- **Clamp to `max(z_min, z_wall,lo) + W/2`**: Superseded by truncation at the wall range (F15). Projecting points onto a line creates crossings and flat terminals; paths are now cut where they leave the wall range, with no point pushed onto a horizontal limit.

## Links out

- The original handoff lived in another agent's private workspace (`~/.gemini/antigravity-cli/brain/...`), which is not reachable from this repo. Its relevant content is captured in this file.
