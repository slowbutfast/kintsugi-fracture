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

// fflate's inflateSync(data) -> Uint8Array, backed by Node's zlib.
const inflateSync = (data) => new Uint8Array(inflateRawSync(data));

const job = JSON.parse(readFileSync(process.argv[2], "utf-8"));
const result = { threemf: [], upload: [], subtitle: [] };

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

process.stdout.write(JSON.stringify(result));
