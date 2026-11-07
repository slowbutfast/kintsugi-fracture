## 1. Test Scaffolding (TDD)

- [ ] 1.1 Write failing test `test_envelope_rejection_thin_cylinder` in `tests/test_envelope.py` asserting `ValueError` on meshes with $p_5 < 1.6\text{ mm}$
- [ ] 1.2 Write failing test `test_envelope_boundary_acceptance` in `tests/test_envelope.py` asserting acceptance and fracture on boundary mesh with $p_5 = 1.6\text{ mm}$
- [ ] 1.3 Write failing test `test_continuous_vein_depth_no_omissions` in `tests/test_kintsugi.py` asserting continuous $d_i = \min(0.75W, 0.5t_i)$ and `gold_solid_omitted == False` on valid runs
- [ ] 1.4 Write failing test for final-attempt near-miss snapping in `tests/test_crack_growth.py` asserting cracks snap to target segments at $\ge 30^\circ$ rather than stopping short

## 2. Preflight Wall Thickness & Envelope Validation

- [ ] 2.1 Update `validate_and_load_mesh` in `kintsugi.py` to sample two-hit wall thickness via inward rays across the trauma band and reject $p_5 < 1.6\text{ mm}$ with `ValueError`
- [ ] 2.2 Update `sample_models.py` to move `thin_cylinder` to negative test fixtures and add a boundary model at $t = 1.6\text{ mm}$
- [ ] 2.3 Update `web_app.py` to handle wall thickness `ValueError` in `/api/validate` and `/api/fracture` gracefully

## 3. Continuous Vein Depth & Simplified Cutter

- [ ] 3.1 In `kintsugi.py`, restore continuous vein depth $d_i = \min(0.75W, 0.5t_i)$ in `_build_vein_cutter`, removing `GROWTH_MIN_DEPTH_MM`, `_vein_point_groups`, and sub-0.25 mm point omissions
- [ ] 3.2 Ensure `_gold_solid_omitted` remains False on all valid ceramic runs ($R < 1.0$) and True only on wealthy pass-throughs ($R \ge 1.0$)
- [ ] 3.3 Update `static/viewer.js` to show `Pristine / Wealthy (0 cracks)` exclusively for $R \ge 1.0$

## 4. Crack Growth Snapping & Morphology Tuning

- [ ] 4.1 In `kintsugi.py`, ensure final-attempt near-miss snapping directly bends advancing steps onto target segment at $\ge 30^\circ$
- [ ] 4.2 In `kintsugi.py`, verify correlated random walk with 15–20% kink probability and $\sigma \approx 18^\circ$ drift, meeting median tortuosity $\ge 1.05$

## 5. Verification & Empirical Audit

- [ ] 5.1 Run full regression test suite (`unittest discover -s tests -v`) and verify 100% clean passes without regressions
- [ ] 5.2 Generate 12-case visual contact sheet (`reports/contact_sheet.png`) and conduct human sign-off against Kintsugi references
- [ ] 5.3 Verify multi-material 3MF import in Bambu Studio / PrusaSlicer
- [ ] 5.4 Populate `verification.md` with Requirement Adherence Matrix, resolved assumptions, and verbatim execution logs
