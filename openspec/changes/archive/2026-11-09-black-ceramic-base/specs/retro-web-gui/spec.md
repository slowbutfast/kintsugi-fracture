## MODIFIED Requirements

### Requirement: Interactive Three.js 3D viewport
The web GUI SHALL provide an interactive WebGL 3D canvas with orbit controls and physically-based rendering (PBR) materials to preview the ceramic body and gold seams before slicing, rendering the vessel against a gallery off-white inset well.

#### Scenario: Real-time 3D inspection
- **WHEN** a fractured or pristine model is displayed in the viewport
- **THEN** system renders the ceramic body with Kuro-raku matte black diffuse roughness (`#18181b`) and the gold seams with metallic specular reflection (`#ffd700`) against a gallery off-white viewport canvas (`#f0ede0`), allowing mouse orbit, pan, and zoom without clipping outside the inset frame
