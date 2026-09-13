<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { cloneMannequinModel } from "../modelPreviewAssets.js";
import LoadingAnimation from "./LoadingAnimation.vue";

const props = defineProps({
  itemId: { type: [Number, String], default: null },
  modelUrl: { type: String, default: "" },
  textureUrl: { type: String, default: "" },
  mannequinUrl: { type: String, default: "" },
  previewKey: { type: [Number, String], default: "" },
  previewLoader: { type: Function, default: null },
  autoLoad: { type: Boolean, default: false },
});
const emit = defineEmits(["ready-change"]);
const canvasHost = ref(null);
const backgroundListbox = ref(null);
const lightingListbox = ref(null);
const state = ref("idle");
const message = ref("");
const backgroundMode = ref("white");
const lightingMode = ref("soft");
const modelVariant = ref("default");
const modelUrls = ref({ default: "", half: "" });
const switchingVariant = ref(false);
const mannequinUrl = ref("");
const mannequinVisible = ref(true);
const expanded = ref(false);
const mannequinOptions = [
  { value: true, label: "显示" },
  { value: false, label: "隐藏" },
];
const modelVariantOptions = [
  { value: "default", label: "正常" },
  { value: "half", label: "半脱" },
];
const backgroundOptions = [
  { value: "white", label: "白" },
  { value: "black", label: "黑" },
];
const lightingOptions = [
  { value: "soft", label: "柔光" },
  { value: "studio", label: "棚拍" },
  { value: "warm", label: "暖光" },
  { value: "cool", label: "冷光" },
  { value: "contour", label: "轮廓" },
  { value: "dramatic", label: "戏剧" },
];
const listboxSteps = [
  { direction: -1, symbol: "▲", label: "上一个" },
  { direction: 1, symbol: "▼", label: "下一个" },
];
const listboxWheelTimes = new WeakMap();
const listboxDragStates = new WeakMap();
const listboxClickSuppressions = new WeakMap();
let renderer;
let controls;
let animationFrame;
let resizeObserver;
let scene;
let camera;
let threeApi;
let lightRig;
let mannequinObject;
let clothingObject;
let previewGeneration = 0;
const WORKBENCH_FBX_DISPLAY_SCALE = 10;

function isCurrentPreview(generation) {
  return generation === previewGeneration;
}

function disposeModelObject(object) {
  if (!object) return;
  object.traverse?.((child) => {
    child.geometry?.dispose?.();
    if (Array.isArray(child.material)) child.material.forEach((material) => material.dispose?.());
    else child.material?.dispose?.();
  });
}

function handleExpandedKeydown(event) {
  if (event.key === "Escape") setExpanded(false);
}

function setExpanded(value) {
  expanded.value = Boolean(value);
  document.body.classList.toggle("model-preview-expanded", expanded.value);
  document.removeEventListener("keydown", handleExpandedKeydown);
  if (expanded.value) document.addEventListener("keydown", handleExpandedKeydown);
}

function handleListboxKeydown(event, options, selectedValue, selectOption, disabled = false) {
  if (disabled || !options.length) return;
  const currentIndex = Math.max(options.findIndex((option) => Object.is(option.value, selectedValue)), 0);
  let nextIndex = currentIndex;
  if (event.key === "ArrowRight" || event.key === "ArrowDown") nextIndex = Math.min(currentIndex + 1, options.length - 1);
  else if (event.key === "ArrowLeft" || event.key === "ArrowUp") nextIndex = Math.max(currentIndex - 1, 0);
  else if (event.key === "Home") nextIndex = 0;
  else if (event.key === "End") nextIndex = options.length - 1;
  else return;
  event.preventDefault();
  const listbox = event.currentTarget;
  selectOption(options[nextIndex].value);
  nextTick(() => {
    const nextOption = listbox.querySelectorAll('[role="option"]')[nextIndex];
    nextOption?.focus({ preventScroll: true });
    nextOption?.scrollIntoView({
      block: "nearest",
      inline: "nearest",
    });
  });
}

function listboxStepDisabled(options, selectedValue, direction, disabled = false) {
  if (disabled || !options.length) return true;
  const currentIndex = Math.max(options.findIndex((option) => Object.is(option.value, selectedValue)), 0);
  return currentIndex + direction < 0 || currentIndex + direction >= options.length;
}

