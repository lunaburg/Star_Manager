<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import LazyThumbnail from "./LazyThumbnail.vue";

const props = defineProps({
  rows: { type: Array, default: () => [] },
  selectedId: { type: String, default: "" },
  eagerCount: { type: Number, default: 24 }
});

const emit = defineEmits(["card-click"]);

const canvas = ref(null);
const viewport = reactive({ scrollTop: 0, height: 0, width: 0 });
const metrics = reactive({ columns: 6, cardWidth: 120, cardHeight: 168, rowHeight: 186 });

const GRID_PADDING = 18;
const GRID_GAP = 16;
const MIN_CARD_WIDTH = 92;

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

function updateViewport() {
  if (!scrollParent) return;
  viewport.scrollTop = scrollParent.scrollTop;
  viewport.height = scrollParent.clientHeight;
  viewport.width = scrollParent.clientWidth;

  const contentWidth = Math.max(0, viewport.width - GRID_PADDING * 2);
  const maxColumns = 6;
  const columns = Math.max(
    1,
    Math.min(maxColumns, Math.floor((contentWidth + GRID_GAP) / (MIN_CARD_WIDTH + GRID_GAP)))
  );
  const cardWidth = Math.max(
    MIN_CARD_WIDTH,
    (contentWidth - (columns - 1) * GRID_GAP) / columns
  );
  const cardHeight = Math.ceil(cardWidth * 352 / 252);

  metrics.columns = columns;
  metrics.cardWidth = cardWidth;
  metrics.cardHeight = cardHeight;
  metrics.rowHeight = cardHeight + GRID_GAP;
}

const rowCount = computed(() => Math.ceil(props.rows.length / metrics.columns));
const totalHeight = computed(() => (
  Math.max(1, rowCount.value * metrics.rowHeight - GRID_GAP)
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
  // A folder switch can reuse the same scroll container with a much shorter
  // list. Start the new virtual canvas at the top instead of keeping a stale
  // scroll offset that would render an empty window.
  scrollParent.scrollTop = 0;
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
      aria-label="服装卡列表"
      :style="{
        transform: `translateY(${offsetTop}px)`,
        gridTemplateColumns: `repeat(${metrics.columns}, minmax(0, 1fr))`,
        gridAutoRows: `${metrics.cardHeight}px`,
        columnGap: `${GRID_GAP}px`,
        rowGap: `${GRID_GAP}px`
      }"
    >
      <button
        v-for="entry in visibleEntries"
        :key="entry.row.id"
        v-memo="[entry.row, isSelected(entry.row)]"
        type="button"
        class="char-card clothes-card-tile"
        :class="{ selected: isSelected(entry.row) }"
        :aria-pressed="isSelected(entry.row)"
        role="listitem"
        @click="emit('card-click', entry.row)"
      >
        <span v-if="isSelected(entry.row)" class="clothes-card-check">✓</span>
        <span class="portrait clothes-card-preview">
          <LazyThumbnail
            :src="entry.row.thumbnailUrl"
            :alt="entry.row.name + ' preview'"
            :eager="entry.index < props.eagerCount"
          />
        </span>
        <span class="card-caption clothes-card-caption">
          <strong v-card-name-scroll><span class="card-name-text">{{ entry.row.name }}</span></strong>
        </span>
      </button>
    </div>
  </div>
</template>
