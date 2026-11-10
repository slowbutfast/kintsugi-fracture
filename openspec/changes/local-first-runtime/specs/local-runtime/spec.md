# local-runtime Specification

## Purpose
Define the native local launcher, port negotiation, pure ASGI security, and health reporting for Kintsugi Studio 2001.

## ADDED Requirements

### Requirement: Native local launcher entrypoint
The application SHALL provide a console script entrypoint `kintsugi-studio` (callable via `uv run kintsugi-studio` or `pip install -e . && kintsugi-studio`) that starts the FastAPI server on loopback (`127.0.0.1`) and opens the default browser.

#### Scenario: Successful local launch
- **WHEN** user executes `kintsugi-studio`
- **THEN** system binds to `127.0.0.1:8000`, waits for `/api/health` to respond, opens `http://127.0.0.1:8000` in the user's default browser, and starts serving requests

#### Scenario: Headless launch with no browser open
- **WHEN** user executes `kintsugi-studio --no-open`
- **THEN** system starts the server on loopback without launching a web browser window

#### Scenario: Non-loopback host warning
- **WHEN** user executes `kintsugi-studio --host 0.0.0.0`
- **THEN** system logs a security warning explaining that unauthenticated endpoints are being exposed to the local network

### Requirement: Deterministic port negotiation and instance reuse
The launcher SHALL probe port 8000 before starting a new server. If port 8000 is already serving Kintsugi Studio, it SHALL reuse that instance. If port 8000 is bound by another service, it SHALL probe ports 8001 through 8009 sequentially.

#### Scenario: Existing Kintsugi Studio instance detected
- **WHEN** user executes `kintsugi-studio` and `GET http://127.0.0.1:8000/api/health` returns `service: "kintsugi-studio"`
- **THEN** system logs that an instance is already running at port 8000, opens the browser to `http://127.0.0.1:8000` (unless `--no-open`), and exits with code 0 without spawning a second server

#### Scenario: Port collision fallback
- **WHEN** port 8000 is occupied by an unrelated non-Kintsugi process
- **THEN** system tests sequential ports `8001` through `8009`, binds the first available port, logs the bound URL, and opens the browser to that URL

### Requirement: Pure ASGI server-side origin and host security
The local server SHALL enforce cross-origin security and DNS rebinding protections via a pure ASGI middleware without using `BaseHTTPMiddleware`. It SHALL restrict access to loopback origins and the production Vercel domain `https://kintsugi-fracture-joeshmo.vercel.app`. Vercel preview domains matching `^https://kintsugi-fracture-[a-zA-Z0-9_-]+-joeshmo\.vercel\.app$` SHALL be trusted only after an explicit operator opt-in (`KINTSUGI_ALLOW_PREVIEWS=1` or `kintsugi-studio --allow-previews`), because `*.vercel.app` names are first-come-first-served and a squatted name could otherwise reach the local engine.

#### Scenario: Allowed origin preflight
- **WHEN** a client at `https://kintsugi-fracture-joeshmo.vercel.app` sends an `OPTIONS` request
- **THEN** system responds with HTTP 204, `Access-Control-Allow-Origin: https://kintsugi-fracture-joeshmo.vercel.app`, `Access-Control-Allow-Methods: GET, POST, OPTIONS`, and a `Vary: Origin` header

#### Scenario: Preview origins require opt-in
- **WHEN** a client at `https://kintsugi-fracture-x-joeshmo.vercel.app` sends an `OPTIONS` request without `KINTSUGI_ALLOW_PREVIEWS=1`
- **THEN** system responds with HTTP 403 and no CORS allow headers
- **AND WHEN** the operator starts the engine with `--allow-previews` and the same request is repeated
- **THEN** system responds with HTTP 204 and the matching `Access-Control-Allow-Origin` header

#### Scenario: Unauthorized preflight rejected
- **WHEN** an untrusted origin (e.g. `https://evil.example`) sends an `OPTIONS` preflight request
- **THEN** system responds with HTTP 403 and returns no CORS allow headers

#### Scenario: Unauthorized simple POST rejected before body read
- **WHEN** an untrusted origin (e.g. `https://evil.example`) sends a simple `POST /api/fracture` request
- **THEN** system responds with HTTP 403 Forbidden without consuming or saving the request body or executing fracture logic

#### Scenario: DNS rebinding rejected via Host header verification
- **WHEN** an incoming HTTP request has an untrusted `Host` header (not `127.0.0.1:<port>`, `localhost:<port>`, or `[::1]:<port>`)
- **THEN** system rejects the request with HTTP 403 Forbidden

#### Scenario: No credential exposure
- **WHEN** any cross-origin request is received
- **THEN** system never returns `Access-Control-Allow-Credentials: true`

### Requirement: Guard timing instrumentation
The procedural fracture engine SHALL measure elapsed execution time for the F1 export and repair audit in `generate_kintsugi_mesh`.

#### Scenario: Guard timing recorded
- **WHEN** a fracture job completes successfully
- **THEN** the returned `timings` dictionary contains a `"guard"` float representing elapsed seconds spent in STL export and manifold edge audits
