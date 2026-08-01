<script setup>
import { computed, ref } from "vue";
import ModelPreview from "../ModelPreview.vue";
import LazyThumbnail from "../LazyThumbnail.vue";

const { ctx } = defineProps({
  ctx: { type: Object, required: true }
});

const modelPreview = ref(null);
const modelPreviewReady = ref(false);
const thumbnailChoiceOpen = ref(false);
const thumbnailChoiceBusy = ref(false);
const thumbnailChoiceError = ref("");
const kindFilterOpen = ref(false);

const selectedKindOption = computed(() => (
  ctx.itemKindOptions.find((option) => option.value === ctx.itemFilters.kind)
  || ctx.itemKindOptions[0]
));
const selectedItemIsClothing = computed(() => (
  String(ctx.selectedItem?.kind || "").includes("\u670d\u9970")
));

function kindOptionParts(option) {
  if (!option?.value) return { category: "all", gender: "", text: option?.label || "\u5168\u90e8 Kind" };
  const segments = String(option.label || "").split("/");
  const hasGender = segments[0] === "\u2642" || segments[0] === "\u2640";
  const category = hasGender ? segments[1] : segments[0];
  const textSegments = hasGender ? segments.slice(2) : segments.slice(1);
  return {
    category: ["\u9762\u90e8", "\u8eab\u4f53", "\u670d\u9970", "\u5934\u53d1", "\u9970\u54c1"].includes(category) ? category : "other",
    gender: hasGender ? segments[0] : "",
    text: textSegments.length ? textSegments.join("/") : String(option.label || "")
  };
}

function selectKindOption(option) {
  ctx.itemFilters.kind = option.value;
  kindFilterOpen.value = false;
  ctx.applyItemFilters();
}

function closeKindFilterSoon() {
  window.setTimeout(() => { kindFilterOpen.value = false; }, 100);
}

function openThumbnailChoice() {
  thumbnailChoiceError.value = "";
  thumbnailChoiceOpen.value = true;
}

async function importThumbnailFromFile() {
  thumbnailChoiceOpen.value = false;
  await ctx.repairThumbnailItem(ctx.selectedItem);
}

async function importThumbnailFromPreview() {
  if (!modelPreviewReady.value || thumbnailChoiceBusy.value) return;
  thumbnailChoiceBusy.value = true;
  thumbnailChoiceError.value = "";
  try {
    const imageData = await modelPreview.value?.captureScreenshot?.();
    if (!imageData) throw new Error("无法取得 3D 预览画面");
    const imported = await ctx.repairThumbnailItem(ctx.selectedItem, { imageData });
    if (!imported) throw new Error("缩略图写入失败，请查看运行日志");
    thumbnailChoiceOpen.value = false;
  } catch (error) {
    thumbnailChoiceError.value = error instanceof Error ? error.message : String(error);
  } finally {
    thumbnailChoiceBusy.value = false;
  }
}

const MOD_STATUS_TONES = {
  normal: "ok",
  warning: "warn",
  manifest_author: "warn",
  unity3d_in_game: "warn",
  thumbnail: "warn",
  duplicate_zipmod: "warn",
  error: "danger",
  read_error: "danger",
  unity3d_missing: "danger",
  unity3d_error: "danger"
};

function modStatusTone(status) {
  return MOD_STATUS_TONES[status] || "neutral";
}
</script>

