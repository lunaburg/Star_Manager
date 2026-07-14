<script setup>
import { nextTick, onBeforeUnmount, ref, watch } from "vue";

const props = defineProps({ itemId: { type: [Number, String], required: true } });
const emit = defineEmits(["ready-change"]);
const canvasHost = ref(null);
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

function handleExpandedKeydown(event) {
  if (event.key === "Escape") setExpanded(false);
}

function setExpanded(value) {
  expanded.value = Boolean(value);
  document.body.classList.toggle("model-preview-expanded", expanded.value);
  document.removeEventListener("keydown", handleExpandedKeydown);
  if (expanded.value) document.addEventListener("keydown", handleExpandedKeydown);
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
  if (lightingMode.value === "contour") {
    lightRig.add(new threeApi.HemisphereLight(0xdbe8ff, 0x08090b, 0.62));
    const key = new threeApi.DirectionalLight(0xffead7, 3.4);
    key.position.set(-3.5, 4.5, 5);
    lightRig.add(key);
    const rim = new threeApi.DirectionalLight(0x90c8ff, 4.1);
    rim.position.set(4.5, 2.5, -4);
    lightRig.add(rim);
    const edge = new threeApi.DirectionalLight(0xffffff, 1.1);
    edge.position.set(0, -2, -3);
    lightRig.add(edge);
  } else {
    lightRig.add(new threeApi.HemisphereLight(0xffffff, 0x66717c, 2.25));
    const key = new threeApi.DirectionalLight(0xffffff, 2.8);
    key.position.set(3, 5, 4);
    lightRig.add(key);
    const fill = new threeApi.DirectionalLight(0xfff4e8, 1.15);
    fill.position.set(-3, 1, 4);
    lightRig.add(fill);
    const rim = new threeApi.DirectionalLight(0xb8d8ff, 1.6);
    rim.position.set(-4, 2, -3);
    lightRig.add(rim);
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
    const fallbackRoot = mannequinBones.get("p_cf_body_00") || mannequinBones.get("cf_N_height") || mannequinBones.values().next().value;
    const bones = object.skeleton.bones.map((bone) => {
      if (mannequinBones.has(bone.name)) return mannequinBones.get(bone.name);
      const fallbackNames = Array.isArray(bone.userData?.fallbackBoneNames) ? bone.userData.fallbackBoneNames : [];
      return fallbackNames.map((name) => mannequinBones.get(name)).find(Boolean) || fallbackRoot;
    });
    if (bones.some((bone) => !bone)) return;
    const inverses = bones.map((bone) => bone.matrixWorld.clone().invert());
    const skeleton = new threeApi.Skeleton(bones, inverses);
    object.bind(skeleton, new threeApi.Matrix4());
    object.bindMode = threeApi.DetachedBindMode;
    object.normalizeSkinWeights();
    object.frustumCulled = false;
    boundMeshCount += 1;
  });
  clothingObject.updateMatrixWorld(true);
  return boundMeshCount;
}

async function setModelVariant(variant) {
  if (variant === modelVariant.value || switchingVariant.value || !modelUrls.value[variant]) return;
  switchingVariant.value = true;
  try {
    await renderModel(modelUrls.value[variant]);
    modelVariant.value = variant;
    message.value = variant === "half"
      ? "当前显示半脱模型 · 拖动旋转 · 滚轮缩放 · 右键平移"
      : "拖动旋转 · 滚轮缩放 · 右键平移";
  } catch (error) {
    message.value = error instanceof Error ? error.message : String(error);
  } finally {
    switchingVariant.value = false;
  }
}

function disposeViewer() {
  if (animationFrame) cancelAnimationFrame(animationFrame);
  resizeObserver?.disconnect();
  controls?.dispose();
  if (scene) {
    scene.traverse((object) => {
      object.geometry?.dispose?.();
      if (Array.isArray(object.material)) object.material.forEach((material) => material.dispose?.());
      else object.material?.dispose?.();
    });
  }
  renderer?.dispose();
  renderer?.domElement?.remove();
  renderer = controls = scene = camera = resizeObserver = lightRig = mannequinObject = clothingObject = null;
}

