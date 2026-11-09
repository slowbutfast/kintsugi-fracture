---
name: Kintsugi Studio 2001 (Windows XP Luna). Inherited from DESIGN.md, no new tokens
colors:
  primary: "#0058ee"
  secondary: "#316ac5"
  background: "#ece9d8"
  surface: "#ffffff"
  text:
    primary: "#222222"
    muted: "#444444"
  border: "#808080"
  status:
    success: "#2e8b14"
    warning: "#b8860b"
    error: "#c02020"
typography:
  fontFamily:
    sans: "'Tahoma', 'Segoe UI', sans-serif"
    mono: "'Lucida Console', monospace"
  scale:
    h1: "13px, weight 700"
    h2: "11px, weight 700"
    body: "11px desktop / 16px mobile form controls, weight 400"
    caption: "10px, weight 400"
spacing:
  xs: "2px"
  sm: "4px"
  md: "8px"
  lg: "12px"
  xl: "16px"
rounded:
  sm: "2px"
  md: "3px"
  lg: "4px"
  full: "9999px"
---

## 1. Visual Overview & Philosophy

The UI changes are copy only, plus two existing components:
- the **upload zone** (`#upload-zone`), which advertises the formats and the size limit;
- the **status bar** (`#status-operation`, `#status-mesh`), which gets clearer error messages.

There are no new components or tokens, and nothing moves. The console diagnostics are a developer surface with no visual design. All styling inherits from `DESIGN.md` and the archived `mobile-ui-menus` design.

## 2. Color System & Contrast

No new colours. Error states reuse the existing status-bar error tone (`#c02020`). It's applied by `updateMeshStatus(..., "error")` and, as today, sits on the `#ece9d8` chassis. Existing pairs are unchanged and already audited in `mobile-ui-menus` (`#222222` on `#ece9d8`, 12.6:1).

## 3. Typography Hierarchy

Unchanged:
- `.upload-subtitle`: Tahoma 10px;
- `.field-note`: Tahoma 10px, `#444444`;
- status-bar cells: Lucida Console 11px.

Status-bar messages can now be longer. The cells keep their existing single-line ellipsis, and the full text is available in the console log and the element's `title` attribute.

## 4. Component Anatomy & States

### Upload zone (`#upload-zone`)
- **`aria-label`:** `Upload a custom STL, OBJ or 3MF`.
- **`.upload-subtitle`, idle:** `.stl, .obj or .3mf · watertight only · up to <N> MB`.
  - `<N>` comes from `max_upload_bytes` in `/api/health`, shown with one decimal place in MB (1 MB = 1,048,576 bytes), e.g. `4.0 MB` hosted and `50.0 MB` locally.
  - Until health loads, or if it fails, the subtitle omits the size phrase.
- **`accept` on `#file-input`:** `.stl,.obj,.3mf`.
- **Hover, focus and drag-over** are unchanged.

### Status-bar messages (copy contract)

| Situation | `#status-operation` text | `#status-mesh` tone |
| :--- | :--- | :--- |
| File over the limit (refused before upload) | `<name> is <X.X> MB; this deployment accepts up to <N.N> MB. Run locally for larger files, or export as binary STL or 3MF.` | error |
| Unsupported suffix | `<name>: unsupported format. Use .stl, .obj or .3mf.` | error |
| 3MF preview failed (validation still runs) | `Preview unavailable for <name>: <reason>. Checking on the server…` | none until validation answers |
| Server rejected the 3MF structure | `Invalid model: <detail>` (existing pattern) | error |
| Platform error (non-JSON) | `<label>: server returned non-JSON (HTTP <status> …). See browser console.` (PR #10 wording) | error |
| App error | `<label>: HTTP <status> [<error_type>]: <detail> (request <id>)` (PR #10 wording) | error |

Every status-bar error message is also set as the cell's `title`, so the full text shows on hover when it's truncated.

### Help dialog
- Line 262 (`Choose a bundled preset or upload a watertight .stl / .obj model.`) becomes `… a watertight .stl, .obj or .3mf model (single object).`

## 5. Responsive Layout & Breakpoints

No layout change. The subtitle wraps within the existing upload zone at ≤ 900 px. Touch target sizes are unchanged (the upload zone already meets 44 px).

## 6. Interaction, Motion & Sound

- **Over-limit and unsupported files** are refused instantly, with no spinner and no viewport change. The previous model stays loaded.
- **3MF preview** behaves like STL: it frames the object on load, and there's no new animation.

## 7. Do's and Don'ts

- **DO** keep error copy in plain words with the numbers in it: the size, the limit, the status.
- **DO** keep the full diagnostic detail in the console and keep the status bar to one sentence plus "See browser console".
- **DON'T** add a new modal or toast for upload errors. The status bar is the established error surface.
- **DON'T** show raw JSON or stack traces in the UI.
