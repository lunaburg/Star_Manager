<script setup>
import { computed, nextTick, onActivated, onBeforeUnmount, onMounted, ref, watch } from "vue";
import LazyThumbnail from "../LazyThumbnail.vue";
import LoadingAnimation from "../LoadingAnimation.vue";
import VirtualCharacterCardGrid from "../VirtualCharacterCardGrid.vue";
import VirtualClothesCardGrid from "../VirtualClothesCardGrid.vue";
import characterCardEmptyAnimation from "../../assets/character-card-empty-loading.json";
import characterCardLoadingAnimation from "../../assets/character-card-loading.json";

const { ctx } = defineProps({
  ctx: { type: Object, required: true }
});

const characterCardGrid = ref(null);
const clothesCardGrid = ref(null);
const sceneCardGrid = ref(null);
const cardGridRefs = { character: characterCardGrid, clothes: clothesCardGrid, scene: sceneCardGrid };

function cardGridForMode(mode) {
  return cardGridRefs[mode]?.value || null;
}

function registerActiveCardGrid() {
  const mode = String(ctx.cardBrowserMode || "");
  const target = cardGridForMode(mode);
  if (target) ctx.registerCardLibraryScrollContainer(mode, target);
}

function handleCharacterCardGridScroll(event) {
  ctx.captureCardLibraryScrollPosition("character", event?.currentTarget);
}

function handleClothesCardGridScroll(event) {
  ctx.captureCardLibraryScrollPosition("clothes", event?.currentTarget);
  ctx.handleClothesCardGridScroll(event);
}

function handleSceneCardGridScroll(event) {
  ctx.captureCardLibraryScrollPosition("scene", event?.currentTarget);
  ctx.handleSceneCardGridScroll(event);
}

onMounted(() => {
  registerActiveCardGrid();
});

onActivated(() => {
  registerActiveCardGrid();
});

onBeforeUnmount(() => {
  ctx.unregisterCardLibraryScrollContainer("character");
  ctx.unregisterCardLibraryScrollContainer("clothes");
  ctx.unregisterCardLibraryScrollContainer("scene");
});

watch(() => ctx.cardBrowserMode, (mode, previousMode) => {
  if (previousMode) ctx.unregisterCardLibraryScrollContainer(previousMode);
  void nextTick(() => {
    const target = cardGridForMode(mode);
    if (target) ctx.registerCardLibraryScrollContainer(mode, target);
  });
});

watch(() => [
  ctx.visibleCards?.length,
  ctx.clothesCards?.length,
  ctx.visibleClothesCards?.length,
  ctx.sceneCards?.length,
  ctx.visibleSceneCards?.length,
  ctx.cardLibrary?.loading,
  ctx.clothesLibrary?.loading,
  ctx.clothesLibrary?.loadingMore,
  ctx.sceneLibrary?.loading,
  ctx.sceneLibrary?.loadingMore
], () => {
  ctx.scheduleCardLibraryScrollRestore(ctx.cardBrowserMode);
});

const cardNameMeasureFrames = new WeakMap();

function measureCardNameOverflow(element) {
  const textElement = element.querySelector(".card-name-text");
  if (!textElement) return;
  const distance = Math.max(0, Math.ceil(textElement.scrollWidth - element.clientWidth));
  const isOverflowing = distance > 2;
  element.classList.toggle("is-overflowing", isOverflowing);
  element.style.setProperty("--card-name-scroll-x", `${-distance}px`);
  element.style.setProperty("--card-name-scroll-duration", `${Math.min(16, Math.max(6, 5 + distance / 18))}s`);
}

function scheduleCardNameMeasure(element) {
  const pendingFrame = cardNameMeasureFrames.get(element);
  if (pendingFrame) cancelAnimationFrame(pendingFrame);
  const frame = requestAnimationFrame(() => {
    cardNameMeasureFrames.delete(element);
    measureCardNameOverflow(element);
  });
  cardNameMeasureFrames.set(element, frame);
}

function cardTagTone(tag, index = -1) {
  if (Number.isInteger(index) && index >= 0) return `tone-${index % 12 + 1}`;
  let hash = 0;
  for (const character of String(tag || "")) {
    hash = ((hash << 5) - hash + character.codePointAt(0)) | 0;
  }
  return `tone-${Math.abs(hash) % 12 + 1}`;
}

const cardNameResizeObserver = typeof ResizeObserver === "undefined"
  ? null
  : new ResizeObserver((entries) => entries.forEach((entry) => scheduleCardNameMeasure(entry.target)));

const vCardNameScroll = {
  mounted(element) {
    cardNameResizeObserver?.observe(element);
    scheduleCardNameMeasure(element);
  },
  updated(element) {
    scheduleCardNameMeasure(element);
  },
  beforeUnmount(element) {
    cardNameResizeObserver?.unobserve(element);
    const pendingFrame = cardNameMeasureFrames.get(element);
    if (pendingFrame) cancelAnimationFrame(pendingFrame);
    cardNameMeasureFrames.delete(element);
  }
};

const DEPENDENCY_GROUPS = [
  { key: "clothes", label: "服装", tone: "blue" },
  { key: "accessory", label: "配饰", tone: "mint" },
  { key: "face", label: "面部与五官", tone: "rose" },
  { key: "hair", label: "发型", tone: "violet" },
  { key: "body", label: "身体与肌肤", tone: "amber" },
  { key: "other", label: "其他依赖", tone: "gray" }
];

const CATEGORY_PARTS = {
  8: ["body", "人体彩绘"],
  110: ["face", "脸型"],
  111: ["face", "面部肌肤"],
  112: ["face", "面部细节"],
  121: ["face", "胡须"],
  131: ["body", "身体肌肤"],
  132: ["body", "身体细节"],
  133: ["body", "晒痕"],
  140: ["clothes", "上衣"],
  141: ["clothes", "下装"],
  144: ["clothes", "手套"],
  147: ["clothes", "鞋子"],
  210: ["face", "脸型"],
  211: ["face", "面部肌肤"],
  212: ["face", "面部细节"],
  231: ["body", "身体肌肤"],
  232: ["body", "身体细节"],
  233: ["body", "晒痕"],
  240: ["clothes", "上衣"],
  241: ["clothes", "下装"],
  242: ["clothes", "内衣"],
  243: ["clothes", "内裤"],
  244: ["clothes", "手套"],
  245: ["clothes", "裤袜"],
  246: ["clothes", "袜子"],
  247: ["clothes", "鞋子"],
  300: ["hair", "后发"],
  301: ["hair", "前发"],
  302: ["hair", "侧发"],
  303: ["hair", "后侧发"],
  313: ["body", "人体彩绘"],
  314: ["face", "眉毛"],
  315: ["face", "睫毛"],
  316: ["face", "眼影"],
  317: ["face", "美瞳"],
  318: ["face", "瞳孔"],
  319: ["face", "眼睛高光"],
  320: ["face", "腮红"],
  322: ["face", "口红"],
  323: ["face", "痣与雀斑"],
  334: ["body", "乳头"],
  335: ["body", "阴毛"],
  348: ["other", "图案"],
  351: ["accessory", "头部配饰"],
  352: ["accessory", "耳部配饰"],
  353: ["accessory", "眼镜"],
  354: ["accessory", "脸部配饰"],
  355: ["accessory", "颈部配饰"],
  356: ["accessory", "肩部配饰"],
  357: ["accessory", "胸部配饰"],
  358: ["accessory", "腰部配饰"],
  359: ["accessory", "背部配饰"],
  360: ["accessory", "胯部配饰"],
  361: ["accessory", "手部配饰"],
  362: ["accessory", "腿部配饰"],
  363: ["accessory", "脚部配饰"]
};

const PROPERTY_PARTS = [
  [/chafileface\.headid$/i, "face", "脸型"],
  [/chafileface\.skinid$/i, "face", "面部肌肤"],
  [/chafileface\.detailid$/i, "face", "面部细节"],
  [/chafileface\.eyebrowid$/i, "face", "眉毛"],
  [/chafileface\.eyelashesid$/i, "face", "睫毛"],
  [/chafileface\.beardid$/i, "face", "胡须"],
  [/chafileface\.eyeblack[12]$/i, "face", "瞳孔"],
  [/chafileface\.hlid$/i, "face", "眼睛高光"],
  [/chafileface\.moleid$/i, "face", "痣与雀斑"],
  [/makeupinfo\.eyeshadowid$/i, "face", "眼影"],
  [/makeupinfo\.cheekid$/i, "face", "腮红"],
  [/makeupinfo\.lipid$/i, "face", "口红"],
  [/chafilehair\.hairback$/i, "hair", "后发"],
  [/chafilehair\.hairfront$/i, "hair", "前发"],
  [/chafilehair\.hairside$/i, "hair", "侧发"],
  [/chafilehair\.(hairoption|hairextension)$/i, "hair", "扩展发型"],
  [/chafilebody\.skinid$/i, "body", "身体肌肤"],
  [/chafilebody\.detailid$/i, "body", "身体细节"],
  [/chafilebody\.sunburnid$/i, "body", "晒痕"],
  [/chafilebody\.paintlayoutid[12]$/i, "body", "人体彩绘"],
  [/chafilebody\.nipid$/i, "body", "乳头"],
  [/chafilebody\.(underhairid|pubichairid)$/i, "body", "阴毛"],
  [/chafileclothes\.clothestop$/i, "clothes", "上衣"],
  [/chafileclothes\.clothesbot$/i, "clothes", "下装"],
  [/chafileclothes\.clothesbra$/i, "clothes", "内衣"],
  [/chafileclothes\.clothesshorts$/i, "clothes", "内裤"],
  [/chafileclothes\.clothesgloves$/i, "clothes", "手套"],
  [/chafileclothes\.clothespantyhose$/i, "clothes", "裤袜"],
  [/chafileclothes\.clothessocks$/i, "clothes", "袜子"],
  [/chafileclothes\.clothesshoes$/i, "clothes", "鞋子"]
];

function dependencyDescriptor(dependency) {
  if (dependency?.dependency_type === "scene") {
    return { group: "other", part: "场景地图" };
  }
  if (dependency?.displayMode === "mod") {
    return { group: "other", part: "场景模组" };
  }
  if (dependency?.dependency_type === "scene_item") {
    return { group: "other", part: "场景物品" };
  }
  if (dependency?.dependency_type === "scene_pattern") {
    return { group: "other", part: "场景图案" };
  }
  const property = String(dependency.property || "").replace(/^outfit\./i, "");
  const category = CATEGORY_PARTS[String(dependency.category_no || "").trim()];
  if (/^accessory\d+\./i.test(property) && category) {
    return { group: category[0], part: category[1] };
  }
  const propertyMatch = PROPERTY_PARTS.find(([pattern]) => pattern.test(property));
  if (propertyMatch) {
    return { group: propertyMatch[1], part: propertyMatch[2] };
  }
  if (category) {
    return { group: category[0], part: category[1] };
  }

  const kind = String(dependency.item?.kind || "");
  const part = kind.split("/").filter(Boolean).at(-1) || "未分类";
  if (kind.includes("面部")) return { group: "face", part };
  if (kind.includes("头发")) return { group: "hair", part };
  if (kind.includes("身体")) return { group: "body", part };
  if (kind.includes("服饰")) return { group: "clothes", part };
  if (kind.includes("饰品")) return { group: "accessory", part };
  return { group: "other", part };
}

