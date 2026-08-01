<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";

const props = defineProps({
  open: { type: Boolean, default: false },
  imageData: { type: String, default: "" },
  imageName: { type: String, default: "" },
  busy: { type: Boolean, default: false }
});

const emit = defineEmits(["cancel", "confirm"]);
const canvas = ref(null);
const image = ref(null);
const loadError = ref("");
const zoom = ref(1);
const position = reactive({ x: 0, y: 0 });
const pointer = reactive({ active: false, id: -1, x: 0, y: 0 });

const FRAME_WIDTH = 504;
const FRAME_HEIGHT = 704;
const MIN_ZOOM = 1;
const MAX_ZOOM = 4;

const baseScale = computed(() => {
  if (!image.value) return 1;
  return Math.max(FRAME_WIDTH / image.value.naturalWidth, FRAME_HEIGHT / image.value.naturalHeight);
});

const renderedSize = computed(() => ({
  width: (image.value?.naturalWidth || FRAME_WIDTH) * baseScale.value * zoom.value,
  height: (image.value?.naturalHeight || FRAME_HEIGHT) * baseScale.value * zoom.value
}));

const cropRegion = computed(() => {
  if (!image.value) return null;
  const rendered = renderedSize.value;
  const left = (rendered.width - FRAME_WIDTH) / 2 - position.x;
  const top = (rendered.height - FRAME_HEIGHT) / 2 - position.y;
  return {
    left: Math.max(0, left / rendered.width),
    top: Math.max(0, top / rendered.height),
    width: Math.min(1, FRAME_WIDTH / rendered.width),
    height: Math.min(1, FRAME_HEIGHT / rendered.height)
  };
});

const outputSize = computed(() => {
  if (!image.value || !cropRegion.value) return "";
  const width = Math.max(1, Math.round(image.value.naturalWidth * cropRegion.value.width));
  const height = Math.max(1, Math.round(image.value.naturalHeight * cropRegion.value.height));
  return `${width} × ${height}`;
});

function clampPosition() {
  const rendered = renderedSize.value;
  const maxX = Math.max(0, (rendered.width - FRAME_WIDTH) / 2);
  const maxY = Math.max(0, (rendered.height - FRAME_HEIGHT) / 2);
  position.x = Math.max(-maxX, Math.min(maxX, position.x));
  position.y = Math.max(-maxY, Math.min(maxY, position.y));
}

function draw() {
  const target = canvas.value;
  const source = image.value;
  if (!target || !source) return;
  const context = target.getContext("2d");
  if (!context) return;
  const rendered = renderedSize.value;
  const x = (FRAME_WIDTH - rendered.width) / 2 + position.x;
  const y = (FRAME_HEIGHT - rendered.height) / 2 + position.y;
  context.clearRect(0, 0, FRAME_WIDTH, FRAME_HEIGHT);
  context.drawImage(source, x, y, rendered.width, rendered.height);
}

function resetCrop() {
  zoom.value = 1;
  position.x = 0;
  position.y = 0;
  clampPosition();
  draw();
}

function updateZoom(value) {
  const next = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, Number(value) || MIN_ZOOM));
  const ratio = next / zoom.value;
  position.x *= ratio;
  position.y *= ratio;
  zoom.value = next;
  clampPosition();
  draw();
}

function nudgeZoom(delta) {
  updateZoom(Math.round((zoom.value + delta) * 20) / 20);
}

function pointerDown(event) {
  if (props.busy || !image.value) return;
  pointer.active = true;
  pointer.id = event.pointerId;
  pointer.x = event.clientX;
  pointer.y = event.clientY;
  canvas.value?.setPointerCapture?.(event.pointerId);
}

function pointerMove(event) {
  if (!pointer.active || pointer.id !== event.pointerId || !canvas.value) return;
  const rect = canvas.value.getBoundingClientRect();
  position.x += (event.clientX - pointer.x) * FRAME_WIDTH / rect.width;
  position.y += (event.clientY - pointer.y) * FRAME_HEIGHT / rect.height;
  pointer.x = event.clientX;
  pointer.y = event.clientY;
  clampPosition();
  draw();
}

function pointerUp(event) {
  if (pointer.id !== event.pointerId) return;
  pointer.active = false;
  pointer.id = -1;
  canvas.value?.releasePointerCapture?.(event.pointerId);
}

function handleWheel(event) {
  if (props.busy) return;
  nudgeZoom(event.deltaY < 0 ? 0.1 : -0.1);
}

function handleCropKeydown(event) {
  if (props.busy || !image.value) return;
  const step = event.shiftKey ? 30 : 10;
  if (event.key === "ArrowLeft") position.x += step;
  else if (event.key === "ArrowRight") position.x -= step;
  else if (event.key === "ArrowUp") position.y += step;
  else if (event.key === "ArrowDown") position.y -= step;
  else return;
  event.preventDefault();
  clampPosition();
  draw();
}

