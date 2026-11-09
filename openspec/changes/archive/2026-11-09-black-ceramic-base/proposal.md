## Why

The user wants to transition the visual appearance of fractured kintsugi vessels from off-white porcelain to traditional Kuro-raku matte black stoneware while keeping the seam veins lustrous metallic gold, set against an off-white viewport canvas that harmonizes with the surrounding Windows XP desktop interface. This creates an authentic pottery gallery exhibition aesthetic with dramatic contrast between the black ceramic body, the gold seam inlays, and the off-white display well.

## What Changes

- **Ceramic base material**: Update `ceramicMaterial` in `static/viewer.js` from off-white (`0xf8f6f0`, roughness `0.85`, metalness `0.05`) to Kuro-raku matte black (`0x18181b`, roughness `0.65`, metalness `0.10`), retaining specular highlights on 3D curves and rims.
- **3D Viewport canvas background**: Update `scene.background` in `static/viewer.js` and `--viewport-bg` in `static/xp.css` from dark slate navy (`#1a1f2c` / `0x1a1f2c`) to gallery off-white (`#f0ede0` / `0xf0ede0`), matching the surrounding `--surface-inset` well inside the sunken 3D beveled frame.
- **Floor grid and ambient lighting**: Soften floor grid lines in `static/viewer.js` from dark slate to warm architectural gray (`0xb8b4a6` / `0xd0ccc0`, opacity `0.40`) and ground hemisphere light bounce to warm neutral (`0xdcd8cc`).
- **Offline rendering tools**: Update `CERAMIC` color tuple from `(235, 230, 218)` to `(24, 24, 27)` (`#18181b`) in `tools/spike_contact_sheet.py`, `tools/render.py`, and `tools/render_remediation.py` so offline contact sheet figures match the Web GUI.
- **Design tokens & specifications**: Update `DESIGN.md` and `openspec/specs/retro-web-gui/spec.md` to reflect the Kuro-raku black ceramic and gallery off-white viewport tokens.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `retro-web-gui`: The interactive Three.js 3D inspection viewport renders the ceramic body in Kuro-raku matte black (`#18181b`) and gold seams in specular metallic gold (`#ffd700`) against a gallery off-white canvas well (`#f0ede0`).

## Impact

- **Affected code**:
  - `static/viewer.js`: Update `ceramicMaterial`, `scene.background`, hemisphere ground light, and `grid`.
  - `static/xp.css`: Update `--ceramic-body` and `--viewport-bg` CSS variables.
  - `DESIGN.md`: Update `ceramic-body` and `viewport-bg` tokens and material description.
  - `tools/spike_contact_sheet.py`, `tools/render.py`, `tools/render_remediation.py`: Update `CERAMIC` RGB tuple to `(24, 24, 27)`.
  - `tests/test_web_api.py`: Add assertions verifying the updated color tokens in `GET /xp.css` and `GET /viewer.js`.
- **Backend APIs & Slicers**:
  - Zero breaking changes to `POST /api/fracture`, `kintsugi.py`, or STL/3MF export formats.
