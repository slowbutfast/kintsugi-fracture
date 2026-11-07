# Architectural Handoff & Advisory: Pivoting from Topological Purity to Visual Aesthetics

### Context: You Already Know This Codebase
You have reviewed our recent commits, audited our F1–F20 remediation logs, and analyzed our verification reports (including the Apple M6 160/160 clean sweep, the fingerprinting in `tools/test_report.py`, and the F18 noise-fold audit). You know `kintsugi.py` inside and out—specifically `_make_noise` (L438), the cylindrical Voronoi graph construction (L450–860), the convex hull cutter swept volume, and our dual-material 3MF exporter.

---

### The Dilemma: The Mathematical Verification Trap
In your recent feedback, you correctly identified:
- **F18**: With noise enabled, 703/1200 seeds (59%) exhibit foldings/crossings with $\max |\nabla \eta| \approx 3.41$ and up to 26.2% fold area in `_make_noise`. You recommended deriving a defensible bound on the full displacement Jacobian or enforcing Lipschitz gradient constraints.
- **F19**: Unresolved rim-breakthrough behavior.
- **F20**: Missing `guard_evaluations` API assertion.

**Here is the project lead's perspective:**
We have spent four consecutive rounds (F1–F20) patching mathematical edge cases—clamping rays, merging collinear edges, resolving Voronoi ray tie-breaks, and now hunting Jacobian bounds. While our unit tests and sweep harnesses pass cleanly (`35/35 OK`, 160/160 seeds), **the visual output is heading in the wrong direction**:
1. **Voronoi yields bathroom tiles, not Kintsugi**: The underlying Voronoi diagram naturally produces cellular, polygonal tiles (like a turtle shell or shower tile grout). Even when perturbed by noise, it lacks the dramatic, high-contrast, lightning-like fissures and organic dendritic branching that define traditional Kintsugi.
2. **Topological tests penalize organic jaggedness**: Whenever we try to make the cracks sharp and dramatic, noise gradients exceed 1.0, triggering your crossing/folding audits. In response, previous remediation passes added smoothing, clamping, and damping that flattened out the cracks into artificial, sterile lines just to satisfy the tests.
3. **Over-engineering for an artistic prototype**: This project is for a **generative robotic art installation**, primarily targeting pottery and vessels printed in **vase mode / thin-wall containers**. We do not need a bulletproof topological CAD solver for arbitrary non-cylindrical manifolds. We need vessels that look stunning, with gold seams that look like genuine lightning fissures pouring over the rim.

---

### Questions for Your Review

Given your deep knowledge of our architecture, please advise on the following three points:

#### 1. The F18 Decision: Fix the Jacobian, or Replace the Voronoi Engine?
Rather than spending another cycle trying to bound the displacement Jacobian on a Voronoi base (which fundamentally wants to be polygonal), should we **surgically delete lines 435–860 of `kintsugi.py`** and replace it with a dedicated **cylindrical fractal lightning generator**?
- Specifically: using **Cylindrical Midpoint Displacement** (recursive midpoint subdivision in unrolled $(\theta, z)$ space with angular wrapping and acute secondary branching) or **stochastic shortest paths on the mesh dual graph** (`networkx.dijkstra_path` with noise-weighted edge costs).
- If we switch to midpoint displacement:
  - Fissure morphology is intrinsically lightning-like and tree-like (branching angles $\approx 25^\circ\text{–}45^\circ$).
  - Self-intersection avoidance is trivial to enforce by construction without needing to bound a global 2D noise Jacobian.
  - The implementation drops from ~425 lines of Voronoi/ray math to ~80 lines, directly feeding the existing `_build_vein_cutter` and `manifold3d` CSG pipeline.
- Do you agree with this architectural pivot away from Voronoi? What risks do you see in the cutter generation or CSG boolean steps if we feed it midpoint-displacement polylines instead?

#### 2. Re-architecting Verification: How to Measure Aesthetics Over Pure Topology
You built the rigorous testing and audit harness that caught F1–F20. How should we re-align that verification infrastructure so that it guides future agents toward aesthetic excellence rather than incentivizing them to smooth away organic character?
- How should we incorporate an **automated visual review gate** into `tools/test_report.py` (e.g., generating multi-angle viewport renders to `output/renders/` on every run for multimodal/human inspection)?
- What computable geometric metrics would you accept in `verification.md` that correlate with visual quality rather than sterility (e.g., fractal dimension $D \in [1.2, 1.4]$, branch angle distributions, rim-crossing counters, tortuosity index $\frac{\text{arc length}}{\text{chord length}}$)?

#### 3. Scope & Slicer Reality for Thin-Wall / Vase Mode
Given that single-wall vase mode prints cannot tolerate detached floating shards, our primary production path is **Vein Inlay Mode** (embossed/debossed gold channels on the vessel surface) rather than physical through-body shattering.
- Considering your open note on Task 6.3 (validating multi-part 3MF import in Bambu Studio / PrusaSlicer), does focusing primarily on surface vein inlays simplify our CSG requirements and eliminate the need to solve arbitrary shard-collision edge cases?

Please share your recommended next steps and how you would prefer we update `tasks.md` and `specs/` to reflect this aesthetic-first direction.