function confirmCrop() {
  if (!cropRegion.value || props.busy) return;
  emit("confirm", { ...cropRegion.value });
}

function cancelCrop() {
  if (!props.busy) emit("cancel");
}

function handleWindowKeydown(event) {
  if (props.open && event.key === "Escape") cancelCrop();
}

watch(
  () => props.imageData,
  async (source) => {
    image.value = null;
    loadError.value = "";
    if (!source) return;
    const nextImage = new Image();
    nextImage.onload = async () => {
      image.value = nextImage;
      await nextTick();
      resetCrop();
    };
    nextImage.onerror = () => {
      loadError.value = "所选图片无法预览，请重新选择。";
    };
    nextImage.src = source;
  },
  { immediate: true }
);

onMounted(() => window.addEventListener("keydown", handleWindowKeydown));
onBeforeUnmount(() => window.removeEventListener("keydown", handleWindowKeydown));
</script>

<template>
  <div v-if="open" class="cropper-backdrop" @click.self="cancelCrop">
    <section class="cropper-panel" role="dialog" aria-modal="true" aria-labelledby="card-cover-crop-title">
      <header class="cropper-header">
        <div>
          <span class="cropper-kicker">人物卡封面 · 63:88</span>
          <h2 id="card-cover-crop-title">选择封面区域</h2>
          <p>拖动图片调整位置，滚轮或滑杆控制缩放。确认后保留裁剪区域的原始分辨率。</p>
        </div>
        <button type="button" class="cropper-close" :disabled="busy" aria-label="关闭裁剪" @click="cancelCrop">×</button>
      </header>

      <div class="cropper-workspace">
        <div class="cropper-stage">
          <div class="cropper-frame" :class="{ dragging: pointer.active }">
            <canvas
              ref="canvas"
              :width="FRAME_WIDTH"
              :height="FRAME_HEIGHT"
              tabindex="0"
              aria-label="封面裁剪区域，可拖动图片或使用方向键调整"
              @pointerdown="pointerDown"
              @pointermove="pointerMove"
              @pointerup="pointerUp"
              @pointercancel="pointerUp"
              @wheel.prevent="handleWheel"
              @keydown="handleCropKeydown"
            />
            <div class="cropper-grid" aria-hidden="true"><i /><i /><b /><b /></div>
            <span class="cropper-ratio">63:88</span>
          </div>
        </div>

        <aside class="cropper-controls">
          <div class="cropper-source">
            <span>所选图片</span>
            <strong :title="imageName">{{ imageName || '未命名图片' }}</strong>
            <small v-if="image">{{ image.naturalWidth }} × {{ image.naturalHeight }}</small>
          </div>
          <div class="cropper-output">
            <span>预计封面尺寸</span>
            <strong>{{ outputSize || '正在读取…' }}</strong>
            <small>不强制缩放为 252 × 352</small>
          </div>
          <label class="cropper-zoom">
            <span><strong>缩放</strong><output>{{ Math.round(zoom * 100) }}%</output></span>
            <div>
              <button type="button" :disabled="busy || zoom <= MIN_ZOOM" aria-label="缩小" @click="nudgeZoom(-0.1)">−</button>
              <input
                :value="zoom"
                type="range"
                :min="MIN_ZOOM"
                :max="MAX_ZOOM"
                step="0.01"
                :disabled="busy"
                aria-label="封面缩放"
                @input="updateZoom($event.target.value)"
              >
              <button type="button" :disabled="busy || zoom >= MAX_ZOOM" aria-label="放大" @click="nudgeZoom(0.1)">＋</button>
            </div>
          </label>
          <button type="button" class="cropper-reset" :disabled="busy" @click="resetCrop">恢复居中</button>
          <p class="cropper-tip">提示：按住 Shift + 方向键可更快移动。</p>
        </aside>
      </div>

      <div v-if="loadError" class="cropper-error" role="alert">{{ loadError }}</div>
      <footer class="cropper-actions">
        <button type="button" :disabled="busy" @click="cancelCrop">取消</button>
        <button type="button" class="cropper-confirm" :disabled="busy || !image || Boolean(loadError)" @click="confirmCrop">
          {{ busy ? '正在写入人物卡…' : '使用此裁剪区域' }}
        </button>
      </footer>
    </section>
  </div>
</template>

<style scoped>
.cropper-backdrop {
  position: fixed;
  inset: 0;
  z-index: 90;
  display: grid;
  place-items: center;
  padding: 22px;
  background: rgb(27 23 22 / 58%);
  backdrop-filter: blur(5px);
}

.cropper-panel {
  width: min(830px, calc(100vw - 32px));
  max-height: calc(100vh - 36px);
  overflow: auto;
  border: 2px solid var(--line-strong);
  border-radius: 14px;
  background: var(--surface-clean);
  box-shadow: 0 28px 80px rgb(31 24 22 / 32%);
}

