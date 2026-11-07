## 1. Test Scaffolding (TDD - Hard Invariants)

- [ ] 1.1 Scaffold failing test `test_growth_paths_planar_and_tjunc` in `tests/test_kintsugi.py` asserting zero crossings, shared T-junctions, clearance $\ge W + 0.8\text{ mm}$ outside exemption zone, and $\ge 30^\circ$ angles
- [ ] 1.2 Scaffold failing test `test_vein_depth_and_kissing_prevention` in `tests/test_kintsugi.py` asserting $d_i \le t_i - 0.8\text{ mm}$ and omission of cutter points where $d_i < 0.25\text{ mm}$
- [ ] 1.3 Scaffold failing test `test_growth_rim_seeding_and_penetration` in `tests/test_kintsugi.py` asserting Poisson rim spacing and non-flat jittered penetration termination
- [ ] 1.4 Scaffold failing test `test_thin_wall_model_manifold` in `tests/test_kintsugi.py` testing vein mode on a 1.2 mm / 0.7 mm thin-wall vessel
- [ ] 1.5 Triage existing unit tests in `tests/test_kintsugi.py`: ensure tests asserting Voronoi geometry (e.g. `test_crack_paths_lie_on_periodic_voronoi`) pass `generator="voronoi"` explicitly so flipping the default does not cause false failures

## 2. Spike Implementation & Visual Contact Sheet

- [ ] 2.1 Implement `generate_crack_growth_paths` in `kintsugi.py` behind `--generator growth|voronoi` flag, implementing Poisson rim seeding, random-walk heading, acute branching ($30^\circ\text{–}45^\circ$), first-hit snapping, and junction exemption
- [ ] 2.2 Add synthetic `thin_cylinder` preset (wall 1.2 mm tapering to 0.7 mm) to `sample_models.py`
- [ ] 2.3 Implement contact sheet generator in `tools/spike_contact_sheet.py` and generate preliminary $4 \times 3$ contact sheet in `output/spike/contact_sheet.png`
- [ ] 2.4 Review `output/spike/contact_sheet.png` against reference Kintsugi morphology and record visual sign-off in `verification.md`

## 3. Core Engine Hardening & Tooling

- [ ] 3.1 Update `_build_vein_cutter` in `kintsugi.py` to enforce the $d < 0.25\text{ mm}$ point omission cutoff, splitting polylines to prevent tangent kissing contacts, with dense sampling $\le W/2$
- [ ] 3.2 Build `tools/growth_audit.py` to evaluate planarity, clearance, incidence angles, T vs Y junction ratio, and tortuosity distribution over seeds 300–499
- [ ] 3.3 Update `tools/test_report.py` and `tools/sweep_out_of_sample.py` to support `--generator growth` and add `--renders` to output `reports/contact_sheet.png`
- [ ] 3.4 Update `static/index.html` and `web_app.py` to make **Vein Inlay** (`vein`) the default fracture mode

## 4. Verification, Slicer Audit & Deprecation

- [ ] 4.1 Run full regression test suite (`.venv/bin/python -m unittest discover -s tests -v`) and verify all tests pass cleanly
- [ ] 4.2 Run `tools/growth_audit.py` on seeds 300–499 and verify 0 crossings, $\ge 80\%$ T-junctions, and median tortuosity $\ge 1.05$
- [ ] 4.3 Run full 160-sample held-out sweep with growth generator (`.venv/bin/python tools/test_report.py run --profile full --renders`) and confirm 0 non-watertight meshes and 0 cutter retries
- [ ] 4.4 Perform thin-wall slicing check of `kintsugi_assembly.3mf` from `thin_cylinder` in Bambu Studio / PrusaSlicer and record part count and toolpath backing evidence
- [ ] 4.5 Populate `verification.md` with Requirement Adherence Matrix, tortuosity metric statistics, resolved assumptions, and schedule legacy Voronoi deprecation