function stepListbox(event, options, selectedValue, selectOption, direction, disabled = false) {
  if (listboxStepDisabled(options, selectedValue, direction, disabled)) return;
  const group = event.currentTarget.closest(".model-preview-control-group");
  const listbox = group?.querySelector('[role="listbox"]');
  if (!listbox) return;
  const currentIndex = Math.max(options.findIndex((option) => Object.is(option.value, selectedValue)), 0);
  const nextIndex = currentIndex + direction;
  selectOption(options[nextIndex].value);
  nextTick(() => {
    listbox.querySelectorAll('[role="option"]')[nextIndex]?.scrollIntoView({
      behavior: "smooth",
      block: "nearest",
      inline: "nearest",
    });
  });
}

function startListboxDrag(event, options, selectedValue, selectOption, disabled = false) {
  if (disabled || !options.length || (event.pointerType === "mouse" && event.button !== 0)) return;
  const listbox = event.currentTarget;
  const selectedIndex = Math.max(options.findIndex((option) => Object.is(option.value, selectedValue)), 0);
  listbox.classList.add("is-dragging");
  listbox.scrollTop = selectedIndex * listbox.clientHeight;
  listbox.setPointerCapture?.(event.pointerId);
  listboxDragStates.set(listbox, {
    pointerId: event.pointerId,
    startY: event.clientY,
    startScrollTop: listbox.scrollTop,
    selectedIndex,
    moved: false,
    options,
    selectOption,
  });
}

function moveListboxDrag(event) {
  const listbox = event.currentTarget;
  const dragState = listboxDragStates.get(listbox);
  if (!dragState || dragState.pointerId !== event.pointerId) return;
  const distance = event.clientY - dragState.startY;
  if (Math.abs(distance) >= 3) dragState.moved = true;
  if (!dragState.moved) return;
  event.preventDefault();
  const rowHeight = Math.max(listbox.clientHeight, 1);
  const maxScroll = (dragState.options.length - 1) * rowHeight;
  listbox.scrollTop = Math.max(0, Math.min(dragState.startScrollTop - distance, maxScroll));
}

function finishListboxDrag(event, cancelled = false) {
  const listbox = event.currentTarget;
  const dragState = listboxDragStates.get(listbox);
  if (!dragState || dragState.pointerId !== event.pointerId) return;
  const rowHeight = Math.max(listbox.clientHeight, 1);
  const nextIndex = cancelled
    ? dragState.selectedIndex
    : Math.max(0, Math.min(Math.round(listbox.scrollTop / rowHeight), dragState.options.length - 1));
  listboxDragStates.delete(listbox);
  listbox.classList.remove("is-dragging");
  if (listbox.hasPointerCapture?.(event.pointerId)) listbox.releasePointerCapture(event.pointerId);
  if (dragState.moved) listboxClickSuppressions.set(listbox, Date.now() + 400);
  dragState.selectOption(dragState.options[nextIndex].value);
  nextTick(() => {
    listbox.querySelectorAll('[role="option"]')[nextIndex]?.scrollIntoView({
      behavior: "smooth",
      block: "nearest",
      inline: "nearest",
    });
  });
}

function suppressListboxClickAfterDrag(event) {
  const listbox = event.currentTarget;
  if (Date.now() > (listboxClickSuppressions.get(listbox) || 0)) return;
  event.preventDefault();
  event.stopPropagation();
  listboxClickSuppressions.delete(listbox);
}

function scrollListbox(event, options, selectedValue, selectOption, disabled = false) {
  if (disabled || !options.length) return;
  const listbox = event.currentTarget;
  const delta = Math.abs(event.deltaY) >= Math.abs(event.deltaX) ? event.deltaY : event.deltaX;
  if (!delta) return;
  const currentIndex = Math.max(options.findIndex((option) => Object.is(option.value, selectedValue)), 0);
  const nextIndex = Math.max(0, Math.min(currentIndex + Math.sign(delta), options.length - 1));
  if (nextIndex === currentIndex) return;
  event.preventDefault();
  const now = performance.now();
  if (now - (listboxWheelTimes.get(listbox) || 0) < 140) return;
  listboxWheelTimes.set(listbox, now);
  selectOption(options[nextIndex].value);
  nextTick(() => {
    listbox.querySelectorAll('[role="option"]')[nextIndex]?.scrollIntoView({
      behavior: "smooth",
      block: "nearest",
      inline: "nearest",
    });
  });
}

