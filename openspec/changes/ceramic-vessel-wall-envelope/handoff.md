# OpenCode Orchestration Handoff: OpenSpec Change 'ceramic-vessel-wall-envelope'

You are the orchestration agent for OpenSpec change 'ceramic-vessel-wall-envelope' running in OpenCode.
Your primary directive is to execute this change using the **`openspec-apply-sub`** skill, which delegates task implementation to the `spec-coder-sub` subagent.

## 1. Orchestration Directive
- **Change Name**: `ceramic-vessel-wall-envelope`
- **Target Skill**: `openspec-apply-sub` (or `/opsx:apply-sub ceramic-vessel-wall-envelope`)
- **Architecture Paradigm**: Vertical Slice Architecture (VSA). Maintain strict isolation between feature compartments and avoid horizontal abstractions.
- **Repository Root**: `/home/node/global-sandbox/projects/wax-robot`

## 2. Target Context Map

| File Path (relative to repo root) | Target Lines | Modification Summary |
|---|---|---|
| `tests/test_envelope.py` | `[NEW]` | Scaffold failing unit tests: `test_envelope_rejection_thin_mesh` (asserting `ValueError` on ~1.5 mm cylinder and `thin_cylinder`), `test_envelope_acceptance_near_boundary` (accepting ~1.7 mm cylinder), and direct unit test of boundary comparison at $1.60\text{ mm}$. |
| `tests/test_kintsugi.py` | `L1170–L1250` | Scaffold failing test `test_continuous_vein_depth_no_omissions` asserting $d_i = \min(0.75W, 0.5t_i)$ and zero omitted points. Repoint any `thin_cylinder` tests to negative envelope tests or supported ceramic fixtures. |
| `tests/test_crack_growth.py` | `L200–L260` | Add regression assertions verifying PATCH-02 growth invariants: final-attempt near-miss snapping at $\ge 30^\circ$, 20% kink probability with $\sigma = 18^\circ$, median tortuosity $\ge 1.05$, and 0 crossings. |
| `kintsugi.py` | `L381–L460` | In `validate_and_load_mesh`, probe two-hit wall thickness along inward surface normals $-n_i$ across `[wall_z_min, wall_z_max]` (independent of $R$). Reject if $p_5 < 1.6\text{ mm}$ with `ValueError` across all fracture modes (`vein` and `ribbon`). |
| `kintsugi.py` | `L728` | Remove `GROWTH_MIN_DEPTH_MM = 0.25`. |
| `kintsugi.py` | `L2130–L2250` | In `project_crack_paths`, clamp rim projection at $z = \text{wall\_z\_max} - \max(0.5, W/2)$ to avoid tapered rim lips. Record $t_i$ as distance along inward surface normal $-n_i$. |
| `kintsugi.py` | `L2330–L2480` | In `_build_vein_cutter`, restore continuous $d_i = \min(0.75W, 0.5t_i)$; remove `_vein_point_groups` and sub-0.25 mm point omissions. Ensure `_gold_solid_omitted` remains False on valid ceramic runs ($R < 1.0$) and True only on wealthy pass-throughs ($R \ge 1.0$) or degenerate empty booleans. |
| `sample_models.py` | `L50–L135` | Remove `thin_cylinder` from `PRESETS` registry and drop alias; delete `presets/thin_cylinder.stl`; provide `create_thin_cylinder_fixture` strictly for negative test use. |
| `web_app.py` | `L135–L145, L200–L220` | Handle wall thickness rejection `ValueError` in `/api/validate` and `/api/fracture` gracefully; clean up `seams_omitted_reason`. |
| `static/viewer.js` | `L405–L415` | Remove stale `"wall thickness < 1.05 mm"` fallback text; display clean `Seams Omitted` if $R < 1.0$ and seams are omitted. |
| `tools/test_report.py` | `L150–L220` | Remove `thin_cylinder` preset entry from test sweep configurations. |
| `tools/sweep_out_of_sample.py` | `L40–L80` | Ensure out-of-sample sweeps run against supported ceramic models (`tea_bowl`, `vase`). |
| `tools/spike_contact_sheet.py` | `L30–L90` | Update 12-case contact sheet matrix to use supported ceramic models (Tea Bowl, Tall Vase). |

