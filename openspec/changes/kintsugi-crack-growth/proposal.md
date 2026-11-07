## Why

The current fracture engine relies on a periodic Voronoi diagram perturbed by a trigonometric noise field. In PATCH-01, bounding the noise gradient to prevent spatial folding (F18) forced noise amplitude down from 5–6.5 mm to a flat 1.35 mm, transforming the fissures into sterile, straight-edged Voronoi tiles ("honeycomb/bathroom-tile grout") rather than organic Kintsugi cracks. 

We need to pivot from polygonal Voronoi tiling to an authentic **sequential rim-seeded crack growth engine with stop-on-hit**, ensuring dramatic lightning morphology, natural T-junctions, and zero crossings by construction, while preserving our rock-solid Manifold3D CSG pipeline and retro Windows XP web interface.

## What Changes

- **Sequential Rim-Seeded Crack Growth**: Cracks initiate at impact seeds along the vessel rim ($z \ge \text{wall\_z\_max}$) and propagate downwards via random-walk heading deviation, creating organic lightning fissures without relying on a global 2D displacement field.
- **Stop-on-Hit Collision Handling**: Propagating segments that intersect existing crack paths terminate at the point of contact to form realistic **T-junctions**, eliminating crossing defects by construction.
- **Printability Guards**: Minimum branch angle ($\ge 30^\circ$) prevents knife-thin ceramic spikes; minimum segment step size ($\ge W/2$) prevents CSG cutter self-overlap.
- **Thin-Wall Vein Mode Optimization**: Vein inlay channels are constrained to leave at least $0.8\text{ mm}$ of ceramic wall backing (`groove_depth <= wall_thickness - 0.8 mm`), preventing accidental wall punctures on thin-wall vessels.
- **Visual Review Verification Gate**: Adds `--renders` to `tools/test_report.py` to produce a canonical 12-image visual contact sheet (`reports/contact_sheet.png`) across presets, seeds, and severities, backed by a tortuosity metric floor ($\text{median} \ge 1.05$).
- **Dual Generator Support**: Exposes `--generator growth|voronoi` in CLI and Web GUI, keeping Voronoi as an explicit comparative baseline while defaulting to `growth`.
- **UI Default Update**: Sets **Vein Inlay** as the default fracture mode in the Windows XP Luna GUI.

## Capabilities

### New Capabilities
*(None - all changes evolve existing capabilities)*

### Modified Capabilities
- `mesh-fracture-engine`: Modifies crack graph generation requirements to use rim-seeded growth with stop-on-hit T-junctions instead of Voronoi relaxation and trigonometric noise; guarantees planarity on final shipped geometry; adds thin-wall ceramic clearance requirement for vein inlays.
- `retro-web-gui`: Updates default selection to Vein Inlay mode and adds a retro generator selector in the parameters dialog.

## Impact

- **Affected Code**: `kintsugi.py` (adds `generate_crack_growth_paths`, keeps Voronoi behind flag, wires growth into existing cutter builder), `web_app.py`, `static/index.html`, `static/viewer.js`, `tools/test_report.py`.
- **Dependencies**: Zero new dependencies. Uses standard `numpy` and existing math utilities.
- **Backward Compatibility**: Fully preserved. Existing `--preset` options, CLI arguments, and output artifacts (`ceramic_body.stl`, `gold_seams.stl`, `kintsugi_assembly.3mf`) remain 100% compatible.
