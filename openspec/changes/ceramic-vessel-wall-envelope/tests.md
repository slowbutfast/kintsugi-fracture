## Automated Tests

- `.venv/bin/python -m unittest tests/test_envelope.py -v`:
  - Verifies that meshes with 5th-percentile wall thickness $p_5 < 1.6\text{ mm}$ (`thin_cylinder`) are rejected by `validate_and_load_mesh` with a descriptive `ValueError`.
  - Verifies that boundary meshes with $p_5 = 1.6\text{ mm}$ are accepted and successfully fracture.
- `.venv/bin/python -m unittest tests/test_kintsugi.py -v`:
  - Verifies continuous vein depth $d_i = \min(0.75W, 0.5t_i)$ along all cutter points, with nominal ceramic backing $\ge 0.8\text{ mm}$ and zero cutter point omissions.
  - Verifies that `_gold_solid_omitted` remains False on valid ceramic fracture runs ($R < 1.0$), while correctly remaining True for wealthy inputs ($R \ge 1.0$).
- `.venv/bin/python -m unittest tests/test_crack_growth.py -v`:
  - Verifies planarity of the crack network (0 crossings across tested seeds and severities).
  - Verifies final-attempt near-miss snapping: advancing cracks reaching within $R_{\text{clear}}$ at arrival angle $\ge 30^\circ$ snap to target segments rather than stopping short with 2–3 mm gaps.
  - Verifies median tortuosity $\ge 1.05$ with $15\%\text{--}20\%$ kink rate.
- `.venv/bin/python -m unittest discover -s tests -v`:
  - Full automated regression test suite covering core engine, web API, and multi-material 3MF generation.
- `.venv/bin/python tools/test_report.py run --profile full --renders`:
  - Complete 160-sample parameter sweep across all supported models and severity settings, asserting 0 retries and clean manifold outputs.

## Manual Verification

- **Visual Contact Sheet Inspection**:
  - **WHEN** developer generates `reports/contact_sheet.png` across the 12-case matrix (Japanese Tea Bowl and Tall Vase at $R \in \{0.0, 0.2, 0.5\}$, 2 seeds each)
  - **THEN** human evaluator confirms gold channels are continuous without empty dropouts, cracks wander organically without staircase zig-zags, and branches terminate in authentic T-junctions.
- **Slicer 3MF Multi-Material Import**:
  - **WHEN** developer opens exported `kintsugi_assembly.3mf` in Bambu Studio or PrusaSlicer
  - **THEN** slicer identifies two separate components (`CeramicBody` and `GoldSeams`) assigned to distinct toolheads/materials without self-intersections or alignment errors.
- **Web UI Wall Thickness Rejection**:
  - **WHEN** user uploads a sub-1.6 mm model via the GUI
  - **THEN** UI status bar reports `Not a valid closed solid: Input vessel wall thickness (...) is below ceramic envelope requirement of 1.60 mm` and disables the fracture button.
