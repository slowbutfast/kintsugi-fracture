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
  generator: $("generator-select"),
  generatorNote: $("generator-note"),
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
  menuEntries: document.querySelectorAll(".menu-entry"),
  menuTriggers: document.querySelectorAll(".menu-item[data-menu]"),
  menuFile: $("menu-file"),
  menuPresets: $("menu-presets"),
  menuHelp: $("menu-help"),
  menuMode: $("menu-mode"),
  menuUpload: $("menu-upload"),
  menuFracture: $("menu-fracture"),
  menuDownloadCeramic: $("menu-download-ceramic"),
  menuDownloadGold: $("menu-download-gold"),
  menuDownload3mf: $("menu-download-3mf"),
  menuResetCamera: $("menu-reset-camera"),
  menuAbout: $("menu-about"),
  mobileTabs: $("mobile-tabs"),
  mobileTabButtons: document.querySelectorAll(".mobile-tab"),
  tabPanels: document.querySelectorAll("[data-tab-panel]"),
  exportBadge: $("export-badge"),
  helpDialog: $("help-dialog"),
  helpDialogClose: $("help-dialog-close"),
  helpDialogOk: $("help-dialog-ok"),
  viewportHint: document.querySelector(".viewport-hint"),
  viewport: $("viewport"),
  studioWindow: $("studio-window"),
};

let renderer;
let scene;
let camera;
let controls;
let grid;

