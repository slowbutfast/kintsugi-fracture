## Source material

- **2026-11-08, Project Lead**: "/plan mobile compatilibity for the website? i was thinking primarily in relation to the ui/menus."
- **2026-11-08, Project Lead Design Decisions**:
  - **Mobile Screen Layout**: "(Recommended) Pinned top 3D viewport + tabbed control panels below (Model / Fracture / Export) + sticky Fracture button"
  - **Menu Bar Behavior**: "(Recommended) Real Windows XP dropdown menus (File / Presets / Mode / Help) on both desktop & mobile, plus quick-switching tabs on mobile"
- **2026-11-08, Project Lead**: "/openspec-ff-change for the mobile_ui_menus change"

### Raised but not acted on

- **Slide-Up Bottom Drawer / Sheet Overlay**: Considered hiding all controls inside a slide-up overlay drawer over a full-screen 3D viewport. Rejected in favor of a split pinned top 3D viewport (`~36–38dvh`) + bottom tabbed XP control sheet (`Model` | `Fracture` | `Export`) + sticky `⚡ FRACTURE MESH` button so the user can adjust the $R$ slider and generator/mode controls while continuously seeing the 3D vessel above.
- **Single Long Scrollable Column on Mobile**: Considered keeping all 4 sidebar panels stacked vertically in a single scrollable page. Rejected because 4 stacked panels (~650px) push the 3D viewport below the fold on mobile phones and cause scroll-vs-orbit gesture conflicts.

## Glossary

| Term | Means | Does NOT mean |
| :--- | :--- | :--- |
| **Pinned Top 3D Viewport** | On mobile (`max-width: 900px`), ordering `.viewport-shell` above `.sidebar` with a dedicated height (`clamp(200px, 36dvh, 310px)`) and `touch-action: none` on `#viewport` so Three.js `OrbitControls` never fights vertical page scrolling. | A `position: fixed` floating overlay that obscures form controls. |
| **Mobile XP Tab Strip (`.mobile-tabs`)** | A 3-tab raised beveled Windows XP control switcher (`Model`, `Fracture`, `Export`) shown on viewports $\le 900\text{px}$ that toggles `.mobile-panel-active` on the corresponding `.panel[data-tab-panel]` sections. | Replacing the desktop sidebar (on viewports $> 900\text{px}$, `.mobile-tabs` is hidden and all sidebar panels remain simultaneously visible). |
| **Windows XP Dropdown Menu (`.menu-dropdown`)** | Classic early-2000s beveled popup menu attached to each `.menu-entry` (`File`, `Presets`, `Mode`, `Help`) in `<nav class="menu-bar">`, supporting mouse click, touch tap, outside-click dismissal, and `Escape` key closure on both desktop and mobile. | Native `<select>` elements placed inside the top menu bar. |

## External research

| Source | What it establishes | Licence | Accessed |
| :--- | :--- | :--- | :--- |
| iOS Safari / WebKit Form Control Auto-Zoom Behavior | Form controls (`<select>`, `<input>`) with computed `font-size < 16px` trigger automatic viewport zoom on focus in iOS Safari; setting `font-size: 16px` inside `@media (max-width: 900px)` prevents unwanted page zoom. | Web Platform Standard | 2026-11-08 |
| CSS Values and Units Module Level 4 (`dvh`) | `100dvh` adapts dynamically as mobile browser address/navigation toolbars expand or retract, preventing bottom status bars and sticky action buttons from being clipped off-screen. | W3C Specification | 2026-11-08 |

## Candidate tech

| Option | Decision | Reason | Date |
| :--- | :--- | :--- | :--- |
| Vanilla HTML/CSS/JS Menu & Tab Controller + `ResizeObserver` | Adopted | Zero external dependencies, preserves single-file `xp.css` and `viewer.js` architecture required by `DESIGN.md`. | 2026-11-08 |
| External UI Library (Bootstrap / Tailwind / Radix) | Rejected | Explicitly forbidden by `DESIGN.md` ("Don't use heavy external CSS frameworks or Node.js build pipelines; keep the styling in a single, crisp, readable `xp.css`"). | 2026-11-08 |

## Patterns adopted

- **`ResizeObserver` on `#viewport`**: Observing `ui.viewport` in `static/viewer.js` so any layout shift (mobile tab change, dynamic address bar resize, maximize toggle) immediately calls `onResize()` and updates the Three.js camera aspect and renderer size.
- **Bidirectional Control & Menu State Sync**: Selecting a preset, generator, or mode from either the top Windows XP dropdown menus (`Presets`, `Mode`) or the sidebar form controls updates both the form inputs and the menu checkmarks (`✓`), and switches to the relevant mobile tab when appropriate.

## Verified facts

| Claim | Value | How verified | Date | Volatility |
| :--- | :--- | :--- | :--- | :--- |
| Existing mobile `@media (max-width: 900px)` rule in `static/xp.css` | `L664-L682` stacks `.sidebar` first (`auto`) and `.viewport-shell` second (`minmax(280px, 1fr)`), burying the 3D viewport below all 4 sidebar panels | Direct inspection of `static/xp.css:664-682` | 2026-11-08 | stable |
| Existing `<nav class="menu-bar">` in `static/index.html` | `L30-L35` contains 4 buttons (`File`, `Presets`, `Mode`, `Help`) that only trigger `data-focus` (`viewer.js:497-502`), with no dropdown menus | Direct inspection of `static/index.html:30-35` and `static/viewer.js:497-502` | 2026-11-08 | stable |
| Input font-size in `static/xp.css` | `L68-L73` sets `button, input, select { font-size: 11px; }`, which triggers iOS Safari auto-zoom on tap | Direct inspection of `static/xp.css:68-73` | 2026-11-08 | stable |

## Unverified assumptions

| Assumption | Confidence | Verification Plan |
| :--- | :--- | :--- |
| `clamp(200px, 36dvh, 310px)` viewport height on $\le 900\text{px}$ leaves sufficient vertical room for the active tab panel and sticky `⚡ FRACTURE MESH` button on $375 \times 667$ and $390 \times 844$ screens | High | Verify on mobile viewport dimensions (`375x667`, `390x844`) and confirm zero clipped controls. |

## Superseded claims

| Superseded Claim | What Replaced It | Reason |
| :--- | :--- | :--- |
| "`@media (max-width: 900px)` with `grid-template-rows: auto minmax(280px, 1fr)` provides adequate mobile responsiveness" | "Mobile viewports require `.viewport-shell` ordered first (`order: -1`) above a tabbed `.sidebar` (`Model` / `Fracture` / `Export`) with a sticky action button and `100dvh` window sizing" | Stacking 4 tall form panels above the 3D canvas hides the 3D model off-screen and causes touch scroll conflicts. |

## Links out

- [mobile_ui_menus_plan.md](file:///home/node/.gemini/antigravity-cli/brain/faa7bdb1-6652-4211-a0bc-d2e552084921/mobile_ui_menus_plan.md) - Technical design and Target Context Map for `mobile-ui-menus`.
- [DESIGN.md](file:///home/node/global-sandbox/projects/wax-robot/DESIGN.md) - Windows XP Luna Retro Minimalist design system tokens and constraints.
