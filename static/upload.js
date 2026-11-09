// Upload limits and pre-flight checks.  Pure functions (no DOM, no three.js) so
// they can be unit-tested under Node: tests/test_viewer_js.py.
//
// The server advertises its limits through GET /api/health.  Vercel rejects
// request bodies over 4.5 MB itself, before the app runs, so a file over the
// limit has to be refused here -- the server can no longer explain it.

export const DEFAULT_LIMITS = Object.freeze({
  maxUploadBytes: 50 * 1024 * 1024,
  acceptedFormats: Object.freeze([".stl", ".obj", ".3mf"]),
  known: false, // true once /api/health answered
});

const MIB = 1024 * 1024;

export function formatMegabytes(bytes) {
  return `${(bytes / MIB).toFixed(1)} MB`;
}

// ".stl, .obj or .3mf"
export function listFormats(formats) {
  if (formats.length <= 1) return formats.join("");
  return `${formats.slice(0, -1).join(", ")} or ${formats[formats.length - 1]}`;
}

// Accept a /api/health body, falling back per field to the defaults.
export function limitsFromHealth(body) {
  const bytes = body && Number(body.max_upload_bytes);
  const formats = body && body.accepted_formats;
  const validFormats =
    Array.isArray(formats) &&
    formats.length > 0 &&
    formats.every((item) => typeof item === "string" && item.startsWith("."));
  return {
    maxUploadBytes:
      Number.isFinite(bytes) && bytes > 0 ? bytes : DEFAULT_LIMITS.maxUploadBytes,
    acceptedFormats: validFormats
      ? formats.map((item) => item.toLowerCase())
      : [...DEFAULT_LIMITS.acceptedFormats],
    known: Boolean(body && Number.isFinite(bytes) && bytes > 0),
  };
}

export function fileSuffix(name) {
  const dot = name.lastIndexOf(".");
  return dot < 0 ? "" : name.slice(dot).toLowerCase();
}

// Returns a refusal message, or null when the file may be uploaded.
export function checkUploadAllowed(file, limits) {
  if (!limits.acceptedFormats.includes(fileSuffix(file.name))) {
    return `${file.name}: unsupported format. Use ${listFormats(limits.acceptedFormats)}.`;
  }
  if (file.size > limits.maxUploadBytes) {
    return (
      `${file.name} is ${formatMegabytes(file.size)}; this deployment accepts up to ` +
      `${formatMegabytes(limits.maxUploadBytes)}. Run locally for larger files, ` +
      "or export as binary STL or 3MF."
    );
  }
  return null;
}

// Upload zone subtitle; the size phrase only appears once the limit is known.
export function uploadSubtitle(limits) {
  const base = `${listFormats(limits.acceptedFormats)} · watertight only`;
  return limits.known ? `${base} · up to ${formatMegabytes(limits.maxUploadBytes)}` : base;
}