function applyBackground() {
  if (!scene || !threeApi) return;
  scene.background = new threeApi.Color(backgroundMode.value === "black" ? 0x050607 : 0xffffff);
}

function applyLighting() {
  if (!scene || !threeApi) return;
  if (lightRig) scene.remove(lightRig);
  lightRig = new threeApi.Group();
  lightRig.name = "StarManagerPreviewLights";

  const addDirectionalLight = (color, intensity, x, y, z) => {
    const light = new threeApi.DirectionalLight(color, intensity);
    light.position.set(x, y, z);
    lightRig.add(light);
  };

  if (lightingMode.value === "studio") {
    lightRig.add(new threeApi.HemisphereLight(0xffffff, 0x66717c, 1.8));
    addDirectionalLight(0xffffff, 3.6, 3.5, 5, 5);
    addDirectionalLight(0xf4f8ff, 1.45, -4, 2, 3);
    addDirectionalLight(0xd7eaff, 1.15, -3, 3, -4);
    addDirectionalLight(0xffffff, 0.75, 0, 5, -1);
  } else if (lightingMode.value === "warm") {
    lightRig.add(new threeApi.HemisphereLight(0xfff3e2, 0x604d4a, 1.5));
    addDirectionalLight(0xffc98f, 3.25, 3.5, 4.5, 4);
    addDirectionalLight(0xfff1dc, 1.25, -3, 1.5, 4);
    addDirectionalLight(0xffc5d8, 1.35, -4, 2.5, -3);
  } else if (lightingMode.value === "cool") {
    lightRig.add(new threeApi.HemisphereLight(0xe9f7ff, 0x40566d, 1.65));
    addDirectionalLight(0xb9ddff, 3.2, 3, 5, 4);
    addDirectionalLight(0xf3f9ff, 1.05, -3.5, 1.5, 4);
    addDirectionalLight(0xd8cfff, 1.7, -4, 2.5, -3.5);
  } else if (lightingMode.value === "contour") {
    lightRig.add(new threeApi.HemisphereLight(0xdbe8ff, 0x08090b, 0.62));
    addDirectionalLight(0xffead7, 3.4, -3.5, 4.5, 5);
    addDirectionalLight(0x90c8ff, 4.1, 4.5, 2.5, -4);
    addDirectionalLight(0xffffff, 1.1, 0, -2, -3);
  } else if (lightingMode.value === "dramatic") {
    lightRig.add(new threeApi.HemisphereLight(0x8298b5, 0x050608, 0.34));
    addDirectionalLight(0xffffff, 4.35, -2.5, 5, 4);
    addDirectionalLight(0x7f9dff, 0.5, 3, 0.5, 2);
    addDirectionalLight(0xff8fb5, 2.9, 4, 3, -4);
  } else {
    lightRig.add(new threeApi.HemisphereLight(0xffffff, 0x66717c, 2.25));
    addDirectionalLight(0xffffff, 2.8, 3, 5, 4);
    addDirectionalLight(0xfff4e8, 1.15, -3, 1, 4);
    addDirectionalLight(0xb8d8ff, 1.6, -4, 2, -3);
  }
  scene.add(lightRig);
}

function setBackground(mode) {
  backgroundMode.value = mode;
  applyBackground();
}

function setLighting(mode) {
  lightingMode.value = mode;
  applyLighting();
}

function syncListboxPosition(listbox, options, selectedValue) {
  if (!listbox) return;
  const selectedIndex = Math.max(options.findIndex((option) => Object.is(option.value, selectedValue)), 0);
  listbox.scrollTop = selectedIndex * Math.max(listbox.clientHeight, 1);
}

async function syncAppearanceListboxes() {
  await nextTick();
  syncListboxPosition(backgroundListbox.value, backgroundOptions, backgroundMode.value);
  syncListboxPosition(lightingListbox.value, lightingOptions, lightingMode.value);
}

function frameVisibleModels() {
  if (!scene || !camera || !controls || !threeApi || !clothingObject) return;
  const box = new threeApi.Box3().setFromObject(clothingObject);
  if (mannequinObject?.visible) box.expandByObject(mannequinObject);
  const sphere = box.getBoundingSphere(new threeApi.Sphere());
  if (!Number.isFinite(sphere.radius) || sphere.radius <= 0) throw new Error("模型尺寸无效");
  controls.target.copy(sphere.center);
  camera.near = Math.max(sphere.radius / 1000, 0.001);
  camera.far = sphere.radius * 100;
  camera.position.copy(sphere.center).add(new threeApi.Vector3(1.35, 0.8, 1.65).normalize().multiplyScalar(sphere.radius * 3.1));
  camera.updateProjectionMatrix();
  controls.update();
}

