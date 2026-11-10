## 1. Test Scaffolding (TDD)

- [ ] 1.1 Scaffold failing unit tests in `tests/test_local_runtime.py` for `pyproject.toml` dependency parity with `requirements.txt`
- [ ] 1.2 Scaffold failing tests for pure ASGI CORS origin filtering (allowing loopback/Vercel, rejecting `evil.example` with 403, and disallowing credentials)
- [ ] 1.3 Scaffold failing tests for Local Network Access (LNA) / PNA preflight header response (`Access-Control-Allow-Private-Network`)
- [ ] 1.4 Scaffold failing tests for port negotiation, instance reuse via `/api/health`, and non-loopback host warning in `studio()`
- [ ] 1.5 Scaffold failing tests for `timings["guard"]` instrumentation in `kintsugi.py`
- [ ] 1.6 Scaffold JavaScript unit tests in `tests/test_viewer_js.py` for `resolveEngineUrl`

## 2. Packaging & Security Middleware Implementation

- [ ] 2.1 Create `pyproject.toml` with PEP 621 metadata, dependencies matching `requirements.txt`, and console script `kintsugi-studio = "web_app:studio"`
- [ ] 2.2 Implement pure ASGI `SecurityCORSMiddleware` in `web_app.py` enforcing strict origin validation and LNA header handling without `BaseHTTPMiddleware`
- [ ] 2.3 Implement launcher entrypoint `studio(argv=None)` in `web_app.py` with port probing (8000–8009), instance reuse, and security warnings
- [ ] 2.4 Add `timings["guard"]` measurement around the F1 STL round-trip and manifold audit in `kintsugi.py`
- [ ] 2.5 Update `vercel.json` to remove Python `functions` block and configure static CDN asset delivery; deprecate `app.py`

## 3. Web GUI Companion Integration

- [ ] 3.1 Implement `resolveEngineUrl` in `static/viewer.js` to dynamically prefix API calls and output download URLs with the active engine base URL
- [ ] 3.2 Add "Connect Engine" user gesture button, connection status badge, and "Open Local App (127.0.0.1:8000) ↗" fallback link to the Windows XP interface
- [ ] 3.3 Implement `api_version` handshake in `GET /api/health` and verify compatibility on companion connection

## 4. Verification & Empirical Audit

- [ ] 4.1 Perform Gate 0 cross-browser verification on real HTTPS Vercel preview (Chrome LNA prompt, Firefox CORS, Safari mixed content fallback)
- [ ] 4.2 Run full regression test suite (`python -m unittest discover -s tests -v`) and verify clean pass across all generators
- [ ] 4.3 Strictly validate OpenSpec change artifacts (`openspec validate local-first-runtime --strict`)
- [ ] 4.4 Populate `verification.md` with Requirement Adherence Matrix, resolved assumptions, and verbatim execution logs