function dependencyStatus(dependency) {
  if (dependency.source_type === "builtin" || dependency.item?.source_type === "builtin") {
    return { label: "游戏本体", state: "matched" };
  }
  if (dependency.matched) return { label: "已匹配", state: "matched" };
  if (dependency.zipmod) return { label: "物品未找到", state: "item-missing" };
  return { label: "模组未安装", state: "mod-missing" };
}

function collapseUnmatchedSceneDependencies(dependencies) {
  const result = [];
  const unmatchedByMod = new Map();
  for (const dependency of dependencies || []) {
    const modId = String(dependency?.mod_id || "").trim();
    if (dependency?.matched || !modId) {
      result.push(dependency);
      continue;
    }

    const key = modId.toLowerCase();
    const existing = unmatchedByMod.get(key);
    if (existing) {
      existing.missingDependencyCount += 1;
      existing.missingDependencies.push(dependency);
      continue;
    }

    const aggregate = {
      ...dependency,
      displayMode: "mod",
      name: dependency.zipmod?.name || modId,
      item: null,
      matched: false,
      missingDependencyCount: 1,
      missingDependencies: [dependency]
    };
    unmatchedByMod.set(key, aggregate);
    result.push(aggregate);
  }
  return result;
}

function buildDependencyGroups(dependencies, { collapseUnmatchedByMod = false } = {}) {
  const displayDependencies = collapseUnmatchedByMod
    ? collapseUnmatchedSceneDependencies(dependencies)
    : dependencies || [];
  const buckets = new Map(DEPENDENCY_GROUPS.map((group) => [group.key, []]));
  for (const dependency of displayDependencies) {
    const descriptor = dependencyDescriptor(dependency);
    buckets.get(descriptor.group).push({
      ...dependency,
      partLabel: descriptor.part,
      displayName: dependency.displayMode === "mod"
        ? dependency.zipmod?.name || dependency.mod_id || "未知模组"
        : dependency.dependency_type === "scene"
        ? dependency.zipmod?.name || dependency.name || dependency.mod_id || "未知场景地图"
        : dependency.item?.name || dependency.name || dependency.mod_id || "未知物品",
      sourceName: dependency.displayMode === "mod"
        ? `${dependency.mod_id || "未知 GUID"} · ${dependency.missingDependencyCount || 1} 项未匹配本地数据库`
        : dependency.item?.source_mod || dependency.zipmod?.name || dependency.mod_id || "来源未知",
      status: dependencyStatus(dependency)
    });
  }
  return DEPENDENCY_GROUPS
    .map((group) => {
      const items = buckets.get(group.key);
      return {
        ...group,
        items,
        missingCount: items.filter((item) => !item.matched).length
      };
    })
    .filter((group) => group.items.length > 0);
}

const cardDependencyGroups = computed(() => buildDependencyGroups(ctx.selectedCardDependencies || []));

const clothesDependencyGroups = computed(() => (
  buildDependencyGroups(ctx.selectedClothesCard?.dependencies || [])
));

const sceneDependencyGroups = computed(() => (
  buildDependencyGroups(ctx.selectedSceneCard?.dependencies || [], { collapseUnmatchedByMod: true })
));

const sceneDependencyDisplayCount = computed(() => (
  sceneDependencyGroups.value.reduce((total, group) => total + group.items.length, 0)
));

const cardModeMeta = computed(() => {
  const modes = {
      clothes: {
        eyebrow: "CLOTHES CARD LIBRARY",
        title: "服装卡浏览器",
        description: "浏览 UserData/coordinate 下的服装卡资源。",
        root: "UserData\\coordinate",
        accent: "clothes",
        detail: "服装卡按 female / male 目录浏览，点击卡片可查看依赖模组和文件信息。"
    },
    scene: {
      title: "场景卡浏览器",
      root: "UserData\\studio\\scene",
      accent: "scene"
    }
  };
  return modes[ctx.cardBrowserMode] || null;
});
</script>