function setMannequinVisible(visible) {
  mannequinVisible.value = visible;
  if (!mannequinObject) return;
  mannequinObject.visible = visible;
  frameVisibleModels();
}

function shouldKeepSourcePreviewBone(name) {
  const normalizedName = String(name || "").trim();
  return /^cf_J_(?:Legsk|sk)_/i.test(normalizedName) || (normalizedName && !/^cf_/i.test(normalizedName));
}

function bindClothingToMannequin() {
  if (!clothingObject || !mannequinObject || !threeApi) return 0;
  const mannequinBones = new Map();
  mannequinObject.traverse((object) => {
    if (object.isBone && object.name) mannequinBones.set(object.name, object);
  });
  mannequinObject.updateMatrixWorld(true);
  let boundMeshCount = 0;
  clothingObject.traverse((object) => {
    if (!object.isSkinnedMesh || !object.skeleton?.bones?.length) return;
    const sourceSkeleton = object.skeleton;
    const sourceBoneInverses = sourceSkeleton.boneInverses.map((matrix) => matrix.clone());
    const sourceBindMatrix = object.bindMatrix.clone();
    const sourceBindMode = object.bindMode;
    const fallbackRoot = mannequinBones.get("p_cf_body_00") || mannequinBones.get("cf_N_height") || mannequinBones.values().next().value;
    const bones = sourceSkeleton.bones.map((bone) => {
      if (mannequinBones.has(bone.name)) return mannequinBones.get(bone.name);
      const fallbackNames = Array.isArray(bone.userData?.fallbackBoneNames) ? bone.userData.fallbackBoneNames : [];
      const fallbackBone = fallbackNames.map((name) => mannequinBones.get(name)).find(Boolean) || fallbackRoot;
      if (!shouldKeepSourcePreviewBone(bone.name)) return fallbackBone;
      return bone;
    });
    const skeleton = new threeApi.Skeleton(bones, sourceBoneInverses);
    object.bind(skeleton, sourceBindMatrix);
    object.bindMode = sourceBindMode;
    object.normalizeSkinWeights();
    object.frustumCulled = false;
    boundMeshCount += 1;
  });
  clothingObject.updateMatrixWorld(true);
  return boundMeshCount;
}

function prepareWorkbenchModelVisibility(object, url) {
  if (!object || !props.modelUrl || !url.toLowerCase().split("?")[0].endsWith(".fbx")) return;
  object.visible = true;
  object.traverse((child) => {
    if (!child.isMesh) return;
    child.visible = true;
    child.frustumCulled = false;
    child.renderOrder = 10;
    const materials = Array.isArray(child.material) ? child.material : [child.material];
    materials.filter(Boolean).forEach((material) => {
      // Keep the garment depth-aware so rear faces cannot draw through its
      // visible surface.  A small forward polygon offset still prevents a
      // coplanar mannequin from swallowing the garment in the preview.
      material.depthTest = true;
      material.depthWrite = true;
      material.polygonOffset = true;
      material.polygonOffsetFactor = -1;
      material.polygonOffsetUnits = -1;
      material.visible = true;
      // Workbench clothing is an outward-facing surface.  Rendering both
      // sides makes reversed/overlapping faces appear as triangular z-fighting
      // patterns, so discard back-facing polygons in the preview.
      material.side = threeApi?.FrontSide ?? material.side;
      if (!material.alphaMap) material.alphaTest = 0;
      material.blending = threeApi?.NormalBlending ?? material.blending;
      // Some Sims 4 FBX exporters leave an alpha flag on an otherwise opaque
      // material.  Keep those meshes from becoming fully transparent in the
      // browser renderer while preserving genuinely translucent materials.
      if (material.opacity <= 0) {
        material.opacity = 1;
        material.transparent = false;
      }
      material.needsUpdate = true;
    });
  });
}

