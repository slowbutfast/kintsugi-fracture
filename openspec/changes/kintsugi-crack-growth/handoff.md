# OpenCode Orchestration Handoff: OpenSpec Change 'kintsugi-crack-growth'

You are the orchestration agent for OpenSpec change 'kintsugi-crack-growth' running in OpenCode.
Your primary directive is to execute this change using the **`openspec-apply-sub`** skill, which delegates task implementation to the `spec-coder-sub` subagent.

## 1. Orchestration Directive
- **Change Name**: `kintsugi-crack-growth`
- **Target Skill**: `openspec-apply-sub` (or `/opsx:apply-sub kintsugi-crack-growth`)
- **Architecture Paradigm**: Procedural 3D Computational Geometry pipeline with drop-in generator modularity (`generate_crack_growth_paths`). Preserve strict mathematical isolation and watertight CSG guarantees.

## 2. Target Context Map
| File Path (relative to repo root) | Target Lines | Modification Summary |
|---|---|---|
| `kintsugi.py` | L719–L860 | Implement `generate_crack_growth_paths` (Poisson rim seeds, random-walk downward heading $\pm 60^\circ$, acute branching $30^\circ\text{–}45^\circ$, stop-on-hit first-contact snapping, shared vertex subdivision, junction exemption zone, and $\pm 2\pi\bar{r}$ seam wrapping). Retain legacy Voronoi generator as `generate_crack_voronoi_paths`. |
| `kintsugi.py` | L994–L1080 | Update `_build_vein_cutter`: enforce depth formula $d_i = \min(0.75W, 0.5t_i, t_i - 0.8\text{ mm})$ and omit points where $d_i < 0.25\text{ mm}$ (splitting polylines) to prevent tangent kissing-edge contact. |
| `kintsugi.py` | L1437–L1550 | In `generate_kintsugi_mesh`, accept `generator: str = "growth"` parameter, routing to growth or Voronoi generator. |
| `kintsugi.py` | L1650–L1736 | In CLI argument parser, expose `--generator {growth,voronoi}` defaulting to `growth`. |
| `sample_models.py` | L100–L124 | Add `create_thin_cylinder_preset` (synthetic thin vessel, wall 1.2 mm tapering to 0.7 mm) to exercise thin-wall vein carving and the 0.25 mm cutoff. |
| `tools/spike_contact_sheet.py` | `[NEW]` | Standalone contact sheet generator rendering Tea Bowl, Tall Vase, and Thin Cylinder into a 12-image matrix (`output/spike/contact_sheet.png`) for visual review. |
| `tools/growth_audit.py` | `[NEW]` | Audit script over held-out seeds 300–499 measuring planarity (0 crossings), minimum clearance ($\ge W + 0.8\text{ mm}$ outside exemption), incidence angles ($\ge 30^\circ$), T vs Y junction ratio, and tortuosity distribution. |
| `tools/test_report.py` | L50–L420 | Add `growth_audit` suite, support `--generator growth` in sweep runs, and implement `--renders` generating `reports/contact_sheet.png`. |
| `tools/sweep_out_of_sample.py` | L30–L80 | Add `--generator` CLI argument (defaulting to `growth`). |
| `static/index.html` | L65–L85 | Set **Vein Inlay** (`vein`) as the default pre-checked radio option. |
| `web_app.py` | L50–L80 | Update `FractureRequest` schema default `mode: str = "vein"` and optional `generator: str = "growth"`. |
| `tests/test_kintsugi.py` | L1080+ | Add failing TDD invariant tests (`test_growth_paths_planar_and_tjunc`, `test_vein_depth_and_kissing_prevention`, `test_growth_rim_seeding_and_penetration`, `test_thin_wall_model_manifold`, `test_growth_tortuosity_floor`). |
| `tests/test_kintsugi.py` | Existing Voronoi tests | Triage tests asserting Voronoi geometry (e.g. `test_crack_paths_lie_on_periodic_voronoi`) to pass `generator="voronoi"` explicitly. |

