## 1. Test Scaffolding (TDD)

- [x] 1.1 Write failing test `test_envelope_rejection_thin_mesh` in `tests/test_envelope.py` asserting `ValueError` on meshes with $p_5 < 1.6\text{ mm}$ (testing ~1.5 mm cylinder and `thin_cylinder` fixture)
- [x] 1.2 Write failing test `test_envelope_acceptance_near_boundary` in `tests/test_envelope.py` asserting acceptance on mesh with $p_5 \approx 1.7\text{ mm}$, plus boundary comparison unit test at $1.60\text{ mm}$
- [x] 1.3 Write failing test `test_continuous_vein_depth_no_omissions` in `tests/test_kintsugi.py` asserting $d_i = \min(0.75W, 0.5t_i)$ and absence of point omission splitting
- [x] 1.4 Add regression tests in `tests/test_crack_growth.py` for shipped PATCH-02 morphology (final-attempt bend snap, 20% kink rate with $\sigma = 18^\circ$, median tortuosity $\ge 1.05$)

## 2. Preflight Normal Wall Thickness & Envelope Validation

- [x] 2.1 Update `validate_and_load_mesh` in `kintsugi.py` to probe inward surface normal wall thickness across `[wall_z_min, wall_z_max]` and reject $p_5 < 1.6\text{ mm}$ with `ValueError` across all modes
- [x] 2.2 Delete `presets/thin_cylinder.stl`, remove `thin_cylinder` from `sample_models.PRESETS`, remove alias, and provide `create_thin_cylinder_fixture` in `sample_models.py` strictly for negative tests
- [x] 2.3 Update all `thin_cylinder` call sites: `test_web_api.py:95`, `test_kintsugi.py:1175, 1201`, `spike_contact_sheet.py`, and `test_report.py` (`sweep_out_of_sample.py` verified: no change needed)
- [x] 2.4 Update `web_app.py` `/api/validate` and `/api/fracture` to handle wall thickness `ValueError` cleanly

## 3. Continuous Vein Depth & Simplified Cutter

- [x] 3.1 In `kintsugi.py`, restore $d_i = \min(0.75W, 0.5t_i)$ using normal wall thickness, remove `GROWTH_MIN_DEPTH_MM`, `_vein_point_groups`, and sub-0.25 mm point omissions
- [x] 3.2 Clamp rim crack projection at $\text{wall\_z\_max} - \max(0.5, W/2)$ in `kintsugi.py` to protect tapered rim lips
- [x] 3.3 Ensure `_gold_solid_omitted` remains False on all valid ceramic runs ($R < 1.0$), True on wealthy pass-throughs ($R \ge 1.0$), and handles empty-gold boolean fallback for both STL and 3MF
- [x] 3.4 Update `viewer.js:410` to remove stale "wall thickness < 1.05 mm" text and clean up `seams_omitted_reason` in `web_app.py`

## 4. Morphology Regression Gating & Sweeps

- [x] 4.1 Confirm regression test passes for final-attempt bend snapping and correlated random walk in `tests/test_crack_growth.py`
- [x] 4.2 Update test sweep tools (`tools/test_report.py`, `tools/sweep_out_of_sample.py`) to run on supported ceramic presets (`tea_bowl`, `vase`)

## 5. Verification & Empirical Audit

- [x] 5.1 Run full regression test suite (`unittest discover -s tests -v`) and verify 100% clean passes without regressions
- [ ] 5.2 Generate 12-case visual contact sheet (`reports/contact_sheet.png`) and conduct human sign-off against Kintsugi references
- [ ] 5.3 Verify multi-material 3MF import in Bambu Studio / PrusaSlicer
- [x] 5.4 Populate `verification.md` with Requirement Adherence Matrix, resolved assumptions, and verbatim execution logs

## Patch 01: Flared-Wall Normal Tests, Tapered-Lip Audit & Defensive Pipeline Verification

- [x] P01.1 Scaffold flared-cone fixture pair in `tests/test_envelope.py`: 1.2 mm normal wall (45° flare) rejected, 2.0 mm accepted
- [x] P01.2 Apply conservative normal-ray miss fallback $\min(t_{\text{normal}}, t_{\text{radial}})$ in `kintsugi.py`
- [x] P01.3 Add tapered-lip test fixture and verify continuous gold carving, reporting minimum carved depth and ceramic backing
- [x] P01.4 In `kintsugi.py`, replace exact float compare in `_gold_solid_omitted` with `1e-6` volume tolerance
- [x] P01.5 Add end-to-end empty-gold pipeline test in `tests/test_web_api.py` with patched empty cutter
- [x] P01.6 Update docstrings, `patch.md`, and `verification.md` with exact backing/depth wording and test results