async function applyWorkbenchTexture(object) {
  if (!object || !props.textureUrl || !threeApi) return;
  const sourceTexture = await new threeApi.TextureLoader().loadAsync(props.textureUrl);
  const sourceImage = sourceTexture.image;
  const canvas = document.createElement("canvas");
  canvas.width = sourceImage.naturalWidth || sourceImage.width;
  canvas.height = sourceImage.naturalHeight || sourceImage.height;
  const context = canvas.getContext("2d", { willReadFrequently: true });
  if (!context || !canvas.width || !canvas.height) throw new Error("贴图画布创建失败");
  context.drawImage(sourceImage, 0, 0, canvas.width, canvas.height);
  const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
  const pixels = imageData.data;
  let redTotal = 0;
  let greenTotal = 0;
  let blueTotal = 0;
  let opaquePixelCount = 0;
  for (let index = 0; index < pixels.length; index += 4) {
    if (pixels[index + 3] <= 12) continue;
    redTotal += pixels[index];
    greenTotal += pixels[index + 1];
    blueTotal += pixels[index + 2];
    opaquePixelCount += 1;
  }
  const fillRed = opaquePixelCount ? Math.round(redTotal / opaquePixelCount) : 128;
  const fillGreen = opaquePixelCount ? Math.round(greenTotal / opaquePixelCount) : 128;
  const fillBlue = opaquePixelCount ? Math.round(blueTotal / opaquePixelCount) : 128;
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.fillStyle = `rgb(${fillRed}, ${fillGreen}, ${fillBlue})`;
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.save();
  context.filter = "blur(12px)";
  context.drawImage(sourceImage, 0, 0, canvas.width, canvas.height);
  context.restore();
  context.drawImage(sourceImage, 0, 0, canvas.width, canvas.height);
  sourceTexture.dispose();
  const texture = new threeApi.CanvasTexture(canvas);
  texture.colorSpace = threeApi.SRGBColorSpace;
  // The FBX exporter already converts Sims 4 UVs to FBX coordinates. Keep the
  // TextureLoader default flip so the lower-half swatch content is sampled.
  texture.flipY = true;
  texture.channel = 0;
  texture.needsUpdate = true;
  object.traverse((child) => {
    if (!child.isMesh) return;
    const materials = Array.isArray(child.material) ? child.material : [child.material];
    materials.filter(Boolean).forEach((material) => {
      material.map = texture;
      material.alphaMap = null;
      material.color?.set?.(0xffffff);
      material.transparent = false;
      material.alphaTest = 0;
      material.opacity = 1;
      material.needsUpdate = true;
    });
  });
}

async function setModelVariant(variant) {
  if (variant === modelVariant.value || switchingVariant.value || !modelUrls.value[variant]) return;
  switchingVariant.value = true;
  const generation = previewGeneration;
  try {
    const rendered = await renderModel(modelUrls.value[variant], generation);
    if (!rendered || !isCurrentPreview(generation)) return;
    modelVariant.value = variant;
    message.value = variant === "half"
      ? "当前显示半脱模型 · 拖动旋转 · 滚轮缩放 · 右键平移"
      : "拖动旋转 · 滚轮缩放 · 右键平移";
  } catch (error) {
    if (isCurrentPreview(generation)) {
      message.value = error instanceof Error ? error.message : String(error);
    }
  } finally {
    if (isCurrentPreview(generation)) switchingVariant.value = false;
  }
}

function disposeViewer() {
  if (animationFrame) cancelAnimationFrame(animationFrame);
  resizeObserver?.disconnect();
  controls?.dispose();
  if (clothingObject) {
    disposeModelObject(clothingObject);
  }
  renderer?.dispose();
  renderer?.domElement?.remove();
  renderer = controls = scene = camera = resizeObserver = lightRig = mannequinObject = clothingObject = null;
}

