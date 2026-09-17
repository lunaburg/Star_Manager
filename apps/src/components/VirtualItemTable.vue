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
  height: 0
});

const HEADER_HEIGHT = 42;
const ROW_HEIGHT = 60;
const OVERSCAN_ROWS = 8;
const columns = "70px 70px minmax(160px, 1.55fr) minmax(72px, .6fr) minmax(120px, 1fr) minmax(180px, 1.6fr)";

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
}

const totalHeight = computed(() => HEADER_HEIGHT + props.rows.length * ROW_HEIGHT);
const firstVisibleRow = computed(() => Math.max(
  0,
  Math.floor(Math.max(0, viewport.scrollTop - HEADER_HEIGHT) / ROW_HEIGHT) - OVERSCAN_ROWS
));
const lastVisibleRow = computed(() => Math.min(
  props.rows.length,
  Math.ceil(Math.max(0, viewport.scrollTop - HEADER_HEIGHT + viewport.height) / ROW_HEIGHT) + OVERSCAN_ROWS
));
const visibleEntries = computed(() => props.rows.slice(firstVisibleRow.value, lastVisibleRow.value).map((row, index) => ({
  row,
  index: firstVisibleRow.value + index
})));
const offsetTop = computed(() => HEADER_HEIGHT + firstVisibleRow.value * ROW_HEIGHT);

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
    class="item-table-virtual-canvas glass-surface--compact"
    role="table"
    aria-label="物品表格"
    :style="{ height: `${Math.max(HEADER_HEIGHT, totalHeight)}px`, '--item-table-columns': columns }"
  >
    <div class="item-table-virtual-header glass-surface--compact" role="row">
      <span role="columnheader">状态</span>
      <span role="columnheader">缩略图</span>
      <span role="columnheader">物品名</span>
      <span role="columnheader">Kind</span>
      <span role="columnheader">作者</span>
      <span role="columnheader">来源模组</span>
    </div>

    <div
      class="item-table-virtual-body"
      role="rowgroup"
      :style="{ transform: `translateY(${offsetTop}px)` }"
    >
      <div
        v-for="entry in visibleEntries"
        :key="`${entry.row.sourceType}:${entry.row.id}`"
        v-memo="[entry.row, isSelected(entry.row)]"
        class="item-table-virtual-row"
        :class="[
          { selected: isSelected(entry.row), 'builtin-item-row': entry.row.isBuiltin },
          props.badgeClass(entry.row.status)
        ]"
        role="row"
        @click="emit('item-click', entry.row)"
        @dblclick="emit('item-dblclick', entry.row)"
        @contextmenu.prevent="emit('item-contextmenu', entry.row, $event)"
      >
        <span class="item-table-virtual-cell" role="cell">
          <span class="badge" :class="props.badgeClass(entry.row.status)">{{ entry.row.status }}</span>
        </span>
        <span class="item-table-virtual-cell" role="cell">
          <span class="item-thumb" :class="props.badgeClass(entry.row.status)">
            <LazyThumbnail
              v-if="entry.row.thumbnailUrl && (entry.row.isStudio || entry.row.status === 'ready')"
              :src="entry.row.thumbnailUrl"
              :alt="entry.row.name + ' preview'"
              :eager="entry.index < 24"
            />
            <span v-else>{{ entry.row.status === 'ready' ? (props.isMapSceneItem(entry.row) ? 'MAP' : 'PNG') : 'MISS' }}</span>
          </span>
        </span>
          <span class="item-table-virtual-cell" role="cell"><span class="text-ellipsis">{{ entry.row.name }}</span></span>
        <span class="item-table-virtual-cell" role="cell">{{ entry.row.kind }}</span>
        <span class="item-table-virtual-cell" role="cell">{{ entry.row.author }}</span>
        <span class="item-table-virtual-cell" role="cell">
          <span class="item-source-cell">
            <span v-if="entry.row.isBuiltin" class="badge builtin-source-badge">本体</span>
            <span class="text-ellipsis" :title="entry.row.sourceMod">{{ entry.row.sourceMod }}</span>
          </span>
        </span>
      </div>
    </div>
  </div>
</template>
