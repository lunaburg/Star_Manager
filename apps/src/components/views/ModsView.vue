<script setup>
import { computed, onActivated, onBeforeUnmount, onMounted, ref, watch } from "vue";
import ModelPreview from "../ModelPreview.vue";
import LazyThumbnail from "../LazyThumbnail.vue";
import LoadingAnimation from "../LoadingAnimation.vue";
import VirtualItemGrid from "../VirtualItemGrid.vue";
import VirtualItemTable from "../VirtualItemTable.vue";
import assemblyDisconnectedLoadingAnimation from "../../assets/assembly-disconnected-loading.json";

const { ctx } = defineProps({
  ctx: { type: Object, required: true }
});

const modelPreview = ref(null);
const modelPreviewReady = ref(false);
const thumbnailChoiceOpen = ref(false);
const thumbnailChoiceBusy = ref(false);
const thumbnailChoiceError = ref("");
const expandedAssemblyGroup = ref("clothes");
const selectedAssemblySlotKey = ref("");
const modTableWrap = ref(null);

function handleModTableScroll(event) {
  ctx.captureModTableScrollPosition(ctx.libraryMode, event.currentTarget);
  ctx.handleModTableScroll(event);
}

onMounted(() => {
  ctx.registerModTableScrollContainer(modTableWrap.value);
});

onActivated(() => {
  // Keep the parent registration valid after KeepAlive moves this view back
  // into the workspace, then restore the current mode after the DOM returns.
  ctx.registerModTableScrollContainer(modTableWrap.value);
});

onBeforeUnmount(() => {
  ctx.unregisterModTableScrollContainer(modTableWrap.value);
});

watch(() => [
  ctx.modRows?.length,
  ctx.itemRows?.length,
  ctx.modDatabase?.loading,
  ctx.itemDatabase?.loading,
  ctx.modDatabase?.loadingMore,
  ctx.itemDatabase?.loadingMore
], () => ctx.scheduleModTableScrollRestore());

watch(() => ctx.assemblyMode, (enabled) => {
  if (!enabled) selectedAssemblySlotKey.value = "";
});

watch(() => [
  ctx.assemblyContext?.scene,
  ctx.assemblyContext?.available,
  ctx.currentGameState?.available
], () => {
  if (!ctx.currentGameState?.available) selectedAssemblySlotKey.value = "";
});

function toggleAssemblyGroup(groupKey) {
  if (!ctx.gameCurrentGroups?.some((group) => group.key === groupKey)) return;
  expandedAssemblyGroup.value = expandedAssemblyGroup.value === groupKey ? "" : groupKey;
}

function assemblySlotKey(group, item) {
  return `${group.key}:${item.partIndex}:${item.categoryNo}`;
}

async function selectAssemblySlot(group, item) {
  const key = assemblySlotKey(group, item);
  const selected = await ctx.selectAssemblySlot(item, group.key);
  if (selected) selectedAssemblySlotKey.value = key;
}

async function handleItemClick(row) {
  if (ctx.assemblyMode) {
    await ctx.applyAssemblyItem(row);
    return;
  }
  ctx.selectItem(row);
}

function handleItemDoubleClick(row) {
  if (ctx.assemblyMode) return;
  ctx.locateSourceMod(row);
}