async function renderModel(url, generation = previewGeneration) {
  await nextTick();
  if (!isCurrentPreview(generation)) return false;
  const THREE = await import("three");
  const [{ OrbitControls }, loaderModule] = await Promise.all([
    import("three/examples/jsm/controls/OrbitControls.js"),
    url.toLowerCase().split("?")[0].endsWith(".fbx")
      ? import("three/examples/jsm/loaders/FBXLoader.js")
      : import("three/examples/jsm/loaders/GLTFLoader.js"),
  ]);
  if (!isCurrentPreview(generation)) return false;
  const ModelLoader = loaderModule.FBXLoader || loaderModule.GLTFLoader;

  // Complete all async asset loading before replacing the shared viewer.
  // Results from an older item are discarded when the user clicks another one.
  // The clothing/item is the primary preview.  A missing or malformed HS2
  // mannequin must not prevent the exported object from rendering.
  const mannequinPromise = mannequinUrl.value
    ? cloneMannequinModel(mannequinUrl.value).catch(() => null)
    : Promise.resolve(null);
  const [model, loadedMannequin] = await Promise.all([
    new ModelLoader().loadAsync(url),
    mannequinPromise,
  ]);
  const modelObject = model?.scene || model;
  const isWorkbenchFbx = props.modelUrl && url.toLowerCase().split("?")[0].endsWith(".fbx");
  if (!isCurrentPreview(generation)) {
    disposeModelObject(modelObject);
    disposeModelObject(loadedMannequin);
    return false;
  }

  const host = canvasHost.value;
  if (!host) {
    disposeModelObject(modelObject);
    disposeModelObject(loadedMannequin);
    return false;
  }
  disposeViewer();
  threeApi = THREE;
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(34, 1, 0.01, 10000);
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: "high-performance" });
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  host.appendChild(renderer.domElement);
  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.07;
  controls.screenSpacePanning = true;
  applyBackground();
  applyLighting();
  clothingObject = modelObject;
  // The Workbench exporter writes TS4 GEOM coordinates in the source game's
  // unit scale.  HS2's reference body is centimeters, so an exported FBX is
  // intentionally one tenth of the mannequin until it is displayed here.
  if (isWorkbenchFbx) {
    clothingObject.scale.multiplyScalar(WORKBENCH_FBX_DISPLAY_SCALE);
    clothingObject.updateMatrixWorld(true);
    prepareWorkbenchModelVisibility(clothingObject, url);
    try {
      await applyWorkbenchTexture(clothingObject);
    } catch {
      // The mesh remains useful even when a particular PNG cannot be decoded
      // by the browser.
    }
  }
  scene.add(clothingObject);
  if (loadedMannequin) {
    mannequinObject = loadedMannequin;
    mannequinObject.name = "StarManagerMannequin";
    mannequinObject.visible = mannequinVisible.value;
    scene.add(mannequinObject);
    // Workbench FBX files are already exported in HS2 coordinates.  Rebinding
    // their optional source skeleton to the mannequin can collapse a rigged
    // mesh at the mannequin root, making the item appear to be missing.  The
    // item is therefore kept in its exported pose; item previews from the
    // mod-library path still use the normal skeleton binding behavior.
    if (!(props.modelUrl && url.toLowerCase().split("?")[0].endsWith(".fbx"))) {
      bindClothingToMannequin();
    }
  }
  frameVisibleModels();
  const resize = () => {
    const width = Math.max(host.clientWidth, 1);
    const height = Math.max(host.clientHeight, 1);
    const devicePixelRatio = Math.min(window.devicePixelRatio || 1, 2);
    const pixelBudget = expanded.value ? 2_500_000 : 1_500_000;
    const budgetPixelRatio = Math.sqrt(pixelBudget / (width * height));
    renderer.setPixelRatio(Math.max(0.75, Math.min(devicePixelRatio, budgetPixelRatio)));
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  };
  resizeObserver = new ResizeObserver(resize);
  resizeObserver.observe(host);
  resize();
  const animate = () => {
    controls.update();
    renderer.render(scene, camera);
    animationFrame = requestAnimationFrame(animate);
  };
  animate();
  return true;
}

async function captureScreenshot() {
  if (state.value !== "ready" || !scene || !camera) throw new Error("请先加载 3D 模型");
  const THREE = await import("three");
  const captureRenderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  captureRenderer.setPixelRatio(1);
  captureRenderer.setSize(512, 512, false);
  captureRenderer.outputColorSpace = THREE.SRGBColorSpace;
  captureRenderer.toneMapping = THREE.ACESFilmicToneMapping;
  captureRenderer.toneMappingExposure = 1.05;
  const previousAspect = camera.aspect;
  camera.aspect = 1;
  camera.updateProjectionMatrix();
  captureRenderer.render(scene, camera);
  const dataUrl = captureRenderer.domElement.toDataURL("image/png");
  camera.aspect = previousAspect;
  camera.updateProjectionMatrix();
  captureRenderer.dispose();
  captureRenderer.forceContextLoss();
  return dataUrl;
}