async function renderModel(url) {
  await nextTick();
  disposeViewer();
  const THREE = await import("three");
  threeApi = THREE;
  const [{ OrbitControls }, { GLTFLoader }] = await Promise.all([
    import("three/examples/jsm/controls/OrbitControls.js"),
    import("three/examples/jsm/loaders/GLTFLoader.js"),
  ]);
  const host = canvasHost.value;
  if (!host) return;
  scene = new THREE.Scene();
  applyBackground();
  camera = new THREE.PerspectiveCamera(34, 1, 0.01, 10000);
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  host.appendChild(renderer.domElement);
  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.07;
  controls.screenSpacePanning = true;
  applyLighting();
  const model = await new GLTFLoader().loadAsync(url);
  clothingObject = model.scene;
  scene.add(clothingObject);
  if (mannequinUrl.value) {
    const { FBXLoader } = await import("three/examples/jsm/loaders/FBXLoader.js");
    mannequinObject = await new FBXLoader().loadAsync(mannequinUrl.value);
    mannequinObject.name = "StarManagerMannequin";
    mannequinObject.visible = mannequinVisible.value;
    scene.add(mannequinObject);
    bindClothingToMannequin();
  }
  frameVisibleModels();
  const resize = () => {
    const width = Math.max(host.clientWidth, 1);
    const height = Math.max(host.clientHeight, 1);
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
  if (!props.itemId || state.value === "loading") return;
  state.value = "loading";
  message.value = "正在解析 Unity 网格…";
  try {
    const result = await window.desktopApi.backendRequest(`/mods/items/${props.itemId}/model-preview`, { method: "POST", body: {} });
    if (!result?.ok) throw new Error(result?.error || "模型生成失败");
    const url = `${window.desktopApi.backendBaseUrl}${result.url}`;
    modelUrls.value = {
      default: url,
      half: result.has_half_model && result.half_url ? `${window.desktopApi.backendBaseUrl}${result.half_url}` : "",
    };
    mannequinUrl.value = result.mannequin_url ? `${window.desktopApi.backendBaseUrl}${result.mannequin_url}` : "";
    mannequinVisible.value = true;
    modelVariant.value = "default";
    message.value = "正在准备预览…";
    await renderModel(url);
    state.value = "ready";
    emit("ready-change", true);
    message.value = "拖动旋转 · 滚轮缩放 · 右键平移";
  } catch (error) {
    disposeViewer();
    state.value = "error";
    emit("ready-change", false);
    message.value = error instanceof Error ? error.message : String(error);
  }
}

watch(() => props.itemId, () => {
  setExpanded(false);
  disposeViewer();
  state.value = "idle";
  emit("ready-change", false);
  message.value = "";
  modelVariant.value = "default";
  modelUrls.value = { default: "", half: "" };
  mannequinUrl.value = "";
  mannequinVisible.value = true;
});
onBeforeUnmount(() => {
  setExpanded(false);
  disposeViewer();
});
defineExpose({ captureScreenshot });
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
        <span class="model-preview-orbit" aria-hidden="true"><i></i></span>
        <strong>{{ state === "error" ? "暂时无法显示" : "3D 模型预览" }}</strong>
        <p v-if="message">{{ message }}</p>
        <button type="button" :disabled="state === 'loading'" @click="loadPreview">
          {{ state === "loading" ? "解析中…" : state === "error" ? "重新尝试" : "加载模型" }}
        </button>
      </div>
    </div>
    <div v-if="state === 'ready'" class="model-preview-controls">
      <div v-if="mannequinUrl" class="model-preview-control-group mannequin-control" aria-label="模特显示">
        <span>模特</span>
        <button type="button" :class="{ active: mannequinVisible }" :aria-pressed="mannequinVisible" @click="setMannequinVisible(true)">显示</button>
        <button type="button" :class="{ active: !mannequinVisible }" :aria-pressed="!mannequinVisible" @click="setMannequinVisible(false)">隐藏</button>
      </div>
      <div v-if="modelUrls.half" class="model-preview-control-group model-variant-control" aria-label="模型状态">
        <span>状态</span>
        <button type="button" :disabled="switchingVariant" :class="{ active: modelVariant === 'default' }" :aria-pressed="modelVariant === 'default'" @click="setModelVariant('default')">正常</button>
        <button type="button" :disabled="switchingVariant" :class="{ active: modelVariant === 'half' }" :aria-pressed="modelVariant === 'half'" @click="setModelVariant('half')">半脱</button>
      </div>
      <div class="model-preview-control-group" aria-label="预览背景">
        <span>背景</span>
        <button type="button" :class="{ active: backgroundMode === 'white' }" :aria-pressed="backgroundMode === 'white'" @click="setBackground('white')">白</button>
        <button type="button" :class="{ active: backgroundMode === 'black' }" :aria-pressed="backgroundMode === 'black'" @click="setBackground('black')">黑</button>
      </div>
      <div class="model-preview-control-group" aria-label="预览灯光">
        <span>灯光</span>
        <button type="button" :class="{ active: lightingMode === 'soft' }" :aria-pressed="lightingMode === 'soft'" @click="setLighting('soft')">柔光</button>
        <button type="button" :class="{ active: lightingMode === 'contour' }" :aria-pressed="lightingMode === 'contour'" @click="setLighting('contour')">轮廓</button>
      </div>
    </div>
    <div v-if="state === 'ready'" class="model-preview-hint"><span>3D</span>{{ message }}</div>
  </section>
</template>
