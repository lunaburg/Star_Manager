<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";

const props = defineProps({
  rows: { type: Array, default: () => [] },
  selectedPath: { type: String, default: "" }
});

const emit = defineEmits(["folder-click", "toggle-folder"]);

const canvas = ref(null);
const viewport = reactive({ scrollTop: 0, height: 0 });
const ROW_HEIGHT = 34;
const OVERSCAN_ROWS = 8;
let scrollParent = null;
let resizeObserver = null;
let viewportRaf = 0;

function updateViewport() {
  if (!scrollParent) return;
  viewport.scrollTop = scrollParent.scrollTop;
  viewport.height = scrollParent.clientHeight;
}

function scheduleViewportUpdate() {
  if (viewportRaf) return;
  viewportRaf = window.requestAnimationFrame(() => {
    viewportRaf = 0;
    updateViewport();
  });
}

const startIndex = computed(() => Math.max(
  0,
  Math.floor(Math.max(0, viewport.scrollTop) / ROW_HEIGHT) - OVERSCAN_ROWS
));
const endIndex = computed(() => Math.min(
  props.rows.length,
  Math.ceil((viewport.scrollTop + viewport.height) / ROW_HEIGHT) + OVERSCAN_ROWS
));
const visibleRows = computed(() => props.rows.slice(startIndex.value, endIndex.value));
const offsetTop = computed(() => startIndex.value * ROW_HEIGHT);
const totalHeight = computed(() => Math.max(1, props.rows.length * ROW_HEIGHT));

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

function handleFolderClick(folder) {
  emit("folder-click", folder);
}

function handleFolderKeydown(event, folder) {
  if (event.key !== "Enter" && event.key !== " ") return;
  event.preventDefault();
  handleFolderClick(folder);
}

function handleToggle(event, folder) {
  event.stopPropagation();
  emit("toggle-folder", folder);
}

onMounted(() => {
  bindViewport();
});

onBeforeUnmount(() => {
  if (viewportRaf) window.cancelAnimationFrame(viewportRaf);
  scrollParent?.removeEventListener("scroll", scheduleViewportUpdate);
  resizeObserver?.disconnect();
});

watch(() => props.rows.length, () => {
  void nextTick(updateViewport);
});
</script>

<template>
  <div
    ref="canvas"
    class="character-card-tree-virtual-canvas"
    :style="{ height: `${totalHeight}px` }"
    role="tree"
    aria-label="人物卡目录"
  >
    <div
      class="character-card-tree-virtual-rows"
      :style="{ transform: `translateY(${offsetTop}px)` }"
    >
      <div
        v-for="folder in visibleRows"
        :key="folder.id"
        class="tree-row"
        :class="{ active: selectedPath === folder.relativePath }"
        :style="{ paddingLeft: `${10 + folder.depth * 18}px` }"
        role="treeitem"
        tabindex="0"
        :aria-expanded="folder.hasChildren ? folder.expanded : undefined"
        @click="handleFolderClick(folder)"
        @keydown="handleFolderKeydown($event, folder)"
      >
        <button
          type="button"
          class="tree-toggle"
          :class="{ placeholder: !folder.hasChildren }"
          :disabled="!folder.hasChildren"
          :aria-label="folder.hasChildren ? `${folder.expanded ? '收起' : '展开'} ${folder.name}` : undefined"
          @click="handleToggle($event, folder)"
        >
          {{ folder.hasChildren ? (folder.expanded ? "-" : "+") : "-" }}
        </button>
        <span class="tree-name">{{ folder.name }}</span>
        <span class="badge warn">{{ folder.count }}</span>
      </div>
    </div>
  </div>
</template>
