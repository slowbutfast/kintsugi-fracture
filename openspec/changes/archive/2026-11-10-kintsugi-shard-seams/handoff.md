# OpenCode Orchestration Handoff: OpenSpec Change 'kintsugi-shard-seams'

You are the orchestration agent for OpenSpec change 'kintsugi-shard-seams' running in OpenCode.
Your primary directive is to execute this change using the **`openspec-apply-sub`** skill, which delegates task implementation to the `spec-coder-sub` subagent.

## 1. Orchestration Directive
- **Change Name**: `kintsugi-shard-seams`
- **Target Skill**: `openspec-apply-sub` (or `/opsx:apply-sub kintsugi-shard-seams`)
- **Architecture Paradigm**: Vertical Slice Architecture (VSA). Maintain strict isolation between feature compartments and avoid horizontal abstractions.

## 2. Target Context Map
| File Path (relative to repo root) | Target Lines | Modification Summary |
|---|---|---|
| `kintsugi.py` | `L1912-L1948` | Update `_tortuosity_values` so closed periodic loops (`len(pts) >= 4` and `_periodic_distance(pts[0], pts[-1], P) <= 1e-6`) without split junctions are split into 4 equal quadrant sub-arcs (`[0, N//4, N//2, 3*N//4, N-1]`) in 2D `(u, z)` space before computing `arc / chord`. Enforce the engine tortuosity floor $\tau \ge 1.05$. |
| `kintsugi.py` | `L1996-L2002` | Update `analyze_growth_paths` so closed periodic loops compute adjacent segment skip span cyclically (`min(abs(i-j), n_segs - abs(i-j)) <= skip_span`) across the $u = 0 \equiv P$ wrap point. |
| `kintsugi.py` | `L2080-L2110` | Add `generate_shard_crack_paths(params: dict, rng: np.random.Generator, *, subdivide_step: float | None = None) -> list[np.ndarray]` implementing Primitive A (Open Rim-to-Rim Wedge Seam with exact `_truncate_polyline_z` truncation), Primitive B (Closed Tilted Loop Seam with linear drift bridge closure and height-capped amplitude allocation), and Seam 2 candidate evaluation ($\le 16$ deterministic draws) with shared T-junction vertex insertion, `params["_growth_junctions"]` metadata recording, `analyze_growth_paths` clearance gate ($\ge W + 0.8\text{ mm}$), and deterministic single-seam fallback. |
| `kintsugi.py` | `L2089-L2106` | Update `generate_crack_paths` to dispatch `generator == "shard"` to `generate_shard_crack_paths(params, rng, subdivide_step=subdivide_step)`. Retain `"growth"` and `"voronoi"`. |
| `kintsugi.py` | `L3018-L3022` | Update `generate_kintsugi_mesh` to validate `generator in ("growth", "shard", "voronoi")` and raise `ValueError("generator='shard' is only supported in 'vein' mode in Stage 1")` when `generator == "shard"` and `mode != "vein"`. |
| `kintsugi.py` | `L3270-L3276` | Update CLI `--generator` argument choices to `["growth", "shard", "voronoi"]`. |
| `web_app.py` | `L170-L195` | Verify `POST /api/fracture` accepts `generator="shard"` in `mode="vein"` and returns HTTP 400 Bad Request when `generator="shard"` is paired with `mode="ribbon"`. |
| `tools/spike_contact_sheet.py` | `L45-L70, L370-L400, L420-L505` | Add `--generator {growth,shard,both}` CLI flag, pass `generator` into `generate_kintsugi_mesh`, and default output to `reports/contact_sheet_shard.png` when `--generator shard` is selected. |
| `tests/test_crack_shard.py` | `[NEW]` | Add TDD unit and integration test suite covering open wedge exact truncation, closed loop linear drift bridge closure and cyclic clearance, verified two-seam T-junction with `params["_growth_junctions"]` metadata vs. deterministic fallback, 2D quadrant sub-arc tortuosity ($\tau \ge 1.05$), watertight `Manifold3D` boolean carving via `generate_kintsugi_mesh`, and API HTTP 400 guard. |

