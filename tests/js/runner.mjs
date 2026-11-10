// Node runner for tests/test_viewer_js.py.  Runs the viewer's pure modules
// (static/threemf.js, static/upload.js) on jobs written by the Python test and
// prints one JSON document.  No dependencies: Node's zlib stands in for
// fflate's inflateSync (the module scans the zip directory itself).
import { readFileSync } from "node:fs";
import { inflateRawSync } from "node:zlib";

import { LIMITS, read3mf } from "../../static/threemf.js";
import {
  checkUploadAllowed,
  DEFAULT_LIMITS,
  limitsFromHealth,
  uploadSubtitle,
} from "../../static/upload.js";
import {
  apiVersionCompatible,
  ENGINE_PORTS,
  presetsFromStaticIndex,
  probeEngine,
  queryLoopbackPermission,
  resolveEngineUrl,
  withLoopbackAddressSpace,
} from "../../static/engine.js";

// fflate's inflateSync(data) -> Uint8Array, backed by Node's zlib.
const inflateSync = (data) => new Uint8Array(inflateRawSync(data));

const job = JSON.parse(readFileSync(process.argv[2], "utf-8"));
const result = { threemf: [], upload: [], subtitle: [], engine: {} };

const DEFAULT_THREEMF_LIMITS = { ...LIMITS };
for (const item of job.threemf || []) {
  Object.assign(LIMITS, DEFAULT_THREEMF_LIMITS, item.limits || {});
  try {
    const bytes = new Uint8Array(readFileSync(item.file));
    const parsed = read3mf(bytes, { inflateSync });
    result.threemf.push({
      name: item.name,
      ok: true,
      unit: parsed.unit,
      triangles: parsed.triangleCount,
      positions: Array.from(parsed.positions),
    });
  } catch (error) {
    result.threemf.push({ name: item.name, ok: false, error: String(error.message) });
  }
}

for (const item of job.upload || []) {
  const limits = item.health ? limitsFromHealth(item.health) : DEFAULT_LIMITS;
  result.upload.push({
    name: item.name,
    message: checkUploadAllowed({ name: item.file_name, size: item.size }, limits),
    limits,
  });
}

for (const item of job.subtitle || []) {
  const limits = item.health ? limitsFromHealth(item.health) : DEFAULT_LIMITS;
  result.subtitle.push({ name: item.name, text: uploadSubtitle(limits) });
}

// Engine companion helpers: resolveEngineUrl, static preset manifests, and the
// deterministic 8000-8009 port probe.  Fetch is stubbed with the per-port
// responses supplied by the Python test.
const engineJob = job.engine || {};
result.engine.resolve = [];
for (const item of engineJob.resolve || []) {
  result.engine.resolve.push({
    name: item.name,
    url: resolveEngineUrl(item.path, item.base),
  });
}

result.engine.static_presets = [];
for (const item of engineJob.static_presets || []) {
  const raw = JSON.parse(readFileSync(item.indexFile, "utf-8"));
  const presets = presetsFromStaticIndex(raw, item.base || "");
  result.engine.static_presets.push({
    name: item.name,
    presets,
    ids: presets.map((preset) => preset.id),
    meshUrls: presets.map((preset) => preset.mesh_url),
  });
}

result.engine.probes = [];
for (const item of engineJob.probes || []) {
  let seenOptions = null;
  const fetchImpl = async (url, options) => {
    seenOptions = options;
    const port = new URL(url).port;
    const spec = (item.responses || {})[port];
    if (!spec) throw new TypeError(`fetch failed for port ${port}`);
    return {
      ok: spec.status >= 200 && spec.status < 300,
      status: spec.status,
      json: async () => spec.body,
    };
  };
  try {
    const probe = await probeEngine({ fetchImpl, ports: item.ports || ENGINE_PORTS });
    result.engine.probes.push({
      name: item.name,
      ok: true,
      port: probe.port,
      baseUrl: probe.baseUrl,
      apiVersion: probe.apiVersion,
      compatible: probe.compatible,
      attempts: probe.attempts,
      targetAddressSpace: seenOptions?.targetAddressSpace,
    });
  } catch (error) {
    result.engine.probes.push({
      name: item.name,
      ok: false,
      error: String(error.message || error),
      targetAddressSpace: seenOptions?.targetAddressSpace,
    });
  }
}

result.engine.address_space = [];
for (const item of engineJob.address_space || []) {
  const options = withLoopbackAddressSpace(item.url, { method: "GET" });
  result.engine.address_space.push({
    name: item.name,
    url: item.url,
    targetAddressSpace: options.targetAddressSpace ?? null,
    method: options.method,
  });
}

result.engine.permissions = [];
for (const item of engineJob.permissions || []) {
  let permissionsLike;
  if (item.behavior === "unsupported") {
    permissionsLike = undefined;
  } else {
    permissionsLike = {
      query: async (descriptor) => {
        if (item.behavior === "throws") throw new TypeError("unknown permission");
        return { name: descriptor.name, state: item.state };
      },
    };
  }
  result.engine.permissions.push({
    name: item.name,
    state: await queryLoopbackPermission(permissionsLike),
  });
}

result.engine.versions = [];
for (const item of engineJob.versions || []) {
  result.engine.versions.push({
    name: item.name,
    compatible: apiVersionCompatible(item.version),
  });
}

process.stdout.write(JSON.stringify(result));
