## 1. Test Scaffolding (TDD)

- [x] 1.1 Scaffold failing unit tests in `tests/test_local_runtime.py` for `pyproject.toml` dependency parity with `requirements.txt`
- [x] 1.2 Scaffold failing tests for pure ASGI CORS origin filtering matching `https://kintsugi-fracture-joeshmo.vercel.app` and opt-in preview URLs
- [x] 1.3 Scaffold failing tests for server-side rejection of simple `POST` requests and `/outputs/*` reads from unauthorized `Origin` headers before body consumption
- [x] 1.4 Scaffold failing tests for `Host` header DNS rebinding rejection (rejecting hosts outside loopback)
- [x] 1.5 Scaffold failing tests for Local Network Access (LNA) client behavior: `targetAddressSpace: "loopback"` and granular permission fallback (no PNA header gate)
- [x] 1.6 Scaffold failing tests for port negotiation (8000–8009), instance reuse via `/api/health`, and non-loopback host warning in `studio()`
- [x] 1.7 Scaffold failing tests for `timings["guard"]` instrumentation in `kintsugi.py`
- [x] 1.8 Scaffold JavaScript unit tests in `tests/test_viewer_js.py` for `resolveEngineUrl` and static preset index loading

## 2. Packaging & Security Middleware Implementation

- [x] 2.1 Create `pyproject.toml` with PEP 621 metadata, dependencies matching `requirements.txt`, and console script `kintsugi-studio = "web_app:studio"`
- [x] 2.2 Implement pure ASGI `SecurityCORSMiddleware` in `web_app.py` enforcing strict origin validation, state-changing POST checks, Host header validation, and standard CORS/LNA behavior without `BaseHTTPMiddleware`
- [x] 2.3 Implement launcher entrypoint `studio(argv=None)` in `web_app.py` with sequential port probing (8000–8009), instance reuse, and security warnings
- [x] 2.4 Add `timings["guard"]` measurement around the F1 STL round-trip and manifold audit in `kintsugi.py`
- [x] 2.5 Generate `static/presets/index.json` containing metadata for bundled presets
- [x] 2.6 Update `vercel.json` with a dedicated static `public/` build output; remove `app.py` so Vercel deploys purely as static CDN assets
- [x] 2.7 Trust Vercel preview origins only with explicit `--allow-previews` / `KINTSUGI_ALLOW_PREVIEWS=1` opt-in
- [x] 2.8 Exclude repository docs, Python sources, and scratch files from the static CDN deploy

## 3. Web GUI Companion Integration

- [x] 3.1 Implement `resolveEngineUrl` in `static/viewer.js` to dynamically prefix API calls and output download URLs with the active engine base URL
- [x] 3.2 Update preset loading in `static/viewer.js` to fall back to `/presets/index.json` when disconnected from a local engine
- [x] 3.3 Add "Connect Engine" user gesture button, sequential port range probing (8000–8009), connection status badge, and "Open Local App (127.0.0.1:8000) ↗" fallback link to the Windows XP interface
- [x] 3.4 Implement `api_version` handshake in `GET /api/health` and verify compatibility on companion connection
- [x] 3.5 Declare `targetAddressSpace: "loopback"` on every loopback health/API/`/outputs` request and query the granular `loopback-network` permission before probing

## 4. Verification & Empirical Audit

- [ ] 4.1 Perform Gate 4.1 cross-browser verification on real HTTPS Vercel preview (root `/` loads the GUI, Chrome LNA prompt, Firefox CORS, Safari mixed content fallback) — requires a deployed preview plus interactive Chrome/Firefox/Safari sessions; not executable in this headless environment
- [x] 4.2 Run full regression test suite (`python -m unittest discover -s tests -v`) and verify clean pass across all generators
- [x] 4.3 Strictly validate OpenSpec change artifacts (`openspec validate local-first-runtime --strict`)
- [x] 4.4 Populate `verification.md` with Requirement Adherence Matrix, resolved assumptions, and verbatim execution logs
