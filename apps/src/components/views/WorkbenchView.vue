<script setup>
import { computed, ref, watch } from "vue";

const { ctx } = defineProps({
  ctx: { type: Object, required: true }
});

const packagePath = ref("");
const outputDir = ref(ctx.paths?.outputDir || "");
const busy = ref(false);
const openingModelPath = ref("");
const result = ref(null);
const notice = ref({ type: "", message: "" });

const backendReady = computed(() => ctx.backendStatus === "ready");
const canExtract = computed(() => (
  backendReady.value
  && Boolean(packagePath.value)
  && Boolean(outputDir.value)
  && !busy.value
));
const packageName = computed(() => packagePath.value.split(/[\\/]/).pop() || "尚未选择文件");

watch(
  () => ctx.paths?.outputDir,
  (value) => {
    outputDir.value = value || "";
  }
);

function formatNumber(value) {
  return new Intl.NumberFormat("zh-CN").format(Number(value || 0));
}

async function selectPackage() {
  const selected = await window.desktopApi?.selectPackageFile?.("选择 Sims 4 Package 模组包");
  if (!selected) return;
  packagePath.value = selected;
  result.value = null;
  notice.value = { type: "", message: "" };
}

async function selectOutputDirectory() {
  const selected = await window.desktopApi?.selectDirectory?.("选择 FBX 输出目录");
  if (!selected) return;
  outputDir.value = selected;
  const saved = await ctx.saveDefaultOutputDirectory?.(selected);
  result.value = null;
  notice.value = saved?.ok === false
    ? { type: "error", message: `目录可用于本次导出，但默认值保存失败：${saved.error || "未知错误"}` }
    : { type: "success", message: "输出目录已保存，下次将自动使用" };
}

async function extractPackage() {
  if (!canExtract.value) return;
  busy.value = true;
  result.value = null;
  notice.value = {
    type: "info",
    message: ctx.blenderExecutablePath
      ? "正在筛选 LOD0、解码贴图并固化 T-Pose 纯网格，请稍候…"
      : "正在筛选 LOD0 并解码贴图；未设置 Blender，将输出静态 FBX…"
  };
  try {
    const response = await window.desktopApi?.backendRequest?.(
      "/tools/sims4/package-fbx",
      {
        method: "POST",
        body: {
          package_path: packagePath.value,
          target_dir: outputDir.value,
          blender_executable_path: ctx.blenderExecutablePath || ""
        }
      }
    );
    if (!response?.ok) throw new Error(response?.error || "Package 模型提取失败");
    result.value = response.data || {};
    notice.value = { type: "success", message: response.message || "LOD0 FBX 模型与贴图已导出" };
    ctx.log?.(`[Workbench] ${response.message || "Sims 4 Package FBX export completed"}`);
  } catch (error) {
    const message = error?.message || String(error);
    const staleBackend = message.includes("hs2_reference_rig.fbx");
    notice.value = {
      type: "error",
      message: staleBackend
        ? "当前仍在运行旧版后端，请完全退出并重新启动 Star_Manager 后再导出。"
        : message
    };
    ctx.log?.(`[Workbench Error] ${message}`);
  } finally {
    busy.value = false;
  }
}

async function openResultDirectory() {
  if (result.value?.output_dir) {
    await window.desktopApi?.openDirectory?.(result.value.output_dir);
  }
}

async function revealModel(filePath) {
  if (filePath) await window.desktopApi?.showItemInFolder?.(filePath);
}

