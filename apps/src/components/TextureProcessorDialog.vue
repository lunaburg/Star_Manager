<script setup>
import { computed, nextTick, onBeforeUnmount, reactive, ref, watch } from "vue";

const props = defineProps({
  open: { type: Boolean, default: false },
  projectId: { type: String, default: "" },
  projectPath: { type: String, default: "" },
  itemName: { type: String, default: "" }
});

const emit = defineEmits(["close", "exported"]);
const cropCanvas = ref(null);
const previewCanvas = ref(null);
const sourceImage = ref(null);
const source = reactive({ path: "", name: "", dataUrl: "" });
const zoom = ref(1);
const position = reactive({ x: 0, y: 0 });
const pointer = reactive({ active: false, id: -1, x: 0, y: 0 });
const outputResolution = ref(1024);
const pureTexture = ref(true);
const textureStrength = ref(1.25);
const selecting = ref(false);
const exporting = ref(false);
const error = ref("");
const exportResult = reactive({ path: "", width: 0, height: 0 });

const FRAME_SIZE = 640;
const PREVIEW_SIZE = 360;
const MIN_ZOOM = 1;
const MAX_ZOOM = 8;
const MIN_RESOLUTION = 64;
const MAX_RESOLUTION = 4096;
const RESOLUTION_PRESETS = [256, 512, 1024, 2048, 4096];
let previewFrame = 0;

const baseScale = computed(() => {
  const image = sourceImage.value;
  if (!image) return 1;
  return Math.max(FRAME_SIZE / image.naturalWidth, FRAME_SIZE / image.naturalHeight);
});

const renderedSize = computed(() => ({
  width: (sourceImage.value?.naturalWidth || FRAME_SIZE) * baseScale.value * zoom.value,
  height: (sourceImage.value?.naturalHeight || FRAME_SIZE) * baseScale.value * zoom.value
}));

const cropRegion = computed(() => {
  const image = sourceImage.value;
  if (!image) return null;
  const rendered = renderedSize.value;
  const left = (rendered.width - FRAME_SIZE) / 2 - position.x;
  const top = (rendered.height - FRAME_SIZE) / 2 - position.y;
  const sourceLeft = Math.max(0, left / rendered.width * image.naturalWidth);
  const sourceTop = Math.max(0, top / rendered.height * image.naturalHeight);
  const sourceSize = Math.min(
    image.naturalWidth - sourceLeft,
    image.naturalHeight - sourceTop,
    FRAME_SIZE / rendered.width * image.naturalWidth
  );
  return { left: sourceLeft, top: sourceTop, size: Math.max(1, sourceSize) };
});

const cropReadout = computed(() => {
  const crop = cropRegion.value;
  if (!crop) return "—";
  return `${Math.round(crop.left)}, ${Math.round(crop.top)} · ${Math.round(crop.size)} px`;
});

const normalizedResolution = computed(() => {
  const value = Math.round(Number(outputResolution.value) || 0);
  return Math.max(MIN_RESOLUTION, Math.min(MAX_RESOLUTION, value));
});

const isPowerOfTwo = computed(() => {
  const value = normalizedResolution.value;
  return value > 0 && (value & (value - 1)) === 0;
});

function clamp(value, minimum, maximum) {
  return Math.max(minimum, Math.min(maximum, value));
}

function clampPosition() {
  const rendered = renderedSize.value;
  const maxX = Math.max(0, (rendered.width - FRAME_SIZE) / 2);
  const maxY = Math.max(0, (rendered.height - FRAME_SIZE) / 2);
  position.x = clamp(position.x, -maxX, maxX);
  position.y = clamp(position.y, -maxY, maxY);
}

function drawCropCanvas() {
  const canvas = cropCanvas.value;
  const image = sourceImage.value;
  if (!canvas || !image) return;
  const context = canvas.getContext("2d");
  if (!context) return;
  const rendered = renderedSize.value;
  const x = (FRAME_SIZE - rendered.width) / 2 + position.x;
  const y = (FRAME_SIZE - rendered.height) / 2 + position.y;
  context.clearRect(0, 0, FRAME_SIZE, FRAME_SIZE);
  context.imageSmoothingEnabled = true;
  context.imageSmoothingQuality = "high";
  context.drawImage(image, x, y, rendered.width, rendered.height);
}

