# Patch Ledger: ceramic-vessel-wall-envelope

## Patch Ledger

| Patch ID | Date | Trigger / Feedback Source | Target Files | Status |
| :--- | :--- | :--- | :--- | :--- |
| `PATCH-01` | 2026-11-08 | Code Review (Agent 1 & Agent 2, PR #2 head `257d94d`) | `kintsugi.py`, `tests/test_envelope.py`, `tests/test_kintsugi.py`, `tests/test_web_api.py` | **RESOLVED** |

---

### [PATCH-01] Flared-Wall Normal Probing Tests, Tapered-Lip Backing Audit & Defensive Pipeline Verification
- **Date**: 2026-11-08 00:15:00 UTC
- **Feedback Source**: Code Review (Agent 1 & Agent 2 Review of PR #2 Head `257d94d`)
- **Reported Issue**:
  1. The test suite only tested vertical cylinders where radial and normal measurements are identical; a 45° flared wall with 1.2 mm normal thickness reads ~1.7 mm radially and needs an explicit rejection test.
  2. In `project_crack_paths`, if the normal ray misses, falling back unconditionally to radial thickness reintroduces the flared-wall overestimate.
  3. "d >= 0.6 mm everywhere" and "0.8 mm backing everywhere" were overclaimed in docstrings/verification text; p5 allows up to 5% below 1.6 mm. A tapered-lip fixture is needed to prove continuous vein carving on varying walls and measure minimum carved depth/backing.
  4. Exact float compare `abs(gold_mesh.volume) <= 0.0` in `_gold_solid_omitted` should use numeric tolerance `1e-6`.
  5. The empty-gold test tested exports directly but did not exercise `generate_kintsugi_mesh` and API responses end-to-end.
  6. Task 2.3 in `tasks.md` claimed an edit to `sweep_out_of_sample.py` when no change was needed.
- **Root Cause**: Scaffolding relied on vertical cylinder fixtures; percentile nuance was conflated with absolute minimums in documentation text; ray-miss fallback was unconstrained.
- **Target Files**: `tests/test_envelope.py`, `tests/test_kintsugi.py`, `tests/test_web_api.py`, `kintsugi.py`, `openspec/changes/ceramic-vessel-wall-envelope/tasks.md`, `openspec/changes/ceramic-vessel-wall-envelope/verification.md`
- **Expected Resolution**:
  - Revolved flared-cone fixture pair passes: 1.2 mm normal thickness rejected ($p_5 < 1.6$), 2.0 mm accepted ($p_5 \approx 2.0$).
  - Normal ray miss fallback uses $\min(t_{\text{normal}}, t_{\text{radial}})$.
  - Tapered-lip fixture passes $p_5 \ge 1.6$, produces continuous watertight gold, and reports minimum carved depth & backing.
  - Float tolerance `1e-6` in `_gold_solid_omitted`.
  - Empty-gold test covers end-to-end API pipeline with monkeypatched empty cutter.
  - All tests pass with zero regressions.
- **Resolution**:
  1. Added `_flared_cone` / `_write_flared_cone` fixtures and `test_envelope_flared_cone_normal_thickness_rejection`. The 45° 1.2 mm-normal cone is rejected even though its radial median is 1.697 mm; the 2.0 mm-normal cone is accepted at $p_5=2.002$ mm and fractures successfully.
  2. `project_crack_paths` now computes both normal and radial thickness. When both exist it uses `min(t_normal, t_radial)`; when the normal ray misses, the radial value is marked for the path-median bound and the fill pass keeps the smaller value.
  3. Added `_tapered_lip_manifold` and `test_tapered_lip_continuous_vein_and_backing`: 2.4 mm body tapering to 1.0 mm over the top 3 mm. Measured $p_5=2.404$ mm, $t_{\min}=1.114$ mm, $d_{\min}=0.557$ mm, nominal backing minimum $0.557$ mm, and $\ge 0.839$ mm wherever $t_i \ge 1.6$ mm. Gold is watertight with zero bad edges.
  4. `_gold_solid_omitted` now uses `1e-6` mm³ volume tolerance for both the manifold and the exported mesh.
  5. Added `test_api_fracture_empty_gold_pipeline`, which patches `_build_vein_cutter` to return an empty manifold and exercises `POST /api/fracture` end-to-end: `seams_omitted: true`, `gold_path: None`, `volumes.gold: 0.0`, `triangle_counts.gold: 0`, and a ceramic STL download.
  6. Docstrings, `tasks.md`, and `verification.md` now state the precise guarantee: nominal backing $\ge 0.5 \cdot t_i$ everywhere, and $\ge 0.8$ mm wherever $t_i \ge 1.6$ mm.
- **Verification Command**: `.venv/bin/python -m unittest discover -s tests -v`
- **Verification Proof**: `Ran 57 tests in 246.504s ... OK`; targeted PATCH-01 suites `Ran 54 tests ... OK`; the baseline pre-patch full profile was green with 0 crossings and 0 cutter retries, and the PATCH-01 full-profile audit was still running against the pushed tree at commit time (see `verification.md`).
- **Status**: **RESOLVED** on 2026-11-08
