# retro-web-gui Specification

## Purpose
TBD - created by archiving change kintsugi-mesh-fracture. Update Purpose after archive.
## Requirements
### Requirement: Windows XP Luna visual design system adherence
The web GUI SHALL strictly adhere to the design tokens and visual style defined in `DESIGN.md`, presenting a single-window Windows XP desktop aesthetic with a Luna royal blue gradient titlebar, beveled borders, Tahoma typography, and inset 3D wells.

#### Scenario: Visual layout rendering
- **WHEN** user opens `http://localhost:8000` in a browser
- **THEN** system renders the `Kintsugi Studio 2001` window frame with royal blue gradient titlebar (`#0058ee` to `#072a8c`), 3-button controls (`_ □ ✕`), menu bar, and Tahoma typography at 11px/12px

### Requirement: Interactive Three.js 3D viewport
The web GUI SHALL provide an interactive WebGL 3D canvas with orbit controls and physically-based rendering (PBR) materials to preview the ceramic body and gold seams before slicing, rendering the vessel against a gallery off-white inset well.

#### Scenario: Real-time 3D inspection
- **WHEN** a fractured or pristine model is displayed in the viewport
- **THEN** system renders the ceramic body with Kuro-raku matte black diffuse roughness (`#18181b`) and the gold seams with metallic specular reflection (`#ffd700`) against a gallery off-white viewport canvas (`#f0ede0`), allowing mouse orbit, pan, and zoom without clipping outside the inset frame

### Requirement: Model preset selection and custom upload
The web GUI SHALL allow selecting bundled preset 3D models or uploading a custom watertight `.stl`, `.obj` or `.3mf` file. Input models must conform to the ceramic vessel envelope ($p_5 \ge 1.6\text{ mm}$ along inward surface normals across the wall range). The `thin_cylinder` model SHALL NOT be offered in user presets.

The deployment SHALL have one upload limit in bytes:
- `KINTSUGI_MAX_UPLOAD_BYTES` when that environment variable is set;
- otherwise 4,194,304 bytes (4 MiB) when the `VERCEL` environment variable is set;
- otherwise 52,428,800 bytes (50 MiB).

`GET /api/health` SHALL report the limit as `max_upload_bytes`, and the accepted suffixes as `accepted_formats` (`[".stl", ".obj", ".3mf"]`). The server SHALL enforce the same limit while streaming the upload. The viewer SHALL read the limit on startup and SHALL refuse a file over it before sending any request.

#### Scenario: Preset model selection
- **WHEN** user chooses a preset model (e.g. `Japanese Tea Bowl` or `Tall Vase`) from the dropdown
- **THEN** system immediately loads and renders the model in the 3D viewport and updates the status bar with mesh metadata

#### Scenario: Custom file upload
- **WHEN** user drags and drops a custom `.stl`, `.obj` or `.3mf` file within the upload limit onto the upload zone
- **THEN** the viewer parses it for preview and calls `POST /api/validate`, which runs `validate_and_load_mesh` in a temporary directory; the status bar reports `Watertight ✓` or `Not a valid closed solid: <detail>` (including wall thickness rejection if $p_5 < 1.6\text{ mm}$, and 3MF structure rejections), and the fracture button stays disabled while the upload is invalid

#### Scenario: Custom 3MF upload preview
- **WHEN** user drops a `.3mf` file containing one build item, whose geometry is split across a component transform and a Production-extension `p:path` part
- **THEN** the viewer previews the same flattened geometry the server validates (transforms applied, parts resolved by path and id, not by bare id), and the status bar reports the server's validation result

#### Scenario: Upload over the limit refused in the browser
- **WHEN** user selects a file larger than the `max_upload_bytes` reported by `GET /api/health`
- **THEN** the viewer sends no request, keeps the fracture button disabled, and the status bar names the file size and the limit in megabytes and suggests running locally or exporting a smaller file (e.g. binary STL or 3MF)

#### Scenario: Upload size cap
- **WHEN** an upload that reaches the app exceeds the upload limit
- **THEN** the API rejects it with HTTP 413 and an app error envelope whose `detail` states the limit, and stores no file