## 3. Technical & Architectural Boundaries
- **In-Scope Decisions**:
  - **Metric Semantics ($R$ vs $S$)**: $R \in [0, 1]$ is the vessel reserve metric and $S = 1 - \text{clip}(R, 0, 1)$ is fracture severity. $R = 0.0 \implies S = 1.0$ (most broken/rugged stoneware fracture); $R \ge 1.0 \implies S = 0.0$ (untouched wealthy vessel, 0 seams).
  - **Severity $S$ to Parameter Mapping**:
    - $S < 0.2$ ($R > 0.8$): 0 seams.
    - $0.2 \le S < 0.35$ ($0.65 < R \le 0.8$): 1 seam, Primitive 1 (`rng.uniform() < 0.5` Wedge vs Loop), harmonics $A_{2,3} = 0.015\,\Delta z_{\text{wall}}$, kink $\sigma_\theta = 4^\circ$, target $\tau \in [1.05, 1.10]$.
    - $0.35 \le S < 0.70$ ($0.30 < R \le 0.65$): 1 or 2 seams (attempt Seam 2), Primitive 1 (`rng.uniform() < 0.5` Wedge vs Loop), harmonics $A_{2,3} = 0.035\,\Delta z_{\text{wall}}$, kink $\sigma_\theta = 8^\circ$, target $\tau \in [1.08, 1.20]$.
    - $0.70 \le S \le 1.0$ ($0.0 \le R \le 0.30$): 2 seams (attempt Seam 2), Primitive 1 (`rng.uniform() < 0.5` Wedge vs Loop), harmonics $A_{2,3} = 0.060\,\Delta z_{\text{wall}}$, kink $\sigma_\theta = 14^\circ$, target $\tau \in [1.12, 1.35]$.
  - **Primitive A (Open Rim-to-Rim Wedge Seam)**: Enters at $z = \text{wall\_z\_max} + 0.35W$, dips to $z_{\text{nadir}} \in [\text{wall\_z\_min} + 0.18\,\Delta z_{\text{wall}}, \text{wall\_z\_max} - 0.20\,\Delta z_{\text{wall}}]$, exits above $\text{wall\_z\_max} + 0.35W$, and is truncated at exact crossings via `_truncate_polyline_z(raw, wall_z_min + 0.5*W, wall_z_max + 0.35*W, min_length=3.0*W)` (never `np.clip`).
  - **Primitive B (Closed Tilted Loop Seam)**: Covers $u \in [0, P]$ with baseline tilt $z_{\text{base}}(u) = z_0 + \bar{r}\tan(\alpha)\cos(u/\bar{r} - \phi)$, integer harmonics ($k \in \{2, 3\}$), and linear drift bridge kink walk ($kink_i = w_i - \frac{i}{N-1}(w_{N-1} - w_0)$) so $z(0) = z(P)$ within `1e-6` mm. Cap vertical amplitudes before sampling to fit inside $[\text{wall\_z\_min} + 0.6W, \text{wall\_z\_max} - 0.6W]$; if available height forces $\alpha < 5^\circ$, select Primitive A (Wedge).
  - **Seam 2 & `_growth_junctions` Metadata**: When $S \ge 0.35$, evaluate up to 16 deterministic candidate rim-to-seam wedges. Accept the first candidate that intersects Seam 1 in $[\text{wall\_z\_min} + W, \text{wall\_z\_max} - W]$ at arrival angle $\ge 30^\circ$, truncate Seam 2 at the intersection, insert a shared vertex into Seam 1, append the T-junction record to `params["_growth_junctions"]`, and verify `analyze_growth_paths` passes with `min_clearance >= W + 0.8` mm. Otherwise fall back deterministically to `[Seam 1]`.
- **Hard Exclusions / No-Go**:
  - Do NOT modify `.env`, `.env.*`, or credential files.
  - Do NOT introduce unapproved external dependencies.
  - Do NOT perform code modifications outside the Target Context Map without prior task coverage.
  - Do NOT modify Web GUI frontend files (`static/index.html`, `static/app.js`, `static/styles.css`) in Stage 1.