## 3. Technical & Architectural Boundaries
- **In-Scope Decisions**:
  - **First-Contact Snapping**: Advancing segment snaps to earliest contact point $\mathbf{p}_{\text{hit}}$ within $R_{\text{clear}} = W + 0.8\text{ mm}$ and subdivides the hit segment with a shared vertex.
  - **Junction Exemption Zone**: Proximity checks ignore parent and incident segments within $R_{\text{exempt}} = \frac{W + 0.8\text{ mm}}{\sin \theta}$.
  - **Zero-Depth Kissing Prevention**: Cutter points with $d < 0.25\text{ mm}$ are omitted from cutter solid generation, splitting polylines.
  - **Rim Projection Clamp**: Points with $z \ge \text{wall\_z\_max}$ cast radial ray at $z = \text{wall\_z\_max} - 0.05\text{ mm}$ to guarantee hitting the vessel lip.
- **Hard Exclusions / No-Go**:
  - Do NOT modify `.env`, `.env.*`, or credential files.
  - Do NOT add new third-party dependencies (no `networkx`, no extra graph packages).
  - Do NOT expose Voronoi toggles in the end-user Web GUI (Voronoi is strictly an internal CLI/dev flag).
  - Do NOT allow tangent cutter contacts ($d \to 0$); always omit points $< 0.25\text{ mm}$.

## 4. Visual & UI Design Specifications
- **Theme**: Windows XP Luna Retro Minimalist (Kintsugi Growth Edition)
- **Key Tokens**:
  - Primary: `#0058ee` (Titlebar Royal Blue) | Secondary: `#70c040` (Action Green)
  - Surface: `#ece9d8` (Classic Window Canvas) | Background: `#3a6ea5` (Bliss Desktop)
  - Text: Primary `#222222`, Muted `#555555`
  - Gold Seam: `#ffd700` (PBR metallic gold, roughness 0.18, metalness 0.92)
- **Component Anatomy & States**:
  - Mode Selector: Radio group pre-selecting **Vein Inlay** (`vein`) by default.
  - Viewport: Three.js WebGL canvas displaying matte ceramic (`#f8f6f0`) and metallic gold fissures.
- **Visual Morphology Guidelines**:
  - Primary trunks originate at Poisson-spaced rim seeds and cascade downwards.
  - Acute branching ($30^\circ\text{–}45^\circ$) with child whisker fissures.
  - True T-junctions ($> 80\%$ meeting at $\ge 140^\circ$), completely eliminating Voronoi honeycomb cell tiles.
  - Jittered penetration depth preventing flat horizontal shelf lines.

## 5. Test Scaffolding & Verification Commands
- **Primary Test Runner**:
  ```bash
  .venv/bin/python -m unittest discover -s tests -v
  ```
- **TDD Requirement**: Task group ## 1 MUST scaffold failing unit tests before touching implementation code. Verify they fail initially.
- **Full Profile Verification**:
  ```bash
  .venv/bin/python tools/test_report.py run --profile full --renders
  ```

## 6. Implementation Task Checklist

### 1. Test Scaffolding (TDD - Hard Invariants)
- [ ] 1.1 Scaffold failing test `test_growth_paths_planar_and_tjunc` in `tests/test_kintsugi.py` asserting zero crossings, shared T-junctions, clearance $\ge W + 0.8\text{ mm}$ outside exemption zone, and $\ge 30^\circ$ angles
- [ ] 1.2 Scaffold failing test `test_vein_depth_and_kissing_prevention` in `tests/test_kintsugi.py` asserting $d_i \le t_i - 0.8\text{ mm}$ and omission of cutter points where $d_i < 0.25\text{ mm}$
- [ ] 1.3 Scaffold failing test `test_growth_rim_seeding_and_penetration` in `tests/test_kintsugi.py` asserting Poisson rim spacing and non-flat jittered penetration termination
- [ ] 1.4 Scaffold failing test `test_thin_wall_model_manifold` in `tests/test_kintsugi.py` testing vein mode on a 1.2 mm / 0.7 mm thin-wall vessel
- [ ] 1.5 Triage existing unit tests in `tests/test_kintsugi.py`: ensure tests asserting Voronoi geometry (e.g. `test_crack_paths_lie_on_periodic_voronoi`) pass `generator="voronoi"` explicitly so flipping the default does not cause false failures

