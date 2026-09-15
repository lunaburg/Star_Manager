<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import LazyThumbnail from "./LazyThumbnail.vue";

const props = defineProps({
  rows: { type: Array, default: () => [] },
  selectedIds: { type: Object, default: () => new Set() },
  bulkMode: { type: Boolean, default: false },
  favoriteTheme: { type: String, default: "" },
  cardTagTone: { type: Function, required: true },
  eagerCount: { type: Number, default: 24 }
});

const emit = defineEmits(["card-click"]);

const canvas = ref(null);
const viewport = reactive({ scrollTop: 0, height: 0, width: 0 });
const metrics = reactive({ columns: 5, cardWidth: 168, cardHeight: 235, rowHeight: 253, gapX: 16, gapY: 18 });

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
  const padding = readCssNumber(styles, "--card-grid-padding", 18);
  const gapX = readCssNumber(styles, "--card-grid-gap-x", 16);
  const gapY = readCssNumber(styles, "--card-grid-gap-y", 18);
  const preferredCardWidth = readCssNumber(styles, "--card-width", 168);
  const contentWidth = Math.max(0, viewport.width - padding * 2);
  const preferredColumns = Math.floor((contentWidth + gapX) / (preferredCardWidth + gapX));
  const compactColumns = Math.floor((contentWidth + gapX) / (MIN_COMPACT_CARD_WIDTH + gapX));
  const columns = Math.max(
    1,
    Math.min(MAX_COLUMNS, Math.max(preferredColumns, Math.min(COMPACT_COLUMNS, compactColumns)))
  );
  const availableCardWidth = (contentWidth - (columns - 1) * gapX) / columns;
  const cardWidth = Math.max(1, Math.min(preferredCardWidth, availableCardWidth));
  const cardHeight = Math.ceil(cardWidth * 352 / 252);

  metrics.columns = columns;
  metrics.cardWidth = cardWidth;
  metrics.cardHeight = cardHeight;
  metrics.rowHeight = cardHeight + gapY;
  metrics.gapX = gapX;
  metrics.gapY = gapY;
}

const rowCount = computed(() => Math.ceil(props.rows.length / metrics.columns));
const totalHeight = computed(() => Math.max(1, rowCount.value * metrics.rowHeight - metrics.gapY));
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
  return Boolean(props.selectedIds?.has?.(row?.absolutePath));
}

function bindViewport() {
  scrollParent = canvas.value?.parentElement || null;
  if (!scrollParent) return;
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
    class="character-card-virtual-canvas"
    :style="{ height: `${Math.max(1, totalHeight)}px` }"
  >
    <div
      class="character-card-virtual-grid"
      role="list"
      aria-label="人物卡列表"
      :style="{
        transform: `translateY(${offsetTop}px)`,
        gridTemplateColumns: `repeat(${metrics.columns}, ${metrics.cardWidth}px)`,
        gridAutoRows: `${metrics.cardHeight}px`,
        columnGap: `${metrics.gapX}px`,
        rowGap: `${metrics.gapY}px`
      }"
    >
      <div
        v-for="entry in visibleEntries"
        :key="entry.row.id"
        v-memo="[entry.row, isSelected(entry.row), props.favoriteTheme, props.bulkMode]"
        role="listitem"
        tabindex="0"
        class="char-card"
        :class="{
          selected: isSelected(entry.row),
          favorite: entry.row.favorite,
          'favorite-theme-neon': entry.row.favorite && props.favoriteTheme === 'neon',
          'favorite-theme-sakura': entry.row.favorite && props.favoriteTheme === 'sakura',
          'favorite-theme-obsidian': entry.row.favorite && props.favoriteTheme === 'obsidian',
          'bulk-mode': props.bulkMode
        }"
        :aria-pressed="isSelected(entry.row)"
        @click="emit('card-click', entry.row)"
        @keydown.enter.prevent="emit('card-click', entry.row)"
        @keydown.space.prevent="emit('card-click', entry.row)"
      >
        <span v-if="isSelected(entry.row)" class="check">✓</span>
        <span v-if="entry.row.missingCount > 0" class="card-missing-badge">缺 {{ entry.row.missingCount }}</span>
        <span class="portrait">
          <LazyThumbnail
            :src="entry.row.thumbnailUrl"
            :alt="entry.row.name + ' preview'"
            :eager="entry.index < props.eagerCount"
          />
        </span>
        <span v-if="entry.row.favorite && props.favoriteTheme === 'sakura'" class="card-theme-petals" aria-hidden="true">
          <i v-for="petalIndex in 5" :key="petalIndex"></i>
        </span>
        <span v-if="entry.row.favorite && props.favoriteTheme === 'obsidian'" class="card-theme-embers" aria-hidden="true">
          <i v-for="emberIndex in 6" :key="emberIndex"></i>
        </span>
        <span
          v-if="entry.row.tags?.length"
          class="card-hover-tags"
          role="tooltip"
          aria-label="人物卡标签"
        >
          <span class="card-hover-tag-list">
            <span
              v-for="tag in entry.row.tags"
              :key="tag"
              class="card-hover-tag"
              :class="props.cardTagTone(tag)"
            >
              {{ tag }}
            </span>
          </span>
        </span>
        <span class="card-caption">
          <strong v-card-name-scroll><span class="card-name-text">{{ entry.row.name }}</span></strong>
          <span>{{ entry.row.modifiedAt }}</span>
        </span>
      </div>
    </div>
  </div>
</template>
