import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { STLLoader } from "three/addons/loaders/STLLoader.js";
import { OBJLoader } from "three/addons/loaders/OBJLoader.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";

const $ = (id) => document.getElementById(id);

const state = {
  presets: [],
  currentPreset: "",
  customFile: null,
  uploadValid: true,
  modelGroup: new THREE.Group(),
  meshGroup: new THREE.Group(),
  downloads: { ceramic_stl: null, gold_stl: null, three_mf: null },
};

const ui = {
  preset: $("preset-select"),
  fileInput: $("file-input"),
  uploadZone: $("upload-zone"),
  modelNote: $("model-note"),
  ratio: $("ratio-slider"),
  ratioValue: $("ratio-value"),
  ratioCaption: $("ratio-caption"),
  mode: $("mode-select"),
  seed: $("seed-input"),
  seamWidth: $("seam-width-input"),
  fracture: $("fracture-button"),
  overlay: $("processing-overlay"),
  statusOperation: $("status-operation"),
  statusMesh: $("status-mesh"),
  statusKernel: $("status-kernel"),
  downloadCeramic: $("download-ceramic"),
  downloadGold: $("download-gold"),
  download3mf: $("download-3mf"),
  viewport: $("viewport"),
  studioWindow: $("studio-window"),
};

let renderer;
let scene;
let camera;
let controls;
let grid;

const ceramicMaterial = new THREE.MeshStandardMaterial({
  color: 0xf8f6f0,
  roughness: 0.72,
  metalness: 0.02,
  envMapIntensity: 0.9,
});

const goldMaterial = new THREE.MeshStandardMaterial({
  color: 0xffd700,
  roughness: 0.26,
  metalness: 0.85,
  envMapIntensity: 1.6,
  emissive: 0x4a3300,
  emissiveIntensity: 0.45,
});

function initViewer() {
  renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(ui.viewport.clientWidth, ui.viewport.clientHeight);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  ui.viewport.appendChild(renderer.domElement);

  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x1a1f2c);

  camera = new THREE.PerspectiveCamera(
    38,
    ui.viewport.clientWidth / Math.max(ui.viewport.clientHeight, 1),
    0.1,
    5000
  );
  camera.up.set(0, 0, 1);

  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.screenSpacePanning = true;
  controls.rotateSpeed = 0.8;
  controls.zoomSpeed = 0.9;

  const hemi = new THREE.HemisphereLight(0xffffff, 0x253044, 1.4);
  scene.add(hemi);

  const key = new THREE.DirectionalLight(0xfff4df, 2.5);
  key.position.set(1.2, -1.5, 2.0);
  scene.add(key);

  const fill = new THREE.DirectionalLight(0x9fc6ff, 1.0);
  fill.position.set(-1.6, 0.8, 0.8);
  scene.add(fill);

  const rim = new THREE.DirectionalLight(0xffd700, 1.2);
  rim.position.set(-0.8, 1.8, 1.1);
  scene.add(rim);

  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  pmrem.dispose();

  grid = new THREE.GridHelper(260, 26, 0x444b5d, 0x283042);
  grid.rotation.x = Math.PI / 2;
  grid.position.z = -0.05;
  grid.material.transparent = true;
  grid.material.opacity = 0.45;
  scene.add(grid);

  scene.add(state.modelGroup);

  window.addEventListener("resize", onResize);
  renderer.setAnimationLoop(() => {
    controls.update();
    renderer.render(scene, camera);
  });
}

function onResize() {
  if (!renderer || !camera) return;
  const width = Math.max(ui.viewport.clientWidth, 1);
  const height = Math.max(ui.viewport.clientHeight, 1);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  renderer.setSize(width, height);
}

function clearModel() {
  for (const child of [...state.meshGroup.children]) {
    child.geometry?.dispose();
  }
  state.meshGroup.clear();
  state.modelGroup.clear();
  state.modelGroup.add(state.meshGroup);
}

