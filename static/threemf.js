// 3MF preview reader for the viewer.  It mirrors the server's rules in
// mesh_formats.py (one build item, transforms composed, Production-extension
// p:path parts, unit -> millimetres, same rejections) so the preview shows the
// geometry the server validates.  three.js's 3MFLoader is not used: it ignores
// units and resolves p:path objects by bare id.
//
// Pure (no DOM, no three.js).  The caller injects inflateSync (fflate's, from
// three/addons/libs/fflate.module.js) so this module can run under Node in
// tests/test_viewer_js.py against the same fixtures as the Python reader.
//
// Returns triangle-soup positions in millimetres.  The server decides validity;
// a preview error is shown but never blocks server validation.

export const UNIT_FACTORS = Object.freeze({
  micron: 0.001,
  millimeter: 1,
  centimeter: 10,
  inch: 25.4,
  foot: 304.8,
  meter: 1000,
});

export const LIMITS = {
  maxUncompressedBytes: 512 * 1024 * 1024,
  maxTriangles: 5_000_000,
  maxDepth: 16,
};

const KINTSUGI_PARTS = ["CeramicBody", "GoldSeams"];
const PLAIN_VOLUME_TYPES = ["", "ModelPart"];
const PLAIN_SUBTYPES = ["", "normal_part"];
const DEFAULT_ROOT = "3D/3dmodel.model";
const decoder = new TextDecoder("utf-8");

