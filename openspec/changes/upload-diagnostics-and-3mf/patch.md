# Patch Log — `upload-diagnostics-and-3mf`

### [PATCH-01] Bound 3MF zip reads, and report damaged packages as invalid models
- **Date**: 2026-11-09
- **Feedback Source**: Code review of PR #11 (REQUEST CHANGES: two Important findings, four nits).
- **Reported Issue**:
  1. **Important — the size cap trusts the zip's own headers (`mesh_formats.py`, `_Package.read`, `_reject_slicer_modifiers`, `load_3mf`).** `load_3mf` summed the declared `file_size` of every entry and then called `archive.read(name)`, which inflates the whole stream before any check. A 203,996-byte file that declares a 1,000-byte part but really expands to 200 MiB inflated all of it (reviewer measured a 437 MiB peak) before raising. On the public deployment an upload under the 4 MiB limit could ask for gigabytes.
  2. **Important — a corrupt package became HTTP 500.** Only `zipfile.ZipFile(path)` was wrapped. Errors raised later, while reading an entry, escaped as `zipfile.BadZipFile` (bad CRC) or `zlib.error` (damaged deflate stream), and `/api/validate` only catches `ValueError`. This broke the "Malformed package rejected" scenario.
  3. **Nits**, none fixed here (see Deferred): ZIP64 is rejected by the preview but accepted by the server; part-name lookups are case-sensitive; each XML part is parsed whole; the slicer modifier markers are from memory.
- **Root Cause**: the reader treated attacker-controlled zip metadata as a size limit, used the unbounded `archive.read`, and let the zip layer's exception types escape instead of converting them at the untrusted-input boundary.
- **Target Files**: `mesh_formats.py`, `tests/test_mesh_formats.py`, `tests/test_web_api.py`, `openspec/changes/upload-diagnostics-and-3mf/` (`specs/mesh-fracture-engine/spec.md`, `architecture.md`, `tests.md`, `tasks.md`, `verification.md`).
- **Expected Resolution**:
  - A package that understates an entry's size is rejected as corrupt, with peak memory that does not grow by the real size.
  - Every damaged-entry failure (bad CRC, corrupt stream, unsupported compression, encrypted entry) is a `ValueError`, and the API answers `valid: false`.
  - An honestly oversized package is still rejected as too large, and everything that loaded before still loads.
- **Status**: RESOLVED (2026-11-09)
- **Resolution**:
  - Tests first (5 red, all for the right reason: the old reader leaked `zipfile.BadZipFile` after a full inflate and a raw `zlib.error`): understated header with a traced-memory bound, honestly oversized part, corrupt deflate stream, wrong CRC, unsupported compression method (plus an oversized vendor config that must stay non-fatal, and an HTTP test that a corrupted 3MF is `valid: false`, not 500).
  - `_Package._read_bounded` reads through `archive.open(name)` with `read(cap + 1)`, where `cap` is the smaller of the entry's declared size and the remaining 512 MiB package budget. It converts `BadZipFile`, `zlib.error`, `lzma.LZMAError`, `EOFError`, `NotImplementedError`, `RuntimeError` and `OSError` to `ValueError("3MF part '<name>' is corrupt or uses an unsupported zip feature: …")`. `read` and `read_optional` (vendor configs, skipped when over `MAX_CONFIG_BYTES`) go through it; the declared-size sum stays as a cheap early reject.
  - **Measured, fresh process per reader**, file of 200 KB declaring 1,000 bytes and really expanding to 200 MiB: the committed reader added **+400 MiB** and raised a raw `zipfile.BadZipFile`; the fixed reader adds **+0 MiB** and raises `ValueError`.
  - **A correction to the first fix attempt:** bounding the read by the 512 MiB budget alone would not have reduced that peak, because 200 MiB is under the budget. The bound that matters is the declared size. While testing, I also found that `zipfile` already truncates at the declared size, which turns an understated header into a fast CRC failure. A separate "declared size" error branch I had written could never run, so I removed it instead of keeping an unreachable message.
- **Deferred** (not part of this patch):
  - ZIP64 in the preview: the server accepts it and the preview refuses it, and the preview degrades gracefully. Added to the manual slicer-export check in `tests.md` instead.
  - Case-insensitive part names, and a per-part cap or `iterparse` for XML memory. The latter is recorded as a known gap in `architecture.md`.
  - The modifier-marker formats stay unverified until real slicer exports are checked (task 5.2).
