## Why

Every upload and download problem encountered since 2026-11-08 stems from **hosted** serverless execution, not the procedural fracture engine:
- the 4.5 MB request/response limit;
- ephemeral per-instance `/tmp`;
- the 300 s function limit;
- an unauthenticated public upload surface with deferred 2 GB memory vulnerabilities.

Real models already produce outputs the hosted app cannot serve (the urdformer bowl's hybrid ceramic is ~8.1 MB binary STL). For a personal 3D printing utility, native local computation is the right default.

## What Changes

Two tracks: **Track A is the implementation proposal. Track B is a documented feasibility study with a gated spike.**

- **Track A: Local-First Companion Runtime.**
  - **Native Local Studio (`kintsugi-studio`)**: A PEP 621 `pyproject.toml` console script entrypoint (`uv run kintsugi-studio` or `pip install -e . && kintsugi-studio`). It binds `127.0.0.1`, probes port 8000 (reusing an existing Kintsugi instance or probing 8001–8009 if occupied), and opens the browser to `http://127.0.0.1:8000`. This same-origin path is universal across all browsers (zero CORS, zero mixed content, zero permission prompts).
  - **Hosted GUI (`https://kintsugi-fracture-joeshmo.vercel.app`) as Static Companion**: Vercel serves the Windows XP GUI and presets purely as static files. To ensure static delivery, remove `app.py`, update `vercel.json` with clean static rewrites, bundle `presets/index.json` so presets load offline/statically, and eliminate Python serverless compute costs and upload attack surfaces completely.
  - **Secure Local Companion Connection & Local Network Access (LNA)**: When loaded on the hosted site, the GUI does not auto-poll loopback. Users connect via an explicit **"Connect Engine"** button (user gesture compliant with Chrome 142+ LNA permission prompts). If connection fails or is blocked (e.g. Safari blocking HTTPS → HTTP loopback as mixed content), the GUI displays an informative fallback link: **"Open Local App (127.0.0.1:8000) ↗"**.
  - **Strict Server-Side Security**:
    - Rejects cross-origin `POST` requests and `/outputs/*` reads with HTTP 403 before reading bodies if `Origin` is present and does not match allowed origins (`http://127.0.0.1:<port>`, `http://localhost:<port>`, `https://kintsugi-fracture-joeshmo.vercel.app`, or `^https://kintsugi-fracture-[a-zA-Z0-9_-]+-joeshmo\.vercel\.app$`).
    - Enforces a `Host` header check to prevent DNS rebinding attacks.
    - Pure ASGI middleware, `allow_credentials=False`.
  - **Asset URL Rewriting & Version Handshake**: Output and download URLs (`/outputs/...`) are dynamically resolved against the active local engine base URL. An `api_version` handshake in `GET /api/health` ensures the hosted GUI and local engine remain compatible.
  - **Guard Instrumentation**: Adds `timings["guard"]` in `kintsugi.py` to measure F1 export/repair guard time.
- **Track B: Browser-Local Execution (Feasibility Study).**
  - Retain research on Pyodide + Web Worker `manifold3d` WASM shim (B1), custom Pyodide wheel (B2), and TypeScript port (B3).
  - Documents hard requirements: `Mesh64` (float64) precision, ~11,000 runtime ray casts per run across 6 call sites, and mandatory manual WASM object `.delete()`.
  - Defined Gate 0 (standalone Node test with published `manifold-3d`) followed by 5 measurable go/no-go parity criteria.

## Capabilities

### New Capabilities
- `local-runtime`: Native console launcher (`kintsugi-studio`), deterministic port probing (8000–8009), instance reuse via `/api/health`, pure ASGI server-side origin/host security middleware, non-loopback `--host` security warnings, and `timings["guard"]` instrumentation.

### Modified Capabilities
- `retro-web-gui`: Static hosted deployment, static `presets/index.json` fallback, user-gesture "Connect Engine" flow, Local Network Access permission handling, "Open Local App" fallback for Safari/mixed-content blocks, `resolveEngineUrl` asset URL qualification, and API version compatibility verification.

## Impact

- **New:** `pyproject.toml` with `kintsugi-studio = "web_app:studio"` script; pure ASGI `SecurityCORSMiddleware`; `static/presets/index.json`.
- **Edited:**
  - `web_app.py`: port negotiation (8000–8009), `/api/health` `api_version` advertisement, non-loopback security warning, and pure ASGI origin/host security check;
  - `static/viewer.js` & `static/index.html`: "Connect Engine" button, engine status badge, "Open Local App" link, asset URL rewriting (`resolveEngineUrl`), and static preset fallback;
  - `vercel.json`: configure static routing; remove `app.py`;
  - `kintsugi.py`: instrument `timings["guard"]`;
  - `README.md`, `TESTING.md`: document local-first workflow.
- **Unchanged:** Core fracture generators, boolean slicing logic, input vessel envelope validation, and export formats.