function frameObject() {
  if (!state.modelGroup.children.length) return;
  const box = new THREE.Box3().setFromObject(state.modelGroup);
  if (box.isEmpty()) return;
  const center = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3());
  const maxDim = Math.max(size.x, size.y, size.z, 1);

  controls.target.copy(center);
  camera.position.copy(center).add(
    new THREE.Vector3(1.15, -1.35, 0.95)
      .normalize()
      .multiplyScalar(maxDim * 1.9)
  );
  camera.near = Math.max(maxDim / 2000, 0.05);
  camera.far = maxDim * 40;
  camera.updateProjectionMatrix();
  controls.minDistance = maxDim * 0.08;
  controls.maxDistance = maxDim * 12;
  controls.update();

  grid.position.z = box.min.z - maxDim * 0.04;
  grid.scale.setScalar(Math.max(maxDim / 90, 0.4));
}

function addGeometry(geometry, material, name) {
  geometry.computeVertexNormals();
  const mesh = new THREE.Mesh(geometry, material);
  mesh.name = name;
  mesh.castShadow = false;
  mesh.receiveShadow = false;
  state.meshGroup.add(mesh);
}

async function loadParts(parts) {
  const loader = new STLLoader();
  const geometries = [];
  for (const part of parts) {
    if (!part.url) continue;
    const geometry = await loader.loadAsync(part.url);
    geometries.push({ geometry, material: part.material, name: part.name });
  }
  clearModel();
  for (const item of geometries) {
    addGeometry(item.geometry, item.material, item.name);
  }
  frameObject();
  updateMeshStatus();
}

function updateMeshStatus(extra = "", tone = "") {
  let faces = 0;
  let parts = 0;
  state.meshGroup.traverse((child) => {
    if (child.isMesh) {
      parts += 1;
      const index = child.geometry.getIndex();
      faces += index ? index.count / 3 : child.geometry.attributes.position.count / 3;
    }
  });
  const suffix = extra ? ` | ${extra}` : "";
  ui.statusMesh.textContent = `Faces: ${Math.round(faces).toLocaleString()} | Parts: ${parts}${suffix}`;
  ui.statusMesh.classList.remove("status-success", "status-error");
  if (tone) ui.statusMesh.classList.add(`status-${tone}`);
}

function setStatus(text) {
  ui.statusOperation.textContent = text;
}

function setBusy(busy) {
  ui.fracture.disabled = busy || !state.uploadValid;
  ui.overlay.hidden = !busy;
  if (busy) {
    setStatus("Computing Manifold3D booleans…");
  }
}

function severityLabel(R) {
  if (R >= 1.0) return "Pristine / Wealthy";
  if (R >= 0.7) return "Mild inequality";
  if (R >= 0.4) return "Moderate inequality";
  return "Severe inequality";
}

function updateRatio() {
  const R = Number(ui.ratio.value);
  ui.ratioValue.textContent = `R = ${R.toFixed(2)}`;
  ui.ratioCaption.textContent = severityLabel(R);
  if (R >= 1.0 && !ui.fracture.disabled) {
    setStatus("Pristine / Wealthy (0 cracks)");
  }
}

function setDownload(element, url, fallbackName) {
  if (!url) {
    element.classList.add("disabled");
    element.setAttribute("href", "#");
    element.removeAttribute("download");
    return;
  }
  element.classList.remove("disabled");
  element.setAttribute("href", url);
  const name = url.split("/").pop() || fallbackName;
  element.setAttribute("download", name);
}

async function loadPreset(presetId) {
  const preset = state.presets.find((item) => item.id === presetId);
  if (!preset) return;
  state.currentPreset = presetId;
  state.customFile = null;
  state.uploadValid = true;
  ui.fracture.disabled = false;
  ui.modelNote.textContent = `Preset: ${preset.name}`;
  setStatus(`Loading ${preset.name}…`);
  try {
    await loadParts([{ url: preset.mesh_url, material: ceramicMaterial, name: preset.name }]);
    setStatus(`Ready · ${preset.name}`);
  } catch (error) {
    setStatus(`Could not load preset: ${error.message}`);
  }
}

