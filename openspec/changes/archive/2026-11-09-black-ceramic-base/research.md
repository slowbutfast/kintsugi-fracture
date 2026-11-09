## Source material

**2026-11-09, project owner (chat):**

> "can you propose a very small openspec change where we change the 'base' color of the objects to black (instead of white), keeping the veins to gold."

**Interactive design alignment (2026-11-09):**
- *Ceramic color tone*: Kuro-raku deep charcoal black (`#18181b` / `0x18181b`) with subtle specular falloff (`roughness: 0.65`, `metalness: 0.10`).
- *Viewport canvas background*: Gallery off-white (`#f0ede0` / `0xf0ede0`) matching the surrounding Windows XP `--surface-inset` well, framed by the 2px sunken bevel (`border-color: #808080 #ffffff #ffffff #808080`) of the `--surface` (`#ece9d8`) chassis.
- *Floor grid & lighting*: Soft warm gray floor grid (`0xb8b4a6` / `0xd0ccc0`) and warm ambient ground bounce (`0xdcd8cc`) so the black vessel and gold seams achieve maximum silhouette clarity and depth.

### Raised but not acted on

- **Pure pitch black (`#000000`) ceramic**: Deliberately avoided. A completely black diffuse material (`0x000000`) with high roughness absorbs all directional lighting and eliminates visible curvature and surface depth. Kuro-raku black (`#18181b`) with subtle specular sheen preserves 3D contours.
- **Dark navy viewport background**: Deliberately transitioned to gallery off-white (`#f0ede0`) per the owner's aesthetic preference. This mirrors authentic museum and exhibition display pedestals for Japanese kintsugi pottery.
- **Dynamic color palette picker**: Considered, but rejected to maintain the minimal, focused early-2000s CAD interface.

## Glossary

| Term | Means | Does NOT mean |
| :--- | :--- | :--- |
| Kuro-raku black | Deep charcoal black ceramic material (`#18181b` / `0x18181b`) inspired by traditional Japanese black raku stoneware | Pure pitch black (`#000000`) or metallic carbon fiber |
| Gallery off-white | Soft warm off-white canvas color (`#f0ede0` / `0xf0ede0`) matching `--surface-inset` | Stark clinical white (`#ffffff`) or beige putty (`#ece9d8`) |
| Base color | The diffuse/specular PBR material applied to the ceramic vessel body | Gold seam material or UI window chrome |

## External research

| Source | What it establishes | Licence | Accessed |
| :--- | :--- | :--- | :--- |
| Japanese Kuro-raku (黒楽) ceramics | Traditional Japanese raku teaware featuring deep, lustrous matte black iron glazes paired with gold lacquer repairs | Cultural domain / Prior art | 2026-11-09 |
| Three.js `MeshStandardMaterial` | Physically-based rendering material using roughness/metalness parameters to catch directional highlights on dark surfaces | MIT | 2026-11-09 |

## Candidate tech

| Option | Decision | Reason | Date |
| :--- | :--- | :--- | :--- |
| Kuro-raku black (`#18181b`) | Adopted | Preserves visible 3D contours under Three.js directional lights while providing maximum contrast with gold seams | 2026-11-09 |
| Pitch black (`#000000`) | Rejected | Absorbs light completely, flattening vessel geometry into 2D silhouettes | 2026-11-09 |
| Gallery off-white canvas (`#f0ede0`) | Adopted | Natural museum-pedestal contrast against black ceramic; harmonizes with Windows XP inset wells | 2026-11-09 |

## Patterns adopted

- **Exhibition Contrast**: Setting a dark ceramic vessel on a subtle warm light pedestal/canvas to maximize visual silhouette separation.
- **Warm Architectural Grid**: Softening floor grid lines to warm neutrals (`0xb8b4a6` / `0xd0ccc0`) with 40% opacity so the drafting floor remains visible without distracting from the model.

## Verified facts

| Claim | Value | How verified | Date | Volatility |
| :--- | :--- | :--- | :--- | :--- |
| Current ceramic material color | `0xf8f6f0` | Inspected `static/viewer.js:72` | 2026-11-09 | stable |
| Current viewport background color | `0x1a1f2c` / `#1a1f2c` | Inspected `static/viewer.js:97` and `static/xp.css:29` | 2026-11-09 | stable |
| Current UI inset surface color | `#f0ede0` | Inspected `static/xp.css:6` and `DESIGN.md:10` | 2026-11-09 | stable |
| Gold seam material color | `0xffd700` / `#ffd700` | Inspected `static/viewer.js:79` and `static/xp.css:32` | 2026-11-09 | stable |
| Contact sheet ceramic color | `(235, 230, 218)` | Inspected `tools/spike_contact_sheet.py:35` | 2026-11-09 | stable |

## Unverified assumptions

| Assumption | Confidence | Verification Cost |
| :--- | :--- | :--- |
| `#f0ede0` viewport background provides sufficient contrast with the `#ece9d8` outer window chassis across various monitor calibrations | High | Visual inspection in browser; separated by 2px beveled border |

## Superseded claims

- **"Viewport canvas should remain dark slate `#1a1f2c`"**: Superseded by gallery off-white `#f0ede0` to achieve the museum-exhibition aesthetic requested by the project owner.

## Links out

- [DESIGN.md](file:///home/node/global-sandbox/projects/wax-robot/DESIGN.md) — visual design tokens and aesthetic guidelines.