async function openModelInBlender(model) {
  if (!ctx.blenderExecutablePath) {
    notice.value = { type: "info", message: "请先在设置页面选择 blender.exe" };
    ctx.activeView = "settings";
    return;
  }
  if (!model?.path || openingModelPath.value) return;
  openingModelPath.value = model.path;
  try {
    const response = await window.desktopApi?.openFbxInBlender?.(
      ctx.blenderExecutablePath,
      model.path
    );
    if (!response?.ok) throw new Error(response?.error || "Blender 启动失败");
    notice.value = { type: "success", message: `已使用 Blender 打开 ${model.file}` };
    ctx.log?.(`[Workbench] Opened FBX in Blender: ${model.path}`);
  } catch (error) {
    notice.value = { type: "error", message: error?.message || String(error) };
    ctx.log?.(`[Workbench Error] Blender launch failed: ${error?.message || String(error)}`);
  } finally {
    openingModelPath.value = "";
  }
}
</script>

<template>
  <section class="view workbench-view">
    <div class="workbench-scroll">
      <div class="workbench-layout">
        <aside class="tool-shelf" aria-label="工作台工具">
          <div class="tool-shelf-head">
            <span>TOOLS</span>
            <strong>制作工具</strong>
          </div>
          <button class="tool-entry active" type="button" aria-current="page">
            <span class="tool-entry-index">01</span>
            <span class="tool-entry-copy">
              <b>Package → FBX</b>
              <small>Sims 4 模型提取</small>
            </span>
            <span class="tool-entry-dot"></span>
          </button>
          <div class="tool-shelf-note">
            <span>+</span>
            <p>后续模组制作工具将在这里继续扩展。</p>
          </div>
        </aside>

        <article class="tool-stage">
          <div class="stage-head">
            <div>
              <h2>模型提取</h2>
            </div>
          </div>

          <div class="file-trays">
            <section class="file-tray" :class="{ filled: packagePath }">
              <div class="tray-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24"><path d="M5 3h9l5 5v13H5V3Z"></path><path d="M14 3v6h6M8 14h8M8 18h5"></path></svg>
              </div>
              <div class="tray-copy">
                <span>源文件</span>
                <strong>{{ packageName }}</strong>
                <code :title="packagePath">{{ packagePath || "请选择一个 .package 文件" }}</code>
              </div>
              <button type="button" @click="selectPackage">{{ packagePath ? "更换" : "选择 Package" }}</button>
            </section>

            <section class="file-tray" :class="{ filled: outputDir }">
              <div class="tray-icon output" aria-hidden="true">
                <svg viewBox="0 0 24 24"><path d="M3 7h7l2 2h9v11H3V7Z"></path><path d="M8 14h8M12 11v6"></path></svg>
              </div>
              <div class="tray-copy">
                <span>输出位置</span>
                <strong>{{ outputDir ? "已选择输出目录" : "等待选择" }}</strong>
                <code :title="outputDir">{{ outputDir || "每次导出都会创建新的结果文件夹" }}</code>
              </div>
              <button type="button" @click="selectOutputDirectory">{{ outputDir ? "更换" : "选择目录" }}</button>
            </section>
          </div>

          <div class="extraction-action">
            <div class="action-note">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 3 7.5 12 12l9-4.5L12 3Z"></path><path d="m3 7.5.1 9L12 21l8.9-4.5.1-9M12 12v9"></path></svg>
              <p>
                <b>{{ ctx.blenderExecutablePath ? "HS2 对齐 T-Pose 纯网格 + 全部色板" : "HS2 坐标静态模型 + 全部色板" }}</b>
                <span v-if="ctx.blenderExecutablePath">借助原始 GEOM 权重将服装固化为 T-Pose，随后删除全部骨骼、顶点组和蒙皮数据，只保留模型网格。</span>
                <span v-else>设置 Blender 后可自动固化 T-Pose；本次仍可导出保持 HS2 大小与坐标的原始静态 FBX。</span>
              </p>
            </div>
            <button class="extract-button" type="button" :disabled="!canExtract" @click="extractPackage">
              <span v-if="busy" class="button-spinner" aria-hidden="true"></span>
              <svg v-else viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v12M7 10l5 5 5-5"></path><path d="M4 17v4h16v-4"></path></svg>
              {{ busy ? "正在加工…" : ctx.blenderExecutablePath ? "提取 T-Pose FBX" : "提取 LOD0 + 贴图" }}
            </button>
          </div>

          <div v-if="notice.message" class="workbench-notice" :class="notice.type" role="status">
            <span>{{ notice.type === "success" ? "✓" : notice.type === "error" ? "!" : "…" }}</span>
            <p>{{ notice.message }}</p>
          </div>

          <section v-if="result" class="result-board">
            <div class="result-head">
              <div>
                <span>EXPORT RECEIPT</span>
                <h3>本次导出结果</h3>
              </div>
              <button type="button" @click="openResultDirectory">打开结果目录</button>
            </div>
            <div class="result-summary">
              <div><span>FBX 模型</span><strong>{{ result.exported_model_count }}</strong></div>
              <div><span>T-Pose 网格</span><strong>{{ result.t_pose_model_count || 0 }}</strong></div>
              <div><span>PNG 贴图</span><strong>{{ result.texture_count }}</strong></div>
              <div><span>GEOM 资源</span><strong>{{ result.geom_resource_count }}</strong></div>
              <div><span>跳过低模</span><strong>{{ result.skipped_non_lod0_count }}</strong></div>
              <code :title="result.output_dir">{{ result.output_dir }}</code>
            </div>
            <div class="result-list">
              <div v-for="model in result.exports" :key="model.path" class="result-model-row">
                <span class="result-file-mark">FBX</span>
                <span class="result-file-copy">
                  <b>{{ model.file }}</b>
                  <small>
                    {{ formatNumber(model.vertices) }} 顶点 · {{ formatNumber(model.triangles) }} 三角面 · {{ model.uv_sets }} 套 UV · HS2 坐标
                    <template v-if="model.t_pose_baked"> · T-Pose 已固化 · 纯网格（无骨骼、无蒙皮）</template>
                    <template v-else> · 静态网格（未固化 T-Pose）</template>
                    <template v-if="model.removed_untextured_triangles"> · 已裁剪 {{ formatNumber(model.removed_untextured_triangles) }} 个无贴图面</template>
                    <template v-if="model.default_texture"> · 默认 {{ model.default_texture.file }}</template>
                  </small>
                </span>
                <span class="result-file-actions">
                  <button
                    class="blender-open-button"
                    type="button"
                    :disabled="Boolean(openingModelPath)"
                    :title="ctx.blenderExecutablePath || '前往设置页面选择 blender.exe'"
                    @click="openModelInBlender(model)"
                  >
                    <span aria-hidden="true">B</span>
                    {{ openingModelPath === model.path ? "正在启动…" : ctx.blenderExecutablePath ? "Blender 打开" : "设置 Blender" }}
                  </button>
                  <button class="result-locate-button" type="button" @click="revealModel(model.path)">定位 ↗</button>
                </span>
              </div>
            </div>
          </section>
        </article>
      </div>
    </div>
  </section>