async function loadPresets() {
  try {
    const response = await fetch("/api/presets");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const body = await response.json();
    state.presets = body.presets || [];
    ui.preset.innerHTML = "";
    for (const preset of state.presets) {
      const option = document.createElement("option");
      option.value = preset.id;
      option.textContent = preset.name;
      ui.preset.appendChild(option);
    }
    ui.preset.value = "tea_bowl";
    await loadPreset("tea_bowl");
  } catch (error) {
    ui.preset.innerHTML = '<option value="">Presets unavailable</option>';
    setStatus(`Preset API error: ${error.message}`);
  }
}

async function handleCustomFile(file) {
  if (!file) return;
  const normalized = file.name.toLowerCase();
  if (!normalized.endsWith(".stl") && !normalized.endsWith(".obj")) {
    setStatus("Only .stl and .obj files are supported");
    return;
  }
  state.customFile = file;
  state.currentPreset = "";
  state.uploadValid = false;
  ui.fracture.disabled = true;
  ui.preset.value = "";
  ui.modelNote.textContent = `Custom: ${file.name}`;
  setStatus(`Loading ${file.name}…`);

  try {
    if (normalized.endsWith(".stl")) {
      const buffer = await file.arrayBuffer();
      const geometry = new STLLoader().parse(buffer);
      clearModel();
      addGeometry(geometry, ceramicMaterial, file.name);
      frameObject();
    } else {
      const text = await file.text();
      const group = new OBJLoader().parse(text);
      clearModel();
      group.traverse((child) => {
        if (child.isMesh) {
          child.material = ceramicMaterial;
          state.meshGroup.add(child);
        }
      });
      frameObject();
    }
    await validateCustomFile(file);
  } catch (error) {
    state.uploadValid = false;
    ui.fracture.disabled = true;
    updateMeshStatus(`Could not read ${file.name}: ${error.message}`, "error");
    setStatus(`Could not read ${file.name}: ${error.message}`);
  }
}

async function validateCustomFile(file) {
  const form = new FormData();
  form.append("file", file);
  setStatus(`Validating watertightness of ${file.name}…`);
  try {
    const response = await fetch("/api/validate", { method: "POST", body: form });
    const body = await response.json();
    if (!response.ok) {
      throw new Error(body.detail || `HTTP ${response.status}`);
    }
    if (body.valid) {
      state.uploadValid = true;
      ui.fracture.disabled = false;
      updateMeshStatus("Watertight ✓", "success");
      setStatus(`Ready · ${file.name}`);
    } else {
      state.uploadValid = false;
      ui.fracture.disabled = true;
      updateMeshStatus(`Not a valid closed solid: ${body.detail}`, "error");
      setStatus(`Invalid model: ${body.detail}`);
    }
  } catch (error) {
    state.uploadValid = false;
    ui.fracture.disabled = true;
    updateMeshStatus(`Validation failed: ${error.message}`, "error");
    setStatus(`Validation failed: ${error.message}`);
  }
}

