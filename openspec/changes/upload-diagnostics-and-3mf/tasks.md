## 1. Test Scaffolding (TDD)

- [x] 1.1 Cherry-pick PR #10 (`e055b34`) onto the implementation branch, so the diagnostics code under test exists; confirm `tests.test_web_api` still passes (18 tests)
- [x] 1.2 Add an in-test 3MF fixture builder (`zipfile`, `_rels/.rels`, core and production namespaces, configurable unit/transforms/items/types/`p:path`) to `tests/fixtures.py`
- [x] 1.3 Write failing tests in `tests/test_mesh_formats.py` for the "3MF package input" requirement: core load, units, transforms, `p:path` resolution with colliding ids, every rejection case, Kintsugi-assembly rejection, `.rels` fallback, and no-repair vertex counts
- [x] 1.4 Write failing tests in `tests/test_web_api.py` for "Request diagnostics and structured error responses": request-id header and body equality; envelopes for 400, 404, 413, 422 and a forced 500; no raw bytes in 422; `assertLogs` arrival, completion and upload lines
- [x] 1.5 Write failing tests in `tests/test_web_api.py` for the modified upload requirement: `/api/health` limit and formats, env override, Vercel default via the resolver, 413 over the limit, `.3mf` validate and fracture, `.ply` rejected with the format list

## 2. Server Diagnostics & Upload Limit (`web_app.py`)

- [x] 2.1 Replace the `BaseHTTPMiddleware` request logger with pure ASGI middleware that sets the request id, logs arrival and completion, and adds `X-Kintsugi-Request-Id`; keep a single `Exception` handler for unhandled errors (no double handling)
- [x] 2.2 Keep the JSON envelope handlers for `StarletteHTTPException`, `RequestValidationError` and `Exception`; move `jsonable_errors` above first use; truncate logged file names to 120 characters
- [x] 2.3 Add `_upload_limit()` (env override → 4 MiB on Vercel → 50 MiB), a module constant used by `_save_upload` and the 413 detail, `ACCEPTED_SUFFIXES`, and `max_upload_bytes` / `accepted_formats` in `/api/health`
- [x] 2.4 Route both suffix checks (`_resolve_input`, `api_validate`) through `ACCEPTED_SUFFIXES` with a detail listing the formats

## 3. 3MF Reader (`mesh_formats.py`, `kintsugi.py`)

- [x] 3.1 Implement `mesh_formats.load_3mf(path)`: root-model discovery through `.rels`, part-name normalisation and traversal rejection, a `(part, id)` object table, a single build item, the component walk with 4×4 composition and depth/cycle limits, unit scaling, type check, `<!DOCTYPE` rejection, size/count caps, assembly detection, and `trimesh.Trimesh(process=False)`
- [x] 3.2 Add the vendor-config modifier/negative-volume check (`Metadata/*.config`)
- [x] 3.3 Dispatch `.3mf` in `kintsugi._load_trimesh`, and accept `.3mf` in the CLI input help text

## 4. Viewer (`static/viewer.js`, `static/index.html`)

- [x] 4.1 Keep `requestJson` from PR #10; load `/api/health` at startup into `state.limits`, with a fallback to defaults plus a console warning
- [x] 4.2 Add `checkUploadAllowed(file, limits)` before preview parsing; refuse over-limit and unsupported files with the design.md copy, sending no request
- [x] 4.3 Implement `read3mf(buffer, { inflateSync })` in `static/threemf.js` (own zip-directory scan, `fflate.inflateSync`, attribute-only XML scanner), mirroring the server rules, and use it for `.3mf` previews; a preview failure shows the design.md message and still runs server validation
- [x] 4.4 Update `#upload-zone` `aria-label`, subtitle (with `up to <N> MB` from health), `#file-input` `accept`, the help dialog line, and the `title` attribute on status-bar error messages

## 5. Verification & Empirical Audit

- [x] 5.1 Run the full regression suite (`./.venv/bin/python -m unittest discover -s tests -v`), verify clean passes and unchanged generator digests, and record the pass counts
- [ ] 5.2 Run the manual checks in tests.md on a local server and on a Vercel preview: over-limit refusal, platform 413 diagnosis, exact platform boundary, slicer 3MF exports and their zip structure, modifier rejection, own-output rejection, and upload-zone copy (PARTIAL: local-server HTTP checks done and logged in verification.md; the Vercel preview, browser, and slicer-export checks are still open)
- [x] 5.3 Populate `verification.md` with the Requirement Adherence Matrix, resolved assumptions (platform byte boundary, slicer 3MF structures, modifier markers), and verbatim execution logs
- [ ] 5.4 Close PR #10 with a link to this change's implementation PR (left for the owner: closing PR #10 is their call once this PR is confirmed)
