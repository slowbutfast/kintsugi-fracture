## MODIFIED Requirements

### Requirement: Model preset selection and custom upload
The web GUI SHALL allow selecting bundled preset 3D models or uploading a custom watertight `.stl`, `.obj` or `.3mf` file. Input models must conform to the ceramic vessel envelope ($p_5 \ge 1.6\text{ mm}$ along inward surface normals across the wall range). The `thin_cylinder` model SHALL NOT be offered in user presets.

The deployment SHALL have one upload limit in bytes:
- `KINTSUGI_MAX_UPLOAD_BYTES` when that environment variable is set;
- otherwise 4,194,304 bytes (4 MiB) when the `VERCEL` environment variable is set;
- otherwise 52,428,800 bytes (50 MiB).

`GET /api/health` SHALL report the limit as `max_upload_bytes`, and the accepted suffixes as `accepted_formats` (`[".stl", ".obj", ".3mf"]`). The server SHALL enforce the same limit while streaming the upload. The viewer SHALL read the limit on startup and SHALL refuse a file over it before sending any request.

#### Scenario: Preset model selection
- **WHEN** user chooses a preset model (e.g. `Japanese Tea Bowl` or `Tall Vase`) from the dropdown
- **THEN** system immediately loads and renders the model in the 3D viewport and updates the status bar with mesh metadata

#### Scenario: Custom file upload
- **WHEN** user drags and drops a custom `.stl`, `.obj` or `.3mf` file within the upload limit onto the upload zone
- **THEN** the viewer parses it for preview and calls `POST /api/validate`, which runs `validate_and_load_mesh` in a temporary directory; the status bar reports `Watertight ✓` or `Not a valid closed solid: <detail>` (including wall thickness rejection if $p_5 < 1.6\text{ mm}$, and 3MF structure rejections), and the fracture button stays disabled while the upload is invalid

#### Scenario: Custom 3MF upload preview
- **WHEN** user drops a `.3mf` file containing one build item, whose geometry is split across a component transform and a Production-extension `p:path` part
- **THEN** the viewer previews the same flattened geometry the server validates (transforms applied, parts resolved by path and id, not by bare id), and the status bar reports the server's validation result

#### Scenario: Upload over the limit refused in the browser
- **WHEN** user selects a file larger than the `max_upload_bytes` reported by `GET /api/health`
- **THEN** the viewer sends no request, keeps the fracture button disabled, and the status bar names the file size and the limit in megabytes and suggests running locally or exporting a smaller file (e.g. binary STL or 3MF)

#### Scenario: Upload size cap enforced by the server
- **WHEN** an upload that reaches the app exceeds the upload limit
- **THEN** the API rejects it with HTTP 413 and an app error envelope whose `detail` states the limit, and stores no file

#### Scenario: Unsupported suffix
- **WHEN** a file whose suffix is not `.stl`, `.obj` or `.3mf` is uploaded
- **THEN** the viewer refuses it before upload, and the API, if called directly, returns HTTP 400 with `detail` listing the accepted formats

#### Scenario: Job retention
- **WHEN** a new fracture job starts
- **THEN** job directories older than `KINTSUGI_JOB_TTL_S` (default 3600 s) are deleted, and at most `KINTSUGI_MAX_JOBS` (default 50) directories are retained, oldest first

## ADDED Requirements

### Requirement: Request diagnostics and structured error responses
The web app SHALL assign every HTTP request a request id of 12 lowercase hexadecimal characters. It SHALL return the id in an `X-Kintsugi-Request-Id` response header and SHALL include it in every server log line for that request. For each `/api/*` request, the server SHALL log:
- one line on arrival: method, path, content type and content length;
- one line on completion: status and elapsed milliseconds.

`POST /api/validate` and `POST /api/fracture` SHALL also log the uploaded file name, MIME type and bytes received. A rejection SHALL log its reason; an unexpected exception SHALL log its full traceback.

Every error response produced by the app SHALL be JSON with `detail`, `error_type`, `status`, `path` and `request_id`. That covers HTTP errors, request-validation errors and unhandled exceptions. Request-validation error details SHALL NOT echo raw upload bytes.

The viewer SHALL send every API call through one request helper. The helper SHALL:
- read the response body as text before parsing it as JSON;
- log each request and response to the browser console, prefixed `[kintsugi]`. The log SHALL include the request label, URL, form field summary (file name, size, MIME type), status, elapsed time, the headers `content-type`, `content-length`, `x-kintsugi-request-id`, `x-vercel-id`, `x-vercel-error` and `x-vercel-cache`, and up to 2,000 characters of the body;
- raise an error that names the status, content type and the start of the body when the body is not JSON;
- raise an error that names the status, `detail`, `error_type` and request id when an app error arrives;
- report a request that receives no response as a network failure, not a parse error.

#### Scenario: App error returns a JSON envelope with a request id
- **WHEN** `POST /api/fracture` is called with an unknown preset id
- **THEN** the response is HTTP 400 JSON with `detail`, `error_type`, `status: 400`, `path: "/api/fracture"` and a `request_id` equal to the `X-Kintsugi-Request-Id` header

#### Scenario: Unhandled exception returns JSON, not plain text
- **WHEN** an API handler raises an exception other than `ValueError` or `HTTPException`
- **THEN** the response is HTTP 500 JSON whose `error_type` is the exception class name, and the server log contains that request id and the traceback

#### Scenario: Request-validation error does not echo upload bytes
- **WHEN** `POST /api/validate` is called without a `file` field
- **THEN** the response is HTTP 422 JSON in the app error envelope whose `detail` lists the missing field, and contains no raw request body

#### Scenario: Platform error reported by name in the browser
- **WHEN** an API call returns a non-JSON body (e.g. HTTP 413, `text/plain`, body `Request Entity Too Large … FUNCTION_PAYLOAD_TOO_LARGE`, no `X-Kintsugi-Request-Id`)
- **THEN** the console logs the status, headers and body preview under `[kintsugi] ✗ <label>`, and the status bar shows `<label>: server returned non-JSON (HTTP 413 …)` with the start of the body, not a JSON parser message

#### Scenario: Successful call logged
- **WHEN** an API call succeeds
- **THEN** the console logs `[kintsugi] ✓ <label>: HTTP <status> in <ms> ms` with the request id header
