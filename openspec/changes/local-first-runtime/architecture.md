# Architecture: Local-First Runtime & Companion GUI

## 1. Context & Motivation

Procedural kintsugi fracture on 3D meshes involves heavy computational geometry: boolean subtraction and intersection using `manifold3d`, normal-directed ray-casting along path points, and multi-part 3MF/STL generation.

Operating this workload inside Vercel serverless functions introduced artificial failure modes:
1. **4.5 MB Payload Limit**: Prevents exporting dense repaired ceramics or 3MF project archives.
2. **300 s Execution Ceiling**: Limits fracture complexity and high fragment counts.
3. **Public Upload Attack Surface**: Memory exhaustion vulnerabilities on arbitrary unauthenticated public uploads.

Moving the computational runtime directly to the user's local hardware eliminates these hosting ceilings while utilizing native C++ Manifold3D binaries.

---

## 2. Dual-Path Architecture

```
+--------------------------------------------------------------------------+
| PATH 1 (Recommended): Native Local Studio (Same-Origin)                  |
| - Terminal command: uv run kintsugi-studio (or kintsugi-studio)          |
| - Automatically opens browser to http://127.0.0.1:8000                   |
| - Both GUI and API served from 127.0.0.1 (Same-Origin)                   |
| - 0 CORS preflights, 0 mixed content issues, 0 browser permission prompts|
| - Universal compatibility: Chrome, Safari, Firefox, Edge                 |
+--------------------------------------------------------------------------+

+--------------------------------------------------------------------------+
| PATH 2: Hosted Vercel Front Door (Cross-Origin Companion)                |
| - Visit https://kintsugi-studio.vercel.app                               |
| - Served statically from Vercel edge CDN (0 serverless compute)          |
| - User clicks "Connect Engine" (User Gesture)                            |
|   * Chrome: Triggers Local Network Access (LNA) permission prompt        |
|   * Firefox: Issues standard CORS preflight                              |
|   * Safari: Mixed-content blocks loopback -> GUI offers direct link:     |
|             "Open in Local Studio (http://127.0.0.1:8000) ↗"             |
| - When connected: API requests posted to http://127.0.0.1:8000           |
| - Asset URLs (/outputs/...) dynamically rewritten to engine base URL     |
+--------------------------------------------------------------------------+
```

---

## 3. Pure ASGI Security & Local Network Access (LNA)

### Threat Model
A local server bound to `127.0.0.1:8000` is accessible to web pages running inside the user's browser via cross-origin requests. An unauthenticated server with wildcard CORS would allow any visited website (e.g. `https://evil.example`) to:
- Read local files or job metadata from `/outputs/...`;
- Flood `/api/fracture` with uploads to fill local disk or trigger memory crashes;
- Fingerprint the user's system via `/api/health`.

### Security Guarantees
1. **Strict Allowed Origins**:
   - `http://localhost:<port>`, `http://127.0.0.1:<port>`
   - `https://kintsugi-studio.vercel.app`
   - `^https://kintsugi-fracture-[a-zA-Z0-9_-]+-joeshmo\.vercel\.app$`
   - Override via `KINTSUGI_ALLOWED_ORIGINS` environment variable.
2. **No Credentials**: `allow_credentials=False`. No session cookies or ambient auth headers are accepted.
3. **Pure ASGI Middleware**: Avoids Starlette's `BaseHTTPMiddleware` (which buffers request bodies and was removed in PR #11).
4. **Local Network Access (LNA) & PNA**:
   - Responds to `Access-Control-Request-Private-Network: true` with `Access-Control-Allow-Private-Network: true` **only** if the requesting `Origin` matches an allowed origin pattern.
   - Unauthorized origins receiving `OPTIONS` preflights receive HTTP 403 with no CORS headers.

---

## 4. Port Negotiation & Instance Reuse

When `kintsugi-studio` launches:
1. Probe `GET http://127.0.0.1:8000/api/health` with a 0.5 s timeout:
   - If response contains `"service": "kintsugi-studio"`, log `"Kintsugi Studio is already running at http://127.0.0.1:8000"`, open browser (unless `--no-open`), and exit 0.
2. If port 8000 is occupied by an unrelated socket:
   - Probe sequential ports `8001` through `8009`.
   - Bind the first available port (falling back to ephemeral if the entire range is occupied).
   - Log bound URL prominently: `Kintsugi Studio running at: http://127.0.0.1:<port>`.
3. Non-loopback warning:
   - If `--host` is not `127.0.0.1`, `localhost`, or `::1`, emit a prominent security warning in console logs.

---

## 5. Client-Side Companion Integration

### User Gesture Connection
Under Chrome 142+ Local Network Access rules, background polling of `127.0.0.1` on page load can fail or trigger unprompted permission blocks. The hosted GUI provides:
- An explicit **"Connect Engine"** button. Clicking it executes the health check as an explicit user gesture.
- A connection badge in the UI showing:
  - `Disconnected`: Engine not yet connected.
  - `Connected (127.0.0.1:8000, API v1.0)`: Ready for local processing.
  - `Failed / Blocked`: Clear error message with direct clickable link: `Open Local App (127.0.0.1:8000) ↗`.

### URL Resolution (`resolveEngineUrl`)
API responses return relative paths:
- `downloads.ceramic_stl` (`/outputs/<job_id>/ceramic_body.stl`)
- `downloads.gold_stl` (`/outputs/<job_id>/gold_seams.stl`)
- `downloads.three_mf` (`/outputs/<job_id>/kintsugi_assembly.3mf`)

The GUI normalizes all asset and API URLs:
```javascript
function resolveEngineUrl(path) {
  if (!path || path.startsWith("http://") || path.startsWith("https://")) return path;
  if (!state.engineBaseUrl) return path;
  return state.engineBaseUrl.replace(/\/+$/, "") + "/" + path.replace(/^\/+/, "");
}
```

### Version Handshake
`/api/health` returns `"api_version": "1.0"`. If the hosted GUI's expected major version differs from the local engine's reported version, the GUI alerts the user to update their local clone (`git pull`).

---

## 6. Guard Timing Instrumentation

In `kintsugi.py`, wrap the F1 round-trip validation guard (`_export_trimesh` + `_stl_bad_edge_count` on ceramic and gold meshes) with timing measurement and record `timings["guard"]`. This directly verifies whether the ~8 s dense mesh delay on `bowl_urdformer` is attributable to the STL repair audit.

---

## 7. Track B: In-Browser Feasibility Study & Early Gate 0

Track B investigates running the full Python engine in-browser via Pyodide and Web Workers.
Key constraints:
1. **Precision**: `kintsugi.py` relies on `mf.Mesh64` (float64 precision). Truncating coordinates to `Float32Array` in WASM risks boolean intersection self-intersections.
2. **Ray-Casting Frequency**: Engine executes ~6,000+ ray casts per run in Python loops. Cross-FFI overhead between Pyodide and JS WASM proxies must be measured.
3. **Manual Memory Management**: Manifold C++ WASM objects must be manually freed via `.delete()`.
4. **Gate 0 Requirement**: Before implementing shims or workers, verify in a standalone Node script that the published `manifold-3d` npm package can import a real vessel mesh, execute radial ray casts, perform one boolean cut, and export watertight STL without errors.
