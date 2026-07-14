<script setup>
import { computed, onMounted, ref, watch } from "vue";
const { ctx } = defineProps({ ctx: { type: Object, required: true } });
const search = ref(""); const category = ref("all"); const loading = ref(false); const error = ref(""); const scanned = ref(false);
const items = ref([]); const selectedId = ref(""); const bepinexPath = ref("");
const summary = ref({ total: 0, plugins: 0, patchers: 0, core: 0, metadata_errors: 0, duplicates: 0, described: 0, with_dependencies: 0 });
const selected = computed(() => items.value.find((item) => item.id === selectedId.value) || null);
const filteredItems = computed(() => { const needle = search.value.trim().toLowerCase(); return items.value.filter((item) => (category.value === "all" || item.category === category.value) && (!needle || [item.name, item.plugin_guid, item.assembly_name, item.relative_path].some((value) => String(value || "").toLowerCase().includes(needle)))); });
const categoryLabel = (value) => ({ plugin: "插件", patcher: "Patcher", core: "核心" }[value] || value);
const displayVersion = (item) => item.plugin_version || item.assembly_version || "—";
function statusLabel(item) { if (item.status === "duplicate") return "GUID 重复"; if (item.metadata_status === "error") return "解析失败"; return item.plugin_guid ? "已识别" : "程序集"; }
function statusTone(item) { return item.status === "duplicate" || item.metadata_status === "error" ? "danger" : (item.plugin_guid ? "ok" : "neutral"); }
async function scanPlugins(forceRefresh = false) {
  if (!ctx.paths.gameDir || loading.value) return; loading.value = true; error.value = "";
  try { const query = new URLSearchParams({ game_dir: ctx.paths.gameDir, limit: "1000" }); if (forceRefresh === true) query.set("refresh", "1"); const result = await window.desktopApi.backendRequest(`/plugins?${query.toString()}`); if (!result?.ok) throw new Error(result?.error || "插件扫描失败"); const data = result.data || {}; items.value = data.items || []; summary.value = { ...summary.value, ...(data.summary || {}) }; bepinexPath.value = data.bepinex_path || `${ctx.paths.gameDir}\\BepInEx`; scanned.value = true; if (!items.value.some((item) => item.id === selectedId.value)) selectedId.value = items.value[0]?.id || ""; }
  catch (scanError) { error.value = scanError?.message || String(scanError); items.value = []; }
  finally { loading.value = false; }
}
async function openBepinexDirectory() { if (bepinexPath.value && window.desktopApi?.openDirectory) await window.desktopApi.openDirectory(bepinexPath.value); }
watch(() => ctx.paths.gameDir, () => { scanned.value = false; selectedId.value = ""; items.value = []; if (ctx.paths.gameDir) scanPlugins(); });
onMounted(() => { if (ctx.paths.gameDir) scanPlugins(); });
</script>
<template>
  <section class="view plugin-view"><section class="panel plugin-page">
    <div class="module-head plugin-head"><h1>插件管理</h1></div>
    <div class="toolbar plugin-toolbar"><input v-model="search" class="search" type="search" placeholder="搜索插件名称 / GUID / DLL"><button type="button" :disabled="!scanned" @click="openBepinexDirectory">打开 BepInEx 目录</button></div>
    <div v-if="error" class="plugin-error"><strong>无法读取插件</strong><span>{{ error }}</span><button type="button" @click="scanPlugins">重试</button></div>
    <div class="plugin-browser"><div class="plugin-list-head"><span>插件</span><span>版本</span><span>类型</span><span>状态</span></div>
      <div v-if="loading" class="plugin-empty"><div class="plugin-scan-loader"><i></i><i></i><i></i></div><strong>正在分析 BepInEx</strong><p>读取程序集和 BepInEx attribute，不会执行 DLL 中的代码。</p></div>
      <div v-else-if="!scanned || filteredItems.length === 0" class="plugin-empty"><div class="plugin-empty-mark"><span>DLL</span><i></i><i></i><i></i></div><strong>{{ !ctx.paths.gameDir ? "先选择 HS2 游戏目录" : (scanned ? "没有匹配的插件" : "准备扫描 BepInEx") }}</strong><p>{{ scanned ? "尝试清除搜索词或切换插件分类。" : "扫描后将显示 Plugins、patchers 与 core 中的 DLL。" }}</p></div>
      <div v-else class="plugin-list" role="listbox"><button v-for="item in filteredItems" :key="item.id" type="button" :class="{ active: selectedId === item.id }" @click="selectedId = item.id"><span class="plugin-name-cell"><b>{{ item.name }}</b><small>{{ item.plugin_guid || item.assembly_name || item.relative_path }}</small></span><code>{{ displayVersion(item) }}</code><span>{{ categoryLabel(item.category) }}</span><span class="badge" :class="statusTone(item)">{{ statusLabel(item) }}</span></button></div>
      <aside class="plugin-detail-placeholder"><template v-if="selected"><span class="plugin-detail-index">{{ String(items.indexOf(selected) + 1).padStart(2, "0") }}</span><div class="plugin-detail-title"><strong>{{ selected.name }}</strong><p>{{ selected.relative_path }}</p></div><section class="plugin-description"><span>{{ selected.description_source === "assembly" ? "DLL 自带说明" : (selected.description_source === "catalog" ? "已知插件" : "功能识别") }}</span><p>{{ selected.description }}</p></section><dl><div><dt>PLUGIN GUID</dt><dd>{{ selected.plugin_guid || "非 BepInEx 插件入口" }}</dd></div><div><dt>PLUGIN VERSION</dt><dd>{{ selected.plugin_version || "—" }}</dd></div></dl><section class="plugin-detail-section"><h3>依赖</h3><p v-if="!selected.dependencies?.length">未声明 BepInEx 依赖</p><ul v-else><li v-for="dependency in selected.dependencies" :key="`${dependency.guid}-${dependency.minimum_version}`"><code>{{ dependency.guid }}</code><span>{{ dependency.minimum_version ? `≥ ${dependency.minimum_version}` : "任意版本" }}</span></li></ul></section><section v-if="selected.processes?.length" class="plugin-detail-section"><h3>适用进程</h3><div class="plugin-process-tags"><code v-for="process in selected.processes" :key="process">{{ process }}</code></div></section><section v-if="selected.metadata_error" class="plugin-detail-section danger-note"><h3>解析诊断</h3><p>{{ selected.metadata_error }}</p></section></template><template v-else><span class="plugin-detail-index">00</span><div><strong>插件详情</strong><p>选择一个插件后查看版本、文件和依赖关系。</p></div></template></aside>
    </div><footer v-if="scanned" class="plugin-result-footer"><span>显示 {{ filteredItems.length }} / {{ summary.total }} 个程序集</span><span>Core {{ summary.core }} · Metadata errors {{ summary.metadata_errors }} · Duplicate GUID {{ summary.duplicates }}</span></footer>
  </section></section>
</template>
