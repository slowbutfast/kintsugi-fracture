## 1. Visual Spike & Aesthetic Evaluation

- [ ] 1.1 Implement prototype algorithmic spike in `tools/spike_growth.py` implementing rim-seeded growth, random-walk heading, acute branching ($30^\circ\text{–}45^\circ$), stop-on-hit snapping, and meridian wrapping ($\pm 2\pi\bar{r}$)
- [ ] 1.2 Run spike against Tea Bowl and Tall Vase across $R \in \{0.0, 0.2, 0.5\}$ and generate preliminary contact sheet in `output/spike/contact_sheet.png`
- [ ] 1.3 Evaluate contact sheet against reference Kintsugi morphology, confirming absence of tile-grout Y-junctions and calibrating tortuosity and clearance parameters

## 2. Test Scaffolding (TDD)

- [ ] 2.1 Scaffold failing test `test_growth_paths_planar_and_tjunc` in `tests/test_kintsugi.py` asserting zero crossings, shared T-junctions, $\ge 30^\circ$ departure/arrival angles, and $\ge W + 0.8\text{ mm}$ clearance
- [ ] 2.2 Scaffold failing test `test_growth_tortuosity_floor` in `tests/test_kintsugi.py` asserting median tortuosity $\ge 1.05$ per junction-to-junction segment
- [ ] 2.3 Scaffold failing test `test_vein_depth_preserves_ceramic_wall` in `tests/test_kintsugi.py` asserting $d_i \le \max(0.0, t_i - 0.8\text{ mm})$, fading to 0 for $t_i \le 0.8\text{ mm}$
- [ ] 2.4 Scaffold failing test `test_growth_rim_seeding_and_penetration` in `tests/test_kintsugi.py` asserting rim initiation ($z \ge \text{wall\_z\_max}$) and depth limited to $H(S)$

## 3. Core Engine & Tooling Implementation

- [ ] 3.1 Implement production `generate_crack_growth_paths` in `kintsugi.py` with deterministic FIFO queue growth order and cutter polyline subdivision ($\le W/2$)
- [ ] 3.2 Update `_build_vein_cutter` in `kintsugi.py` with the non-puncturing depth formula $d_i = \max(0.0, \min(0.75W, 0.5t_i, t_i - 0.8\text{ mm}))$
- [ ] 3.3 Add `--generator growth|voronoi` flag to `kintsugi.py` (defaulting to `growth`) and retain legacy Voronoi generator for CLI audits
- [ ] 3.4 Build `tools/growth_audit.py` to evaluate planarity, clearance, incidence angles, T vs Y junction ratio, and tortuosity distribution over seeds 300–499
- [ ] 3.5 Update `static/index.html` and `web_app.py` to make **Vein Inlay** (`vein`) the default fracture mode
- [ ] 3.6 Update `tools/test_report.py` and `tools/sweep_out_of_sample.py` to support `--generator growth` and add `--renders` to produce the 12-image contact sheet matrix (`reports/contact_sheet.png`)

## 4. Verification & Empirical Audit

- [ ] 4.1 Run full regression test suite (`.venv/bin/python -m unittest discover -s tests -v`) and verify all tests pass cleanly
- [ ] 4.2 Run `tools/growth_audit.py` on seeds 300–499 and verify 0 crossings, $\ge 80\%$ T-junctions, and median tortuosity $\ge 1.05$
- [ ] 4.3 Run full 160-sample held-out sweep with growth generator (`.venv/bin/python tools/test_report.py run --profile full --renders`) and confirm 0 non-watertight meshes and 0 cutter retries
- [ ] 4.4 Perform thin-wall slicing check of `kintsugi_assembly.3mf` in Bambu Studio / PrusaSlicer and record part count and toolpath backing evidence
- [ ] 4.5 Populate `verification.md` with Requirement Adherence Matrix, tortuosity metric statistics, resolved assumptions, and verbatim execution logs
