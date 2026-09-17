<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import LazyThumbnail from "./LazyThumbnail.vue";

const props = defineProps({
  rows: { type: Array, default: () => [] },
  selectedId: { type: String, default: "" },
  eagerCount: { type: Number, default: 24 },
  variant: { type: String, default: "clothes" },
  aspectWidth: { type: Number, default: 252 },
  aspectHeight: { type: Number, default: 352 },
  ariaLabel: { type: String, default: "服装卡列表" }
});

const emit = defineEmits(["card-click"]);

const canvas = ref(null);
const viewport = reactive({ scrollTop: 0, height: 0, width: 0 });
const metrics = reactive({ columns: 5, cardWidth: 168, cardHeight: 235, rowHeight: 251, gap: 16 });

const GRID_PADDING = 18;
const GRID_GAP = 16;
const MAX_COLUMNS = 5;
const COMPACT_COLUMNS = 4;
const MIN_COMPACT_CARD_WIDTH = 128;

let scrollParent = null;
let resizeObserver = null;
let viewportRaf = 0;

function scheduleViewportUpdate() {
  if (viewportRaf) return;
  viewportRaf = window.requestAnimationFrame(() => {
    viewportRaf = 0;
    updateViewport();
  });
}

function readCssNumber(styles, property, fallback) {
  const value = Number.parseFloat(styles.getPropertyValue(property));
  return Number.isFinite(value) ? value : fallback;
}

function updateViewport() {
  if (!scrollParent) return;
  viewport.scrollTop = scrollParent.scrollTop;
  viewport.height = scrollParent.clientHeight;
  viewport.width = scrollParent.clientWidth;

  const styles = window.getComputedStyle(scrollParent);
  const padding = readCssNumber(styles, "--card-grid-padding", GRID_PADDING);
  const gap = readCssNumber(styles, "--card-grid-gap-x", GRID_GAP);
  const preferredCardWidth = readCssNumber(styles, "--card-width", 168);
  const contentWidth = Math.max(0, viewport.width - padding * 2);
  const preferredColumns = Math.floor((contentWidth + gap) / (preferredCardWidth + gap));
  const compactColumns = Math.floor((contentWidth + gap) / (MIN_COMPACT_CARD_WIDTH + gap));
  const columns = Math.max(
    1,
    Math.min(MAX_COLUMNS, Math.max(preferredColumns, Math.min(COMPACT_COLUMNS, compactColumns)))
  );
  const availableCardWidth = (contentWidth - (columns - 1) * gap) / columns;
  const cardWidth = Math.max(1, Math.min(preferredCardWidth, availableCardWidth));
  const previewHeight = Math.ceil(cardWidth * props.aspectHeight / props.aspectWidth);
  const cardHeight = props.variant === "scene"
    ? previewHeight + 24
    : previewHeight;

  metrics.columns = columns;
  metrics.cardWidth = cardWidth;
  metrics.cardHeight = cardHeight;
  metrics.rowHeight = cardHeight + gap;
  metrics.gap = gap;
}

const rowCount = computed(() => Math.ceil(props.rows.length / metrics.columns));
const totalHeight = computed(() => (
  Math.max(1, rowCount.value * metrics.rowHeight - metrics.gap)
));
const startRow = computed(() => Math.max(
  0,
  Math.floor(Math.max(0, viewport.scrollTop) / metrics.rowHeight) - 4
));
const endRow = computed(() => Math.min(
  rowCount.value,
  Math.ceil((viewport.scrollTop + viewport.height) / metrics.rowHeight) + 4
));
const visibleEntries = computed(() => {
  const start = startRow.value * metrics.columns;
  const end = Math.min(props.rows.length, endRow.value * metrics.columns);
  return props.rows.slice(start, end).map((row, index) => ({ row, index: start + index }));
});
const offsetTop = computed(() => startRow.value * metrics.rowHeight);

function isSelected(row) {
  return String(props.selectedId || "") === String(row?.relativePath || row?.id || "");
}

function bindViewport() {
  scrollParent = canvas.value?.parentElement || null;
  if (!scrollParent) return;
  scrollParent.addEventListener("scroll", scheduleViewportUpdate, { passive: true });
  resizeObserver = typeof ResizeObserver === "function"
    ? new ResizeObserver(scheduleViewportUpdate)
    : null;
  resizeObserver?.observe(scrollParent);
  updateViewport();
}

onMounted(() => {
  bindViewport();
  window.addEventListener("resize", scheduleViewportUpdate, { passive: true });
});

onBeforeUnmount(() => {
  if (viewportRaf) window.cancelAnimationFrame(viewportRaf);
  scrollParent?.removeEventListener("scroll", scheduleViewportUpdate);
  resizeObserver?.disconnect();
  window.removeEventListener("resize", scheduleViewportUpdate);
});

watch(
  () => props.rows.length,
  () => {
    void nextTick(updateViewport);
  }
);
</script>

<template>
  <div
    ref="canvas"
    class="clothes-card-virtual-canvas"
    :style="{ height: `${Math.max(1, totalHeight)}px` }"
  >
    <div
      class="clothes-card-virtual-grid"
      role="list"
      :aria-label="props.ariaLabel"
      :style="{
        transform: `translateY(${offsetTop}px)`,
        gridTemplateColumns: `repeat(${metrics.columns}, ${metrics.cardWidth}px)`,
        gridAutoRows: `${metrics.cardHeight}px`,
        columnGap: `${metrics.gap}px`,
        rowGap: `${metrics.gap}px`,
        justifyContent: 'space-between'
      }"
    >
      <button
        v-for="entry in visibleEntries"
        :key="entry.row.id"
        v-memo="[entry.row, isSelected(entry.row)]"
        type="button"
        class="char-card clothes-card-tile"
        :class="{ selected: isSelected(entry.row), 'scene-card-tile': props.variant === 'scene' }"
        :aria-pressed="isSelected(entry.row)"
        role="listitem"
        @click="emit('card-click', entry.row)"
      >
        <span v-if="isSelected(entry.row)" class="clothes-card-check">✓</span>
        <span class="portrait clothes-card-preview" :class="{ 'scene-card-preview': props.variant === 'scene' }">
          <LazyThumbnail
            :src="entry.row.thumbnailUrl"
            :alt="entry.row.name + ' preview'"
            :eager="entry.index < props.eagerCount"
          />
        </span>
        <span class="card-caption clothes-card-caption" :class="{ 'scene-card-caption': props.variant === 'scene' }">
          <strong v-card-name-scroll><span class="card-name-text">{{ entry.row.name }}</span></strong>
        </span>
      </button>
    </div>
  </div>
</template>