<template>
<template v-if="ctx.cardBrowserMode === 'character'">
<section class="view">
          <div class="character-layout">
            <section class="panel browser-panel">
              <div class="module-head">
                <div><h1>人物卡浏览器（{{ ctx.cardBrowserCountText }}）</h1><p class="subtext mono">{{ ctx.cardFolderDisplay }}</p></div>
                <button
                  class="module-icon-button card-browser-refresh-button"
                  type="button"
                  :disabled="ctx.cardLibrary.loading || !ctx.cardLibrary.validGameDir"
                  aria-label="刷新当前目录人物卡"
                  title="刷新当前目录人物卡"
                  @click="ctx.refreshCurrentCardFolder"
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                    <path d="M20 11a8 8 0 0 0-14.8-4L3.5 9" />
                    <path d="M3.5 4.5V9h4.5" />
                    <path d="M4 13a8 8 0 0 0 14.8 4L20.5 15" />
                    <path d="M20.5 19.5V15H16" />
                  </svg>
                </button>
              </div>
              <div class="toolbar">
                <div class="toolbar-left">
                  <button
                    v-if="!ctx.cardBulkMode"
                    class="bulk-select-button"
                    type="button"
                    :disabled="!ctx.visibleCards.length"
                    title="进入人物卡多选模式"
                    aria-label="进入人物卡多选模式"
                    @click="ctx.enterCardBulkMode"
                  >
                    多选
                  </button>
                  <div v-else class="bulk-select-status" aria-live="polite">
                    <span>已选 {{ ctx.selectedCount }} 张</span>
                    <button type="button" @click="ctx.exitCardBulkMode">退出</button>
                  </div>
                  <div v-if="ctx.cardBulkMode" class="card-bulk-action-bar" aria-label="人物卡批量操作">
                    <label class="card-select-all">
                      <input
                        type="checkbox"
                        :checked="ctx.allVisibleCardsSelected"
                        :indeterminate.prop="ctx.someVisibleCardsSelected"
                        aria-label="全选当前文件夹人物卡"
                        @change="ctx.toggleAllVisibleCards"
                      >
                      <span>全选</span>
                    </label>
                  </div>
                  <div v-if="ctx.cardBulkMode" class="card-bulk-toolbar-actions" aria-label="人物卡批量操作">
                    <button
                      class="icon-action card-move-action"
                      type="button"
                      :disabled="ctx.selectedCount === 0 || !ctx.cardMoveAvailable || ctx.cardMovePrompt.busy"
                      :aria-label="`移动已选择的 ${ctx.selectedCount} 张人物卡`"
                      data-tooltip="移动人物卡"
                      @click="ctx.openCardMovePrompt"
                    >
                      <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                        <path d="M3 7h7l2 2h9v10H3Z" />
                        <path d="m12 12 2.5 2.5L12 17M14.5 14.5H8" />
                      </svg>
                      <span class="action-count" aria-hidden="true">{{ ctx.selectedCount }}</span>
                    </button>
                    <button
                      class="icon-action card-tag-bulk-action"
                      type="button"
                      :disabled="ctx.selectedCount === 0 || ctx.bulkCardTagPrompt.busy"
                      :aria-label="`为已选择的 ${ctx.selectedCount} 张人物卡添加标签`"
                      data-tooltip="批量添加标签"
                      @click="ctx.openBulkCardTagPrompt"
                    >
                      <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                        <path d="M4 5h9l7 7-8 8-8-8V5Z" />
                        <circle cx="9" cy="10" r="1.5" />
                        <path d="M16 5v6M13 8h6" />
                      </svg>
                      <span class="action-count" aria-hidden="true">{{ ctx.selectedCount }}</span>
                    </button>
                    <button
                      class="icon-action card-delete-action"
                      type="button"
                      :disabled="ctx.selectedCount === 0 || ctx.cardDeletePrompt.busy"
                      :aria-label="`删除已选择的 ${ctx.selectedCount} 张人物卡`"
                      data-tooltip="删除人物卡"
                      @click="ctx.openCardDeletePrompt"
                    >
                      <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                        <path d="M4 7h16M9 7V4h6v3M7 7l1 13h8l1-13M10 11v5M14 11v5" />
                      </svg>
                      <span class="action-count" aria-hidden="true">{{ ctx.selectedCount }}</span>
                    </button>
                    <button
                      class="primary icon-action extract-action"
                      type="button"
                      :disabled="ctx.selectedCount === 0 || ctx.isBusy"
                      :aria-label="`提取依赖，已选择 ${ctx.selectedCount} 张人物卡`"
                      data-tooltip="提取依赖"
                      @click="ctx.openCardDependencyExportPrompt"
                    >
                      <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                        <path d="M10 13a5 5 0 0 0 7.07 0l2.12-2.12a5 5 0 0 0-7.07-7.07l-1.22 1.22" />
                        <path d="M14 11a5 5 0 0 0-7.07 0L4.81 13.12a5 5 0 0 0 7.07 7.07l1.22-1.22" />
                      </svg>
                      <span class="action-count" aria-hidden="true">{{ ctx.selectedCount }}</span>
                    </button>
                  </div>
                </div>
                <div class="toolbar-right">
                  <div class="card-filter-toolbar-controls">
                    <div class="card-tag-filter-controls">
                    <div
                      class="card-tag-scope-switch"
                      :class="{ 'is-library': ctx.cardTagFilter.scope === 'library' }"
                      role="group"
                      aria-label="标签筛选范围"
                    >
                      <button
                        type="button"
                        :class="{ active: ctx.cardTagFilter.scope === 'directory' }"
                        :aria-pressed="ctx.cardTagFilter.scope === 'directory'"
                        title="只筛选当前目录中的人物卡"
                        @click="ctx.setCardTagScope('directory')"
                      >
                        当前目录
                      </button>
                      <button
                        type="button"
                        :class="{ active: ctx.cardTagFilter.scope === 'library' }"
                        :aria-pressed="ctx.cardTagFilter.scope === 'library'"
                        title="筛选整个人物卡库中的人物卡"
                        @click="ctx.setCardTagScope('library')"
                      >
                        人物卡库
                      </button>
                    </div>
                    <div class="card-tag-filter-combobox">
                    <svg class="card-tag-filter-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                      <circle cx="10.5" cy="10.5" r="5.5" />
                      <path d="m15 15 4 4" />
                    </svg>
                    <input
                      :value="ctx.cardTagFilter.search"
                      type="text"
                      role="combobox"
                      aria-label="按标签筛选人物卡"
                      aria-autocomplete="list"
                      aria-controls="card-tag-filter-options"
                      :aria-expanded="ctx.cardTagFilter.open"
                      placeholder="搜索标签"
                      autocomplete="off"
                      @focus="ctx.openCardTagFilter"
                      @blur="ctx.closeCardTagFilterSoon"
                      @input="ctx.updateCardTagFilterSearch($event.target.value)"
                      @keydown.enter.prevent="ctx.applyFirstCardTagFilterSuggestion"
                      @keydown.down.prevent="ctx.openCardTagFilter"
                      @keydown.escape="ctx.closeCardTagFilter"
                    >
                    <button
                      v-if="ctx.cardTagFilter.search"
                      class="card-tag-filter-clear"
                      type="button"
                      aria-label="清除标签筛选"
                      title="清除标签筛选"
                      @mousedown.prevent
                      @click="ctx.clearCardTagFilter"
                    >
                      <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                        <path d="m7 7 10 10M17 7 7 17" />
                      </svg>
                    </button>
                    <div
                      v-if="ctx.cardTagFilter.open"
                      id="card-tag-filter-options"
                      class="card-tag-filter-options"
                      :class="{ dense: !ctx.cardTagFilter.search.trim() }"
                      role="listbox"
                      aria-label="标签联想结果"
                    >
                      <div v-if="!ctx.cardTagFilter.search.trim()" class="card-tag-filter-heading">已有标签</div>
                      <div v-if="ctx.cardTagFilter.loading" class="card-tag-filter-empty">正在读取全库标签…</div>
                      <button
                        v-for="tag in ctx.cardTagFilterSuggestions"
                        :key="tag"
                        type="button"
                        class="card-tag-filter-option"
                        :class="[
                          { active: ctx.cardDependencyFilter === `tag:${tag}` },
                          !ctx.cardTagFilter.search.trim() ? cardTagTone(tag) : ''
                        ]"
                        role="option"
                        :title="tag"
                        :aria-selected="ctx.cardDependencyFilter === `tag:${tag}`"
                        @mousedown.prevent="ctx.selectCardTagFilter(tag)"
                      >
                        <span class="card-tag-filter-option-label">
                          <i :class="cardTagTone(tag)" aria-hidden="true"></i>
                          <span>{{ tag }}</span>
                        </span>
                        <svg v-if="ctx.cardDependencyFilter === `tag:${tag}`" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                          <path d="m5 12 4 4L19 6" />
                        </svg>
                      </button>
                      <div
                        v-if="!ctx.cardTagFilter.loading && !ctx.cardTagFilterSuggestions.length"
                        class="card-tag-filter-empty"
                      >
                        没有匹配标签
                      </div>
                      <div
                        v-if="ctx.cardTagFilter.error"
                        class="card-tag-filter-error"
                        :title="ctx.cardTagFilter.error"
                      >
                        全库标签读取失败，仍可使用当前目录标签
                      </div>
                    </div>
                    </div>
                    </div>
                    <select
                      class="card-dependency-filter"
                      :value="ctx.cardDependencyFilter.startsWith('tag:') ? 'all' : ctx.cardDependencyFilter"
                      aria-label="人物卡筛选"
                      title="筛选人物卡"
                      @change="ctx.setCardDependencyFilter($event.target.value)"
                    >
                      <option value="all">全部人物卡</option>
                      <option value="favorite">已收藏</option>
                      <option value="missing">依赖缺失</option>
                   </select>
                  </div>
                </div>
              </div>
              <div ref="characterCardGrid" class="card-grid" @scroll.passive="handleCharacterCardGridScroll">
                <div v-if="ctx.cardTagFilter.resultsLoading" class="card-state">
                  <strong>正在筛选整个人物卡库</strong>
                  <span class="subtext">正在查找带有“{{ ctx.cardTagFilter.libraryTag }}”标签的人物卡</span>
                </div>
                <div v-else-if="ctx.cardTagFilter.resultsError" class="card-state">
                  <strong>全库标签筛选失败</strong>
                  <span class="subtext">{{ ctx.cardTagFilter.resultsError }}</span>
                </div>
                <div v-else-if="ctx.cardLibrary.loading && ctx.cards.length === 0" class="card-state">
                  <LoadingAnimation class="card-loading-animation" :animation-data="characterCardLoadingAnimation" />
                  <strong>正在加载人物卡</strong>
                </div>
                <div v-else-if="ctx.cardLibrary.checked && !ctx.cardLibrary.validGameDir" class="card-state">
                  <strong>请选择有效的游戏目录</strong>
                </div>
                <div v-else-if="ctx.cardLibrary.error" class="card-state">
                  <strong>{{ ctx.cardLibrary.error }}</strong>
                </div>
                <div v-else-if="ctx.visibleCards.length === 0" class="card-state">
                  <LoadingAnimation class="card-empty-loading-animation" :animation-data="characterCardEmptyAnimation" />
                  <strong>{{ ctx.cardDependencyFilter === 'missing' && ctx.cards.length ? '当前目录没有依赖缺失的人物卡' : ctx.cardDependencyFilter === 'favorite' && ctx.cards.length ? '当前目录还没有收藏的人物卡' : ctx.cardDependencyFilter.startsWith('tag:') && ctx.cardTagFilter.scope === 'library' ? `人物卡库中没有“${ctx.cardDependencyFilter.slice(4)}”标签的人物卡` : ctx.cardDependencyFilter.startsWith('tag:') && ctx.cards.length ? `当前目录没有“${ctx.cardDependencyFilter.slice(4)}”标签的人物卡` : '未找到人物卡' }}</strong>
                  <span class="subtext mono">{{ ctx.cardTagFilter.scope === 'library' && ctx.cardDependencyFilter.startsWith('tag:') ? 'UserData/chara · 全库' : ctx.cardFolderDisplay }}</span>
                </div>
                <VirtualCharacterCardGrid
                  v-else
                  :rows="ctx.visibleCards"
                  :selected-ids="ctx.selectedCards"
                  :bulk-mode="ctx.cardBulkMode"
                  :favorite-theme="ctx.managerSettings.favoriteCardTheme"
                  :card-tag-tone="cardTagTone"
                  @card-click="ctx.handleCardClick"
                />
              </div>
            </section>
            <aside class="panel side-panel character-side-panel">
              <div class="module-head character-side-head">
                <div>
                  <h2>{{ ctx.characterSideMode === 'tree' ? '卡片目录' : '卡片详情' }}</h2>
                  <p class="subtext">{{ ctx.characterSideMode === 'tree' ? 'UserData/chara' : '当前人物卡' }}</p>
                </div>
                <div class="side-toggle" aria-label="卡片侧栏视图">
                  <button type="button" :class="{ active: ctx.characterSideMode === 'tree' }" @click="ctx.characterSideMode = 'tree'">目录</button>
                  <button type="button" :class="{ active: ctx.characterSideMode === 'detail' }" @click="ctx.characterSideMode = 'detail'">详情</button>
                </div>
              </div>
              <div v-if="ctx.characterSideMode === 'tree'" class="tree">
                <div v-if="ctx.cardLibrary.checked && !ctx.cardLibrary.validGameDir" class="tree-state">请选择有效的游戏目录</div>
                <template v-else>
                  <div
                    v-for="folder in ctx.cardFolders"
                    :key="folder.id"
                    class="tree-row"
                    :class="{ active: ctx.selectedCardFolder === folder.relativePath }"
                    :style="{ paddingLeft: `${10 + folder.depth * 18}px` }"
                    role="button"
                    tabindex="0"
                    :aria-expanded="folder.hasChildren ? folder.expanded : undefined"
                    @click="ctx.handleCardFolderClick(folder)"
                    @keydown.enter.prevent="ctx.handleCardFolderClick(folder)"
                    @keydown.space.prevent="ctx.handleCardFolderClick(folder)"
                  >
                    <button
                      type="button"
                      class="tree-toggle"
                      :class="{ placeholder: !folder.hasChildren }"
                      :disabled="!folder.hasChildren"
                      :aria-label="folder.hasChildren ? `${folder.expanded ? '收起' : '展开'} ${folder.name}` : undefined"
                      @click.stop="ctx.toggleCardFolder(folder)"
                    >
                      {{ folder.hasChildren ? (folder.expanded ? "-" : "+") : "-" }}
                    </button>
                    <span class="tree-name">{{ folder.name }}</span>
                    <span class="badge warn">{{ folder.count }}</span>
                  </div>
                </template>
              </div>
              <div v-else class="card-detail-pane">
                <div v-if="!ctx.selectedCardDetail" class="detail-empty">
                  <strong>未选择人物卡</strong>
                  <span>点击左侧卡片后查看文件信息。</span>
                </div>
                <template v-else>
                  <div class="card-detail-preview" :class="{ favorite: ctx.selectedCardDetail.favorite, 'favorite-theme-neon': ctx.selectedCardDetail.favorite && ctx.managerSettings.favoriteCardTheme === 'neon', 'favorite-theme-sakura': ctx.selectedCardDetail.favorite && ctx.managerSettings.favoriteCardTheme === 'sakura', 'favorite-theme-obsidian': ctx.selectedCardDetail.favorite && ctx.managerSettings.favoriteCardTheme === 'obsidian' }">
                    <img :src="ctx.selectedCardDetail.coverUrl" :alt="ctx.selectedCardDetail.name + ' preview'">
                    <span v-if="ctx.selectedCardDetail.favorite && ctx.managerSettings.favoriteCardTheme === 'sakura'" class="card-theme-petals" aria-hidden="true">
                      <i v-for="petalIndex in 5" :key="petalIndex"></i>
                    </span>
                    <span v-if="ctx.selectedCardDetail.favorite && ctx.managerSettings.favoriteCardTheme === 'obsidian'" class="card-theme-embers" aria-hidden="true">
                      <i v-for="emberIndex in 6" :key="emberIndex"></i>
                    </span>
                    <button
                      type="button"
                      class="card-favorite-button"
                      :class="{ active: ctx.selectedCardDetail.favorite }"
                      :disabled="Boolean(ctx.favoritingCardPath)"
                      :aria-pressed="ctx.selectedCardDetail.favorite"
                      :aria-label="ctx.selectedCardDetail.favorite ? '取消收藏人物卡' : '收藏人物卡'"
                      :title="ctx.selectedCardDetail.favorite ? '取消收藏' : '收藏'"
                      @click="ctx.toggleSelectedCardFavorite"
                    >
                      <svg viewBox="0 0 24 24" aria-hidden="true">
                        <path d="m12 3 2.7 5.5 6.1.9-4.4 4.3 1 6.1-5.4-2.9-5.4 2.9 1-6.1-4.4-4.3 6.1-.9L12 3Z" />
                      </svg>
                    </button>
                    <button
                      type="button"
                      class="card-cover-replace-button"
                      :disabled="ctx.replacingCardCover"
                      :aria-label="ctx.replacingCardCover ? '正在替换人物卡封面' : '替换人物卡封面'"
                      :aria-busy="ctx.replacingCardCover"
                      :title="ctx.replacingCardCover ? '处理中...' : '替换封面'"
                      @click="ctx.replaceSelectedCardCover"
                    >
                      <svg viewBox="0 0 24 24" aria-hidden="true">
                        <rect x="3" y="3" width="18" height="18" rx="2" />
                        <circle cx="9" cy="8" r="2" />
                        <path d="m5 18 4-4 3 3 2-2 5 3" />
                      </svg>
                    </button>
                  </div>
                  <div
                    v-if="ctx.cardCoverNotice.message"
                    class="card-cover-notice"
                    :class="ctx.cardCoverNotice.type"
                    role="status"
                  >
                    {{ ctx.cardCoverNotice.message }}
                  </div>
                  <div
                    v-if="ctx.cardFavoriteNotice.message"
                    class="card-cover-notice"
                    :class="ctx.cardFavoriteNotice.type"
                    role="status"
                  >
                    {{ ctx.cardFavoriteNotice.message }}
                  </div>
                  <div class="tabs mod-detail-tabs card-detail-tabs" aria-label="人物卡详情视图">
                    <button :class="{ active: ctx.cardDetailTab === '详情' }" type="button" @click="ctx.cardDetailTab = '详情'">详情</button>
                    <button :class="{ active: ctx.cardDetailTab === '关联' }" type="button" @click="ctx.cardDetailTab = '关联'">关联</button>
                    <button :class="{ active: ctx.cardDetailTab === '工具' }" type="button" @click="ctx.cardDetailTab = '工具'">工具</button>
                  </div>
                  <div v-if="ctx.cardDetailTab === '详情'" class="drawer-tab-panel active card-detail-info-panel">
                    <section class="card-rating-panel" aria-labelledby="card-rating-title">
                      <div class="card-rating-copy">
                        <span id="card-rating-title">人物卡评分</span>
                        <strong>{{ ctx.ratingCardPath ? '保存中...' : (ctx.selectedCardDetail.rating ? `${ctx.selectedCardDetail.rating} / 5` : '未评分') }}</strong>
                      </div>
                      <div class="card-rating-stars" role="radiogroup" aria-label="人物卡评分，1 到 5 星">
                        <button
                          v-for="star in 5"
                          :key="star"
                          type="button"
                          class="card-rating-star"
                          :class="{ active: star <= (ctx.selectedCardDetail.rating || 0) }"
                          :disabled="Boolean(ctx.ratingCardPath)"
                          role="radio"
                          :aria-checked="ctx.selectedCardDetail.rating === star"
                          :aria-label="`${star} 星`"
                          :title="`评为 ${star} 星`"
                          @click="ctx.setSelectedCardRating(star)"
                        >
                          <span class="card-rating-star-glyph" aria-hidden="true">★</span>
                        </button>
                      </div>
                      <div
                        v-if="ctx.cardRatingNotice.message"
                        class="card-rating-notice"
                        :class="ctx.cardRatingNotice.type"
                        role="status"
                        aria-live="polite"
                      >
                        {{ ctx.cardRatingNotice.message }}
                      </div>
                    </section>
                    <section class="card-tags-section" aria-labelledby="card-tags-title">
                      <span id="card-tags-title" class="card-tags-title">人物卡标签</span>
                      <div class="card-tag-list">
                        <span
                          v-for="(tag, tagIndex) in ctx.selectedCardDetail.tags"
                          :key="tag"
                          class="card-tag-chip"
                          :class="cardTagTone(tag, tagIndex)"
                        >
                          {{ tag }}
                        </span>
                        <button
                          type="button"
                          class="card-tag-add-button"
                          aria-label="添加或编辑人物卡标签"
                          title="添加或编辑标签"
                          @click="ctx.openCardTagPrompt"
                        >
                          <svg viewBox="0 0 24 24" aria-hidden="true">
                            <circle cx="12" cy="12" r="9" />
                            <path d="M12 8v8M8 12h8" />
                          </svg>
                        </button>
                      </div>
                      <div
                        v-if="ctx.cardTagNotice.message"
                        class="card-tag-save-notice"
                        :class="ctx.cardTagNotice.type"
                        role="status"
                      >
                        {{ ctx.cardTagNotice.message }}
                      </div>
                    </section>
                    <div class="drawer-section mod-detail-section">
                      <div class="profile-section-head flex-between">
                        <span class="drawer-section-title">人物参数</span>
                        <button
                          v-if="!ctx.cardProfileEditor.editing && !ctx.selectedCardProfileLoading && !ctx.selectedCardProfileError"
                          type="button"
                          class="profile-edit-button"
                          @click="ctx.openCardProfileEditor"
                        >
                          编辑
                        </button>
                      </div>
                      <div v-if="ctx.selectedCardProfileLoading" class="detail-inline-state">正在解析人物卡参数...</div>
                      <div v-else-if="ctx.selectedCardProfileError" class="detail-inline-state">{{ ctx.selectedCardProfileError }}</div>
                      <form v-else-if="ctx.cardProfileEditor.editing" class="profile-editor" @submit.prevent="ctx.saveCardProfile">
                        <label class="profile-edit-row">
                          <span><strong>姓名</strong><small>fullname</small></span>
                          <input v-model.trim="ctx.cardProfileEditor.values.fullname" type="text" maxlength="80" autocomplete="off">
                        </label>
                        <div class="profile-edit-row profile-readonly-row">
                          <span><strong>性别</strong><small>sex</small></span>
                          <strong>{{ ctx.formatCharacterSex(ctx.selectedCardProfile?.sex) }}</strong>
                          <small class="profile-lock-note">由人物卡结构决定</small>
                        </div>
                        <label class="profile-edit-row">
                          <span><strong>性格</strong><small>personality</small></span>
                          <select v-model.number="ctx.cardProfileEditor.values.personality">
                            <option v-for="option in ctx.personalityOptions" :key="option.value" :value="option.value">
                              {{ option.label }}
                            </option>
                          </select>
                        </label>
                        <div class="profile-edit-row">
                          <span><strong>生日</strong><small>birthday</small></span>
                          <div class="profile-birthday-fields two-column-grid">
                            <label><input v-model.number="ctx.cardProfileEditor.values.birthMonth" type="number" min="1" max="12"><span>月</span></label>
                            <label><input v-model.number="ctx.cardProfileEditor.values.birthDay" type="number" min="1" max="31"><span>日</span></label>
                          </div>
                        </div>
                        <label class="profile-edit-row">
                          <span><strong>声线</strong><small>voiceRate</small></span>
                          <input v-model.number="ctx.cardProfileEditor.values.voiceRate" type="number" min="0" max="1" step="0.01">
                        </label>
                        <label class="profile-edit-row profile-boolean-row">
                          <span><strong>扶她</strong><small>futanari</small></span>
                          <input v-model="ctx.cardProfileEditor.values.futanari" type="checkbox">
                        </label>
                        <div v-if="ctx.cardProfileEditor.error" class="card-tool-notice error" role="alert">{{ ctx.cardProfileEditor.error }}</div>
                        <div class="profile-editor-actions">
                          <button type="button" :disabled="ctx.cardProfileEditor.busy" @click="ctx.cancelCardProfileEditor">取消</button>
                          <button class="primary" type="submit" :disabled="ctx.cardProfileEditor.busy">
                            {{ ctx.cardProfileEditor.busy ? '保存中...' : '保存人物参数' }}
                          </button>
                        </div>
                      </form>
                      <template v-else>
                        <div class="kv mod-kv"><span>fullname</span><strong>{{ ctx.formatProfileValue(ctx.selectedCardProfile?.fullname) }}</strong></div>
                        <div class="kv mod-kv"><span>sex</span><strong>{{ ctx.formatCharacterSex(ctx.selectedCardProfile?.sex) }}</strong></div>
                        <div class="kv mod-kv"><span>personality</span><strong>{{ ctx.formatPersonality(ctx.selectedCardProfile?.personality) }}</strong></div>
                        <div class="kv mod-kv"><span>birthday</span><strong>{{ ctx.selectedCardProfile?.birthMonth != null && ctx.selectedCardProfile?.birthDay != null ? `${ctx.selectedCardProfile.birthMonth}月${ctx.selectedCardProfile.birthDay}号` : '-' }}</strong></div>
                        <div class="kv mod-kv"><span>voiceRate</span><strong>{{ ctx.formatProfileValue(ctx.selectedCardProfile?.voiceRate) }}</strong></div>
                        <div class="kv mod-kv"><span>futanari</span><strong>{{ ctx.formatProfileValue(ctx.selectedCardProfile?.futanari) }}</strong></div>
                      </template>
                      <div v-if="ctx.cardProfileEditor.message && !ctx.cardProfileEditor.editing" class="card-tool-notice success" role="status">
                        {{ ctx.cardProfileEditor.message }}
                      </div>
                    </div>
                  </div>
                  <div v-else-if="ctx.cardDetailTab === '关联'" class="drawer-tab-panel active card-detail-related-panel">
                    <div class="drawer-section mod-detail-section">
                      <span class="drawer-section-title">关联</span>
                      <div v-if="ctx.selectedCardProfileLoading" class="detail-inline-state">正在解析人物卡依赖...</div>
                      <div v-else-if="ctx.selectedCardProfileError" class="detail-inline-state">{{ ctx.selectedCardProfileError }}</div>
                      <div v-else-if="ctx.selectedCardDependencies.length === 0" class="detail-inline-state">暂无关联数据</div>
                      <div v-else class="card-dependency-browser">
                        <div class="card-dependency-overview">
                          <span>
                            <strong>{{ ctx.selectedCardDependencies.length }}</strong>
                            项物品依赖
                          </span>
                          <div class="card-dependency-overview-actions">
                            <button
                              v-if="ctx.cardDependencyRemoteSummary.missingCount > 0 && ctx.cardDependencyRemoteSummary.availableCount > 0"
                              type="button"
                              class="card-dependency-install-all"
                              :disabled="ctx.cardDependencyRemoteBusy && !ctx.cardDependencyRemote.allTaskId"
                              :title="ctx.cardDependencyRemote.allTaskId ? (ctx.cardDependencyRemote.allStatus === 'paused' ? '点击继续任务' : '点击暂停任务') : '安装全部可获取的缺失模组'"
                              @click.stop="ctx.cardDependencyRemote.allTaskId ? ctx.toggleAllCardDependencies() : ctx.installAllCardDependencies()"
                            >
                              {{ ctx.cardDependencyRemote.allTaskId
                                ? (ctx.cardDependencyRemote.allStatus === 'paused' ? '继续全部' : '暂停全部')
                                : (ctx.cardDependencyRemoteBusy ? '准备中...' : '全部安装') }}
                            </button>
                          </div>
                        </div>
                        <section
                          v-for="group in cardDependencyGroups"
                          :key="group.key"
                          class="card-dependency-group"
                          :class="`tone-${group.tone}`"
                        >
                          <header class="card-dependency-group-head">
                            <span class="dependency-group-title">
                              <strong>{{ group.label }}</strong>
                            </span>
                            <span class="dependency-group-count">
                              {{ group.items.length }}
                              <small v-if="group.missingCount">缺 {{ group.missingCount }}</small>
                            </span>
                          </header>
                          <div class="card-dependency-list">
                            <div
                              v-for="dependency in group.items"
                              :key="dependency.id"
                              class="card-dependency-item"
                              :class="[dependency.status.state, { 'has-inline-progress': ctx.cardDependencyInlineProgress(dependency) }]"
                              role="button"
                              tabindex="0"
                              :title="`${dependency.partLabel} · ${dependency.property || '无内部属性'} · ${dependency.status.label}`"
                              @click="ctx.openCardDependencyItem(dependency)"
                              @keydown.enter.prevent="ctx.openCardDependencyItem(dependency)"
                              @keydown.space.prevent="ctx.openCardDependencyItem(dependency)"
                            >
                              <span class="item-thumb" :class="dependency.item ? ctx.badgeClass(dependency.item.status) : 'missing'">
                                <LazyThumbnail
                                  v-if="dependency.item?.thumbnailUrl"
                                  :src="dependency.item.thumbnailUrl"
                                  :alt="dependency.displayName + ' thumbnail'"
                                />
                                <span v-else>{{ dependency.matched ? "PNG" : "MISS" }}</span>
                              </span>
                              <span class="card-dependency-main">
                                <strong>{{ dependency.displayName }}</strong>
                                <span class="dependency-item-meta">
                                  <span class="dependency-part-label">{{ dependency.partLabel }}</span>
                                  <small>{{ dependency.sourceName }}</small>
                                </span>
                              </span>
                              <span class="dependency-match-actions">
                                <span
                                  v-if="dependency.status.state === 'matched'"
                                  class="dependency-match-state"
                                  :class="dependency.status.state"
                                >
                                  {{ dependency.status.label }}
                                </span>
                                <template v-if="['mod-missing', 'item-missing'].includes(dependency.status.state)">
                                  <div v-if="ctx.cardDependencyInlineProgress(dependency)" class="dependency-inline-progress" aria-live="polite">
                                    <div class="dependency-inline-progress-head">
                                      <span>{{ ctx.cardDependencyInlineProgress(dependency).phase === 'download' ? '下载' : '安装' }}</span>
                                      <span class="dependency-inline-progress-actions">
                                        <strong>{{ Math.round(ctx.cardDependencyInlineProgress(dependency).phase === 'download' ? ctx.cardDependencyInlineProgress(dependency).downloadProgress : ctx.cardDependencyInlineProgress(dependency).installProgress) }}%</strong>
                                        <button
                                          type="button"
                                          class="dependency-inline-control"
                                          :title="ctx.cardDependencyRemote.statuses[ctx.normalizeCardDependencyGuid(dependency)] === 'paused' ? '继续任务' : '暂停任务'"
                                          :aria-label="ctx.cardDependencyRemote.statuses[ctx.normalizeCardDependencyGuid(dependency)] === 'paused' ? '继续任务' : '暂停任务'"
                                          @click.stop="ctx.installCardDependency(dependency)"
                                        >
                                          <svg v-if="ctx.cardDependencyRemote.statuses[ctx.normalizeCardDependencyGuid(dependency)] === 'paused'" viewBox="0 0 24 24" aria-hidden="true">
                                            <path d="M8 5.5v13l10-6.5L8 5.5Z" />
                                          </svg>
                                          <svg v-else viewBox="0 0 24 24" aria-hidden="true">
                                            <path d="M7 5v14M17 5v14" />
                                          </svg>
                                        </button>
                                      </span>
                                    </div>
                                    <template v-if="ctx.cardDependencyInlineProgress(dependency).phase === 'download'">
                                      <div class="dependency-inline-progress-stage download">
                                        <div class="dependency-inline-progress-track"><span :style="{ width: `${ctx.cardDependencyInlineProgress(dependency).downloadProgress}%` }"></span></div>
                                        <small>{{ ctx.formatDownloadSpeed(ctx.cardDependencyInlineProgress(dependency).downloadSpeedBps) }}</small>
                                      </div>
                                    </template>
                                    <template v-else-if="ctx.cardDependencyInlineProgress(dependency).phase === 'install'">
                                      <div class="dependency-inline-progress-stage install">
                                        <div class="dependency-inline-progress-track"><span :style="{ width: `${ctx.cardDependencyInlineProgress(dependency).installProgress}%` }"></span></div>
                                        <small>正在写入索引</small>
                                      </div>
                                    </template>
                                  </div>
                                  <button
                                    v-if="ctx.cardDependencyRemote.taskIds[ctx.normalizeCardDependencyGuid(dependency)]"
                                    type="button"
                                    class="dependency-cancel-download"
                                    title="取消下载"
                                    @click.stop="ctx.cancelCardDependency(dependency)"
                                  >
                                    取消下载
                                  </button>
                                  <button
                                    v-else-if="ctx.cardDependencyRemoteFor(dependency)?.status === 'available'"
                                    type="button"
                                    class="dependency-install-button"
                                    title="安装此模组"
                                    @click.stop="ctx.installCardDependency(dependency)"
                                  >
                                    {{ ctx.cardDependencyRemote.busyGuids[ctx.normalizeCardDependencyGuid(dependency)] ? '准备中...' : '安装' }}
                                  </button>
                                  <span
                                    v-else-if="ctx.cardDependencyRemoteFor(dependency)?.status === 'unavailable'"
                                    class="dependency-unavailable-label"
                                  >
                                    无法获取
                                  </span>
                                  <span v-else class="dependency-checking-label">检查中</span>
                                </template>
                                <small
                                  v-if="ctx.cardDependencyRemote.notices[ctx.normalizeCardDependencyGuid(dependency)]"
                                  class="dependency-install-notice"
                                >
                                  {{ ctx.cardDependencyRemote.notices[ctx.normalizeCardDependencyGuid(dependency)] }}
                                </small>
                              </span>
                            </div>
                          </div>
                        </section>
                      </div>
                    </div>
                  </div>
                  <div v-else class="drawer-tab-panel active">
                    <div class="drawer-section mod-detail-section">
                      <span class="drawer-section-title">工具</span>
                      <div class="card-tool-stack">
                        <div class="character-tool-card card-load-tool">
                          <span class="character-tool-copy">
                            <strong>读取到游戏</strong>
                          </span>
                          <span class="character-tool-actions">
                            <button class="character-tool-action" type="button" :disabled="ctx.cardLoadPrompt.busy" @click="ctx.openCardLoadPrompt">
                              选择读取
                            </button>
                          </span>
                          <div
                            v-if="ctx.cardLoadNotice.message"
                            class="card-tool-notice card-load-notice"
                            :class="ctx.cardLoadNotice.type"
                            role="status"
                            aria-live="polite"
                          >
                            {{ ctx.cardLoadNotice.message }}
                          </div>
                        </div>

                        <div class="character-tool-card">
                          <span class="character-tool-copy">
                            <strong>设为看板娘</strong>
                          </span>
                          <span class="character-tool-actions">
                            <button class="character-tool-action" type="button" :disabled="Boolean(ctx.settingNaviSlot)" title="替换 navi 看板娘" @click="ctx.setSelectedCardAsNavi('navi')">
                              {{ ctx.settingNaviSlot === 'navi' ? '替换中' : 'navi' }}
                            </button>
                            <button class="character-tool-action" type="button" :disabled="Boolean(ctx.settingNaviSlot)" title="替换 sitri 看板娘" @click="ctx.setSelectedCardAsNavi('sitri')">
                              {{ ctx.settingNaviSlot === 'sitri' ? '替换中' : 'sitri' }}
                            </button>
                          </span>
                        </div>
                        <div
                          v-if="ctx.naviActionNotice.message"
                          class="card-tool-notice"
                          :class="ctx.naviActionNotice.type"
                          role="status"
                          aria-live="polite"
                        >
                          {{ ctx.naviActionNotice.message }}
                        </div>

                        <div class="character-tool-card coordinate-export-tool">
                          <span class="character-tool-copy">
                            <strong>导出为服装卡</strong>
                          </span>
                          <span class="character-tool-actions coordinate-tool-actions">
                            <button class="character-tool-action" type="button" :disabled="ctx.exportingCoordinateCard" @click="ctx.openCoordinateExportSettings">
                              配置
                            </button>
                            <button class="character-tool-action" type="button" :disabled="ctx.exportingCoordinateCard" @click="ctx.exportSelectedCardCoordinate">
                              {{ ctx.exportingCoordinateCard ? '导出中' : '导出' }}
                            </button>
                          </span>
                          <div
                            v-if="ctx.coordinateExportNotice.message"
                            class="card-tool-notice coordinate-export-notice"
                            :class="ctx.coordinateExportNotice.type"
                            role="status"
                            aria-live="polite"
                          >
                            <span>{{ ctx.coordinateExportNotice.message }}</span>
                            <button
                              v-if="ctx.coordinateExportNotice.path"
                              type="button"
                              @click="ctx.revealExportedCoordinate"
                            >
                              打开位置
                            </button>
                          </div>
                        </div>

                        <div class="character-tool-card portable-package-tool">
                          <span class="character-tool-copy">
                            <strong>生成便携依赖包</strong>
                          </span>
                          <span class="character-tool-actions">
                            <button class="character-tool-action" type="button" :disabled="ctx.exportingPortablePackage" @click="ctx.openPortablePackageSettings">
                              配置
                            </button>
                            <button class="character-tool-action" type="button" :disabled="ctx.exportingPortablePackage" @click="ctx.exportSelectedCardPortablePackage">
                              {{ ctx.exportingPortablePackage ? '生成中' : '生成' }}
                            </button>
                          </span>
                          <div
                            v-if="ctx.portablePackageNotice.message"
                            class="card-tool-notice coordinate-export-notice"
                            :class="ctx.portablePackageNotice.type"
                            role="status"
                            aria-live="polite"
                          >
                            <span>{{ ctx.portablePackageNotice.message }}</span>
                            <button v-if="ctx.portablePackageNotice.path" type="button" @click="ctx.revealPortablePackage">
                              打开位置
                            </button>
                          </div>
                        </div>

                        <div class="character-tool-card character-tool-danger-card">
                          <span class="character-tool-copy">
                            <strong>删除人物卡</strong>
                          </span>
                          <span class="character-tool-actions">
                            <button
                              class="character-tool-action"
                              type="button"
                              :disabled="ctx.cardSingleDeletePrompt.busy"
                              title="将人物卡移入回收站"
                              @click="ctx.openSelectedCardDeletePrompt"
                            >
                              删除
                            </button>
                          </span>
                        </div>

                      </div>
                    </div>
                  </div>
                </template>
              </div>
            </aside>
          </div>
          <div
            v-if="ctx.cardLoadPrompt.open"
            class="prompt-backdrop"
            @click.self="!ctx.cardLoadPrompt.busy && (ctx.cardLoadPrompt.open = false)"
          >
            <div class="prompt-panel card-load-prompt" role="dialog" aria-modal="true" aria-labelledby="card-load-prompt-title">
              <div class="card-load-prompt-head">
                <div>
                  <strong id="card-load-prompt-title">选择读取内容</strong>
                </div>
                <button
                  type="button"
                  class="card-load-close"
                  :disabled="ctx.cardLoadPrompt.busy"
                  aria-label="关闭读取选项"
                  @click="ctx.cardLoadPrompt.open = false"
                >
                  ×
                </button>
              </div>
              <div v-if="ctx.selectedCardDetail" class="card-load-target">
                <img :src="ctx.selectedCardDetail.coverUrl" :alt="ctx.selectedCardDetail.name + ' preview'">
                <span>
                  <small>当前人物卡</small>
                  <strong>{{ ctx.selectedCardDetail.name }}</strong>
                </span>
              </div>
              <div class="card-load-option-list two-column-grid">
                <button
                  v-for="option in ctx.CARD_LOAD_OPTIONS"
                  :key="option.key"
                  type="button"
                  class="card-load-option"
                  :class="{ selected: ctx.cardLoadPrompt.selected.includes(option.key) }"
                  :disabled="ctx.cardLoadPrompt.busy"
                  :aria-pressed="ctx.cardLoadPrompt.selected.includes(option.key)"
                  @click="ctx.toggleCardLoadOption(option.key)"
                >
                  <span class="card-load-option-check" aria-hidden="true">
                    {{ ctx.cardLoadPrompt.selected.includes(option.key) ? '✓' : '' }}
                  </span>
                  <span class="card-load-option-copy">
                    <strong>{{ option.label }}</strong>
                    <small>{{ option.description }}</small>
                  </span>
                </button>
              </div>
              <div v-if="ctx.cardLoadPrompt.error" class="prompt-error" role="alert">{{ ctx.cardLoadPrompt.error }}</div>
              <div class="prompt-actions">
                <button type="button" :disabled="ctx.cardLoadPrompt.busy" @click="ctx.cardLoadPrompt.open = false">取消</button>
                <button class="primary" type="button" :disabled="ctx.cardLoadPrompt.busy || !ctx.cardLoadPrompt.selected.length" @click="ctx.loadSelectedCardToGame">
                  {{ ctx.cardLoadPrompt.busy ? '读取中...' : '读取到游戏' }}
                </button>
              </div>
            </div>
          </div>
          <div
            v-if="ctx.bulkCardTagPrompt.open"
            class="prompt-backdrop"
            @click.self="!ctx.bulkCardTagPrompt.busy && (ctx.bulkCardTagPrompt.open = false)"
          >
            <div class="prompt-panel card-tag-prompt" role="dialog" aria-modal="true" aria-labelledby="bulk-card-tag-prompt-title">
              <div class="card-tag-prompt-head">
                <div>
                  <strong id="bulk-card-tag-prompt-title">批量添加人物卡标签</strong>
                  <span>为已选择的 {{ ctx.selectedCount }} 张人物卡追加标签，不会覆盖原有标签</span>
                </div>
                <span class="card-tag-selection-count">{{ ctx.bulkCardTagPrompt.selected.length }} / 12</span>
              </div>
              <div class="card-tag-prompt-section">
                <span class="card-tag-prompt-label">选择要添加的标签</span>
                <div v-if="ctx.bulkCardTagPrompt.loading" class="card-tag-prompt-empty">正在读取标签...</div>
                <div v-else-if="ctx.bulkCardTagPrompt.available.length" class="card-tag-choice-list">
                  <button
                    v-for="(tag, tagIndex) in ctx.bulkCardTagPrompt.available"
                    :key="tag"
                    type="button"
                    class="card-tag-choice"
                    :class="[cardTagTone(tag, tagIndex), { selected: ctx.bulkCardTagPrompt.selected.some((item) => item.toLocaleLowerCase() === tag.toLocaleLowerCase()) }]"
                    :aria-pressed="ctx.bulkCardTagPrompt.selected.some((item) => item.toLocaleLowerCase() === tag.toLocaleLowerCase())"
                    :disabled="ctx.bulkCardTagPrompt.busy"
                    @click="ctx.toggleBulkCardTagPromptTag(tag)"
                  >
                    <span>{{ tag }}</span>
                    <svg v-if="ctx.bulkCardTagPrompt.selected.some((item) => item.toLocaleLowerCase() === tag.toLocaleLowerCase())" viewBox="0 0 16 16" aria-hidden="true">
                      <path d="m3 8 3 3 7-7" />
                    </svg>
                  </button>
                  </div>
                <div v-else class="card-tag-prompt-empty">还没有可复用的标签</div>
              </div>
              <form class="card-tag-create-row" @submit.prevent="ctx.addBulkCardTagDraft">
                <label for="new-bulk-card-tag">新建标签</label>
                <div>
                  <input id="new-bulk-card-tag" v-model="ctx.bulkCardTagPrompt.draft" type="text" maxlength="24" autocomplete="off" placeholder="例如：粉发、礼服、成熟">
                  <button type="submit" :disabled="ctx.bulkCardTagPrompt.busy">添加</button>
                </div>
              </form>
              <div v-if="ctx.bulkCardTagPrompt.error" class="prompt-error" role="alert">{{ ctx.bulkCardTagPrompt.error }}</div>
              <div class="prompt-actions">
                <button type="button" :disabled="ctx.bulkCardTagPrompt.busy" @click="ctx.bulkCardTagPrompt.open = false">取消</button>
                <button class="primary" type="button" :disabled="ctx.bulkCardTagPrompt.busy || !ctx.bulkCardTagPrompt.selected.length" @click="ctx.submitBulkAddCharacterCardTags">
                  {{ ctx.bulkCardTagPrompt.busy ? '提交中...' : `为 ${ctx.selectedCount} 张卡添加` }}
                </button>
              </div>
            </div>
          </div>
          <div
            v-if="ctx.cardTagPrompt.open"
            class="prompt-backdrop"
            @click.self="!ctx.cardTagPrompt.busy && (ctx.cardTagPrompt.open = false)"
          >
            <div class="prompt-panel card-tag-prompt" role="dialog" aria-modal="true" aria-labelledby="card-tag-prompt-title">
              <div class="card-tag-prompt-head">
                <div>
                  <strong id="card-tag-prompt-title">编辑人物卡标签</strong>
                </div>
                <span class="card-tag-selection-count">{{ ctx.cardTagPrompt.selected.length }} / 12</span>
              </div>
              <div class="card-tag-prompt-section">
                <span class="card-tag-prompt-label">当前卡片已有标签</span>
                <div v-if="ctx.cardTagPrompt.current.length" class="card-tag-choice-list">
                  <button
                    v-for="(tag, tagIndex) in ctx.cardTagPrompt.current"
                    :key="tag"
                    type="button"
                    class="card-tag-choice"
                    :class="[cardTagTone(tag, tagIndex), { selected: ctx.cardTagPrompt.selected.some((item) => item.toLocaleLowerCase() === tag.toLocaleLowerCase()) }]"
                    :aria-pressed="ctx.cardTagPrompt.selected.some((item) => item.toLocaleLowerCase() === tag.toLocaleLowerCase())"
                    :disabled="ctx.cardTagPrompt.busy"
                    @click="ctx.toggleCardTagPromptTag(tag)"
                  >
                    <span>{{ tag }}</span>
                    <svg v-if="ctx.cardTagPrompt.selected.some((item) => item.toLocaleLowerCase() === tag.toLocaleLowerCase())" viewBox="0 0 16 16" aria-hidden="true">
                      <path d="m3 8 3 3 7-7" />
                    </svg>
                  </button>
                </div>
                <div v-else class="card-tag-prompt-empty">当前人物卡还没有标签</div>
              </div>
              <div class="card-tag-prompt-section">
                <span class="card-tag-prompt-label">人物卡库标签</span>
                <div v-if="ctx.cardTagPrompt.loading" class="card-tag-prompt-empty">正在读取标签...</div>
                <div v-else-if="ctx.cardTagPromptLibraryTags.length" class="card-tag-choice-list">
                  <button
                    v-for="(tag, tagIndex) in ctx.cardTagPromptLibraryTags"
                    :key="tag"
                    type="button"
                    class="card-tag-choice"
                    :class="[cardTagTone(tag, tagIndex), { selected: ctx.cardTagPrompt.selected.some((item) => item.toLocaleLowerCase() === tag.toLocaleLowerCase()) }]"
                    :aria-pressed="ctx.cardTagPrompt.selected.some((item) => item.toLocaleLowerCase() === tag.toLocaleLowerCase())"
                    :disabled="ctx.cardTagPrompt.busy"
                    @click="ctx.toggleCardTagPromptTag(tag)"
                  >
                    <span>{{ tag }}</span>
                    <svg v-if="ctx.cardTagPrompt.selected.some((item) => item.toLocaleLowerCase() === tag.toLocaleLowerCase())" viewBox="0 0 16 16" aria-hidden="true">
                      <path d="m3 8 3 3 7-7" />
                    </svg>
                  </button>
                </div>
                <div v-else class="card-tag-prompt-empty">没有匹配的人物卡库标签</div>
              </div>
              <form class="card-tag-create-row" @submit.prevent="ctx.addCardTagDraft">
                <label for="new-card-tag">新建标签</label>
                <div>
                  <input id="new-card-tag" v-model="ctx.cardTagPrompt.draft" type="text" maxlength="24" autocomplete="off" placeholder="例如：粉发、礼服、成熟">
                  <button type="submit" :disabled="ctx.cardTagPrompt.busy">添加</button>
                </div>
              </form>
              <div v-if="ctx.cardTagPrompt.error" class="prompt-error" role="alert">{{ ctx.cardTagPrompt.error }}</div>
              <div class="prompt-actions">
                <button type="button" :disabled="ctx.cardTagPrompt.busy" @click="ctx.cardTagPrompt.open = false">取消</button>
                <button class="primary" type="button" :disabled="ctx.cardTagPrompt.busy" @click="ctx.saveSelectedCardTags">
                  {{ ctx.cardTagPrompt.busy ? '保存中...' : '保存标签' }}
                </button>
              </div>
            </div>
          </div>
