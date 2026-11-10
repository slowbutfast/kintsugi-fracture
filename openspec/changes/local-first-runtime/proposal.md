## Why

Every upload and download bottleneck encountered on the project stems from **hosted** serverless execution, not the procedural fracture engine:
- the 4.5 MB serverless request body ceiling;
- ephemeral per-instance `/tmp` storage;
- the 300 s function timeout;
- a public upload attack surface with unauthenticated processing and deferred memory vulnerabilities.

Outputs on real meshes can easily exceed hosted limits (e.g., the urdformer bowl produces ~8.1 MB of ceramic STL alone). For a personal, non-commercial 3D printing tool, running computation on the user's local machine is the better default.

## What Changes

Two tracks: **Track A is the implementation proposal. Track B is a documented feasibility study with a gated spike.**

- **Track A: Local-First Companion Runtime.**
  - **Native Local Studio (`kintsugi-studio`)**: A PEP 621 `pyproject.toml` console script entrypoint. It runs the FastAPI server on `127.0.0.1`, probes port 8000 (reusing an existing Kintsugi instance or falling back deterministically across 8000–8009 if occupied), and opens the browser to `http://127.0.0.1:8000`. This is the primary same-origin path (zero CORS, zero mixed content, zero browser permission prompts, works in all browsers including Safari).
  - **Hosted GUI (`https://kintsugi-studio.vercel.app`) as Static Companion**: Vercel serves the Windows XP web GUI and presets purely as static assets (removing Python `functions` from `vercel.json` and deprecating `app.py`). This eliminates hosted compute costs, upload attack surfaces, and the 2 GB memory vulnerability.
  - **Secure Local Companion Connection & Local Network Access (LNA)**: When loaded on the hosted site, the GUI does not auto-poll loopback. Users connect via an explicit **"Connect Engine"** button (user gesture compliant with Chrome 142+ LNA permission prompts). If connection fails or is blocked (e.g. Safari blocking HTTPS → HTTP loopback as mixed content), the GUI displays an informative fallback link: **"Open Local App (127.0.0.1:8000) ↗"**.
  - **Pure ASGI Security**: Strict origin verification for CORS and LNA preflights, allowing only loopback and trusted Vercel production/preview origins. Disallows credentials (`allow_credentials=False`) and rejects untrusted web origins with 403.
  - **Asset URL Rewriting & Version Handshake**: Output and download URLs (`/outputs/...`) are dynamically resolved against the active local engine base URL. An `api_version` handshake in `GET /api/health` ensures the hosted GUI and local engine remain compatible.
  - **Guard Instrumentation**: Adds `timings["guard"]` to measure F1 export/repair guard time in `kintsugi.py`.
- **Track B: Browser-Local Execution (Feasibility Only).**
  - Retain research on Pyodide + Web Worker `manifold3d` WASM shim.
  - Documents hard requirements: `Mesh64` (float64) precision, ~6,000+ ray casts per fracture, and mandatory manual WASM object `.delete()`.
  - Defined Gate 0 spike required before any implementation.

## Capabilities

### New Capabilities
- `local-runtime`: Native console launcher (`kintsugi-studio`), deterministic port probing (8000–8009), instance reuse via `/api/health`, pure ASGI CORS and Local Network Access (LNA) security middleware, non-loopback `--host` security warnings, and `timings["guard"]` instrumentation.

### Modified Capabilities
- `retro-web-gui`: Static hosted deployment, user-gesture "Connect Engine" flow, Local Network Access permission handling, "Open Local App" fallback for Safari/mixed-content blocks, `resolveEngineUrl` asset URL qualification, and API version compatibility verification.

## Impact

- **New:** `pyproject.toml` with `kintsugi-studio = "web_app:studio"` script; pure ASGI `SecurityCORSMiddleware`.
- **Edited:**
  - `web_app.py`: port negotiation (8000–8009), `/api/health` `api_version` advertisement, non-loopback security warning, and pure ASGI CORS/LNA middleware;
  - `static/viewer.js` & `static/index.html`: "Connect Engine" button, engine status badge, "Open Local App" link, asset URL rewriting (`resolveEngineUrl`), and `api_version` check;
  - `vercel.json`: remove `functions` entry (static-only deployment);
  - `kintsugi.py`: instrument `timings["guard"]`;
  - `README.md`, `TESTING.md`: document local-first workflow.
- **Unchanged:** Core fracture generators, boolean slicing logic, input vessel envelope validation, and export formats.