async function loadPreview() {
  if ((!props.itemId && !props.modelUrl && typeof props.previewLoader !== "function") || state.value === "loading") return;
  const generation = ++previewGeneration;
  state.value = "loading";
  message.value = "正在解析 Unity 网格…";
  try {
    let url = props.modelUrl;
    if (url) {
      modelUrls.value = { default: url, half: "" };
      mannequinUrl.value = props.mannequinUrl || "";
    } else {
      const result = typeof props.previewLoader === "function"
        ? await props.previewLoader()
        : await window.desktopApi.backendRequest(`/mods/items/${props.itemId}/model-preview`, { method: "POST", body: {} });
      if (!isCurrentPreview(generation)) return;
      if (!result?.ok) throw new Error(result?.error || "模型生成失败");
      url = `${window.desktopApi.backendBaseUrl}${result.url}`;
      modelUrls.value = {
        default: url,
        half: result.has_half_model && result.half_url ? `${window.desktopApi.backendBaseUrl}${result.half_url}` : "",
      };
      mannequinUrl.value = result.mannequin_url ? `${window.desktopApi.backendBaseUrl}${result.mannequin_url}` : "";
    }
    // Workbench previews start with the exported item alone.  This keeps the
    // garment/accessory geometry and its textures unambiguous while the FBX
    // pipeline is being inspected; the mannequin can still be enabled from
    // the preview control after the item is visible.
    mannequinVisible.value = !props.modelUrl;
    modelVariant.value = "default";
    message.value = "正在准备预览…";
    const rendered = await renderModel(url, generation);
    if (!rendered || !isCurrentPreview(generation)) return;
    state.value = "ready";
    await syncAppearanceListboxes();
    emit("ready-change", true);
    message.value = "拖动旋转 · 滚轮缩放 · 右键平移";
  } catch (error) {
    if (!isCurrentPreview(generation)) return;
    disposeViewer();
    state.value = "error";
    emit("ready-change", false);
    message.value = error instanceof Error ? error.message : String(error);
  }
}

watch(() => [props.itemId, props.modelUrl, props.textureUrl, props.mannequinUrl, props.previewKey], async () => {
  previewGeneration += 1;
  switchingVariant.value = false;
  setExpanded(false);
  disposeViewer();
  state.value = "idle";
  emit("ready-change", false);
  message.value = "";
  modelVariant.value = "default";
  modelUrls.value = { default: "", half: "" };
  mannequinUrl.value = "";
  mannequinVisible.value = !props.modelUrl;
  if (props.autoLoad) {
    await nextTick();
    loadPreview();
  }
});
onMounted(() => {
  if (props.autoLoad) loadPreview();
});
onBeforeUnmount(() => {
  previewGeneration += 1;
  setExpanded(false);
  disposeViewer();
});
defineExpose({ captureScreenshot, loadPreview });
</script>

