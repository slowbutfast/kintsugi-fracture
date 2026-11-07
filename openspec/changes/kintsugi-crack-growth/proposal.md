## Why

The current fracture engine relies on a periodic Voronoi diagram perturbed by a trigonometric noise field. In PATCH-01, bounding the noise gradient to prevent spatial folding on presets forced noise amplitude down from 5–6.5 mm to a flat 1.35 mm, transforming the fissures into sterile, straight-edged Voronoi tiles ("bathroom-tile grout") rather than organic Kintsugi cracks. Furthermore, the Voronoi noise field carries a mathematical proof gap that folds at small vessel radii ($r_{bar} \le 12\text{ mm}$).

We are executing an aesthetic and architectural pivot from polygonal Voronoi tiling to an authentic **sequential rim-seeded crack growth engine with stop-on-hit**, ensuring dramatic lightning morphology, natural T-junctions, and zero unintended crossings by construction, while preserving our rock-solid Manifold3D CSG pipeline and retro Windows XP web interface.

## What Changes

- **Sequential Rim-Seeded Crack Growth**: Cracks initiate at impact seeds along the upper vessel rim and propagate downwards into the trauma band via bounded random-walk heading deviation ($\pm 60^\circ$ from downwards), creating organic lightning fissures without relying on a global 2D displacement field.
- **Stop-on-Hit Collision Handling**: When an advancing segment intersects or approaches within clearance of an existing crack path, it snaps to the hit point, terminates growth, and subdivides the hit segment with a shared vertex, creating clean **T-junctions** and eliminating crossings by construction.
- **Seam Clearance & Angle Guards**:
  - Minimum branch departure angle ($\ge 30^\circ$) and minimum T-junction arrival incidence angle ($\ge 30^\circ$) prevent knife-thin ceramic spikes.
  - Parallel crack segments must maintain a clearance of at least $W + 0.8\text{ mm}$ to prevent gold channels from merging into unprintable blobs.
- **Thin-Wall Ceramic Backing Guarantee**:
  - Vein inlay depth is defined as $d_i = \max(0.0, \min(0.75W, 0.5t_i, t_i - 0.8\text{ mm}))$.
  - On vessel walls thinner than $0.8\text{ mm}$, groove depth fades to $0.0\text{ mm}$ (no carving) rather than puncturing the ceramic.
- **Severity & Growth Bounds**: Economic severity $S$ controls seed count, branch probability, and maximum penetration depth below the rim ($H(S) = H_{\text{wall}} \cdot (0.2 + 0.8S)$).
- **Aesthetic Verification Gate**: Adds an automated contact sheet generator (`tools/test_report.py run --renders`) producing a 12-image matrix (`reports/contact_sheet.png`) for visual review, backed by an empirical tortuosity floor ($\text{median} \ge 1.05$) measured per junction-to-junction segment.
- **UI Default Update**: Sets **Vein Inlay** as the default fracture mode in the Windows XP Luna GUI. (The legacy Voronoi generator remains accessible via CLI flag `--generator voronoi` for comparative audits, but is not exposed in the GUI).

## Capabilities

### New Capabilities
*(None - all changes evolve existing capabilities)*

### Modified Capabilities
- `mesh-fracture-engine`: Modifies crack graph generation requirements to use rim-seeded growth with stop-on-hit T-junctions; defines explicit clearance, incidence angle, and growth termination rules; guarantees planarity on shipped growth paths; and enforces non-puncture ceramic clearance for vein inlays.
- `retro-web-gui`: Updates default fracture mode selection to Vein Inlay.

## Impact

- **Affected Code**: `kintsugi.py` (implements `generate_crack_growth_paths`, keeps Voronoi behind CLI flag, updates vein cutter depth), `web_app.py`, `static/index.html`, `static/viewer.js`, `tools/test_report.py`.
- **Dependencies**: Zero new dependencies. Uses standard `numpy` and existing math utilities.
- **Backward Compatibility & Breaking Changes**:
  - **BREAKING (Visual Output)**: Because the default crack generator changes from Voronoi to crack growth, identical random seeds will yield completely different, organic fracture patterns. This is intentional for an artistic installation.
  - **BREAKING (API Default)**: `POST /api/fracture` defaults to `vein` mode and `growth` generator.
  - **Preserved**: Output container schemas (`ceramic_body.stl`, `gold_seams.stl`, `kintsugi_assembly.3mf`) remain 100% structurally conforming to 3MF Core Specifications.
