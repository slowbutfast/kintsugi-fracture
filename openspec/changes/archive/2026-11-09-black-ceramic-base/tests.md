## Automated Tests

- `.venv/bin/python -m unittest tests/test_web_api.py -v`:
  - Verifies that `GET /xp.css` contains `--ceramic-body: #18181b` and `--viewport-bg: #f0ede0`.
  - Verifies that `GET /viewer.js` contains `0x18181b` (ceramic color) and `0xf0ede0` (scene background color).
  - Verifies that all web API health, preset, and fracture endpoints continue passing without regression.
- `.venv/bin/python -m unittest discover -s tests -p "test_*.py" -v`:
  - Full test suite regression verifying all existing geometry generation, envelope validation, and API contracts remain 100% green.

## Manual Verification

- **3D Viewport Inspection**:
  - **WHEN** the developer loads `http://localhost:8000` in a desktop or mobile browser
  - **THEN** the 3D viewport canvas renders in gallery off-white (`#f0ede0`) within the sunken 2px beveled well, and the initial `Japanese Tea Bowl` renders in deep Kuro-raku matte black (`#18181b`) with visible contour highlights.
- **Fracture Seam Contrast**:
  - **WHEN** the developer triggers `⚡ FRACTURE MESH` at $R = 0.5$
  - **THEN** the fractured vessel displays deep black ceramic pieces contrasted against brilliant metallic gold veins (`#ffd700`) with high visual clarity.
- **Model Preset Switching**:
  - **WHEN** the developer switches presets to `Small Vase` or `3D Benchy`
  - **THEN** the new model loads immediately with the same Kuro-raku black ceramic material and frames cleanly on the off-white drafting grid.
