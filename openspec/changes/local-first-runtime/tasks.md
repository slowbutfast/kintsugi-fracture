## 1. Test Scaffolding (TDD)

- [ ] 1.1 Scaffold failing unit tests in `tests/test_local_runtime.py` for `pyproject.toml` dependency parity with `requirements.txt`
- [ ] 1.2 Scaffold failing tests for pure ASGI CORS origin filtering matching `https://kintsugi-fracture-joeshmo.vercel.app` and preview URLs
- [ ] 1.3 Scaffold failing tests for server-side rejection of simple `POST` requests and `/outputs/*` reads from unauthorized `Origin` headers before body consumption
- [ ] 1.4 Scaffold failing tests for `Host` header DNS rebinding rejection (rejecting hosts outside loopback)
- [ ] 1.5 Scaffold failing tests for Local Network Access (LNA) / PNA preflight header response (`Access-Control-Allow-Private-Network`)
- [ ] 1.6 Scaffold failing tests for port negotiation (8000–8009), instance reuse via `/api/health`, and non-loopback host warning in `studio()`
- [ ] 1.7 Scaffold failing tests for `timings["guard"]` instrumentation in `kintsugi.py`
- [ ] 1.8 Scaffold JavaScript unit tests in `tests/test_viewer_js.py` for `resolveEngineUrl` and static preset index loading

## 2. Packaging & Security Middleware Implementation

- [ ] 2.1 Create `pyproject.toml` with PEP 621 metadata, dependencies matching `requirements.txt`, and console script `kintsugi-studio = "web_app:studio"`
- [ ] 2.2 Implement pure ASGI `SecurityCORSMiddleware` in `web_app.py` enforcing strict origin validation, state-changing POST checks, Host header validation, and LNA header handling without `BaseHTTPMiddleware`
- [ ] 2.3 Implement launcher entrypoint `studio(argv=None)` in `web_app.py` with sequential port probing (8000–8009), instance reuse, and security warnings
- [ ] 2.4 Add `timings["guard"]` measurement around the F1 STL round-trip and manifold audit in `kintsugi.py`
- [ ] 2.5 Generate `static/presets/index.json` containing metadata for bundled presets
- [ ] 2.6 Update `vercel.json` with static rewrites; remove `app.py` so Vercel deploys purely as static CDN assets

## 3. Web GUI Companion Integration

- [ ] 3.1 Implement `resolveEngineUrl` in `static/viewer.js` to dynamically prefix API calls and output download URLs with the active engine base URL
- [ ] 3.2 Update preset loading in `static/viewer.js` to fall back to `/presets/index.json` when disconnected from a local engine
- [ ] 3.3 Add "Connect Engine" user gesture button, sequential port range probing (8000–8009), connection status badge, and "Open Local App (127.0.0.1:8000) ↗" fallback link to the Windows XP interface
- [ ] 3.3 Implement `api_version` handshake in `GET /api/health` and verify compatibility on companion connection

## 4. Verification & Empirical Audit

- [ ] 4.1 Perform Gate 0 cross-browser verification on real HTTPS Vercel preview (Chrome LNA prompt, Firefox CORS, Safari mixed content fallback)
- [ ] 4.2 Run full regression test suite (`python -m unittest discover -s tests -v`) and verify clean pass across all generators
- [ ] 4.3 Strictly validate OpenSpec change artifacts (`openspec validate local-first-runtime --strict`)
- [ ] 4.4 Populate `verification.md` with Requirement Adherence Matrix, resolved assumptions, and verbatim execution logs
