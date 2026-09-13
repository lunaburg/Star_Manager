<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import LazyThumbnail from "./LazyThumbnail.vue";

const props = defineProps({
  rows: { type: Array, default: () => [] },
  selectedId: { type: [String, Number], default: null },
  badgeClass: { type: Function, required: true },
  isMapSceneItem: { type: Function, required: true }
});

const emit = defineEmits(["item-click", "item-dblclick", "item-contextmenu"]);

const canvas = ref(null);
const viewport = reactive({
  scrollTop: 0,
  height: 0,
  width: 0
});
const metrics = reactive({
  columns: 1,
  cardHeight: 140,
  rowHeight: 142
});

let scrollParent = null;
let resizeObserver = null;
let viewportRaf = 0;

function findScrollParent(element) {
  let parent = element?.parentElement || null;
  while (parent) {
    const styles = window.getComputedStyle(parent);
    if (/(auto|scroll|overlay)/i.test(`${styles.overflowY} ${styles.overflow}`)) return parent;
    parent = parent.parentElement;
  }
  return null;
}

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

  const contentWidth = Math.max(0, viewport.width - 12);
  metrics.columns = Math.max(1, Math.floor((contentWidth + 2) / 106));
  const cardWidth = Math.max(104, (contentWidth - (metrics.columns - 1) * 2) / metrics.columns);
  metrics.cardHeight = Math.ceil(cardWidth + 20);
  metrics.rowHeight = metrics.cardHeight + 2;
}

const rowCount = computed(() => Math.ceil(props.rows.length / metrics.columns));
const totalHeight = computed(() => Math.max(12, 12 + rowCount.value * metrics.rowHeight));
const startRow = computed(() => Math.max(0, Math.floor(viewport.scrollTop / metrics.rowHeight) - 4));
const endRow = computed(() => Math.min(
  rowCount.value,
  Math.ceil((viewport.scrollTop + viewport.height) / metrics.rowHeight) + 4
));
const visibleEntries = computed(() => {
  const start = startRow.value * metrics.columns;
  const end = Math.min(props.rows.length, endRow.value * metrics.columns);
  return props.rows.slice(start, end).map((row, index) => ({
    row,
    index: start + index
  }));
});
const offsetTop = computed(() => startRow.value * metrics.rowHeight);

function isSelected(row) {
  if (props.selectedId == null) return false;
  return String(props.selectedId) === String(row?.id);
}

function handleScroll() {
  scheduleViewportUpdate();
}

function bindViewport() {
  scrollParent = findScrollParent(canvas.value);
  if (!scrollParent) return;
  scrollParent.addEventListener("scroll", handleScroll, { passive: true });
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
  scrollParent?.removeEventListener("scroll", handleScroll);
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
    class="compact-item-virtual-canvas glass-surface--compact"
    :style="{ height: `${totalHeight}px` }"
  >
    <div
      class="compact-item-grid compact-item-grid--virtual glass-surface--compact"
      role="list"
      aria-label="物品紧凑视图"
      :style="{
        transform: `translateY(${offsetTop}px)`,
        '--compact-item-card-height': `${metrics.cardHeight}px`,
        '--compact-item-row-height': `${metrics.rowHeight}px`
      }"
    >
      <button
        v-for="entry in visibleEntries"
        :key="`${entry.row.sourceType}:${entry.row.id}`"
        v-memo="[entry.row, isSelected(entry.row)]"
        type="button"
        class="compact-item-card"
        :class="[
          { selected: isSelected(entry.row) },
          props.badgeClass(entry.row.status),
          { 'is-builtin': entry.row.isBuiltin }
        ]"
        :title="`${entry.row.name}\n${entry.row.kind}\n${entry.row.author} · ${entry.row.sourceMod}`"
        role="listitem"
        @click="emit('item-click', entry.row)"
        @dblclick="emit('item-dblclick', entry.row)"
        @contextmenu.prevent="emit('item-contextmenu', entry.row, $event)"
      >
        <span class="compact-item-image">
          <LazyThumbnail
            v-if="entry.row.thumbnailUrl && entry.row.status === 'ready'"
            :src="entry.row.thumbnailUrl"
            :alt="entry.row.name + ' preview'"
            :eager="entry.index < 24"
          />
          <span v-else class="compact-item-placeholder">
            <b>{{ entry.row.status === 'ready' ? (props.isMapSceneItem(entry.row) ? 'MAP' : 'PNG') : 'MISS' }}</b>
            <small>{{ entry.row.status }}</small>
          </span>
          <span v-if="entry.row.status !== 'ready'" class="compact-item-status">{{ entry.row.status }}</span>
          <span v-if="entry.row.isBuiltin" class="compact-item-source">本体</span>
        </span>
        <span class="compact-item-name">{{ entry.row.name }}</span>
      </button>
    </div>
  </div>
</template>