## 3. Technical & Architectural Boundaries
- **In-Scope Decisions**:
  - Preflight normal wall thickness probing: sample across R-independent wall range `[wall_z_min, wall_z_max]` using inward surface normals $-n_i$. Reject if $p_5 < 1.6\text{ mm}$ across all modes (`vein` and `ribbon`).
  - Classical continuous vein depth: restore $d_i = \min(0.75W, 0.5t_i)$. Guarantee nominal ceramic backing $\ge 0.5 \cdot t_i$ everywhere and $\ge 0.8\text{ mm}$ wherever $t_i \ge 1.6\text{ mm}$. Minimum depth for valid runs is $0.6\text{ mm}$.
  - Rim lip protection: clamp rim projection at $z = \text{wall\_z\_max} - \max(0.5, W/2)$.
  - Remove all point dropping logic (`GROWTH_MIN_DEPTH_MM`, `_vein_point_groups`).
  - Clean up presets: delete `presets/thin_cylinder.stl` and remove it from UI dropdown; keep fixture for negative unit tests only.
  - Reconcile export: retain `_gold_solid_omitted` safeguard for $R \ge 1.0$ and empty-gold fallbacks.
- **Hard Exclusions / No-Go**:
  - Do NOT modify `.env`, `.env.*`, or credentials.
  - Do NOT introduce unapproved external dependencies (maintain zero-new-dependencies policy with `trimesh`, `manifold3d`, `scipy`, `numpy`).
  - Do NOT perform code modifications outside the Target Context Map without prior task coverage.
  - Do NOT dynamically inflate or alter geometry of sub-1.6 mm meshes; reject with `ValueError`.

## 4. Visual & UI Design Specifications
- **Theme**: Windows XP Luna Retro Minimalist (Ceramic Envelope Edition)
- **Key Tokens**:
  - Primary: `#0058ee` (Luna Royal Blue) | Secondary: `#70c040` (Emerald Green)
  - Surface: `#ece9d8` (Dialog Gray) | Surface-Inset: `#f0ede0`
  - Text: Primary `#222222` (Tahoma), Muted `#555555`
  - Status: Success `#3e8e18`, Warning `#e68a00`, Error `#e81123`
- **Component Anatomy & States**:
  - `#status-bar`: Inset 3D sunken well. Displays `Watertight ✓ | Vertices: N | Wall: X.XX mm` on valid models, `Not a valid closed solid: Wall thickness (X.XX mm) < 1.60 mm required` on rejection, `Pristine / Wealthy (0 cracks)` for $R \ge 1.0$, and `Seams Omitted` for empty gold fallback.
- **Visual Contact Sheet (12-case matrix)**:
  - Generate `reports/contact_sheet.png` across Japanese Tea Bowl and Tall Vase at $R \in \{0.0, 0.2, 0.5\}$ (2 seeds each) for visual evaluation.

## 5. Test Scaffolding & Verification Commands
- **Primary Test Runner**: `.venv/bin/python -m unittest discover -s tests -v`
- **Targeted Test Commands**:
  - `tests/test_envelope.py`: `.venv/bin/python -m unittest tests/test_envelope.py -v`
  - `tests/test_kintsugi.py`: `.venv/bin/python -m unittest tests/test_kintsugi.py -v`
  - `tests/test_crack_growth.py`: `.venv/bin/python -m unittest tests/test_crack_growth.py -v`
  - Full Report Sweep: `.venv/bin/python tools/test_report.py run --profile full --renders`
- **TDD Requirement**: Task group ## 1 MUST scaffold failing unit tests for envelope rejection, boundary acceptance, and continuous vein depth BEFORE touching implementation code. Confirm they fail initially.

## 6. Implementation Task Checklist