async function fracture() {
  const hasCustom = Boolean(state.customFile);
  const preset = ui.preset.value;
  if (!hasCustom && !preset) {
    setStatus("Choose a preset or drop a custom model first");
    return;
  }
  if (hasCustom && !state.uploadValid) {
    setStatus("Custom model is not a valid closed solid");
    return;
  }

  const form = new FormData();
  if (hasCustom) {
    form.append("file", state.customFile);
  } else {
    form.append("preset", preset);
  }
  const modeInput = document.querySelector('input[name="mode"]:checked');
  form.append("R", ui.ratio.value);
  form.append("mode", modeInput ? modeInput.value : "vein");
  form.append("seed", ui.seed.value || "7");
  if (ui.seamWidth.value !== "") {
    form.append("seam_width", ui.seamWidth.value);
  }

  setBusy(true);
  try {
    const response = await fetch("/api/fracture", { method: "POST", body: form });
    const body = await response.json();
    if (!response.ok) {
      throw new Error(body.detail || `HTTP ${response.status}`);
    }

    state.downloads = body.downloads;
    setDownload(ui.downloadCeramic, body.downloads.ceramic_stl, "ceramic_body.stl");
    setDownload(ui.downloadGold, body.downloads.gold_stl, "gold_seams.stl");
    setDownload(ui.download3mf, body.downloads.three_mf, "kintsugi_assembly.3mf");

    await loadParts([
      { url: body.downloads.ceramic_stl, material: ceramicMaterial, name: "CeramicBody" },
      { url: body.downloads.gold_stl, material: goldMaterial, name: "GoldSeams" },
    ]);

    const volumes = body.volumes;
    const seamsOmitted = Boolean(body.seams_omitted);
    const currentRatio = Number(ui.ratio.value);
    let label;
    if (seamsOmitted && currentRatio < 1.0) {
      const reason = body.seams_omitted_reason || "wall thickness < 1.05 mm";
      label = `Seams Omitted (${reason})`;
    } else if (body.num_cracks === 0) {
      label = "Pristine / Wealthy (0 cracks)";
    } else {
      label = `${body.num_cracks} cracks · gold ${volumes.gold.toFixed(1)} mm³`;
    }
    setStatus(label);
    updateMeshStatus(
      `Ceramic ${volumes.ceramic.toFixed(1)} mm³ · Gold ${volumes.gold.toFixed(1)} mm³`
    );
  } catch (error) {
    setStatus(`Fracture failed: ${error.message}`);
  } finally {
    setBusy(false);
  }
}

function wireEvents() {
  ui.preset.addEventListener("change", () => {
    if (ui.preset.value) loadPreset(ui.preset.value);
  });

  ui.uploadZone.addEventListener("click", () => ui.fileInput.click());
  ui.uploadZone.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      ui.fileInput.click();
    }
  });
  ui.fileInput.addEventListener("change", () => handleCustomFile(ui.fileInput.files[0]));

  for (const eventName of ["dragenter", "dragover"]) {
    ui.uploadZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      ui.uploadZone.classList.add("dragover");
    });
  }
  for (const eventName of ["dragleave", "drop"]) {
    ui.uploadZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      ui.uploadZone.classList.remove("dragover");
    });
  }
  ui.uploadZone.addEventListener("drop", (event) => {
    const file = event.dataTransfer?.files?.[0];
    if (file) handleCustomFile(file);
  });

  ui.ratio.addEventListener("input", updateRatio);
  ui.fracture.addEventListener("click", fracture);

  document.querySelectorAll("[data-focus]").forEach((item) => {
    item.addEventListener("click", () => {
      const target = $(item.dataset.focus);
      target?.focus();
    });
  });

  $("btn-minimize").addEventListener("click", () => {
    ui.studioWindow.classList.toggle("minimized");
  });
  $("btn-maximize").addEventListener("click", () => {
    ui.studioWindow.classList.toggle("maximized");
    setTimeout(onResize, 30);
  });
  $("btn-close").addEventListener("click", () => {
    if (window.confirm("Close Kintsugi Studio 2001?")) {
      ui.studioWindow.style.display = "none";
    }
  });
}

async function start() {
  initViewer();
  wireEvents();
  updateRatio();
  setDownload(ui.downloadCeramic, null);
  setDownload(ui.downloadGold, null);
  setDownload(ui.download3mf, null);
  await loadPresets();
}

start().catch((error) => {
  console.error(error);
  setStatus(`Startup error: ${error.message}`);
});
