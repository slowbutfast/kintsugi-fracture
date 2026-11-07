## 1. Test Scaffolding (TDD)

- [ ] 1.1 Scaffold failing unit test `test_growth_paths_planar_and_tjunc` in `tests/test_kintsugi.py` asserting zero crossings, shared T-junctions, and $\ge 30^\circ$ branch angles on `generate_crack_growth_paths`
- [ ] 1.2 Scaffold failing unit test `test_growth_tortuosity_floor` in `tests/test_kintsugi.py` asserting median tortuosity $\ge 1.05$ across severities $S \in \{0.3, 0.6, 1.0\}$
- [ ] 1.3 Scaffold failing unit test `test_vein_depth_preserves_ceramic_wall` in `tests/test_kintsugi.py` asserting $d_i \le t_i - 0.8\text{ mm}$ for thin-wall vessels
- [ ] 1.4 Scaffold failing API test `test_api_fracture_with_generator` in `tests/test_web_api.py` asserting `/api/fracture` accepts `generator="growth"` and `generator="voronoi"`

## 2. Crack Growth Engine Implementation

- [ ] 2.1 Implement prototype algorithmic spike in `tools/spike_growth.py` validating rim-seeded growth, random-walk heading, acute branching, and stop-on-hit segment collision
- [ ] 2.2 Implement `generate_crack_growth_paths` in `kintsugi.py` with periodic seam wrapping ($\theta \pm 2\pi$), step size $\ge W/2$, and acute branch constraints ($30^\circ\text{–}45^\circ$)
- [ ] 2.3 Expose `--generator growth|voronoi` flag in `kintsugi.py`, defaulting to `growth` while retaining `generate_crack_paths` as legacy fallback
- [ ] 2.4 Update `_build_vein_cutter` in `kintsugi.py` to clamp channel depth to $d_i = \min(0.75\,W,\ 0.5\,t_i,\ \max(0.2,\ t_i - 0.8\text{ mm}))$

## 3. UI/UX & Tooling Updates

- [ ] 3.1 Update `web_app.py` `/api/fracture` request schema to accept `generator: str = "growth"` and pass it to the fracture pipeline
- [ ] 3.2 Update `static/index.html` to default fracture mode to `vein` (Vein Inlay)
- [ ] 3.3 Add Windows XP Luna styled `<select>` dropdown for `Fracture Model: [Organic Lightning (Recommended) | Voronoi Tiling (Legacy)]` in `static/index.html` and wire into `static/viewer.js`
- [ ] 3.4 Add `--renders` flag to `tools/test_report.py` to generate the 12-image contact sheet matrix (`reports/contact_sheet.png`) across presets, seeds, and severities

## 4. Verification & Empirical Audit

- [ ] 4.1 Run full regression test suite (`.venv/bin/python -m unittest discover -s tests -v`) and verify 100% clean passes
- [ ] 4.2 Run full 160-sample held-out sweep with `--generator growth` (`.venv/bin/python tools/test_report.py run --profile full --renders`) and confirm 0 non-watertight meshes and 0 cutter retries
- [ ] 4.3 Inspect generated contact sheet `reports/contact_sheet.png` to confirm organic lightning morphology, clean rim cascade, and absence of tile grout patterns
- [ ] 4.4 Perform slicer toolpath verification for `kintsugi_assembly.3mf` in Bambu Studio / PrusaSlicer under standard thin-wall profile
- [ ] 4.5 Populate `verification.md` with Requirement Adherence Matrix, tortuosity metric statistics, resolved assumptions, and verbatim execution logs