### 1. Test Scaffolding (TDD)
- [ ] 1.1 Write failing test `test_envelope_rejection_thin_mesh` in `tests/test_envelope.py` asserting `ValueError` on meshes with $p_5 < 1.6\text{ mm}$ (testing ~1.5 mm cylinder and `thin_cylinder` fixture)
- [ ] 1.2 Write failing test `test_envelope_acceptance_near_boundary` in `tests/test_envelope.py` asserting acceptance on mesh with $p_5 \approx 1.7\text{ mm}$, plus boundary comparison unit test at $1.60\text{ mm}$
- [ ] 1.3 Write failing test `test_continuous_vein_depth_no_omissions` in `tests/test_kintsugi.py` asserting $d_i = \min(0.75W, 0.5t_i)$ and absence of point omission splitting
- [ ] 1.4 Add regression tests in `tests/test_crack_growth.py` for shipped PATCH-02 morphology (final-attempt bend snap, 20% kink rate with $\sigma = 18^\circ$, median tortuosity $\ge 1.05$)

### 2. Preflight Normal Wall Thickness & Envelope Validation
- [ ] 2.1 Update `validate_and_load_mesh` in `kintsugi.py` to probe inward surface normal wall thickness across `[wall_z_min, wall_z_max]` and reject $p_5 < 1.6\text{ mm}$ with `ValueError` across all modes
- [ ] 2.2 Delete `presets/thin_cylinder.stl`, remove `thin_cylinder` from `sample_models.PRESETS`, remove alias, and provide `create_thin_cylinder_fixture` in `sample_models.py` strictly for negative tests
- [ ] 2.3 Update all `thin_cylinder` call sites: `test_web_api.py:95`, `test_kintsugi.py:1175, 1201`, `spike_contact_sheet.py`, `test_report.py`, and `sweep_out_of_sample.py`
- [ ] 2.4 Update `web_app.py` `/api/validate` and `/api/fracture` to handle wall thickness `ValueError` cleanly

### 3. Continuous Vein Depth & Simplified Cutter
- [ ] 3.1 In `kintsugi.py`, restore $d_i = \min(0.75W, 0.5t_i)$ using normal wall thickness, remove `GROWTH_MIN_DEPTH_MM`, `_vein_point_groups`, and sub-0.25 mm point omissions
- [ ] 3.2 Clamp rim crack projection at $\text{wall\_z\_max} - \max(0.5, W/2)$ in `kintsugi.py` to protect tapered rim lips
- [ ] 3.3 Ensure `_gold_solid_omitted` remains False on all valid ceramic runs ($R < 1.0$), True on wealthy pass-throughs ($R \ge 1.0$), and handles empty-gold boolean fallback for both STL and 3MF
- [ ] 3.4 Update `viewer.js:410` to remove stale "wall thickness < 1.05 mm" text and clean up `seams_omitted_reason` in `web_app.py`

### 4. Morphology Regression Gating & Sweeps
- [ ] 4.1 Confirm regression test passes for final-attempt bend snapping and correlated random walk in `tests/test_crack_growth.py`
- [ ] 4.2 Update test sweep tools (`tools/test_report.py`, `tools/sweep_out_of_sample.py`) to run on supported ceramic presets (`tea_bowl`, `vase`)

### 5. Verification & Empirical Audit
- [ ] 5.1 Run full regression test suite (`unittest discover -s tests -v`) and verify 100% clean passes without regressions
- [ ] 5.2 Generate 12-case visual contact sheet (`reports/contact_sheet.png`) and conduct human sign-off against Kintsugi references
- [ ] 5.3 Verify multi-material 3MF import in Bambu Studio / PrusaSlicer
- [ ] 5.4 Populate `verification.md` with Requirement Adherence Matrix, resolved assumptions, and verbatim execution logs

## 7. Post-Implementation & Verification Obligations
When `spec-coder-sub` finishes:
1. Verify all checkboxes in `tasks.md` are marked `- [x]`. Only tick boxes that genuinely ran and passed.
2. Confirm test suite pass count remains $\ge 44$ and clean sweeps report 0 retries.
3. Ensure `openspec/changes/ceramic-vessel-wall-envelope/verification.md` is populated with:
   - Executive Summary & Environment
   - Requirement Adherence Audit Matrix (mapping every spec scenario to its verifying test)
   - Resolved Assumptions & Empirical Proof
   - Nomenclature & Code Symbol Audit
   - Verbatim Execution Logs
4. Run verification via `openspec-verify-change`.
5. If clean with no critical issues, sync specs: `openspec specs apply --change "ceramic-vessel-wall-envelope"`.