<template>
  <section class="view">
    <div class="mod-layout mod-management-layout">
      <section class="panel browser-panel mod-page">
        <div class="module-head mod-head">
          <h1>模组管理</h1>
          <div class="library-summary mod-summary">
            <span class="badge ok">{{ ctx.formatStat(ctx.stats.zipmods) }} zipmod</span>
            <span class="badge">{{ ctx.formatStat(ctx.stats.modItems) }} items</span>
            <span class="badge warn">{{ ctx.formatStat(ctx.stats.zipmodWarnings) }} warnings</span>
            <span class="badge danger">{{ ctx.formatStat(ctx.stats.zipmodErrors) }} errors</span>
            <span class="badge neutral">last {{ ctx.formatDatabaseTime(ctx.stats.lastDatabaseBuiltAt) }}</span>
          </div>
        </div>

        <div class="mod-strip">
          <div class="mode-strip mod-tabs">
            <button :class="{ active: ctx.libraryMode === 'mods' }" type="button" @click="ctx.setLibraryMode('mods')">模组浏览</button>
            <button :class="{ active: ctx.libraryMode === 'items' }" type="button" @click="ctx.setLibraryMode('items')">物品浏览</button>
          </div>
          <div class="dependency-usage-filter" aria-label="角色卡依赖筛选">
            <button
              v-for="option in ctx.dependencyUsageOptions"
              :key="option.value || 'all'"
              type="button"
              :class="{ active: ctx.dependencyUsageFilter === option.value }"
              @click="ctx.setDependencyUsageFilter(option.value)"
            >
              {{ option.label }}
            </button>
          </div>
        </div>

        <div class="toolbar library-toolbar">
          <div v-if="ctx.libraryMode === 'items'" class="toolbar-left filter-grid items">
            <input
              v-model="ctx.itemFilters.search"
              class="search"
              aria-label="搜索物品名字或模组 GUID"
              placeholder="搜索物品名字 / 模组 GUID"
              @input="ctx.scheduleItemSearch"
            >
            <div class="kind-filter-select" @focusout="closeKindFilterSoon" @keydown.esc="kindFilterOpen = false">
              <button
                type="button"
                class="kind-filter-trigger"
                :class="`kind-option-${selectedKindOption.gender}`"
                aria-label="Kind 筛选"
                aria-haspopup="listbox"
                :aria-expanded="kindFilterOpen"
                @click="kindFilterOpen = !kindFilterOpen"
              >
                <span class="kind-option-content">
                  <span v-if="kindOptionParts(selectedKindOption).gender" class="kind-gender">{{ kindOptionParts(selectedKindOption).gender }}</span>
                  <svg v-if="kindOptionParts(selectedKindOption).category === '面部'" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="8"></circle><path d="M9 10h.01M15 10h.01M9 15c1.8 1.3 4.2 1.3 6 0"></path></svg>
                  <svg v-else-if="kindOptionParts(selectedKindOption).category === '身体'" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="5" r="2.5"></circle><path d="M8.5 21 10 14 7 10l2-2h6l2 2-3 4 1.5 7M10 14h4"></path></svg>
                  <svg v-else-if="kindOptionParts(selectedKindOption).category === '服饰'" viewBox="0 0 24 24" aria-hidden="true"><path d="m8 5-5 4 3 4 2-1v8h8v-8l2 1 3-4-5-4c-.8 1.2-2.1 2-4 2s-3.2-.8-4-2Z"></path></svg>
                  <svg v-else-if="kindOptionParts(selectedKindOption).category === '头发'" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 20c1-3 1-6 1-9a6 6 0 0 1 12 0c0 3 0 6 1 9M8 20c1-4 1-8 1-12M12 20V7M16 20c-1-4-1-8-1-12"></path></svg>
                  <svg v-else-if="kindOptionParts(selectedKindOption).category === '饰品'" viewBox="0 0 24 24" aria-hidden="true"><path d="m12 3 2.1 5.2L20 9l-4.4 3.8L17 19l-5-3.2L7 19l1.4-6.2L4 9l5.9-.8L12 3Z"></path><circle cx="12" cy="12" r="2.2"></circle></svg>
                  <span>{{ kindOptionParts(selectedKindOption).text }}</span>
                </span>
                <span class="kind-filter-chevron" aria-hidden="true">▾</span>
              </button>
              <div v-if="kindFilterOpen" class="kind-option-list" role="listbox" aria-label="Kind 筛选选项">
                <button
                  v-for="kind in ctx.itemKindOptions"
                  :key="kind.value || 'all'"
                  type="button"
                  role="option"
                  :aria-selected="ctx.itemFilters.kind === kind.value"
                  :class="[`kind-option-${kind.gender}`, { active: ctx.itemFilters.kind === kind.value }]"
                  @mousedown.prevent="selectKindOption(kind)"
                >
                  <span class="kind-option-content">
                    <span v-if="kindOptionParts(kind).gender" class="kind-gender">{{ kindOptionParts(kind).gender }}</span>
                    <svg v-if="kindOptionParts(kind).category === '面部'" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="8"></circle><path d="M9 10h.01M15 10h.01M9 15c1.8 1.3 4.2 1.3 6 0"></path></svg>
                    <svg v-else-if="kindOptionParts(kind).category === '身体'" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="5" r="2.5"></circle><path d="M8.5 21 10 14 7 10l2-2h6l2 2-3 4 1.5 7M10 14h4"></path></svg>
                    <svg v-else-if="kindOptionParts(kind).category === '服饰'" viewBox="0 0 24 24" aria-hidden="true"><path d="m8 5-5 4 3 4 2-1v8h8v-8l2 1 3-4-5-4c-.8 1.2-2.1 2-4 2s-3.2-.8-4-2Z"></path></svg>
                    <svg v-else-if="kindOptionParts(kind).category === '头发'" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 20c1-3 1-6 1-9a6 6 0 0 1 12 0c0 3 0 6 1 9M8 20c1-4 1-8 1-12M12 20V7M16 20c-1-4-1-8-1-12"></path></svg>
                    <svg v-else-if="kindOptionParts(kind).category === '饰品'" viewBox="0 0 24 24" aria-hidden="true"><path d="m12 3 2.1 5.2L20 9l-4.4 3.8L17 19l-5-3.2L7 19l1.4-6.2L4 9l5.9-.8L12 3Z"></path><circle cx="12" cy="12" r="2.2"></circle></svg>
                    <span>{{ kindOptionParts(kind).text }}</span>
                  </span>
                  <span v-if="ctx.itemFilters.kind === kind.value" class="kind-option-check" aria-hidden="true">✓</span>
                </button>
              </div>
            </div>
            <select v-model="ctx.itemFilters.author" aria-label="作者筛选" @change="ctx.applyItemFilters">
              <option v-for="author in ctx.itemAuthorOptions" :key="author || 'all'" :value="author">
                {{ author || "全部作者" }}
              </option>
            </select>
            <select v-model="ctx.itemFilters.status" aria-label="状态筛选" @change="ctx.applyItemFilters">
              <option value="">全部状态</option>
              <option value="ready">正常</option>
              <option value="error">错误</option>
              <option value="thumb">缩略图异常</option>
            </select>
          </div>

          <button
            v-if="ctx.libraryMode === 'items'"
            class="bulk-delete-error-items-button danger-action"
            type="button"
            title="批量删除当前筛选列表下的所有错误物品"
            aria-label="批量删除当前筛选列表下的所有错误物品"
            :aria-busy="ctx.bulkActionBusy === 'items-delete'"
            :disabled="!ctx.itemDatabase.exists || Boolean(ctx.bulkActionBusy)"
            @click="ctx.openBulkDeleteErrorItemsPrompt"
          >
            删除错误物品
          </button>

          <div v-else class="toolbar-left filter-grid mods">
            <button
              v-if="!ctx.modBulkMode"
              class="bulk-select-button"
              type="button"
              title="进入批量选择模式"
              aria-label="进入批量选择模式"
              @click="ctx.enterModBulkMode"
            >
              多选
            </button>
            <div v-else class="bulk-select-status" aria-live="polite">
              <span>已选 {{ ctx.selectedModCount }} 个</span>
              <button type="button" @click="ctx.exitModBulkMode">退出</button>
            </div>
            <div class="author-combobox">
              <input
                v-model="ctx.modFilters.author"
                type="text"
                aria-label="作者筛选"
                placeholder="全部作者"
                autocomplete="off"
                @focus="ctx.modAuthorFilterOpen = true"
                @blur="ctx.closeModAuthorFilterSoon"
                @input="ctx.modAuthorFilterOpen = true; ctx.scheduleModAuthorFilter()"
                @keydown.enter.prevent="ctx.applyModFilters"
              >
              <button
                class="author-combobox-toggle"
                type="button"
                aria-label="显示作者列表"
                @mousedown.prevent
                @click="ctx.modAuthorFilterOpen = !ctx.modAuthorFilterOpen"
              >
                ▼
              </button>
              <div v-if="ctx.modAuthorFilterOpen" class="author-option-list" role="listbox">
                <button
                  v-for="author in ctx.filteredZipmodAuthorOptions"
                  :key="author || 'all'"
                  type="button"
                  :class="{ active: ctx.modFilters.author === author }"
                  role="option"
                  :aria-selected="ctx.modFilters.author === author"
                  @mousedown.prevent="ctx.selectModAuthorFilter(author)"
                >
                  {{ author || "全部作者" }}
                </button>
                <div v-if="ctx.filteredZipmodAuthorOptions.length === 0" class="author-option-empty">没有匹配作者</div>
              </div>
            </div>
            <select
              v-model="ctx.modFilters.status"
              class="mod-status-filter"
              :class="`status-filter-${modStatusTone(ctx.modFilters.status)}`"
              aria-label="状态筛选"
              @change="ctx.applyModFilters"
            >
              <option class="status-option-neutral" value="">全部状态</option>
              <option class="status-option-neutral" value="abnormal">全部异常</option>
              <option class="status-option-ok" value="normal">正常</option>
              <option class="status-option-warn" value="warning">警告</option>
              <option class="status-option-warn" value="manifest_author">　缺少模组作者</option>
              <option class="status-option-warn" value="unity3d_in_game">　Unity3D 仅在游戏目录</option>
              <option class="status-option-warn" value="thumbnail">　缩略图缺失</option>
              <option class="status-option-warn" value="duplicate_zipmod">　存在重复模组</option>
              <option class="status-option-danger" value="error">错误</option>
              <option class="status-option-danger" value="read_error">　读取错误</option>
              <option class="status-option-danger" value="unity3d_missing">　Unity3D 文件缺失</option>
              <option class="status-option-danger" value="unity3d_error">　Unity3D 资源读取异常</option>
            </select>
          </div>

          <div v-if="ctx.libraryMode === 'mods' && ctx.modBulkMode" class="bulk-action-bar" aria-label="批量操作">
            <button
              class="bulk-icon-button"
              type="button"
              title="导出已选模组"
              aria-label="导出已选模组"
              :aria-busy="ctx.bulkActionBusy === 'export'"
              :disabled="ctx.selectedModCount === 0 || Boolean(ctx.bulkActionBusy)"
              @click="ctx.openBulkExportPrompt"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <path d="M12 4v10" fill="none" stroke="currentColor" stroke-linecap="round"></path>
                <path d="m8 8 4-4 4 4" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"></path>
                <path d="M5 14v5h14v-5" fill="none" stroke="currentColor" stroke-linejoin="round"></path>
              </svg>
            </button>
            <button
              class="bulk-icon-button"
              type="button"
              title="按作者整理已选模组"
              aria-label="按作者整理已选模组"
              :aria-busy="ctx.bulkActionBusy === 'organize'"
              :disabled="ctx.selectedModCount === 0 || Boolean(ctx.bulkActionBusy)"
              @click="ctx.openBulkOrganizePrompt"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <path d="M3 7h7l2 2h9v10H3z" fill="none" stroke="currentColor" stroke-linejoin="round"></path>
                <path d="M7 13h10" fill="none" stroke="currentColor" stroke-linecap="round"></path>
                <path d="M7 16h6" fill="none" stroke="currentColor" stroke-linecap="round"></path>
              </svg>
            </button>
            <button
              class="bulk-icon-button"
              type="button"
              title="批量剪切补入 unity3d"
              aria-label="批量剪切补入 unity3d"
              :aria-busy="ctx.bulkActionBusy === 'unity3d'"
              :disabled="ctx.selectedModCount === 0 || Boolean(ctx.bulkActionBusy)"
              @click="ctx.openBulkRepairUnity3dPrompt"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <path d="M5 4h9l5 5v11H5z" fill="none" stroke="currentColor" stroke-linejoin="round"></path>
                <path d="M14 4v5h5" fill="none" stroke="currentColor" stroke-linejoin="round"></path>
                <path d="M12 17V9" fill="none" stroke="currentColor" stroke-linecap="round"></path>
                <path d="m8.5 13.5 3.5 3.5 3.5-3.5" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"></path>
              </svg>
            </button>
            <button
              class="bulk-icon-button"
              type="button"
              title="智能清理重复模组"
              aria-label="智能清理重复模组"
              :aria-busy="ctx.bulkActionBusy === 'duplicates'"
              :disabled="ctx.selectedModCount === 0 || Boolean(ctx.bulkActionBusy)"
              @click="ctx.openBulkDuplicateCleanupPrompt"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <path d="M14 4 6 12" fill="none" stroke="currentColor" stroke-linecap="round"></path>
                <path d="m12 2 4 4" fill="none" stroke="currentColor" stroke-linecap="round"></path>
                <path d="M5 13h8l2 7H3z" fill="none" stroke="currentColor" stroke-linejoin="round"></path>
                <path d="M7 13v7" fill="none" stroke="currentColor" stroke-linecap="round"></path>
                <path d="M11 13v7" fill="none" stroke="currentColor" stroke-linecap="round"></path>
                <path d="M4 20h12" fill="none" stroke="currentColor" stroke-linecap="round"></path>
              </svg>
            </button>
            <button
              class="bulk-icon-button"
              type="button"
              title="批量删除已选模组"
              aria-label="批量删除已选模组"
              :aria-busy="ctx.bulkActionBusy === 'delete'"
              :disabled="ctx.selectedModCount === 0 || Boolean(ctx.bulkActionBusy)"
              @click="ctx.openBulkDeletePrompt"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <path d="M3 6h18" fill="none" stroke="currentColor" stroke-linecap="round"></path>
                <path d="M8 6V4h8v2" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"></path>
                <path d="M6 6l1 15h10l1-15" fill="none" stroke="currentColor" stroke-linejoin="round"></path>
                <path d="M10 10v7" fill="none" stroke="currentColor" stroke-linecap="round"></path>
                <path d="M14 10v7" fill="none" stroke="currentColor" stroke-linecap="round"></path>
              </svg>
            </button>
            <button
              class="bulk-icon-button"
              type="button"
              title="批量修改作者"
              aria-label="批量修改作者"
              :aria-busy="ctx.bulkActionBusy === 'author'"
              :disabled="ctx.selectedModCount === 0 || Boolean(ctx.bulkActionBusy)"
              @click="ctx.openBulkAuthorPrompt"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <path d="M8 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z" fill="none" stroke="currentColor"></path>
                <path d="M3 21v-2a5 5 0 0 1 5-5h2.5" fill="none" stroke="currentColor" stroke-linecap="round"></path>
                <path d="m14 18 5.5-5.5 2 2L16 20h-2z" fill="none" stroke="currentColor" stroke-linejoin="round"></path>
                <path d="m18.5 13.5 2 2" fill="none" stroke="currentColor" stroke-linecap="round"></path>
              </svg>
            </button>
          </div>
        </div>

        <div class="table-wrap" @scroll="ctx.handleModTableScroll">
          <template v-if="ctx.libraryMode === 'items'">
            <div v-if="ctx.itemDatabase.loading && ctx.itemRows.length === 0" class="table-state">
              <strong>正在加载物品数据库</strong>
              <span>首批读取 {{ ctx.itemDatabase.limit }} 个对象。</span>
            </div>
            <div v-else-if="ctx.itemDatabase.checked && !ctx.itemDatabase.exists" class="table-state">
              <strong>请创建数据库</strong>
              <span>当前未找到模组数据库，创建后才能加载物品浏览列表。</span>
              <button type="button" @click="ctx.buildModDatabase">创建数据库</button>
            </div>
            <div v-else-if="ctx.itemDatabaseEmpty" class="table-state">
              <strong>物品数据库为空</strong>
              <span>请选择有效 HS2 游戏目录，然后重新创建数据库。</span>
              <button type="button" @click="ctx.selectGameDir">选择 HS2 目录</button>
              <button type="button" @click="ctx.buildModDatabase">重建数据库</button>
            </div>
            <div v-else-if="ctx.itemDatabase.error" class="table-state">
              <strong>物品列表加载失败</strong>
              <span>{{ ctx.itemDatabase.error }}</span>
              <button type="button" @click="ctx.refreshModDatabaseList">重试</button>
            </div>
            <table v-else>
              <thead>
                <tr><th>状态</th><th>缩略图</th><th>物品名</th><th>Kind</th><th>作者</th><th>来源模组</th></tr>
              </thead>
              <tbody>
                <tr v-for="row in ctx.itemRows" :key="row.id" :class="{ 'selected-row': ctx.selectedItem?.id === row.id }" @click="ctx.selectItem(row)" @dblclick="ctx.locateSourceMod(row)">
                  <td><span class="badge" :class="ctx.badgeClass(row.status)">{{ row.status }}</span></td>
                  <td>
                    <span class="item-thumb" :class="ctx.badgeClass(row.status)">
                      <LazyThumbnail v-if="row.thumbnailUrl && row.status === 'ready'" :src="row.thumbnailUrl" :alt="row.name + ' preview'" />
                      <span v-else>{{ row.status === 'ready' ? 'PNG' : 'MISS' }}</span>
                    </span>
                  </td>
                  <td><span class="truncate">{{ row.name }}</span></td>
                  <td>{{ row.kind }}</td>
                  <td>{{ row.author }}</td>
                  <td>{{ row.sourceMod }}</td>
                </tr>
              </tbody>
            </table>
            <div v-if="ctx.itemDatabase.exists" class="table-load-more">
              <span v-if="ctx.itemDatabase.loadingMore">继续加载中...</span>
              <span v-else-if="ctx.itemDatabase.hasMore">已加载 {{ ctx.itemRows.length.toLocaleString() }} / {{ ctx.itemDatabase.total.toLocaleString() }}</span>
              <span v-else>已加载全部 {{ ctx.itemRows.length.toLocaleString() }} 个对象</span>
            </div>
          </template>

          <div v-else-if="ctx.modDatabase.loading && ctx.modRows.length === 0" class="table-state">
            <strong>正在加载模组数据库</strong>
            <span>首批读取 {{ ctx.modDatabase.limit }} 个对象。</span>
          </div>
          <div v-else-if="ctx.modDatabase.checked && !ctx.modDatabase.exists" class="table-state">
            <strong>请创建数据库</strong>
            <span>当前未找到模组数据库，创建后才能加载模组浏览列表。</span>
            <button type="button" @click="ctx.buildModDatabase">创建数据库</button>
          </div>
          <div v-else-if="ctx.modDatabaseEmpty" class="table-state">
            <strong>模组数据库为空</strong>
            <span>请选择有效 HS2 游戏目录，然后重新创建数据库。</span>
            <button type="button" @click="ctx.selectGameDir">选择 HS2 目录</button>
            <button type="button" @click="ctx.buildModDatabase">重建数据库</button>
          </div>
          <div v-else-if="ctx.modDatabase.error" class="table-state">
            <strong>模组列表加载失败</strong>
            <span>{{ ctx.modDatabase.error }}</span>
            <button type="button" @click="ctx.refreshModDatabaseList">重试</button>
          </div>
          <table v-else :class="{ 'bulk-mode-table': ctx.modBulkMode }">
            <thead>
              <tr>
                <th v-if="ctx.modBulkMode" class="select-column">
                  <label class="select-all-cell">
                    <input
                      type="checkbox"
                      :checked="ctx.allVisibleModsSelected"
                      :indeterminate.prop="ctx.someVisibleModsSelected"
                      aria-label="全选当前加载的模组"
                      @change="ctx.toggleAllVisibleMods"
                    >
                    <span>全选</span>
                  </label>
                </th>
                <th>状态</th>
                <th>名称</th>
                <th>作者</th>
                <th>版本</th>
                <th>物品数</th>
                <th>包标识 / GUID</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in ctx.modRows"
                :key="row.id"
                :class="{ 'selected-row': ctx.selectedMod?.id === row.id, 'bulk-selected-row': ctx.selectedModIds.has(Number(row.id)) }"
                @click="ctx.selectMod(row)"
              >
                <td v-if="ctx.modBulkMode" class="select-column">
                  <input
                    type="checkbox"
                    :checked="ctx.selectedModIds.has(Number(row.id))"
                    :aria-label="`选择 ${row.name}`"
                    @click.stop
                    @change="ctx.toggleModSelection(row)"
                  >
                </td>
                <td><span class="badge" :class="ctx.badgeClass(row.status)">{{ row.status }}</span></td>
                <td><span class="truncate">{{ row.name }}</span></td>
                <td>{{ row.author }}</td>
                <td>{{ row.version }}</td>
                <td>{{ row.itemCount }}</td>
                <td><span class="truncate mono">{{ row.guid }}</span></td>
              </tr>
            </tbody>
          </table>
          <div v-if="ctx.libraryMode === 'mods' && ctx.modDatabase.exists" class="table-load-more">
            <span v-if="ctx.modDatabase.loadingMore">继续加载中...</span>
            <span v-else-if="ctx.modDatabase.hasMore">已加载 {{ ctx.modRows.length.toLocaleString() }} / {{ ctx.modDatabase.total.toLocaleString() }}</span>
            <span v-else>已加载全部 {{ ctx.modRows.length.toLocaleString() }} 个对象</span>
          </div>
        </div>
      </section>

      <aside class="panel side-panel mod-detail-panel">
        <div class="panel-head mod-detail-head">
          <h2>详细信息</h2>
          <span v-if="ctx.libraryMode === 'items' && ctx.selectedItem" class="badge" :class="ctx.badgeClass(ctx.selectedItem.status)">{{ ctx.selectedItem.status }}</span>
          <span v-else-if="ctx.libraryMode === 'mods' && ctx.selectedMod" class="badge" :class="ctx.badgeClass(ctx.selectedMod.status)">{{ ctx.selectedMod.status }}</span>
        </div>
        <div class="drawer-body mod-detail-body">
          <div v-if="(ctx.libraryMode === 'items' && !ctx.selectedItem) || (ctx.libraryMode === 'mods' && !ctx.selectedMod)" class="detail-empty">
            <strong>请选择一个对象</strong>
          </div>

          <template v-else-if="ctx.libraryMode === 'items'">
            <div class="drawer-hero item-drawer-hero mod-detail-hero">
              <span class="drawer-thumb" :aria-label="ctx.selectedItem.name + ' thumbnail'">
                <img v-if="ctx.selectedItem.thumbnailUrl && ctx.selectedItem.status === 'ready'" :src="ctx.selectedItem.thumbnailUrl" :alt="ctx.selectedItem.name + ' preview'">
              </span>
              <div class="drawer-hero-content">
                <h3>{{ ctx.selectedItem.name }}</h3>
                <div class="library-summary">
                  <span class="badge">{{ ctx.selectedItem.kind }}</span>
                  <span class="badge">{{ ctx.selectedItem.author }}</span>
                  <span class="badge" :class="ctx.badgeClass(ctx.selectedItem.status)">{{ ctx.selectedItem.status }}</span>
                </div>
              </div>
            </div>
            <div class="tabs mod-detail-tabs item-detail-tabs" aria-label="物品详情视图">
              <button :class="{ active: ctx.itemTab === '详情' }" type="button" @click="ctx.itemTab = '详情'">详情</button>
              <button :class="{ active: ctx.itemTab === '工具' }" type="button" @click="ctx.itemTab = '工具'">工具</button>
            </div>
            <div v-if="ctx.itemTab === '详情'" class="drawer-tab-panel active">
              <div class="drawer-section mod-detail-section">
                <span class="drawer-section-title">来源模组</span>
                <div class="kv mod-kv"><span>模组名称</span><strong>{{ ctx.selectedItem.sourceMod }}</strong></div>
                <div class="kv mod-kv"><span>包标识</span><strong>{{ ctx.selectedItem.raw.zipmod_guid || "-" }}</strong></div>
                <div class="kv mod-kv"><span>物品 ID</span><strong>{{ ctx.selectedItem.raw.item_id || ctx.selectedItem.id }}</strong></div>
                <div class="kv mod-kv"><span>分类表</span><strong>{{ ctx.selectedItem.raw.csv_path || ctx.selectedItem.kind }}</strong></div>
                <div class="kv mod-kv"><span>依赖 Unity3D</span><strong class="mono" :title="ctx.selectedItem.raw.main_ab || '-'">{{ ctx.itemUnity3dFileName(ctx.selectedItem) }}</strong></div>
              </div>
            </div>
            <div v-else class="drawer-tab-panel active">
              <ModelPreview
                ref="modelPreview"
                :item-id="ctx.selectedItem.id"
                :auto-load="selectedItemIsClothing"
                @ready-change="modelPreviewReady = $event"
              />
              <div class="drawer-section mod-detail-section item-tools-section">
                <div class="item-tools-heading">
                  <div>
                    <span class="drawer-section-title">物品工具</span>
                  </div>
                  <span class="item-tools-count">4 项</span>
                </div>
                <div class="item-tools-list">
                  <div class="item-tool-card">
                    <span class="item-tool-icon" aria-hidden="true">
                      <svg viewBox="0 0 24 24" focusable="false">
                        <path d="m4 8 8-4 8 4-8 4-8-4Z"></path>
                        <path d="m4 8 .1 8 7.9 4 7.9-4L20 8M12 12v8"></path>
                      </svg>
                    </span>
                    <div class="item-tool-copy">
                      <strong>来源模组</strong>
                      <small :title="ctx.selectedItem.sourceMod">{{ ctx.selectedItem.sourceMod }}</small>
                    </div>
                    <button type="button" @click="ctx.locateSourceMod()">定位</button>
                  </div>
                  <div class="item-tool-card">
                    <span class="item-tool-icon" aria-hidden="true">
                      <svg viewBox="0 0 24 24" focusable="false">
                        <path d="m4 7 7-3 7 3-7 3-7-3ZM4 7v8l7 3 3-1.3M11 10v8"></path>
                        <path d="M16 12v8M13.5 17.5 16 20l2.5-2.5M14 20h6"></path>
                      </svg>
                    </span>
                    <div class="item-tool-copy">
                      <strong>导出 FBX 模型</strong>
                      <small>静态网格、材质与贴图</small>
                    </div>
                    <button type="button" :disabled="ctx.exportingFbxItemId === ctx.selectedItem.id" @click="ctx.exportItemFbx(ctx.selectedItem)">{{ ctx.exportingFbxItemId === ctx.selectedItem.id ? "导出中..." : "导出" }}</button>
                  </div>
                  <div class="item-tool-card">
                    <span class="item-tool-icon" aria-hidden="true">
                      <svg viewBox="0 0 24 24" focusable="false">
                        <rect x="3" y="5" width="16" height="14" rx="2"></rect>
                        <circle cx="8" cy="10" r="1.5"></circle>
                        <path d="m5 17 4-4 3 3 2-2 3 3M20 3v4M18 5h4"></path>
                      </svg>
                    </span>
                    <div class="item-tool-copy">
                      <strong>重建缩略图</strong>
                      <small>从图片或当前 3D 视角生成</small>
                    </div>
                    <span class="item-tool-status" :class="{ ready: ctx.selectedItem.raw.thumbnail_status === 'ready' }">{{ ctx.selectedItem.raw.thumbnail_status || "未知" }}</span>
                    <button type="button" :disabled="ctx.repairingThumbnailItemId === ctx.selectedItem.id" @click="openThumbnailChoice">{{ ctx.repairingThumbnailItemId === ctx.selectedItem.id ? "导入中..." : "重建" }}</button>
                  </div>
                  <div class="item-tool-card">
                    <span class="item-tool-icon" aria-hidden="true">
                      <svg viewBox="0 0 24 24" focusable="false">
                        <rect x="7" y="4" width="13" height="11" rx="2"></rect>
                        <path d="M17 18H6a2 2 0 0 1-2-2V7M9 13l3-3 2.5 2.5L17 10l3 3"></path>
                        <circle cx="11" cy="8" r="1"></circle>
                      </svg>
                    </span>
                    <div class="item-tool-copy">
                      <strong>批量缩略图工具</strong>
                      <small>处理当前筛选列表</small>
                    </div>
                    <button type="button" :disabled="Boolean(ctx.bulkActionBusy)" @click="ctx.openThumbnailToolsPrompt">打开</button>
                  </div>
                </div>
                <div class="item-danger-zone">
                  <div class="item-tool-copy">
                    <strong>删除物品</strong>
                    <small :title="ctx.selectedItem.name">{{ ctx.selectedItem.name }}</small>
                  </div>
                  <button type="button" :disabled="ctx.deletingItemId === ctx.selectedItem.id" @click="ctx.deleteModItemRow(ctx.selectedItem)">{{ ctx.deletingItemId === ctx.selectedItem.id ? "删除中..." : "删除" }}</button>
                </div>
              </div>
            </div>
          </template>

          <template v-else>
            <div class="drawer-hero mod-detail-hero">
              <h3>{{ ctx.selectedMod.name }}</h3>
              <div class="library-summary">
                <span class="badge">{{ ctx.selectedMod.author }}</span>
                <span class="badge">v{{ ctx.selectedMod.version }}</span>
                <span class="badge ok">{{ ctx.selectedMod.itemCount }} items</span>
              </div>
            </div>
            <div class="tabs mod-detail-tabs" aria-label="模组详情视图">
              <button :class="{ active: ctx.modTab === '详情' }" type="button" @click="ctx.setModTab('详情')">详情</button>
              <button :class="{ active: ctx.modTab === '物品' }" type="button" @click="ctx.setModTab('物品')">物品</button>
              <button :class="{ active: ctx.modTab === '诊断' }" type="button" @click="ctx.setModTab('诊断')">诊断</button>
            </div>
            <div v-if="ctx.modTab === '详情'" class="drawer-tab-panel active">
              <div class="drawer-section mod-detail-section">
                <span class="drawer-section-title">基础信息</span>
                <div class="kv mod-kv"><span>数据库 ID</span><strong>{{ ctx.selectedMod.id }}</strong></div>
                <div class="kv mod-kv"><span>包标识</span><strong>{{ ctx.selectedMod.guid }}</strong></div>
                <div class="kv mod-kv"><span>最近扫描</span><strong>{{ ctx.selectedMod.raw.last_scanned_at || "-" }}</strong></div>
              </div>
              <div class="drawer-section mod-detail-section">
                <span class="drawer-section-title">文件位置</span>
                <div class="kv mod-kv"><span>文件名</span><strong>{{ ctx.selectedMod.raw.file_name || "-" }}</strong></div>
                <button class="kv mod-kv folder-kv" type="button" @click="ctx.openSelectedModInFolder">
                  <span>所在文件夹</span>
                </button>
              </div>
              <div class="drawer-section mod-detail-section">
                <span class="drawer-section-title">工具</span>
                <div class="kv mod-kv with-action tool-kv">
                  <span>Manifest</span>
                  <button type="button" @click="ctx.openManifestEditor">修改</button>
                </div>
              </div>
            </div>
            <div v-else-if="ctx.modTab === '物品'" class="drawer-tab-panel active">
              <div class="drawer-section mod-detail-section">
                <span class="drawer-section-title">关联物品</span>
                <div v-if="ctx.selectedModItemsLoading" class="detail-inline-state">正在加载关联物品...</div>
                <div v-else-if="ctx.selectedModItemsError" class="detail-inline-state">{{ ctx.selectedModItemsError }}</div>
                <div v-else-if="ctx.selectedModItems.length === 0" class="detail-inline-state">暂无关联物品</div>
                <div v-else class="related-item-list">
                  <button v-for="item in ctx.selectedModItems" :key="item.id" type="button" class="related-item" @click="ctx.openModItemInItemBrowser(item)">
                    <span class="related-thumb" :class="ctx.badgeClass(item.status)">
                      <LazyThumbnail v-if="item.thumbnailUrl && item.status === 'ready'" :src="item.thumbnailUrl" :alt="item.name + ' preview'" />
                      <span v-else>{{ item.status === "ready" ? "PNG" : "MISS" }}</span>
                    </span>
                    <div class="related-item-main">
                      <strong>{{ item.name }}</strong>
                      <p class="subtext mono">{{ item.kind }}</p>
                    </div>
                    <span class="badge" :class="ctx.badgeClass(item.status)">{{ item.status }}</span>
                  </button>
                </div>
              </div>
            </div>
            <div v-else class="drawer-tab-panel active">
              <div class="drawer-section mod-detail-section">
                <span class="drawer-section-title">诊断摘要</span>
                <div class="kv mod-kv"><span>扫描状态</span><strong>{{ ctx.selectedMod.status }}</strong></div>
                <div class="kv mod-kv"><span>错误信息</span><strong>{{ ctx.selectedModDiagnosticSummary }}</strong></div>
              </div>
              <div class="drawer-section mod-detail-section">
                <span class="drawer-section-title">异常详情</span>
                <div v-if="ctx.selectedModDiagnosticsLoading" class="detail-inline-state">正在读取诊断...</div>
                <div v-else-if="ctx.selectedModDiagnosticsError" class="detail-inline-state">{{ ctx.selectedModDiagnosticsError }}</div>
                <div v-else-if="!ctx.selectedModDiagnostics || ctx.selectedModDiagnosticGroups.length === 0" class="detail-inline-state">未发现异常</div>
                <div v-else class="diagnostic-list">
                  <article v-for="issue in ctx.selectedModDiagnosticGroups" :key="issue.type + ':' + issue.path" class="diagnostic-card">
                    <div class="diagnostic-card-head">
                      <strong>{{ issue.title }}</strong>
                      <span class="badge" :class="ctx.badgeClass(issue.badgeStatus)">{{ issue.affected_count }} items</span>
                    </div>
                    <div v-if="issue.type === 'unity3d' && issue.status === 'missing'" class="kv mod-kv unity3d-file-kv">
                      <span>Unity3D 文件</span><strong class="mono">{{ ctx.unity3dIssueFileName(issue) }}</strong>
                    </div>
                    <div v-if="issue.type !== 'thumbnail'" class="affected-items">
                      <span v-for="item in issue.affected_items" :key="item.id" class="badge neutral">{{ item.name || item.item_id }}</span>
                    </div>
                    <button
                      v-if="issue.type === 'manifest_author'"
                      type="button"
                      class="diagnostic-action"
                      @click="ctx.openManifestAuthorPrompt(issue)"
                    >
                      补作者
                    </button>
                    <div v-if="issue.type === 'thumbnail'" class="thumbnail-repair-list">
                      <div v-for="item in issue.affected_items" :key="item.id" class="thumbnail-repair-item">
                        <div class="thumbnail-repair-main">
                          <strong>{{ item.name || item.item_id }}</strong>
                          <p v-if="item.thumbnail_error_detail || item.thumbnail_error" class="subtext diagnostic-detail">
                            {{ ctx.thumbnailIssueReason(item) }}
                          </p>
                        </div>
                        <button
                          type="button"
                          class="diagnostic-action"
                          :disabled="ctx.repairingThumbnailItemId === item.id"
                          @click="ctx.repairThumbnailItem(item)"
                        >
                          {{ ctx.repairingThumbnailItemId === item.id ? "导入中..." : "选择图片" }}
                        </button>
                      </div>
                    </div>
                    <button
                      v-if="issue.type === 'duplicate_zipmod'"
                      type="button"
                      class="diagnostic-action"
                      :disabled="ctx.cleaningDuplicateZipmods"
                      @click="ctx.openDuplicateZipmodPrompt(issue)"
                    >
                      管理重复模组
                    </button>
                    <button
                      v-if="issue.repair_action === 'copy_into_zipmod'"
                      type="button"
                      class="diagnostic-action"
                      :disabled="ctx.repairingUnity3dPath === issue.path"
                      @click="ctx.repairUnity3dIssue(issue)"
                    >
                      {{ ctx.repairingUnity3dPath === issue.path ? "正在剪切..." : "剪切补入 zipmod" }}
                    </button>
                  </article>
                </div>
                <button
                  v-if="ctx.selectedModCanDelete"
                  type="button"
                  class="diagnostic-action"
                  @click="ctx.deleteSelectedMod"
                >
                  删除模组
                </button>
              </div>
            </div>
          </template>
        </div>
      </aside>
    </div>
  </section>
  <Teleport to="body">
    <div v-if="thumbnailChoiceOpen" class="prompt-backdrop" @click.self="thumbnailChoiceOpen = false">
      <div class="prompt-panel thumbnail-rebuild-panel" role="dialog" aria-modal="true" aria-labelledby="thumbnail-rebuild-title">
        <strong id="thumbnail-rebuild-title">重建物品缩略图</strong>
        <p>选择图片来源。两种方式都会写入当前 zipmod 并更新物品 CSV。</p>
        <div class="thumbnail-source-options">
          <button type="button" class="thumbnail-source-card" :disabled="thumbnailChoiceBusy" @click="importThumbnailFromFile">
            <span class="thumbnail-source-index">01</span>
            <strong>从外部导入</strong>
            <small>选择一张本地 PNG 图片</small>
          </button>
          <button type="button" class="thumbnail-source-card preview-source" :disabled="!modelPreviewReady || thumbnailChoiceBusy" @click="importThumbnailFromPreview">
            <span class="thumbnail-source-index">02</span>
            <strong>{{ thumbnailChoiceBusy ? "正在生成…" : "使用 3D 截图" }}</strong>
            <small>{{ modelPreviewReady ? "采用当前旋转与缩放视角" : "请先加载上方 3D 模型" }}</small>
          </button>
        </div>
        <div v-if="thumbnailChoiceError" class="prompt-error">{{ thumbnailChoiceError }}</div>
        <div class="prompt-actions">
          <button type="button" :disabled="thumbnailChoiceBusy" @click="thumbnailChoiceOpen = false">取消</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