## 4. Visual & UI Design Specifications
- **Status: Backend geometry generator & batch contact-sheet inspection change (No Web GUI changes in Stage 1).**
- **Contact Sheet Palette (`tools/spike_contact_sheet.py`)**:
  - Background: `#F6F2EA` | Ceramic Body: `#2D2B2A` / `#D8D1C5` | Gold Vein Inlay: `#D4AF37` | Wall Bounds Marker: `#7A6F5D`
- **12-Case Spike Matrix (`reports/contact_sheet_shard.png`)**:
  - 2 vessel presets (`Tea Bowl`, `Tall Vase`) $\times$ 3 reserve levels ($R \in \{0.5, 0.2, 0.0\}$, corresponding to $S \in \{0.5, 0.8, 1.0\}$) $\times$ 2 seeds (`seed=0`, `seed=1`).

## 5. Test Scaffolding & Verification Commands
- **Primary Test Runner**:
  - Targeted TDD suite: `.venv/bin/python -m unittest tests/test_crack_shard.py -v`
  - Full regression suite: `.venv/bin/python -m unittest discover -s tests -p "test_*.py" -v`
- **TDD Requirement**: Task group `## 1` MUST scaffold failing unit/integration tests in `tests/test_crack_shard.py` before touching implementation code in `kintsugi.py`. Verify they fail initially.