function renderTexture(target, size, neutralize = pureTexture.value) {
  const image = sourceImage.value;
  const crop = cropRegion.value;
  if (!target || !image || !crop) return false;
  target.width = size;
  target.height = size;
  const context = target.getContext("2d", { willReadFrequently: neutralize });
  if (!context) return false;
  context.clearRect(0, 0, size, size);
  context.imageSmoothingEnabled = true;
  context.imageSmoothingQuality = "high";
  context.drawImage(
    image,
    crop.left,
    crop.top,
    crop.size,
    crop.size,
    0,
    0,
    size,
    size
  );
  if (!neutralize) return true;

  const original = context.getImageData(0, 0, size, size);
  const grayscaleCanvas = document.createElement("canvas");
  grayscaleCanvas.width = size;
  grayscaleCanvas.height = size;
  const grayscaleContext = grayscaleCanvas.getContext("2d", { willReadFrequently: true });
  if (!grayscaleContext) return true;
  const grayscale = grayscaleContext.createImageData(size, size);
  for (let index = 0; index < original.data.length; index += 4) {
    const luminance = Math.round(
      original.data[index] * 0.2126
      + original.data[index + 1] * 0.7152
      + original.data[index + 2] * 0.0722
    );
    grayscale.data[index] = luminance;
    grayscale.data[index + 1] = luminance;
    grayscale.data[index + 2] = luminance;
    grayscale.data[index + 3] = 255;
  }
  grayscaleContext.putImageData(grayscale, 0, 0);

  const blurredCanvas = document.createElement("canvas");
  blurredCanvas.width = size;
  blurredCanvas.height = size;
  const blurredContext = blurredCanvas.getContext("2d", { willReadFrequently: true });
  if (!blurredContext) return true;
  const blurRadius = Math.max(3, Math.round(size * 0.018));
  blurredContext.filter = `blur(${blurRadius}px)`;
  blurredContext.drawImage(grayscaleCanvas, 0, 0);
  blurredContext.filter = "none";
  const blurred = blurredContext.getImageData(0, 0, size, size);

  const strength = Number(textureStrength.value) || 1;
  for (let index = 0; index < original.data.length; index += 4) {
    const detail = grayscale.data[index] - blurred.data[index];
    const neutral = clamp(Math.round(248 + detail * strength * 1.75), 0, 255);
    original.data[index] = neutral;
    original.data[index + 1] = neutral;
    original.data[index + 2] = neutral;
    original.data[index + 3] = 255;
  }
  context.putImageData(original, 0, 0);
  return true;
}

function schedulePreview() {
  if (!props.open || !sourceImage.value) return;
  cancelAnimationFrame(previewFrame);
  previewFrame = requestAnimationFrame(() => {
    drawCropCanvas();
    renderTexture(previewCanvas.value, PREVIEW_SIZE);
  });
}

function resetCrop() {
  zoom.value = 1;
  position.x = 0;
  position.y = 0;
  clampPosition();
  schedulePreview();
}

function updateZoom(value) {
  const next = clamp(Number(value) || MIN_ZOOM, MIN_ZOOM, MAX_ZOOM);
  const ratio = next / zoom.value;
  position.x *= ratio;
  position.y *= ratio;
  zoom.value = next;
  clampPosition();
  schedulePreview();
}

function nudgeZoom(delta) {
  updateZoom(Math.round((zoom.value + delta) * 20) / 20);
}

function pointerDown(event) {
  if (!sourceImage.value || exporting.value) return;
  pointer.active = true;
  pointer.id = event.pointerId;
  pointer.x = event.clientX;
  pointer.y = event.clientY;
  cropCanvas.value?.setPointerCapture?.(event.pointerId);
}