.cropper-header {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  padding: 20px 22px 17px;
  border-bottom: 1px solid var(--line);
}

.cropper-kicker {
  color: var(--teal);
  font-size: 11px;
  font-weight: 900;
  letter-spacing: .12em;
}

.cropper-header h2 { margin: 3px 0 5px; font-size: 24px; }
.cropper-header p { margin: 0; color: var(--muted); font-size: 13px; }

.cropper-close {
  width: 34px;
  height: 34px;
  padding: 0;
  border-radius: 50%;
  font-size: 24px;
  line-height: 1;
}

.cropper-workspace {
  display: grid;
  grid-template-columns: minmax(290px, 1fr) 230px;
  gap: 22px;
  padding: 22px;
  background:
    linear-gradient(90deg, rgb(231 169 132 / 8%) 1px, transparent 1px),
    linear-gradient(rgb(231 169 132 / 8%) 1px, transparent 1px),
    #f8f4f1;
  background-size: 18px 18px;
}

.cropper-stage { display: grid; place-items: center; min-height: 474px; }

.cropper-frame {
  position: relative;
  width: min(315px, 100%);
  aspect-ratio: 63 / 88;
  overflow: hidden;
  border: 4px solid #fff;
  border-radius: 8px;
  background: #282727;
  box-shadow: 0 0 0 2px #d69069, 0 18px 42px rgb(111 65 42 / 28%);
}

.cropper-frame canvas {
  display: block;
  width: 100%;
  height: 100%;
  cursor: grab;
  touch-action: none;
}

.cropper-frame.dragging canvas { cursor: grabbing; }
.cropper-frame canvas:focus-visible { outline: 3px solid var(--teal); outline-offset: -5px; }

.cropper-grid { position: absolute; inset: 0; pointer-events: none; }
.cropper-grid i, .cropper-grid b { position: absolute; display: block; background: rgb(255 255 255 / 52%); box-shadow: 0 0 1px rgb(0 0 0 / 30%); }
.cropper-grid i { top: 0; bottom: 0; width: 1px; }
.cropper-grid i:first-child { left: 33.333%; }
.cropper-grid i:nth-child(2) { left: 66.666%; }
.cropper-grid b { left: 0; right: 0; height: 1px; }
.cropper-grid b:nth-child(3) { top: 33.333%; }
.cropper-grid b:nth-child(4) { top: 66.666%; }

.cropper-ratio {
  position: absolute;
  right: 9px;
  bottom: 9px;
  padding: 4px 7px;
  border: 1px solid rgb(255 255 255 / 60%);
  border-radius: 99px;
  color: #fff;
  background: rgb(24 22 22 / 55%);
  font-size: 10px;
  font-weight: 900;
  letter-spacing: .08em;
  pointer-events: none;
}

.cropper-controls { display: flex; flex-direction: column; gap: 12px; }
.cropper-source, .cropper-output { display: grid; gap: 3px; padding: 13px; border: 1px solid var(--line); border-radius: 8px; background: rgb(255 255 255 / 82%); }
.cropper-source span, .cropper-output span { color: var(--muted); font-size: 11px; font-weight: 800; }
.cropper-source strong { overflow: hidden; font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
.cropper-source small, .cropper-output small { color: var(--muted); font-size: 11px; }
.cropper-output { border-left: 4px solid var(--teal); }
.cropper-output strong { color: var(--teal); font-size: 22px; }

.cropper-zoom { display: grid; gap: 8px; padding-top: 4px; }
.cropper-zoom > span { display: flex; justify-content: space-between; font-size: 12px; }
.cropper-zoom output { color: var(--muted); font-weight: 800; }
.cropper-zoom > div { display: grid; grid-template-columns: 34px 1fr 34px; align-items: center; gap: 7px; }
.cropper-zoom button { width: 34px; height: 34px; padding: 0; font-size: 18px; }
.cropper-zoom input { width: 100%; accent-color: var(--teal); }
.cropper-reset { width: 100%; }
.cropper-tip { margin: 0; color: var(--muted); font-size: 11px; line-height: 1.5; }
.cropper-error { margin: 0 22px 15px; padding: 10px; border: 1px solid #bd5353; border-radius: 6px; color: #972b2b; background: #fff0f0; font-size: 12px; font-weight: 800; }

.cropper-actions {
  display: flex;
  justify-content: flex-end;
  gap: 9px;
  padding: 15px 22px;
  border-top: 1px solid var(--line);
}

.cropper-confirm { color: #fff; border-color: #106f68; background: #12857c; }
.cropper-confirm:hover:not(:disabled) { background: #0d716a; }

@media (max-width: 690px) {
  .cropper-workspace { grid-template-columns: 1fr; }
  .cropper-stage { min-height: 0; }
  .cropper-controls { display: grid; grid-template-columns: 1fr 1fr; }
  .cropper-zoom, .cropper-reset, .cropper-tip { grid-column: 1 / -1; }
}
</style>