</template>

<style scoped>
.workbench-view {
  overflow: hidden;
}

.workbench-scroll {
  height: 100%;
  overflow: auto;
  padding: 0 10px 12px 0;
}

.result-head span {
  color: #48636f;
  font-family: var(--mono);
  font-size: 11px;
  font-weight: 900;
  letter-spacing: .12em;
}

.workbench-layout {
  display: grid;
  grid-template-columns: 235px minmax(0, 1fr);
  gap: 18px;
  margin-top: 18px;
}

.tool-shelf,
.tool-stage {
  border: 3px solid var(--line-strong);
  border-radius: 8px;
  background: rgba(255, 253, 250, .97);
  box-shadow: var(--soft-shadow);
}

.tool-shelf {
  align-self: start;
  overflow: hidden;
}

.tool-shelf-head {
  display: grid;
  gap: 3px;
  padding: 16px;
  border-bottom: 1px solid var(--line);
  background: #f5fbff;
}

.tool-shelf-head span {
  color: #69808b;
  font-family: var(--mono);
  font-size: 10px;
  font-weight: 900;
  letter-spacing: .16em;
}

.tool-shelf-head strong {
  font-size: 17px;
}

.tool-entry {
  width: calc(100% - 16px);
  height: auto;
  min-height: 76px;
  display: grid;
  grid-template-columns: 35px minmax(0, 1fr) 8px;
  align-items: center;
  gap: 9px;
  margin: 8px;
  padding: 10px;
  border: 2px solid var(--line-strong);
  text-align: left;
  box-shadow: 3px 4px 0 #2e2e2e;
}