<template>
  <section class="model-preview-card" :class="[`is-${state}`, { 'is-expanded': expanded }]">
    <div ref="canvasHost" class="model-preview-canvas">
      <button
        v-if="state === 'ready'"
        type="button"
        class="model-preview-expand-button"
        :aria-label="expanded ? '退出放大预览' : '放大 3D 预览'"
        :title="expanded ? '退出放大（Esc）' : '放大预览'"
        @click="setExpanded(!expanded)"
      >
        <svg v-if="!expanded" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M8.5 4H4v4.5M15.5 4H20v4.5M20 15.5V20h-4.5M8.5 20H4v-4.5" />
        </svg>
        <svg v-else viewBox="0 0 24 24" aria-hidden="true">
          <path d="M9 4v5H4M15 4v5h5M20 15h-5v5M4 15h5v5" />
        </svg>
      </button>
      <div v-if="state !== 'ready'" class="model-preview-placeholder">
        <LoadingAnimation v-if="state === 'loading'" class="model-preview-loading-animation" />
        <strong>{{ state === "error" ? "暂时无法显示" : "3D 模型预览" }}</strong>
        <p v-if="message">{{ message }}</p>
        <button type="button" :disabled="state === 'loading'" @click="loadPreview">
          {{ state === "loading" ? "解析中…" : state === "error" ? "重新尝试" : "加载模型" }}
        </button>
      </div>
    </div>
    <div v-if="state === 'ready'" class="model-preview-controls">
      <div v-if="mannequinUrl" class="model-preview-control-group mannequin-control">
        <span>模特</span>
        <div class="model-preview-binary-toggle" role="group" aria-label="模特显示">
          <button
            v-for="option in mannequinOptions"
            :key="String(option.value)"
            type="button"
            class="model-preview-toggle-option"
            :class="{ 'is-selected': mannequinVisible === option.value }"
            :aria-pressed="mannequinVisible === option.value"
            @click="setMannequinVisible(option.value)"
          >{{ option.label }}</button>
        </div>
      </div>
      <div v-if="modelUrls.half" class="model-preview-control-group model-variant-control">
        <span>状态</span>
        <div class="model-preview-binary-toggle" role="group" aria-label="模型状态" :aria-busy="switchingVariant">
          <button
            v-for="option in modelVariantOptions"
            :key="option.value"
            type="button"
            class="model-preview-toggle-option"
            :class="{ 'is-selected': modelVariant === option.value }"
            :aria-pressed="modelVariant === option.value"
            :disabled="switchingVariant"
            @click="setModelVariant(option.value)"
          >{{ option.label }}</button>
        </div>
      </div>
      <div class="model-preview-control-group background-control">
        <span>背景</span>
        <div
          ref="backgroundListbox"
          class="model-preview-option-list"
          role="listbox"
          aria-label="预览背景"
          aria-orientation="vertical"
          title="上下拖动或滚轮切换"
          @keydown="handleListboxKeydown($event, backgroundOptions, backgroundMode, setBackground)"
          @wheel="scrollListbox($event, backgroundOptions, backgroundMode, setBackground)"
          @pointerdown="startListboxDrag($event, backgroundOptions, backgroundMode, setBackground)"
          @pointermove="moveListboxDrag"
          @pointerup="finishListboxDrag"
          @pointercancel="finishListboxDrag($event, true)"
          @click.capture="suppressListboxClickAfterDrag"
        >
          <button
            v-for="option in backgroundOptions"
            :key="option.value"
            type="button"
            class="model-preview-option"
            :class="{ 'is-selected': backgroundMode === option.value }"
            role="option"
            :aria-selected="backgroundMode === option.value"
            :tabindex="backgroundMode === option.value ? 0 : -1"
            @click="setBackground(option.value)"
          >{{ option.label }}</button>
        </div>
        <div class="model-preview-list-stepper">
          <button
            v-for="step in listboxSteps"
            :key="step.direction"
            type="button"
            :aria-label="`${step.label}背景选项`"
            :disabled="listboxStepDisabled(backgroundOptions, backgroundMode, step.direction)"
            @click="stepListbox($event, backgroundOptions, backgroundMode, setBackground, step.direction)"
          ><span aria-hidden="true">{{ step.symbol }}</span></button>
        </div>
      </div>
      <div class="model-preview-control-group lighting-control">
        <span>灯光</span>
        <div
          ref="lightingListbox"
          class="model-preview-option-list"
          role="listbox"
          aria-label="预览灯光"
          aria-orientation="vertical"
          title="上下拖动或滚轮切换"
          @keydown="handleListboxKeydown($event, lightingOptions, lightingMode, setLighting)"
          @wheel="scrollListbox($event, lightingOptions, lightingMode, setLighting)"
          @pointerdown="startListboxDrag($event, lightingOptions, lightingMode, setLighting)"
          @pointermove="moveListboxDrag"
          @pointerup="finishListboxDrag"
          @pointercancel="finishListboxDrag($event, true)"
          @click.capture="suppressListboxClickAfterDrag"
        >
          <button
            v-for="option in lightingOptions"
            :key="option.value"
            type="button"
            class="model-preview-option"
            :class="{ 'is-selected': lightingMode === option.value }"
            role="option"
            :aria-selected="lightingMode === option.value"
            :tabindex="lightingMode === option.value ? 0 : -1"
            @click="setLighting(option.value)"
          >{{ option.label }}</button>
        </div>
        <div class="model-preview-list-stepper">
          <button
            v-for="step in listboxSteps"
            :key="step.direction"
            type="button"
            :aria-label="`${step.label}灯光选项`"
            :disabled="listboxStepDisabled(lightingOptions, lightingMode, step.direction)"
            @click="stepListbox($event, lightingOptions, lightingMode, setLighting, step.direction)"
          ><span aria-hidden="true">{{ step.symbol }}</span></button>
        </div>
      </div>
    </div>
    <div v-if="state === 'ready'" class="model-preview-hint">
      <div class="model-preview-hint-copy">
        <span class="model-preview-hint-label">3D</span>
        <span class="model-preview-hint-message">{{ message }}</span>
      </div>
    </div>
  </section>
</template>
