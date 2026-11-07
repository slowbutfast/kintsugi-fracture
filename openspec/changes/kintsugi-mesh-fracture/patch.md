# OpenSpec Change 'kintsugi-mesh-fracture' Patch History

### [PATCH-01] Remediate F18 noise folding, F19 rim break-through, and F20 API assertion
- **Date**: 2026-11-07 05:17:00 UTC
- **Feedback Source**: Multi-Agent Verification Audit (Rounds 3 & Cross-Platform Review)
- **Reported Issue**:
  - **F18**: `_make_noise` in `kintsugi.py` generates noise fields with gradients up to 3.41 ($|\nabla \eta| > 1$). In 59% of seeds (703/1200), the noise displacement folds over itself, causing loops and self-intersecting cracks.
  - **F19**: Cracks truncate $W/2$ below the vessel rim (`wall_z_max - 0.5 * W`), losing the characteristic Kintsugi feature of cracks running over the lip.
  - **F20**: The `guard_evaluations` field added to the `web_app.py` `/api/fracture` response lacks a test assertion in `tests/test_web_api.py` and documentation in `verification.md`.
- **Root Cause**:
  - `_make_noise` gives every octave the same spatial gradient amplitude ($base\_amplitude / rbar$), so summing across 4 octaves yields gradients $\approx 4 \times base\_amplitude / rbar > 1.0$.
  - `z_wall_hi` truncation strictly bounds polylines below the top rim without overshooting across the rim face.
  - `test_web_api.py` checks response fields but omitted `guard_evaluations`.
- **Target Files**: `kintsugi.py`, `tests/test_kintsugi.py`, `tests/test_web_api.py`, `tools/test_report.py`
- **Expected Resolution**:
  - `tools/noise_fold_audit.py` reports `fold_area == 0.0%`, `max_grad <= 0.7`, and 0 crossings with noise on.
  - Cracks at the top rim break through the lip (`wall_z_max + W`) without causing non-manifold or kissing face defects.
  - `test_api_fracture_*` asserts `guard_evaluations >= 1`.
  - `tools/test_report.py` has `KNOWN_OPEN` empty.
- **Status**: RESOLVED