#### Scenario: Unsupported suffix
- **WHEN** a file whose suffix is not `.stl`, `.obj` or `.3mf` is uploaded
- **THEN** the viewer refuses it before upload, and the API, if called directly, returns HTTP 400 with `detail` listing the accepted formats

#### Scenario: Job retention
- **WHEN** a new fracture job starts
- **THEN** job directories older than `KINTSUGI_JOB_TTL_S` (default 3600 s) are deleted, and at most `KINTSUGI_MAX_JOBS` (default 50) directories are retained, oldest first

### Requirement: Real-time parameter controls and fracture execution
The web GUI SHALL provide interactive controls for income ratio $R$, fracture generator (`growth`, `shard`, `hybrid`, or `voronoi`), fracture mode (`vein` vs `ribbon`), and seed, with asynchronous fracture execution and progress feedback. The default fracture generator SHALL be `growth` (Rim Growth) and the default fracture mode SHALL be `vein` (Vein Inlay). When the user selects the `shard` generator (`Shard Planes`) or the `hybrid` generator (`Hybrid (Shard + Growth)`), the web GUI SHALL automatically select `vein` mode and disable the `ribbon` mode option while `shard` or `hybrid` remains active. When `hybrid` is selected, the web GUI SHALL reveal a `#hybrid-settings` control group exposing `through_count`, `through_shape` (distinguishing the edge-reaching `Rim-to-Rim Wedge` default from the closed interior `Closed Tilted Loop`), `tilt_deg`, `hairline_count`, `hairline_reach`, and `roughness` with `Auto` defaults, and SHALL display the resolved values and surface fragment count (`num_fragments`) returned in `parameters.hybrid` after fracture execution. If a client sends any hybrid knob to `POST /api/fracture` when `generator` is not `"hybrid"`, the API SHALL return `HTTP 400 Bad Request`.

#### Scenario: Triggering fracture computation with vein default
- **WHEN** user loads the application, sets $R = 0.35$, and clicks the green `⚡ FRACTURE MESH` button
- **THEN** system dispatches a `POST /api/fracture` request defaulting to `generator: "growth"` and `mode: "vein"`, updates the 3D viewport with the resulting ceramic body and gold lightning veins upon completion, and displays computed volume metrics

#### Scenario: Selecting Shard Planes generator in the Web GUI
- **WHEN** user selects `Shard Planes — tilted kintsugi seams` (`value="shard"`) in `#generator-select` and clicks `⚡ FRACTURE MESH`
- **THEN** the UI automatically checks the `vein` mode radio button, disables the `ribbon` mode radio button, hides `#hybrid-settings`, updates `#generator-note` to indicate Vein Inlay only, and dispatches `POST /api/fracture` with `generator="shard"` and `mode="vein"`

#### Scenario: Selecting Hybrid generator and using Hybrid settings in the Web GUI
- **WHEN** user selects `Hybrid — macro shards + interior hairlines` (`value="hybrid"`) in `#generator-select` or `#menu-mode`
- **THEN** the UI unhides `#hybrid-settings`, automatically checks `vein` mode and disables `ribbon` mode, sends `generator="hybrid"` (plus any overridden hybrid knobs) to `POST /api/fracture`, and updates `#hybrid-resolved-note` in `#hybrid-settings` with the resolved values and fragment count from `parameters.hybrid`

#### Scenario: Rejecting hybrid knobs with non-hybrid generator via API
- **WHEN** a client sends `POST /api/fracture` with `generator="growth"` or `generator="shard"` alongside any hybrid form parameter (e.g. `through_count=2` or `hairline_count=4`)
- **THEN** `POST /api/fracture` returns `HTTP 400 Bad Request` with an error detail explaining that hybrid parameters are only valid when `generator="hybrid"`

#### Scenario: Wealthy parameter setting
- **WHEN** user sets $R \ge 1.0$
- **THEN** system immediately updates the status label to `Pristine / Wealthy (0 cracks)` and renders the intact ceramic body without gold veins