const selectedItemIsClothing = computed(() => (
  String(ctx.selectedItem?.kind || "").includes("\u670d\u9970")
));

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
  unity3d_not_in_mod: "warn",
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
      <section class="panel browser-panel mod-page glass-surface--compact">
        <div class="module-head mod-head glass-surface--compact">
          <h1>模组管理</h1>
          <div class="library-summary mod-summary">
            <span class="badge ok">{{ ctx.formatStat(ctx.modDatabase.total) }} zipmod</span>
            <span class="badge">{{ ctx.formatStat(ctx.stats.modItems) }} items</span>
            <span class="badge warn">{{ ctx.formatStat(ctx.stats.zipmodWarnings) }} warnings</span>
            <span class="badge danger">{{ ctx.formatStat(ctx.stats.zipmodErrors) }} errors</span>
            <span class="badge neutral">last {{ ctx.formatDatabaseTime(ctx.stats.lastDatabaseBuiltAt) }}</span>
          </div>
        </div>

        <div class="mod-strip glass-surface--compact">
          <div class="mode-strip mod-tabs">
            <button :class="{ active: ctx.libraryMode === 'mods' }" type="button" @click="ctx.setLibraryMode('mods')">模组浏览</button>
            <button :class="{ active: ctx.libraryMode === 'items' }" type="button" @click="ctx.setLibraryMode('items')">物品浏览</button>
          </div>
          <div v-if="ctx.libraryMode === 'items'" class="assembly-mode-control">
            <button
              class="assembly-mode-toggle"
              :class="{ active: ctx.assemblyMode }"
              type="button"
              :aria-pressed="ctx.assemblyMode"
              title="切换右侧为游戏角色编辑器的实际装配信息"
              @click="ctx.setAssemblyMode(!ctx.assemblyMode)"
            >
              <span>{{ ctx.assemblyMode ? '退出装配模式' : '装配模式' }}</span>
            </button>
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

        <div class="toolbar library-toolbar glass-surface--compact">
          <div v-if="ctx.libraryMode === 'items'" class="toolbar-left filter-grid items">
            <input
              v-model="ctx.itemFilters.search"
              class="search"
              aria-label="搜索物品名字或模组 GUID"
              placeholder="搜索物品名字 / 模组 GUID"
              @input="ctx.scheduleItemSearch"
            >
            <div class="author-combobox" @keydown.esc="ctx.itemAuthorFilterOpen = false">
              <input
                v-model="ctx.itemFilters.author"
                type="text"
                aria-label="作者筛选"
                aria-haspopup="listbox"
                :aria-expanded="ctx.itemAuthorFilterOpen"
                placeholder="输入作者关键字"
                autocomplete="off"
                spellcheck="false"
                @focus="ctx.itemAuthorFilterOpen = true; ctx.loadItemFilters()"
                @blur="ctx.closeItemAuthorFilterSoon"
                @input="ctx.itemAuthorFilterOpen = true; ctx.scheduleItemSearch()"
                @keydown.enter.prevent="ctx.applyItemFilters"
              >
              <button
                class="author-combobox-toggle"
                type="button"
                aria-label="显示作者列表"
                @mousedown.prevent
                @click="ctx.loadItemFilters(); ctx.itemAuthorFilterOpen = !ctx.itemAuthorFilterOpen"
              >
                ▼
              </button>
              <div v-if="ctx.itemAuthorFilterOpen" class="author-option-list" role="listbox" aria-label="作者筛选选项">
                <button
                  v-for="author in ctx.filteredItemAuthorOptions"
                  :key="author || 'all'"
                  type="button"
                  :class="{ active: ctx.itemFilters.author === author }"
                  role="option"
                  :aria-selected="ctx.itemFilters.author === author"
                  @mousedown.prevent="ctx.selectItemAuthorFilter(author)"
                >
                  {{ author || "全部作者" }}
                </button>
                <div v-if="ctx.filteredItemAuthorOptions.length === 0" class="author-option-empty">没有匹配作者</div>
              </div>
            </div>
            <select v-model="ctx.itemFilters.source" aria-label="物品来源筛选" title="筛选模组物品或游戏本体物品" @change="ctx.applyItemFilters">
              <option value="">全部来源</option>
              <option value="mod">模组物品</option>
              <option value="builtin">游戏本体</option>
            </select>
            <select v-model="ctx.itemFilters.status" aria-label="状态筛选" @change="ctx.applyItemFilters">
              <option value="">全部状态</option>
              <option value="ready">正常</option>
              <option value="error">错误</option>
              <option value="thumb">缩略图异常</option>
            </select>
          </div>

          <div v-if="ctx.libraryMode === 'items'" class="item-toolbar-actions">
            <button class="bulk-delete-error-items-button danger-action" type="button" title="批量删除当前筛选列表下的所有错误模组物品" aria-label="批量删除当前筛选列表下的所有错误模组物品" :aria-busy="ctx.bulkActionBusy === 'items-delete'" :disabled="!ctx.itemDatabase.exists || ctx.itemFilters.source === 'builtin' || Boolean(ctx.bulkActionBusy)" @click="ctx.openBulkDeleteErrorItemsPrompt">
              删除错误物品
            </button>
          </div>

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
                placeholder="输入作者关键字"
                autocomplete="off"
                @focus="ctx.modAuthorFilterOpen = true; ctx.loadZipmodAuthors()"
                @blur="ctx.closeModAuthorFilterSoon"
                @input="ctx.modAuthorFilterOpen = true; ctx.scheduleModAuthorFilter()"
                @keydown.enter.prevent="ctx.applyModFilters"
              >
              <button
                class="author-combobox-toggle"
                type="button"
                aria-label="显示作者列表"
                @mousedown.prevent
                @click="ctx.loadZipmodAuthors(); ctx.modAuthorFilterOpen = !ctx.modAuthorFilterOpen"
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
              <option class="status-option-warn" value="unity3d_not_in_mod">　unity3d未在模组内</option>
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
              class="bulk-icon-button bulk-export-action"
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
              class="bulk-icon-button bulk-organize-action"
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
              class="bulk-icon-button bulk-unity3d-action"
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
              class="bulk-icon-button bulk-duplicate-action"
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
              class="bulk-icon-button bulk-delete-action"
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
              class="bulk-icon-button bulk-author-action"
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

        <div ref="modTableWrap" class="table-wrap" @scroll="handleModTableScroll">
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
            <VirtualItemGrid
              v-else-if="ctx.itemViewMode === 'compact'"
              :rows="ctx.itemRows"
              :selected-id="ctx.selectedItem?.id"
              :badge-class="ctx.badgeClass"
              :is-map-scene-item="ctx.isMapSceneItem"
              @item-click="handleItemClick"
              @item-dblclick="handleItemDoubleClick"
              @item-contextmenu="(row, event) => ctx.openItemContextMenu(row, event)"
            />
            <VirtualItemTable
              v-else
              :rows="ctx.itemRows"
              :selected-id="ctx.selectedItem?.id"
              :badge-class="ctx.badgeClass"
              :is-map-scene-item="ctx.isMapSceneItem"
              @item-click="handleItemClick"
              @item-dblclick="handleItemDoubleClick"
              @item-contextmenu="(row, event) => ctx.openItemContextMenu(row, event)"
            />
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
                <td><span class="text-ellipsis">{{ row.name }}</span></td>
                <td>{{ row.author }}</td>
                <td>{{ row.version }}</td>
                <td>{{ row.itemCount }}</td>
                <td><span class="text-ellipsis mono">{{ row.guid }}</span></td>
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
          <h2>{{ ctx.libraryMode === 'items' && ctx.assemblyMode ? '当前角色装配' : '详细信息' }}</h2>
          <span
            v-if="ctx.libraryMode === 'items' && ctx.assemblyMode && ctx.assemblyTargetSlot.active"
            class="assembly-selected-slot"
            :title="ctx.assemblyTargetSlot.label"
          >
            {{ ctx.assemblyTargetSlot.label }}
          </span>
          <span v-if="ctx.libraryMode === 'items' && ctx.assemblyMode" class="badge ok">实时同步</span>
          <span v-else-if="ctx.libraryMode === 'items' && ctx.selectedItem" class="badge" :class="ctx.badgeClass(ctx.selectedItem.status)">{{ ctx.selectedItem.status }}</span>
          <span v-else-if="ctx.libraryMode === 'mods' && ctx.selectedMod" class="badge" :class="ctx.badgeClass(ctx.selectedMod.status)">{{ ctx.selectedMod.status }}</span>
        </div>
        <div class="drawer-body mod-detail-body">
          <div v-if="ctx.libraryMode === 'items' && ctx.assemblyMode" class="assembly-detail-view" :class="{ 'is-disconnected': !ctx.currentGameState.available }">
            <template v-if="ctx.currentGameState.available">
              <div class="assembly-groups">
                <section v-for="group in ctx.gameCurrentGroups" :key="group.key" class="assembly-group" :class="{ 'is-expanded': expandedAssemblyGroup === group.key }">
                  <button
                    class="assembly-group-head"
                    type="button"
                    :aria-expanded="expandedAssemblyGroup === group.key"
                    :aria-controls="`assembly-group-content-${group.key}`"
                    :aria-label="`${expandedAssemblyGroup === group.key ? '收起' : '展开'}${group.label}`"
                    @click="toggleAssemblyGroup(group.key)"
                  >
                    <span class="assembly-group-head-copy">
                      <span class="assembly-group-label">{{ group.label }}</span>
                    </span>
                    <span class="assembly-group-head-actions">
                      <strong class="assembly-group-count">{{ (ctx.currentGameState[group.key] || []).length }}</strong>
                      <span class="assembly-group-chevron" :class="{ open: expandedAssemblyGroup === group.key }" aria-hidden="true">⌄</span>
                    </span>
                  </button>
                  <div v-if="expandedAssemblyGroup === group.key" :id="`assembly-group-content-${group.key}`" class="assembly-group-content">
                    <div v-if="(ctx.currentGameState[group.key] || []).length" class="assembly-slot-list">
                      <article
                        v-for="item in (ctx.currentGameState[group.key] || [])"
                        :key="`${group.key}-${item.partIndex}-${item.categoryNo}`"
                        class="assembly-slot-row"
                        :class="{ empty: Number(item.localSlot || 0) === 0, selected: selectedAssemblySlotKey === assemblySlotKey(group, item) }"
                        role="button"
                        tabindex="0"
                        :aria-pressed="selectedAssemblySlotKey === assemblySlotKey(group, item)"
                        :title="`点击以筛选可装配到${ctx.gameCurrentSlotLabel(item)}的物品`"
                          @click="selectAssemblySlot(group, item)"
                          @keydown.enter.prevent="selectAssemblySlot(group, item)"
                          @keydown.space.prevent="selectAssemblySlot(group, item)"
                      >
                        <span
                          class="assembly-slot-thumb"
                          :class="{ empty: Number(item.localSlot || 0) === 0, placeholder: !item.thumbnailUrl }"
                          aria-hidden="true"
                        >
                          <LazyThumbnail
                            v-if="item.thumbnailUrl"
                            :src="item.thumbnailUrl"
                            :alt="`${ctx.gameCurrentItemName(item)}缩略图`"
                          />
                          <span v-else class="assembly-slot-thumb-placeholder">{{ Number(item.localSlot || 0) === 0 ? '—' : 'IMG' }}</span>
                        </span>
                        <div class="assembly-slot-copy">
                          <strong>
                            {{ ctx.gameCurrentSlotLabel(item) }}
                            <em v-if="item.partLabel"> · {{ item.partLabel }}</em>
                          </strong>
                          <span class="assembly-item-name">{{ ctx.gameCurrentItemName(item) }}</span>
                        </div>
                      </article>
                    </div>
                    <div v-else class="assembly-group-empty">游戏未返回该组栏位。</div>
                  </div>
                </section>
              </div>
            </template>
            <div v-else class="assembly-disconnected-state" role="status" aria-label="等待游戏连接">
              <LoadingAnimation
                class="assembly-disconnected-animation"
                :animation-data="assemblyDisconnectedLoadingAnimation"
              />
            </div>
          </div>
          <div v-else-if="(ctx.libraryMode === 'items' && !ctx.selectedItem) || (ctx.libraryMode === 'mods' && !ctx.selectedMod)" class="detail-empty">
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
            <div v-if="ctx.itemGameNotice?.message" class="item-game-notice" :class="ctx.itemGameNotice.type" role="status" aria-live="polite">
              <span>{{ ctx.itemGameNotice.message }}</span>
              <button type="button" aria-label="关闭换装提示" @click="ctx.itemGameNotice.message = ''">×</button>
            </div>
            <div v-if="!ctx.selectedItem.isBuiltin" class="tabs mod-detail-tabs item-detail-tabs" aria-label="物品详情视图">
              <button :class="{ active: ctx.itemTab === '详情' }" type="button" @click="ctx.itemTab = '详情'">详情</button>
              <button :class="{ active: ctx.itemTab === '工具' }" type="button" @click="ctx.itemTab = '工具'">工具</button>
            </div>
            <div v-if="ctx.selectedItem.isBuiltin" class="drawer-tab-panel active">
              <div class="drawer-section mod-detail-section builtin-item-detail">
                <span class="drawer-section-title">游戏本体物品</span>
                <div class="kv mod-kv"><span>来源</span><strong>游戏本体</strong></div>
                <div class="kv mod-kv"><span>物品 ID</span><strong>{{ ctx.selectedItem.raw.item_id || ctx.selectedItem.dbId || '-' }}</strong></div>
                <div class="kv mod-kv"><span>分类</span><strong>{{ ctx.selectedItem.kind }}</strong></div>
                <div class="kv mod-kv"><span>原版列表</span><strong class="mono" :title="ctx.selectedItem.raw.source_path || '-'">{{ ctx.selectedItem.raw.source_path || '-' }}</strong></div>
                <div class="kv mod-kv"><span>模型资源</span><strong class="mono" :title="ctx.selectedItem.raw.main_ab || '-'">{{ ctx.itemUnity3dFileName(ctx.selectedItem) }}</strong></div>
                <div class="kv mod-kv"><span>资源状态</span><strong>{{ ctx.selectedItem.raw.resource_status || '未知' }}</strong></div>
              </div>
            </div>
            <div v-else-if="ctx.itemTab === '详情'" class="drawer-tab-panel active">
              <div class="drawer-section mod-detail-section">
                <span class="drawer-section-title">来源模组</span>
                <div class="kv mod-kv"><span>模组名称</span><button type="button" class="source-mod-link" :title="`定位来源模组：${ctx.selectedItem.sourceMod}`" :aria-label="`定位来源模组：${ctx.selectedItem.sourceMod}`" @click="ctx.locateSourceMod()"><span>{{ ctx.selectedItem.sourceMod }}</span><span class="source-mod-link-icon" aria-hidden="true">↗</span></button></div>
                <div class="kv mod-kv"><span>包标识</span><strong>{{ ctx.selectedItem.raw.zipmod_guid || "-" }}</strong></div>
                <div class="kv mod-kv"><span>{{ ctx.isMapSceneItem(ctx.selectedItem) ? '地图编号' : '物品 ID' }}</span><strong>{{ ctx.selectedItem.raw.item_id || ctx.selectedItem.id }}</strong></div>
                <div class="kv mod-kv"><span>{{ ctx.isMapSceneItem(ctx.selectedItem) ? '地图注册表' : '分类表' }}</span><strong>{{ ctx.selectedItem.raw.csv_path || ctx.selectedItem.kind }}</strong></div>
                <div class="kv mod-kv"><span>{{ ctx.isMapSceneItem(ctx.selectedItem) ? '场景资源' : '依赖 Unity3D' }}</span><button type="button" class="unity3d-export-link mono" :disabled="ctx.exportingUnity3dItemId === ctx.selectedItem.id || !ctx.selectedItem.raw?.main_ab" :title="`点击复制导出 Unity3D：${ctx.itemUnity3dFileName(ctx.selectedItem)}`" :aria-label="`点击复制导出 Unity3D：${ctx.itemUnity3dFileName(ctx.selectedItem)}`" @click="ctx.exportItemUnity3d(ctx.selectedItem)"><span>{{ ctx.exportingUnity3dItemId === ctx.selectedItem.id ? '导出中...' : ctx.itemUnity3dFileName(ctx.selectedItem) }}</span><span class="unity3d-export-icon" aria-hidden="true">⇩</span></button></div>
              </div>
            </div>
            <div v-else class="drawer-tab-panel active">
              <div v-if="ctx.workbenchTemplateSelection?.active" class="drawer-section mod-detail-section workbench-template-selection">
                <div class="item-tools-heading">
                  <div>
                    <span class="drawer-section-title">临时工具</span>
                    <small>选择完成或取消后自动消失</small>
                  </div>
                  <span class="item-tools-count">一次性</span>
                </div>
                <div class="item-tool-card workbench-template-tool-card">
                  <span class="item-tool-icon" aria-hidden="true">
                    <svg viewBox="0 0 24 24" focusable="false">
                      <path d="m4 8 8-4 8 4-8 4-8-4Z"></path>
                      <path d="m4 8 .1 8 7.9 4 7.9-4L20 8M12 12v8"></path>
                      <path d="M16 15h5M18.5 12.5v5"></path>
                    </svg>
                  </span>
                  <div class="item-tool-copy">
                    <strong>作为模板</strong>
                  </div>
                  <button
                    type="button"
                    :disabled="ctx.workbenchTemplateSelection.busy || !ctx.selectedItem.raw?.main_ab || ctx.selectedItem.status === 'error' || ctx.isMapSceneItem(ctx.selectedItem)"
                    @click="ctx.selectWorkbenchTemplateFromItem(ctx.selectedItem)"
                  >
                    {{ ctx.workbenchTemplateSelection.busy ? "读取中..." : "选择" }}
                  </button>
                  <button type="button" :disabled="ctx.workbenchTemplateSelection.busy" @click="ctx.cancelWorkbenchTemplateSelection">取消</button>
                </div>
                <div v-if="ctx.workbenchTemplateSelection.error" class="setup-error" role="alert">
                  <span>!</span>{{ ctx.workbenchTemplateSelection.error }}
                </div>
              </div>
              <div v-if="ctx.isMapSceneItem(ctx.selectedItem)" class="drawer-section mod-detail-section">
                <span class="drawer-section-title">地图场景</span>
                <ModelPreview
                  ref="modelPreview"
                  :item-id="ctx.selectedItem.id"
                  @ready-change="modelPreviewReady = $event"
                />
              </div>
              <template v-else>
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
                  <span class="item-tools-count">3 项</span>
                </div>
                <div class="item-tools-list">
                  <div class="item-tool-card">
                    <div class="item-tool-copy">
                      <strong>使用 SB3Utility 打开</strong>
                    </div>
                    <button type="button" :disabled="ctx.openingUnity3dItemId === ctx.selectedItem.id" @click="ctx.openItemUnity3d(ctx.selectedItem)">{{ ctx.openingUnity3dItemId === ctx.selectedItem.id ? "打开中..." : "打开" }}</button>
                  </div>
                  <div class="item-tool-card">
                    <div class="item-tool-copy">
                      <strong>重建缩略图</strong>
                    </div>
                    <span class="item-tool-status" :class="{ ready: ctx.selectedItem.raw.thumbnail_status === 'ready' }">{{ ctx.selectedItem.raw.thumbnail_status || "未知" }}</span>
                    <button type="button" :disabled="ctx.repairingThumbnailItemId === ctx.selectedItem.id" @click="openThumbnailChoice">{{ ctx.repairingThumbnailItemId === ctx.selectedItem.id ? "导入中..." : "重建" }}</button>
                  </div>
                  <div class="item-tool-card">
                    <div class="item-tool-copy">
                      <strong>批量缩略图工具</strong>
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
              </template>
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
                <button
                  class="kv mod-kv folder-kv"
                  type="button"
                  :title="`在资源管理器中定位：${ctx.selectedMod.raw.file_name || '当前模组'}`"
                  :aria-label="`在资源管理器中定位：${ctx.selectedMod.raw.file_name || '当前模组'}`"
                  @click="ctx.openSelectedModInFolder"
                >
                  <span>文件名</span>
                  <strong>{{ ctx.selectedMod.raw.file_name || "-" }}</strong>
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
                      <span v-else>{{ item.status === "ready" ? (ctx.isMapSceneItem(item) ? "MAP" : "PNG") : "MISS" }}</span>
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
                    <div v-if="issue.type === 'unity3d' && ['in_game', 'not_in_mod'].includes(issue.status) && issue.game_path" class="kv mod-kv unity3d-file-kv">
                      <span>当前所在位置</span><strong class="mono" :title="issue.game_path || '-'">{{ issue.game_path || "-" }}</strong>
                    </div>
                    <div v-if="issue.type === 'unity3d' && ['in_game', 'not_in_mod'].includes(issue.status)" class="kv mod-kv unity3d-file-kv">
                      <span>资源来源</span><strong>{{ issue.source === 'other_zipmod' ? '其它 zipmod' : '游戏目录' }}</strong>
                    </div>
                    <div v-if="issue.type === 'unity3d' && issue.other_zipmods?.length" class="affected-items">
                      <span v-for="provider in issue.other_zipmods" :key="provider.path" class="badge neutral" :title="provider.path">提供：{{ provider.path.split(/[\\/]/).filter(Boolean).pop() || provider.path }}</span>
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
    <div
      v-if="ctx.itemContextMenu?.open"
      class="item-context-backdrop"
      @mousedown.self="ctx.closeItemContextMenu"
      @contextmenu.prevent
    >
      <div class="item-context-menu" :style="{ left: `${ctx.itemContextMenu.x}px`, top: `${ctx.itemContextMenu.y}px` }" role="menu" @mousedown.stop>
        <div class="item-context-heading">物品操作</div>
        <div class="item-context-name" :title="ctx.itemContextMenu.item?.name">{{ ctx.itemContextMenu.item?.name }}</div>
        <button
          type="button"
          class="item-context-action primary-context-action"
          role="menuitem"
          :disabled="ctx.itemGameApply?.busy || !ctx.itemGameApplySpec(ctx.itemContextMenu.item).supported"
          @click="ctx.requestItemGameApply"
        >
          {{ ctx.itemGameApplyLabel(ctx.itemContextMenu.item) }}
        </button>
        <div v-if="!ctx.itemGameApplySpec(ctx.itemContextMenu.item).supported" class="item-context-boundary">
          {{ ctx.itemGameApplySpec(ctx.itemContextMenu.item).reason }}
        </div>
        <button v-if="!ctx.itemContextMenu.item?.isBuiltin" type="button" class="item-context-action" role="menuitem" @click="ctx.locateSourceMod(ctx.itemContextMenu.item); ctx.closeItemContextMenu()">定位来源模组</button>
      </div>
    </div>
    <div v-if="ctx.itemAccessoryPrompt?.open" class="prompt-backdrop" @click.self="ctx.closeItemAccessoryPrompt">
      <div class="prompt-panel game-item-slot-panel" role="dialog" aria-modal="true" aria-labelledby="game-item-slot-title">
        <strong id="game-item-slot-title">应用饰品到游戏角色</strong>
        <p>请选择角色制作器中的配饰槽。这个操作只改变当前角色，不会写入物品库或角色卡；请确认正在运行的 HS2 就是当前选择的游戏目录。</p>
        <div class="game-item-target" :title="ctx.itemAccessoryPrompt.item?.name">
          <span>目标物品</span>
          <strong>{{ ctx.itemAccessoryPrompt.item?.name }}</strong>
        </div>
        <label class="game-item-slot-field">
          <span>角色配饰槽</span>
          <select v-model.number="ctx.itemAccessoryPrompt.slotNo">
            <option v-for="option in ctx.gameAccessorySlotOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
          </select>
        </label>
        <div class="game-item-boundary-note">
          {{ ctx.itemGameApplySpec(ctx.itemAccessoryPrompt.item).isBuiltin
            ? '原版物品会使用 CategoryNo + 原版 ID 直接校验游戏列表；不会按名称猜测。'
            : '插件会用模组 GUID + 类别 + CSV slot 严格解析游戏运行时 ID；映射不唯一时会拒绝执行。' }}
        </div>
        <div v-if="ctx.itemAccessoryPrompt.error" class="prompt-error">{{ ctx.itemAccessoryPrompt.error }}</div>
        <div class="prompt-actions">
          <button type="button" :disabled="ctx.itemAccessoryPrompt.busy" @click="ctx.closeItemAccessoryPrompt">取消</button>
          <button class="primary" type="button" :disabled="ctx.itemAccessoryPrompt.busy || ctx.itemGameApply?.busy" @click="ctx.confirmItemAccessoryApply">
            {{ ctx.itemAccessoryPrompt.busy ? "正在换装…" : "应用到当前角色" }}
          </button>
        </div>
      </div>
    </div>
    <div v-if="ctx.itemFacePrompt?.open" class="prompt-backdrop" @click.self="ctx.closeItemFacePrompt">
      <div class="prompt-panel game-item-slot-panel" role="dialog" aria-modal="true" aria-labelledby="game-item-face-title">
        <strong id="game-item-face-title">应用面部物品到游戏角色</strong>
        <p>请选择左眼或右眼。这个操作只改变当前角色，不会写入物品库或角色卡；请确认正在运行的 HS2 就是当前选择的游戏目录。</p>
        <div class="game-item-target" :title="ctx.itemFacePrompt.item?.name">
          <span>目标物品</span>
          <strong>{{ ctx.itemFacePrompt.item?.name }}</strong>
        </div>
        <label class="game-item-slot-field">
          <span>眼别</span>
          <select v-model.number="ctx.itemFacePrompt.facePartNo">
            <option :value="0">左眼</option>
            <option :value="1">右眼</option>
          </select>
        </label>
        <div class="game-item-boundary-note">
          {{ ctx.itemGameApplySpec(ctx.itemFacePrompt.item).isBuiltin
            ? '原版物品会使用 CategoryNo + 原版 ID 直接校验游戏列表；不会按名称猜测。'
            : '插件会用模组 GUID + 类别 + CSV slot 严格解析游戏运行时 ID；映射不唯一时会拒绝执行。' }}
        </div>
        <div v-if="ctx.itemFacePrompt.error" class="prompt-error">{{ ctx.itemFacePrompt.error }}</div>
        <div class="prompt-actions">
          <button type="button" :disabled="ctx.itemFacePrompt.busy" @click="ctx.closeItemFacePrompt">取消</button>
          <button class="primary" type="button" :disabled="ctx.itemFacePrompt.busy || ctx.itemGameApply?.busy" @click="ctx.confirmItemFaceApply">
            {{ ctx.itemFacePrompt.busy ? "正在换装…" : "应用到当前角色" }}
          </button>
        </div>
      </div>
    </div>
    <div v-if="ctx.itemBodyPrompt?.open" class="prompt-backdrop" @click.self="ctx.closeItemBodyPrompt">
      <div class="prompt-panel game-item-slot-panel" role="dialog" aria-modal="true" aria-labelledby="game-item-body-title">
        <strong id="game-item-body-title">应用身体物品到游戏角色</strong>
        <p>普通身体物品会直接应用；身体彩绘请选择目标彩绘层。这个操作只改变当前角色，不会写入物品库或角色卡。</p>
        <div class="game-item-target" :title="ctx.itemBodyPrompt.item?.name">
          <span>目标物品</span>
          <strong>{{ ctx.itemBodyPrompt.item?.name }}</strong>
        </div>
        <label v-if="ctx.itemGameApplySpec(ctx.itemBodyPrompt.item).type === 'body' && ['8', '313'].includes(String(ctx.itemGameApplySpec(ctx.itemBodyPrompt.item).categoryNo))" class="game-item-slot-field">
          <span>彩绘层</span>
          <select v-model.number="ctx.itemBodyPrompt.bodyPartNo">
            <option v-for="option in ctx.GAME_BODY_PAINT_SLOT_OPTIONS" :key="option.value" :value="option.value">{{ option.label }}</option>
          </select>
        </label>
        <div class="game-item-boundary-note">
          {{ ctx.itemGameApplySpec(ctx.itemBodyPrompt.item).isBuiltin
            ? '原版物品会使用 CategoryNo + 原版 ID 直接校验游戏列表；不会按名称猜测。'
            : '插件会用模组 GUID + 类别 + CSV slot 严格解析游戏运行时 ID；映射不唯一时会拒绝执行。' }}
        </div>
        <div v-if="ctx.itemBodyPrompt.error" class="prompt-error">{{ ctx.itemBodyPrompt.error }}</div>
        <div class="prompt-actions">
          <button type="button" :disabled="ctx.itemBodyPrompt.busy" @click="ctx.closeItemBodyPrompt">取消</button>
          <button class="primary" type="button" :disabled="ctx.itemBodyPrompt.busy || ctx.itemGameApply?.busy" @click="ctx.confirmItemBodyApply">
            {{ ctx.itemBodyPrompt.busy ? "正在换装…" : "应用到当前角色" }}
          </button>
        </div>
      </div>
    </div>
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
