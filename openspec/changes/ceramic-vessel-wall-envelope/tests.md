## Automated Tests

- `.venv/bin/python -m unittest tests/test_envelope.py -v`:
  - Verifies that meshes with 5th-percentile normal wall thickness $p_5 < 1.6\text{ mm}$ (e.g. cylinder with wall thickness $\approx 1.5\text{ mm}$ and `thin_cylinder` fixture) are rejected by `validate_and_load_mesh` with a descriptive `ValueError` in both vein and ribbon modes.
  - Verifies that boundary vessels with $p_5 \approx 1.7\text{ mm}$ are accepted and successfully fracture.
  - Verifies the boundary comparison helper logic directly at $1.60\text{ mm}$.
- `.venv/bin/python -m unittest tests/test_kintsugi.py -v`:
  - Verifies continuous vein depth $d_i = \min(0.75W, 0.5t_i)$ along all cutter points with zero cutter point omissions.
  - Verifies rim crack projection clamping at $\text{wall\_z\_max} - \max(0.5, W/2)$.
  - Regression test for `_gold_solid_omitted`: verifies False on valid ceramic runs ($R < 1.0$), True on wealthy pass-throughs ($R \ge 1.0$), and verifies fallback behavior when $R < 1.0$ with an empty gold boolean.
- `.venv/bin/python -m unittest tests/test_crack_growth.py -v`:
  - Regression test for final-attempt near-miss snapping: advancing cracks reaching within $R_{\text{clear}}$ at arrival angle $\ge 30^\circ$ snap to target segments when forward projection fails.
  - Regression test for correlated random walk: 20% kink rate with Gaussian $\sigma \approx 18^\circ$, maintaining median tortuosity $\ge 1.05$ and 0 crossings.
- `.venv/bin/python -m unittest discover -s tests -v`:
  - Full regression test suite covering core engine, web API, and multi-material 3MF export.
- `.venv/bin/python tools/test_report.py run --profile full --renders`:
  - Parameter sweep across supported ceramic presets (`tea_bowl`, `vase`), asserting 0 retries and clean manifold outputs.

## Manual Verification

- **Visual Contact Sheet Inspection**:
  - **WHEN** developer generates `reports/contact_sheet.png` across the 12-case matrix (Japanese Tea Bowl and Tall Vase at $R \in \{0.0, 0.2, 0.5\}$, 2 seeds each)
  - **THEN** human evaluator inspects for continuous unbroken gold channels, organic wandering morphology, and clean T-junction branch stops, recording sign-off in `verification.md`.
- **Slicer 3MF Multi-Material Import**:
  - **WHEN** developer opens exported `kintsugi_assembly.3mf` in Bambu Studio or PrusaSlicer
  - **THEN** slicer identifies two separate components (`CeramicBody` and `GoldSeams`) assigned to distinct toolheads/materials without self-intersections or alignment errors.
- **Web UI Wall Thickness Rejection**:
  - **WHEN** user uploads a sub-1.6 mm model via the GUI
  - **THEN** UI status bar reports `Not a valid closed solid: Input vessel wall thickness (...) is below ceramic envelope requirement of 1.60 mm` and disables the fracture button.
