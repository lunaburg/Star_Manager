<script setup>
import { computed } from "vue";
import LazyThumbnail from "../LazyThumbnail.vue";

const { ctx } = defineProps({
  ctx: { type: Object, required: true }
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
  { key: "clothes", label: "服装", marker: "衣", tone: "blue" },
  { key: "accessory", label: "配饰", marker: "饰", tone: "mint" },
  { key: "face", label: "面部与五官", marker: "脸", tone: "rose" },
  { key: "hair", label: "发型", marker: "发", tone: "violet" },
  { key: "body", label: "身体与肌肤", marker: "身", tone: "amber" },
  { key: "other", label: "其他依赖", marker: "其", tone: "gray" }
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
  if (dependency.matched) return { label: "已匹配", state: "matched" };
  if (dependency.zipmod) return { label: "物品未找到", state: "item-missing" };
  return { label: "模组未安装", state: "mod-missing" };
}

const cardDependencyGroups = computed(() => {
  const buckets = new Map(DEPENDENCY_GROUPS.map((group) => [group.key, []]));
  for (const dependency of ctx.selectedCardDependencies || []) {
    const descriptor = dependencyDescriptor(dependency);
    buckets.get(descriptor.group).push({
      ...dependency,
      partLabel: descriptor.part,
      displayName: dependency.item?.name || dependency.name || dependency.mod_id || "未知物品",
      sourceName: dependency.item?.source_mod || dependency.zipmod?.name || dependency.mod_id || "来源未知",
      status: dependencyStatus(dependency)
    });
  }
  return DEPENDENCY_GROUPS
    .map((group) => {
      const items = buckets.get(group.key);
      return {
        ...group,
        items,
        missingCount: items.filter((item) => !item.matched).length,
        partSummary: [...new Set(items.map((item) => item.partLabel))].join(" · ")
      };
    })
    .filter((group) => group.items.length > 0);
});
</script>

<template>
<section class="view">
          <div class="character-layout">
            <section class="panel browser-panel">
              <div class="module-head">
                <div><h1>人物卡浏览器（{{ ctx.cardBrowserCountText }}）</h1><p class="subtext mono">{{ ctx.cardFolderDisplay }}</p></div>
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
                </div>
                <div class="toolbar-right">
                  <select
                    :value="ctx.cardDependencyFilter.startsWith('tag:') ? 'all' : ctx.cardDependencyFilter"
                    aria-label="人物卡筛选"
                    title="筛选人物卡"
                    @change="ctx.setCardDependencyFilter($event.target.value)"
                  >
                    <option value="all">全部人物卡</option>
                    <option value="favorite">已收藏</option>
                    <option value="missing">依赖缺失</option>
                  </select>
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
                  <button
                    v-if="ctx.cardBulkMode"
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
                    v-if="ctx.cardBulkMode"
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
                    v-if="ctx.cardBulkMode"
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
                    :disabled="!ctx.cardBulkMode || ctx.selectedCount === 0 || ctx.isBusy"
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
              <div class="card-grid">
                <div v-if="ctx.cardTagFilter.resultsLoading" class="card-state">
                  <strong>正在筛选整个人物卡库</strong>
                  <span class="subtext">正在查找带有“{{ ctx.cardTagFilter.libraryTag }}”标签的人物卡</span>
                </div>
                <div v-else-if="ctx.cardTagFilter.resultsError" class="card-state">
                  <strong>全库标签筛选失败</strong>
                  <span class="subtext">{{ ctx.cardTagFilter.resultsError }}</span>
                </div>
                <div v-else-if="ctx.cardLibrary.loading && ctx.cards.length === 0" class="card-state">
                  <strong>正在加载人物卡</strong>
                </div>
                <div v-else-if="ctx.cardLibrary.checked && !ctx.cardLibrary.validGameDir" class="card-state">
                  <strong>请选择有效的游戏目录</strong>
                </div>
                <div v-else-if="ctx.cardLibrary.error" class="card-state">
                  <strong>{{ ctx.cardLibrary.error }}</strong>
                </div>
                <div v-else-if="ctx.visibleCards.length === 0" class="card-state">
                  <strong>{{ ctx.cardDependencyFilter === 'missing' && ctx.cards.length ? '当前目录没有依赖缺失的人物卡' : ctx.cardDependencyFilter === 'favorite' && ctx.cards.length ? '当前目录还没有收藏的人物卡' : ctx.cardDependencyFilter.startsWith('tag:') && ctx.cardTagFilter.scope === 'library' ? `人物卡库中没有“${ctx.cardDependencyFilter.slice(4)}”标签的人物卡` : ctx.cardDependencyFilter.startsWith('tag:') && ctx.cards.length ? `当前目录没有“${ctx.cardDependencyFilter.slice(4)}”标签的人物卡` : '未找到人物卡' }}</strong>
                  <span class="subtext mono">{{ ctx.cardTagFilter.scope === 'library' && ctx.cardDependencyFilter.startsWith('tag:') ? 'UserData/chara · 全库' : ctx.cardFolderDisplay }}</span>
                </div>
                <template v-else>
                  <div
                    v-for="card in ctx.visibleCards"
                    :key="card.id"
                    role="button"
                    tabindex="0"
                    class="char-card"
                    :class="{ selected: ctx.selectedCards.has(card.absolutePath), favorite: card.favorite, 'favorite-theme-neon': card.favorite && ctx.managerSettings.favoriteCardTheme === 'neon', 'favorite-theme-sakura': card.favorite && ctx.managerSettings.favoriteCardTheme === 'sakura', 'favorite-theme-obsidian': card.favorite && ctx.managerSettings.favoriteCardTheme === 'obsidian', 'bulk-mode': ctx.cardBulkMode }"
                    :aria-pressed="ctx.selectedCards.has(card.absolutePath)"
                    @click="ctx.handleCardClick(card)"
                    @keydown.enter.prevent="ctx.handleCardClick(card)"
                    @keydown.space.prevent="ctx.handleCardClick(card)"
                  >
                    <span v-if="ctx.selectedCards.has(card.absolutePath)" class="check">✓</span>
                    <span v-if="card.missingCount > 0" class="card-missing-badge">缺 {{ card.missingCount }}</span>
                    <span class="portrait">
                      <LazyThumbnail :src="card.thumbnailUrl" :alt="card.name + ' preview'" />
                    </span>
                    <span v-if="card.favorite && ctx.managerSettings.favoriteCardTheme === 'sakura'" class="card-theme-petals" aria-hidden="true">
                      <i v-for="petalIndex in 5" :key="petalIndex"></i>
                    </span>
                    <span v-if="card.favorite && ctx.managerSettings.favoriteCardTheme === 'obsidian'" class="card-theme-embers" aria-hidden="true">
                      <i v-for="emberIndex in 6" :key="emberIndex"></i>
                    </span>
                    <span
                      v-if="card.tags?.length"
                      class="card-hover-tags"
                      role="tooltip"
                      aria-label="人物卡标签"
                    >
                      <span class="card-hover-tag-list">
                        <span
                          v-for="tag in card.tags"
                          :key="tag"
                          class="card-hover-tag"
                          :class="cardTagTone(tag)"
                        >
                          {{ tag }}
                        </span>
                      </span>
                    </span>
                    <span class="card-caption">
                      <strong v-card-name-scroll><span class="card-name-text">{{ card.name }}</span></strong>
                      <span>{{ card.modifiedAt }}</span>
                    </span>
                  </div>
                </template>
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
                  <div v-if="ctx.cardDetailTab === '详情'" class="drawer-tab-panel active">
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
                      <div class="profile-section-head">
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
                          <div class="profile-birthday-fields">
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
                  <div v-else-if="ctx.cardDetailTab === '关联'" class="drawer-tab-panel active">
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
                          <small>{{ cardDependencyGroups.length }} 个部位分组</small>
                        </div>
                        <section
                          v-for="group in cardDependencyGroups"
                          :key="group.key"
                          class="card-dependency-group"
                          :class="`tone-${group.tone}`"
                        >
                          <header class="card-dependency-group-head">
                            <span class="dependency-group-marker" aria-hidden="true">{{ group.marker }}</span>
                            <span class="dependency-group-title">
                              <strong>{{ group.label }}</strong>
                              <small>{{ group.partSummary }}</small>
                            </span>
                            <span class="dependency-group-count">
                              {{ group.items.length }}
                              <small v-if="group.missingCount">缺 {{ group.missingCount }}</small>
                            </span>
                          </header>
                          <div class="card-dependency-list">
                            <button
                              v-for="dependency in group.items"
                              :key="dependency.id"
                              type="button"
                              class="card-dependency-item"
                              :class="dependency.status.state"
                              :title="`${dependency.partLabel} · ${dependency.property || '无内部属性'} · ${dependency.status.label}`"
                              @click="ctx.openCardDependencyItem(dependency)"
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
                              <span class="dependency-match-state" :class="dependency.status.state">
                                {{ dependency.status.label }}
                              </span>
                            </button>
                          </div>
                        </section>
                      </div>
                    </div>
                  </div>
                  <div v-else class="drawer-tab-panel active">
                    <div class="drawer-section mod-detail-section">
                      <span class="drawer-section-title">工具</span>
                      <div class="card-tool-stack">
                        <div class="character-tool-card">
                          <span class="character-tool-icon" aria-hidden="true">
                            <svg viewBox="0 0 24 24"><path d="M7 4h10v4a5 5 0 0 1-10 0V4Z"/><path d="M5 21v-4a5 5 0 0 1 5-5h4a5 5 0 0 1 5 5v4"/><path d="M9 7h.01M15 7h.01"/><path d="m18.5 3 .5 1.2 1.2.5-1.2.5-.5 1.2-.5-1.2-1.2-.5 1.2-.5.5-1.2Z"/></svg>
                          </span>
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
                          <span class="character-tool-icon" aria-hidden="true">
                            <svg viewBox="0 0 24 24"><path d="M8 3h8l3 3v15H5V3h3Z"/><path d="M14 3v5h5M8 13h8M8 17h5"/></svg>
                          </span>
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
                          <span class="character-tool-icon" aria-hidden="true">
                            <svg viewBox="0 0 24 24"><path d="M4 7h16v13H4V7Z"/><path d="M8 7V4h8v3M4 11h16M10 14h4"/></svg>
                          </span>
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
                      </div>
                    </div>
                  </div>
                </template>
              </div>
            </aside>
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
                  <span>选择已有标签，或创建一个新标签</span>
                </div>
                <span class="card-tag-selection-count">{{ ctx.cardTagPrompt.selected.length }} / 12</span>
              </div>
              <div class="card-tag-prompt-section">
                <span class="card-tag-prompt-label">已有标签</span>
                <div v-if="ctx.cardTagPrompt.loading" class="card-tag-prompt-empty">正在读取标签...</div>
                <div v-else-if="ctx.cardTagPrompt.available.length" class="card-tag-choice-list">
                  <button
                    v-for="(tag, tagIndex) in ctx.cardTagPrompt.available"
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
                <div v-else class="card-tag-prompt-empty">还没有可复用的标签</div>
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
