// Companion-engine helpers shared by the viewer and the Node test runner.
// This module deliberately has no DOM or three.js dependencies so it can be
// imported by Node during tests.

export const ENGINE_PORT_START = 8000;
export const ENGINE_PORT_END = 8009;
export const ENGINE_PORTS = Object.freeze(
  Array.from(
    { length: ENGINE_PORT_END - ENGINE_PORT_START + 1 },
    (_, index) => ENGINE_PORT_START + index
  )
);
export const EXPECTED_API_VERSION = "1.0";

/** Trim trailing slashes so URL joins never produce a double slash. */
export function normalizeEngineBase(baseUrl = "") {
  return String(baseUrl || "").trim().replace(/\/+$/, "");
}

/** Qualify a relative API or asset path against the connected engine. */
export function resolveEngineUrl(path, baseUrl = "") {
  const value = String(path ?? "");
  if (!value) return value;
  // Absolute URLs and protocol-relative URLs are already fully qualified.
  if (/^(?:[a-z][a-z0-9+.-]*:)?\/\//i.test(value)) return value;
  const base = normalizeEngineBase(baseUrl);
  const suffix = value.startsWith("/") ? value : `/${value}`;
  return base ? `${base}${suffix}` : suffix;
}

/** Convert a manual port input into the deterministic probe list. */
export function enginePortsFor(manualPort) {
  if (manualPort === undefined || manualPort === null || manualPort === "") {
    return [...ENGINE_PORTS];
  }
  const port = Number(manualPort);
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    return [...ENGINE_PORTS];
  }
  return [port];
}

export function isLoopbackHostname(hostname = "") {
  const value = String(hostname).toLowerCase().replace(/^\[|\]$/g, "");
  return value === "127.0.0.1" || value === "localhost" || value === "::1";
}

/** True when an absolute URL targets an HTTP loopback endpoint. */
export function isLoopbackHttpUrl(url, baseUrl) {
  try {
    // Relative URLs are same-origin (hosted or local) and never need LNA here.
    const parsed = baseUrl ? new URL(String(url), baseUrl) : new URL(String(url));
    return parsed.protocol === "http:" && isLoopbackHostname(parsed.hostname);
  } catch {
    return false;
  }
}

/**
 * Declare `targetAddressSpace: "loopback"` for local engine requests.
 *
 * Chrome's Local Network Access (LNA) guidance requires this for HTTPS pages
 * that call `http://127.0.0.1`; it exempts the request from mixed-content
 * blocking before DNS resolution.  Browsers without LNA support ignore the
 * unknown RequestInit member and keep the existing CORS/fallback behavior.
 */
export function withLoopbackAddressSpace(url, options = {}) {
  if (!isLoopbackHttpUrl(url)) return { ...options };
  return { ...options, targetAddressSpace: "loopback" };
}

/**
 * Query Chrome's granular loopback permission without crashing older renderers.
 * Unsupported or unknown permission names fall back to "prompt"; the explicit
 * Connect Engine click still triggers the browser prompt where LNA exists.
 */
export async function queryLoopbackPermission(
  permissionsLike = globalThis.navigator?.permissions
) {
  if (!permissionsLike || typeof permissionsLike.query !== "function") {
    return "prompt";
  }
  try {
    const status = await permissionsLike.query({ name: "loopback-network" });
    return status?.state || "prompt";
  } catch {
    return "prompt";
  }
}

/** True when the GUI itself was opened from the local engine (same-origin). */
export function isSameOriginLocalLocation(locationLike) {
  if (!locationLike) return false;
  return isLoopbackHostname(locationLike.hostname || "");
}

function majorVersion(version) {
  if (version === undefined || version === null) return null;
  const match = String(version).trim().match(/^(\d+)/);
  return match ? Number(match[1]) : null;
}

/** Major-version compatibility: 1.x is compatible with a 1.x GUI. */
export function apiVersionCompatible(version, expected = EXPECTED_API_VERSION) {
  const actualMajor = majorVersion(version);
  const expectedMajor = majorVersion(expected);
  return (
    actualMajor !== null && expectedMajor !== null && actualMajor === expectedMajor
  );
}

/** Normalise `/api/presets` or the static manifest into viewer preset rows. */
export function presetsFromStaticIndex(index, baseUrl = "") {
  const list = Array.isArray(index)
    ? index
    : index && Array.isArray(index.presets)
      ? index.presets
      : [];
  return list
    .filter((preset) => preset && preset.id)
    .map((preset) => ({
      ...preset,
      mesh_url: resolveEngineUrl(
        preset.mesh_url || `/presets/${preset.filename || `${preset.id}.stl`}`,
        baseUrl
      ),
    }));
}

async function fetchWithTimeout(fetchImpl, url, timeoutMs) {
  const options = withLoopbackAddressSpace(url, {
    method: "GET",
    mode: "cors",
    cache: "no-store",
  });
  if (typeof AbortController === "undefined" || !timeoutMs) {
    return fetchImpl(url, options);
  }
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetchImpl(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Probe 127.0.0.1:8000-8009 in order and return the first Kintsugi Studio
 * health response.  Called only from an explicit "Connect Engine" gesture so
 * browser Local Network Access permission prompts are user-initiated.
 */
export async function probeEngine({
  fetchImpl = globalThis.fetch,
  ports = ENGINE_PORTS,
  host = "127.0.0.1",
  timeoutMs = 1500,
} = {}) {
  if (typeof fetchImpl !== "function") {
    throw new Error("fetch is unavailable in this browser");
  }
  const candidates = Array.from(ports);
  const attempts = [];
  let lastError = null;

  for (const candidate of candidates) {
    const port = Number(candidate);
    if (!Number.isInteger(port) || port < 1 || port > 65535) continue;
    attempts.push(port);
    const baseUrl = `http://${host}:${port}`;
    try {
      const response = await fetchWithTimeout(
        fetchImpl,
        `${baseUrl}/api/health`,
        timeoutMs
      );
      if (!response || !response.ok) {
        lastError = new Error(
          `HTTP ${response ? response.status : "no response"} on port ${port}`
        );
        continue;
      }
      const health = await response.json();
      if (!health || health.service !== "kintsugi-studio") {
        lastError = new Error(`port ${port} is not Kintsugi Studio`);
        continue;
      }
      return {
        baseUrl,
        port,
        health,
        apiVersion: health.api_version ?? null,
        compatible: apiVersionCompatible(health.api_version),
        attempts,
      };
    } catch (error) {
      lastError = error;
    }
  }

  const range = candidates.length
    ? `${Math.min(...candidates)}-${Math.max(...candidates)}`
    : `${ENGINE_PORT_START}-${ENGINE_PORT_END}`;
  const detail = lastError ? ` (${lastError.message})` : "";
  throw new Error(`No Kintsugi Studio engine found on ports ${range}${detail}`);
}