</section>
</template>
<section v-else-if="ctx.cardBrowserMode === 'clothes'" class="view clothes-card-view">
  <div class="clothes-card-layout">
    <section class="panel clothes-browser-panel">
      <div class="module-head clothes-browser-head">
        <div>
          <h1>服装卡浏览器（{{ ctx.clothesCardCountText }}）</h1>
          <p class="subtext mono">UserData/coordinate{{ ctx.selectedClothesFolder ? `/${ctx.selectedClothesFolder}` : '' }}</p>
        </div>
        <button
          class="module-icon-button card-browser-refresh-button"
          type="button"
          :disabled="ctx.clothesLibrary.loading || !ctx.clothesLibrary.validGameDir"
          aria-label="刷新服装卡库"
          title="刷新服装卡库"
          @click="ctx.refreshClothesCards"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <path d="M20 11a8 8 0 0 0-14.8-4L3.5 9" />
            <path d="M3.5 4.5V9h4.5" />
            <path d="M4 13a8 8 0 0 0 14.8 4L20.5 15" />
            <path d="M20.5 19.5V15H16" />
          </svg>
        </button>
      </div>

      <div ref="clothesCardGrid" class="card-grid clothes-card-grid" @scroll.passive="handleClothesCardGridScroll">
        <div v-if="ctx.clothesLibrary.loading && !ctx.clothesCards.length" class="clothes-card-state">
          <LoadingAnimation class="card-loading-animation" :animation-data="characterCardLoadingAnimation" />
          <strong>正在读取服装卡</strong>
        </div>
        <div v-else-if="ctx.clothesLibrary.indexing && !ctx.visibleClothesCards.length" class="clothes-card-state">
          <LoadingAnimation class="card-loading-animation" :animation-data="characterCardLoadingAnimation" />
          <strong>正在识别服装卡</strong>
          <span class="subtext">普通 PNG 不会显示在列表中</span>
        </div>
        <div v-else-if="ctx.clothesLibrary.checked && !ctx.clothesLibrary.validGameDir" class="clothes-card-state">
          <strong>请选择有效的游戏目录</strong>
          <span class="subtext">需要存在 UserData/coordinate/female 或 male</span>
        </div>
        <div v-else-if="ctx.clothesLibrary.error" class="clothes-card-state">
          <strong>{{ ctx.clothesLibrary.error }}</strong>
        </div>
        <div v-else-if="!ctx.visibleClothesCards.length" class="clothes-card-state">
          <strong>当前目录没有服装卡</strong>
          <span class="subtext mono">UserData/coordinate{{ ctx.selectedClothesFolder ? `/${ctx.selectedClothesFolder}` : '' }}</span>
        </div>
        <VirtualClothesCardGrid
          v-else-if="ctx.visibleClothesCards.length"
          :rows="ctx.visibleClothesCards"
          :selected-id="ctx.selectedClothesDetailPath"
          @card-click="ctx.handleClothesCardClick"
        />
        <div v-if="ctx.clothesLibrary.loadingMore" class="clothes-card-load-more">正在继续识别服装卡…</div>
        <div v-else-if="ctx.clothesLibrary.indexing" class="clothes-card-load-more">正在识别当前目录中的服装卡…</div>
      </div>
    </section>

    <aside class="panel side-panel character-side-panel clothes-side-panel">
      <div class="module-head character-side-head">
        <div>
          <h2>{{ ctx.clothesSideMode === 'tree' ? '服装卡目录' : '服装卡详情' }}</h2>
          <p class="subtext">{{ ctx.clothesSideMode === 'tree' ? 'UserData/coordinate' : '当前服装卡' }}</p>
        </div>
        <div class="side-toggle" aria-label="服装卡侧栏视图">
          <button type="button" :class="{ active: ctx.clothesSideMode === 'tree' }" @click="ctx.clothesSideMode = 'tree'">目录</button>
          <button type="button" :class="{ active: ctx.clothesSideMode === 'detail' }" @click="ctx.clothesSideMode = 'detail'">详情</button>
        </div>
      </div>

      <div v-if="ctx.clothesSideMode === 'tree'" class="clothes-directory-section">
        <div class="clothes-directory-tree">
          <div
            v-for="folder in ctx.clothesFolders"
            :key="folder.id"
            class="tree-row clothes-tree-row"
            :class="{ active: ctx.selectedClothesFolder === folder.relativePath }"
            :style="{ paddingLeft: `${10 + folder.depth * 18}px` }"
            role="button"
            tabindex="0"
            :aria-expanded="folder.hasChildren ? folder.expanded : undefined"
            @click="ctx.selectClothesFolder(folder.relativePath)"
            @keydown.enter.prevent="ctx.selectClothesFolder(folder.relativePath)"
            @keydown.space.prevent="ctx.selectClothesFolder(folder.relativePath)"
          >
            <button
              type="button"
              class="tree-toggle clothes-tree-toggle"
              :class="{ placeholder: !folder.hasChildren }"
              :disabled="!folder.hasChildren"
              :aria-label="folder.hasChildren ? `${folder.expanded ? '收起' : '展开'} ${folder.name}` : undefined"
              @click.stop="ctx.toggleClothesFolder(folder)"
              @keydown.enter.stop="ctx.toggleClothesFolder(folder)"
              @keydown.space.prevent.stop="ctx.toggleClothesFolder(folder)"
            >{{ folder.hasChildren ? (folder.expanded ? '-' : '+') : '·' }}</button>
            <span class="tree-name clothes-folder-name">{{ folder.name }}</span>
            <span class="clothes-folder-count">
              {{ folder.count }}
            </span>
          </div>
        </div>
      </div>

      <div v-else class="clothes-detail-section">
        <template v-if="ctx.selectedClothesCard">
          <div class="clothes-detail-preview">
            <img :src="ctx.selectedClothesCard.coverUrl || ctx.selectedClothesCard.thumbnailUrl" :alt="ctx.selectedClothesCard.name + ' preview'">
          </div>
          <div class="tabs mod-detail-tabs clothes-detail-tabs" role="tablist" aria-label="服装卡详情视图">
            <button
              type="button"
              role="tab"
              :aria-selected="ctx.clothesDetailTab === '详情'"
              :class="{ active: ctx.clothesDetailTab === '详情' }"
              @click="ctx.clothesDetailTab = '详情'"
            >详情</button>
            <button
              type="button"
              role="tab"
              :aria-selected="ctx.clothesDetailTab === '关联'"
              :class="{ active: ctx.clothesDetailTab === '关联' }"
              @click="ctx.clothesDetailTab = '关联'"
            >关联</button>
          </div>
          <div v-if="ctx.clothesDetailTab === '详情'" class="clothes-detail-tab-panel">
            <h2 class="clothes-detail-title">{{ ctx.selectedClothesCard.name }}</h2>
            <p class="subtext mono clothes-detail-path">{{ ctx.selectedClothesCard.relativePath }}</p>
            <div class="clothes-detail-meta">
              <span>文件大小 <b>{{ ctx.formatBytes(ctx.selectedClothesCard.fileSize) }}</b></span>
              <span>修改时间 <b>{{ ctx.selectedClothesCard.modifiedAt || '-' }}</b></span>
            </div>
            <button class="clothes-open-directory" type="button" @click="ctx.openClothesDirectory(ctx.selectedClothesCard.directory)">打开所在目录</button>
          </div>
          <div v-else-if="ctx.clothesDetailTab === '关联'" class="clothes-detail-tab-panel">
            <div v-if="ctx.clothesLibrary.detailLoading" class="detail-inline-state">正在解析服装卡依赖...</div>
            <div v-else-if="!ctx.selectedClothesCard.dependencies?.length" class="clothes-detail-empty">暂无关联物品。</div>
            <div v-else class="card-dependency-browser clothes-dependency-browser">
              <div class="card-dependency-overview">
                <span><strong>{{ ctx.selectedClothesCard.dependencies.length }}</strong>项物品依赖</span>
              </div>
              <section
                v-for="group in clothesDependencyGroups"
                :key="group.key"
                class="card-dependency-group"
                :class="`tone-${group.tone}`"
              >
                <header class="card-dependency-group-head">
                  <span class="dependency-group-title">
                    <strong>{{ group.label }}</strong>
                  </span>
                  <span class="dependency-group-count">{{ group.items.length }}</span>
                </header>
                <div class="card-dependency-list">
                  <div
                    v-for="dependency in group.items"
                    :key="dependency.id || `${dependency.property}-${dependency.slot}-${dependency.local_slot}`"
                    class="card-dependency-item"
                    :class="dependency.status.state"
                    role="button"
                    tabindex="0"
                    :title="`${dependency.partLabel} · ${dependency.property || '无内部属性'} · ${dependency.status.label}`"
                    @click="ctx.openCardDependencyItem(dependency)"
                    @keydown.enter.prevent="ctx.openCardDependencyItem(dependency)"
                    @keydown.space.prevent="ctx.openCardDependencyItem(dependency)"
                  >
                    <span class="item-thumb" :class="dependency.item ? ctx.badgeClass(dependency.item.status) : 'missing'">
                      <LazyThumbnail
                        v-if="dependency.item?.thumbnailUrl"
                        :src="dependency.item.thumbnailUrl"
                        :alt="dependency.displayName + ' thumbnail'"
                      />
                      <span v-else>{{ dependency.matched ? 'PNG' : 'MISS' }}</span>
                    </span>
                    <span class="card-dependency-main">
                      <strong>{{ dependency.displayName }}</strong>
                      <span class="dependency-item-meta">
                        <span class="dependency-part-label">{{ dependency.partLabel }}</span>
                        <small>{{ dependency.sourceName }}</small>
                      </span>
                    </span>
                    <span class="dependency-match-actions">
                      <span class="dependency-match-state" :class="dependency.status.state">{{ dependency.status.label }}</span>
                    </span>
                  </div>
                </div>
              </section>
            </div>
          </div>
        </template>
        <div v-else class="clothes-detail-empty">选择一张服装卡查看依赖与文件信息。</div>
      </div>
    </aside>
  </div>
