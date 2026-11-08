# Proposal: Tilted Shard-Plane Fracture Generator (`kintsugi-shard-seams`)

## Why

The existing rim-to-floor growth generator (`generator="growth"`) grows cracks tip-by-tip from the upper rim using local heading noise, kink branches, and collision clamping. While mathematically constrained, tip-by-tip growth lacks the macroscopic shard topology of real kintsugi—where a dropped ceramic vessel breaks into 2–4 large visual shard regions along sweeping, tilted fracture planes—and has required multiple rounds of local collision, rim-clamping, and hook-suppression patches.

Rather than physically slicing the 3D mesh into separate solid shards and re-unioning them (which is a geometric identity on the solid vessel in `vein` mode and adds unnecessary 3D CSG boolean passes), we synthesize the **1D exterior seam traces** where tilted, roughened fracture planes meet the cylindrical unwrapped wall `(u, z)` and feed those polylines directly into the existing `project_crack_paths` $\to$ `_build_vein_cutter` $\to$ `Manifold3D` pipeline.

## What Changes

- **Opt-in Shard-Plane Fracture Generator (`generator="shard"`)**:
  - Add `"shard"` to allowed generator choices `("growth", "shard", "voronoi")` in `generate_kintsugi_mesh` and `generate_crack_paths(params, rng, *, subdivide_step=None, generator="growth")`.
  - Keep `generator="growth"` as the default so all existing tests, presets, and API behavior remain unchanged.
  - Scope `generator="shard"` to `mode="vein"` in Stage 1, raising a `ValueError` if paired with `mode="ribbon"`. In `web_app.py`, this `ValueError` returns an `HTTP 400 Bad Request`.
- **Pipeline Integration & Metric Semantics**:
  - Fracture behavior is governed by severity $S = 1 - \text{clip}(R, 0, 1)$, where $R$ is the inequality reserve metric ($R=0 \implies S=1.0$, most damaged; $R \ge 1.0 \implies S=0$, untouched vessel).
  - Generator signature strictly conforms to the engine dispatch pattern:
    `generate_shard_crack_paths(params: dict, rng: np.random.Generator, *, subdivide_step: float | None = None) -> list[np.ndarray]`.
- **Stage 1 Seam Primitives in `(u, z)` Space**:
  - **Primitive A — Open Rim-to-Rim Wedge Seam**: Enters at the upper rim ($z = \text{wall\_z\_max} + 0.35W$), dips to a deterministic nadir $z_{\text{nadir}} \in [\text{wall\_z\_min} + 0.18\,\Delta z_{\text{wall}}, \text{wall\_z\_max} - 0.20\,\Delta z_{\text{wall}}]$, and exits back through the upper rim. Truncated at exact wall-band crossings via `_truncate_polyline_z` (never `np.clip`) so rim endpoints land cleanly on the lip without flat horizontal shelves.
  - **Primitive B — Closed Tilted Loop Seam**: A $360^\circ$ periodic curve $u \in [0, P]$ derived from $z_{\text{base}}(u) = z_0 + \bar{r}\tan(\alpha)\cos(u/\bar{r} - \phi)$ plus low-order periodic Fourier harmonics ($k \in \{2, 3\}$) and a linear drift bridge kink walk so $z(0) = z(P)$ exactly. Amplitudes are height-capped before sampling; if available wall height forces $\alpha < 5^\circ$, the generator falls back to Primitive A (Wedge) rather than flattening the loop into a horizontal ring.
  - **Seam 2 Rim-to-Seam Wedge & Shared T-Junction**: When $S \ge 0.35$, the generator attempts a second seam originating from the upper rim. Up to 16 deterministic draws are evaluated to find a first intersection with Seam 1 in $[\text{wall\_z\_min} + W, \text{wall\_z\_max} - W]$ at arrival angle $\ge 30^\circ$. If found, Seam 2 is truncated at the intersection, a shared vertex is inserted into Seam 1, and the junction is recorded in `params["_growth_junctions"]` so `analyze_growth_paths` applies exemption zone $r_{\text{exempt}} = 1.10 r_{\text{clear}} / \sin 30^\circ$ while checking $r_{\text{clear}} \ge W + 0.8\text{ mm}$ elsewhere. If no candidate succeeds within 16 tries, the generator falls back deterministically to returning `[Seam 1]`.
- **Closed-Loop Audit & Tortuosity Support**:
  - Update `analyze_growth_paths` to use cyclic segment index distance (`min(diff, n_path_segs - diff) <= skip_span`) when a path is a closed periodic loop (`_periodic_distance(path[0], path[-1], period) <= 1e-6`), preventing false clearance failures across the $u=0 \equiv P$ wrap point.
  - Update `_tortuosity_values` so closed periodic loops are split into 4 equal quadrant sub-arcs ($\Delta u = P / 4$) in 2D $(u, z)$ before computing arc over chord, enforcing the engine tortuosity floor $\tau \ge 1.05$.
- **Side-by-Side Contact Sheet Comparison**:
  - Extend `tools/spike_contact_sheet.py` with `--generator {growth,shard,both}` calling `generate_kintsugi_mesh` to render a 12-case contact sheet (`reports/contact_sheet_shard.png`) across Tea Bowl and Tall Vase at $R \in \{0.0, 0.2, 0.5\}$ and seeds 0 and 1.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `mesh-fracture-engine`: Add `Requirement: Shard-plane crack generation` defining the opt-in `generator="shard"` seam primitives, exact wall-band truncation, height-capped drift bridge loop closure, verified Seam 2 T-junction with `params["_growth_junctions"]` metadata and deterministic fallback, closed-loop cyclic clearance and 2D quadrant sub-arc tortuosity ($\tau \ge 1.05$), and Stage 1 `mode="vein"` scope.

## Impact

- **`kintsugi.py`**:
  - `_tortuosity_values` and `analyze_growth_paths` (`L1912-L2058`): Add closed-loop quadrant sub-arc tortuosity and cyclic segment adjacency skip logic.
  - `generate_shard_crack_paths` (inserted before `generate_crack_paths` around `L2080`): Implement Stage 1 shard-plane seam synthesis, exact truncation, and verified T-junction insertion with `params["_growth_junctions"]`.
  - `generate_crack_paths` (`L2089-L2106`): Dispatch `generator == "shard"` to `generate_shard_crack_paths(params, rng, subdivide_step=subdivide_step)`. Retain `"growth"` and `"voronoi"`.
  - `generate_kintsugi_mesh` and CLI parser (`L3018-L3022`, `L3270-L3276`): Accept `"shard"` in `generator`, raise `ValueError` for `generator="shard"` and `mode="ribbon"`.
- **`web_app.py`**:
  - `api_fracture` handles `generator="shard"`, converting `ValueError` for `mode="ribbon"` into HTTP 400.
- **`tools/spike_contact_sheet.py`**:
  - Add `--generator {growth,shard,both}` CLI flag calling `generate_kintsugi_mesh`.
- **`tests/test_crack_shard.py`**:
  - New TDD unit and integration suite verifying open wedge truncation, closed loop drift bridge periodic continuity and cyclic clearance, verified two-seam T-junction vs. deterministic fallback, 2D quadrant sub-arc tortuosity ($\tau \ge 1.05$), and watertight `Manifold3D` boolean output on Tea Bowl and Tall Vase.
