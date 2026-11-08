# Patch Ledger: ceramic-vessel-wall-envelope

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
- **Status**: PENDING
