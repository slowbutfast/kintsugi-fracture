# Surgical Patch Handoff: OpenSpec Change 'kintsugi-mesh-fracture' [PATCH-01]

## 1. Executive Objective & Diagnostic Feedback
- **Change Name**: `kintsugi-mesh-fracture`
- **Patch ID**: `PATCH-01`
- **Objective**: Fix noise-on folding/crossings (F18), allow cracks to break cleanly through the vessel rim (F19), add `guard_evaluations` API test coverage (F20), and lift the `KNOWN-FAIL` exemption so the test report suite passes unconditionally.
- **Feedback & Diagnostic Trace**:
  ```text
  1. F18 (noise folding):
     tea_bowl S=0.6  fold area mean 21.8% max 26.1%  max|grad eta| 3.41  crossings (noise on) 703/1200
     With noise on, 59% of seeds produce crossing or knotted cracks due to unbounded noise gradients (|grad eta| > 1.0).

  2. F19 (rim truncation):
     Cracks that run into the rim truncate at wall_z_max - 0.5 * W, stopping W/2 below the lip.
     At S=1.0, 30% of crack ends fail to break through the rim, missing the signature Kintsugi lip fracture.

  3. F20 (unasserted API field):
     web_app.py returns "guard_evaluations" in the /api/fracture payload, but tests/test_web_api.py never asserts its presence or value.

  4. KNOWN_OPEN exemption:
     tools/test_report.py currently exempts noise_fold with KNOWN_OPEN = {"noise_fold": "F18"}.
  ```
- **Root Cause Analysis**:
  - In `_make_noise`, every octave's amplitude scales as $base\_amplitude \cdot 2^{-k}$ while spatial frequency scales as $2^k / rbar$. The product (gradient amplitude) is constant across all 4 octaves ($base\_amplitude / rbar$), summing to $4 \times base\_amplitude / rbar$. When $base\_amplitude$ scales with spacing, the gradient exceeds 1.0, destroying injectivity and causing folds ($\det J < 0$).
  - `z_wall_hi` truncates polylines strictly below the top wall probe. To let cracks break through the rim, polylines should extend to `wall_z_max + W`, with any vertices above `wall_z_max` projected via ray cast at `wall_z_max - 0.05` to avoid non-manifold coplanar faces on the horizontal rim plane.
  - `tests/test_web_api.py` checks result keys but omitted `guard_evaluations`.

---

## 2. Strict Target Context Map

| File Path (relative to repo root) | Target Lines | Modification Summary |
|---|---|---|
| `kintsugi.py` | `L438-L460` | In `_make_noise`, scale octave amplitudes such that the maximum spatial gradient across all octaves is provably bounded ($\le 0.70 < 1.0$). Ensure $\det J > 0$ everywhere. |
| `kintsugi.py` | `L147-L155`, `L825-L835` | Adjust top rim truncation: let rim-bound polylines reach `wall_z_max + W` (so the cutter pierces the rim face), projecting points above `wall_z_max` at `wall_z_max - 0.05` without hitting floor. |
| `tests/test_kintsugi.py` | `L1-L80` | Add unit test `test_noise_field_gradient_bounded_and_no_crossings` verifying `fold_area == 0.0%`, `max_grad < 1.0`, and zero noise-on crossings. |
| `tests/test_web_api.py` | `L35-L65` | Add `self.assertIn("guard_evaluations", data)` and `self.assertGreaterEqual(data["guard_evaluations"], 1)` to fracture tests. |
| `tools/test_report.py` | `L53-L56` | Remove `noise_fold: F18` from `KNOWN_OPEN` (`KNOWN_OPEN: dict[str, str] = {}`), so clean audit is required for overall PASS. |

---

## 3. Blast Radius & Invariant Guardrails
- **STRICT BLAST RADIUS**: Modify ONLY `kintsugi.py`, `tests/test_kintsugi.py`, `tests/test_web_api.py`, and `tools/test_report.py`.
- **FORBIDDEN**:
  - Do NOT modify the core CSG boolean pipeline (`manifold3d` calls).
  - Do NOT loosen existing assertions in `test_kintsugi.py` (all 35 existing tests must continue to pass).
  - Do NOT introduce retries or non-watertight outputs in `tools/sweep_out_of_sample.py`.
- **INVARIANTS TO PRESERVE**:
  - 100% watertight STL/3MF outputs across all presets and modes.
  - Byte-identical determinism on identical inputs and seeds.
  - `tools/crack_graph_audit.py` must stay at 0 phantoms, 0 crossings, 0 clamp lines.

---

## 4. Visual & UI Impact
- Status: Visual geometry improvement. Cracks will remain organically winding without self-intersecting loops or hooks, and will break cleanly out over the rim of the vessel. No changes to CSS/HTML or UI layout.

---

## 5. Reproduction & Verification Protocol
1. **Reproduce Noise Folding (F18)**:
   ```bash
   .venv/bin/python tools/noise_fold_audit.py --presets tea_bowl --severities 0.6 --seeds 300 305
   ```
   *Expected Failure*: `fold area mean ~21%, max|grad eta| > 3.0`.
2. **Apply Minimal Fix**:
   - Update `_make_noise` to enforce gradient sum $\le 0.70$.
   - Update rim truncation to allow overshoot beyond `wall_z_max`.
   - Update `tests/test_web_api.py` with `guard_evaluations` assertion.
   - Clear `KNOWN_OPEN` in `tools/test_report.py`.
3. **Verify Noise Audit Passes**:
   ```bash
   .venv/bin/python tools/noise_fold_audit.py --presets tea_bowl vase --severities 0.3 0.6 1.0 --seeds 300 500
   ```
   *Expected Result*: `fold area 0.0%`, `max|grad eta| < 1.0`, `crossings 0`.
4. **Full Regression Suite**:
   ```bash
   .venv/bin/python tools/test_report.py run --profile full
   ```
   *Expected Result*: 100% clean passes, `overall: PASS`, with zero `KNOWN-FAIL` exemptions.

---

## 6. Surgical Patch Checklist
- [ ] P01.1 Run `.venv/bin/python tools/noise_fold_audit.py --presets tea_bowl --severities 0.6 --seeds 300 305` and verify fold area > 0.
- [ ] P01.2 Bound noise displacement gradient $\le 0.70$ in `kintsugi.py:_make_noise`.
- [ ] P01.3 Implement rim break-through in `kintsugi.py` (`wall_z_max + W`).
- [ ] P01.4 Add `guard_evaluations` assertion in `tests/test_web_api.py`.
- [ ] P01.5 Clear `KNOWN_OPEN` in `tools/test_report.py`.
- [ ] P01.6 Run `.venv/bin/python -m unittest discover -s tests -v` (confirm 36/36 tests pass).
- [ ] P01.7 Run `.venv/bin/python tools/test_report.py run --profile full` (confirm overall PASS with 0 failures).
- [ ] P01.8 Update `openspec/changes/kintsugi-mesh-fracture/tasks.md` checkboxes.
- [ ] P01.9 Update `openspec/changes/kintsugi-mesh-fracture/patch.md` status to RESOLVED.
- [ ] P01.10 Update `openspec/changes/kintsugi-mesh-fracture/verification.md` with audit results.
