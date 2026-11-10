## Automated Tests

All tests run under the repo's `unittest` runner. 3MF fixtures are built inside the tests with `zipfile` from the existing `tests/fixtures.py` bowl, so no binary fixtures are committed.

- `./.venv/bin/python -m unittest tests.test_mesh_formats -v`:
  - **Core load:** a single-object millimetre 3MF of the fixture bowl loads with identical vertices and face count, and passes `validate_and_load_mesh`.
  - **Units and transforms:**
    - `unit="meter"` plus a build-item translation plus a component rotation gives the expected millimetre coordinates within 1e-6;
    - every unit in the table maps to its factor;
    - an unknown unit raises.
  - **Production extension:** a component with `p:path` resolves the object in the referenced part even when the root defines a colliding id. A `p:path` to a missing part raises. A `p:path` containing `..` raises.
  - **Rejections:** each of the following raises a `ValueError` naming the problem:
    - two build items;
    - zero build items;
    - an object of `type="support"`;
    - a missing object id;
    - a component cycle;
    - nesting deeper than 16 levels;
    - a non-ZIP file;
    - a missing root model;
    - a part with `<!DOCTYPE`;
    - an empty mesh.
  - **Kintsugi assembly:** a package written by `export_kintsugi_3mf` from a real fracture result is rejected as "already a Kintsugi output".
  - **Fallbacks:** a root model found through `_rels/.rels` at a non-default path loads, and a package without `_rels/.rels` falls back to `3D/3dmodel.model`.
  - **Hostile and damaged packages:** an entry whose header understates its size (64 MiB of XML declared as 1,000 bytes) is rejected as corrupt with a traced peak memory under 2 MiB; an honestly declared part over the budget is rejected as too large; a corrupt deflate stream, a wrong CRC and an unsupported compression method each raise `ValueError` naming the part; an oversized vendor config is skipped, not fatal. Over the API, a corrupted 3MF answers `valid: false`, not HTTP 500.
  - **No-repair contract:** the loaded mesh is built with `process=False`, so its vertex count equals the sum of the source objects' vertices (duplicates kept).
- `./.venv/bin/python -m unittest tests.test_web_api -v`:
  - **Request id:** every response carries a 12-hex `X-Kintsugi-Request-Id`, and `request_id` in error bodies equals the header.
  - **Error envelope:**
    - a 400 (unknown preset), a 404 API path and a 413 (upload over a patched-down limit) each return `detail`, `error_type`, `status` and `path`;
    - a 422 (missing `file`) returns the envelope without raw body bytes;
    - a forced unhandled exception (patch `kintsugi.validate_and_load_mesh` to raise `RuntimeError`) returns 500 JSON with `error_type: "RuntimeError"`.
  - **Upload limit:** `/api/health` reports `max_upload_bytes` and `accepted_formats`. With the limit env var set, both the reported and the enforced limit change. With `VERCEL=1` and no override, the reported limit is 4,194,304. This is checked through the limit-resolution function, so the app isn't re-imported.
  - **3MF over the API:** `POST /api/validate` with a valid 3MF returns `valid: true`. A two-item 3MF returns `valid: false` with the single-object message. `POST /api/fracture` with a valid 3MF at R=0.5 succeeds.
  - **Unsupported suffix:** a `.ply` returns 400 whose `detail` lists `.stl, .obj, .3mf`.
  - **Logging:** `assertLogs("kintsugi.web")` captures the arrival and completion lines with the same request id, and the validate upload line with the file name and byte count.
- `./.venv/bin/python -m unittest tests.test_viewer_js -v` (needs Node; skipped without it):
  - **Preview parity:** the same fixtures run through `static/threemf.js` and `mesh_formats.load_3mf` give the same triangle geometry (units, transforms, `p:path` with a colliding id, reused objects, mirrored transforms, stored and deflated zip entries, entity-escaped names) and are rejected for the same reasons (every rejection case above, plus a truncated zip and a package over the size cap).
  - **Upload pre-flight:** within-limit files pass (including exactly at the limit and upper-case suffixes); over-limit files get a message naming the size and the limit; unsupported suffixes list the formats; missing or malformed `/api/health` data falls back to the defaults; the upload-zone subtitle shows the limit only once it is known.
- `./.venv/bin/python -m unittest discover -s tests -v`: the full regression suite stays green, with no change to generator digests.

## Manual Verification

- **Platform limit message (Vercel preview):**
  - **WHEN** the owner drops a 6 MB STL on the preview deployment
  - **THEN** no network request is sent (DevTools Network tab shows none for `/api/validate`), and the status bar says `<name> is 6.0 MB; this deployment accepts up to 4.0 MB …`
- **Platform error still diagnosable:**
  - **WHEN** the client limit is bypassed by setting `KINTSUGI_MAX_UPLOAD_BYTES` above 4.5 MB on a preview and uploading a 4.6 MB file
  - **THEN** the console shows `[kintsugi] ✗ Validate upload: HTTP 413 returned non-JSON body` with `FUNCTION_PAYLOAD_TOO_LARGE`, and the status bar names HTTP 413
- **Exact platform boundary (resolves an unverified assumption):**
  - **WHEN** files of 4,400,000 and 4,600,000 bytes are uploaded with the client limit raised
  - **THEN** record which one reaches the app (it has an `X-Kintsugi-Request-Id`) in `verification.md`
- **Slicer 3MF exports:**
  - **WHEN** a single bowl is exported as 3MF from PrusaSlicer, Bambu Studio and OrcaSlicer (whichever are available) and dropped into the local app
  - **THEN** each previews correctly, validates with the same result as the STL export of the same model, and the zip structure (core vs `p:path`, vendor `Metadata/*.config`, and whether the archive uses ZIP64 markers, which the server accepts but the preview rejects) is recorded in `verification.md`
- **Browser inflate and preview (not testable without a browser):**
  - **WHEN** a deflate-compressed 3MF (e.g. `kintsugi`'s own fixture, or any slicer export) is dropped into the app in a real browser
  - **THEN** the preview shows the model, the console has no `[kintsugi] 3MF preview failed` warning, and the geometry matches the STL export of the same model
- **Modifier volume:**
  - **WHEN** a slicer export with a modifier or negative volume added is dropped in
  - **THEN** it is rejected with the modifier/negative-volume message
- **Own output round trip:**
  - **WHEN** `kintsugi_assembly.3mf` downloaded from a fracture is dropped back in
  - **THEN** the status bar says it is already a Kintsugi output
- **Upload zone copy:**
  - **WHEN** the app loads locally and on the preview
  - **THEN** the subtitle reads `.stl, .obj or .3mf · watertight only · up to 50.0 MB` locally and `… up to 4.0 MB` on Vercel