.tool-entry.active {
  background: linear-gradient(100deg, #ffe5ef, #e8f7ff);
}

.tool-entry-index {
  display: grid;
  place-items: center;
  width: 35px;
  height: 35px;
  border: 2px solid var(--line-strong);
  border-radius: 5px;
  background: #fff;
  font-family: var(--mono);
  font-size: 12px;
}

.tool-entry-copy {
  min-width: 0;
  display: grid;
  gap: 3px;
}

.tool-entry-copy b,
.tool-entry-copy small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tool-entry-copy b {
  font-size: 13px;
}

.tool-entry-copy small {
  font-size: 11px;
}

.tool-entry-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #42b88d;
  box-shadow: 0 0 0 3px rgba(66, 184, 141, .16);
}

.tool-shelf-note {
  display: flex;
  gap: 10px;
  margin: 8px;
  padding: 13px;
  border: 1px dashed #bdb6bc;
  border-radius: 6px;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.55;
}

.tool-shelf-note > span {
  font-family: var(--mono);
  font-size: 18px;
  font-weight: 900;
}

.tool-stage {
  min-width: 0;
  padding: 14px 22px 22px;
}

.stage-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}

.stage-head h2 {
  margin: 0;
  font-size: 22px;
}

.file-trays {
  display: grid;
  gap: 10px;
}

.file-tray {
  display: grid;
  grid-template-columns: 48px minmax(0, 1fr) auto;
  align-items: center;
  gap: 13px;
  min-width: 0;
  padding: 13px;
  border: 2px solid #c9c4c8;
  border-radius: 7px;
  background: #fff;
  transition: border-color .15s ease, background .15s ease;
}

.file-tray.filled {
  border-color: var(--line-strong);
  background: #fcfeff;
}

.tray-icon {
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  border: 2px solid var(--line-strong);
  border-radius: 6px;
  background: #fff0f6;
}

.tray-icon.output {
  background: #e7f7ff;
}