### 2. Spike Implementation & Visual Contact Sheet
- [ ] 2.1 Implement `generate_crack_growth_paths` in `kintsugi.py` behind `--generator growth|voronoi` flag, implementing Poisson rim seeding, random-walk heading, acute branching ($30^\circ\text{–}45^\circ$), first-hit snapping, and junction exemption
- [ ] 2.2 Add synthetic `thin_cylinder` preset (wall 1.2 mm tapering to 0.7 mm) to `sample_models.py`
- [ ] 2.3 Implement contact sheet generator in `tools/spike_contact_sheet.py` and generate preliminary $4 \times 3$ contact sheet in `output/spike/contact_sheet.png`
- [ ] 2.4 Review `output/spike/contact_sheet.png` against reference Kintsugi morphology and record visual sign-off in `verification.md`

### 3. Core Engine Hardening & Tooling
- [ ] 3.1 Update `_build_vein_cutter` in `kintsugi.py` to enforce the $d < 0.25\text{ mm}$ point omission cutoff, splitting polylines to prevent tangent kissing contacts, with dense sampling $\le W/2$
- [ ] 3.2 Build `tools/growth_audit.py` to evaluate planarity, clearance, incidence angles, T vs Y junction ratio, and tortuosity distribution over seeds 300–499
- [ ] 3.3 Update `tools/test_report.py` and `tools/sweep_out_of_sample.py` to support `--generator growth` and add `--renders` to output `reports/contact_sheet.png`
- [ ] 3.4 Update `static/index.html` and `web_app.py` to make **Vein Inlay** (`vein`) the default fracture mode

### 4. Verification, Slicer Audit & Deprecation
- [ ] 4.1 Run full regression test suite (`.venv/bin/python -m unittest discover -s tests -v`) and verify all tests pass cleanly
- [ ] 4.2 Run `tools/growth_audit.py` on seeds 300–499 and verify 0 crossings, $\ge 80\%$ T-junctions, and median tortuosity $\ge 1.05$
- [ ] 4.3 Run full 160-sample held-out sweep with growth generator (`.venv/bin/python tools/test_report.py run --profile full --renders`) and confirm 0 non-watertight meshes and 0 cutter retries
- [ ] 4.4 Perform thin-wall slicing check of `kintsugi_assembly.3mf` from `thin_cylinder` in Bambu Studio / PrusaSlicer and record part count and toolpath backing evidence
- [ ] 4.5 Populate `verification.md` with Requirement Adherence Matrix, tortuosity metric statistics, resolved assumptions, and schedule legacy Voronoi deprecation

## 7. Post-Implementation & Verification Obligations
When `spec-coder-sub` finishes:
1. Verify all checkboxes in `tasks.md` are marked `- [x]`. Only tick boxes that genuinely ran and passed.
2. Check data preservation: confirm watertightness and zero retries across sweeps.
3. Ensure `openspec/changes/kintsugi-crack-growth/verification.md` is populated with:
   - Executive Summary & Environment
   - Requirement Adherence Audit Matrix (mapping every spec scenario to its verifying test)
   - Resolved Assumptions & Empirical Proof
   - Tortuosity distribution and T-junction ratio metrics
   - Verbatim Execution Logs
4. Automatically run verification via `openspec-verify-change`.
5. If clean with no critical issues, sync specs: `openspec specs apply --change "kintsugi-crack-growth"`.