#### Scenario: Seams omitted feedback
- **WHEN** fracture response returns `seams_omitted: true` with $R < 1.0$
- **THEN** system displays `Seams Omitted` in the status indicator without claiming pristine wealth or displaying stale sub-millimeter thickness thresholds

### Requirement: One-click slicer asset download
The web GUI SHALL provide download buttons for exporting individual binary STL files and the unified multi-material `.3mf` container.

#### Scenario: Multi-material 3MF download
- **WHEN** user clicks `Download kintsugi_assembly.3mf`
- **THEN** system downloads the single-object, two-component 3MF archive ready for dual-extrusion slicing in Bambu Studio or PrusaSlicer

### Requirement: Interactive Windows XP menu bar and mobile tabbed layout
The web GUI SHALL provide interactive Windows XP dropdown menus on `<nav class="menu-bar">` (`File`, `Presets`, `Mode`, `Help`) across both desktop and mobile viewports, and SHALL adapt viewports at or below `900px` width to a pinned top 3D viewport with a 3-tab Windows XP control switcher (`Model`, `Fracture`, `Export`) and a sticky primary `⚡ FRACTURE MESH` button.

- **Windows XP Dropdown Menus**:
  - `File` (`#menu-file`) SHALL expose actions to upload a custom `.stl`/`.obj` file (`#menu-upload`), trigger `⚡ Fracture Mesh Now` (`#menu-fracture`), and download generated `Ceramic Body (.stl)` (`#menu-download-ceramic`), `Gold Seams (.stl)` (`#menu-download-gold`), and `Kintsugi Assembly (.3mf)` (`#menu-download-3mf`).
  - `Presets` (`#menu-presets`) SHALL dynamically list bundled presets from `/api/presets` with a checkmark (`✓`) indicating the active preset.
  - `Mode` (`#menu-mode`) SHALL expose generator choices (`growth`, `shard`, `voronoi`) and cut mode choices (`vein`, `ribbon`) with synchronized checkmarks (`✓`), disabling `ribbon` when `shard` is active.
  - `Help` (`#menu-help`) SHALL expose `Reset 3D Camera View` (`#menu-reset-camera`) and `About Kintsugi Studio 2001…` (`#menu-about`), which toggles an informational modal dialog (`#help-dialog`).
- **Mobile Pinned Viewport & Tabbed Control Panels (`max-width: 900px`)**:
  - `.viewport-shell` SHALL be ordered above `.sidebar` (`order: -1`) so the 3D model viewport remains pinned at the top of the window without scrolling.
  - `#mobile-tabs` SHALL render three selectable tabs (`data-tab="model"`, `data-tab="fracture"` active by default, and `data-tab="export"` with an `#export-badge` indicator when downloads are available) that toggle `.mobile-panel-active` on the matching `.panel[data-tab-panel]` sections.
  - `#fracture-button` SHALL remain sticky at the bottom of `.sidebar` on mobile viewports, and `<select>` / `<input>` controls SHALL use `font-size: 16px` with `100dvh` window sizing and a `ResizeObserver` on `#viewport`.

#### Scenario: Opening and using Windows XP dropdown menus
- **WHEN** user clicks or taps `File`, `Presets`, `Mode`, or `Help` in `<nav class="menu-bar">`
- **THEN** the corresponding `.menu-dropdown` opens (`hidden` removed, `aria-expanded="true"`), selecting an item executes its action (loading a preset, switching generator/mode with updated `✓` checkmarks, triggering upload/fracture/download, or opening `#help-dialog`), and clicking outside or pressing `Escape` closes all open dropdown menus

#### Scenario: Mobile pinned top viewport and tab switching
- **WHEN** the application is viewed on a mobile viewport (`max-width: 900px`)
- **THEN** `.viewport-shell` is positioned at the top of `.window-body` (`order: -1`), `#mobile-tabs` is visible with `Fracture` active by default (`data-tab-panel="fracture"` shown, inactive tab panels hidden), tapping `Model` or `Export` switches the visible `[data-tab-panel]` section, and `#fracture-button` remains sticky at the bottom