## 6. Implementation Task Checklist
- [ ] 1.1 Create `tests/test_crack_shard.py` with failing test `test_open_wedge_seam_exact_truncation_and_rim_landing` verifying that open rim-to-rim wedge seams have no flat-run shelves (no two consecutive points within $1\text{e-}6$ mm of bounds), raw endpoints extend above `wall_z_max` by $\le 0.35W$, and projected 3D endpoints land on the upper rim lip ($z \ge \text{wall\_z\_max} - 0.5W$).
- [ ] 1.2 Add failing test `test_closed_loop_drift_bridge_closure_and_cyclic_clearance` in `tests/test_crack_shard.py` verifying that closed loop seams satisfy `_periodic_distance(path[0], path[-1], period) <= 1e-6` via linear drift bridge, remain strictly within $[\text{wall\_z\_min} + 0.6W, \text{wall\_z\_max} - 0.6W]$, fall back to Primitive A (Wedge) if available wall height forces $\alpha < 5^\circ$, and pass `analyze_growth_paths` with cyclic segment skip across $u=0 \equiv P$.
- [ ] 1.3 Add failing test `test_two_seam_verified_intersection_and_fallback` in `tests/test_crack_shard.py` verifying that for $S \ge 0.35$, when 2 paths are returned, Seam 2 terminates at an exact shared T-junction vertex on Seam 1 inside $[\text{wall\_z\_min} + W, \text{wall\_z\_max} - W]$ at arrival angle $\ge 30^\circ$, `params["_growth_junctions"]` records the junction metadata, `analyze_growth_paths` passes with clearance $\ge W + 0.8\text{ mm}$, and the generator deterministically falls back to `[Seam 1]` if 16 candidate draws fail.
- [ ] 1.4 Add failing test `test_closed_loop_quadrant_subarc_tortuosity` in `tests/test_crack_shard.py` verifying that `_tortuosity_values` splits closed periodic loops into 4 quadrant sub-arcs in 2D $(u, z)$ space, producing finite tortuosity values satisfying $\tau \ge 1.05$ across $R \in \{0.5, 0.2, 0.0\}$ ($S \in \{0.5, 0.8, 1.0\}$) with median tortuosity increasing monotonically as $R$ decreases from $0.5$ to $0.0$.
- [ ] 1.5 Add failing test `test_generate_kintsugi_mesh_shard_mode_watertight_and_ribbon_guard` in `tests/test_crack_shard.py` verifying that `generate_kintsugi_mesh(..., mode="vein", generator="shard")` produces watertight ceramic and gold meshes with zero bad edges on Tea Bowl and Tall Vase, and raises `ValueError` when invoked with `mode="ribbon"`.
- [ ] 1.6 Add failing test `test_api_fracture_shard_mode_validation` in `tests/test_crack_shard.py` verifying that `POST /api/fracture` accepts `generator=shard` in `mode=vein`, and returns HTTP status 400 Bad Request when called with `generator=shard` and `mode=ribbon`.
- [ ] 2.1 Update `analyze_growth_paths` in `kintsugi.py` (`L1996-L2002`) so paths that are closed periodic loops (`_periodic_distance(path[0], path[-1], period) <= 1e-6`) compute adjacent segment skip span cyclically (`min(diff, n_path_segs - diff) <= skip_span`).
- [ ] 2.2 Update `_tortuosity_values` in `kintsugi.py` (`L1912-L1948`) so closed periodic loops without split junctions are split into 4 equal quadrant sub-arcs ($\Delta u = P / 4$) in 2D $(u, z)$ space before computing arc over chord, enforcing the engine floor $\tau \ge 1.05$.
- [ ] 3.1 Implement `generate_shard_crack_paths(params: dict, rng: np.random.Generator, *, subdivide_step: float | None = None) -> list[np.ndarray]` in `kintsugi.py` (`L2080-L2110`) supporting Primitive A (Wedge with `_truncate_polyline_z`) and Primitive B (Loop with linear drift bridge closure and height capping).
- [ ] 3.2 Implement candidate Seam 2 evaluation ($\le 16$ deterministic draws), arrival-angle check ($\ge 30^\circ$), shared T-junction vertex insertion, `params["_growth_junctions"]` metadata recording, `analyze_growth_paths` clearance gate ($\ge W + 0.8\text{ mm}$), and single-seam fallback in `generate_shard_crack_paths`.
- [ ] 3.3 Wire `generate_crack_paths` (`L2089-L2106`) to dispatch `generator == "shard"` to `generate_shard_crack_paths`. Update `generate_kintsugi_mesh` (`L3018-L3022`) to validate `generator in ("growth", "shard", "voronoi")` and raise `ValueError` if `generator == "shard"` and `mode != "vein"`. Update CLI argument parser in `kintsugi.py` (`L3270-L3276`).
- [ ] 4.1 Update `tools/spike_contact_sheet.py` (`L45-L70, L370-L400, L420-L505`) to accept `--generator {growth,shard,both}`, pass `generator` into `generate_kintsugi_mesh`, and default output to `reports/contact_sheet_shard.png` for `shard`.
- [ ] 4.2 Render `reports/contact_sheet_shard.png` via `.venv/bin/python tools/spike_contact_sheet.py --generator shard --output reports/contact_sheet_shard.png` and verify all 12 cells complete cleanly.
- [ ] 5.1 Run `.venv/bin/python -m unittest tests/test_crack_shard.py -v` and the full regression suite `.venv/bin/python -m unittest discover -s tests -p "test_*.py" -v`, verifying 100% pass rate and zero regressions.
- [ ] 5.2 Populate `verification.md` with Requirement Adherence Matrix, resolved assumptions, contact sheet comparison summary, and verbatim execution logs.
- [ ] 5.3 Perform visual inspection of `reports/contact_sheet_shard.png` side-by-side with `reports/contact_sheet.png` across all 12 cells.
- [ ] 5.4 Human review and decision on future default generator (`growth` vs `shard`).

## 7. Post-Implementation & Verification Obligations
When `spec-coder-sub` finishes:
1. Verify all automated checkboxes (`1.1`–`5.2`) in `tasks.md` are marked `- [x]`. Leave human-only tasks (`5.3`, `5.4`) unchecked (`- [ ]`) for user visual sign-off. Only tick boxes that genuinely ran and passed.
2. Check data preservation: confirm all existing presets and tests pass with zero regressions.
3. Ensure `openspec/changes/kintsugi-shard-seams/verification.md` is populated with:
   - Executive Summary & Environment
   - Requirement Adherence Audit Matrix (mapping every spec scenario to its verifying test)
   - Resolved Assumptions & Empirical Proof
   - Nomenclature & Code Symbol Audit
   - Verbatim Execution Logs
4. Automatically run verification via `openspec-verify-change`.
5. If clean with no critical issues, sync specs: `openspec specs apply --change "kintsugi-shard-seams"`.