</section>
<section v-else class="view scene-card-view">
  <div class="scene-card-layout">
    <section class="panel clothes-browser-panel scene-browser-panel">
      <div class="module-head clothes-browser-head">
        <div>
          <h1>场景卡浏览器（{{ ctx.sceneCardCountText }}）</h1>
          <p class="subtext mono">UserData/studio/scene{{ ctx.selectedSceneFolder ? `/${ctx.selectedSceneFolder}` : '' }}</p>
        </div>
        <button
          class="module-icon-button card-browser-refresh-button"
          type="button"
          :disabled="ctx.sceneLibrary.loading || !ctx.sceneLibrary.validGameDir"
          aria-label="刷新场景卡库"
          title="刷新场景卡库"
          @click="ctx.refreshSceneCards"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <path d="M20 11a8 8 0 0 0-14.8-4L3.5 9" />
            <path d="M3.5 4.5V9h4.5" />
            <path d="M4 13a8 8 0 0 0 14.8 4L20.5 15" />
            <path d="M20.5 19.5V15H16" />
          </svg>
        </button>
      </div>

      <div ref="sceneCardGrid" class="card-grid clothes-card-grid scene-card-grid" @scroll.passive="handleSceneCardGridScroll">
        <div v-if="ctx.sceneLibrary.loading && !ctx.sceneCards.length" class="clothes-card-state">
          <LoadingAnimation class="card-loading-animation" :animation-data="characterCardLoadingAnimation" />
          <strong>正在读取场景卡</strong>
        </div>
        <div v-else-if="ctx.sceneLibrary.checked && !ctx.sceneLibrary.validGameDir" class="clothes-card-state">
          <strong>请选择有效的游戏目录</strong>
          <span class="subtext">需要存在 UserData/studio/scene</span>
        </div>
        <div v-else-if="ctx.sceneLibrary.error" class="clothes-card-state">
          <strong>{{ ctx.sceneLibrary.error }}</strong>
        </div>
        <div v-else-if="!ctx.visibleSceneCards.length" class="clothes-card-state">
          <strong>当前目录没有场景卡</strong>
          <span class="subtext mono">UserData/studio/scene{{ ctx.selectedSceneFolder ? `/${ctx.selectedSceneFolder}` : '' }}</span>
        </div>
        <VirtualClothesCardGrid
          v-else-if="ctx.visibleSceneCards.length"
          :rows="ctx.visibleSceneCards"
          :selected-id="ctx.selectedSceneDetailPath"
          variant="scene"
          :aspect-width="320"
          :aspect-height="180"
          aria-label="场景卡列表"
          @card-click="ctx.handleSceneCardClick"
        />
        <div v-if="ctx.sceneLibrary.loadingMore" class="clothes-card-load-more">正在继续读取场景卡…</div>
      </div>
    </section>

    <aside class="panel side-panel character-side-panel clothes-side-panel scene-side-panel">
      <div class="module-head character-side-head">
        <div>
          <h2>{{ ctx.sceneSideMode === 'tree' ? '场景卡目录' : '场景卡详情' }}</h2>
          <p class="subtext">{{ ctx.sceneSideMode === 'tree' ? 'UserData/studio/scene' : '当前场景卡' }}</p>
        </div>
        <div class="side-toggle" aria-label="场景卡侧栏视图">
          <button type="button" :class="{ active: ctx.sceneSideMode === 'tree' }" @click="ctx.sceneSideMode = 'tree'">目录</button>
          <button type="button" :class="{ active: ctx.sceneSideMode === 'detail' }" @click="ctx.sceneSideMode = 'detail'">详情</button>
        </div>
      </div>

      <div v-if="ctx.sceneSideMode === 'tree'" class="clothes-directory-section">
        <div class="clothes-directory-tree">
          <div
            v-for="folder in ctx.sceneFolders"
            :key="folder.id"
            class="tree-row clothes-tree-row"
            :class="{ active: ctx.selectedSceneFolder === folder.relativePath }"
            :style="{ paddingLeft: `${10 + folder.depth * 18}px` }"
            role="button"
            tabindex="0"
            :aria-expanded="folder.hasChildren ? folder.expanded : undefined"
            @click="ctx.selectSceneFolder(folder.relativePath)"
            @keydown.enter.prevent="ctx.selectSceneFolder(folder.relativePath)"
            @keydown.space.prevent="ctx.selectSceneFolder(folder.relativePath)"
          >
            <button
              type="button"
              class="tree-toggle clothes-tree-toggle"
              :class="{ placeholder: !folder.hasChildren }"
              :disabled="!folder.hasChildren"
              :aria-label="folder.hasChildren ? `${folder.expanded ? '收起' : '展开'} ${folder.name}` : undefined"
              @click.stop="ctx.toggleSceneFolder(folder)"
              @keydown.enter.stop="ctx.toggleSceneFolder(folder)"
              @keydown.space.prevent.stop="ctx.toggleSceneFolder(folder)"
            >{{ folder.hasChildren ? (folder.expanded ? '-' : '+') : '·' }}</button>
            <span class="tree-name clothes-folder-name">{{ folder.name }}</span>
            <span class="clothes-folder-count">{{ folder.count }}</span>
          </div>
        </div>
      </div>

      <div v-else class="clothes-detail-section">
        <template v-if="ctx.selectedSceneCard">
          <div class="clothes-detail-preview scene-detail-preview">
            <img class="scene-detail-preview-image" :src="ctx.selectedSceneCard.thumbnailUrl || ctx.selectedSceneCard.coverUrl" :alt="ctx.selectedSceneCard.name + ' preview'">
          </div>
          <div class="tabs mod-detail-tabs clothes-detail-tabs scene-detail-tabs" role="tablist" aria-label="场景卡详情视图">
            <button
              type="button"
              role="tab"
              :aria-selected="ctx.sceneDetailTab === '详情'"
              :class="{ active: ctx.sceneDetailTab === '详情' }"
              @click="ctx.sceneDetailTab = '详情'"
            >详情</button>
            <button
              type="button"
              role="tab"
              :aria-selected="ctx.sceneDetailTab === '关联'"
              :class="{ active: ctx.sceneDetailTab === '关联' }"
              @click="ctx.sceneDetailTab = '关联'"
            >关联</button>
          </div>
          <div v-if="ctx.sceneDetailTab === '详情'" class="clothes-detail-tab-panel">
            <h2 class="clothes-detail-title">{{ ctx.selectedSceneCard.name }}</h2>
            <p class="subtext mono clothes-detail-path">{{ ctx.selectedSceneCard.relativePath }}</p>
            <div class="clothes-detail-meta">
              <span>文件大小 <b>{{ ctx.formatBytes(ctx.selectedSceneCard.fileSize) }}</b></span>
              <span>修改时间 <b>{{ ctx.selectedSceneCard.modifiedAt || '-' }}</b></span>
            </div>
            <button class="clothes-open-directory" type="button" @click="ctx.openSceneDirectory(ctx.selectedSceneCard.directory)">打开所在目录</button>
          </div>
          <div v-else-if="ctx.sceneDetailTab === '关联'" class="clothes-detail-tab-panel">
            <div v-if="ctx.sceneLibrary.detailLoading" class="detail-inline-state">正在解析场景卡依赖...</div>
            <div v-else-if="!ctx.selectedSceneCard.dependencies?.length" class="clothes-detail-empty">暂无关联模组。</div>
            <div v-else class="card-dependency-browser scene-dependency-browser">
              <div class="card-dependency-overview">
                <span>
                  <strong>{{ sceneDependencyDisplayCount }}</strong>项场景依赖
                  <small v-if="ctx.sceneDependencyRemoteSummary.availableCount">可补全 {{ ctx.sceneDependencyRemoteSummary.availableCount }} 个模组</small>
                </span>
                <div class="card-dependency-overview-actions">
                  <button
                    v-if="ctx.sceneDependencyRemoteSummary.missingCount > 0 && ctx.sceneDependencyRemoteSummary.availableCount > 0"
                    type="button"
                    class="card-dependency-install-all"
                    :disabled="ctx.cardDependencyRemoteBusy && !ctx.cardDependencyRemote.allTaskId"
                    :title="ctx.cardDependencyRemote.allTaskId ? (ctx.cardDependencyRemote.allStatus === 'paused' ? '点击继续任务' : '点击暂停任务') : '安装全部可获取的缺失模组'"
                    @click.stop="ctx.cardDependencyRemote.allTaskId ? ctx.toggleAllCardDependencies() : ctx.installAllCardDependencies()"
                  >
                    {{ ctx.cardDependencyRemote.allTaskId
                      ? (ctx.cardDependencyRemote.allStatus === 'paused' ? '继续全部' : '暂停全部')
                      : (ctx.cardDependencyRemoteBusy ? '准备中...' : '全部安装') }}
                  </button>
                </div>
              </div>
              <section
                v-for="group in sceneDependencyGroups"
                :key="group.key"
                class="card-dependency-group"
                :class="`tone-${group.tone}`"
              >
                <header class="card-dependency-group-head">
                  <span class="dependency-group-title"><strong>{{ group.label }}</strong></span>
                  <span class="dependency-group-count">{{ group.items.length }}</span>
                </header>
                <div class="card-dependency-list">
                  <div
                    v-for="dependency in group.items"
                    :key="dependency.id || `${dependency.property}-${dependency.mod_id}`"
                    class="card-dependency-item"
                    :class="dependency.status.state"
                    role="button"
                    tabindex="0"
                    :title="`${dependency.partLabel} · ${dependency.status.label}`"
                    @click="ctx.openCardDependencyItem(dependency)"
                    @keydown.enter.prevent="ctx.openCardDependencyItem(dependency)"
                    @keydown.space.prevent="ctx.openCardDependencyItem(dependency)"
                  >
                    <span class="item-thumb" :class="dependency.item ? ctx.badgeClass(dependency.item.status) : (dependency.matched ? 'ok' : 'missing')">
                      <LazyThumbnail
                        v-if="dependency.item?.thumbnailUrl"
                        :src="dependency.item.thumbnailUrl"
                        :alt="dependency.displayName + ' thumbnail'"
                      />
                      <span v-else>{{ dependency.displayMode === 'mod' ? 'MOD' : (dependency.dependency_type === 'scene' ? (dependency.matched ? 'MAP' : 'MISS') : (dependency.matched ? 'ITEM' : 'MISS')) }}</span>
                    </span>
                    <span class="card-dependency-main">
                      <strong>{{ dependency.displayName }}</strong>
                      <span class="dependency-item-meta">
                        <span class="dependency-part-label">{{ dependency.partLabel }}</span>
                        <small>{{ dependency.sourceName }}</small>
                        <small v-if="dependency.displayMode === 'mod'">已合并同模组缺失项</small>
                      </span>
                    </span>
                    <span class="dependency-match-actions">
                      <span
                        v-if="dependency.status.state === 'matched'"
                        class="dependency-match-state"
                        :class="dependency.status.state"
                      >
                        {{ dependency.status.label }}
                      </span>
                      <template v-if="['mod-missing', 'item-missing'].includes(dependency.status.state)">
                        <div v-if="ctx.cardDependencyInlineProgress(dependency)" class="dependency-inline-progress" aria-live="polite">
                          <div class="dependency-inline-progress-head">
                            <span>{{ ctx.cardDependencyInlineProgress(dependency).phase === 'download' ? '下载' : '安装' }}</span>
                            <span class="dependency-inline-progress-actions">
                              <strong>{{ Math.round(ctx.cardDependencyInlineProgress(dependency).phase === 'download' ? ctx.cardDependencyInlineProgress(dependency).downloadProgress : ctx.cardDependencyInlineProgress(dependency).installProgress) }}%</strong>
                              <button
                                type="button"
                                class="dependency-inline-control"
                                :title="ctx.cardDependencyRemote.statuses[ctx.normalizeCardDependencyGuid(dependency)] === 'paused' ? '继续任务' : '暂停任务'"
                                :aria-label="ctx.cardDependencyRemote.statuses[ctx.normalizeCardDependencyGuid(dependency)] === 'paused' ? '继续任务' : '暂停任务'"
                                @click.stop="ctx.installCardDependency(dependency)"
                              >
                                <svg v-if="ctx.cardDependencyRemote.statuses[ctx.normalizeCardDependencyGuid(dependency)] === 'paused'" viewBox="0 0 24 24" aria-hidden="true">
                                  <path d="M8 5.5v13l10-6.5L8 5.5Z" />
                                </svg>
                                <svg v-else viewBox="0 0 24 24" aria-hidden="true">
                                  <path d="M7 5v14M17 5v14" />
                                </svg>
                              </button>
                            </span>
                          </div>
                          <template v-if="ctx.cardDependencyInlineProgress(dependency).phase === 'download'">
                            <div class="dependency-inline-progress-stage download">
                              <div class="dependency-inline-progress-track"><span :style="{ width: `${ctx.cardDependencyInlineProgress(dependency).downloadProgress}%` }"></span></div>
                              <small>{{ ctx.formatDownloadSpeed(ctx.cardDependencyInlineProgress(dependency).downloadSpeedBps) }}</small>
                            </div>
                          </template>
                          <template v-else-if="ctx.cardDependencyInlineProgress(dependency).phase === 'install'">
                            <div class="dependency-inline-progress-stage install">
                              <div class="dependency-inline-progress-track"><span :style="{ width: `${ctx.cardDependencyInlineProgress(dependency).installProgress}%` }"></span></div>
                              <small>正在写入索引</small>
                            </div>
                          </template>
                        </div>
                        <button
                          v-if="ctx.cardDependencyRemote.taskIds[ctx.normalizeCardDependencyGuid(dependency)]"
                          type="button"
                          class="dependency-cancel-download"
                          title="取消下载"
                          @click.stop="ctx.cancelCardDependency(dependency)"
                        >
                          取消下载
                        </button>
                        <button
                          v-else-if="ctx.cardDependencyRemoteFor(dependency)?.status === 'available'"
                          type="button"
                          class="dependency-install-button"
                          title="安装此模组"
                          @click.stop="ctx.installCardDependency(dependency)"
                        >
                          {{ ctx.cardDependencyRemote.busyGuids[ctx.normalizeCardDependencyGuid(dependency)] ? '准备中...' : '安装' }}
                        </button>
                        <span
                          v-else-if="ctx.cardDependencyRemoteFor(dependency)?.status === 'unavailable'"
                          class="dependency-unavailable-label"
                        >
                          无法获取
                        </span>
                        <span v-else class="dependency-checking-label">检查中</span>
                        <small
                          v-if="ctx.cardDependencyRemote.notices[ctx.normalizeCardDependencyGuid(dependency)]"
                          class="dependency-install-notice"
                        >
                          {{ ctx.cardDependencyRemote.notices[ctx.normalizeCardDependencyGuid(dependency)] }}
                        </small>
                      </template>
                    </span>
                  </div>
                </div>
              </section>
            </div>
          </div>
        </template>
        <div v-else class="clothes-detail-empty">选择一张场景卡查看依赖与文件信息。</div>
      </div>
    </aside>
  </div>
</section>
</template>