#### Scenario: Export tab readiness badge and File menu download sync
- **WHEN** a fracture run completes and returns download URLs for ceramic STL, gold STL, and 3MF assets
- **THEN** both the `Slicer Assets` panel links and the `File` menu download links (`#menu-download-ceramic`, `#menu-download-gold`, `#menu-download-3mf`) are enabled with matching `href` attributes, and `#export-badge` is unhidden until the user opens the `Export` tab

#### Scenario: Mobile touch sizing and ResizeObserver viewport sync
- **WHEN** the mobile layout resizes or switches tabs on a coarse-pointer / `max-width: 900px` device
- **THEN** `.window` uses dynamic viewport height (`100dvh`), `.xp-select` and `.xp-input` use `font-size: 16px` (preventing iOS Safari auto-zoom) with touch targets $\ge 40\text{px}$, and the `ResizeObserver` on `#viewport` updates the Three.js renderer dimensions

### Requirement: Request diagnostics and structured error responses
The web app SHALL assign every HTTP request a request id of 12 lowercase hexadecimal characters. It SHALL return the id in an `X-Kintsugi-Request-Id` response header and SHALL include it in every server log line for that request. For each `/api/*` request, the server SHALL log:
- one line on arrival: method, path, content type and content length;
- one line on completion: status and elapsed milliseconds.

`POST /api/validate` and `POST /api/fracture` SHALL also log the uploaded file name, MIME type and bytes received. A rejection SHALL log its reason; an unexpected exception SHALL log its full traceback.

Every error response produced by the app SHALL be JSON with `detail`, `error_type`, `status`, `path` and `request_id`. That covers HTTP errors, request-validation errors and unhandled exceptions. Request-validation error details SHALL NOT echo raw upload bytes.

The viewer SHALL send every API call through one request helper. The helper SHALL:
- read the response body as text before parsing it as JSON;
- log each request and response to the browser console, prefixed `[kintsugi]`. The log SHALL include the request label, URL, form field summary (file name, size, MIME type), status, elapsed time, the headers `content-type`, `content-length`, `x-kintsugi-request-id`, `x-vercel-id`, `x-vercel-error` and `x-vercel-cache`, and up to 2,000 characters of the body;
- raise an error that names the status, content type and the start of the body when the body is not JSON;
- raise an error that names the status, `detail`, `error_type` and request id when an app error arrives;
- report a request that receives no response as a network failure, not a parse error.

#### Scenario: App error returns a JSON envelope with a request id
- **WHEN** `POST /api/fracture` is called with an unknown preset id
- **THEN** the response is HTTP 400 JSON with `detail`, `error_type`, `status: 400`, `path: "/api/fracture"` and a `request_id` equal to the `X-Kintsugi-Request-Id` header

#### Scenario: Unhandled exception returns JSON, not plain text
- **WHEN** an API handler raises an exception other than `ValueError` or `HTTPException`
- **THEN** the response is HTTP 500 JSON whose `error_type` is the exception class name, and the server log contains that request id and the traceback

#### Scenario: Request-validation error does not echo upload bytes
- **WHEN** `POST /api/validate` is called without a `file` field
- **THEN** the response is HTTP 422 JSON in the app error envelope whose `detail` lists the missing field, and contains no raw request body

#### Scenario: Platform error reported by name in the browser
- **WHEN** an API call returns a non-JSON body (e.g. HTTP 413, `text/plain`, body `Request Entity Too Large … FUNCTION_PAYLOAD_TOO_LARGE`, no `X-Kintsugi-Request-Id`)
- **THEN** the console logs the status, headers and body preview under `[kintsugi] ✗ <label>`, and the status bar shows `<label>: server returned non-JSON (HTTP 413 …)` with the start of the body, not a JSON parser message

#### Scenario: Successful call logged
- **WHEN** an API call succeeds
- **THEN** the console logs `[kintsugi] ✓ <label>: HTTP <status> in <ms> ms` with the request id header