.tray-icon svg {
  width: 25px;
  height: 25px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.tray-copy {
  min-width: 0;
  display: grid;
  gap: 3px;
}

.tray-copy > span {
  color: var(--muted);
  font-size: 11px;
  font-weight: 800;
}

.tray-copy strong,
.tray-copy code {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tray-copy code {
  color: #60707a;
  font-family: var(--mono);
  font-size: 11px;
}

.file-tray > button {
  min-width: 112px;
  padding: 0 12px;
  box-shadow: 2px 3px 0 #2e2e2e;
}

.extraction-action {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-top: 16px;
  padding: 14px;
  border: 1px solid #d5d0cc;
  border-radius: 7px;
  background: #fffaf3;
}

.action-note {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 11px;
}

.action-note svg {
  flex: 0 0 30px;
  width: 30px;
  height: 30px;
  fill: none;
  stroke: #59656a;
  stroke-width: 1.6;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.action-note p {
  display: grid;
  gap: 3px;
}

.action-note span {
  color: var(--muted);
  font-size: 12px;
}

.extract-button {
  min-width: 180px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 0 18px;
  background: var(--teal);
  box-shadow: 4px 5px 0 #2e2e2e;
}

.extract-button svg,
.button-spinner {
  width: 18px;
  height: 18px;
}

.extract-button svg {
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.button-spinner {
  border: 2px solid rgba(0, 0, 0, .2);
  border-top-color: #111;
  border-radius: 50%;
  animation: spin .7s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.workbench-notice {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-top: 12px;
  padding: 10px 12px;
  border: 1px solid #9ebbd0;
  border-radius: 6px;
  background: #eef8ff;
  color: #315d75;
  font-size: 13px;
  font-weight: 700;
}

.workbench-notice > span {
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border: 1px solid currentColor;
  border-radius: 50%;
  font-family: var(--mono);
  font-weight: 900;
}

.workbench-notice.success {
  border-color: #92c6ae;
  background: #effbf4;
  color: #177052;
}

.workbench-notice.error {
  border-color: #e2a3a9;
  background: #fff1f2;
  color: #a13843;
}

.result-board {
  margin-top: 14px;
  overflow: hidden;
  border: 2px solid var(--line-strong);
  border-radius: 7px;
  background: #fff;
}

.result-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 13px 14px;
  border-bottom: 1px solid var(--line);
  background: linear-gradient(90deg, #f2fbff, #fff4f8);
}

.result-head h3 {
  margin-top: 3px;
}

.result-head button {
  padding: 0 12px;
}

.result-summary {
  display: grid;
  grid-template-columns: repeat(5, minmax(86px, 112px)) minmax(0, 1fr);
  gap: 10px;
  align-items: stretch;
  padding: 12px;
  border-bottom: 1px solid var(--line);
}

.result-summary > div {
  display: grid;
  gap: 2px;
  padding: 8px 10px;
  border: 1px solid #d8d7d5;
  border-radius: 5px;
  background: #fafafa;
}

.result-summary span {
  color: var(--muted);
  font-size: 11px;
}

.result-summary strong {
  font-family: var(--mono);
  font-size: 18px;
}

.result-summary > code {
  min-width: 0;
  display: flex;
  align-items: center;
  overflow: hidden;
  padding: 10px;
  border: 1px dashed #bcb8b5;
  border-radius: 5px;
  color: #5c6670;
  font-family: var(--mono);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.result-list {
  display: grid;
}

.result-model-row {
  width: 100%;
  min-height: 58px;
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) auto;
  align-items: center;
  gap: 11px;
  padding: 9px 13px;
  background: #fff;
  text-align: left;
}

.result-model-row + .result-model-row {
  border-top: 1px solid #e1dedb;
}

.result-model-row:hover {
  background: #f5fbff;
}

.result-model-row.is-selected {
  background: linear-gradient(90deg, #eefaff, #fff4f8);
  box-shadow: inset 4px 0 0 var(--teal);
}

.result-file-mark {
  display: grid;
  place-items: center;
  width: 42px;
  height: 34px;
  border: 2px solid var(--line-strong);
  border-radius: 5px;
  background: var(--teal-soft);
  font-family: var(--mono);
  font-size: 11px;
  font-weight: 900;
}

.result-file-copy {
  min-width: 0;
  display: grid;
  gap: 3px;
}

.result-file-copy b,
.result-file-copy small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.result-open {
  color: #4c6572;
  font-size: 12px;
  font-weight: 900;
}

.result-file-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.result-file-actions button {
  min-height: 34px;
  padding: 0 10px;
  font-size: 11px;
}

.blender-open-button {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border-color: #2f3f47;
  background: linear-gradient(100deg, #ffe4ef, #dff4ff);
  box-shadow: 2px 3px 0 #2e2e2e;
}

.blender-open-button > span {
  display: grid;
  place-items: center;
  width: 18px;
  height: 18px;
  border: 1px solid currentColor;
  border-radius: 50%;
  font-family: var(--mono);
  font-size: 9px;
  font-weight: 900;
}

.result-locate-button {
  border-color: #a8b2b8;
  background: #fff;
  color: #4c6572;
  box-shadow: none;
}

@media (max-width: 1320px) {
  .workbench-layout { grid-template-columns: 205px minmax(0, 1fr); }
  .result-summary { grid-template-columns: repeat(5, 1fr); }
  .result-summary > code { grid-column: 1 / -1; }
}
</style>