function pointerMove(event) {
  if (!pointer.active || pointer.id !== event.pointerId || !cropCanvas.value) return;
  const rect = cropCanvas.value.getBoundingClientRect();
  position.x += (event.clientX - pointer.x) * FRAME_SIZE / rect.width;
  position.y += (event.clientY - pointer.y) * FRAME_SIZE / rect.height;
  pointer.x = event.clientX;
  pointer.y = event.clientY;
  clampPosition();
  schedulePreview();
}

function pointerUp(event) {
  if (pointer.id !== event.pointerId) return;
  pointer.active = false;
  pointer.id = -1;
  cropCanvas.value?.releasePointerCapture?.(event.pointerId);
}

function handleWheel(event) {
  if (!exporting.value) nudgeZoom(event.deltaY < 0 ? 0.1 : -0.1);
}

function handleCropKeydown(event) {
  if (!sourceImage.value || exporting.value) return;
  const step = event.shiftKey ? 30 : 8;
  if (event.key === "ArrowLeft") position.x += step;
  else if (event.key === "ArrowRight") position.x -= step;
  else if (event.key === "ArrowUp") position.y += step;
  else if (event.key === "ArrowDown") position.y -= step;
  else return;
  event.preventDefault();
  clampPosition();
  schedulePreview();
}

function setResolution(value) {
  outputResolution.value = Number(value);
}

function normalizeResolution() {
  outputResolution.value = normalizedResolution.value;
}

function resetSource() {
  sourceImage.value = null;
  Object.assign(source, { path: "", name: "", dataUrl: "" });
  Object.assign(exportResult, { path: "", width: 0, height: 0 });
  error.value = "";
  zoom.value = 1;
  position.x = 0;
  position.y = 0;
}

async function selectSourceImage() {
  if (selecting.value || exporting.value) return;
  selecting.value = true;
  error.value = "";
  try {
    const selected = await window.desktopApi?.selectImageForCrop?.("选择要处理的贴图");
    if (!selected) return;
    if (!selected.ok) throw new Error(selected.error || "贴图读取失败");
    const image = new Image();
    await new Promise((resolve, reject) => {
      image.onload = resolve;
      image.onerror = () => reject(new Error("所选图片无法解码，请换用 PNG、JPG 或 WebP。"));
      image.src = selected.dataUrl;
    });
    sourceImage.value = image;
    Object.assign(source, {
      path: String(selected.path || ""),
      name: String(selected.name || "未命名贴图"),
      dataUrl: String(selected.dataUrl || "")
    });
    Object.assign(exportResult, { path: "", width: 0, height: 0 });
    await nextTick();
    resetCrop();
  } catch (caught) {
    error.value = caught?.message || String(caught);
  } finally {
    selecting.value = false;
  }
}

