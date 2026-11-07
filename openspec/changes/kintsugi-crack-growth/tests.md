## Automated Tests

- `.venv/bin/python -m unittest discover -s tests -v`:
  - Runs all existing 36 regression unit tests covering input validation, Manifold3D status, 3MF structure, debris swap, determinism, and Web API.
- `tests/test_kintsugi.py::test_growth_paths_planar_and_tjunc`:
  - Asserts that crack paths generated under `generate_crack_growth_paths` have zero segment self-intersections across 200 random seeds.
  - Asserts that every path contact point with an existing segment is registered as a shared T-junction node.
  - Asserts that no branches form acute angles $< 30^\circ$.
- `tests/test_kintsugi.py::test_growth_tortuosity_floor`:
  - Measures the tortuosity ratio ($\frac{\text{arc length}}{\text{chord length}}$) across all generated cracks for severities $S \in \{0.3, 0.6, 1.0\}$.
  - Asserts that the median tortuosity satisfies $\ge 1.05$, catching any regression that flattens cracks into straight lines.
- `tests/test_kintsugi.py::test_vein_depth_preserves_ceramic_wall`:
  - Asserts that for any vessel with wall thickness $t_i$, the vein cutter depth satisfies $d_i \le t_i - 0.8\text{ mm}$, guaranteeing leak-proof ceramic backing.
- `tests/test_web_api.py::test_api_fracture_with_generator`:
  - Asserts that `POST /api/fracture` accepts `generator="growth"` and `generator="voronoi"`, returning valid STL paths and volume statistics.
- `.venv/bin/python tools/test_report.py run --profile full --renders`:
  - Runs the full test suite, out-of-sample sweeps (160 runs), and generates the 12-image contact sheet matrix at `reports/contact_sheet.png`.

## Manual Verification

- **Visual Contact Sheet Inspection (`reports/contact_sheet.png`)**:
  - **WHEN** developer runs `.venv/bin/python tools/test_report.py run --renders`
  - **THEN** system outputs a 12-panel matrix showing Tea Bowl and Tall Vase with gold veins; developer inspects the images to confirm organic lightning branching, natural T-junctions, and clean rim cascades without horizontal lip lines.
- **Windows XP Luna GUI & Generator Toggle**:
  - **WHEN** user launches `python web_app.py` and opens `http://127.0.0.1:8000`
  - **THEN** the Luna XP interface renders with **Vein Inlay** pre-selected, the generator dropdown shows `Organic Lightning (Recommended)`, and clicking `⚡ FRACTURE MESH` renders the 3D lightning gold seams in the Three.js viewport.
- **Slicer Import & Thin-Wall Toolpath Preview**:
  - **WHEN** user imports `kintsugi_assembly.3mf` into Bambu Studio or PrusaSlicer
  - **THEN** the model loads as a single object with two parts (`ceramic_body` and `gold_seams`), and slicing under a standard 2-perimeter profile reveals continuous ceramic wall backing behind the gold channels.