const ceramicMaterial = new THREE.MeshStandardMaterial({
  color: 0x18181b,
  roughness: 0.65,
  metalness: 0.10,
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
  scene.background = new THREE.Color(0xf0ede0);

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

  const hemi = new THREE.HemisphereLight(0xffffff, 0xdcd8cc, 1.4);
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

  grid = new THREE.GridHelper(260, 26, 0xb8b4a6, 0xd0ccc0);
  grid.rotation.x = Math.PI / 2;
  grid.position.z = -0.05;
  grid.material.transparent = true;
  grid.material.opacity = 0.40;
  scene.add(grid);

  scene.add(state.modelGroup);

  window.addEventListener("resize", onResize);
  if (typeof ResizeObserver !== "undefined") {
    new ResizeObserver(() => onResize()).observe(ui.viewport);
  }
  if (ui.viewportHint && window.matchMedia?.("(pointer: coarse)").matches) {
    ui.viewportHint.textContent = "Drag to orbit · Pinch to zoom · Two-finger pan";
  }
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

const MOBILE_TABS = ["model", "fracture", "export"];

function openMenu(name) {
  syncMenuChecks();
  for (const entry of ui.menuEntries) {
    const trigger = entry.querySelector(".menu-item");
    const dropdown = entry.querySelector(".menu-dropdown");
    const shouldOpen = Boolean(
      trigger && trigger.dataset.menu === name && dropdown
    );
    trigger?.setAttribute("aria-expanded", shouldOpen ? "true" : "false");
    if (dropdown) dropdown.hidden = !shouldOpen;
  }
}

function closeMenus() {
  for (const entry of ui.menuEntries) {
    entry.querySelector(".menu-item")?.setAttribute("aria-expanded", "false");
    const dropdown = entry.querySelector(".menu-dropdown");
    if (dropdown) dropdown.hidden = true;
  }
}

function anyMenuOpen() {
  return Boolean(document.querySelector(".menu-dropdown:not([hidden])"));
}

function switchMobileTab(tabName) {
  const target = MOBILE_TABS.includes(tabName) ? tabName : "fracture";
  for (const button of ui.mobileTabButtons) {
    const active = button.dataset.tab === target;
    button.classList.toggle("active", active);
    button.setAttribute("aria-selected", active ? "true" : "false");
  }
  for (const panel of ui.tabPanels) {
    panel.classList.toggle(
      "mobile-panel-active",
      panel.dataset.tabPanel === target
    );
  }
  if (target === "export" && ui.exportBadge) {
    ui.exportBadge.hidden = true;
  }
  requestAnimationFrame(onResize);
}

function syncMenuChecks() {
  const presetId = ui.preset.value;
  for (const option of ui.menuPresets.querySelectorAll("[data-preset]")) {
    option.setAttribute(
      "aria-checked",
      option.dataset.preset === presetId ? "true" : "false"
    );
  }

  const generator = ui.generator ? ui.generator.value : "growth";
  for (const option of ui.menuMode.querySelectorAll("[data-generator]")) {
    option.setAttribute(
      "aria-checked",
      option.dataset.generator === generator ? "true" : "false"
    );
  }

  const modeInput = document.querySelector('input[name="mode"]:checked');
  const mode = modeInput ? modeInput.value : "vein";
  const ribbonOption = ui.menuMode.querySelector('[data-mode="ribbon"]');
  if (ribbonOption) {
    const ribbonDisabled = generator === "shard";
    ribbonOption.classList.toggle("disabled", ribbonDisabled);
    ribbonOption.setAttribute(
      "aria-disabled",
      ribbonDisabled ? "true" : "false"
    );
    ribbonOption.tabIndex = ribbonDisabled ? -1 : 0;
  }
  for (const option of ui.menuMode.querySelectorAll("[data-mode]")) {
    option.setAttribute(
      "aria-checked",
      option.dataset.mode === mode ? "true" : "false"
    );
  }
}

function populatePresetMenu() {
  if (!ui.menuPresets) return;
  ui.menuPresets.innerHTML = '<div class="menu-section-label">Bundled Presets</div>';
  for (const preset of state.presets) {
    const option = document.createElement("button");
    option.type = "button";
    option.className = "menu-option";
    option.dataset.preset = preset.id;
    option.setAttribute("role", "menuitemradio");
    option.setAttribute("aria-checked", "false");

    const check = document.createElement("span");
    check.className = "menu-check";
    check.setAttribute("aria-hidden", "true");

    const label = document.createElement("span");
    label.textContent = preset.name;

    option.append(check, label);
    ui.menuPresets.appendChild(option);
  }
}

function openHelpDialog() {
  closeMenus();
  if (!ui.helpDialog) return;
  ui.helpDialog.hidden = false;
  ui.helpDialogClose?.focus();
}

function closeHelpDialog() {
  if (ui.helpDialog) ui.helpDialog.hidden = true;
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

function syncGeneratorMode() {
  if (!ui.generator) return;
  const gen = ui.generator.value;
  const veinInput = document.querySelector('input[name="mode"][value="vein"]');
  const ribbonInput = document.querySelector('input[name="mode"][value="ribbon"]');
  if (gen === "shard") {
    if (veinInput) veinInput.checked = true;
    if (ribbonInput) ribbonInput.disabled = true;
    if (ui.generatorNote) {
      ui.generatorNote.textContent = "Tilted shard seams (Vein Inlay only).";
    }
  } else {
    if (ribbonInput) ribbonInput.disabled = false;
    if (ui.generatorNote) {
      ui.generatorNote.textContent =
        gen === "voronoi"
          ? "Periodic cellular Voronoi seams."
          : "Rim-seeded branching cracks.";
    }
  }
  syncMenuChecks();
}

function setDownload(element, url, fallbackName) {
  if (!element) return;
  if (!url) {
    element.classList.add("disabled");
    element.setAttribute("href", "#");
    element.setAttribute("aria-disabled", "true");
    element.removeAttribute("download");
    return;
  }
  element.classList.remove("disabled");
  element.setAttribute("href", url);
  element.setAttribute("aria-disabled", "false");
  const name = url.split("/").pop() || fallbackName;
  element.setAttribute("download", name);

  const activeTab = document.querySelector(".mobile-tab.active")?.dataset.tab;
  if (ui.exportBadge && activeTab !== "export") {
    ui.exportBadge.hidden = false;
  }
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
    populatePresetMenu();
    ui.preset.value = "tea_bowl";
    syncMenuChecks();
    await loadPreset("tea_bowl");
  } catch (error) {
    ui.preset.innerHTML = '<option value="">Presets unavailable</option>';
    if (ui.menuPresets) {
      ui.menuPresets.innerHTML =
        '<div class="menu-section-label">Presets Unavailable</div>';
    }
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
  syncMenuChecks();
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
      const wall =
        typeof body.wall_thickness_p5 === "number"
          ? ` | Wall: ${body.wall_thickness_p5.toFixed(2)} mm`
          : "";
      const vertices =
        typeof body.vertices === "number"
          ? ` | Vertices: ${body.vertices}`
          : "";
      updateMeshStatus(`Watertight ✓${vertices}${wall}`, "success");
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
  form.append("generator", ui.generator ? ui.generator.value : "growth");
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
    setDownload(ui.menuDownloadCeramic, body.downloads.ceramic_stl, "ceramic_body.stl");
    setDownload(ui.menuDownloadGold, body.downloads.gold_stl, "gold_seams.stl");
    setDownload(ui.menuDownload3mf, body.downloads.three_mf, "kintsugi_assembly.3mf");

    await loadParts([
      { url: body.downloads.ceramic_stl, material: ceramicMaterial, name: "CeramicBody" },
      { url: body.downloads.gold_stl, material: goldMaterial, name: "GoldSeams" },
    ]);

    const volumes = body.volumes;
    const seamsOmitted = Boolean(body.seams_omitted);
    const currentRatio = Number(ui.ratio.value);
    let label;
    if (seamsOmitted && currentRatio < 1.0) {
      label = "Seams Omitted";
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
    syncMenuChecks();
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
  if (ui.generator) {
    ui.generator.addEventListener("change", syncGeneratorMode);
  }
  ui.fracture.addEventListener("click", fracture);

  for (const trigger of ui.menuTriggers) {
    trigger.addEventListener("click", (event) => {
      event.stopPropagation();
      const name = trigger.dataset.menu;
      const dropdown = $(`menu-${name}`);
      const wasOpen = dropdown ? !dropdown.hidden : false;
      closeMenus();
      if (!wasOpen) openMenu(name);
    });
    trigger.addEventListener("pointerenter", () => {
      if (window.matchMedia?.("(hover: hover)").matches && anyMenuOpen()) {
        openMenu(trigger.dataset.menu);
      }
    });
  }

  document.addEventListener("pointerdown", (event) => {
    if (!event.target.closest(".menu-entry")) closeMenus();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeMenus();
      closeHelpDialog();
    }
  });

  ui.menuUpload?.addEventListener("click", () => {
    closeMenus();
    ui.fileInput.click();
  });

  ui.menuFracture?.addEventListener("click", () => {
    closeMenus();
    fracture();
  });

  for (const link of [
    ui.menuDownloadCeramic,
    ui.menuDownloadGold,
    ui.menuDownload3mf,
  ]) {
    link?.addEventListener("click", (event) => {
      if (
        link.classList.contains("disabled") ||
        link.getAttribute("aria-disabled") === "true"
      ) {
        event.preventDefault();
        return;
      }
      closeMenus();
    });
  }

  ui.menuPresets?.addEventListener("click", (event) => {
    const option = event.target.closest("[data-preset]");
    if (!option) return;
    ui.preset.value = option.dataset.preset;
    loadPreset(option.dataset.preset);
    syncMenuChecks();
    closeMenus();
  });

  ui.menuMode?.addEventListener("click", (event) => {
    const generatorOption = event.target.closest("[data-generator]");
    if (generatorOption) {
      if (ui.generator) ui.generator.value = generatorOption.dataset.generator;
      syncGeneratorMode();
      syncMenuChecks();
      closeMenus();
      return;
    }
    const modeOption = event.target.closest("[data-mode]");
    if (!modeOption || modeOption.classList.contains("disabled")) return;
    const input = document.querySelector(
      `input[name="mode"][value="${modeOption.dataset.mode}"]`
    );
    if (input && !input.disabled) {
      input.checked = true;
      syncGeneratorMode();
      syncMenuChecks();
      closeMenus();
    }
  });

  ui.menuResetCamera?.addEventListener("click", () => {
    frameObject();
    closeMenus();
  });

  ui.menuAbout?.addEventListener("click", openHelpDialog);

  for (const button of ui.mobileTabButtons) {
    button.addEventListener("click", () => switchMobileTab(button.dataset.tab));
  }

  ui.helpDialog?.addEventListener("click", (event) => {
    if (event.target === ui.helpDialog) closeHelpDialog();
  });
  ui.helpDialogClose?.addEventListener("click", closeHelpDialog);
  ui.helpDialogOk?.addEventListener("click", closeHelpDialog);

  document.querySelectorAll('input[name="mode"]').forEach((input) => {
    input.addEventListener("change", () => {
      syncGeneratorMode();
      syncMenuChecks();
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
  syncGeneratorMode();
  setDownload(ui.downloadCeramic, null);
  setDownload(ui.downloadGold, null);
  setDownload(ui.download3mf, null);
  setDownload(ui.menuDownloadCeramic, null);
  setDownload(ui.menuDownloadGold, null);
  setDownload(ui.menuDownload3mf, null);
  switchMobileTab("fracture");
  await loadPresets();
}

start().catch((error) => {
  console.error(error);
  setStatus(`Startup error: ${error.message}`);
});
