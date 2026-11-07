## Automated Tests

- `.venv/bin/python -m unittest discover -s tests -v`:
  - Runs all regression unit tests covering input validation, Manifold3D status, 3MF structure, debris swap, determinism, and Web API.
- `tests/test_kintsugi.py::test_growth_paths_planar_and_tjunc`:
  - Asserts that crack paths generated under `generate_crack_growth_paths` have zero segment self-intersections across 200 random seeds.
  - Asserts that every collision point with an existing segment snaps to the earliest contact point and subdivides the hit segment into a shared T-junction vertex.
  - Asserts that branch departure angles and arrival incidence angles are $\ge 30^\circ$.
  - Asserts that non-intersecting segments maintain clearance $\ge W + 0.8\text{ mm}$ outside the junction exemption zone.
- `tests/test_kintsugi.py::test_vein_depth_and_kissing_prevention`:
  - Asserts that vein cutter depth satisfies $d_i \le t_i - 0.8\text{ mm}$.
  - Asserts that path points with $d_i < 0.25\text{ mm}$ are omitted from cutter generation, splitting the cutter and preventing tangent non-manifold kissing contacts.
- `tests/test_kintsugi.py::test_growth_rim_seeding_and_penetration`:
  - Asserts that trunks originate at $z \ge \text{wall\_z\_max}$ with angular spacing $\ge \frac{W + 1.5\text{ mm}}{\bar r}$.
  - Asserts that trunk penetration depths do not terminate on a flat horizontal line (standard deviation of termination $z > 0.5\text{ mm}$).
- `tests/test_kintsugi.py::test_growth_tortuosity_floor`:
  - Measures the tortuosity ratio ($\frac{\text{arc length}}{\text{chord length}}$) per junction-to-junction segment across severities $S \in \{0.3, 0.6, 1.0\}$.
  - Asserts that median tortuosity satisfies $\ge 1.05$.
- `tests/test_kintsugi.py::test_thin_wall_model_manifold`:
  - Runs vein mode CSG fracture on the synthetic `thin_cylinder` model (wall thickness 1.2 mm tapering to 0.7 mm) and asserts that outputs reload with 0 non-manifold edges.
- `tools/growth_audit.py --seeds 300-499`:
  - Evaluates planarity, minimum clearance, incidence angles, T vs Y junction ratio, and tortuosity distribution across 200 held-out seeds.
- `tools/sweep_out_of_sample.py --generator growth`:
  - Runs 160 out-of-sample combinations verifying watertightness and 0 CSG retries.
- `.venv/bin/python tools/test_report.py run --profile full --renders`:
  - Runs unit tests, `growth_audit`, held-out sweep with growth generator, and outputs the contact sheet to `reports/contact_sheet.png`.

## Manual Verification

- **Visual Contact Sheet Inspection (`reports/contact_sheet.png`)**:
  - **WHEN** developer runs `.venv/bin/python tools/test_report.py run --renders`
  - **THEN** system outputs a 12-panel matrix showing Tea Bowl and Tall Vase with gold veins; developer inspects the images against reference Kintsugi morphology to confirm organic lightning branching, natural T-junctions, and clean rim cascades without horizontal lip lines.
- **Windows XP Luna GUI**:
  - **WHEN** user launches `python web_app.py` and opens `http://127.0.0.1:8000`
  - **THEN** the Luna XP interface renders with **Vein Inlay** pre-selected, and clicking `⚡ FRACTURE MESH` renders the 3D lightning gold seams in the Three.js viewport.
- **Slicer Import & Thin-Wall Toolpath Preview**:
  - **WHEN** user imports `kintsugi_assembly.3mf` generated from `thin_cylinder` into Bambu Studio or PrusaSlicer
  - **THEN** the model loads as a single object with two parts (`ceramic_body` and `gold_seams`), and slicing under a standard 2-perimeter profile reveals continuous ceramic wall backing behind the gold channels.