// -- XML (attribute-only subset: all 3MF structure lives in attributes) --------
const TOKEN =
  /<!--[\s\S]*?-->|<\?[\s\S]*?\?>|<!\[CDATA\[[\s\S]*?\]\]>|<(\/?)([A-Za-z_][\w:.\-]*)((?:\s+[\w:.\-]+\s*=\s*(?:"[^"]*"|'[^']*'))*)\s*(\/?)>/g;
const ATTRIBUTE = /([\w:.\-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')/g;

function decodeEntities(value) {
  return value
    .replace(/&#x([0-9a-fA-F]+);/g, (_, hex) => String.fromCodePoint(parseInt(hex, 16)))
    .replace(/&#(\d+);/g, (_, dec) => String.fromCodePoint(parseInt(dec, 10)))
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'")
    .replace(/&amp;/g, "&");
}

function localName(name) {
  const colon = name.indexOf(":");
  return colon < 0 ? name : name.slice(colon + 1);
}

function parseXml(bytes, name) {
  if (
    (bytes[0] === 0xff && bytes[1] === 0xfe) ||
    (bytes[0] === 0xfe && bytes[1] === 0xff)
  ) {
    throw new Error(`3MF part '${name}' must be UTF-8 encoded XML`);
  }
  const text = decoder.decode(bytes);
  if (/<!doctype/i.test(text)) {
    throw new Error(
      `3MF part '${name}' contains a DOCTYPE declaration, which is not allowed`
    );
  }
  const root = { name: "#root", attrs: {}, children: [] };
  const stack = [root];
  TOKEN.lastIndex = 0;
  let match;
  while ((match = TOKEN.exec(text)) !== null) {
    const [, closing, tag, attrText, selfClosing] = match;
    if (tag === undefined) continue; // comment, processing instruction, CDATA
    if (closing) {
      const open = stack.pop();
      if (stack.length === 0 || open.raw !== tag) {
        throw new Error(`3MF part '${name}' is not valid XML (unbalanced <${tag}>)`);
      }
      continue;
    }
    const attrs = {};
    ATTRIBUTE.lastIndex = 0;
    let attr;
    while ((attr = ATTRIBUTE.exec(attrText)) !== null) {
      attrs[attr[1]] = decodeEntities(attr[2] !== undefined ? attr[2] : attr[3]);
    }
    const node = { name: localName(tag), raw: tag, attrs, children: [] };
    stack[stack.length - 1].children.push(node);
    if (!selfClosing) stack.push(node);
  }
  if (stack.length !== 1 || root.children.length !== 1) {
    throw new Error(`3MF part '${name}' is not valid XML`);
  }
  return root.children[0];
}

const child = (node, name) => node.children.find((item) => item.name === name) || null;
const children = (node, name) => node.children.filter((item) => item.name === name);

// -- geometry --------------------------------------------------------------------
function normalisePart(target, what) {
  if (!target || target.includes("\\")) {
    throw new Error(`invalid 3MF ${what} path '${target}'`);
  }
  const stripped = target.replace(/^\/+/, "");
  const segments = stripped.split("/");
  if (!stripped || segments.includes("..") || segments.includes("")) {
    throw new Error(
      `3MF ${what} path '${target}' must stay inside the package (no '..' or empty segments)`
    );
  }
  return segments.filter((segment) => segment !== ".").join("/");
}

// 12 values -> 4x4 row-major matrix for row vectors: p' = [x y z 1] * M.
function parseTransform(text, where) {
  const matrix = new Float64Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]);
  if (text === undefined || text.trim() === "") return matrix;
  const values = text.trim().split(/\s+/).map(Number);
  if (values.length !== 12 || !values.every(Number.isFinite)) {
    throw new Error(`3MF transform on ${where} must have 12 finite values, got '${text}'`);
  }
  for (let row = 0; row < 3; row += 1) {
    for (let column = 0; column < 3; column += 1) {
      matrix[row * 4 + column] = values[row * 3 + column];
    }
  }
  matrix[12] = values[9];
  matrix[13] = values[10];
  matrix[14] = values[11];
  return matrix;
}

// a * b with the row-vector convention (apply `a` first, then `b`).
function multiply(a, b) {
  const out = new Float64Array(16);
  for (let row = 0; row < 4; row += 1) {
    for (let column = 0; column < 4; column += 1) {
      let sum = 0;
      for (let k = 0; k < 4; k += 1) sum += a[row * 4 + k] * b[k * 4 + column];
      out[row * 4 + column] = sum;
    }
  }
  return out;
}

function determinant3(m) {
  return (
    m[0] * (m[5] * m[10] - m[6] * m[9]) -
    m[1] * (m[4] * m[10] - m[6] * m[8]) +
    m[2] * (m[4] * m[9] - m[5] * m[8])
  );
}

function parseObject(node, part) {
  const id = node.attrs.id;
  if (id === undefined) throw new Error(`3MF object without an id in '${part}'`);
  const parsed = {
    id,
    type: node.attrs.type || "model",
    name: node.attrs.name || null,
    vertices: null,
    faces: null,
    components: [],
  };
  const mesh = child(node, "mesh");
  if (mesh) {
    const vertexNodes = children(child(mesh, "vertices") || { children: [] }, "vertex");
    const triangleNodes = children(child(mesh, "triangles") || { children: [] }, "triangle");
    if (triangleNodes.length > LIMITS.maxTriangles) {
      throw new Error(
        `3MF object ${id} has too many triangles (${triangleNodes.length} > ${LIMITS.maxTriangles})`
      );
    }
    const vertices = new Float64Array(vertexNodes.length * 3);
    vertexNodes.forEach((vertex, index) => {
      const x = Number(vertex.attrs.x);
      const y = Number(vertex.attrs.y);
      const z = Number(vertex.attrs.z);
      if (![x, y, z].every(Number.isFinite) || vertex.attrs.x === undefined) {
        throw new Error(
          `3MF object ${id} in '${part}' has a vertex with a missing or non-numeric coordinate`
        );
      }
      vertices.set([x, y, z], index * 3);
    });
    const faces = new Int32Array(triangleNodes.length * 3);
    triangleNodes.forEach((triangle, index) => {
      ["v1", "v2", "v3"].forEach((key, slot) => {
        const value = Number(triangle.attrs[key]);
        if (!Number.isInteger(value) || value < 0 || value >= vertexNodes.length) {
          throw new Error(
            `3MF object ${id} has a triangle that references vertex ${triangle.attrs[key]}, ` +
              `but the object only has ${vertexNodes.length} vertices`
          );
        }
        faces[index * 3 + slot] = value;
      });
    });
    parsed.vertices = vertices;
    parsed.faces = faces;
  }
  const components = child(node, "components");
  if (components) {
    for (const component of children(components, "component")) {
      const target = component.attrs.objectid;
      if (target === undefined) {
        throw new Error(`3MF component without an objectid in object ${id}`);
      }
      const pathKey = Object.keys(component.attrs).find(
        (key) => key === "path" || key.endsWith(":path")
      );
      parsed.components.push({
        target,
        path: pathKey ? component.attrs[pathKey] : null,
        transform: parseTransform(
          component.attrs.transform,
          `a component of object ${id}`
        ),
      });
    }
  }
  return parsed;
}

function checkSlicerModifiers(files) {
  for (const [name, bytes] of Object.entries(files)) {
    const lowered = name.toLowerCase();
    if (!lowered.startsWith("metadata/") || !lowered.endsWith(".config")) continue;
    let root;
    try {
      root = parseXml(bytes, name);
    } catch {
      continue; // vendor config is only a hint; never trusted, never fatal
    }
    const visit = (node) => {
      const { subtype, key, value } = node.attrs;
      let flagged = null;
      if (subtype !== undefined && !PLAIN_SUBTYPES.includes(subtype)) flagged = subtype;
      else if (key === "volume_type" && value !== undefined && !PLAIN_VOLUME_TYPES.includes(value)) flagged = value;
      else if (key === "subtype" && value !== undefined && !PLAIN_SUBTYPES.includes(value)) flagged = value;
      if (flagged !== null) {
        throw new Error(
          `3MF contains slicer modifier or negative volumes ('${flagged}' in ${name}); ` +
            "only plain model parts are supported"
        );
      }
      node.children.forEach(visit);
    };
    visit(root);
  }
}

// -- zip ---------------------------------------------------------------------
// fflate 0.6.9 (the version three r160 bundles) has no unzip filter: unzipSync
// inflates every entry, including thumbnails.  So the central directory is read
// here, sizes are checked first, and only the parts we need are inflated, by
// the injected inflateSync (fflate's).  Sizes come from the zip's own headers;
// the server (Python zipfile) is the authority for hostile packages.
const messageOf = (error) => (error instanceof Error ? error.message : String(error));

function listZipEntries(bytes) {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  let eocd = -1;
  for (let i = bytes.length - 22; i >= Math.max(0, bytes.length - 65557); i -= 1) {
    if (view.getUint32(i, true) === 0x06054b50) {
      eocd = i;
      break;
    }
  }
  if (eocd < 0) throw new Error("no zip directory found");
  const count = view.getUint16(eocd + 10, true);
  let offset = view.getUint32(eocd + 16, true);
  const entries = [];
  for (let index = 0; index < count; index += 1) {
    if (offset + 46 > bytes.length || view.getUint32(offset, true) !== 0x02014b50) {
      throw new Error("corrupt zip directory");
    }
    const flags = view.getUint16(offset + 8, true);
    const method = view.getUint16(offset + 10, true);
    const compressedSize = view.getUint32(offset + 20, true);
    const originalSize = view.getUint32(offset + 24, true);
    const nameLength = view.getUint16(offset + 28, true);
    const extraLength = view.getUint16(offset + 30, true);
    const commentLength = view.getUint16(offset + 32, true);
    const localOffset = view.getUint32(offset + 42, true);
    const name = decoder.decode(bytes.subarray(offset + 46, offset + 46 + nameLength));
    offset += 46 + nameLength + extraLength + commentLength;
    if (compressedSize === 0xffffffff || originalSize === 0xffffffff || localOffset === 0xffffffff) {
      throw new Error("ZIP64 packages are not supported");
    }
    if (flags & 1) throw new Error(`zip entry '${name}' is encrypted`);
    if (localOffset + 30 > bytes.length || view.getUint32(localOffset, true) !== 0x04034b50) {
      throw new Error("corrupt zip entry header");
    }
    const dataOffset =
      localOffset + 30 + view.getUint16(localOffset + 26, true) + view.getUint16(localOffset + 28, true);
    if (dataOffset + compressedSize > bytes.length) throw new Error("truncated zip entry");
    entries.push({ name, method, compressedSize, originalSize, dataOffset });
  }
  return entries;
}

const isWantedPart = (name) => {
  const lowered = name.toLowerCase();
  return (
    lowered.endsWith(".model") ||
    lowered === "_rels/.rels" ||
    (lowered.startsWith("metadata/") && lowered.endsWith(".config"))
  );
};

function extractParts(bytes, inflateSync) {
  let entries;
  try {
    entries = listZipEntries(bytes);
  } catch (error) {
    throw new Error(`not a valid 3MF (ZIP) package: ${messageOf(error)}`);
  }
  const total = entries.reduce((sum, entry) => sum + entry.originalSize, 0);
  if (total > LIMITS.maxUncompressedBytes) {
    throw new Error(
      `3MF package is too large when uncompressed (${Math.round(total / 1048576)} MB; ` +
        `limit ${Math.round(LIMITS.maxUncompressedBytes / 1048576)} MB)`
    );
  }
  const files = {};
  for (const entry of entries) {
    if (!isWantedPart(entry.name)) continue;
    const raw = bytes.subarray(entry.dataOffset, entry.dataOffset + entry.compressedSize);
    try {
      if (entry.method === 0) files[entry.name] = raw.slice();
      else if (entry.method === 8) files[entry.name] = inflateSync(raw);
      else throw new Error(`unknown compression type ${entry.method}`);
    } catch (error) {
      throw new Error(`not a valid 3MF (ZIP) package: ${entry.name}: ${messageOf(error)}`);
    }
  }
  return files;
}

export function read3mf(buffer, { inflateSync }) {
  const bytes = buffer instanceof Uint8Array ? buffer : new Uint8Array(buffer);
  const files = extractParts(bytes, inflateSync);

  const parts = new Map();
  const part = (name) => {
    if (!parts.has(name)) {
      if (!(name in files)) {
        throw new Error(`3MF part '${name}' was not found in the package`);
      }
      const root = parseXml(files[name], name);
      const objects = new Map();
      const resources = child(root, "resources");
      if (resources) {
        for (const node of children(resources, "object")) {
          const parsed = parseObject(node, name);
          objects.set(parsed.id, parsed);
        }
      }
      parts.set(name, { root, objects });
    }
    return parts.get(name);
  };

  let rootName = DEFAULT_ROOT;
  if ("_rels/.rels" in files) {
    const rels = parseXml(files["_rels/.rels"], "_rels/.rels");
    const relationship = children(rels, "Relationship").find((item) =>
      (item.attrs.Type || "").endsWith("/3dmodel")
    );
    if (relationship) rootName = normalisePart(relationship.attrs.Target || "", "root model");
  }
  if (!(rootName in files)) {
    throw new Error(`3MF package has no root model (expected '${rootName}')`);
  }
  const root = part(rootName).root;

  const unit = root.attrs.unit || "millimeter";
  if (!(unit in UNIT_FACTORS)) {
    throw new Error(
      `unknown 3MF unit '${unit}'; expected one of ${Object.keys(UNIT_FACTORS).join(", ")}`
    );
  }
  const items = children(child(root, "build") || { children: [] }, "item");
  if (items.length === 0) throw new Error("3MF has no build item to load");
  if (items.length !== 1) {
    throw new Error(
      `Only single-object 3MF files are supported; this file has ${items.length} build items`
    );
  }
  if (items[0].attrs.objectid === undefined) throw new Error("3MF build item has no objectid");
  const start = parseTransform(items[0].attrs.transform, "the build item");

  const blocks = [];
  const names = new Set();
  let triangleTotal = 0;
  const walk = (partName, objectId, matrix, depth, chain) => {
    if (depth > LIMITS.maxDepth) {
      throw new Error(`3MF component nesting is deeper than ${LIMITS.maxDepth} levels`);
    }
    const key = `${partName}\u0000${objectId}`;
    if (chain.has(key)) throw new Error(`3MF component cycle detected at object ${objectId}`);
    const object = part(partName).objects.get(objectId);
    if (!object) throw new Error(`3MF object ${objectId} not found in '${partName}'`);
    if (object.type !== "model") {
      throw new Error(
        `3MF object ${objectId} has type '${object.type}'; only objects of type 'model' are supported`
      );
    }
    if (object.vertices && object.faces) {
      if (object.name) names.add(object.name);
      triangleTotal += object.faces.length / 3;
      if (triangleTotal > LIMITS.maxTriangles) {
        throw new Error(
          `3MF flattens to too many triangles (limit ${LIMITS.maxTriangles} triangles)`
        );
      }
      const flip = determinant3(matrix) < 0; // a mirror flips winding; keep it outward
      const positions = new Float32Array(object.faces.length * 3);
      const { vertices, faces } = object;
      for (let face = 0; face < faces.length; face += 3) {
        const order = flip ? [0, 2, 1] : [0, 1, 2];
        for (let slot = 0; slot < 3; slot += 1) {
          const v = faces[face + order[slot]] * 3;
          const x = vertices[v];
          const y = vertices[v + 1];
          const z = vertices[v + 2];
          const target = (face + slot) * 3;
          positions[target] = x * matrix[0] + y * matrix[4] + z * matrix[8] + matrix[12];
          positions[target + 1] = x * matrix[1] + y * matrix[5] + z * matrix[9] + matrix[13];
          positions[target + 2] = x * matrix[2] + y * matrix[6] + z * matrix[10] + matrix[14];
        }
      }
      blocks.push(positions);
    }
    const nextChain = new Set(chain).add(key);
    for (const component of object.components) {
      const childPart =
        component.path === null ? partName : normalisePart(component.path, "component");
      if (childPart !== partName && !(childPart in files)) {
        throw new Error(
          `3MF part '${childPart}' referenced by object ${objectId} was not found in the package`
        );
      }
      walk(childPart, component.target, multiply(component.transform, matrix), depth + 1, nextChain);
    }
  };
  walk(rootName, items[0].attrs.objectid, start, 1, new Set());

  if (names.size === KINTSUGI_PARTS.length && KINTSUGI_PARTS.every((name) => names.has(name))) {
    throw new Error(
      "This file is already a Kintsugi output (CeramicBody + GoldSeams); upload the original model instead"
    );
  }
  checkSlicerModifiers(files);
  if (triangleTotal === 0) throw new Error("3MF contains no triangles");

  const factor = UNIT_FACTORS[unit];
  const positions = new Float32Array(triangleTotal * 9);
  let offset = 0;
  for (const block of blocks) {
    positions.set(block, offset);
    offset += block.length;
  }
  if (factor !== 1) {
    for (let index = 0; index < positions.length; index += 1) positions[index] *= factor;
  }
  return { positions, triangleCount: triangleTotal, unit };
}
