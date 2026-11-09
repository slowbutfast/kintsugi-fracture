# Verification — upload-diagnostics-and-3mf

## Executive Summary & Environment

- **Status**: automated checks PASS; manual checks that need a browser, a Vercel preview or slicer exports are **NOT done** (listed under "Not verified"). The owner's sign-off covers those.
- **Date verified**: 2026-11-09
- **Environment**: Linux 5.15.0-1081-oracle aarch64 container, Python 3.11, Node v22.23.2, shared project virtualenv (`.venv`); trimesh 5.2.0, numpy, manifold3d, fastapi.
- **Base**: `origin/main` at `aeeb872` (PR #9 merged), plus PR #10's commit `e055b34` cherry-picked as task 1.1.
- **Full regression suite**: 146 tests, OK, 0 skipped (`Ran 146 tests in 260.233s`).
- **Re-run after the last edits** (logging sanitiser, viewer zip handling, fixture compression option, which landed after the full run started): `tests.test_mesh_formats tests.test_viewer_js tests.test_web_api`, 76 tests, OK (`Ran 76 tests in 15.298s`).
- **Generator regression**: `tests.test_crack_hybrid.test_growth_and_shard_baseline_digests_unchanged` passes in the full run, so growth and shard output is unchanged.
- **Dependencies**: none added. The reader needs neither `networkx` nor `lxml` (checked below).

### How the tests were written

Tests were written first and run red. `tests.test_mesh_formats` failed 30/30 (module missing). Of the 17 new API tests, 7 failed and 10 passed before any server change: the 10 describe behaviour PR #10 already implemented (request id, error envelope, logging), so for those the tests pin existing behaviour rather than drive new code. The 7 that failed covered the upload limit, `.3mf` and the suffix message.

## Requirement Adherence Audit Matrix

### `retro-web-gui`

| Requirement / Scenario | Verifying test(s) | Status |
| :--- | :--- | :--- |
| Upload requirement: limit resolution order (env override, 4 MiB on Vercel, else 50 MiB) | `test_upload_limit_resolution_order` | **PASS** |
| `/api/health` reports `max_upload_bytes` and `accepted_formats` | `test_health_reports_limit_and_formats`; live HTTP check | **PASS** |
| Scenario: Custom file upload (`.3mf`) | `test_validate_accepts_a_3mf_vessel`; live HTTP check (p5 3.005 mm) | **PASS** |
| Scenario: Custom 3MF upload preview | `tests.test_viewer_js` preview parity (Node, same fixtures as the server reader, including a `p:path` part with a colliding id and nested transforms) | **PASS (Node only)**, browser check pending |
| Scenario: Upload over the limit refused in the browser | `tests.test_viewer_js` upload pre-flight (`checkUploadAllowed`: within, exactly at, one byte over, upper-case suffix, missing/malformed health); `handleCustomFile` returns before any `fetch` | **PASS (logic)**, no-request behaviour pending in a browser |
| Scenario: Upload size cap enforced by the server | `test_oversized_upload_returns_413_envelope`, `test_reported_and_enforced_limit_follow_the_constant`; live check (413 JSON, `Upload exceeds the 293.0 KB limit for this deployment`) | **PASS** |
| Scenario: Unsupported suffix | `test_unsupported_suffix_lists_the_accepted_formats` (validate and fracture); `tests.test_viewer_js` (`model.ply: unsupported format. Use .stl, .obj or .3mf.`) | **PASS** |
| Scenario: Preset model selection, Job retention (unchanged) | existing `test_api_presets`, `test_job_retention` | **PASS** |
| Request diagnostics: request id on every response, unique per request | `test_every_response_carries_a_request_id`, `test_request_ids_are_unique_per_request` | **PASS** |
| Scenario: App error returns a JSON envelope | `test_unknown_preset_returns_envelope`, `test_unknown_path_returns_envelope`, `test_oversized_upload_returns_413_envelope` | **PASS** |
| Scenario: Unhandled exception returns JSON, not plain text | `test_unhandled_exception_returns_json_500_and_logs_traceback` | **PASS** |
| Scenario: Request-validation error does not echo upload bytes | `test_request_validation_error_does_not_echo_upload_bytes`; live check (marker not echoed) | **PASS** |
| Server log lines (arrival, completion, upload, rejection reason, traceback) | `test_validate_logs_arrival_upload_and_completion`, `test_rejected_validation_logs_the_reason`; live server log | **PASS** |
| Scenario: Platform error reported by name in the browser | `requestJson` from PR #10; the owner's console output on the PR #10 preview showed the real Vercel 413 reported this way. No automated test | **PASS (observed once)**, not automated |
| Scenario: Successful call logged in the console | none (needs a browser) | **NOT VERIFIED** |
| UI copy (upload zone `aria-label`, subtitle, `accept`, help line); viewer modules served | `test_ui_advertises_3mf_and_serves_the_viewer_modules`; subtitle text in `tests.test_viewer_js` | **PASS (markup and logic)** |

### `mesh-fracture-engine` — 3MF package input

| Scenario | Verifying test(s) | Status |
| :--- | :--- | :--- |
| Single-object core 3MF loads in millimetres | `test_single_object_millimetre_load_matches_source`, `test_missing_unit_attribute_defaults_to_millimetre`, `test_validate_and_load_mesh_accepts_3mf_like_the_stl` | **PASS** |
| Metre unit and transforms are applied | `test_metre_unit_and_composed_transforms`, `test_every_unit_maps_to_its_millimetre_factor`, `test_mirrored_transform_keeps_outward_winding`, `test_metre_3mf_validates_where_the_metre_stl_is_rejected` | **PASS** |
| Production-extension part resolved by path | `test_production_path_resolves_by_path_not_bare_id`, `test_production_path_to_missing_part_rejected`, `test_production_path_with_parent_segments_rejected` | **PASS** |
| Multiple build items rejected | `test_two_build_items_rejected`, `test_zero_build_items_rejected` | **PASS** |
| Non-model object type rejected | `test_non_model_object_type_rejected`, `test_unreachable_non_model_object_is_ignored` | **PASS** |
| Kintsugi assembly rejected | `test_kintsugi_assembly_rejected` (a real fracture's `export_kintsugi_3mf` output); CLI check | **PASS** |
| Malformed package rejected (not a ZIP, no root model, missing object, unknown unit, cycle, depth, DOCTYPE, empty mesh, bad triangle index) | `test_not_a_zip_rejected`, `test_missing_root_model_rejected`, `test_missing_object_id_rejected`, `test_unknown_unit_rejected`, `test_component_cycle_rejected`, `test_component_nesting_depth_limit`, `test_doctype_rejected_before_parsing`, `test_empty_mesh_rejected`, `test_out_of_range_triangle_index_rejected` | **PASS** |
| Reader discovery and fallbacks (`.rels` target, default part) | `test_root_model_found_through_relationship`, `test_package_without_rels_falls_back_to_default_part` | **PASS** |
| Size caps; no-repair contract; stdlib only | `test_size_caps_are_enforced`, `test_object_reused_by_two_components_keeps_both_copies`, `test_reader_uses_only_the_standard_library_for_3mf` | **PASS** |
| Slicer modifier / negative volumes rejected (architecture risk mitigation, beyond the delta spec) | `test_vendor_config_modifier_volumes_rejected`, `test_vendor_config_with_only_model_parts_is_accepted`. The config formats used are **from memory, not from real slicer exports** | **PASS (synthetic only)** |

## Resolved Assumptions & Empirical Proof

| Assumption / question | How it was checked | Result |
| :--- | :--- | :--- |
| trimesh's 3MF loader would not work on Vercel | Blocked `networkx` and `lxml` via `sys.modules` and ran `validate_and_load_mesh` on a 3MF, then `trimesh.load` on the same file | Our reader validated it (extents 90 × 90 × 60); trimesh raised `ModuleNotFoundError`. Confirmed |
| three r160's bundled fflate can filter entries (plan: `unzipSync` with `filter`) | Fetched `fflate.module.js` from unpkg | **Wrong.** It is fflate 0.6.9 and `unzipSync(data)` takes no options. The viewer reader was redesigned (own zip-directory scan, injected `inflateSync`); architecture.md and research.md were updated |
| A 3MF is smaller than the binary STL | `os.stat` on the fixture bowl | 8,102 bytes vs 38,484 bytes (21%) |
| STL and 3MF routes agree | `test_validate_and_load_mesh_accepts_3mf_like_the_stl` | Same face count and extents; p5 equal within 1e-4 mm (the STL is float32) |
| Viewer and server readers agree | `tests/test_viewer_js.py`, 9 accepted and 15 rejected fixtures | Same geometry (1e-3 mm) and same rejection reasons |
| The parity test can fail | Mutation runs: (1) unit factor ignored, (2) transform order swapped | (1) failed 2 subtests (`inch_unit`, `metre_transforms`); (2) failed `metre_transforms`. Both restored, file verified identical to the original |
| The real server behaves over HTTP | Started `web_app.py` with `KINTSUGI_MAX_UPLOAD_BYTES=300000` and called it | health, 3MF validate (200, valid), oversize (413 JSON), bad suffix (400), 404 JSON, 422 without echoing bytes, 3MF fracture (200, 7 cracks); request ids matched the server log lines |
| The CLI accepts 3MF | Ran `kintsugi.py bowl.3mf -R 0.5 --3mf`, then fed the assembly back in | Exit 0 with three outputs; re-feeding the assembly exits 1 with the "already a Kintsugi output" message |

## Not verified (needs the owner or a real environment)

These are open assumptions from research.md. Nothing here has been confirmed.

| Item | Why it is open |
| :--- | :--- |
| Exact Vercel body limit (4,400,000 vs 4,600,000 bytes) | Needs two uploads to a preview deployment. The 4 MiB hosted default is chosen to be safe under either reading |
| `VERCEL=1` default end to end | Only the resolver function is tested. The deployed value and upload-zone subtitle were not seen |
| What PrusaSlicer, Bambu Studio and OrcaSlicer actually write (core vs `p:path`, `Metadata/*.config` markers for modifier volumes) | No slicer exports were available. The reader follows the 3MF spec and the architecture's assumptions; the modifier/negative-volume check uses markers recalled from memory and is only tested with synthetic configs. Real exports might trip it or slip past it |
| Browser behaviour: `fflate.inflateSync` on real bytes, the 3MF preview, the `[kintsugi] ✓` console line, status-bar copy and `title` hover, refusal with no request sent | No browser was available. The viewer reader was tested under Node with `zlib` in place of fflate |
| Closing PR #10 (task 5.4) | Done after the owner confirms this PR |

## Nomenclature & Code Symbol Audit

| Glossary term | Code symbol | Location |
| :--- | :--- | :--- |
| Request id | `RequestContextMiddleware`, `X-Kintsugi-Request-Id`, `_request_id` | `web_app.py` |
| App error (envelope) | `_error_payload` and the three exception handlers | `web_app.py` |
| Upload limit | `_upload_limit`, `MAX_UPLOAD_BYTES`, `HOSTED_UPLOAD_LIMIT_BYTES`, `limitsFromHealth` | `web_app.py`, `static/upload.js` |
| Flattened mesh | `mesh_formats.load_3mf` | `mesh_formats.py` |
| Production-extension reference | `p:path` handling in `_parse_object` and `walk` | `mesh_formats.py`, `static/threemf.js` |
| Kintsugi assembly | `KINTSUGI_PART_NAMES` | `mesh_formats.py` (and the same check in `static/threemf.js`) |

## Verbatim Execution Logs

```text
$ ./.venv/bin/python -m unittest discover -s tests -v
Ran 146 tests in 260.233s
OK
exit=0
```

```text
$ ./.venv/bin/python -m unittest tests.test_mesh_formats tests.test_viewer_js tests.test_web_api -v
Ran 76 tests in 15.298s
OK
```

Per class in the 76-test run: `MeshFormatsTestCase` 31, `ViewerJsTestCase` 9, `WebApiTestCase` 18, `WebDiagnosticsTestCase` 10, `WebUploadLimitAndFormatsTestCase` 8.

```text
$ python -I nodeps_check.py   # networkx and lxml made unimportable
networkx blocked: ok
validated 3MF without networkx/lxml; extents [90.0, 90.0, 60.0]
trimesh loader fails here: ModuleNotFoundError import of networkx halted; None in sys.modules
```

```text
$ python -I live_check.py   # real server, KINTSUGI_MAX_UPLOAD_BYTES=300000
bowl.3mf bytes: 8102 | limit: 300000
health: 200 {'status': 'ok', 'kernel': 'Manifold3D', 'max_upload_bytes': 300000, 'accepted_formats': ['.stl', '.obj', '.3mf']} | rid: de05c1689df4
validate 3mf: 200 valid= True p5= 3.005 | rid: 717facd5113f
oversize: 413 application/json {'detail': 'Upload exceeds the 293.0 KB limit for this deployment', 'error_type': 'HTTPException', 'status': 413, 'path': '/api/validate', 'request_id': 'da4920af3646'}
bad suffix: 400 Custom models must be one of: .stl, .obj, .3mf
404: 404 application/json HTTPException
422: 422 marker echoed: False
fracture 3mf: 200 cracks= 7 | rid: 77b155b156d0
```

```text
$ python -I cli_check.py
cli exit: 0
outputs: ['ceramic_body.stl', 'gold_seams.stl', 'kintsugi_assembly.3mf']
re-feeding our own assembly: exit 1
ValueError: This file is already a Kintsugi output (CeramicBody + GoldSeams); upload the original model instead
```
