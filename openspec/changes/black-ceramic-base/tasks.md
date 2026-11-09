## 1. Test Scaffolding (TDD)

- [ ] 1.1 Write failing assertions in `tests/test_web_api.py` asserting that `GET /xp.css` contains `--ceramic-body: #18181b` and `--viewport-bg: #f0ede0`, and that `GET /viewer.js` contains `0x18181b` and `0xf0ede0`.

## 2. Web GUI Materials, Viewport Background & Grid

- [ ] 2.1 Update `static/viewer.js` to configure `ceramicMaterial` with `color: 0x18181b`, `roughness: 0.65`, `metalness: 0.10`, set `scene.background = new THREE.Color(0xf0ede0)`, set hemisphere light ground bounce to `0xdcd8cc`, and adjust `GridHelper` lines to `0xb8b4a6` / `0xd0ccc0` with `0.40` opacity.
- [ ] 2.2 Update `static/xp.css` to set `--ceramic-body: #18181b;` and `--viewport-bg: #f0ede0;`.

## 3. Offline Tool Synchronization & Design Specs

- [ ] 3.1 Update `tools/spike_contact_sheet.py`, `tools/render.py`, and `tools/render_remediation.py` to set `CERAMIC = (24, 24, 27)` (`#18181b`).
- [ ] 3.2 Update `DESIGN.md` tokens for `ceramic-body: "#18181b"`, `viewport-bg: "#f0ede0"`, and update the aesthetic description to reference Kuro-raku black stoneware on a gallery off-white canvas.

## 4. Verification & Empirical Audit

- [ ] 4.1 Run full regression test suite `.venv/bin/python -m unittest discover -s tests -p "test_*.py" -v` and verify 100% test pass rate with zero regressions.
- [ ] 4.2 Manually verify in the Web GUI that the 3D canvas renders in gallery off-white within the beveled well, that preset vessels load in Kuro-raku matte black with visible curvature highlights, and that gold veins shine vividly.
- [ ] 4.3 Populate `verification.md` with Requirement Adherence Matrix, resolved assumptions, and verbatim execution logs.