function suggestedFileName() {
  const sourceStem = source.name.replace(/\.[^.]+$/, "");
  const raw = String(props.itemName || sourceStem || "texture").trim();
  const safe = raw.replace(/[<>:"/\\|?*\u0000-\u001f]/g, "_").replace(/[. ]+$/g, "") || "texture";
  return `${safe}_texture_${normalizedResolution.value}.png`;
}

async function exportPng() {
  if (!sourceImage.value || exporting.value) return;
  exporting.value = true;
  error.value = "";
  Object.assign(exportResult, { path: "", width: 0, height: 0 });
  try {
    normalizeResolution();
    const output = document.createElement("canvas");
    if (!renderTexture(output, normalizedResolution.value)) throw new Error("贴图渲染失败");
    const dataUrl = output.toDataURL("image/png");
    const result = await window.desktopApi?.exportWorkbenchProcessedTexture?.({
      projectId: props.projectId,
      projectPath: props.projectPath,
      suggestedName: suggestedFileName(),
      dataUrl,
      width: normalizedResolution.value,
      height: normalizedResolution.value
    });
    if (!result?.ok) throw new Error(result?.error || "PNG 保存失败");
    if (result.canceled) return;
    Object.assign(exportResult, {
      path: String(result.path || ""),
      width: normalizedResolution.value,
      height: normalizedResolution.value
    });
    emit("exported", result);
  } catch (caught) {
    error.value = caught?.message || String(caught);
  } finally {
    exporting.value = false;
  }
}

function revealExport() {
  if (exportResult.path) window.desktopApi?.showItemInFolder?.(exportResult.path);
}

function closeDialog() {
  if (!selecting.value && !exporting.value) emit("close");
}

function handleWindowKeydown(event) {
  if (props.open && event.key === "Escape") closeDialog();
}

watch([pureTexture, textureStrength], schedulePreview);
watch(() => props.open, (open) => {
  if (!open) resetSource();
});

window.addEventListener("keydown", handleWindowKeydown);
onBeforeUnmount(() => {
  window.removeEventListener("keydown", handleWindowKeydown);
  cancelAnimationFrame(previewFrame);
});
</script>

<template>
  <div v-if="open" class="texture-dialog-backdrop" @click.self="closeDialog">
    <section class="texture-dialog" role="dialog" aria-modal="true" aria-labelledby="texture-processor-title">
      <header class="texture-dialog-header">
        <div>
          <span class="texture-kicker">ITEM TOOL / TEXTURE LAB</span>
          <h2 id="texture-processor-title">贴图净化与方形裁剪</h2>
          <p>为 SB3Utility 准备标准 PNG：选择 1:1 区域、输出尺寸，并可将有色底材还原为白色纯纹理。</p>
        </div>
        <button class="texture-close" type="button" :disabled="selecting || exporting" aria-label="关闭" @click="closeDialog">×</button>
      </header>

      <div v-if="!sourceImage" class="texture-empty">
        <div class="texture-empty-mark" aria-hidden="true">
          <svg viewBox="0 0 64 64"><path d="M8 12h48v40H8zM8 40l13-13 11 10 8-8 16 15M44 22h.01" /></svg>
        </div>
        <span>INPUT / JPG · PNG · WEBP</span>
        <h3>选择一张原始贴图</h3>
        <p>原文件不会被修改；完成后会通过保存窗口生成新的 PNG。</p>
        <button class="texture-primary" type="button" :disabled="selecting" @click="selectSourceImage">
          {{ selecting ? "正在读取…" : "选择图片" }}
        </button>
      </div>

      <div v-else class="texture-workspace">
        <div class="texture-crop-column">
          <div class="texture-section-label"><span>01</span><strong>选择 1:1 区域</strong><em>{{ cropReadout }}</em></div>
          <div class="texture-crop-stage">
            <div class="texture-crop-frame" :class="{ dragging: pointer.active }">
              <canvas
                ref="cropCanvas"
                :width="FRAME_SIZE"
                :height="FRAME_SIZE"
                tabindex="0"
                aria-label="方形贴图裁剪区域，可拖动图片或使用方向键调整"
                @pointerdown="pointerDown"
                @pointermove="pointerMove"
                @pointerup="pointerUp"
                @pointercancel="pointerUp"
                @wheel.prevent="handleWheel"
                @keydown="handleCropKeydown"
              />
              <div class="texture-crop-grid" aria-hidden="true"><i /><i /><b /><b /></div>
              <span class="texture-ratio">1 : 1</span>
            </div>
          </div>
          <div class="texture-zoom-control">
            <button type="button" :disabled="zoom <= MIN_ZOOM || exporting" aria-label="缩小" @click="nudgeZoom(-0.1)">−</button>
            <label>
              <span>缩放 <output>{{ Math.round(zoom * 100) }}%</output></span>
              <input :value="zoom" type="range" :min="MIN_ZOOM" :max="MAX_ZOOM" step="0.01" :disabled="exporting" @input="updateZoom($event.target.value)">
            </label>
            <button type="button" :disabled="zoom >= MAX_ZOOM || exporting" aria-label="放大" @click="nudgeZoom(0.1)">＋</button>
            <button class="texture-reset" type="button" :disabled="exporting" @click="resetCrop">居中</button>
          </div>
          <div class="texture-source-line">
            <div><span>源图</span><strong :title="source.path">{{ source.name }}</strong><small>{{ sourceImage.naturalWidth }} × {{ sourceImage.naturalHeight }}</small></div>
            <button type="button" :disabled="selecting || exporting" @click="selectSourceImage">更换</button>
          </div>
        </div>

        <aside class="texture-control-column">
          <div class="texture-section-label"><span>02</span><strong>检查输出</strong></div>
          <div class="texture-preview-shell" :class="{ neutral: pureTexture }">
            <canvas ref="previewCanvas" :width="PREVIEW_SIZE" :height="PREVIEW_SIZE" aria-label="处理后贴图预览" />
            <span>{{ pureTexture ? "PURE / WHITE" : "ORIGINAL COLOR" }}</span>
          </div>

          <label class="texture-mode-card">
            <input v-model="pureTexture" type="checkbox" :disabled="exporting">
            <span class="texture-mode-switch" aria-hidden="true"><i /></span>
            <span>
              <strong>纯纹理 · 去除基础颜色</strong>
              <small>中和色相与局部光照，以白色为底保留凹凸纤维。</small>
            </span>
          </label>

          <label v-if="pureTexture" class="texture-strength">
            <span><strong>纹理强度</strong><output>{{ Math.round(textureStrength * 100) }}%</output></span>
            <input v-model.number="textureStrength" type="range" min="0.5" max="2.5" step="0.05" :disabled="exporting">
          </label>

          <div class="texture-resolution">
            <div><strong>输出分辨率</strong><small :class="{ warning: !isPowerOfTwo }">{{ isPowerOfTwo ? "Unity 推荐的 2 次幂尺寸" : "可用，但不是 2 次幂尺寸" }}</small></div>
            <div class="texture-resolution-presets">
              <button
                v-for="preset in RESOLUTION_PRESETS"
                :key="preset"
                type="button"
                :class="{ active: normalizedResolution === preset }"
                :disabled="exporting"
                @click="setResolution(preset)"
              >{{ preset }}</button>
            </div>
            <label class="texture-custom-resolution">
              <span>自定义</span>
              <input v-model.number="outputResolution" type="number" :min="MIN_RESOLUTION" :max="MAX_RESOLUTION" step="1" :disabled="exporting" @blur="normalizeResolution">
              <em>× {{ normalizedResolution }} px</em>
            </label>
          </div>

          <div v-if="exportResult.path" class="texture-export-success" role="status">
            <span>✓</span>
            <div><strong>PNG 已保存</strong><small :title="exportResult.path">{{ exportResult.path }}</small></div>
            <button type="button" @click="revealExport">定位</button>
          </div>
          <div v-if="error" class="texture-error" role="alert"><span>!</span>{{ error }}</div>
        </aside>
      </div>

      <footer v-if="sourceImage" class="texture-dialog-actions">
        <p><strong>SB3Utility READY</strong><span>PNG · RGBA 8-bit · {{ normalizedResolution }} × {{ normalizedResolution }}</span></p>
        <div>
          <button type="button" :disabled="exporting" @click="closeDialog">关闭</button>
          <button class="texture-primary" type="button" :disabled="exporting" @click="exportPng">
            <span v-if="exporting" class="texture-spinner" aria-hidden="true" />
            {{ exporting ? "正在生成…" : "导出 PNG" }}
          </button>
        </div>
      </footer>
    </section>
  </div>
</template>

<style scoped>
.texture-dialog-backdrop { position: fixed; inset: 0; z-index: 88; display: grid; place-items: center; padding: 20px; background: rgb(25 31 31 / 66%); backdrop-filter: blur(7px); }
.texture-dialog { width: min(1080px, calc(100vw - 28px)); max-height: calc(100vh - 34px); overflow: auto; border: 2px solid #294e55; border-radius: 12px; background: #f7f3ec; box-shadow: 0 30px 90px rgb(9 26 29 / 40%); }
.texture-dialog-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; padding: 20px 22px 17px; border-bottom: 1px solid #b7cbc9; background: linear-gradient(105deg, #eff8f6 0 64%, #f5e8d7 64% 100%); }
.texture-kicker { color: #347b7b; font-family: var(--mono); font-size: 10px; font-weight: 900; letter-spacing: .14em; }
.texture-dialog-header h2 { margin: 5px 0 5px; color: #253d42; font-size: 25px; letter-spacing: -.035em; }
.texture-dialog-header p { max-width: 720px; margin: 0; color: #607579; font-size: 12px; line-height: 1.6; }
.texture-close { display: grid; width: 34px; height: 34px; flex: 0 0 34px; place-items: center; padding: 0; border: 1px solid #8ea9aa; border-radius: 50%; background: rgb(255 255 255 / 76%); color: #416b6e; box-shadow: none; font-size: 23px; line-height: 1; }
.texture-empty { display: grid; min-height: 430px; place-items: center; align-content: center; gap: 7px; padding: 36px; text-align: center; background: radial-gradient(circle at 50% 46%, rgb(117 170 174 / 14%), transparent 28%), repeating-linear-gradient(0deg, transparent 0 31px, rgb(46 93 99 / 5%) 31px 32px), #fbf9f4; }
.texture-empty-mark { display: grid; width: 86px; height: 86px; place-items: center; margin-bottom: 8px; border: 1px solid #83aeb0; border-radius: 50%; color: #397b7e; background: #eef8f6; box-shadow: 5px 6px 0 #d9c7b0; }
.texture-empty-mark svg { width: 46px; fill: none; stroke: currentColor; stroke-width: 1.5; }
.texture-empty > span { color: #7d9799; font-family: var(--mono); font-size: 9px; font-weight: 900; letter-spacing: .12em; }
.texture-empty h3 { margin: 2px 0; color: #294e55; font-size: 20px; }
.texture-empty p { margin: 0 0 12px; color: #728387; font-size: 11px; }
.texture-primary { border-color: #265f65; background: #347b7b; color: #fff; box-shadow: 3px 3px 0 #253d42; }
.texture-primary:hover:not(:disabled) { background: #286a6b; }
.texture-workspace { display: grid; grid-template-columns: minmax(460px, 1.25fr) minmax(330px, .75fr); min-height: 570px; }
.texture-crop-column,.texture-control-column { min-width: 0; padding: 18px 20px; }
.texture-crop-column { border-right: 1px solid #b7cbc9; background: repeating-linear-gradient(90deg, transparent 0 23px, rgb(47 100 103 / 5%) 23px 24px), #e9efeb; }
.texture-control-column { display: flex; flex-direction: column; gap: 12px; background: #fbf8f2; }
.texture-section-label { display: flex; align-items: center; gap: 8px; min-height: 24px; }
.texture-section-label > span { display: grid; width: 23px; height: 23px; place-items: center; border-radius: 50%; background: #315f65; color: #fff; font-family: var(--mono); font-size: 9px; font-weight: 900; }
.texture-section-label strong { color: #34575c; font-size: 12px; }
.texture-section-label em { margin-left: auto; color: #6f8588; font-family: var(--mono); font-size: 9px; font-style: normal; }
.texture-crop-stage { display: grid; min-height: 448px; place-items: center; padding: 16px 0 12px; }
.texture-crop-frame { position: relative; width: min(420px, 88%); aspect-ratio: 1; overflow: hidden; border: 5px solid #fff; border-radius: 4px; background: #2f3737; box-shadow: 0 0 0 2px #5e8f91, 12px 14px 0 rgb(198 177 149 / 58%), 0 24px 50px rgb(35 68 72 / 24%); }
.texture-crop-frame canvas { display: block; width: 100%; height: 100%; cursor: grab; touch-action: none; }
.texture-crop-frame.dragging canvas { cursor: grabbing; }
.texture-crop-frame canvas:focus-visible { outline: 3px solid #f0b879; outline-offset: -5px; }
.texture-crop-grid { position: absolute; inset: 0; pointer-events: none; }
.texture-crop-grid i,.texture-crop-grid b { position: absolute; display: block; background: rgb(255 255 255 / 50%); box-shadow: 0 0 1px rgb(0 0 0 / 35%); }
.texture-crop-grid i { top: 0; bottom: 0; width: 1px; }
.texture-crop-grid i:first-child { left: 33.333%; }
.texture-crop-grid i:nth-child(2) { left: 66.666%; }
.texture-crop-grid b { left: 0; right: 0; height: 1px; }
.texture-crop-grid b:nth-child(3) { top: 33.333%; }
.texture-crop-grid b:nth-child(4) { top: 66.666%; }
.texture-ratio { position: absolute; right: 9px; bottom: 9px; padding: 4px 8px; border: 1px solid rgb(255 255 255 / 68%); border-radius: 99px; color: #fff; background: rgb(31 44 44 / 65%); font-family: var(--mono); font-size: 9px; font-weight: 900; pointer-events: none; }
.texture-zoom-control { display: grid; grid-template-columns: 34px minmax(0, 1fr) 34px 50px; gap: 7px; align-items: end; }
.texture-zoom-control > button { height: 34px; padding: 0; box-shadow: none; }
.texture-zoom-control > button:not(.texture-reset) { font-size: 17px; }
.texture-zoom-control label { display: grid; gap: 5px; }
.texture-zoom-control label span { display: flex; justify-content: space-between; color: #587276; font-size: 10px; font-weight: 800; }
.texture-zoom-control output { font-family: var(--mono); }
.texture-zoom-control input { width: 100%; accent-color: #347b7b; }
.texture-reset { font-size: 10px; }
.texture-source-line { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 10px; align-items: center; margin-top: 11px; padding: 9px 10px; border: 1px solid #b9ceca; border-radius: 5px; background: rgb(255 255 255 / 68%); }
.texture-source-line > div { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; gap: 7px; min-width: 0; align-items: center; }
.texture-source-line span,.texture-source-line small { color: #71898b; font-size: 9px; }
.texture-source-line strong { overflow: hidden; color: #365f64; font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
.texture-source-line button { height: 28px; padding: 0 9px; box-shadow: none; font-size: 9px; }
.texture-preview-shell { position: relative; width: min(280px, 76%); align-self: center; aspect-ratio: 1; overflow: hidden; border: 1px solid #b3a994; border-radius: 5px; background: conic-gradient(#e7e4dd 25%, #fff 0 50%, #e7e4dd 0 75%, #fff 0) 0 0 / 18px 18px; box-shadow: 8px 9px 0 #d8c7ae; }
.texture-preview-shell.neutral { border-color: #7fa6a4; box-shadow: 8px 9px 0 #c4d9d4; }
.texture-preview-shell canvas { display: block; width: 100%; height: 100%; }
.texture-preview-shell > span { position: absolute; left: 7px; bottom: 7px; padding: 4px 6px; border-radius: 3px; color: #fff; background: rgb(35 57 59 / 68%); font-family: var(--mono); font-size: 8px; font-weight: 900; letter-spacing: .08em; }
.texture-mode-card { display: grid; grid-template-columns: auto auto minmax(0, 1fr); gap: 9px; align-items: center; padding: 11px; border: 1px solid #aac8c2; border-radius: 6px; background: #eef7f3; cursor: pointer; }
.texture-mode-card > input { position: absolute; opacity: 0; pointer-events: none; }
.texture-mode-switch { position: relative; width: 34px; height: 19px; border-radius: 99px; background: #9aa9a7; transition: background .16s ease; }
.texture-mode-switch i { position: absolute; top: 3px; left: 3px; width: 13px; height: 13px; border-radius: 50%; background: #fff; box-shadow: 0 1px 3px rgb(0 0 0 / 20%); transition: transform .16s ease; }
.texture-mode-card > input:checked + .texture-mode-switch { background: #347b70; }
.texture-mode-card > input:checked + .texture-mode-switch i { transform: translateX(15px); }
.texture-mode-card > span:last-child { display: grid; gap: 2px; min-width: 0; }
.texture-mode-card strong { color: #315d59; font-size: 11px; }
.texture-mode-card small { color: #6e8581; font-size: 9px; line-height: 1.4; }
.texture-strength { display: grid; gap: 6px; padding: 0 2px; }
.texture-strength > span { display: flex; justify-content: space-between; color: #4e6f70; font-size: 10px; }
.texture-strength output { font-family: var(--mono); font-weight: 900; }
.texture-strength input { width: 100%; accent-color: #347b70; }
.texture-resolution { display: grid; gap: 8px; padding: 11px; border: 1px solid #d4c6ae; border-radius: 6px; background: #fffdf8; }
.texture-resolution > div:first-child { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
.texture-resolution strong { color: #5f5545; font-size: 11px; }
.texture-resolution small { color: #688b7f; font-size: 8px; }
.texture-resolution small.warning { color: #a06b32; }
.texture-resolution-presets { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 4px; }
.texture-resolution-presets button { height: 28px; min-width: 0; padding: 0 2px; border-color: #cfc3af; background: #f8f4ec; box-shadow: none; color: #7a6b55; font-family: var(--mono); font-size: 8px; }
.texture-resolution-presets button.active { border-color: #347b7b; background: #e7f4f1; color: #286a6b; box-shadow: inset 0 -2px #347b7b; }
.texture-custom-resolution { display: grid; grid-template-columns: auto 82px minmax(0, 1fr); gap: 7px; align-items: center; }
.texture-custom-resolution span,.texture-custom-resolution em { color: #80715d; font-size: 9px; font-style: normal; }
.texture-custom-resolution input { width: 82px; height: 30px; padding: 0 6px; border: 1px solid #cbbda6; border-radius: 4px; font-family: var(--mono); font-size: 10px; }
.texture-export-success,.texture-error { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; gap: 8px; align-items: center; padding: 9px 10px; border-radius: 5px; }
.texture-export-success { border: 1px solid #8ebda9; background: #eff9f3; color: #39745b; }
.texture-export-success > span,.texture-error > span { display: grid; width: 20px; height: 20px; place-items: center; border-radius: 50%; color: #fff; font-size: 10px; font-weight: 900; }
.texture-export-success > span { background: #4e9274; }
.texture-export-success > div { display: grid; min-width: 0; gap: 2px; }
.texture-export-success strong { font-size: 10px; }
.texture-export-success small { overflow: hidden; font-family: var(--mono); font-size: 8px; text-overflow: ellipsis; white-space: nowrap; }
.texture-export-success button { height: 27px; padding: 0 8px; box-shadow: none; font-size: 9px; }
.texture-error { grid-template-columns: auto minmax(0, 1fr); border: 1px solid #cf8e87; background: #fff1ef; color: #9b4942; font-size: 10px; }
.texture-error > span { background: #b65c53; }
.texture-dialog-actions { display: flex; align-items: center; justify-content: space-between; gap: 18px; padding: 13px 20px; border-top: 1px solid #b7cbc9; background: #eef4f1; }
.texture-dialog-actions p { display: grid; gap: 2px; margin: 0; }
.texture-dialog-actions p strong { color: #347b70; font-family: var(--mono); font-size: 9px; letter-spacing: .1em; }
.texture-dialog-actions p span { color: #698083; font-size: 9px; }
.texture-dialog-actions > div { display: flex; gap: 8px; }
.texture-dialog-actions button,.texture-empty button { min-height: 34px; padding: 0 13px; font-size: 10px; font-weight: 900; }
.texture-spinner { width: 12px; height: 12px; border: 2px solid rgb(255 255 255 / 38%); border-top-color: #fff; border-radius: 50%; animation: texture-spin .7s linear infinite; }
@keyframes texture-spin { to { transform: rotate(360deg); } }
@media (max-width: 820px) {
  .texture-workspace { grid-template-columns: 1fr; }
  .texture-crop-column { border-right: 0; border-bottom: 1px solid #b7cbc9; }
  .texture-crop-stage { min-height: 380px; }
  .texture-crop-frame { width: min(360px, 88%); }
  .texture-preview-shell { width: min(300px, 80%); }
}
@media (max-width: 520px) {
  .texture-dialog-header p { display: none; }
  .texture-crop-column,.texture-control-column { padding: 14px; }
  .texture-crop-stage { min-height: 330px; }
  .texture-source-line > div { grid-template-columns: auto minmax(0, 1fr); }
  .texture-source-line small { display: none; }
  .texture-dialog-actions { align-items: stretch; flex-direction: column; }
  .texture-dialog-actions > div { justify-content: flex-end; }
}
</style>
