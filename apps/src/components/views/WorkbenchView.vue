<script setup>
import { computed, nextTick, onActivated, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import ModelPreview from "../ModelPreview.vue";
import TextureProcessorDialog from "../TextureProcessorDialog.vue";
import blenderIcon from "../../assets/blender-icon.png";
import sb3utilityIcon from "../../assets/sb3utility-icon.png";

const { ctx } = defineProps({
  ctx: { type: Object, required: true }
});

const profileForm = reactive({
  authorId: ctx.workbenchAuthorId || "",
  workspacePath: ctx.workbenchWorkspacePath || ""
});
const setupMode = ref(!hasProfile(ctx.workbenchAuthorId, ctx.workbenchWorkspacePath));
const savingProfile = ref(false);
const setupError = ref("");
const notice = reactive({ type: "", message: "" });
const projectPrompt = reactive({ open: false, name: "", error: "", busy: false });
const projectListCollapsed = ref(false);
const projectSearchQuery = ref("");
const PROJECT_LIST_COLLAPSED_KEY = "star-manager.workbench-project-list-collapsed";
const PROJECT_SELECTION_ORDER_KEY = "star-manager.workbench-project-selection-order";
const projectSelectionOrder = ref(readProjectSelectionOrder());
const deletingProjectId = ref("");
const deletingItemId = ref("");
const deletePrompt = reactive({
  open: false,
  title: "",
  message: "",
  detail: "",
  resolve: null
});
const deletePromptDialog = ref(null);
const items = ref([]);
const selectedItem = ref(null);
const itemBrowser = reactive({ loading: false, error: "" });
const projectUnity3dLibrary = reactive({ loading: false, error: "", files: [] });
let projectUnity3dLoadToken = 0;
const projectAssetLibrary = reactive({ loading: false, error: "", textures: [], models: [], total: 0 });
let projectAssetLoadToken = 0;
const workbenchTexturePreview = reactive({ asset: null, dataUrl: "", loading: false, error: "", width: 0, height: 0 });
const WORKBENCH_TEXTURE_PREVIEW_MAX_DIMENSION = 1200;
let workbenchTexturePreviewToken = 0;
const itemPrompt = reactive({ open: false, name: "", category: "", error: "", busy: false });
const resourceEditor = reactive({
  open: false,
  mode: "existing",
  loading: false,
  saving: false,
  error: "",
  files: [],
  relativePath: "",
  sourcePath: "",
  candidates: [],
  mainData: "",
  mainDataPathId: 0,
  mainDataAssetFile: "",
  objectCount: 0,
  gameObjectCount: 0
});
const templatePicker = reactive({
  selected: null,
  preparedPath: ""
});
const templatePreprocess = reactive({
  busy: false,
  error: "",
  renameName: ""
});
const pendingTemplateSelection = ref(null);

const selectedItemRecord = computed(() => selectedItem.value?.csvData?.record || {});
const workbenchModelPreview = ref(null);
const workbenchThumbnail = reactive({
  dataUrl: "",
  sourcePath: "",
  loading: false,
  busy: false,
  missing: true,
  error: ""
});
let workbenchThumbnailLoadToken = 0;
const mainResourceCheck = reactive({
  loading: false,
  status: "idle",
  message: "",
  fields: {},
  token: 0
});
const openingMainAb = ref(false);
const openingWorkbenchFbxPath = ref("");
const openingWorkbenchSb3Path = ref("");
const textureProcessorOpen = ref(false);
const textureGroupDefinitions = [
  { index: 1, key: "texture-1", fields: ["MainTex", "ColorMaskTex"] },
  { index: 2, key: "texture-2", fields: ["MainTex02", "ColorMask02Tex"] },
  { index: 3, key: "texture-3", fields: ["MainTex03", "ColorMask03Tex"] }
];
const textureFieldNames = textureGroupDefinitions.flatMap((group) => group.fields);
const MAX_TEXTURE_GROUPS = textureGroupDefinitions.length;
const editableResourceFields = ["Name", "MainData", ...textureFieldNames];
const editableResourceValues = reactive(
  Object.fromEntries(editableResourceFields.map((field) => [field, ""]))
);
const resourceFieldSaving = ref("");
const textureImporting = ref("");
const workbenchPreviewRevision = ref(0);
const workbenchPreviewReady = ref(false);
const packagingMod = ref(false);
const packagingProgress = reactive({ stage: "", message: "", current: 0, total: 0, fileName: "" });
let removePackageProgressListener = null;
const packageSuccessPrompt = reactive({
  open: false,
  jumping: false,
  error: "",
  databaseUpdated: false,
  databaseError: "",
  projectGuid: "",
  projectName: "",
  fileName: "",
  fileCount: 0,
  replacedCount: 0
});
const sims4FbxPrompt = reactive({
  open: false,
  packagePath: "",
  outputDir: "",
  outputDirProjectId: "",
  busy: false,
  deletingResult: false,
  openingModelPath: "",
  result: null,
  notice: { type: "", message: "" }
});
const fbxTransformPrompt = reactive({
  open: false,
  sourcePath: "",
  sourceRelativePath: "",
  backupOriginal: true,
  busy: false,
  error: "",
  result: null,
  notice: { type: "", message: "" }
});
const fbxSkinPrompt = reactive({
  open: false,
  sourcePath: "",
  sourceRelativePath: "",
  backupOriginal: true,
  busy: false,
  error: "",
  result: null,
  notice: { type: "", message: "" }
});
const hs2SkeletonPrompt = reactive({
  open: false,
  sourcePath: "",
  sourceRelativePath: "",
  skeletonPath: "",
  backupOriginal: true,
  busy: false,
  error: "",
  result: null,
  notice: { type: "", message: "" }
});
const fbxWeightPrompt = reactive({
  open: false,
  sourcePath: "",
  targetPath: "",
  targetRelativePath: "",
  backupOriginal: true,
  busy: false,
  error: "",
  result: null,
  notice: { type: "", message: "" }
});
const textureGroupCount = ref(1);
const selectedItemResourceGroups = computed(() => [{
  key: "model",
  title: "模型",
  fields: ["MainAB", "MainData"]
}]);
const textureGroups = computed(() => textureGroupDefinitions.slice(0, textureGroupCount.value));
const sims4FbxPackageName = computed(() => (
  String(sims4FbxPrompt.packagePath || "").split(/[\\/]/).pop() || "尚未选择文件"
));
const canExportSims4Fbx = computed(() => (
  ctx.backendStatus === "ready"
  && Boolean(sims4FbxPrompt.packagePath)
  && Boolean(sims4FbxPrompt.outputDir)
  && !sims4FbxPrompt.busy
  && !sims4FbxPrompt.deletingResult
));

const itemCategoryOptions = computed(() => {
  const seen = new Set();
  const sourceOptions = Array.isArray(ctx.workbenchItemCategoryOptions)
    ? ctx.workbenchItemCategoryOptions
    : ctx.itemKindOptions;
  return (Array.isArray(sourceOptions) ? sourceOptions : [])
    .filter((option) => {
      const value = String(option?.value || "").trim();
      return value && !value.startsWith("__");
    })
    .map((option) => ({
      value: String(option.value).trim(),
      label: String(option.label || option.value).trim()
    }))
    .filter((option) => {
      if (seen.has(option.value)) return false;
      seen.add(option.value);
      return true;
    });
});

onMounted(() => {
  projectListCollapsed.value = readProjectListCollapsed();
  rememberProjectSelection(ctx.workbenchActiveProjectId);
  removePackageProgressListener = window.desktopApi?.onWorkbenchPackageProgress?.((progress = {}) => {
    Object.assign(packagingProgress, {
      stage: String(progress.stage || ""),
      message: String(progress.message || ""),
      current: Number(progress.current || 0),
      total: Number(progress.total || 0),
      fileName: String(progress.fileName || "")
    });
  }) || null;
});

onActivated(() => {
  // KeepAlive reactivations do not run onMounted again. Template selections
  // arrive while this page is deactivated, so consume them on every return.
  const pending = ctx.consumeWorkbenchTemplateSelection?.();
  if (!pending) return;
  pendingTemplateSelection.value = pending;
  void nextTick(() => restorePendingTemplateSelection());
});

onBeforeUnmount(() => {
  removePackageProgressListener?.();
  removePackageProgressListener = null;
});

const packagingLabel = computed(() => {
  if (!packagingMod.value) return "打包模组";
  if (packagingProgress.stage === "database") {
    if (packagingProgress.current > 0 && packagingProgress.total > 0) {
      return `同步数据库 ${packagingProgress.current}%`;
    }
    return packagingProgress.message || "正在同步数据库…";
  }
  if (packagingProgress.current > 0 && packagingProgress.total > 0) {
    return `打包中 ${packagingProgress.current}/${packagingProgress.total}`;
  }
  return packagingProgress.message || "打包中...";
});

function textureGroupCountForItem(item) {
  const record = item?.csvData?.record || {};
  let count = 1;
  textureGroupDefinitions.forEach((group, index) => {
    if (group.fields.some((field) => String(record[field] || "").trim())) {
      count = index + 1;
    }
  });
  return Math.min(MAX_TEXTURE_GROUPS, count);
}

function textureFieldsSignature(record) {
  return textureFieldNames.map((field) => String(record?.[field] || "").trim()).join("|");
}

function textureGroupDefaultValue(field, groupIndex) {
  const itemName = String(selectedItemRecord.value.Name || selectedItem.value?.name || "").trim();
  if (/^MainTex\d*$/.test(String(field || ""))) {
    return itemName ? `${itemName}_diffuse${groupIndex}` : "";
  }
  if (/^ColorMask\d*Tex$/.test(String(field || ""))) return `mc_${groupIndex}`;
  return "";
}

function textureFieldLabel(field, groupIndex = 1) {
  const baseLabel = String(field || "").startsWith("MainTex") ? "MainTex" : "ColorMaskTex";
  const suffix = Number(groupIndex) > 1 ? String(groupIndex).padStart(2, "0") : "";
  return `${baseLabel}${suffix}`;
}

const projectsForWorkspace = computed(() => {
  const workspacePath = comparablePath(ctx.workbenchWorkspacePath);
  if (!workspacePath || !Array.isArray(ctx.workbenchProjects)) return [];
  const projects = ctx.workbenchProjects.filter((project) => {
    const projectPath = comparablePath(project?.path);
    return projectPath === workspacePath || projectPath.startsWith(`${workspacePath}\\`);
  });
  const selectionIndex = new Map(projectSelectionOrder.value.map((id, index) => [id, index]));
  return projects
    .map((project, sourceIndex) => ({ project, sourceIndex }))
    .sort((a, b) => {
      const aIndex = selectionIndex.get(String(a.project?.id || ""));
      const bIndex = selectionIndex.get(String(b.project?.id || ""));
      if (aIndex !== undefined && bIndex !== undefined) return bIndex - aIndex;
      if (aIndex !== undefined) return -1;
      if (bIndex !== undefined) return 1;
      return b.sourceIndex - a.sourceIndex;
    })
    .map(({ project }) => project);
});
const hasProjects = computed(() => projectsForWorkspace.value.length > 0);
const filteredProjects = computed(() => {
  const query = String(projectSearchQuery.value || "").trim().toLocaleLowerCase();
  if (!query) return projectsForWorkspace.value;

  return projectsForWorkspace.value.filter((project) => [
    project?.name,
    project?.guid,
    project?.path
  ].some((value) => String(value || "").toLocaleLowerCase().includes(query)));
});
const activeProject = computed(() => {
  const activeId = String(ctx.workbenchActiveProjectId || "").trim();
  return projectsForWorkspace.value.find((project) => String(project?.id || "") === activeId) || null;
});
watch(projectSearchQuery, (value) => {
  if (String(value || "").trim()) projectListCollapsed.value = false;
});
const canPreviewSelectedItem = computed(() => (
  Boolean(activeProject.value && selectedItem.value)
  && mainResourceFieldStatus("MainAB") === "found"
  && mainResourceFieldStatus("MainData") === "found"
));
const workbenchPreviewKey = computed(() => [
  activeProject.value?.id,
  selectedItem.value?.id,
  selectedItemRecord.value.MainAB,
  selectedItemRecord.value.MainData,
  workbenchPreviewRevision.value
].map((value) => String(value || "").trim()).join("|"));
function hasProfile(authorId, workspacePath) {
  return Boolean(String(authorId || "").trim() && String(workspacePath || "").trim());
}

function comparablePath(value) {
  return String(value || "")
    .trim()
    .replace(/[\\/]+$/g, "")
    .replaceAll("/", "\\")
    .toLocaleLowerCase();
}

function defaultTemplateRenameName(item = selectedItem.value) {
  const record = item?.csvData?.record || {};
  const itemName = String(record.Name || item?.name || "").trim();
  return itemName ? `${itemName}_obj` : "";
}

function pendingTemplateTargetMatches(item, request) {
  const target = request?.targetItem || {};
  const targetRecordId = String(request?.itemId || target.csvData?.record?.ID || "").trim();
  const targetCsvPath = String(request?.csvPath || target.csvPath || "").trim();
  const rowRecord = item?.csvData?.record || {};
  const rowRecordId = String(rowRecord.ID || "").trim();
  const rowCsvPath = String(item?.csvPath || "").trim();

  if (targetRecordId && rowRecordId === targetRecordId && (!targetCsvPath || rowCsvPath === targetCsvPath)) {
    return true;
  }
  return Boolean(target.id && String(item?.id || "") === String(target.id));
}

function restorePendingTemplateSelection() {
  const pending = pendingTemplateSelection.value;
  const project = activeProject.value;
  if (!pending || !project) return false;
  if (pending.request?.projectId && String(pending.request.projectId) !== String(project.id)) return false;

  const target = items.value.find((item) => pendingTemplateTargetMatches(item, pending.request));
  if (!target) return false;

  selectedItem.value = target;
  const result = pending.result;
  if (result && !result.cancelled) {
    resourceEditor.open = true;
    resourceEditor.mode = "template";
    resourceEditor.loading = false;
    resourceEditor.saving = false;
    resourceEditor.error = "";
    resourceEditor.candidates = Array.isArray(result.candidates) ? result.candidates : [];
    resourceEditor.mainData = String(result.mainData || resourceEditor.candidates[0]?.value || "");
    resourceEditor.mainDataPathId = Number(result.mainDataPathId || 0);
    resourceEditor.mainDataAssetFile = String(result.mainDataAssetFile || "");
    resourceEditor.objectCount = Number(result.objectCount || 0);
    resourceEditor.gameObjectCount = Number(result.gameObjectCount || 0);
    templatePicker.selected = result.templateItem || null;
    templatePicker.preparedPath = String(result.preparedPath || "");
    syncMainDataCandidate();
    templatePreprocess.error = "";
    templatePreprocess.renameName = defaultTemplateRenameName(target);
    showNotice("success", "已返回工作台，请确认 MainData 后写入当前物品。");
  }
  pendingTemplateSelection.value = null;
  return true;
}

watch(
  () => [ctx.workbenchAuthorId, ctx.workbenchWorkspacePath],
  ([authorId, workspacePath]) => {
    if (!savingProfile.value) {
      profileForm.authorId = authorId || "";
      profileForm.workspacePath = workspacePath || "";
    }
    if (hasProfile(authorId, workspacePath)) setupMode.value = false;
  }
);

watch(
  () => ctx.paths?.outputDir,
  (value) => {
    if (!sims4FbxPrompt.outputDir) sims4FbxPrompt.outputDir = String(value || "").trim();
  }
);

watch(
  () => ctx.workbenchActiveProjectId,
  (projectId) => {
    rememberProjectSelection(projectId);
  },
  { immediate: true }
);

watch(
  () => [setupMode.value, projectsForWorkspace.value.length],
  ([isSetup, projectCount]) => {
    if (!isSetup && projectCount === 0 && !projectPrompt.busy) {
      openProjectPrompt();
    }
  },
  { immediate: true }
);

watch(
  () => activeProject.value?.id,
  async () => {
    selectedItem.value = null;
    resetWorkbenchTexturePreview();
    await loadItemsForActiveProject();
    await loadWorkbenchUnity3dFiles();
    await loadWorkbenchProjectAssets();
    restorePendingTemplateSelection();
  },
  { immediate: true }
);

watch(
  () => [activeProject.value?.id, selectedItem.value?.id].join("|"),
  () => {
    textureGroupCount.value = textureGroupCountForItem(selectedItem.value);
    workbenchPreviewReady.value = false;
  },
  { immediate: true }
);

watch(
  () => items.value.map((item) => item.id).join("|"),
  () => {
    if (selectedItem.value && !items.value.some((item) => item.id === selectedItem.value.id)) {
      selectedItem.value = null;
    }
    restorePendingTemplateSelection();
  }
);

watch(
  () => [
    activeProject.value?.id,
    selectedItem.value?.id,
    selectedItemRecord.value.ThumbAB,
    selectedItemRecord.value.ThumbTex
  ].map((value) => String(value || "").trim()).join("|"),
  () => {
    void loadWorkbenchItemThumbnail();
  },
  { immediate: true }
);

watch(
  () => [
    activeProject.value?.id,
    selectedItem.value?.id,
    selectedItemRecord.value.Name,
    selectedItemRecord.value.MainAB,
    selectedItemRecord.value.MainData,
    textureFieldsSignature(selectedItemRecord.value)
  ].map((value) => String(value || "").trim()).join("|"),
  () => {
    void checkMainResource();
  },
  { immediate: true }
);

watch(
  () => [
    activeProject.value?.id,
    selectedItem.value?.id,
    selectedItemRecord.value.MainData,
    textureFieldsSignature(selectedItemRecord.value)
  ].map((value) => String(value || "").trim()).join("|"),
  () => {
    syncEditableResourceValues();
  },
  { immediate: true }
);

async function selectWorkspace() {
  const selected = await window.desktopApi?.selectDirectory?.("选择工具台工作空间");
  if (!selected) return;
  profileForm.workspacePath = selected;
  setupError.value = "";
}

async function saveProfile() {
  const authorId = profileForm.authorId.trim();
  const workspacePath = profileForm.workspacePath.trim();
  if (!authorId) {
    setupError.value = "请填写模组作者 ID，后续作品信息会使用这个署名。";
    return;
  }
  if (!workspacePath) {
    setupError.value = "请选择一个工作空间文件夹。";
    return;
  }

  savingProfile.value = true;
  setupError.value = "";
  try {
    const result = await ctx.saveWorkbenchProfile?.(authorId, workspacePath);
    if (!result?.ok) throw new Error(result?.error || "工具台信息保存失败");
    notice.type = "success";
    notice.message = "工坊信息已保存，欢迎开始制作。";
    setupMode.value = false;
  } catch (error) {
    setupError.value = error?.message || String(error);
  } finally {
    savingProfile.value = false;
  }
}

function openProjectPrompt() {
  projectPrompt.name = "";
  projectPrompt.error = "";
  projectPrompt.open = true;
}

function readProjectSelectionOrder() {
  try {
    const value = JSON.parse(window.localStorage?.getItem(PROJECT_SELECTION_ORDER_KEY) || "[]");
    return Array.isArray(value)
      ? value.map((id) => String(id || "").trim()).filter(Boolean).slice(-100)
      : [];
  } catch {
    return [];
  }
}

function rememberProjectSelection(projectId) {
  const id = String(projectId || "").trim();
  if (!id) return;
  projectSelectionOrder.value = [
    ...projectSelectionOrder.value.filter((currentId) => currentId !== id),
    id
  ].slice(-100);
  try {
    window.localStorage?.setItem(PROJECT_SELECTION_ORDER_KEY, JSON.stringify(projectSelectionOrder.value));
  } catch {
    // LocalStorage may be unavailable; ordering still applies for the current view.
  }
}

function readProjectListCollapsed() {
  try {
    return window.localStorage?.getItem(PROJECT_LIST_COLLAPSED_KEY) === "1";
  } catch {
    return false;
  }
}

function toggleProjectList() {
  projectListCollapsed.value = !projectListCollapsed.value;
  try {
    window.localStorage?.setItem(PROJECT_LIST_COLLAPSED_KEY, projectListCollapsed.value ? "1" : "0");
  } catch {
    // LocalStorage may be unavailable; the toggle still applies for the current view.
  }
}

function collapseProjectList() {
  projectListCollapsed.value = true;
  try {
    window.localStorage?.setItem(PROJECT_LIST_COLLAPSED_KEY, "1");
  } catch {
    // LocalStorage may be unavailable; the collapse still applies for the current view.
  }
}

function showNotice(type, message) {
  notice.type = type;
  notice.message = message;
}

function askDeleteConfirmation({ title, message, detail }) {
  return new Promise((resolve) => {
    if (typeof deletePrompt.resolve === "function") deletePrompt.resolve(false);
    deletePrompt.title = title;
    deletePrompt.message = message;
    deletePrompt.detail = detail;
    deletePrompt.resolve = resolve;
    deletePrompt.open = true;
  });
}

function closeDeletePrompt(confirmed = false) {
  const resolve = deletePrompt.resolve;
  deletePrompt.resolve = null;
  deletePrompt.open = false;
  if (typeof resolve === "function") resolve(confirmed);
}

watch(
  () => deletePrompt.open,
  (open) => {
    if (open) void nextTick(() => deletePromptDialog.value?.focus());
  }
);

async function loadItemsForActiveProject() {
  const project = activeProject.value;
  items.value = [];
  itemBrowser.error = "";
  if (!project?.id || !project.path) return;

  itemBrowser.loading = true;
  try {
    const scanItems = window.desktopApi?.scanWorkbenchItems;
    if (typeof scanItems !== "function") {
      items.value = [];
      return;
    }
    const result = await scanItems({
      projectId: project.id,
      projectPath: project.path
    });
    if (!result?.ok) throw new Error(result?.error || "物品读取失败");
    items.value = Array.isArray(result.items) ? result.items : [];
  } catch (error) {
    itemBrowser.error = error?.message || String(error);
  } finally {
    itemBrowser.loading = false;
  }
}

async function loadWorkbenchItemThumbnail() {
  const project = activeProject.value;
  const item = selectedItem.value;
  const token = ++workbenchThumbnailLoadToken;
  workbenchThumbnail.dataUrl = "";
  workbenchThumbnail.sourcePath = "";
  workbenchThumbnail.error = "";
  workbenchThumbnail.missing = true;
  if (!project?.id || !project.path || !item?.csvPath) {
    workbenchThumbnail.loading = false;
    return;
  }

  const thumbAB = String(selectedItemRecord.value.ThumbAB || "").trim();
  const thumbTex = String(selectedItemRecord.value.ThumbTex || "").trim();
  if (!thumbAB) {
    workbenchThumbnail.loading = false;
    return;
  }

  const loadThumbnail = window.desktopApi?.loadWorkbenchThumbnail;
  if (typeof loadThumbnail !== "function") {
    workbenchThumbnail.loading = false;
    workbenchThumbnail.error = "工作台缩略图接口未加载";
    return;
  }

  workbenchThumbnail.loading = true;
  try {
    const result = await loadThumbnail({
      projectId: project.id,
      projectPath: project.path,
      csvPath: item.csvPath,
      itemId: selectedItemRecord.value.ID,
      thumbAB,
      thumbTex
    });
    if (token !== workbenchThumbnailLoadToken) return;
    if (result?.ok && result.dataUrl) {
      workbenchThumbnail.dataUrl = result.dataUrl;
      workbenchThumbnail.sourcePath = String(result.sourcePath || "");
      workbenchThumbnail.missing = false;
      return;
    }
    workbenchThumbnail.error = String(result?.error || "缩略图文件不存在");
  } catch (error) {
    if (token === workbenchThumbnailLoadToken) {
      workbenchThumbnail.error = error?.message || String(error);
    }
  } finally {
    if (token === workbenchThumbnailLoadToken) workbenchThumbnail.loading = false;
  }
}

function handleWorkbenchThumbnailError() {
  workbenchThumbnail.dataUrl = "";
  workbenchThumbnail.missing = true;
  workbenchThumbnail.error = "缩略图无法在当前窗口显示";
}

async function loadWorkbenchProjectAssets() {
  const project = activeProject.value;
  const token = ++projectAssetLoadToken;
  projectAssetLibrary.loading = false;
  projectAssetLibrary.error = "";
  projectAssetLibrary.textures = [];
  projectAssetLibrary.models = [];
  projectAssetLibrary.total = 0;
  if (!project?.id || !project.path) return;

  const scanAssets = window.desktopApi?.scanWorkbenchAssetFiles;
  if (typeof scanAssets !== "function") {
    projectAssetLibrary.error = "工程资源扫描功能尚未加载，请重启应用后再试。";
    return;
  }

  projectAssetLibrary.loading = true;
  try {
    const result = await scanAssets({
      projectId: project.id,
      projectPath: project.path
    });
    if (token !== projectAssetLoadToken) return;
    if (!result?.ok) throw new Error(result?.error || "工程资源读取失败");
    projectAssetLibrary.textures = Array.isArray(result.textures) ? result.textures : [];
    projectAssetLibrary.models = Array.isArray(result.models) ? result.models : [];
    projectAssetLibrary.total = Number(result.total || projectAssetLibrary.textures.length + projectAssetLibrary.models.length);
  } catch (error) {
    if (token === projectAssetLoadToken) {
      projectAssetLibrary.error = error?.message || String(error);
    }
  } finally {
    if (token === projectAssetLoadToken) projectAssetLibrary.loading = false;
  }
}

function formatWorkbenchAssetSize(value) {
  const bytes = Number(value || 0);
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

function locateWorkbenchAsset(asset) {
  if (!asset?.path) return;
  void window.desktopApi?.showItemInFolder?.(asset.path);
}

async function openWorkbenchAssetInSb3Utility(asset) {
  if (!asset?.path || openingWorkbenchSb3Path.value) return;
  const openAsset = window.desktopApi?.openWorkbenchAssetInSb3Utility;
  if (typeof openAsset !== "function") {
    showNotice("error", "SB3Utility 打开接口未加载，请重启应用后再试。");
    return;
  }

  openingWorkbenchSb3Path.value = asset.path;
  try {
    const result = await openAsset({
      projectId: activeProject.value?.id,
      projectPath: activeProject.value?.path,
      relativePath: asset.relativePath
    });
    if (!result?.ok) throw new Error(result?.error || "无法使用 SB3Utility 打开资源");
    showNotice("success", `已使用 SB3Utility 打开 ${asset.name}`);
    ctx.log?.(`[Workbench] Opened asset in SB3Utility: ${asset.path}`);
  } catch (error) {
    showNotice("error", error?.message || String(error));
    ctx.log?.(`[Workbench Error] SB3Utility launch failed: ${error?.message || String(error)}`);
  } finally {
    openingWorkbenchSb3Path.value = "";
  }
}

async function openWorkbenchAssetInBlender(asset) {
  if (!asset?.path || openingWorkbenchFbxPath.value) return;
  if (!ctx.blenderExecutablePath) {
    showNotice("info", "请先在设置页面选择 blender.exe。");
    ctx.activeView = "settings";
    return;
  }
  const openFbxInBlender = window.desktopApi?.openFbxInBlender;
  if (typeof openFbxInBlender !== "function") {
    showNotice("error", "Blender 打开接口未加载，请重启应用后再试。");
    return;
  }

  openingWorkbenchFbxPath.value = asset.path;
  try {
    const result = await openFbxInBlender(ctx.blenderExecutablePath, asset.path);
    if (!result?.ok) throw new Error(result?.error || "Blender 启动失败");
    showNotice("success", `已使用 Blender 打开 ${asset.name}`);
    ctx.log?.(`[Workbench] Opened FBX in Blender: ${asset.path}`);
  } catch (error) {
    showNotice("error", error?.message || String(error));
    ctx.log?.(`[Workbench Error] Blender launch failed: ${error?.message || String(error)}`);
  } finally {
    openingWorkbenchFbxPath.value = "";
  }
}

function resetWorkbenchTexturePreview() {
  workbenchTexturePreviewToken += 1;
  Object.assign(workbenchTexturePreview, {
    asset: null,
    dataUrl: "",
    loading: false,
    error: "",
    width: 0,
    height: 0
  });
}

const workbenchTextureStageStyle = computed(() => {
  const width = Number(workbenchTexturePreview.width || 0);
  const height = Number(workbenchTexturePreview.height || 0);
  return width > 0 && height > 0 ? { aspectRatio: `${width} / ${height}` } : {};
});

function handleWorkbenchTexturePreviewLoad(event) {
  const image = event?.currentTarget;
  const width = Number(image?.naturalWidth || 0);
  const height = Number(image?.naturalHeight || 0);
  if (!width || !height) {
    handleWorkbenchTexturePreviewError();
    return;
  }
  workbenchTexturePreview.width = width;
  workbenchTexturePreview.height = height;
}

function createWorkbenchTexturePreview(dataUrl) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => {
      const sourceWidth = Number(image.naturalWidth || 0);
      const sourceHeight = Number(image.naturalHeight || 0);
      if (!sourceWidth || !sourceHeight) {
        reject(new Error("贴图无法读取尺寸"));
        return;
      }

      const scale = Math.min(
        1,
        WORKBENCH_TEXTURE_PREVIEW_MAX_DIMENSION / Math.max(sourceWidth, sourceHeight)
      );
      const width = Math.max(1, Math.round(sourceWidth * scale));
      const height = Math.max(1, Math.round(sourceHeight * scale));
      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;
      const context = canvas.getContext("2d");
      if (!context) {
        reject(new Error("贴图预览画布初始化失败"));
        return;
      }
      context.imageSmoothingEnabled = true;
      context.imageSmoothingQuality = "high";
      context.drawImage(image, 0, 0, width, height);

      try {
        resolve({ dataUrl: canvas.toDataURL("image/png"), width, height });
      } catch (error) {
        reject(error);
      }
    };
    image.onerror = () => reject(new Error("贴图无法解码"));
    image.src = dataUrl;
  });
}

function handleWorkbenchTexturePreviewError() {
  if (workbenchTexturePreview.asset) workbenchTexturePreview.error = "贴图无法解码";
}

async function previewWorkbenchTexture(asset) {
  const project = activeProject.value;
  const token = ++workbenchTexturePreviewToken;
  Object.assign(workbenchTexturePreview, {
    asset,
    dataUrl: "",
    loading: true,
    error: "",
    width: 0,
    height: 0
  });
  if (!project?.id || !project.path || !asset?.relativePath) {
    workbenchTexturePreview.loading = false;
    workbenchTexturePreview.error = "当前工程贴图路径无效";
    return;
  }

  try {
    const loadPreview = window.desktopApi?.loadWorkbenchAssetPreview;
    if (typeof loadPreview !== "function") throw new Error("贴图预览功能尚未加载，请重启应用后再试。");
    const result = await loadPreview({
      projectId: project.id,
      projectPath: project.path,
      relativePath: asset.relativePath
    });
    if (token !== workbenchTexturePreviewToken) return;
    if (!result?.ok || !result.dataUrl) throw new Error(result?.error || "贴图读取失败");
    const preview = await createWorkbenchTexturePreview(result.dataUrl);
    if (token !== workbenchTexturePreviewToken) return;
    Object.assign(workbenchTexturePreview, {
      dataUrl: preview.dataUrl,
      width: preview.width,
      height: preview.height,
      loading: false
    });
  } catch (error) {
    if (token === workbenchTexturePreviewToken) {
      workbenchTexturePreview.error = error?.message || String(error);
    }
  } finally {
    if (token === workbenchTexturePreviewToken) workbenchTexturePreview.loading = false;
  }
}

function openItemPrompt() {
  itemPrompt.name = "";
  itemPrompt.category = "";
  itemPrompt.error = "";
  itemPrompt.open = true;
}

async function createItem() {
  const project = activeProject.value;
  const name = itemPrompt.name.trim();
  const category = itemPrompt.category.trim();
  if (!project) {
    itemPrompt.error = "请先选择一个模组工程。";
    return;
  }
  if (!name) {
    itemPrompt.error = "请输入物品名称。";
    return;
  }
  if (!category) {
    itemPrompt.error = "请输入物品类别。";
    return;
  }

  itemPrompt.busy = true;
  itemPrompt.error = "";
  try {
    const createWorkbenchItem = window.desktopApi?.createWorkbenchItem;
    if (typeof createWorkbenchItem !== "function") {
      throw new Error("物品创建功能尚未加载，请重启应用后再试。");
    }
    const result = await createWorkbenchItem({
      projectId: project.id,
      projectPath: project.path,
      name,
      category
    });
    if (!result?.ok || !result.item) throw new Error(result?.error || "物品创建失败");
    items.value = [...items.value, result.item];
    selectedItem.value = result.item;
    itemPrompt.open = false;
  } catch (error) {
    itemPrompt.error = error?.message || String(error);
  } finally {
    itemPrompt.busy = false;
  }
}

function selectItem(item) {
  if (!item?.id) return;
  selectedItem.value = item;
}

function leaveItemWorkspace() {
  selectedItem.value = null;
}

async function selectProject(project) {
  if (!project?.id) return;
  if (project.id === activeProject.value?.id) {
    rememberProjectSelection(project.id);
    projectSearchQuery.value = "";
    collapseProjectList();
    return;
  }
  const result = await ctx.setWorkbenchActiveProject?.(project.id);
  if (!result?.ok) {
    notice.type = "error";
    notice.message = result?.error || "无法切换当前工程";
    return;
  }
  rememberProjectSelection(project.id);
  projectSearchQuery.value = "";
  collapseProjectList();
  notice.type = "success";
  notice.message = `已将「${project.name}」设为当前工作中心。`;
}

async function createProject() {
  const name = projectPrompt.name.trim();
  if (!name) {
    projectPrompt.error = "请输入模组名称，它会写入 manifest.xml 的 name 字段。";
    return;
  }

  projectPrompt.busy = true;
  projectPrompt.error = "";
  try {
    const result = await ctx.createWorkbenchProject?.(name);
    if (!result?.ok) throw new Error(result?.error || "模组工程创建失败");
    projectPrompt.open = false;
    notice.type = "success";
    notice.message = `已创建「${result.project.name}」，manifest.xml 的 name 已设置。`;
  } catch (error) {
    projectPrompt.error = error?.message || String(error);
  } finally {
    projectPrompt.busy = false;
  }
}

async function deleteProject(project) {
  if (!project?.id || deletingProjectId.value) return;
  const projectName = String(project.name || "未命名工程").trim();
  const confirmed = await askDeleteConfirmation({
    title: "确认删除模组工程？",
    message: `模组工程「${projectName}」`,
    detail: "工程目录及其中的所有文件都会被删除，且无法恢复。"
  });
  if (!confirmed) return;

  deletingProjectId.value = project.id;
  try {
    const result = await ctx.deleteWorkbenchProject?.(project);
    if (!result?.ok) throw new Error(result?.error || "工程删除失败");
    selectedItem.value = null;
    items.value = [];
    showNotice("success", result.warning || `已删除模组工程「${projectName}」。`);
  } catch (error) {
    showNotice("error", error?.message || String(error));
  } finally {
    deletingProjectId.value = "";
  }
}

async function openItemDirectory(item) {
  if (!item?.path) return;
  const result = await window.desktopApi?.openDirectory?.(item.path);
  if (result?.ok === false) {
    showNotice("error", result.error || "无法打开 CSV 所在目录");
    return;
  }
  showNotice("success", `已打开「${item.csvPath || "CSV"}」所在目录。`);
}

async function packageCurrentMod() {
  if (packagingMod.value) return;
  const project = activeProject.value;
  const gameDir = String(ctx.paths?.gameDir || "").trim();
  if (!project?.id || !project.path) {
    showNotice("error", "请先打开一个有效的模组工程。");
    return;
  }
  if (!gameDir) {
    showNotice("error", "请先在开始页面选择 HS2 游戏目录。");
    return;
  }

  const packageMod = window.desktopApi?.packageWorkbenchMod;
  if (typeof packageMod !== "function") {
    showNotice("error", "模组打包接口未加载，请重启应用后再试。");
    return;
  }

  packagingMod.value = true;
  Object.assign(packagingProgress, { stage: "", message: "正在准备打包", current: 0, total: 0, fileName: "" });
  try {
    const result = await packageMod({
      projectId: project.id,
      projectPath: project.path,
      gameDir
    });
    if (!result?.ok) throw new Error(result?.error || "模组打包失败");
    const replacement = Number(result.replacedCount || 0) > 0
      ? `已替换 ${result.replacedCount} 个旧版本`
      : "已写入游戏目录";
    const databaseUpdated = result.databaseUpdated === true;
    Object.assign(packageSuccessPrompt, {
      open: true,
      jumping: false,
      error: "",
      databaseUpdated,
      databaseError: String(result.databaseError || ""),
      projectGuid: String(project.guid || "").trim(),
      projectName: String(project.name || "未命名工程").trim(),
      fileName: String(result.fileName || "zipmod"),
      fileCount: Number(result.fileCount || 0),
      replacedCount: Number(result.replacedCount || 0)
    });
    const databaseMessage = databaseUpdated
      ? "并已单独同步到模组数据库"
      : `但数据库同步失败：${result.databaseError || "请稍后手动增量更新数据库"}`;
    showNotice(
      databaseUpdated ? "success" : "error",
      `模组已打包：${result.fileName || "zipmod"}（${result.fileCount || 0} 个文件，${replacement}），${databaseMessage}。`
    );
  } catch (error) {
    showNotice("error", error?.message || String(error));
  } finally {
    packagingMod.value = false;
    Object.assign(packagingProgress, { stage: "", message: "", current: 0, total: 0, fileName: "" });
  }
}

function closePackageSuccessPrompt() {
  if (packageSuccessPrompt.jumping) return;
  packageSuccessPrompt.open = false;
}

async function jumpToPackagedMod() {
  if (packageSuccessPrompt.jumping) return;
  packageSuccessPrompt.jumping = true;
  packageSuccessPrompt.error = "";
  try {
    const result = await ctx.openPackagedMod?.(packageSuccessPrompt.projectGuid);
    if (!result?.ok) throw new Error(result?.error || "无法定位已打包模组");
    packageSuccessPrompt.open = false;
  } catch (error) {
    packageSuccessPrompt.error = error?.message || String(error);
  } finally {
    packageSuccessPrompt.jumping = false;
  }
}

function openSims4FbxPrompt() {
  const project = activeProject.value;
  const projectId = String(project?.id || "").trim();
  if (!sims4FbxPrompt.outputDir || sims4FbxPrompt.outputDirProjectId !== projectId) {
    sims4FbxPrompt.outputDir = String(project?.path || ctx.paths?.outputDir || "").trim();
    sims4FbxPrompt.outputDirProjectId = projectId;
  }
  sims4FbxPrompt.notice = { type: "", message: "" };
  sims4FbxPrompt.open = true;
}

function openFbxTransformPrompt() {
  fbxTransformPrompt.open = true;
  fbxTransformPrompt.error = "";
  fbxTransformPrompt.result = null;
  fbxTransformPrompt.notice = !ctx.blenderExecutablePath
    ? { type: "info", message: "请先在设置页面配置 Blender，再开始处理。" }
    : { type: "", message: "" };
}

function closeFbxTransformPrompt() {
  if (fbxTransformPrompt.busy) return;
  fbxTransformPrompt.open = false;
}

function fbxTransformCompletionMessage(result) {
  const translationIssueCount = Number(result?.translationIssueCount || 0);
  const translationRepairedCount = Number(result?.translationRepairedCount || 0);
  const alignmentMessage = result?.alignmentRepairApplied
    ? `检测到 ${translationIssueCount} 个 Mesh 存在异常局部平移，已自动修复 ${translationRepairedCount} 个。`
    : result?.alignmentIssueDetected
      ? `检测到 ${translationIssueCount} 个 Mesh 存在异常局部平移，请检查输出文件。`
      : "未检测到 Mesh 与骨架的异常局部平移。";
  const outputMessage = result?.overwroteInput
    ? "旋转与缩放已应用，原文件已直接更新。"
    : "旋转与缩放已应用，原文件未被覆盖。";
  return `${alignmentMessage}${outputMessage}`;
}

const fbxTransformSourceName = computed(() => (
  String(fbxTransformPrompt.sourcePath || "").split(/[\\/]/).pop() || ""
));

async function selectFbxTransformSource() {
  const project = activeProject.value;
  if (!project?.id || !project.path) return;
  const result = await window.desktopApi?.selectWorkbenchFbxFile?.({
    projectId: project.id,
    projectPath: project.path
  });
  if (!result?.ok) {
    fbxTransformPrompt.notice = { type: "error", message: result?.error || "FBX 文件选择失败" };
    return;
  }
  if (result.canceled) return;
  fbxTransformPrompt.sourcePath = String(result.path || "");
  fbxTransformPrompt.sourceRelativePath = String(result.relativePath || "");
  fbxTransformPrompt.result = null;
  fbxTransformPrompt.error = "";
  fbxTransformPrompt.notice = { type: "success", message: "已选择当前项目目录内的 FBX。" };
}

async function transformFbx() {
  const project = activeProject.value;
  if (!project?.id || !project.path || !fbxTransformPrompt.sourcePath || fbxTransformPrompt.busy) return;
  if (!ctx.blenderExecutablePath) {
    fbxTransformPrompt.notice = { type: "info", message: "请先在设置页面配置 Blender。" };
    ctx.activeView = "settings";
    return;
  }
  fbxTransformPrompt.busy = true;
  fbxTransformPrompt.error = "";
  fbxTransformPrompt.result = null;
  fbxTransformPrompt.notice = { type: "info", message: "Blender 正在导入 FBX、应用旋转与缩放，并检测/修复 Mesh 与骨架的局部平移，请稍候。" };
  try {
    const result = await window.desktopApi?.transformWorkbenchFbx?.({
      projectId: project.id,
      projectPath: project.path,
      sourcePath: fbxTransformPrompt.sourcePath,
      blenderPath: ctx.blenderExecutablePath,
      backupOriginal: fbxTransformPrompt.backupOriginal
    });
    if (!result?.ok) throw new Error(result?.error || "FBX 变换应用失败");
    fbxTransformPrompt.result = result;
    fbxTransformPrompt.notice = {
      type: "success",
      message: fbxTransformCompletionMessage(result)
    };
    await loadWorkbenchProjectAssets();
    ctx.log?.(`[Workbench] Applied FBX rotation and scale: ${result.input} -> ${result.output}`);
  } catch (error) {
    fbxTransformPrompt.error = error?.message || String(error);
    fbxTransformPrompt.notice = { type: "error", message: fbxTransformPrompt.error };
    ctx.log?.(`[Workbench Error] FBX transform failed: ${fbxTransformPrompt.error}`);
  } finally {
    fbxTransformPrompt.busy = false;
  }
}

async function revealFbxTransformOutput() {
  if (fbxTransformPrompt.result?.output) {
    await window.desktopApi?.showItemInFolder?.(fbxTransformPrompt.result.output);
  }
}

function openFbxSkinPrompt() {
  fbxSkinPrompt.open = true;
  fbxSkinPrompt.error = "";
  fbxSkinPrompt.result = null;
  fbxSkinPrompt.notice = { type: "", message: "" };
  if (!ctx.blenderExecutablePath) {
    fbxSkinPrompt.notice = { type: "info", message: "请先在设置页面配置 Blender，再开始处理。" };
  }
}

function closeFbxSkinPrompt() {
  if (fbxSkinPrompt.busy) return;
  fbxSkinPrompt.open = false;
}

const fbxSkinSourceName = computed(() => (
  String(fbxSkinPrompt.sourcePath || "").split(/[\\/]/).pop() || ""
));

async function selectFbxSkinSource() {
  const project = activeProject.value;
  if (!project?.id || !project.path) return;
  const result = await window.desktopApi?.selectWorkbenchFbxFile?.({
    projectId: project.id,
    projectPath: project.path
  });
  if (!result?.ok) {
    fbxSkinPrompt.notice = { type: "error", message: result?.error || "FBX 文件选择失败" };
    return;
  }
  if (result.canceled) return;
  fbxSkinPrompt.sourcePath = String(result.path || "");
  fbxSkinPrompt.sourceRelativePath = String(result.relativePath || "");
  fbxSkinPrompt.result = null;
  fbxSkinPrompt.error = "";
  fbxSkinPrompt.notice = { type: "success", message: "已选择当前项目目录内的 FBX。" };
}

async function removeFbxSkin() {
  const project = activeProject.value;
  if (!project?.id || !project.path || !fbxSkinPrompt.sourcePath || fbxSkinPrompt.busy) return;
  if (!ctx.blenderExecutablePath) {
    fbxSkinPrompt.notice = { type: "info", message: "请先在设置页面配置 Blender。" };
    ctx.activeView = "settings";
    return;
  }
  fbxSkinPrompt.busy = true;
  fbxSkinPrompt.error = "";
  fbxSkinPrompt.result = null;
  fbxSkinPrompt.notice = { type: "info", message: "Blender 正在导入 FBX、移除骨骼与蒙皮并导出新文件，请稍候。" };
  try {
    const result = await window.desktopApi?.removeWorkbenchFbxSkin?.({
      projectId: project.id,
      projectPath: project.path,
      sourcePath: fbxSkinPrompt.sourcePath,
      blenderPath: ctx.blenderExecutablePath,
      backupOriginal: fbxSkinPrompt.backupOriginal
    });
    if (!result?.ok) throw new Error(result?.error || "FBX 处理失败");
    fbxSkinPrompt.result = result;
    fbxSkinPrompt.notice = {
      type: "success",
      message: result.overwroteInput
        ? "处理完成，原文件已直接更新。"
        : "处理完成，原文件未被覆盖。"
    };
    await loadWorkbenchProjectAssets();
    ctx.log?.(`[Workbench] Removed FBX skin: ${result.input} -> ${result.output}`);
  } catch (error) {
    fbxSkinPrompt.error = error?.message || String(error);
    fbxSkinPrompt.notice = { type: "error", message: fbxSkinPrompt.error };
    ctx.log?.(`[Workbench Error] FBX skin removal failed: ${fbxSkinPrompt.error}`);
  } finally {
    fbxSkinPrompt.busy = false;
  }
}

async function revealFbxSkinOutput() {
  if (fbxSkinPrompt.result?.output) await window.desktopApi?.showItemInFolder?.(fbxSkinPrompt.result.output);
}

function openHs2SkeletonPrompt() {
  hs2SkeletonPrompt.open = true;
  hs2SkeletonPrompt.error = "";
  hs2SkeletonPrompt.result = null;
  hs2SkeletonPrompt.notice = !ctx.blenderExecutablePath
    ? { type: "info", message: "请先在设置页面配置 Blender，再开始处理。" }
    : { type: "", message: "" };
}

function closeHs2SkeletonPrompt() {
  if (hs2SkeletonPrompt.busy) return;
  hs2SkeletonPrompt.open = false;
}

const hs2SkeletonSourceName = computed(() => (
  String(hs2SkeletonPrompt.sourcePath || "").split(/[\\/]/).pop() || ""
));
const hs2SkeletonReferenceName = computed(() => (
  String(hs2SkeletonPrompt.skeletonPath || "").split(/[\\/]/).pop() || ""
));

async function selectHs2SkeletonMesh() {
  const project = activeProject.value;
  if (!project?.id || !project.path) return;
  const result = await window.desktopApi?.selectWorkbenchFbxFile?.({
    projectId: project.id,
    projectPath: project.path
  });
  if (!result?.ok) {
    hs2SkeletonPrompt.notice = { type: "error", message: result?.error || "Mesh FBX 文件选择失败" };
    return;
  }
  if (result.canceled) return;
  hs2SkeletonPrompt.sourcePath = String(result.path || "");
  hs2SkeletonPrompt.sourceRelativePath = String(result.relativePath || "");
  hs2SkeletonPrompt.result = null;
  hs2SkeletonPrompt.error = "";
  hs2SkeletonPrompt.notice = { type: "success", message: "已选择当前项目目录内的 Mesh FBX。" };
}

async function selectHs2SkeletonReference() {
  const result = await window.desktopApi?.selectFbxReferenceFile?.({
    title: "选择 HS2 标准骨架 FBX",
    defaultPath: hs2SkeletonPrompt.skeletonPath
      ? String(hs2SkeletonPrompt.skeletonPath).replace(/[\\/][^\\/]*$/, "")
      : "D:\\Workspace\\HS2_workspace\\hs"
  });
  if (!result?.ok) {
    hs2SkeletonPrompt.notice = { type: "error", message: result?.error || "骨架 FBX 文件选择失败" };
    return;
  }
  if (result.canceled) return;
  hs2SkeletonPrompt.skeletonPath = String(result.path || "");
  hs2SkeletonPrompt.result = null;
  hs2SkeletonPrompt.error = "";
  hs2SkeletonPrompt.notice = { type: "success", message: "已选择 HS2 骨架来源。" };
}

async function bindHs2Skeleton() {
  const project = activeProject.value;
  if (!project?.id || !project.path || !hs2SkeletonPrompt.sourcePath || !hs2SkeletonPrompt.skeletonPath || hs2SkeletonPrompt.busy) return;
  if (!ctx.blenderExecutablePath) {
    hs2SkeletonPrompt.notice = { type: "info", message: "请先在设置页面配置 Blender。" };
    ctx.activeView = "settings";
    return;
  }
  hs2SkeletonPrompt.busy = true;
  hs2SkeletonPrompt.error = "";
  hs2SkeletonPrompt.result = null;
  hs2SkeletonPrompt.notice = { type: "info", message: "Blender 正在导入 Mesh 和 HS2 骨架，请稍候。" };
  try {
    const result = await window.desktopApi?.bindWorkbenchHs2Skeleton?.({
      projectId: project.id,
      projectPath: project.path,
      sourcePath: hs2SkeletonPrompt.sourcePath,
      skeletonPath: hs2SkeletonPrompt.skeletonPath,
      blenderPath: ctx.blenderExecutablePath,
      backupOriginal: hs2SkeletonPrompt.backupOriginal
    });
    if (!result?.ok) throw new Error(result?.error || "HS2 骨架绑定失败");
    hs2SkeletonPrompt.result = result;
    hs2SkeletonPrompt.notice = {
      type: "success",
      message: result.overwroteInput ? "骨架绑定完成，原文件已直接更新。" : "骨架绑定完成，原文件未被覆盖。"
    };
    await loadWorkbenchProjectAssets();
    ctx.log?.(`[Workbench] Bound HS2 skeleton: ${result.input} -> ${result.output}`);
  } catch (error) {
    hs2SkeletonPrompt.error = error?.message || String(error);
    hs2SkeletonPrompt.notice = { type: "error", message: hs2SkeletonPrompt.error };
    ctx.log?.(`[Workbench Error] HS2 skeleton binding failed: ${hs2SkeletonPrompt.error}`);
  } finally {
    hs2SkeletonPrompt.busy = false;
  }
}

async function revealHs2SkeletonOutput() {
  if (hs2SkeletonPrompt.result?.output) await window.desktopApi?.showItemInFolder?.(hs2SkeletonPrompt.result.output);
}

function openFbxWeightPrompt() {
  fbxWeightPrompt.open = true;
  fbxWeightPrompt.error = "";
  fbxWeightPrompt.result = null;
  fbxWeightPrompt.notice = !ctx.blenderExecutablePath
    ? { type: "info", message: "请先在设置页面配置 Blender，再开始处理。" }
    : { type: "", message: "" };
}

function closeFbxWeightPrompt() {
  if (fbxWeightPrompt.busy) return;
  fbxWeightPrompt.open = false;
}

const fbxWeightSourceName = computed(() => (
  String(fbxWeightPrompt.sourcePath || "").split(/[\\/]/).pop() || ""
));
const fbxWeightTargetName = computed(() => (
  String(fbxWeightPrompt.targetPath || "").split(/[\\/]/).pop() || ""
));

async function selectFbxWeightSource() {
  const result = await window.desktopApi?.selectFbxReferenceFile?.({
    title: "选择已有骨骼和蒙皮的 FBX",
    defaultPath: fbxWeightPrompt.sourcePath
      ? String(fbxWeightPrompt.sourcePath).replace(/[\\/][^\\/]*$/, "")
      : "D:\\Workspace\\HS2_workspace"
  });
  if (!result?.ok) {
    fbxWeightPrompt.notice = { type: "error", message: result?.error || "权重来源文件选择失败" };
    return;
  }
  if (result.canceled) return;
  fbxWeightPrompt.sourcePath = String(result.path || "");
  fbxWeightPrompt.result = null;
  fbxWeightPrompt.error = "";
  fbxWeightPrompt.notice = { type: "success", message: "已选择带骨骼和蒙皮的权重来源 FBX。" };
}

async function selectFbxWeightTarget() {
  const project = activeProject.value;
  if (!project?.id || !project.path) return;
  const result = await window.desktopApi?.selectWorkbenchFbxFile?.({
    projectId: project.id,
    projectPath: project.path
  });
  if (!result?.ok) {
    fbxWeightPrompt.notice = { type: "error", message: result?.error || "目标 FBX 文件选择失败" };
    return;
  }
  if (result.canceled) return;
  fbxWeightPrompt.targetPath = String(result.path || "");
  fbxWeightPrompt.targetRelativePath = String(result.relativePath || "");
  fbxWeightPrompt.result = null;
  fbxWeightPrompt.error = "";
  fbxWeightPrompt.notice = { type: "success", message: "已选择当前项目内的目标 FBX。" };
}

async function transferFbxWeights() {
  const project = activeProject.value;
  if (!project?.id || !project.path || !fbxWeightPrompt.sourcePath || !fbxWeightPrompt.targetPath || fbxWeightPrompt.busy) return;
  if (!ctx.blenderExecutablePath) {
    fbxWeightPrompt.notice = { type: "info", message: "请先在设置页面配置 Blender。" };
    ctx.activeView = "settings";
    return;
  }
  fbxWeightPrompt.busy = true;
  fbxWeightPrompt.error = "";
  fbxWeightPrompt.result = null;
  fbxWeightPrompt.notice = { type: "info", message: "Blender 正在按骨骼名称匹配并转移空间权重，请稍候。" };
  try {
    const result = await window.desktopApi?.transferWorkbenchFbxWeights?.({
      projectId: project.id,
      projectPath: project.path,
      sourcePath: fbxWeightPrompt.sourcePath,
      targetPath: fbxWeightPrompt.targetPath,
      blenderPath: ctx.blenderExecutablePath,
      backupOriginal: fbxWeightPrompt.backupOriginal
    });
    if (!result?.ok) throw new Error(result?.error || "FBX 权重转移失败");
    fbxWeightPrompt.result = result;
    fbxWeightPrompt.notice = {
      type: "success",
      message: result.overwroteInput ? "权重转移完成，目标文件已直接更新。" : "权重转移完成，目标原文件未被覆盖。"
    };
    await loadWorkbenchProjectAssets();
    ctx.log?.(`[Workbench] Transferred FBX weights: ${result.source} -> ${result.output}`);
  } catch (error) {
    fbxWeightPrompt.error = error?.message || String(error);
    fbxWeightPrompt.notice = { type: "error", message: fbxWeightPrompt.error };
    ctx.log?.(`[Workbench Error] FBX weight transfer failed: ${fbxWeightPrompt.error}`);
  } finally {
    fbxWeightPrompt.busy = false;
  }
}

async function revealFbxWeightOutput() {
  if (fbxWeightPrompt.result?.output) await window.desktopApi?.showItemInFolder?.(fbxWeightPrompt.result.output);
}

function openTextureProcessor() {
  if (!activeProject.value || !selectedItem.value) return;
  textureProcessorOpen.value = true;
}

async function handleTextureExported(result) {
  await loadWorkbenchProjectAssets();
  showNotice("success", `贴图已处理为 ${result.width || ""} × ${result.height || ""} PNG。`);
  ctx.log?.(`[Workbench] Exported processed texture: ${result.path || ""}`);
}

function closeSims4FbxPrompt() {
  if (sims4FbxPrompt.busy || sims4FbxPrompt.deletingResult) return;
  sims4FbxPrompt.open = false;
}

async function selectSims4Package() {
  const selected = await window.desktopApi?.selectPackageFile?.("选择 Sims 4 Package 模组包");
  if (!selected) return;
  sims4FbxPrompt.packagePath = selected;
  sims4FbxPrompt.result = null;
  sims4FbxPrompt.notice = { type: "", message: "" };
}

async function selectSims4OutputDirectory() {
  const selected = await window.desktopApi?.selectDirectory?.("选择 FBX 输出目录");
  if (!selected) return;
  sims4FbxPrompt.outputDir = selected;
  sims4FbxPrompt.outputDirProjectId = String(activeProject.value?.id || "").trim();
  sims4FbxPrompt.result = null;
  const saved = await ctx.saveDefaultOutputDirectory?.(selected);
  sims4FbxPrompt.notice = saved?.ok === false
    ? { type: "error", message: `目录可用于本次导出，但默认值保存失败：${saved.error || "未知错误"}` }
    : { type: "success", message: "输出目录已保存，下次将自动使用。" };
}

async function extractSims4Package() {
  if (!canExportSims4Fbx.value) {
    sims4FbxPrompt.notice = {
      type: "error",
      message: ctx.backendStatus === "ready"
        ? "请选择 Package 文件和输出目录。"
        : "后端尚未准备完成，请稍后再试。"
    };
    return;
  }

  sims4FbxPrompt.busy = true;
  sims4FbxPrompt.result = null;
  sims4FbxPrompt.notice = {
    type: "info",
    message: ctx.blenderExecutablePath
      ? "正在筛选 LOD0、解码贴图、固化 T-Pose 并清理反向重合面，请稍候…"
      : "正在筛选 LOD0 并解码贴图；未设置 Blender，将输出静态 FBX…"
  };
  try {
    const response = await window.desktopApi?.backendRequest?.("/tools/sims4/package-fbx", {
      method: "POST",
      body: {
        package_path: sims4FbxPrompt.packagePath,
        target_dir: sims4FbxPrompt.outputDir,
        blender_executable_path: ctx.blenderExecutablePath || ""
      }
    });
    if (!response?.ok) throw new Error(response?.error || "Package 模型提取失败");
    sims4FbxPrompt.result = response.data || {};
    sims4FbxPrompt.notice = { type: "success", message: response.message || "LOD0 FBX 模型与贴图已导出。" };
    ctx.log?.(`[Workbench] ${response.message || "Sims 4 Package FBX export completed"}`);
  } catch (error) {
    const message = error?.message || String(error);
    sims4FbxPrompt.notice = {
      type: "error",
      message: message.includes("ts4_reference_rig.fbx") || message.includes("hs2_reference_rig.fbx")
        ? "当前后端资源版本过旧，请完全退出并重新启动 Star_Manager 后再导出。"
        : message
    };
    ctx.log?.(`[Workbench Error] ${message}`);
  } finally {
    sims4FbxPrompt.busy = false;
  }
}

async function deleteSims4ResultDirectory() {
  const outputDir = String(sims4FbxPrompt.result?.output_dir || "").trim();
  if (!outputDir || sims4FbxPrompt.busy || sims4FbxPrompt.deletingResult) return;
  const folderName = outputDir.split(/[\\/]/).filter(Boolean).pop() || outputDir;
  sims4FbxPrompt.deletingResult = true;
  try {
    const result = await window.desktopApi?.deleteSims4ResultDirectory?.(outputDir);
    if (!result?.ok) throw new Error(result?.error || "删除导出结果失败");
    sims4FbxPrompt.result = null;
    sims4FbxPrompt.notice = { type: "success", message: `已删除导出结果目录「${folderName}」。` };
    ctx.log?.(`[Workbench] Deleted Sims 4 FBX export directory: ${outputDir}`);
  } catch (error) {
    sims4FbxPrompt.notice = { type: "error", message: error?.message || String(error) };
    ctx.log?.(`[Workbench Error] Failed to delete Sims 4 FBX export directory: ${error?.message || String(error)}`);
  } finally {
    sims4FbxPrompt.deletingResult = false;
  }
}

async function revealSims4Model(filePath) {
  if (filePath) await window.desktopApi?.showItemInFolder?.(filePath);
}

async function openSims4ModelInBlender(model) {
  if (!ctx.blenderExecutablePath) {
    closeSims4FbxPrompt();
    showNotice("info", "请先在设置页面选择 blender.exe。");
    ctx.activeView = "settings";
    return;
  }
  if (!model?.path || sims4FbxPrompt.openingModelPath) return;
  sims4FbxPrompt.openingModelPath = model.path;
  try {
    const response = await window.desktopApi?.openFbxInBlender?.(ctx.blenderExecutablePath, model.path);
    if (!response?.ok) throw new Error(response?.error || "Blender 启动失败");
    sims4FbxPrompt.notice = { type: "success", message: `已使用 Blender 打开 ${model.file}` };
    ctx.log?.(`[Workbench] Opened FBX in Blender: ${model.path}`);
  } catch (error) {
    sims4FbxPrompt.notice = { type: "error", message: error?.message || String(error) };
    ctx.log?.(`[Workbench Error] Blender launch failed: ${error?.message || String(error)}`);
  } finally {
    sims4FbxPrompt.openingModelPath = "";
  }
}

async function deleteItem(item) {
  const project = activeProject.value;
  if (!project?.id || !item?.id || deletingItemId.value) return;
  const itemName = String(item.csvData?.record?.Name || item.name || "未命名物品").trim();
  const confirmed = await askDeleteConfirmation({
    title: "确认删除模组物品？",
    message: `模组物品「${itemName}」`,
    detail: "只会删除 CSV 中的这条物品数据，CSV 文件和其它资源会保留。"
  });
  if (!confirmed) return;

  deletingItemId.value = item.id;
  try {
    const result = await window.desktopApi?.deleteWorkbenchItem?.({
      projectId: project.id,
      projectPath: project.path,
      csvPath: item.csvPath,
      itemId: item.id
    });
    if (!result?.ok) throw new Error(result?.error || "物品删除失败");
    if (selectedItem.value?.id === item.id) selectedItem.value = null;
    await loadItemsForActiveProject();
    showNotice("success", `已删除物品「${itemName}」。`);
  } catch (error) {
    showNotice("error", error?.message || String(error));
  } finally {
    deletingItemId.value = "";
  }
}

const resourceModeLabel = computed(() => ({
  existing: "选择或导入",
  import: "选择或导入",
  template: "物品 Unity3D 模板"
}[resourceEditor.mode] || "主资源"));

function openDatabaseTemplatePicker() {
  if (!activeProject.value || !selectedItem.value) return;
  ctx.beginWorkbenchTemplateSelection?.({
    projectId: activeProject.value.id,
    projectPath: activeProject.value.path,
    csvPath: selectedItem.value.csvPath,
    itemId: selectedItemRecord.value.ID || selectedItem.value.id,
    targetItem: selectedItem.value
  });
}

function closeResourceEditor() {
  if (resourceEditor.saving || templatePreprocess.busy) return;
  resourceEditor.open = false;
  resourceEditor.error = "";
}

function resetResourceEditor(mode) {
  resourceEditor.open = true;
  resourceEditor.mode = mode;
  resourceEditor.loading = false;
  resourceEditor.saving = false;
  resourceEditor.error = "";
  resourceEditor.files = [];
  resourceEditor.relativePath = "";
  resourceEditor.sourcePath = "";
  resourceEditor.candidates = [];
  resourceEditor.mainData = "";
  resourceEditor.mainDataPathId = 0;
  resourceEditor.mainDataAssetFile = "";
  resourceEditor.objectCount = 0;
  resourceEditor.gameObjectCount = 0;
  templatePicker.selected = null;
  templatePicker.preparedPath = "";
  templatePreprocess.busy = false;
  templatePreprocess.error = "";
  templatePreprocess.renameName = ["template", "existing", "import"].includes(mode) ? defaultTemplateRenameName() : "";
}

function syncMainDataCandidate() {
  const selected = resourceEditor.candidates.find((candidate) => candidate?.value === resourceEditor.mainData);
  resourceEditor.mainDataPathId = Number(selected?.path_id || 0);
  resourceEditor.mainDataAssetFile = String(selected?.asset_file || "");
}

function mergeMainDataCandidates(result) {
  const candidates = [
    ...(Array.isArray(result?.candidates) ? result.candidates : []),
    ...(Array.isArray(result?.game_object_candidates) ? result.game_object_candidates : [])
  ];
  const seen = new Set();
  return candidates.filter((candidate) => {
    const value = String(candidate?.value || "").trim();
    if (!value) return false;
    if (String(candidate?.kind || "") === "GameObject" && candidate?.is_animator !== true) return false;
    const identity = [
      candidate?.kind || "GameObject",
      candidate?.asset_file || "",
      candidate?.path_id ?? "",
      candidate?.component_index ?? "",
      value
    ].join("\u0000");
    if (seen.has(identity)) return false;
    seen.add(identity);
    return true;
  });
}

function resetMainResourceCheck() {
  mainResourceCheck.loading = false;
  mainResourceCheck.status = "idle";
  mainResourceCheck.message = "";
  mainResourceCheck.fields = {};
}

function mainResourceFieldStatus(field) {
  return String(mainResourceCheck.fields?.[field]?.status || "");
}

function mainResourceFieldTitle(field) {
  const status = mainResourceFieldStatus(field);
  if (field === "MainAB") {
    return status === "found" ? "Unity3D 文件已找到" : "Unity3D 文件不存在";
  }
  return status === "found" ? "已在 Unity3D 中找到" : "未在 Unity3D 中找到";
}

function syncEditableResourceValues() {
  for (const field of editableResourceFields) {
    editableResourceValues[field] = String(selectedItemRecord.value[field] || "");
  }
}

function isEditableResourceField(field) {
  return editableResourceFields.includes(field);
}

function canImportTextureField(field) {
  return textureFieldNames.includes(field)
    && mainResourceFieldStatus(field) === "missing"
    && Boolean(String(editableResourceValues[field] || selectedItemRecord.value[field] || "").trim())
    && Boolean(String(selectedItemRecord.value.MainAB || "").trim());
}

function canReplaceTextureField(field) {
  return textureFieldNames.includes(field)
    && mainResourceFieldStatus(field) === "found"
    && Boolean(String(editableResourceValues[field] || selectedItemRecord.value[field] || "").trim())
    && Boolean(String(selectedItemRecord.value.MainAB || "").trim());
}

async function checkMainResource() {
  const project = activeProject.value;
  const item = selectedItem.value;
  const record = selectedItemRecord.value;
  const mainAB = String(record.MainAB || "").trim();
  const token = ++mainResourceCheck.token;

  if (!project || !item || !mainAB) {
    resetMainResourceCheck();
    return;
  }

  mainResourceCheck.loading = true;
  mainResourceCheck.status = "checking";
  mainResourceCheck.message = "正在检查 Unity3D";
  mainResourceCheck.fields = {};

  try {
    const validate = window.desktopApi?.validateWorkbenchMainResource;
    if (typeof validate !== "function") throw new Error("资源检查接口未加载");
    const result = await validate({
      projectId: project.id,
      projectPath: project.path,
      mainAB,
      mainData: String(record.MainData || "").trim(),
      mainTex: String(record.MainTex || "").trim(),
      colorMaskTex: String(record.ColorMaskTex || "").trim(),
      textureFields: Object.fromEntries(
        textureFieldNames.map((field) => [field, String(record[field] || "").trim()])
      )
    });
    if (token !== mainResourceCheck.token) return;
    if (!result?.ok) throw new Error(result?.error || "资源检查失败");
    mainResourceCheck.loading = false;
    mainResourceCheck.status = String(result.status || "ready");
    mainResourceCheck.message = String(result.message || "Unity3D 资源已找到");
    mainResourceCheck.fields = result.checks || {};
  } catch (error) {
    if (token !== mainResourceCheck.token) return;
    mainResourceCheck.loading = false;
    mainResourceCheck.status = "unreadable";
    mainResourceCheck.message = error?.message || "Unity3D 无法读取";
    mainResourceCheck.fields = {};
  }
}

async function openMainAbInSb3Utility() {
  const project = activeProject.value;
  const mainAB = String(selectedItemRecord.value.MainAB || "").trim();
  if (!project || !mainAB || openingMainAb.value) return;

  const openResource = window.desktopApi?.openWorkbenchMainResourceInSb3Utility;
  if (typeof openResource !== "function") {
    showNotice("error", "SB3Utility 打开接口未加载，请重启应用后再试。");
    return;
  }

  openingMainAb.value = true;
  try {
    const result = await openResource({
      projectId: project.id,
      projectPath: project.path,
      mainAB
    });
    if (!result?.ok) throw new Error(result?.error || "无法使用 SB3Utility 打开 Unity3D");
  } catch (error) {
    showNotice("error", error?.message || String(error));
  } finally {
    openingMainAb.value = false;
  }
}

async function loadWorkbenchModelPreview() {
  const project = activeProject.value;
  const item = selectedItem.value;
  const record = selectedItemRecord.value;
  if (!project || !item || !canPreviewSelectedItem.value) {
    throw new Error("请先配置可用的 MainAB 和 MainData");
  }

  const preview = window.desktopApi?.previewWorkbenchItem;
  if (typeof preview !== "function") {
    throw new Error("工作台模型预览接口未加载，请重启应用后再试。");
  }
  const result = await preview({
    projectId: project.id,
    projectPath: project.path,
    mainAB: String(record.MainAB || "").trim(),
    mainData: String(record.MainData || "").trim(),
    kind: String(record.Kind || "").trim()
  });
  if (!result?.ok) throw new Error(result?.error || "3D 模型生成失败");
  return result;
}

function refreshWorkbenchPreview() {
  workbenchPreviewReady.value = false;
  workbenchPreviewRevision.value += 1;
}

async function buildWorkbenchThumbnail() {
  if (workbenchThumbnail.busy) return;
  const project = activeProject.value;
  const item = selectedItem.value;
  if (!project || !item) return;
  if (!workbenchPreviewReady.value) {
    showNotice("error", "请先等待 3D 预览加载完成，再构建缩略图。");
    return;
  }

  workbenchThumbnail.busy = true;
  workbenchThumbnail.error = "";
  try {
    const imageData = await workbenchModelPreview.value?.captureScreenshot?.();
    if (!imageData) throw new Error("无法取得 3D 预览画面");
    const saveThumbnail = window.desktopApi?.saveWorkbenchThumbnail;
    if (typeof saveThumbnail !== "function") throw new Error("工作台缩略图写入接口未加载，请重启应用后再试。");

    const result = await saveThumbnail({
      projectId: project.id,
      projectPath: project.path,
      csvPath: item.csvPath,
      itemId: selectedItemRecord.value.ID,
      imageData
    });
    if (!result?.ok || !result.item) throw new Error(result?.error || "缩略图写入失败");

    const itemIndex = items.value.findIndex((current) => current.id === result.item.id);
    if (itemIndex >= 0) {
      items.value = items.value.map((current, index) => index === itemIndex ? result.item : current);
    }
    selectedItem.value = result.item;
    workbenchThumbnail.dataUrl = String(result.dataUrl || "");
    workbenchThumbnail.sourcePath = String(result.sourcePath || "");
    workbenchThumbnail.missing = !workbenchThumbnail.dataUrl;
    showNotice("success", "缩略图已生成，并已写入当前物品 CSV。");
  } catch (error) {
    workbenchThumbnail.error = error?.message || String(error);
    showNotice("error", workbenchThumbnail.error);
  } finally {
    workbenchThumbnail.busy = false;
  }
}

async function updateResourceFields(updates, { force = false, successMessage = "" } = {}) {
  if (resourceFieldSaving.value) return false;
  const project = activeProject.value;
  const item = selectedItem.value;
  if (!project || !item) return false;

  const requestedFields = Object.fromEntries(
    Object.entries(updates || {})
      .filter(([field]) => isEditableResourceField(field))
      .map(([field, value]) => [field, String(value || "").trim()])
  );
  const previousValues = Object.fromEntries(
    Object.keys(requestedFields).map((field) => [field, String(selectedItemRecord.value[field] || "").trim()])
  );
  const fieldsToUpdate = Object.keys(requestedFields).filter((field) => (
    force || requestedFields[field] !== previousValues[field]
  ));
  if (!fieldsToUpdate.length) return true;

  const updateFields = window.desktopApi?.updateWorkbenchItemResourceFields;
  if (typeof updateFields !== "function") {
    for (const field of fieldsToUpdate) editableResourceValues[field] = previousValues[field];
    showNotice("error", "资源字段编辑接口未加载，请重启应用后再试。");
    return false;
  }

  resourceFieldSaving.value = fieldsToUpdate.join(",");
  try {
    const result = await updateFields({
      projectId: project.id,
      projectPath: project.path,
      csvPath: item.csvPath,
      itemId: selectedItemRecord.value.ID,
      fields: Object.fromEntries(fieldsToUpdate.map((field) => [field, requestedFields[field]]))
    });
    if (!result?.ok || !result.item) throw new Error(result?.error || "资源字段保存失败");
    const itemIndex = items.value.findIndex((current) => current.id === result.item.id);
    if (itemIndex >= 0) {
      items.value = items.value.map((current, index) => index === itemIndex ? result.item : current);
    }
    selectedItem.value = result.item;
    for (const field of fieldsToUpdate) {
      editableResourceValues[field] = String(result.item.csvData?.record?.[field] || "");
    }
    if (successMessage) showNotice("success", successMessage);
    return true;
  } catch (error) {
    for (const field of fieldsToUpdate) editableResourceValues[field] = previousValues[field];
    showNotice("error", error?.message || String(error));
    return false;
  } finally {
    resourceFieldSaving.value = "";
  }
}

async function saveEditableResourceField(field) {
  if (!isEditableResourceField(field)) return;
  const nextValue = String(editableResourceValues[field] || "").trim();
  if (field === "Name" && !nextValue) {
    editableResourceValues[field] = String(selectedItemRecord.value[field] || "");
    showNotice("error", "物品名称不能为空");
    return;
  }
  await updateResourceFields({ [field]: nextValue });
}

function cancelEditableResourceField(field) {
  if (!isEditableResourceField(field)) return;
  editableResourceValues[field] = String(selectedItemRecord.value[field] || "");
}

async function addTextureGroup() {
  if (textureGroupCount.value >= MAX_TEXTURE_GROUPS || resourceFieldSaving.value) return;
  const group = textureGroupDefinitions[textureGroupCount.value];
  const updates = Object.fromEntries(
    group.fields.map((field) => [field, textureGroupDefaultValue(field, group.index)])
  );
  const saved = await updateResourceFields(updates, {
    force: true,
    successMessage: `已新增第 ${group.index} 组贴图字段。`
  });
  if (saved) textureGroupCount.value = Math.min(MAX_TEXTURE_GROUPS, textureGroupCount.value + 1);
}

async function deleteTextureGroup(groupIndex) {
  if (textureGroupCount.value <= 1 || resourceFieldSaving.value) return;
  const index = Number(groupIndex);
  if (!Number.isInteger(index) || index < 0 || index >= textureGroupCount.value) return;

  const record = selectedItemRecord.value;
  const updates = {};
  for (let position = index; position < textureGroupCount.value; position += 1) {
    const targetGroup = textureGroupDefinitions[position];
    const sourceGroup = textureGroupDefinitions[position + 1];
    for (const [fieldIndex, targetField] of targetGroup.fields.entries()) {
      const sourceField = sourceGroup?.fields[fieldIndex];
      updates[targetField] = sourceField ? String(record[sourceField] || "").trim() : "";
    }
  }
  const saved = await updateResourceFields(updates, {
    force: true,
    successMessage: `已删除第 ${textureGroupDefinitions[index].index} 组贴图。`
  });
  if (saved) textureGroupCount.value = Math.max(1, textureGroupCount.value - 1);
}

async function writeTextureField(field, replaceExisting = false) {
  const canWrite = replaceExisting ? canReplaceTextureField(field) : canImportTextureField(field);
  if (!canWrite || textureImporting.value) return;
  const project = activeProject.value;
  const mainAB = String(selectedItemRecord.value.MainAB || "").trim();
  const textureName = String(editableResourceValues[field] || selectedItemRecord.value[field] || "").trim();
  const sourcePath = await window.desktopApi?.selectImageFile?.(
    replaceExisting ? `选择用于替换 ${textureName} 的贴图` : "选择外部贴图",
    replaceExisting ? project?.path : undefined
  );
  if (!sourcePath || !project || !mainAB || !textureName) return;

  const importTexture = window.desktopApi?.importWorkbenchTexture;
  if (typeof importTexture !== "function") {
    showNotice("error", "贴图导入接口未加载，请重启应用后再试。");
    return;
  }

  textureImporting.value = field;
  try {
    const result = await importTexture({
      projectId: project.id,
      projectPath: project.path,
      mainAB,
      mainData: String(selectedItemRecord.value.MainData || "").trim(),
      sourcePath,
      textureName,
      replaceExisting
    });
    if (!result?.ok) throw new Error(result?.error || (replaceExisting ? "贴图替换失败" : "贴图导入失败"));
    await checkMainResource();
    refreshWorkbenchPreview();
    showNotice("success", replaceExisting ? `已替换贴图 ${textureName}` : `已导入并改名为 ${textureName}`);
  } catch (error) {
    showNotice("error", error?.message || String(error));
  } finally {
    textureImporting.value = "";
  }
}

async function importTextureField(field) {
  await writeTextureField(field, false);
}

async function replaceTextureField(field) {
  await writeTextureField(field, true);
}

async function loadMainDataCandidates(filePath, preferred = "", preferredPathId = 0, preferredAssetFile = "") {
  const request = window.desktopApi?.backendRequest;
  if (typeof request !== "function") throw new Error("资源读取接口尚未加载，请重启应用后再试。");
  const result = await request("/workbench/unity3d/assets", {
    method: "POST",
    body: { path: filePath }
  });
  if (!result?.ok) throw new Error(result?.error || "无法读取 Unity3D 内部模型对象");
  resourceEditor.candidates = mergeMainDataCandidates(result);
  resourceEditor.objectCount = Number(result.object_count || 0);
  resourceEditor.gameObjectCount = Number(result.game_object_count || 0);
  const preferredCandidate = resourceEditor.candidates.find((candidate) => candidate.value === preferred)
    || resourceEditor.candidates.find((candidate) => (
      Number(candidate?.path_id || 0) === Number(preferredPathId || 0)
      && String(candidate?.asset_file || "") === String(preferredAssetFile || "")
    ));
  resourceEditor.mainData = preferredCandidate?.value || result.default || resourceEditor.candidates[0]?.value || preferred || "";
  resourceEditor.mainDataPathId = Number(preferredCandidate?.path_id || 0);
  resourceEditor.mainDataAssetFile = String(preferredCandidate?.asset_file || "");
}

async function loadExistingUnity3dFiles() {
  const project = activeProject.value;
  if (!project) return;
  const scan = window.desktopApi?.scanWorkbenchUnity3d;
  if (typeof scan !== "function") throw new Error("Unity3D 扫描接口尚未加载，请重启应用后再试。");
  const result = await scan({ projectId: project.id, projectPath: project.path });
  if (!result?.ok) throw new Error(result?.error || "无法扫描当前工程的 Unity3D 文件");
  resourceEditor.files = Array.isArray(result.files) ? result.files : [];
}

async function loadWorkbenchUnity3dFiles() {
  const project = activeProject.value;
  const token = ++projectUnity3dLoadToken;
  projectUnity3dLibrary.loading = false;
  projectUnity3dLibrary.error = "";
  projectUnity3dLibrary.files = [];
  if (!project?.id || !project.path) return;

  const scan = window.desktopApi?.scanWorkbenchUnity3d;
  if (typeof scan !== "function") {
    projectUnity3dLibrary.error = "Unity3D 扫描功能尚未加载，请重启应用后再试。";
    return;
  }

  projectUnity3dLibrary.loading = true;
  try {
    const result = await scan({ projectId: project.id, projectPath: project.path });
    if (token !== projectUnity3dLoadToken) return;
    if (!result?.ok) throw new Error(result?.error || "无法扫描当前工程的 Unity3D 文件");
    projectUnity3dLibrary.files = Array.isArray(result.files) ? result.files : [];
  } catch (error) {
    if (token === projectUnity3dLoadToken) {
      projectUnity3dLibrary.error = error?.message || String(error);
    }
  } finally {
    if (token === projectUnity3dLoadToken) projectUnity3dLibrary.loading = false;
  }
}

async function selectInlineExistingUnity3d(event) {
  const relativePath = String(event?.target?.value || "").trim();
  if (!relativePath || !activeProject.value || !selectedItem.value) return;

  resetResourceEditor("existing");
  resourceEditor.files = [...projectUnity3dLibrary.files];
  resourceEditor.relativePath = relativePath;
  await selectExistingUnity3d();
}

function templateItemThumbnailUrl(templateItem) {
  const rawPath = String(templateItem?.thumbnail_url || "").trim();
  if (!rawPath) return "";
  if (/^(?:https?:\/|data:|blob:)/i.test(rawPath)) return rawPath;
  const baseUrl = String(window.desktopApi?.backendBaseUrl || "").replace(/\/+$/g, "");
  return baseUrl ? `${baseUrl}${rawPath.startsWith("/") ? rawPath : `/${rawPath}`}` : rawPath;
}

function hideTemplateItemThumbnail(event) {
  if (event?.currentTarget) event.currentTarget.hidden = true;
}

async function selectExistingUnity3d() {
  const file = resourceEditor.files.find((item) => item.relativePath === resourceEditor.relativePath);
  if (!file) {
    resourceEditor.candidates = [];
    resourceEditor.mainData = "";
    return;
  }
  resourceEditor.loading = true;
  resourceEditor.error = "";
  try {
    await loadMainDataCandidates(file.path);
  } catch (error) {
    resourceEditor.error = error?.message || String(error);
  } finally {
    resourceEditor.loading = false;
  }
}

async function chooseImportedUnity3d() {
  const sourcePath = await window.desktopApi?.selectUnity3dFile?.("选择要导入的 Unity3D 文件");
  if (!sourcePath) return false;
  resourceEditor.sourcePath = sourcePath;
  resourceEditor.loading = true;
  resourceEditor.error = "";
  try {
    await loadMainDataCandidates(sourcePath);
    return true;
  } catch (error) {
    resourceEditor.error = error?.message || String(error);
    return false;
  } finally {
    resourceEditor.loading = false;
  }
}

async function switchResourceSource(mode) {
  if (!['existing', 'import'].includes(mode) || resourceEditor.mode === mode || resourceEditor.saving) return;
  resourceEditor.mode = mode;
  resourceEditor.loading = false;
  resourceEditor.error = "";
  resourceEditor.relativePath = "";
  resourceEditor.sourcePath = "";
  resourceEditor.candidates = [];
  resourceEditor.mainData = "";
  resourceEditor.mainDataPathId = 0;
  resourceEditor.mainDataAssetFile = "";
  resourceEditor.objectCount = 0;
  resourceEditor.gameObjectCount = 0;
  templatePreprocess.renameName = ["existing", "import"].includes(mode) ? defaultTemplateRenameName() : "";
  if (mode === "import") await chooseImportedUnity3d();
}

async function openMainResourceEditor(mode) {
  if (!activeProject.value || !selectedItem.value) return;
  resetResourceEditor(mode);
  resourceEditor.loading = true;
  try {
    if (mode === "existing") {
      await loadExistingUnity3dFiles();
      const currentPath = String(selectedItemRecord.value.MainAB || "").trim();
      if (resourceEditor.files.some((file) => file.relativePath === currentPath)) {
        resourceEditor.relativePath = currentPath;
        await selectExistingUnity3d();
      }
    }
  } catch (error) {
    resourceEditor.error = error?.message || String(error);
  } finally {
    resourceEditor.loading = false;
  }
  if (mode === "import" && !resourceEditor.sourcePath) {
    await chooseImportedUnity3d();
  }
}

function selectedTemplateMainDataCandidate() {
  return resourceEditor.candidates.find((candidate) => candidate?.value === resourceEditor.mainData);
}

async function preprocessResource(operation) {
  if (!["template", "existing", "import"].includes(resourceEditor.mode) || templatePreprocess.busy || resourceEditor.saving) return;
  const selectedName = String(resourceEditor.mainData || "").trim();
  const candidate = selectedTemplateMainDataCandidate();
  const isTemplate = resourceEditor.mode === "template";
  const isImport = resourceEditor.mode === "import";
  const existingFile = resourceEditor.files.find((file) => file.relativePath === resourceEditor.relativePath);
  const sourcePath = isTemplate
    ? templatePicker.preparedPath
    : isImport
      ? resourceEditor.sourcePath
      : existingFile?.path;
  if (!selectedName || !sourcePath) {
    templatePreprocess.error = "请先选择一个有效的 MainData 模型对象。";
    return;
  }
  const nextName = String(templatePreprocess.renameName || "").trim();
  if (["duplicate_and_rename_selected", "rename_selected"].includes(operation) && !nextName) {
    templatePreprocess.error = "请输入新的对象名称。";
    return;
  }
  const preprocess = window.desktopApi?.preprocessWorkbenchTemplate;
  if (typeof preprocess !== "function") {
    templatePreprocess.error = "资源处理接口尚未加载，请重启应用后再试。";
    return;
  }

  templatePreprocess.busy = true;
  templatePreprocess.error = "";
  try {
    const result = await preprocess({
      sourcePath,
      operation,
      selectedName,
      newName: ["duplicate_and_rename_selected", "rename_selected"].includes(operation) ? nextName : "",
      selectedPathId: Number(candidate?.path_id || 0),
      selectedAssetFile: String(candidate?.asset_file || ""),
      componentIndex: Number(candidate?.component_index ?? -1),
      writeBack: !isTemplate && !isImport,
      projectId: isTemplate || isImport ? "" : activeProject.value?.id,
      projectPath: isTemplate || isImport ? "" : activeProject.value?.path,
      mainAB: isTemplate || isImport ? "" : resourceEditor.relativePath
    });
    if (!result?.ok) throw new Error(result?.error || "Unity3D 预处理失败");
    if (isTemplate) templatePicker.preparedPath = String(result.path || templatePicker.preparedPath);
    if (isImport) resourceEditor.sourcePath = String(result.path || resourceEditor.sourcePath);
    resourceEditor.candidates = mergeMainDataCandidates(result);
    resourceEditor.objectCount = Number(result.object_count || 0);
    resourceEditor.gameObjectCount = Number(result.game_object_count || 0);
    resourceEditor.mainData = String(result.main_data || result.default || resourceEditor.candidates[0]?.value || "");
    resourceEditor.mainDataPathId = Number(result.selected_path_id || candidate?.path_id || 0);
    resourceEditor.mainDataAssetFile = String(result.selected_asset_file || candidate?.asset_file || "");
    syncMainDataCandidate();
    templatePreprocess.renameName = defaultTemplateRenameName();
    const actionLabel = {
      keep_selected: "已清除其他对象",
      duplicate_selected: "已复制当前对象",
      duplicate_and_rename_selected: "已复制所选对象并重命名",
      rename_selected: "已重命名当前对象"
    }[operation] || "已完成资源处理";
    showNotice("success", `${actionLabel}：${resourceEditor.mainData}`);
  } catch (error) {
    templatePreprocess.error = error?.message || String(error);
  } finally {
    templatePreprocess.busy = false;
  }
}

async function saveMainResource() {
  const project = activeProject.value;
  const item = selectedItem.value;
  const databaseTemplate = resourceEditor.mode === "template";
  const mainData = String(resourceEditor.mainData || "").trim();
  if (!project || !item) return;
  if (!mainData) {
    resourceEditor.error = databaseTemplate
      ? "请选择数据库物品中的 MainData 模型对象。"
      : "请选择或填写 MainData 模型对象名。";
    return;
  }
  if (databaseTemplate && (!templatePicker.selected || !templatePicker.preparedPath)) {
    resourceEditor.error = "请选择一个可用的 Unity3D 模板。";
    return;
  }
  if (resourceEditor.mode === "existing" && !resourceEditor.relativePath) {
    resourceEditor.error = "请选择一个当前工程内的 Unity3D 文件。";
    return;
  }
  if (resourceEditor.mode === "import" && !resourceEditor.sourcePath) {
    resourceEditor.error = "请选择要导入的 Unity3D 文件。";
    return;
  }

  resourceEditor.saving = true;
  resourceEditor.error = "";
  try {
    const applyResource = window.desktopApi?.applyWorkbenchMainResource;
    if (typeof applyResource !== "function") throw new Error("主资源写入接口尚未加载，请重启应用后再试。");
    const result = await applyResource({
      projectId: project.id,
      projectPath: project.path,
      csvPath: item.csvPath,
      itemId: selectedItemRecord.value.ID,
      mode: databaseTemplate ? "database" : resourceEditor.mode,
      relativePath: resourceEditor.relativePath,
      sourcePath: databaseTemplate ? templatePicker.preparedPath : resourceEditor.sourcePath,
      sourceItemId: databaseTemplate ? templatePicker.selected?.id : "",
      mainData
    });
    if (!result?.ok || !result.item) throw new Error(result?.error || "主资源写入失败");
    const itemIndex = items.value.findIndex((current) => current.id === result.item.id);
    if (itemIndex >= 0) {
      items.value = items.value.map((current, index) => index === itemIndex ? result.item : current);
    }
    selectedItem.value = result.item;
    resourceEditor.open = false;
    await loadWorkbenchUnity3dFiles();
    showNotice("success", `已通过「${resourceModeLabel.value}」补足主资源：${result.resource.relativePath}`);
  } catch (error) {
    resourceEditor.error = error?.message || String(error);
  } finally {
    resourceEditor.saving = false;
  }
}

</script>

<template>
  <section class="view workbench-view">
    <div class="workbench-scroll">
      <div v-if="setupMode" class="workbench-onboarding">
        <div class="onboarding-grid">
          <section class="setup-card setup-form-card">
            <div class="section-kicker">01 / CREATOR PROFILE</div>
            <h2>先登记你的制作信息</h2>
            <p class="section-intro">这些信息会作为模组工程的默认上下文保存到本机，不会写入 HS2 游戏目录。</p>

            <form class="profile-form" @submit.prevent="saveProfile">
              <label class="field-label" for="workbench-author-id">
                <span>模组作者 ID <em>必填</em></span>
                <input
                  id="workbench-author-id"
                  v-model="profileForm.authorId"
                  type="text"
                  maxlength="80"
                  autocomplete="off"
                  placeholder="例如：yukilat"
                >
              </label>

              <label class="field-label" for="workbench-workspace-path">
                <span>工具台工作空间 <em>必填</em></span>
                <div class="path-picker">
                  <input
                    id="workbench-workspace-path"
                    v-model="profileForm.workspacePath"
                    type="text"
                    readonly
                    placeholder="请选择一个专门存放模组工程的文件夹"
                  >
                  <button type="button" @click="selectWorkspace">选择文件夹</button>
                </div>
              </label>

              <div v-if="setupError" class="setup-error" role="alert">
                <span>!</span>{{ setupError }}
              </div>

              <div class="form-footer">
                <button class="primary setup-submit" type="submit" :disabled="savingProfile">
                  <span v-if="savingProfile" class="button-spinner" aria-hidden="true"></span>
                  {{ savingProfile ? "正在保存…" : "保存并进入工具台" }}
                </button>
              </div>
            </form>
          </section>
        </div>
      </div>

      <div v-else class="workbench-home">
      <div v-if="notice.message && notice.type !== 'success'" class="workbench-notice" :class="notice.type" role="status">
          <span>{{ notice.type === "success" ? "✓" : "!" }}</span>
          <p>{{ notice.message }}</p>
        </div>

        <section v-if="!hasProjects" class="first-project-banner">
          <div>
            <span class="section-kicker">FIRST BUILD</span>
            <h2>创建你的第一个模组</h2>
          </div>
          <button class="primary" type="button" @click="openProjectPrompt">创建</button>
        </section>

        <div v-if="projectPrompt.open" class="project-prompt-backdrop" role="presentation" @click.self="projectPrompt.open = false">
          <section class="project-prompt" role="dialog" aria-modal="true" aria-labelledby="project-prompt-title">
            <div class="prompt-decoration" aria-hidden="true"><span></span><span></span><span></span></div>
            <span class="section-kicker">NEW MOD PROJECT / 01</span>
            <h2 id="project-prompt-title">创建模组</h2>
            <label class="field-label" for="workbench-project-name">
              <span>模组名称</span>
              <input id="workbench-project-name" v-model="projectPrompt.name" type="text" maxlength="120" autocomplete="off" placeholder="例如：Soft Ribbon Set">
            </label>
            <div v-if="projectPrompt.error" class="setup-error" role="alert"><span>!</span>{{ projectPrompt.error }}</div>
            <div class="prompt-actions">
              <button type="button" :disabled="projectPrompt.busy" @click="projectPrompt.open = false">稍后再说</button>
              <button class="primary" type="button" :disabled="projectPrompt.busy" @click="createProject">
                <span v-if="projectPrompt.busy" class="button-spinner" aria-hidden="true"></span>
                {{ projectPrompt.busy ? "正在创建…" : "创建" }}
              </button>
            </div>
          </section>
        </div>

        <div v-if="packageSuccessPrompt.open" class="project-prompt-backdrop package-success-backdrop" role="presentation" @click.self="closePackageSuccessPrompt">
          <section
            class="project-prompt package-success-prompt"
            role="dialog"
            aria-modal="true"
            aria-labelledby="package-success-title"
            @keydown.esc.prevent="closePackageSuccessPrompt"
          >
            <div class="prompt-decoration" aria-hidden="true"><span></span><span></span><span></span></div>
            <span class="section-kicker">PACKAGE COMPLETE / {{ packageSuccessPrompt.projectName }}</span>
            <h2 id="package-success-title">模组打包成功</h2>
            <div class="package-success-detail">
              <strong>{{ packageSuccessPrompt.fileName }}</strong>
              <span>{{ packageSuccessPrompt.fileCount }} 个文件 · {{ packageSuccessPrompt.replacedCount ? `已替换 ${packageSuccessPrompt.replacedCount} 个旧版本` : "首次写入" }}</span>
            </div>
            <div v-if="packageSuccessPrompt.error" class="setup-error package-success-error" role="alert"><span>!</span>{{ packageSuccessPrompt.error }}</div>
            <div class="prompt-actions">
              <button type="button" :disabled="packageSuccessPrompt.jumping" @click="closePackageSuccessPrompt">取消</button>
              <button class="primary" type="button" :disabled="packageSuccessPrompt.jumping" @click="jumpToPackagedMod">
                <span v-if="packageSuccessPrompt.jumping" class="button-spinner" aria-hidden="true"></span>
                {{ packageSuccessPrompt.jumping ? "正在跳转…" : "跳转" }}
              </button>
            </div>
          </section>
        </div>

        <div v-if="sims4FbxPrompt.open" class="project-prompt-backdrop sims4-fbx-backdrop" role="presentation" @click.self="closeSims4FbxPrompt">
          <section
            class="project-prompt sims4-fbx-prompt"
            role="dialog"
            aria-modal="true"
            aria-labelledby="sims4-fbx-prompt-title"
            @keydown.esc.prevent="closeSims4FbxPrompt"
          >
            <div class="prompt-decoration" aria-hidden="true"><span></span><span></span><span></span></div>
            <div class="sims4-fbx-modal-head">
              <div>
                <span class="section-kicker">SIMS 4 / PACKAGE → FBX</span>
                <h2 id="sims4-fbx-prompt-title">Package 转 FBX</h2>
              </div>
              <button class="sims4-fbx-close" type="button" :disabled="sims4FbxPrompt.busy || sims4FbxPrompt.deletingResult" aria-label="关闭" @click="closeSims4FbxPrompt">×</button>
            </div>
            <div class="sims4-fbx-fields">
              <label class="field-label sims4-fbx-field" for="sims4-package-path">
                <span>源文件 <em>必选</em></span>
                <div class="sims4-fbx-path-row">
                  <input id="sims4-package-path" :value="sims4FbxPackageName" type="text" readonly :title="sims4FbxPrompt.packagePath">
                  <button type="button" :disabled="sims4FbxPrompt.busy || sims4FbxPrompt.deletingResult" @click="selectSims4Package">{{ sims4FbxPrompt.packagePath ? "更换" : "选择 Package" }}</button>
                </div>
              </label>
              <label class="field-label sims4-fbx-field" for="sims4-fbx-output-dir">
                <span>输出目录 <em>必选</em></span>
                <div class="sims4-fbx-path-row">
                  <input id="sims4-fbx-output-dir" :value="sims4FbxPrompt.outputDir || '尚未选择目录'" type="text" readonly :title="sims4FbxPrompt.outputDir">
                  <button type="button" :disabled="sims4FbxPrompt.busy || sims4FbxPrompt.deletingResult" @click="selectSims4OutputDirectory">{{ sims4FbxPrompt.outputDir ? "更换" : "选择目录" }}</button>
                </div>
              </label>
            </div>

            <div v-if="sims4FbxPrompt.notice.message" class="workbench-notice sims4-fbx-notice" :class="sims4FbxPrompt.notice.type" role="status">
              <span>{{ sims4FbxPrompt.notice.type === "success" ? "✓" : sims4FbxPrompt.notice.type === "error" ? "!" : "…" }}</span>
              <p>{{ sims4FbxPrompt.notice.message }}</p>
            </div>

            <section v-if="sims4FbxPrompt.result" class="sims4-fbx-result">
              <div class="sims4-fbx-result-head">
                <div>
                  <span>EXPORT RECEIPT</span>
                  <h3>本次导出结果</h3>
                </div>
                <button
                  class="sims4-fbx-delete-result"
                  type="button"
                  :disabled="sims4FbxPrompt.busy || sims4FbxPrompt.deletingResult"
                  title="删除当前导出结果目录"
                  aria-label="删除当前导出结果目录"
                  @click="deleteSims4ResultDirectory"
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                    <path d="M4 7h16M9 7V4h6v3m-8 0 1 13h8l1-13M10 11v6m4-6v6" />
                  </svg>
                </button>
              </div>
              <div class="sims4-fbx-result-summary">
                <div><span>FBX 模型</span><strong>{{ sims4FbxPrompt.result.exported_model_count }}</strong></div>
                <div><span>T-Pose 网格</span><strong>{{ sims4FbxPrompt.result.t_pose_model_count || 0 }}</strong></div>
                <div><span>PNG 贴图</span><strong>{{ sims4FbxPrompt.result.texture_count }}</strong></div>
                <div><span>GEOM 资源</span><strong>{{ sims4FbxPrompt.result.geom_resource_count }}</strong></div>
                <div><span>跳过低模</span><strong>{{ sims4FbxPrompt.result.skipped_non_lod0_count }}</strong></div>
                <div><span>反向重合面</span><strong>{{ sims4FbxPrompt.result.reverse_duplicate_groups_detected || 0 }}</strong></div>
                <div><span>已安全清理</span><strong>{{ sims4FbxPrompt.result.reverse_duplicate_faces_removed || 0 }}</strong></div>
                <div><span>歧义跳过</span><strong>{{ sims4FbxPrompt.result.reverse_duplicate_ambiguous_groups || 0 }}</strong></div>
              </div>
              <code class="sims4-fbx-result-path" :title="sims4FbxPrompt.result.output_dir">{{ sims4FbxPrompt.result.output_dir }}</code>
              <div class="sims4-fbx-result-list">
                <div v-for="model in sims4FbxPrompt.result.exports || []" :key="model.path" class="sims4-fbx-result-row">
                  <span class="sims4-fbx-file-mark">FBX</span>
                  <span class="sims4-fbx-file-copy">
                    <strong>{{ model.file }}</strong>
                  </span>
                  <span class="sims4-fbx-result-actions">
                    <button type="button" :disabled="Boolean(sims4FbxPrompt.openingModelPath)" @click="openSims4ModelInBlender(model)">
                      {{ sims4FbxPrompt.openingModelPath === model.path ? "正在启动…" : ctx.blenderExecutablePath ? "Blender 打开" : "设置 Blender" }}
                    </button>
                    <button type="button" @click="revealSims4Model(model.path)">定位 ↗</button>
                  </span>
                </div>
              </div>
            </section>

            <div class="prompt-actions sims4-fbx-actions">
              <button type="button" :disabled="sims4FbxPrompt.busy || sims4FbxPrompt.deletingResult" @click="closeSims4FbxPrompt">关闭</button>
              <button class="primary" type="button" :disabled="!canExportSims4Fbx" @click="extractSims4Package">
                <span v-if="sims4FbxPrompt.busy" class="button-spinner" aria-hidden="true"></span>
                {{ sims4FbxPrompt.busy ? "正在加工…" : ctx.blenderExecutablePath ? "提取 T-Pose FBX" : "提取 LOD0 + 贴图" }}
              </button>
            </div>
          </section>
        </div>

        <div v-if="fbxTransformPrompt.open" class="project-prompt-backdrop fbx-transform-backdrop" role="presentation" @click.self="closeFbxTransformPrompt">
          <section
            class="project-prompt fbx-skin-prompt fbx-transform-prompt"
            role="dialog"
            aria-modal="true"
            aria-labelledby="fbx-transform-prompt-title"
            @keydown.esc.prevent="closeFbxTransformPrompt"
          >
            <div class="prompt-decoration" aria-hidden="true"><span></span><span></span><span></span></div>
            <div class="fbx-skin-modal-head">
              <div>
                <span class="section-kicker">ITEM TOOL / FBX</span>
                <h2 id="fbx-transform-prompt-title">应用旋转与缩放</h2>
              </div>
              <button class="sims4-fbx-close" type="button" :disabled="fbxTransformPrompt.busy" aria-label="关闭" @click="closeFbxTransformPrompt">×</button>
            </div>
            <p class="fbx-skin-description fbx-transform-description">工具会同时检查 Mesh 的异常局部平移；发现模型与骨架错开的平移问题时，会将平移烘焙到网格并自动把 Mesh 变换归零。</p>
            <div class="fbx-skin-source-row fbx-transform-source-row">
              <div>
                <span class="field-label-text">源 FBX（当前项目目录）</span>
                <strong v-if="fbxTransformPrompt.sourcePath" :title="fbxTransformPrompt.sourcePath">{{ fbxTransformSourceName }}</strong>
                <code>{{ fbxTransformPrompt.sourceRelativePath || "尚未选择文件" }}</code>
              </div>
              <button type="button" :disabled="fbxTransformPrompt.busy" @click="selectFbxTransformSource">{{ fbxTransformPrompt.sourcePath ? "更换文件" : "选择 FBX" }}</button>
            </div>
            <label class="fbx-skin-backup-toggle">
              <input v-model="fbxTransformPrompt.backupOriginal" type="checkbox" :disabled="fbxTransformPrompt.busy">
              <span>
                <strong>处理前备份原文件</strong>
                <small>开启后输出为新的 <code>_transformed.fbx</code> 文件。</small>
              </span>
            </label>
            <div v-if="fbxTransformPrompt.notice.message" class="workbench-notice fbx-skin-notice" :class="fbxTransformPrompt.notice.type" role="status">
              <span>{{ fbxTransformPrompt.notice.type === "success" ? "✓" : fbxTransformPrompt.notice.type === "error" ? "!" : "i" }}</span>
              <p>{{ fbxTransformPrompt.notice.message }}</p>
            </div>
            <section v-if="fbxTransformPrompt.result" class="fbx-skin-result">
              <div class="fbx-skin-result-head">
                <div><span>OUTPUT / TRANSFORMS + ALIGNMENT</span><h3>处理完成</h3></div>
                <button type="button" @click="revealFbxTransformOutput">定位输出</button>
              </div>
              <code :title="fbxTransformPrompt.result.output">{{ fbxTransformPrompt.result.outputRelativePath }}{{ fbxTransformPrompt.result.overwroteInput ? "（已覆盖原文件）" : "" }}</code>
              <small v-if="fbxTransformPrompt.result.backupRelativePath" class="fbx-skin-backup-path">备份：{{ fbxTransformPrompt.result.backupRelativePath }}</small>
              <div
                class="fbx-transform-alignment-status"
                :class="fbxTransformPrompt.result.alignmentRepairApplied ? 'repaired' : fbxTransformPrompt.result.alignmentIssueDetected ? 'warning' : 'clean'"
              >
                <strong>{{ fbxTransformPrompt.result.alignmentRepairApplied ? "已自动修复 Mesh 局部平移" : fbxTransformPrompt.result.alignmentIssueDetected ? "检测到局部平移，请检查输出" : "未检测到 Mesh 局部平移异常" }}</strong>
                <span v-if="fbxTransformPrompt.result.translationRepairedMeshNames?.length">修复对象：{{ fbxTransformPrompt.result.translationRepairedMeshNames.join("、") }}</span>
              </div>
              <div class="fbx-skin-result-summary fbx-transform-result-summary">
                <div><span>非单位变换</span><strong>{{ fbxTransformPrompt.result.changedObjectCount }}</strong></div>
                <div><span>平移异常</span><strong>{{ fbxTransformPrompt.result.translationIssueCount }}</strong></div>
                <div><span>自动修复</span><strong>{{ fbxTransformPrompt.result.translationRepairedCount }}</strong></div>
                <div><span>Mesh</span><strong>{{ fbxTransformPrompt.result.meshCount }}</strong></div>
                <div><span>Armature</span><strong>{{ fbxTransformPrompt.result.armatureCount }}</strong></div>
              </div>
            </section>
            <div v-if="fbxTransformPrompt.error" class="setup-error" role="alert"><span>!</span>{{ fbxTransformPrompt.error }}</div>
            <div class="prompt-actions fbx-skin-actions">
              <button type="button" :disabled="fbxTransformPrompt.busy" @click="closeFbxTransformPrompt">关闭</button>
              <button class="primary" type="button" :disabled="fbxTransformPrompt.busy || !fbxTransformPrompt.sourcePath || !ctx.blenderExecutablePath" @click="transformFbx">
                <span v-if="fbxTransformPrompt.busy" class="button-spinner" aria-hidden="true"></span>
                {{ fbxTransformPrompt.busy ? "正在处理…" : ctx.blenderExecutablePath ? "应用并导出" : "请先配置 Blender" }}
              </button>
            </div>
          </section>
        </div>

        <div v-if="fbxSkinPrompt.open" class="project-prompt-backdrop fbx-skin-backdrop" role="presentation" @click.self="closeFbxSkinPrompt">
          <section
            class="project-prompt fbx-skin-prompt"
            role="dialog"
            aria-modal="true"
            aria-labelledby="fbx-skin-prompt-title"
            @keydown.esc.prevent="closeFbxSkinPrompt"
          >
            <div class="prompt-decoration" aria-hidden="true"><span></span><span></span><span></span></div>
            <div class="fbx-skin-modal-head">
              <div>
                <span class="section-kicker">ITEM TOOL / FBX</span>
                <h2 id="fbx-skin-prompt-title">FBX 纯网格</h2>
              </div>
              <button class="sims4-fbx-close" type="button" :disabled="fbxSkinPrompt.busy" aria-label="关闭" @click="closeFbxSkinPrompt">×</button>
            </div>
            <div class="fbx-skin-source-row">
              <div>
                <span class="field-label-text">源 FBX（当前项目目录）</span>
                <strong v-if="fbxSkinPrompt.sourcePath" :title="fbxSkinPrompt.sourcePath">{{ fbxSkinSourceName }}</strong>
                <code>{{ fbxSkinPrompt.sourceRelativePath || "尚未选择文件" }}</code>
              </div>
              <button type="button" :disabled="fbxSkinPrompt.busy" @click="selectFbxSkinSource">{{ fbxSkinPrompt.sourcePath ? "更换文件" : "选择 FBX" }}</button>
            </div>
            <label class="fbx-skin-backup-toggle">
              <input v-model="fbxSkinPrompt.backupOriginal" type="checkbox" :disabled="fbxSkinPrompt.busy">
              <span>
                <strong>备份原文件</strong>
              </span>
            </label>
            <div v-if="fbxSkinPrompt.notice.message" class="workbench-notice fbx-skin-notice" :class="fbxSkinPrompt.notice.type" role="status">
              <span>{{ fbxSkinPrompt.notice.type === "success" ? "✓" : fbxSkinPrompt.notice.type === "error" ? "!" : "i" }}</span>
              <p>{{ fbxSkinPrompt.notice.message }}</p>
            </div>
            <section v-if="fbxSkinPrompt.result" class="fbx-skin-result">
              <div class="fbx-skin-result-head">
                <div><span>OUTPUT / STATIC MESH</span><h3>处理完成</h3></div>
                <button type="button" @click="revealFbxSkinOutput">定位输出</button>
              </div>
              <code :title="fbxSkinPrompt.result.output">{{ fbxSkinPrompt.result.outputRelativePath }}{{ fbxSkinPrompt.result.overwroteInput ? "（已覆盖原文件）" : "" }}</code>
              <small v-if="fbxSkinPrompt.result.backupRelativePath" class="fbx-skin-backup-path">备份：{{ fbxSkinPrompt.result.backupRelativePath }}</small>
              <div class="fbx-skin-result-summary">
                <div><span>Mesh</span><strong>{{ fbxSkinPrompt.result.meshCount }}</strong></div>
                <div><span>移除 Modifier</span><strong>{{ fbxSkinPrompt.result.removedArmatureModifiers }}</strong></div>
                <div><span>移除顶点组</span><strong>{{ fbxSkinPrompt.result.removedVertexGroups }}</strong></div>
              </div>
            </section>
            <div v-if="fbxSkinPrompt.error" class="setup-error" role="alert"><span>!</span>{{ fbxSkinPrompt.error }}</div>
            <div class="prompt-actions fbx-skin-actions">
              <button type="button" :disabled="fbxSkinPrompt.busy" @click="closeFbxSkinPrompt">关闭</button>
              <button class="primary" type="button" :disabled="fbxSkinPrompt.busy || !fbxSkinPrompt.sourcePath || !ctx.blenderExecutablePath" @click="removeFbxSkin">
                <span v-if="fbxSkinPrompt.busy" class="button-spinner" aria-hidden="true"></span>
                {{ fbxSkinPrompt.busy ? "正在处理…" : ctx.blenderExecutablePath ? "开始处理" : "请先配置 Blender" }}
              </button>
            </div>
          </section>
        </div>

        <div v-if="hs2SkeletonPrompt.open" class="project-prompt-backdrop hs2-skeleton-backdrop" role="presentation" @click.self="closeHs2SkeletonPrompt">
          <section
            class="project-prompt fbx-skin-prompt hs2-skeleton-prompt"
            role="dialog"
            aria-modal="true"
            aria-labelledby="hs2-skeleton-prompt-title"
            @keydown.esc.prevent="closeHs2SkeletonPrompt"
          >
            <div class="prompt-decoration" aria-hidden="true"><span></span><span></span><span></span></div>
            <div class="fbx-skin-modal-head">
              <div>
                <span class="section-kicker">ITEM TOOL / HS2 RIG</span>
                <h2 id="hs2-skeleton-prompt-title">绑定 HS2 骨架</h2>
              </div>
              <button class="sims4-fbx-close" type="button" :disabled="hs2SkeletonPrompt.busy" aria-label="关闭" @click="closeHs2SkeletonPrompt">×</button>
            </div>
            <div class="hs2-skeleton-fields">
              <div class="fbx-skin-source-row">
                <div>
                  <span class="field-label-text">Mesh FBX（当前项目目录）</span>
                  <strong v-if="hs2SkeletonPrompt.sourcePath" :title="hs2SkeletonPrompt.sourcePath">{{ hs2SkeletonSourceName }}</strong>
                  <code>{{ hs2SkeletonPrompt.sourceRelativePath || "尚未选择文件" }}</code>
                </div>
                <button type="button" :disabled="hs2SkeletonPrompt.busy" @click="selectHs2SkeletonMesh">{{ hs2SkeletonPrompt.sourcePath ? "更换 Mesh" : "选择 Mesh FBX" }}</button>
              </div>
              <div class="fbx-skin-source-row hs2-skeleton-reference-row">
                <div>
                  <span class="field-label-text">HS2 骨架来源（可在项目外）</span>
                  <strong v-if="hs2SkeletonPrompt.skeletonPath" :title="hs2SkeletonPrompt.skeletonPath">{{ hs2SkeletonReferenceName }}</strong>
                  <code>{{ hs2SkeletonPrompt.skeletonPath || "请选择 body.fbx" }}</code>
                </div>
                <button type="button" :disabled="hs2SkeletonPrompt.busy" @click="selectHs2SkeletonReference">{{ hs2SkeletonPrompt.skeletonPath ? "更换骨架" : "选择 body.fbx" }}</button>
              </div>
            </div>
            <label class="fbx-skin-backup-toggle">
              <input v-model="hs2SkeletonPrompt.backupOriginal" type="checkbox" :disabled="hs2SkeletonPrompt.busy">
              <span>
                <strong>处理前备份原文件</strong>
              </span>
            </label>
            <div v-if="hs2SkeletonPrompt.notice.message" class="workbench-notice fbx-skin-notice" :class="hs2SkeletonPrompt.notice.type" role="status">
              <span>{{ hs2SkeletonPrompt.notice.type === "success" ? "✓" : hs2SkeletonPrompt.notice.type === "error" ? "!" : "i" }}</span>
              <p>{{ hs2SkeletonPrompt.notice.message }}</p>
            </div>
            <section v-if="hs2SkeletonPrompt.result" class="fbx-skin-result">
              <div class="fbx-skin-result-head">
                <div><span>OUTPUT / HS2 RIG</span><h3>绑定完成</h3></div>
                <button type="button" @click="revealHs2SkeletonOutput">定位输出</button>
              </div>
              <code :title="hs2SkeletonPrompt.result.output">{{ hs2SkeletonPrompt.result.outputRelativePath }}{{ hs2SkeletonPrompt.result.overwroteInput ? "（已覆盖原文件）" : "" }}</code>
              <small v-if="hs2SkeletonPrompt.result.backupRelativePath" class="fbx-skin-backup-path">备份：{{ hs2SkeletonPrompt.result.backupRelativePath }}</small>
              <div class="fbx-skin-result-summary hs2-skeleton-result-summary">
                <div><span>Mesh</span><strong>{{ hs2SkeletonPrompt.result.meshCount }}</strong></div>
                <div><span>骨骼</span><strong>{{ hs2SkeletonPrompt.result.boneCount }}</strong></div>
                <div><span>蒙皮 Modifier</span><strong>{{ hs2SkeletonPrompt.result.armatureModifiers }}</strong></div>
                <div><span>顶点组</span><strong>{{ hs2SkeletonPrompt.result.vertexGroups }}</strong></div>
              </div>
            </section>
            <div v-if="hs2SkeletonPrompt.error" class="setup-error" role="alert"><span>!</span>{{ hs2SkeletonPrompt.error }}</div>
            <div class="prompt-actions fbx-skin-actions">
              <button type="button" :disabled="hs2SkeletonPrompt.busy" @click="closeHs2SkeletonPrompt">关闭</button>
              <button class="primary" type="button" :disabled="hs2SkeletonPrompt.busy || !hs2SkeletonPrompt.sourcePath || !hs2SkeletonPrompt.skeletonPath || !ctx.blenderExecutablePath" @click="bindHs2Skeleton">
                <span v-if="hs2SkeletonPrompt.busy" class="button-spinner" aria-hidden="true"></span>
                {{ hs2SkeletonPrompt.busy ? "正在绑定…" : ctx.blenderExecutablePath ? "开始绑定" : "请先配置 Blender" }}
              </button>
            </div>
          </section>
        </div>

        <div v-if="fbxWeightPrompt.open" class="project-prompt-backdrop fbx-weight-backdrop" role="presentation" @click.self="closeFbxWeightPrompt">
          <section
            class="project-prompt fbx-skin-prompt fbx-weight-prompt"
            role="dialog"
            aria-modal="true"
            aria-labelledby="fbx-weight-prompt-title"
            @keydown.esc.prevent="closeFbxWeightPrompt"
          >
            <div class="prompt-decoration" aria-hidden="true"><span></span><span></span><span></span></div>
            <div class="fbx-skin-modal-head">
              <div>
                <span class="section-kicker">ITEM TOOL / WEIGHTS</span>
                <h2 id="fbx-weight-prompt-title">复制 FBX 权重</h2>
              </div>
              <button class="sims4-fbx-close" type="button" :disabled="fbxWeightPrompt.busy" aria-label="关闭" @click="closeFbxWeightPrompt">×</button>
            </div>
            <div class="hs2-skeleton-fields">
              <div class="fbx-skin-source-row fbx-weight-source-row">
                <div>
                  <span class="field-label-text">权重来源（已有蒙皮，可在项目外）</span>
                  <strong v-if="fbxWeightPrompt.sourcePath" :title="fbxWeightPrompt.sourcePath">{{ fbxWeightSourceName }}</strong>
                  <code>{{ fbxWeightPrompt.sourcePath || "请选择 meshes0.fbx" }}</code>
                </div>
                <button type="button" :disabled="fbxWeightPrompt.busy" @click="selectFbxWeightSource">{{ fbxWeightPrompt.sourcePath ? "更换来源" : "选择来源 FBX" }}</button>
              </div>
              <div class="fbx-skin-source-row">
                <div>
                  <span class="field-label-text">目标 FBX（当前项目目录）</span>
                  <strong v-if="fbxWeightPrompt.targetPath" :title="fbxWeightPrompt.targetPath">{{ fbxWeightTargetName }}</strong>
                  <code>{{ fbxWeightPrompt.targetRelativePath || "请选择带骨架的目标 FBX" }}</code>
                </div>
                <button type="button" :disabled="fbxWeightPrompt.busy" @click="selectFbxWeightTarget">{{ fbxWeightPrompt.targetPath ? "更换目标" : "选择目标 FBX" }}</button>
              </div>
            </div>
            <label class="fbx-skin-backup-toggle">
              <input v-model="fbxWeightPrompt.backupOriginal" type="checkbox" :disabled="fbxWeightPrompt.busy">
              <span>
                <strong>处理前备份目标文件</strong>
              </span>
            </label>
            <div v-if="fbxWeightPrompt.notice.message" class="workbench-notice fbx-skin-notice" :class="fbxWeightPrompt.notice.type" role="status">
              <span>{{ fbxWeightPrompt.notice.type === "success" ? "✓" : fbxWeightPrompt.notice.type === "error" ? "!" : "i" }}</span>
              <p>{{ fbxWeightPrompt.notice.message }}</p>
            </div>
            <section v-if="fbxWeightPrompt.result" class="fbx-skin-result">
              <div class="fbx-skin-result-head">
                <div><span>OUTPUT / WEIGHT TRANSFER</span><h3>转移完成</h3></div>
                <button type="button" @click="revealFbxWeightOutput">定位输出</button>
              </div>
              <code :title="fbxWeightPrompt.result.output">{{ fbxWeightPrompt.result.outputRelativePath }}{{ fbxWeightPrompt.result.overwroteInput ? "（已覆盖目标文件）" : "" }}</code>
              <small v-if="fbxWeightPrompt.result.backupRelativePath" class="fbx-skin-backup-path">备份：{{ fbxWeightPrompt.result.backupRelativePath }}</small>
              <div class="fbx-skin-result-summary fbx-weight-result-summary">
                <div><span>映射骨骼组</span><strong>{{ fbxWeightPrompt.result.mappedGroupCount }}</strong></div>
                <div><span>已写入顶点</span><strong>{{ fbxWeightPrompt.result.weightedVertexCount }}</strong></div>
                <div><span>Armature Modifier</span><strong>{{ fbxWeightPrompt.result.armatureModifiers }}</strong></div>
                <div><span>最近距离</span><strong>{{ Number(fbxWeightPrompt.result.averageNearestDistance || 0).toFixed(4) }}</strong></div>
              </div>
            </section>
            <div v-if="fbxWeightPrompt.error" class="setup-error" role="alert"><span>!</span>{{ fbxWeightPrompt.error }}</div>
            <div class="prompt-actions fbx-skin-actions">
              <button type="button" :disabled="fbxWeightPrompt.busy" @click="closeFbxWeightPrompt">关闭</button>
              <button class="primary" type="button" :disabled="fbxWeightPrompt.busy || !fbxWeightPrompt.sourcePath || !fbxWeightPrompt.targetPath || !ctx.blenderExecutablePath" @click="transferFbxWeights">
                <span v-if="fbxWeightPrompt.busy" class="button-spinner" aria-hidden="true"></span>
                {{ fbxWeightPrompt.busy ? "正在转移…" : ctx.blenderExecutablePath ? "开始转移权重" : "请先配置 Blender" }}
              </button>
            </div>
          </section>
        </div>

        <section
          v-if="hasProjects"
          class="project-board"
          :class="{ 'is-project-space': activeProject && projectListCollapsed, 'is-project-list-open': activeProject && !projectListCollapsed }"
        >
          <div v-if="!activeProject" class="board-head compact">
            <div><span class="section-kicker">MY MOD PROJECTS</span><h2>模组项目</h2></div>
            <div v-if="!activeProject" class="project-board-actions">
              <label class="project-search-control project-search-control-board">
                <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                  <circle cx="10.8" cy="10.8" r="6.4" />
                  <path d="m16 16 4.6 4.6" />
                </svg>
                <input
                  v-model="projectSearchQuery"
                  type="search"
                  autocomplete="off"
                  spellcheck="false"
                  placeholder="搜索项目…"
                  aria-label="搜索模组项目"
                  aria-controls="workbench-project-list"
                  @focus="projectListCollapsed = false"
                  @keydown.esc.stop="projectSearchQuery = ''"
                >
                <span v-if="projectSearchQuery.trim()" class="project-search-count">{{ filteredProjects.length }}</span>
              </label>
              <button
                class="project-list-toggle"
                type="button"
                :aria-expanded="!projectListCollapsed"
                :aria-label="projectListCollapsed ? '显示模组项目列表' : '隐藏模组项目列表'"
                @click="toggleProjectList"
              >
                {{ projectListCollapsed ? "显示列表" : "隐藏列表" }}
              </button>
              <button type="button" @click="openProjectPrompt">新建项目</button>
            </div>
          </div>
          <div v-if="!projectListCollapsed" id="workbench-project-list" class="project-list">
            <article
              v-for="project in filteredProjects"
              :key="project.id"
              class="project-row"
              :class="{ 'is-current': project.id === activeProject?.id }"
              role="button"
              tabindex="0"
              :aria-pressed="project.id === activeProject?.id"
              @click="selectProject(project)"
              @keydown.enter.prevent="selectProject(project)"
              @keydown.space.prevent="selectProject(project)"
            >
              <div class="project-row-copy">
                <strong>{{ project.name }}</strong>
              </div>
              <button
                class="workbench-delete-button"
                type="button"
                :disabled="deletingProjectId === project.id"
                :title="`删除工程：${project.name}`"
                :aria-label="`删除工程：${project.name}`"
                @click.stop="deleteProject(project)"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                  <path d="M4 7h16M9 7V4h6v3m-8 0 1 13h8l1-13M10 11v6m4-6v6" />
                </svg>
              </button>
            </article>
            <div v-if="projectSearchQuery.trim() && !filteredProjects.length" class="project-list-empty" role="status">
              未找到匹配的项目
            </div>
          </div>
          <div v-else-if="false" class="project-list-collapsed" role="status">
            <div>
              <strong>项目列表已隐藏</strong>
              <span>{{ projectsForWorkspace.length }} 个模组项目</span>
            </div>
            <span v-if="activeProject">当前项目：{{ activeProject.name }}</span>
          </div>

          <div v-if="activeProject" class="project-workbench-toolbar project-workbench-toolbar-floating" role="toolbar" aria-label="当前模组工具栏">
            <div class="project-workbench-toolbar-label">
              <strong>{{ activeProject.name }}</strong>
            </div>
            <div class="project-workbench-toolbar-tools">
              <button
                class="project-workbench-context-button project-list-toggle-control"
                type="button"
                :title="projectListCollapsed ? '显示模组项目列表' : '隐藏模组项目列表'"
                @click="toggleProjectList"
              >
                <svg
                  class="project-list-toggle-icon"
                  :class="{ 'is-expanded': !projectListCollapsed }"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                  focusable="false"
                >
                  <path d="m6 9 6 6 6-6" />
                </svg>
              </button>
              <button class="project-workbench-context-button" type="button" @click="openProjectPrompt">新建项目</button>
              <button
                class="workbench-tool-button"
                type="button"
                :disabled="packagingMod"
                :title="ctx.paths?.gameDir ? '将当前工程打包为正式 zipmod 并替换旧版本' : '请先选择 HS2 游戏目录'"
                @click="packageCurrentMod"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                  <path d="M4 8.5h6l1.5 2H20v9H4z" />
                  <path d="M8 5h8v4H8zM10 14h4M10 17h4" />
                </svg>
                <span>{{ packagingLabel }}</span>
              </button>
              <button
                class="workbench-tool-button"
                type="button"
                title="将 Sims 4 Package 模组包转换为 FBX 和 PNG"
                @click="openSims4FbxPrompt"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                  <path d="m12 3 8 4.5v9L12 21l-8-4.5v-9z" />
                  <path d="m4 7.5 8 4.5 8-4.5M12 12v9" />
                </svg>
                <span>Package → FBX</span>
              </button>
              <div v-if="selectedItem" class="item-workbench-toolbar item-workbench-toolbar--project" role="toolbar" aria-label="当前物品工具栏">
                <div class="item-workbench-toolbar-label">
                  <strong>物品工具</strong>
                </div>
                <div class="item-workbench-toolbar-tools">
                  <button
                    class="workbench-tool-button fbx-transform-tool-button"
                    type="button"
                    title="使用 Blender 导入 FBX，应用 Mesh 的现有旋转与缩放后重新导出"
                    aria-label="应用 FBX 旋转与缩放"
                    @click="openFbxTransformPrompt"
                  >
                    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                      <path d="M8 6a7 7 0 1 1-2 10" />
                      <path d="M8 2v4H4" />
                      <path d="M10 10h7v7h-7zM17 10l3-3M16 7h4v4" />
                    </svg>
                  </button>
                  <button
                    class="workbench-tool-button fbx-skin-tool-button"
                    type="button"
                    title="删除 FBX 骨骼、蒙皮和顶点组，保留网格"
                    aria-label="FBX 纯网格"
                    @click="openFbxSkinPrompt"
                  >
                    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                      <path d="M4 5h16v14H4z" />
                      <path d="M8 9h8M8 13h5M16 16l4 4M20 16l-4 4" />
                    </svg>
                  </button>
                  <button
                    class="workbench-tool-button hs2-skeleton-tool-button"
                    type="button"
                    title="为无骨骼 FBX 添加 HS2 标准骨架，不添加蒙皮"
                    aria-label="绑定 HS2 骨架"
                    @click="openHs2SkeletonPrompt"
                  >
                    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                      <path d="M12 4v16M7 8h10M7 16h10M7 8v8M17 8v8" />
                      <circle cx="12" cy="4" r="2" />
                      <circle cx="7" cy="8" r="2" />
                      <circle cx="17" cy="8" r="2" />
                      <circle cx="7" cy="16" r="2" />
                      <circle cx="17" cy="16" r="2" />
                    </svg>
                  </button>
                  <button
                    class="workbench-tool-button fbx-weight-tool-button"
                    type="button"
                    title="从已有蒙皮 FBX 向目标骨架 FBX 转移权重"
                    aria-label="复制 FBX 权重"
                    @click="openFbxWeightPrompt"
                  >
                    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                      <path d="M5 7h6v4H5zM13 13h6v4h-6z" />
                      <path d="M11 9h2v6M9 15h4M15 9h-4" />
                      <path d="m9 13-2 2 2 2M15 11l2-2-2-2" />
                    </svg>
                  </button>
                  <button
                    class="workbench-tool-button texture-processor-tool-button"
                    type="button"
                    title="裁剪方形贴图、选择分辨率并去除基础颜色"
                    aria-label="贴图处理"
                    @click="openTextureProcessor"
                  >
                    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                      <path d="M7 3v14a4 4 0 0 0 4 4h10M3 7h14a4 4 0 0 1 4 4v10" />
                      <path d="m11 14 2-2 4 4M15 9h.01" />
                    </svg>
                  </button>
                </div>
              </div>
              <label class="project-search-control">
                <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                  <circle cx="10.8" cy="10.8" r="6.4" />
                  <path d="m16 16 4.6 4.6" />
                </svg>
                <input
                  v-model="projectSearchQuery"
                  type="search"
                  autocomplete="off"
                  spellcheck="false"
                  placeholder="搜索项目…"
                  aria-label="搜索模组项目"
                  aria-controls="workbench-project-list"
                  @focus="projectListCollapsed = false"
                  @keydown.esc.stop="projectSearchQuery = ''"
                >
                <span v-if="projectSearchQuery.trim()" class="project-search-count">{{ filteredProjects.length }}</span>
              </label>
            </div>
          </div>
        </section>

        <div v-if="itemPrompt.open" class="project-prompt-backdrop" role="presentation" @click.self="itemPrompt.open = false">
          <section class="project-prompt" role="dialog" aria-modal="true" aria-labelledby="item-prompt-title">
            <div class="prompt-decoration" aria-hidden="true"><span></span><span></span><span></span></div>
            <span class="section-kicker">NEW ITEM / {{ activeProject?.name }}</span>
            <h2 id="item-prompt-title">新建物品</h2>
            <label class="field-label" for="workbench-item-name">
              <span>物品名称 <em>必填</em></span>
              <input id="workbench-item-name" v-model="itemPrompt.name" type="text" maxlength="120" autocomplete="off" placeholder="例如：Ribbon Set">
            </label>
            <label class="field-label" for="workbench-item-category">
              <span>物品类别 <em>必填</em></span>
              <select id="workbench-item-category" v-model="itemPrompt.category" :disabled="!itemCategoryOptions.length">
                <option value="" disabled>{{ itemCategoryOptions.length ? "请选择物品类别" : "当前物品管理暂无类别" }}</option>
                <option v-for="option in itemCategoryOptions" :key="option.value" :value="option.value">
                  {{ option.label }}（{{ option.value }}）
                </option>
              </select>
            </label>
            <div v-if="itemPrompt.error" class="setup-error" role="alert"><span>!</span>{{ itemPrompt.error }}</div>
            <div class="prompt-actions">
              <button type="button" :disabled="itemPrompt.busy" @click="itemPrompt.open = false">取消</button>
              <button class="primary" type="button" :disabled="itemPrompt.busy" @click="createItem">
                <span v-if="itemPrompt.busy" class="button-spinner" aria-hidden="true"></span>
                {{ itemPrompt.busy ? "正在创建…" : "创建物品" }}
              </button>
            </div>
          </section>
        </div>

        <div
          v-if="deletePrompt.open"
          class="project-prompt-backdrop delete-confirm-backdrop"
          role="presentation"
          @click.self="closeDeletePrompt(false)"
        >
          <section
            class="project-prompt delete-confirm-prompt"
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-prompt-title"
            aria-describedby="delete-prompt-message delete-prompt-detail"
            ref="deletePromptDialog"
            tabindex="-1"
            @keydown.esc.prevent="closeDeletePrompt(false)"
          >
            <div class="prompt-decoration" aria-hidden="true"><span></span><span></span><span></span></div>
            <span class="section-kicker">DELETE / CONFIRM</span>
            <h2 id="delete-prompt-title">{{ deletePrompt.title }}</h2>
            <p id="delete-prompt-message" class="delete-confirm-message">{{ deletePrompt.message }}</p>
            <div class="delete-confirm-detail">
              <span aria-hidden="true">!</span>
              <p id="delete-prompt-detail">{{ deletePrompt.detail }}</p>
            </div>
            <div class="prompt-actions">
              <button type="button" @click="closeDeletePrompt(false)">取消</button>
              <button class="delete-confirm-action" type="button" @click="closeDeletePrompt(true)">删除</button>
            </div>
          </section>
        </div>

        <section v-if="activeProject && !selectedItem" class="item-browser">
          <div class="board-head compact item-browser-head">
            <div>
              <h2>模组物品</h2>
              <p><code>{{ activeProject.guid }}</code></p>
            </div>
            <div class="item-browser-actions">
              <span class="shelf-count">{{ items.length }} ITEMS</span>
              <button type="button" @click="openItemPrompt">新建物品</button>
            </div>
          </div>

          <div v-if="itemBrowser.loading" class="item-browser-state">正在读取当前工程的物品…</div>
          <div v-else-if="itemBrowser.error" class="setup-error" role="alert"><span>!</span>{{ itemBrowser.error }}</div>
          <div v-else-if="items.length" class="item-list">
            <article
              v-for="item in items"
              :key="item.id"
              class="item-row"
              :class="{ 'is-selected': selectedItem?.id === item.id }"
              role="button"
              tabindex="0"
              :aria-pressed="selectedItem?.id === item.id"
              @click="selectItem(item)"
              @keydown.enter.prevent="selectItem(item)"
              @keydown.space.prevent="selectItem(item)"
            >
              <div class="item-row-copy">
                <strong>{{ item.csvData?.record?.Name || item.name || "未命名物品" }}</strong>
              </div>
              <button
                class="workbench-delete-button"
                type="button"
                :disabled="deletingItemId === item.id"
                :title="`删除物品：${item.csvData?.record?.Name || item.name || '未命名物品'}`"
                :aria-label="`删除物品：${item.csvData?.record?.Name || item.name || '未命名物品'}`"
                @click.stop="deleteItem(item)"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                  <path d="M4 7h16M9 7V4h6v3m-8 0 1 13h8l1-13M10 11v6m4-6v6" />
                </svg>
              </button>
            </article>
          </div>
        </section>

        <section v-else-if="activeProject && selectedItem" class="item-workspace">
          <header class="item-workspace-head">
            <div class="item-workspace-topbar">
              <button class="workspace-back" type="button" @click="leaveItemWorkspace">← 返回物品列表</button>
              <div class="item-workspace-actions">
                <span class="workspace-status">CSV SOURCE</span>
                <button type="button" @click="openItemDirectory(selectedItem)">打开 CSV 目录</button>
              </div>
            </div>

            <div class="item-workspace-content">
              <div class="item-workspace-heading">
                <input
                  v-model="editableResourceValues.Name"
                  class="item-name-input"
                  type="text"
                  maxlength="120"
                  autocomplete="off"
                  placeholder="物品名称"
                  aria-label="物品名称"
                  :disabled="Boolean(resourceFieldSaving)"
                  @blur="saveEditableResourceField('Name')"
                  @keydown.enter.prevent="$event.target.blur()"
                  @keydown.esc.prevent="cancelEditableResourceField('Name')"
                >
              </div>
              <div class="item-workspace-thumbnail" aria-label="当前物品缩略图">
                <div v-if="workbenchThumbnail.loading" class="item-workspace-thumbnail-state">
                  <span class="button-spinner" aria-hidden="true"></span>
                  <span>正在读取缩略图…</span>
                </div>
                <button
                  v-else-if="workbenchThumbnail.dataUrl"
                  class="item-workspace-thumbnail-preview"
                  type="button"
                  :disabled="workbenchThumbnail.busy"
                  :aria-busy="workbenchThumbnail.busy"
                  aria-label="重新拍摄缩略图"
                  title="点击重新拍摄缩略图"
                  @click="buildWorkbenchThumbnail"
                >
                  <img
                    :src="workbenchThumbnail.dataUrl"
                    :alt="`${selectedItemRecord.Name || '当前物品'} 缩略图`"
                    @error="handleWorkbenchThumbnailError"
                  >
                </button>
                <button
                  v-else
                  class="workbench-thumbnail-build"
                  type="button"
                  :disabled="workbenchThumbnail.busy || !workbenchPreviewReady"
                  :aria-busy="workbenchThumbnail.busy"
                  aria-label="构建缩略图"
                  title="从当前 3D 预览截图并写入 CSV"
                  @click="buildWorkbenchThumbnail"
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                    <path d="M5 7h3l1.3-2h5.4L16 7h3v11H5z" />
                    <circle cx="12" cy="12" r="3.2" />
                  </svg>
                </button>
              </div>
            </div>
          </header>

          <div class="item-resource-grid">
            <article v-for="group in selectedItemResourceGroups" :key="group.key" class="item-resource-card" :class="`is-${group.key}`">
              <h3>{{ group.title }}</h3>
              <dl>
                <div v-for="field in group.fields" :key="field" class="resource-field">
                  <dt>{{ field }}</dt>
                  <dd class="resource-field-value">
                    <input
                      v-if="isEditableResourceField(field)"
                      v-model="editableResourceValues[field]"
                      class="resource-field-input"
                      type="text"
                      autocomplete="off"
                      :disabled="Boolean(resourceFieldSaving)"
                      :placeholder="field === 'MainData' ? 'MainData' : '待填写'"
                      :aria-label="field"
                      @blur="saveEditableResourceField(field)"
                      @keydown.enter.prevent="$event.target.blur()"
                      @keydown.esc.prevent="cancelEditableResourceField(field)"
                    >
                    <select
                      v-else-if="field === 'MainAB' && projectUnity3dLibrary.files.length"
                      class="main-resource-existing-select"
                      :value="selectedItemRecord.MainAB || ''"
                      :disabled="projectUnity3dLibrary.loading || resourceEditor.saving"
                      title="选择当前工程已有的 Unity3D"
                      aria-label="选择当前工程已有的 Unity3D"
                      @change="selectInlineExistingUnity3d"
                    >
                      <option value="" disabled>选择已有 Unity3D</option>
                      <option
                        v-if="selectedItemRecord.MainAB && !projectUnity3dLibrary.files.some((file) => file.relativePath === selectedItemRecord.MainAB)"
                        :value="selectedItemRecord.MainAB"
                        disabled
                      >{{ selectedItemRecord.MainAB }}（未找到）</option>
                      <option v-for="file in projectUnity3dLibrary.files" :key="file.path" :value="file.relativePath">
                        {{ file.relativePath }}
                      </option>
                    </select>
                    <button
                      v-else-if="field === 'MainAB' && selectedItemRecord[field]"
                      class="resource-field-link"
                      type="button"
                      :disabled="openingMainAb"
                      title="使用 SB3Utility 打开 Unity3D"
                      @click.stop="openMainAbInSb3Utility"
                    >
                      <span :title="selectedItemRecord[field]">{{ selectedItemRecord[field] }}</span>
                    </button>
                    <span
                      v-else-if="!isEditableResourceField(field)"
                      :class="{ 'is-empty': !selectedItemRecord[field] }"
                      :title="selectedItemRecord[field] || ''"
                    >{{ selectedItemRecord[field] || "待填写" }}</span>
                    <span
                      v-if="['found', 'missing'].includes(mainResourceFieldStatus(field))"
                      class="resource-field-check"
                      :class="`is-${mainResourceFieldStatus(field)}`"
                      :title="mainResourceFieldTitle(field)"
                      aria-hidden="true"
                    >{{ mainResourceFieldStatus(field) === 'found' ? '✓' : '×' }}</span>
                    <button
                      v-if="canImportTextureField(field)"
                      class="texture-import-button"
                      type="button"
                      :disabled="Boolean(textureImporting)"
                      title="从外部导入贴图并使用当前资源名"
                      @click.stop="importTextureField(field)"
                    >{{ textureImporting === field ? "导入中" : "导入" }}</button>
                    <button
                      v-if="field === 'MainAB' && projectUnity3dLibrary.files.length && selectedItemRecord.MainAB"
                      class="main-resource-open-button"
                      type="button"
                      :disabled="openingMainAb"
                      title="使用 SB3Utility 打开当前 Unity3D"
                      aria-label="使用 SB3Utility 打开当前 Unity3D"
                      @click.stop="openMainAbInSb3Utility"
                    >
                      <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                        <path d="M14 5h5v5M19 5l-8 8" />
                        <path d="M18 13v5a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5" />
                      </svg>
                    </button>
                    <button
                      v-if="field === 'MainAB' && (!selectedItemRecord.MainAB || !selectedItemRecord.MainData)"
                      class="main-resource-add-button"
                      type="button"
                      title="从数据库选择 Unity3D 主资源"
                      aria-label="从数据库选择 Unity3D 主资源"
                      @click.stop="openDatabaseTemplatePicker"
                    >
                      <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                        <path d="M12 5v14M5 12h14" />
                      </svg>
                    </button>
                  </dd>
                </div>
              </dl>
            </article>
            <article class="item-resource-card is-texture">
              <div class="item-resource-card-title">
                <h3>贴图</h3>
                <button
                  v-if="textureGroups.length < MAX_TEXTURE_GROUPS"
                  class="texture-group-add-button"
                  type="button"
                  :disabled="Boolean(resourceFieldSaving)"
                  title="新增一组贴图"
                  aria-label="新增一组贴图"
                  @click.stop="addTextureGroup"
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                    <path d="M12 5v14M5 12h14" />
                  </svg>
                </button>
              </div>
              <div class="texture-group-list">
                <section v-for="(group, groupIndex) in textureGroups" :key="group.key" class="texture-group">
                  <div class="texture-group-heading">
                    <span>第 {{ group.index }} 组</span>
                    <button
                      v-if="textureGroups.length > 1"
                      class="texture-group-remove-button"
                      type="button"
                      :disabled="Boolean(resourceFieldSaving)"
                      :title="`删除第 ${group.index} 组贴图`"
                      :aria-label="`删除第 ${group.index} 组贴图`"
                      @click.stop="deleteTextureGroup(groupIndex)"
                    >
                      <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                        <path d="M8 7V4h8v3M5 7h14M7 7l.75 13h8.5L17 7M10 11v5M14 11v5" />
                      </svg>
                    </button>
                  </div>
                  <dl>
                    <div v-for="field in group.fields" :key="field" class="resource-field">
                      <dt>{{ textureFieldLabel(field, group.index) }}</dt>
                      <dd class="resource-field-value">
                        <input
                          v-if="isEditableResourceField(field)"
                          v-model="editableResourceValues[field]"
                          class="resource-field-input"
                          type="text"
                          autocomplete="off"
                          :disabled="Boolean(resourceFieldSaving)"
                          placeholder="待填写"
                          :aria-label="`${field} 第 ${group.index} 组`"
                          @blur="saveEditableResourceField(field)"
                          @keydown.enter.prevent="$event.target.blur()"
                          @keydown.esc.prevent="cancelEditableResourceField(field)"
                        >
                        <span
                          v-if="['found', 'missing'].includes(mainResourceFieldStatus(field))"
                          class="resource-field-check"
                          :class="`is-${mainResourceFieldStatus(field)}`"
                          :title="mainResourceFieldTitle(field)"
                          aria-hidden="true"
                        >{{ mainResourceFieldStatus(field) === 'found' ? '✓' : '×' }}</span>
                        <button
                          v-if="canImportTextureField(field)"
                          class="texture-import-button"
                          type="button"
                          :disabled="Boolean(textureImporting)"
                          title="从外部导入贴图并使用当前资源名"
                          @click.stop="importTextureField(field)"
                        >{{ textureImporting === field ? "导入中" : "导入" }}</button>
                        <button
                          v-if="canReplaceTextureField(field)"
                          class="texture-replace-button"
                          :class="{ 'is-busy': textureImporting === field }"
                          type="button"
                          :disabled="Boolean(textureImporting)"
                          :title="`替换贴图 ${editableResourceValues[field] || selectedItemRecord[field]}`"
                          :aria-label="`替换贴图 ${editableResourceValues[field] || selectedItemRecord[field]}`"
                          @click.stop="replaceTextureField(field)"
                        >
                          <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                            <path d="M7.5 7H18l-2.5-2.5M18 7l-2.5 2.5M16.5 17H6l2.5 2.5M6 17l2.5-2.5" />
                          </svg>
                        </button>
                      </dd>
                    </div>
                  </dl>
                </section>
              </div>
            </article>
          </div>

          <div class="workbench-preview-row">
            <section class="workbench-item-preview" aria-labelledby="workbench-item-preview-title">
            <header class="workbench-item-preview-head">
              <div>
                <h3 id="workbench-item-preview-title">{{ workbenchTexturePreview.asset ? "贴图预览" : "3D 物品预览" }}</h3>
              </div>
              <div class="workbench-item-preview-actions">
                <span v-if="!workbenchTexturePreview.asset" class="workbench-preview-state" :class="{ 'is-ready': workbenchPreviewReady }">
                  {{ workbenchPreviewReady ? "READY" : canPreviewSelectedItem ? "AUTO LOAD" : "WAITING" }}
                </span>
                <span v-else class="workbench-preview-state is-ready">TEXTURE</span>
                <button
                  v-if="workbenchTexturePreview.asset"
                  class="workbench-preview-back"
                  type="button"
                  title="返回 3D 预览"
                  @click="resetWorkbenchTexturePreview"
                >返回 3D</button>
                <button
                  v-if="!workbenchTexturePreview.asset && canPreviewSelectedItem"
                  class="workbench-preview-refresh"
                  type="button"
                  title="重新生成 3D 预览"
                  aria-label="重新生成 3D 预览"
                  @click="refreshWorkbenchPreview"
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                    <path d="M20 7v5h-5M4 17v-5h5M6.1 9a7 7 0 0 1 11.6-2L20 9M4 15l2.3 2a7 7 0 0 0 11.6-2" />
                  </svg>
                </button>
              </div>
            </header>
            <ModelPreview
              v-if="!workbenchTexturePreview.asset && canPreviewSelectedItem"
              ref="workbenchModelPreview"
              :preview-key="workbenchPreviewKey"
              :preview-loader="loadWorkbenchModelPreview"
              auto-load
              @ready-change="workbenchPreviewReady = $event"
            />
            <div v-else-if="workbenchTexturePreview.asset" class="workbench-texture-preview">
              <div v-if="workbenchTexturePreview.loading" class="workbench-texture-state">正在读取贴图…</div>
              <div v-else-if="workbenchTexturePreview.error" class="workbench-texture-state is-error">
                <span>!</span>
                <strong>{{ workbenchTexturePreview.error }}</strong>
              </div>
              <div v-else class="workbench-texture-stage" :style="workbenchTextureStageStyle">
                <img
                  :src="workbenchTexturePreview.dataUrl"
                  :alt="`${workbenchTexturePreview.asset.name} 贴图预览`"
                  draggable="false"
                  @load="handleWorkbenchTexturePreviewLoad"
                  @error="handleWorkbenchTexturePreviewError"
                >
              </div>
            </div>
            <div v-else class="workbench-preview-empty">
              <svg viewBox="0 0 64 64" aria-hidden="true" focusable="false">
                <path d="m32 8 22 12-22 12L10 20 32 8Z" />
                <path d="m10 20 .3 24L32 56l21.7-12L54 20M32 32v24" />
                <path d="m22 24 20-11M22 40l8 4" />
              </svg>
              <strong>等待可预览资源</strong>
              <p>配置有效的 MainAB 和 MainData 后，将自动生成当前物品的交互式 3D 预览。</p>
            </div>
            </section>

            <section class="workbench-asset-library" aria-labelledby="workbench-asset-library-title">
              <header class="workbench-asset-library-head">
                <div>
                  <h3 id="workbench-asset-library-title">工程资源</h3>
                </div>
                <button
                  class="workbench-asset-refresh"
                  type="button"
                  :disabled="projectAssetLibrary.loading"
                  title="重新扫描工程资源"
                  aria-label="重新扫描工程资源"
                  @click="loadWorkbenchProjectAssets"
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                    <path d="M20 7v5h-5M4 17v-5h5M6.1 9a7 7 0 0 1 11.6-2L20 9M4 15l2.3 2a7 7 0 0 0 11.6-2" />
                  </svg>
                </button>
              </header>

              <div v-if="projectAssetLibrary.loading" class="workbench-asset-state">正在扫描工程目录…</div>
              <div v-else-if="projectAssetLibrary.error" class="workbench-asset-error" role="alert">
                <span>!</span>{{ projectAssetLibrary.error }}
              </div>
              <template v-else>
                <div class="workbench-asset-summary" aria-label="工程资源统计">
                  <div>
                    <strong>{{ projectAssetLibrary.textures.length }}</strong>
                    <span>贴图</span>
                  </div>
                  <div>
                    <strong>{{ projectAssetLibrary.models.length }}</strong>
                    <span>FBX</span>
                  </div>
                  <small>{{ projectAssetLibrary.total }} 个资源</small>
                </div>

                <div v-if="projectAssetLibrary.total" class="workbench-asset-groups">
                  <section class="workbench-asset-group">
                    <div class="workbench-asset-group-head">
                      <h4>贴图资源</h4>
                      <span>{{ projectAssetLibrary.textures.length }}</span>
                    </div>
                    <div v-if="!projectAssetLibrary.textures.length" class="workbench-asset-empty">未找到贴图文件</div>
                    <div
                      v-for="asset in projectAssetLibrary.textures"
                      :key="asset.path"
                      class="workbench-asset-row"
                      role="button"
                      tabindex="0"
                      :aria-pressed="workbenchTexturePreview.asset?.path === asset.path"
                      :title="`预览贴图 ${asset.name}`"
                      @click="previewWorkbenchTexture(asset)"
                      @keydown.enter.prevent="previewWorkbenchTexture(asset)"
                      @keydown.space.prevent="previewWorkbenchTexture(asset)"
                    >
                      <span class="workbench-asset-file-mark is-texture">TEX</span>
                      <span class="workbench-asset-file-copy">
                        <strong>{{ asset.name }}</strong>
                        <small>{{ formatWorkbenchAssetSize(asset.size) }}</small>
                      </span>
                      <button
                        class="workbench-asset-sb3"
                        type="button"
                        :disabled="openingWorkbenchSb3Path === asset.path"
                        title="使用 SB3Utility 打开"
                        :aria-label="`使用 SB3Utility 打开 ${asset.name}`"
                        @click.stop="openWorkbenchAssetInSb3Utility(asset)"
                      >
                        <img :src="sb3utilityIcon" alt="" aria-hidden="true">
                      </button>
                      <button
                        class="workbench-asset-locate"
                        type="button"
                        :title="`定位 ${asset.relativePath}`"
                        :aria-label="`定位 ${asset.name}`"
                        @click.stop="locateWorkbenchAsset(asset)"
                      >↗</button>
                    </div>
                  </section>

                  <section class="workbench-asset-group">
                    <div class="workbench-asset-group-head">
                      <h4>FBX 模型</h4>
                      <span>{{ projectAssetLibrary.models.length }}</span>
                    </div>
                    <div v-if="!projectAssetLibrary.models.length" class="workbench-asset-empty">未找到 FBX 文件</div>
                    <div
                      v-for="asset in projectAssetLibrary.models"
                      :key="asset.path"
                      class="workbench-asset-row workbench-asset-row-model"
                      role="button"
                      tabindex="0"
                      :title="`定位 ${asset.relativePath}`"
                      @click="locateWorkbenchAsset(asset)"
                      @keydown.enter.prevent="locateWorkbenchAsset(asset)"
                      @keydown.space.prevent="locateWorkbenchAsset(asset)"
                    >
                      <span class="workbench-asset-file-mark is-model">FBX</span>
                      <span class="workbench-asset-file-copy">
                        <strong>{{ asset.name }}</strong>
                      </span>
                      <button
                        class="workbench-asset-sb3"
                        type="button"
                        :disabled="openingWorkbenchSb3Path === asset.path"
                        title="使用 SB3Utility 打开"
                        :aria-label="`使用 SB3Utility 打开 ${asset.name}`"
                        @click.stop="openWorkbenchAssetInSb3Utility(asset)"
                      >
                        <img :src="sb3utilityIcon" alt="" aria-hidden="true">
                      </button>
                      <button
                        class="workbench-asset-blender"
                        type="button"
                        :disabled="openingWorkbenchFbxPath === asset.path"
                        title="使用 Blender 打开"
                        :aria-label="`使用 Blender 打开 ${asset.name}`"
                        @click.stop="openWorkbenchAssetInBlender(asset)"
                      >
                        <img :src="blenderIcon" alt="" aria-hidden="true">
                      </button>
                      <button
                        class="workbench-asset-locate"
                        type="button"
                        title="定位 FBX 文件"
                        :aria-label="`定位 ${asset.name}`"
                        @click.stop="locateWorkbenchAsset(asset)"
                      >↗</button>
                    </div>
                  </section>
                </div>
                <div v-else class="workbench-asset-empty workbench-asset-empty-all">当前工程目录下暂无贴图或 FBX 模型</div>
              </template>
            </section>
          </div>

          <section v-if="resourceEditor.open" class="main-resource-editor">
            <div v-if="resourceEditor.loading" class="item-browser-state">正在读取 Unity3D 资源…</div>
            <div v-else class="main-resource-editor-body">
              <div v-if="resourceEditor.mode === 'template'" class="template-resource-section">
                <div v-if="templatePicker.selected" class="template-selected-summary">
                  <span class="template-item-thumb">
                    <span aria-hidden="true">3D</span>
                    <img
                      v-if="templateItemThumbnailUrl(templatePicker.selected)"
                      :src="templateItemThumbnailUrl(templatePicker.selected)"
                      :alt="`${templatePicker.selected.name || 'Unity3D'} 缩略图`"
                      @error="hideTemplateItemThumbnail"
                    >
                  </span>
                  <span class="template-selected-copy">
                    <strong>{{ templatePicker.selected.name || `物品 ${templatePicker.selected.item_id || templatePicker.selected.id}` }}</strong>
                    <small>模组 GUID：{{ templatePicker.selected.zipmod_guid || "未知" }}</small>
                    <small class="mono" :title="templatePicker.selected.main_ab || '-'">{{ templatePicker.selected.main_ab || "Unity3D 路径未知" }}</small>
                  </span>
                </div>
                <div v-else class="template-selection-empty">
                  <strong>尚未选择 Unity3D 模板</strong>
                  <small>返回物品管理，在物品详情的“工具”页选择一个物品。</small>
                </div>

                <label class="field-label" for="workbench-template-main-data">
                  <span>MainData 模型对象 <em>必选</em></span>
                  <input
                    id="workbench-template-main-data"
                    v-model="resourceEditor.mainData"
                    list="workbench-template-main-data-options"
                    type="text"
                    maxlength="160"
                    autocomplete="off"
                    placeholder="请输入模型对象名"
                    @input="syncMainDataCandidate"
                  >
                  <datalist id="workbench-template-main-data-options">
                    <option v-for="candidate in resourceEditor.candidates" :key="candidate.kind + ':' + candidate.path_id" :value="candidate.value">
                      {{ candidate.value }} · {{ candidate.kind }}
                    </option>
                  </datalist>
                </label>
              </div>

              <div v-if="resourceEditor.mode === 'existing'" class="resource-editor-section">
                <label class="field-label" for="workbench-existing-unity3d">
                  <span>当前工程内的 Unity3D <em>必选</em></span>
                  <select id="workbench-existing-unity3d" v-model="resourceEditor.relativePath" @change="selectExistingUnity3d">
                    <option value="">请选择 abdata 下的文件</option>
                    <option v-for="file in resourceEditor.files" :key="file.relativePath" :value="file.relativePath">
                      {{ file.relativePath }}
                    </option>
                  </select>
                </label>
                <small v-if="!resourceEditor.files.length" class="resource-editor-hint">当前工程的 abdata 下还没有 Unity3D 文件。</small>
              </div>

              <div v-else-if="resourceEditor.mode === 'import'" class="resource-editor-section">
                <div class="resource-editor-path-row">
                  <div>
                    <span class="field-label-text">外部 Unity3D 文件 <em>必选</em></span>
                    <code>{{ resourceEditor.sourcePath || "尚未选择文件" }}</code>
                  </div>
                  <button type="button" @click="chooseImportedUnity3d">重新选择</button>
                </div>
                <small class="resource-editor-hint">导入后会复制到 abdata/chara/作者名/作者名_模组名_序号.unity3d。</small>
              </div>

              <label v-if="resourceEditor.mode !== 'template'" class="field-label" for="workbench-main-data">
                <span>MainData 模型对象 <em>必选</em></span>
                <select v-if="resourceEditor.candidates.length" id="workbench-main-data" v-model="resourceEditor.mainData">
                  <option v-for="candidate in resourceEditor.candidates" :key="candidate.kind + ':' + candidate.value" :value="candidate.value">
                    {{ candidate.value }} · {{ candidate.kind }}
                  </option>
                </select>
                <input
                  v-else
                  id="workbench-main-data"
                  v-model="resourceEditor.mainData"
                  type="text"
                  maxlength="160"
                  autocomplete="off"
                  placeholder="例如：sjjpl_Bikini_005"
                >
              </label>
              <section v-if="['template', 'existing', 'import'].includes(resourceEditor.mode)" class="template-preprocess-tools resource-object-tools">
                <div v-if="['template', 'import'].includes(resourceEditor.mode)" class="external-resource-actions">
                  <div class="external-resource-action-row">
                    <button
                      type="button"
                      :disabled="resourceEditor.saving || templatePreprocess.busy || !String(resourceEditor.mainData || '').trim()"
                      @click="preprocessResource('keep_selected')"
                    >
                      {{ templatePreprocess.busy ? "处理中…" : "清除其他对象" }}
                    </button>
                    <button
                      type="button"
                      :disabled="resourceEditor.saving || templatePreprocess.busy || !String(resourceEditor.mainData || '').trim()"
                      @click="preprocessResource('duplicate_selected')"
                    >
                      {{ templatePreprocess.busy ? "处理中…" : "复制当前对象" }}
                    </button>
                  </div>
                  <div class="template-preprocess-rename">
                    <label
                      class="field-label"
                      :for="resourceEditor.mode === 'template' ? 'workbench-template-rename' : 'workbench-import-rename'"
                    >
                      <span>新的对象名称</span>
                      <input
                        :id="resourceEditor.mode === 'template' ? 'workbench-template-rename' : 'workbench-import-rename'"
                        v-model="templatePreprocess.renameName"
                        type="text"
                        maxlength="160"
                        autocomplete="off"
                        :disabled="resourceEditor.saving || templatePreprocess.busy || !String(resourceEditor.mainData || '').trim()"
                      >
                    </label>
                    <button
                      type="button"
                      :disabled="resourceEditor.saving || templatePreprocess.busy || !String(resourceEditor.mainData || '').trim()"
                      @click="preprocessResource('rename_selected')"
                    >
                      {{ templatePreprocess.busy ? "处理中…" : "重命名当前对象" }}
                    </button>
                  </div>
                </div>
                <div v-else class="template-preprocess-grid">
                  <div class="template-preprocess-rename">
                    <label class="field-label" :for="resourceEditor.mode === 'template' ? 'workbench-template-rename' : 'workbench-existing-rename'">
                      <span>新的对象名称</span>
                      <input
                        :id="resourceEditor.mode === 'template' ? 'workbench-template-rename' : 'workbench-existing-rename'"
                        v-model="templatePreprocess.renameName"
                        type="text"
                        maxlength="160"
                        autocomplete="off"
                        :disabled="resourceEditor.saving || templatePreprocess.busy || !String(resourceEditor.mainData || '').trim()"
                      >
                    </label>
                    <button
                      type="button"
                      :disabled="resourceEditor.saving || templatePreprocess.busy || !String(resourceEditor.mainData || '').trim()"
                      @click="preprocessResource('duplicate_and_rename_selected')"
                    >
                      {{ templatePreprocess.busy ? "处理中…" : "复制所选对象并重命名" }}
                    </button>
                  </div>
                </div>
                <div v-if="templatePreprocess.error" class="setup-error" role="alert"><span>!</span>{{ templatePreprocess.error }}</div>
              </section>
              <div v-if="resourceEditor.error" class="setup-error" role="alert"><span>!</span>{{ resourceEditor.error }}</div>
              <div class="main-resource-editor-footer">
                <button type="button" @click="closeResourceEditor">取消</button>
                <button class="primary" type="button" :disabled="resourceEditor.saving || templatePreprocess.busy" @click="saveMainResource">
                  {{ resourceEditor.saving ? "正在写入…" : "写入 CSV 并完成" }}
                </button>
              </div>
            </div>
          </section>

        </section>

      </div>
    </div>
    <TextureProcessorDialog
      :open="textureProcessorOpen"
      :project-id="activeProject?.id || ''"
      :project-path="activeProject?.path || ''"
      :item-name="String(selectedItemRecord.Name || selectedItem?.name || '')"
      @close="textureProcessorOpen = false"
      @exported="handleTextureExported"
    />
  </section>
</template>

<style scoped>
.workbench-view {
  overflow: hidden;
  margin-top: -10px;
  height: calc(100% + 10px);
}

.workbench-scroll {
  height: 100%;
  overflow: auto;
  padding: 0 10px 20px 0;
}

.workbench-onboarding,
.workbench-home {
  display: grid;
  gap: 16px;
  margin-top: 18px;
  padding-bottom: 18px;
}

.workbench-onboarding {
  min-height: 100%;
  place-items: center;
  align-content: center;
  margin-top: 0;
  padding: 18px 0 36px;
}

.setup-card,
.process-board,
.coming-board,
.principles-board {
  border: 2px solid var(--line-strong);
  border-radius: 8px;
  background: rgba(255, 253, 250, .97);
}

.section-kicker {
  color: #58717d;
  font-family: var(--mono);
  font-size: 10px;
  font-weight: 900;
  letter-spacing: .15em;
}

.onboarding-grid {
  display: grid;
  width: min(920px, calc(100% - 32px));
  grid-template-columns: minmax(0, 1fr);
  gap: 16px;
}

.setup-card {
  padding: 25px 28px;
}

.setup-form-card {
  box-shadow: var(--soft-shadow);
}

.setup-card h2,
.process-board h2,
.coming-board h2,
.principles-board h2 {
  margin: 7px 0 0;
  font-size: 21px;
  letter-spacing: -.025em;
}

.section-intro {
  max-width: 620px;
  margin: 8px 0 23px;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.7;
}

.profile-form {
  display: grid;
  gap: 19px;
}

.field-label {
  display: grid;
  gap: 7px;
}

.field-label > span {
  display: flex;
  align-items: center;
  gap: 7px;
  font-weight: 900;
}

.field-label em {
  padding: 2px 5px;
  border: 1px solid #d09aac;
  border-radius: 3px;
  background: #fff0f5;
  color: #a14868;
  font-size: 10px;
  font-style: normal;
  font-weight: 800;
}

.field-label input,
.field-label select {
  height: 44px;
  border: 2px solid #bdb6bc;
  border-radius: 6px;
  padding: 0 12px;
  font-size: 14px;
  box-shadow: inset 0 1px 2px rgba(23, 23, 23, .05);
}

.field-label select {
  background: #fff;
  cursor: pointer;
}

.field-label select:disabled {
  background: #f1f0ef;
  color: #a4a0a0;
  cursor: not-allowed;
}

.field-label input:focus,
.field-label select:focus {
  outline: 2px solid #9ed8ff;
  outline-offset: 1px;
  border-color: var(--line-strong);
}

.field-label small {
  color: var(--muted);
  font-size: 11px;
}

.path-picker {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 116px;
  gap: 8px;
}

.path-picker input {
  color: #52636c;
  font-family: var(--mono);
  font-size: 11px;
  text-overflow: ellipsis;
}

.path-picker button {
  height: 44px;
  box-shadow: 3px 4px 0 #2e2e2e;
}

.setup-error {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 12px;
  border: 1px solid #dfa9ae;
  border-radius: 5px;
  background: #fff1f2;
  color: #9e3b47;
  font-size: 12px;
  line-height: 1.5;
}

.setup-error span {
  display: grid;
  place-items: center;
  width: 18px;
  height: 18px;
  flex: 0 0 18px;
  border: 1px solid currentColor;
  border-radius: 50%;
  font-family: var(--mono);
  font-weight: 900;
}

.form-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 16px;
  margin-top: 3px;
}

.setup-submit {
  min-width: 174px;
  height: 42px;
  box-shadow: 3px 4px 0 #2e2e2e;
}

.button-spinner {
  width: 15px;
  height: 15px;
  display: inline-block;
  border: 2px solid rgba(0, 0, 0, .2);
  border-top-color: #111;
  border-radius: 50%;
  animation: spin .7s linear infinite;
}

.workbench-notice {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 9px 12px;
  border: 1px solid #92c6ae;
  border-radius: 5px;
  background: #effbf4;
  color: #177052;
  font-size: 12px;
  font-weight: 800;
}

.workbench-notice.error {
  border-color: #dfa9ae;
  background: #fff1f2;
  color: #9e3b47;
}

.workbench-notice > span {
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  border: 1px solid currentColor;
  border-radius: 50%;
  font-family: var(--mono);
}

.workbench-notice p { margin: 0; }

.first-project-banner {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 14px;
  padding: 15px 17px;
  border: 2px solid #b98645;
  border-radius: 6px;
  background: linear-gradient(105deg, #fff7d6, #fffdf6);
  box-shadow: 3px 4px 0 rgba(46, 46, 46, .12);
}

.first-project-banner h2 { margin: 5px 0 3px; font-size: 17px; }
.first-project-banner button { min-width: 140px; box-shadow: 3px 4px 0 #2e2e2e; }

.project-prompt-backdrop {
  position: fixed;
  z-index: 30;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(31, 37, 42, .34);
  backdrop-filter: blur(3px);
}

.project-prompt {
  width: min(540px, 100%);
  position: relative;
  overflow: hidden;
  padding: 28px;
  border: 3px solid var(--line-strong);
  border-radius: 8px;
  background: #fffdfa;
  box-shadow: 8px 9px 0 #2e2e2e;
}

.prompt-decoration {
  position: absolute;
  top: 17px;
  right: 22px;
  display: flex;
  gap: 5px;
}

.prompt-decoration span { width: 8px; height: 8px; display: block; border: 1px solid var(--line-strong); border-radius: 50%; background: var(--pink); }
.prompt-decoration span:nth-child(2) { background: var(--teal); }
.prompt-decoration span:nth-child(3) { background: #ffe39a; }
.project-prompt h2 { margin: 9px 0 7px; font-size: 24px; letter-spacing: -.04em; }
.project-prompt .field-label input { height: 42px; }
.project-prompt .field-label em { border-color: #9ec8d3; background: #edf9fc; color: #397283; }
.sims4-fbx-backdrop { z-index: 50; }
.sims4-fbx-prompt { width: min(860px, 100%); max-height: min(88vh, 820px); overflow: auto; background: linear-gradient(145deg, #fffdfa 0%, #f5fcfd 100%); }
.sims4-fbx-modal-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.sims4-fbx-modal-head h2 { margin-bottom: 0; }
.sims4-fbx-close { display: grid; width: 30px; height: 30px; flex: 0 0 30px; place-items: center; padding: 0; border: 1px solid #b9cbd0; border-radius: 50%; background: #fff; color: #5d7d86; box-shadow: none; font-size: 21px; line-height: 1; }
.sims4-fbx-close:hover { border-color: #397283; background: #edf8fb; color: #245b69; }
.sims4-fbx-close:disabled { cursor: wait; opacity: .55; }
.sims4-fbx-fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.sims4-fbx-field { min-width: 0; padding: 12px; border: 1px solid #c8dadd; border-radius: 7px; background: rgba(255, 255, 255, .76); }
.sims4-fbx-path-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 8px; min-width: 0; }
.sims4-fbx-path-row input { min-width: 0; overflow: hidden; color: #426d78; font-family: var(--mono); font-size: 11px; text-overflow: ellipsis; }
.sims4-fbx-path-row button { height: 42px; padding: 0 11px; box-shadow: 2px 3px 0 #2e2e2e; font-size: 10px; white-space: nowrap; }
.sims4-fbx-field small { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sims4-fbx-notice { margin-top: 14px; }
.sims4-fbx-result { display: grid; gap: 10px; margin-top: 16px; overflow: hidden; border: 2px solid #8ebdca; border-radius: 7px; background: rgba(255, 255, 255, .82); }
.sims4-fbx-result-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 13px 14px 0; }
.sims4-fbx-result-head > div { display: grid; gap: 3px; }
.sims4-fbx-result-head span { color: #48636f; font-family: var(--mono); font-size: 10px; font-weight: 900; letter-spacing: .1em; }
.sims4-fbx-result-head h3 { margin: 0; color: #315e6c; font-size: 17px; }
.sims4-fbx-result-head button { height: 30px; padding: 0 10px; box-shadow: 2px 3px 0 #2e2e2e; font-size: 10px; }
.sims4-fbx-result-head button.sims4-fbx-delete-result { display: grid; width: 34px; place-items: center; padding: 0; border-color: #d7a29b; background: #fff4f2; color: #a94940; }
.sims4-fbx-result-head button.sims4-fbx-delete-result:hover { border-color: #b94e44; background: #ffe9e6; color: #8f3028; }
.sims4-fbx-result-head button.sims4-fbx-delete-result:disabled { cursor: wait; opacity: .58; }
.sims4-fbx-delete-result svg { width: 17px; height: 17px; fill: none; stroke: currentColor; stroke-linecap: round; stroke-linejoin: round; stroke-width: 1.8; }
.sims4-fbx-result-summary { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; padding: 0 14px; }
.sims4-fbx-result-summary > div { display: grid; gap: 2px; padding: 8px 9px; border: 1px solid #d4e1e3; border-radius: 4px; background: #fbfefe; }
.sims4-fbx-result-summary span { color: #71888e; font-size: 10px; }
.sims4-fbx-result-summary strong { color: #315e6c; font-family: var(--mono); font-size: 17px; }
.sims4-fbx-result-path { display: block; overflow: hidden; margin: 0 14px; color: #53737d; font-family: var(--mono); font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
.sims4-fbx-result-list { display: grid; border-top: 1px solid #d8e5e6; }
.sims4-fbx-result-row { display: grid; grid-template-columns: 42px minmax(0, 1fr) auto; gap: 10px; align-items: center; min-width: 0; padding: 10px 14px; }
.sims4-fbx-result-row + .sims4-fbx-result-row { border-top: 1px solid #e1eaeb; }
.sims4-fbx-result-row:hover { background: #f4fbfd; }
.sims4-fbx-file-mark { display: grid; width: 40px; height: 32px; place-items: center; border: 1px solid #8ebdca; border-radius: 4px; background: #edf8fb; color: #397283; font-family: var(--mono); font-size: 10px; font-weight: 900; }
.sims4-fbx-file-copy { display: grid; gap: 3px; min-width: 0; }
.sims4-fbx-file-copy strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sims4-fbx-file-copy strong { color: #315e6c; font-size: 11px; }
.sims4-fbx-result-actions { display: flex; align-items: center; gap: 7px; }
.sims4-fbx-result-actions button { min-height: 30px; padding: 0 9px; border-radius: 4px; box-shadow: none; font-size: 10px; white-space: nowrap; }
.sims4-fbx-result-actions button:first-child { border-color: #8ebdca; background: #edf8fb; color: #315e6c; }
.sims4-fbx-result-actions button:first-child:hover { border-color: #397283; background: #e2f3f7; }
.sims4-fbx-result-actions button:last-child { border-color: #c2cdd0; background: #fff; color: #5d747b; }
.sims4-fbx-result-actions button:disabled { cursor: wait; opacity: .58; }
.sims4-fbx-actions { margin-top: 20px; }
.fbx-transform-backdrop { z-index: 54; }
.fbx-transform-prompt { background: linear-gradient(145deg, #fffdfa 0%, #f3f9fd 100%); }
.fbx-transform-description { margin-bottom: 12px; }
.fbx-transform-source-row { border-color: #aacbd5; background: #f4fbfd; }
.fbx-transform-source-row strong { color: #315e6c; }
.fbx-transform-source-row code { color: #567985; }
.fbx-skin-backdrop { z-index: 55; }
.fbx-skin-prompt { width: min(680px, 100%); max-height: min(88vh, 760px); overflow: auto; background: linear-gradient(145deg, #fffdfa 0%, #f4fbf8 100%); }
.fbx-skin-modal-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.fbx-skin-modal-head h2 { margin-bottom: 0; }
.fbx-skin-description { margin: 2px 0 15px; color: #5f7379; font-size: 11px; line-height: 1.6; }
.fbx-skin-source-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 12px; align-items: center; padding: 12px; border: 1px solid #b9d5c5; border-radius: 7px; background: #f5fcf7; }
.fbx-skin-source-row > div { display: grid; gap: 4px; min-width: 0; }
.fbx-skin-source-row strong,.fbx-skin-source-row code { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fbx-skin-source-row strong { color: #2f6754; font-size: 13px; }
.fbx-skin-source-row code { color: #5b8475; font-family: var(--mono); font-size: 10px; }
.fbx-skin-source-row button { height: 36px; padding: 0 11px; box-shadow: 2px 3px 0 #2e2e2e; font-size: 10px; white-space: nowrap; }
.fbx-skin-backup-toggle { display: flex; align-items: flex-start; gap: 9px; margin-top: 11px; padding: 9px 11px; border: 1px solid #d4e3d9; border-radius: 5px; background: #fbfffc; cursor: pointer; }
.fbx-skin-backup-toggle input { width: 15px; height: 15px; flex: 0 0 15px; margin: 1px 0 0; accent-color: #4e9a7d; }
.fbx-skin-backup-toggle span { display: grid; gap: 3px; }
.fbx-skin-backup-toggle strong { color: #396d59; font-size: 11px; }
.fbx-skin-backup-toggle small { color: #71888e; font-size: 10px; line-height: 1.4; }
.fbx-skin-backup-toggle code { color: #537d6b; font-family: var(--mono); }
.fbx-skin-notice { margin-top: 14px; }
.fbx-skin-result { display: grid; gap: 10px; margin-top: 15px; padding: 13px 14px; border: 2px solid #8ebdca; border-radius: 7px; background: rgba(255, 255, 255, .82); }
.fbx-skin-result-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.fbx-skin-result-head > div { display: grid; gap: 3px; }
.fbx-skin-result-head span { color: #48636f; font-family: var(--mono); font-size: 10px; font-weight: 900; letter-spacing: .1em; }
.fbx-skin-result-head h3 { margin: 0; color: #315e6c; font-size: 17px; }
.fbx-skin-result-head button { height: 30px; padding: 0 10px; box-shadow: 2px 3px 0 #2e2e2e; font-size: 10px; }
.fbx-skin-result > code { overflow: hidden; color: #53737d; font-family: var(--mono); font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
.fbx-skin-backup-path { overflow: hidden; color: #71888e; font-family: var(--mono); font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
.fbx-transform-alignment-status { display: grid; gap: 4px; padding: 9px 10px; border: 1px solid #cbdfe3; border-radius: 5px; background: #f8fcfd; }
.fbx-transform-alignment-status strong { font-size: 11px; }
.fbx-transform-alignment-status span { overflow: hidden; color: #71888e; font-family: var(--mono); font-size: 10px; line-height: 1.4; text-overflow: ellipsis; white-space: nowrap; }
.fbx-transform-alignment-status.repaired { border-color: #a7d2be; background: #f2fbf5; }
.fbx-transform-alignment-status.repaired strong { color: #2f6754; }
.fbx-transform-alignment-status.warning { border-color: #e0c18d; background: #fff9ee; }
.fbx-transform-alignment-status.warning strong { color: #8a6331; }
.fbx-transform-alignment-status.clean strong { color: #315e6c; }
.hs2-skeleton-backdrop { z-index: 56; }
.hs2-skeleton-fields { display: grid; gap: 10px; }
.hs2-skeleton-reference-row { border-color: #c8c0d8; background: #fbf9ff; }
.hs2-skeleton-reference-row strong { color: #62517f; }
.hs2-skeleton-reference-row code { color: #7a6c95; }
.hs2-skeleton-reference-row button { border-color: #a69bc1; background: #f5f1ff; color: #5e4d7c; }
.hs2-skeleton-reference-row button:hover:not(:disabled) { border-color: #756496; background: #eee8ff; }
.fbx-skin-result-summary { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
.fbx-transform-result-summary { grid-template-columns: repeat(5, minmax(0, 1fr)); }
.hs2-skeleton-result-summary { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.fbx-weight-backdrop { z-index: 57; }
.fbx-weight-source-row { border-color: #d7c2b1; background: #fffaf5; }
.fbx-weight-source-row strong { color: #805d3e; }
.fbx-weight-source-row code { color: #98765a; }
.fbx-weight-source-row button { border-color: #c9a984; background: #fff5e9; color: #7d5a39; }
.fbx-weight-source-row button:hover:not(:disabled) { border-color: #a97b4f; background: #ffecd4; }
.fbx-weight-result-summary { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.fbx-skin-result-summary > div { display: grid; gap: 2px; padding: 8px 9px; border: 1px solid #d4e1e3; border-radius: 4px; background: #fbfefe; }
.fbx-skin-result-summary span { color: #71888e; font-size: 10px; }
.fbx-skin-result-summary strong { color: #315e6c; font-family: var(--mono); font-size: 17px; }
.fbx-skin-actions { margin-top: 18px; }
.package-success-backdrop { z-index: 60; }
.package-success-prompt { width: min(500px, 100%); background: linear-gradient(145deg, #fffdfa 0%, #f3fbf6 100%); }
.package-success-prompt h2 { color: #24694f; }
.package-success-detail { display: grid; gap: 5px; padding: 12px 13px; border: 1px solid #b9d5c5; border-radius: 6px; background: #f0fbf4; color: #56806e; }
.package-success-detail strong { overflow: hidden; color: #24694f; font-family: var(--mono); font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.package-success-detail span { font-size: 11px; }
.package-success-error { margin-top: 14px; }
.prompt-actions { display: flex; justify-content: flex-end; gap: 9px; margin-top: 20px; }
.prompt-actions button { min-width: 108px; height: 40px; }
.prompt-actions .primary { min-width: 174px; box-shadow: 3px 4px 0 #2e2e2e; }
.delete-confirm-backdrop { z-index: 40; }
.delete-confirm-prompt { width: min(520px, 100%); }
.delete-confirm-prompt h2 { margin-bottom: 8px; }
.delete-confirm-message { margin: 0; color: #315f69; font-size: 15px; font-weight: 900; }
.delete-confirm-detail { display: flex; align-items: flex-start; gap: 9px; margin-top: 17px; padding: 11px 12px; border: 1px solid #d9a5ad; border-radius: 5px; background: #fff3f4; color: #8f3f4d; }
.delete-confirm-detail > span { display: grid; width: 18px; height: 18px; flex: 0 0 18px; place-items: center; border: 1px solid currentColor; border-radius: 50%; font-family: var(--mono); font-size: 11px; font-weight: 900; }
.delete-confirm-detail p { margin: 0; font-size: 12px; line-height: 1.55; }
.prompt-actions .delete-confirm-action { min-width: 108px; border-color: #b45d6a; background: #b45d6a; color: #fff; box-shadow: 3px 4px 0 #2e2e2e; }
.prompt-actions .delete-confirm-action:hover { border-color: #963d4c; background: #963d4c; }

.board-head,
.board-head.compact {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}

.route-progress,
.shelf-count {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: #177052;
  font-family: var(--mono);
  font-size: 10px;
  font-weight: 900;
  white-space: nowrap;
}

.project-board {
  padding: 18px 21px;
  border: 2px solid var(--line-strong);
  border-radius: 8px;
  background: #fff;
}
.project-board.is-project-space,
.project-board.is-project-list-open { position: relative; display: block; padding: 0; border: 0; background: transparent; box-shadow: none; }
.project-board.is-project-list-open > .board-head { order: 0; }
.project-board.is-project-list-open > .project-workbench-toolbar-floating { order: 1; margin: 0; }
.project-board.is-project-list-open > .project-list { position: absolute; top: calc(100% + 7px); right: 0; left: 0; z-index: 30; display: grid; max-height: min(360px, calc(100vh - 180px)); margin-top: 0; padding: 8px; overflow-y: auto; border: 1px solid #8ebdca; border-radius: 7px; background: rgba(255, 255, 255, .98); box-shadow: 3px 4px 0 rgba(46, 46, 46, .16); backdrop-filter: blur(8px); }

.project-board .board-head h2 { margin-top: 5px; }
.project-board .board-head > button,
.project-board-actions > button { height: 32px; padding: 0 11px; box-shadow: 2px 3px 0 #2e2e2e; font-size: 11px; }
.project-board-actions { display: flex; align-items: center; gap: 8px; }
.project-search-control { display: inline-flex; position: relative; min-width: 150px; height: 28px; align-items: center; gap: 6px; padding: 0 8px; border: 1px solid #9fc2cc; border-radius: 4px; background: #fff; color: #53737d; box-shadow: 1px 2px 0 rgba(46, 46, 46, .12); }
.project-search-control:focus-within { border-color: #397283; outline: 2px solid rgba(117, 170, 184, .2); }
.project-search-control svg { width: 14px; height: 14px; flex: 0 0 14px; fill: none; stroke: currentColor; stroke-linecap: round; stroke-linejoin: round; stroke-width: 1.8; }
.project-search-control input { width: 100%; min-width: 0; height: 24px; padding: 0; border: 0; outline: 0; background: transparent; color: #315e6c; font-size: 10px; }
.project-search-control input::placeholder { color: #8ba8b0; }
.project-search-control input::-webkit-search-cancel-button { cursor: pointer; }
.project-search-count { min-width: 17px; padding: 2px 4px; border-radius: 3px; background: #e8f7f9; color: #397283; font-family: var(--mono); font-size: 9px; font-weight: 900; line-height: 1.2; text-align: center; }
.project-search-control-board { flex: 1 1 190px; max-width: 280px; }
.project-list-toggle { border-color: #9ec8d3; background: #f2fbfd; color: #315e6c; }
.project-list-toggle:hover { border-color: #397283; background: #e7f7fa; color: #245b69; }
.project-list { display: grid; gap: 8px; margin-top: 15px; }
.project-list-collapsed { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 15px; padding: 11px 12px; border: 1px dashed #a9c4ca; border-radius: 5px; background: #f7fcfd; color: #53737d; font-size: 11px; }
.project-list-collapsed > div { display: grid; gap: 3px; min-width: 0; }
.project-list-collapsed strong { color: #315e6c; font-size: 12px; }
.project-list-collapsed span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.project-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: 10px; padding: 9px 10px; border: 1px solid #ddd7d4; border-radius: 5px; background: #fffdfb; cursor: pointer; transition: border-color .16s ease, background .16s ease, transform .16s ease, box-shadow .16s ease; }
.project-row:hover { border-color: #9cc2cf; background: #f8fcff; transform: translateY(-1px); }
.project-row:focus-visible { outline: 2px solid #78b9d4; outline-offset: 2px; }
.project-row.is-current { border-color: #72b79a; background: #f1fcf5; }
.project-row-copy { min-width: 0; display: grid; gap: 3px; }
.project-row-copy strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; }
.project-row-copy code { color: #53737d; font-family: var(--mono); font-size: 10px; }
.project-list-empty { padding: 17px 12px; border: 1px dashed #a9c4ca; border-radius: 5px; background: #f7fcfd; color: #6b8790; font-size: 11px; text-align: center; }
.project-row > button { height: 31px; padding: 0 10px; box-shadow: 2px 3px 0 #2e2e2e; font-size: 10px; }
.workbench-delete-button {
  display: inline-grid;
  width: 31px;
  height: 31px;
  place-items: center;
  padding: 0 !important;
  border: 1px solid #c8929b;
  border-radius: 4px;
  background: #fff5f6;
  color: #a24858;
  box-shadow: 2px 3px 0 #2e2e2e;
}
.workbench-delete-button svg { width: 16px; height: 16px; fill: none; stroke: currentColor; stroke-linecap: round; stroke-linejoin: round; stroke-width: 1.8; }
.workbench-delete-button:hover { border-color: #a24858; background: #ffe8eb; color: #8f3042; }
.workbench-delete-button:focus-visible { outline: 2px solid #78b9d4; outline-offset: 2px; }
.workbench-delete-button:disabled { cursor: wait; opacity: .55; }

.item-browser { padding: 18px 21px 21px; border: 2px solid #b8c7cd; border-radius: 8px; background: #fff; }
.item-browser-head { align-items: center; }
.item-browser-head h2 { margin: 5px 0 3px; font-size: 19px; }
.item-browser-head p { margin: 0; color: var(--muted); font-size: 11px; }
.item-browser-head p code { color: #53737d; font-family: var(--mono); }
.item-browser-actions { display: flex; align-items: center; gap: 12px; }
.item-browser-actions button { height: 32px; padding: 0 12px; box-shadow: 2px 3px 0 #2e2e2e; font-size: 11px; }
.item-browser-state { padding: 28px 12px; color: var(--muted); font-size: 12px; text-align: center; }
.item-list { display: grid; gap: 8px; margin-top: 17px; }
.item-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: 10px; padding: 9px 10px; border: 1px solid #ddd7d4; border-radius: 5px; background: #fffdfb; cursor: pointer; transition: border-color .16s ease, background .16s ease, transform .16s ease, box-shadow .16s ease; }
.item-row:hover { border-color: #9cc2cf; background: #f8fcff; }
.item-row:focus-visible { outline: 2px solid #78b9d4; outline-offset: 2px; }
.item-row.is-selected { border-color: #72b79a; background: #f1fcf5; box-shadow: inset 4px 0 0 #34ad8a; }
.item-row-copy { min-width: 0; display: grid; gap: 3px; }
.item-row-copy strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; }
.item-row-copy code { color: #53737d; font-family: var(--mono); font-size: 9px; }
.item-row > button { height: 31px; padding: 0 10px; box-shadow: 2px 3px 0 #2e2e2e; font-size: 10px; }
.item-workspace { display: grid; gap: 16px; padding: 20px 20px 22px; border: 2px solid #8ebdca; border-radius: 8px; background: linear-gradient(145deg, #fff 0%, #f6fbfd 58%, #fff8fb 100%); }
.item-workspace-head { display: grid; gap: 14px; padding: 0 0 16px; border-bottom: 1px solid #d7e7eb; }
.item-workspace-topbar { display: flex; align-items: center; justify-content: space-between; gap: 18px; min-height: 34px; }
.item-workspace-content { display: grid; grid-template-columns: 130px minmax(0, 1fr); align-items: end; gap: 10px; }
.item-workspace-heading { display: flex; grid-column: 2; grid-row: 1; min-width: 0; flex-direction: column; justify-content: center; padding: 4px 0 2px; }
.workspace-back { display: block; width: fit-content; margin: 0; padding: 0; border: 0; background: transparent; box-shadow: none; color: #3f7180; font-family: var(--mono); font-size: 13px; font-weight: 900; letter-spacing: .02em; text-transform: uppercase; }
.workspace-back:hover { color: #244f5b; text-decoration: underline; }
.item-workspace-heading h2 { margin: 0; font-size: 25px; line-height: 1.05; letter-spacing: -.04em; }
.item-name-input { display: block; width: min(100%, 560px); min-width: 0; margin: 0; padding: 0 4px 6px; border: 1px solid transparent; border-radius: 4px; background: transparent; color: var(--text); font-family: inherit; font-size: 30px; font-weight: 900; line-height: 1.05; letter-spacing: -.05em; }
.item-name-input:hover { border-color: #b6d1d8; background: rgba(255, 255, 255, .72); }
.item-name-input:focus { border-color: #75aab8; background: #fff; outline: 2px solid rgba(117, 170, 184, .2); }
.item-name-input:disabled { cursor: wait; opacity: .65; }
.item-workspace-thumbnail { position: relative; display: flex; grid-column: 1; grid-row: 1; width: 130px; aspect-ratio: 1 / 1; min-width: 0; min-height: 0; height: auto; align-items: center; justify-self: start; overflow: hidden; padding: 14px 5px 5px; border: 0; border-radius: 0; background: transparent; box-shadow: none; }
.item-workspace-thumbnail-state { display: flex; width: auto; align-items: center; justify-content: center; gap: 8px; color: #6b8790; font-family: var(--mono); font-size: 10px; }
.item-workspace-thumbnail-preview { display: flex; width: 100%; height: 100%; min-width: 0; align-items: center; justify-content: center; gap: 11px; padding: 0; border: 0; border-radius: 4px; background: transparent; box-shadow: none; }
.item-workspace-thumbnail-preview:not(:disabled) { cursor: pointer; }
.item-workspace-thumbnail-preview:hover:not(:disabled) img { border-color: #397283; box-shadow: 2px 3px 0 rgba(46, 46, 46, .18); transform: translateY(-1px); }
.item-workspace-thumbnail-preview:focus-visible { outline: 2px solid #75aab8; outline-offset: 2px; }
.item-workspace-thumbnail-preview:disabled { cursor: wait; opacity: .62; }
.item-workspace-thumbnail-preview img { display: block; width: 100%; height: 100%; max-width: 220px; max-height: 220px; flex: 0 1 auto; object-fit: cover; border: 1px solid #8db3bd; border-radius: 4px; background: #fff; box-shadow: 2px 3px 0 rgba(46, 46, 46, .12); }
.item-workspace-thumbnail-copy { display: grid; min-width: 0; gap: 3px; }
.item-workspace-thumbnail-kicker { color: #6b8d96; font-family: var(--mono); font-size: 9px; font-weight: 900; letter-spacing: .08em; }
.item-workspace-thumbnail-copy strong { color: #315e6c; font-size: 12px; }
.item-workspace-thumbnail-copy small { overflow: hidden; color: #78929a; font-family: var(--mono); font-size: 9px; text-overflow: ellipsis; white-space: nowrap; }
.workbench-thumbnail-build { display: flex; width: 100%; height: 100%; min-width: 0; max-width: none; min-height: 0; align-items: center; justify-content: center; gap: 10px; padding: 8px 12px; border: 1px dashed #79aebc; border-radius: 5px; background: rgba(255, 255, 255, .65); color: #397283; text-align: left; box-shadow: none; }
.workbench-thumbnail-build:hover:not(:disabled) { border-color: #397283; background: #e8f7f9; color: #245b69; transform: translateY(-1px); }
.workbench-thumbnail-build:disabled { cursor: wait; opacity: .62; }
.workbench-thumbnail-build svg { width: 27px; height: 27px; flex: 0 0 27px; fill: none; stroke: currentColor; stroke-linecap: round; stroke-linejoin: round; stroke-width: 1.6; }
.item-workspace-actions { display: flex; min-width: 154px; align-items: center; justify-content: flex-end; gap: 8px; flex-direction: row; }
.workspace-status { padding: 5px 8px; border: 1px solid #9fcbb3; border-radius: 4px; background: #effbf4; color: #25805d; font-family: var(--mono); font-size: 10px; font-weight: 900; letter-spacing: .05em; white-space: nowrap; }
.item-workspace-actions button { height: 34px; width: auto; padding: 0 12px; border-radius: 5px; background: #fff; box-shadow: 2px 3px 0 #2e2e2e; font-size: 11px; }
.project-workbench-toolbar,
.item-workbench-toolbar { display: flex; align-items: center; gap: 18px; min-height: 58px; padding: 10px 14px; border-radius: 7px; }
.project-workbench-toolbar { margin-top: 15px; border: 1px solid #8ebdca; background: #f5fcfd; }
.project-workbench-toolbar-floating { position: sticky; top: 10px; z-index: 12; min-height: 42px; gap: 10px; margin: 0; padding: 6px 10px; border-color: #79aebc; background: rgba(245, 252, 253, .94); box-shadow: 2px 3px 0 rgba(46, 46, 46, .16); backdrop-filter: blur(8px); }
.item-workbench-toolbar { border: 1px solid #c9dfe3; background: rgba(255, 255, 255, .68); }
.item-workbench-toolbar--project { order: 1; min-width: 0; min-height: 27px; gap: 8px; margin: 0; padding: 0 0 0 10px; border: 0; border-left: 1px solid #d7e7eb; border-radius: 0; background: transparent; }
.project-workbench-toolbar-label,
.item-workbench-toolbar-label { display: grid; flex: 0 0 auto; gap: 3px; min-width: 112px; }
.project-workbench-toolbar-kicker { color: #6b8d96; font-family: var(--mono); font-size: 9px; font-weight: 900; letter-spacing: .08em; }
.project-workbench-toolbar-label strong,
.item-workbench-toolbar-label strong { color: #315e6c; font-size: 14px; line-height: 1; }
.project-workbench-toolbar-tools,
.item-workbench-toolbar-tools { display: flex; flex: 1 1 auto; align-items: center; min-height: 34px; padding-left: 16px; border-left: 1px solid #d7e7eb; }
.project-workbench-toolbar-tools { gap: 10px; }
.item-workbench-toolbar-tools { gap: 8px; }
.item-workbench-toolbar--project .item-workbench-toolbar-label { min-width: 72px; gap: 0; }
.item-workbench-toolbar--project .item-workbench-toolbar-label strong { font-size: 10px; white-space: nowrap; }
.item-workbench-toolbar--project .item-workbench-toolbar-tools { min-height: 27px; padding-left: 0; border-left: 0; }
.project-workbench-toolbar-floating .project-workbench-toolbar-label { min-width: 92px; gap: 2px; }
.project-workbench-toolbar-floating .project-workbench-toolbar-label strong { font-size: 12px; }
.project-workbench-toolbar-floating .project-workbench-toolbar-label small { overflow: hidden; color: #78929a; font-size: 9px; text-overflow: ellipsis; white-space: nowrap; }
.project-workbench-toolbar-floating .project-workbench-toolbar-tools { min-height: 27px; padding-left: 10px; }
.project-workbench-toolbar-floating .project-search-control { order: 2; flex: 0 0 280px; width: 280px; min-width: 0; max-width: 280px; margin-left: auto; }
.project-workbench-toolbar-floating .workbench-tool-button { order: 1; }
.project-workbench-toolbar-floating .project-workbench-context-button { order: 2; }
.project-workbench-toolbar-floating .project-workbench-context-button:not(.project-list-toggle-control) { order: 0; }
.project-workbench-toolbar-floating .project-workbench-context-button:first-child { order: 3; margin-left: auto; }
.project-workbench-toolbar-floating .project-workbench-context-button.project-list-toggle-control:first-child { order: 3; margin-left: 0; }
.project-workbench-context-button { height: 28px; padding: 0 9px; border: 1px solid #9fc2cc; border-radius: 4px; background: #fff; color: #315e6c; box-shadow: 1px 2px 0 rgba(46, 46, 46, .16); font-size: 10px; font-weight: 800; white-space: nowrap; }
.project-workbench-context-button:hover { border-color: #397283; background: #eaf8fa; color: #245b69; }
.project-workbench-context-button:focus-visible { outline: 2px solid #78b9d4; outline-offset: 1px; }
.project-list-toggle-control { display: inline-flex; min-width: 30px; align-items: center; justify-content: center; padding: 0; }
.project-list-toggle-icon { width: 15px; height: 15px; fill: none; stroke: currentColor; stroke-linecap: round; stroke-linejoin: round; stroke-width: 2; transition: transform .16s ease; }
.project-list-toggle-icon.is-expanded { transform: rotate(180deg); }
.project-workbench-toolbar-floating .workbench-tool-button { height: 28px; padding: 0 9px; font-size: 10px; }
.project-workbench-toolbar-floating .workbench-tool-button svg { width: 14px; height: 14px; }
.item-workbench-toolbar-empty { color: #78929a; font-size: 11px; }
.item-workbench-toolbar .workbench-tool-button { width: 36px; min-width: 36px; justify-content: center; gap: 0; padding: 0; }
.item-workbench-toolbar .workbench-tool-button svg { width: 17px; height: 17px; }
.workbench-tool-button { display: inline-flex; align-items: center; gap: 7px; height: 34px; padding: 0 12px; border: 1px solid #75aab8; border-radius: 5px; background: #f1fafc; color: #315e6c; box-shadow: 2px 2px 0 #2e2e2e; font-size: 11px; font-weight: 900; }
.workbench-tool-button:hover:not(:disabled) { border-color: #397283; background: #e5f5f8; }
.workbench-tool-button:disabled { cursor: wait; opacity: .58; }
.workbench-tool-button svg { width: 16px; height: 16px; fill: none; stroke: currentColor; stroke-linecap: round; stroke-linejoin: round; stroke-width: 1.7; }
.item-resource-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.item-resource-card { min-width: 0; padding: 0 15px 13px; border: 1px solid #d1dfe2; border-radius: 7px; background: linear-gradient(145deg, #fff, #fafdfe); }
.item-resource-card.is-texture { background: linear-gradient(145deg, #fff, #fffafd); }
.item-resource-card h3 { margin: 0 -15px 2px; padding: 12px 15px 9px; border-bottom: 1px solid #dfe7e8; color: #315e6c; font-size: 18px; line-height: 1; }
.item-resource-card-title { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin: 0 -15px 2px; padding: 0 15px; border-bottom: 1px solid #dfe7e8; }
.item-resource-card-title h3 { min-width: 0; flex: 1 1 auto; margin: 0; padding: 12px 0 9px; border-bottom: 0; }
.texture-group-add-button { display: inline-grid; width: 26px; height: 26px; flex: 0 0 26px; place-items: center; padding: 0; border: 1px solid #75aab8; border-radius: 4px; background: #f1fafc; color: #397283; box-shadow: none; }
.texture-group-add-button svg { width: 15px; height: 15px; fill: none; stroke: currentColor; stroke-linecap: round; stroke-width: 2; }
.texture-group-add-button:hover { border-color: #397283; background: #e2f3f7; color: #245b69; }
.texture-group-add-button:focus-visible { outline: 2px solid #78b9d4; outline-offset: 1px; }
.texture-group-add-button:disabled { cursor: wait; opacity: .58; }
.texture-group-list { display: grid; gap: 2px; }
.texture-group { min-width: 0; padding: 8px 0 2px; }
.texture-group + .texture-group { padding-top: 11px; border-top: 1px solid #e4e9e9; }
.texture-group-heading { display: flex; align-items: center; justify-content: space-between; gap: 10px; min-height: 20px; margin-bottom: 2px; color: #6a858c; font-family: var(--mono); font-size: 10px; font-weight: 900; }
.texture-group-remove-button { display: inline-grid; width: 22px; height: 22px; flex: 0 0 22px; place-items: center; padding: 0; border: 1px solid #d8a4ab; border-radius: 3px; background: #fff5f6; color: #a24858; box-shadow: none; }
.texture-group-remove-button svg { width: 14px; height: 14px; fill: none; stroke: currentColor; stroke-linecap: round; stroke-linejoin: round; stroke-width: 1.7; }
.texture-group-remove-button:hover { border-color: #a24858; background: #ffe8eb; color: #8f3042; }
.texture-group-remove-button:focus-visible { outline: 2px solid #e1a0a8; outline-offset: 1px; }
.texture-group-remove-button:disabled { cursor: wait; opacity: .58; }
.item-resource-card dl { display: grid; gap: 6px; margin: 0; }
.resource-field { display: grid; grid-template-columns: minmax(86px, .75fr) minmax(0, 1.25fr); gap: 10px; align-items: start; padding-top: 8px; border-top: 1px dashed #dfe4e2; }
.resource-field dt { color: #52666d; font-family: var(--mono); font-size: 12px; font-weight: 800; }
.resource-field-value { min-width: 0; display: flex; align-items: center; gap: 8px; overflow: hidden; margin: 0; color: #204f5b; font-family: var(--mono); font-size: 13px; font-weight: 700; }
.resource-field-value > span { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.resource-field-value > span.is-empty { color: #8d747b; font-family: var(--mono); font-style: normal; }
.resource-field-input { min-width: 0; width: 100%; height: 25px; padding: 2px 5px; border: 1px solid transparent; border-radius: 3px; background: transparent; color: inherit; font: inherit; }
.resource-field-input::placeholder { color: #8d747b; opacity: 1; }
.resource-field-input:hover { border-color: #c4d9dc; background: #fbfefe; }
.resource-field-input:focus { outline: 2px solid #9ed8ff; outline-offset: 1px; border-color: #75aab8; background: #fff; }
.resource-field-input:disabled { cursor: wait; opacity: .58; }
.resource-field-link { min-width: 0; display: flex; align-items: center; overflow: hidden; padding: 0; border: 0; background: transparent; box-shadow: none; color: inherit; font: inherit; text-align: left; }
.resource-field-link > span { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.resource-field-link:hover { color: #176347; text-decoration: underline; }
.resource-field-link:focus-visible { outline: 2px solid #78b9d4; outline-offset: 2px; border-radius: 2px; }
.resource-field-link:disabled { cursor: wait; opacity: .58; }
.main-resource-existing-select { min-width: 0; width: 100%; height: 29px; padding: 3px 27px 3px 7px; border: 1px solid #b8d2d8; border-radius: 4px; background: #f7fcfd; color: #204f5b; font-family: var(--mono); font-size: 11px; font-weight: 800; text-overflow: ellipsis; }
.main-resource-existing-select:hover { border-color: #75aab8; background: #fff; }
.main-resource-existing-select:focus { outline: 2px solid #9ed8ff; outline-offset: 1px; border-color: #4f94a5; background: #fff; }
.main-resource-existing-select:disabled { cursor: wait; opacity: .58; }
.main-resource-open-button { display: inline-grid; width: 24px; height: 24px; flex: 0 0 24px; place-items: center; padding: 0; border: 1px solid #75aab8; border-radius: 4px; background: #f1fafc; color: #397283; box-shadow: none; }
.main-resource-open-button svg { width: 14px; height: 14px; fill: none; stroke: currentColor; stroke-linecap: round; stroke-linejoin: round; stroke-width: 1.8; }
.main-resource-open-button:hover:not(:disabled) { border-color: #397283; background: #e2f3f7; color: #245b69; }
.main-resource-open-button:focus-visible { outline: 2px solid #78b9d4; outline-offset: 1px; }
.main-resource-open-button:disabled { cursor: wait; opacity: .58; }
.main-resource-add-button { display: inline-grid; width: 24px; height: 24px; flex: 0 0 24px; place-items: center; padding: 0; border: 1px solid #76b99a; border-radius: 50%; background: #effbf4; color: #25805d; box-shadow: 1px 2px 0 rgba(46, 46, 46, .18); }
.main-resource-add-button svg { width: 15px; height: 15px; fill: none; stroke: currentColor; stroke-linecap: round; stroke-width: 2; }
.main-resource-add-button:hover { border-color: #25805d; background: #dff5e9; color: #176347; }
.main-resource-add-button:focus-visible { outline: 2px solid #78b9d4; outline-offset: 2px; }
.resource-field-check { display: inline-grid; width: 16px; height: 16px; flex: 0 0 16px; place-items: center; border: 1px solid currentColor; border-radius: 50%; font-family: var(--mono); font-size: 10px; font-weight: 900; line-height: 1; }
.resource-field-check.is-found { color: #25805d; background: #effbf4; }
.resource-field-check.is-missing { color: #a24858; background: #fff1f2; }
.texture-import-button { flex: 0 0 auto; height: 22px; padding: 0 7px; border: 1px solid #75aab8; border-radius: 3px; background: #f1fafc; color: #397283; box-shadow: none; font-size: 10px; font-weight: 800; }
.texture-import-button:hover { border-color: #397283; background: #e2f3f7; color: #245b69; }
.texture-import-button:focus-visible { outline: 2px solid #78b9d4; outline-offset: 1px; }
.texture-import-button:disabled { cursor: wait; opacity: .58; }
.texture-replace-button { display: inline-grid; width: 25px; height: 22px; flex: 0 0 25px; place-items: center; padding: 0; border: 1px solid #75aab8; border-radius: 3px; background: #f1fafc; color: #397283; box-shadow: none; }
.texture-replace-button svg { width: 15px; height: 15px; fill: none; stroke: currentColor; stroke-linecap: round; stroke-linejoin: round; stroke-width: 1.8; }
.texture-replace-button:hover:not(:disabled) { border-color: #397283; background: #e2f3f7; color: #245b69; }
.texture-replace-button:focus-visible { outline: 2px solid #78b9d4; outline-offset: 1px; }
.texture-replace-button:disabled { cursor: wait; opacity: .58; }
.texture-replace-button.is-busy svg { animation: workbench-texture-replace-spin .8s linear infinite; }
@keyframes workbench-texture-replace-spin { to { transform: rotate(180deg); } }
.main-resource-check { display: flex; align-items: center; gap: 8px; min-height: 30px; padding: 6px 10px; border: 1px solid #c8dcdf; border-radius: 5px; background: #f8fcfd; color: #456a73; font-size: 11px; font-weight: 800; }
.main-resource-check-dot { width: 8px; height: 8px; flex: 0 0 8px; border-radius: 50%; background: currentColor; }
.main-resource-check.is-checking { color: #397283; }
.main-resource-check.is-checking .main-resource-check-dot { animation: pulse 1s ease-in-out infinite; }
.main-resource-check.is-ready { border-color: #9fcbb3; background: #effbf4; color: #25805d; }
.main-resource-check.is-incomplete { border-color: #c8dcdf; background: #f8fcfd; color: #53737d; }
.main-resource-check.is-missing_file,
.main-resource-check.is-main_data_missing,
.main-resource-check.is-texture_missing,
.main-resource-check.is-unreadable { border-color: #dfa9ae; background: #fff1f2; color: #9e3b47; }
.workbench-preview-row { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; min-width: 0; }
.workbench-item-preview { display: grid; align-self: start; align-content: start; width: 100%; min-width: 0; max-width: 100%; gap: 10px; padding: 12px; border: 1px solid #9fc2cc; border-radius: 7px; background: linear-gradient(155deg, rgba(255, 255, 255, .96), rgba(240, 249, 251, .9)); box-shadow: 3px 4px 0 rgba(46, 46, 46, .08); }
.workbench-item-preview-head { display: flex; align-items: center; justify-content: space-between; gap: 14px; padding: 1px 2px 0; }
.workbench-item-preview-head > div:first-child { min-width: 0; display: block; }
.workbench-item-preview-head > div:first-child > span { grid-column: 1; color: #6b8d96; font-family: var(--mono); font-size: 9px; font-weight: 900; letter-spacing: .09em; }
.workbench-item-preview-head h3 { grid-column: auto; margin: 0; color: #315e6c; font-size: 15px; }
.workbench-item-preview-head small { grid-column: 1 / -1; min-width: 0; margin-top: 3px; overflow: hidden; color: #78929a; font-family: var(--mono); font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
.workbench-item-preview-actions { display: flex; flex: 0 0 auto; align-items: center; gap: 7px; }
.workbench-preview-state { padding: 4px 6px; border: 1px solid #b5cbd1; border-radius: 3px; background: #f5fafb; color: #728b92; font-family: var(--mono); font-size: 8px; font-weight: 900; letter-spacing: .08em; }
.workbench-preview-state.is-ready { border-color: #8fc8ad; background: #effbf4; color: #25805d; }
.workbench-preview-refresh { display: inline-grid; width: 29px; height: 29px; place-items: center; padding: 0; border: 1px solid #75aab8; border-radius: 4px; background: #f1fafc; color: #397283; box-shadow: 1px 2px 0 rgba(46, 46, 46, .16); }
.workbench-preview-refresh:hover { border-color: #397283; background: #e2f3f7; color: #245b69; }
.workbench-preview-refresh:focus-visible { outline: 2px solid #efb8cd; outline-offset: 2px; }
.workbench-preview-refresh svg { width: 16px; height: 16px; fill: none; stroke: currentColor; stroke-linecap: round; stroke-linejoin: round; stroke-width: 1.7; }
.workbench-preview-back { height: 29px; padding: 0 8px; border: 1px solid #c89eb3; border-radius: 4px; background: #fff4f8; color: #87445f; box-shadow: 1px 2px 0 rgba(46, 46, 46, .14); font-size: 10px; font-weight: 900; white-space: nowrap; }
.workbench-preview-back:hover { border-color: #a85d7c; background: #ffeaf2; color: #71364e; }
.workbench-preview-back:focus-visible { outline: 2px solid #78b9d4; outline-offset: 2px; }
.workbench-item-preview :deep(.model-preview-card) { margin: 0; border-radius: 6px; }
.workbench-item-preview :deep(.model-preview-canvas) { height: auto; aspect-ratio: 1 / 1; }
.workbench-texture-preview { min-width: 0; }
.workbench-texture-stage { display: flex; width: 100%; aspect-ratio: 1 / 1; min-width: 0; min-height: 290px; max-height: min(620px, 68vh); align-items: center; justify-content: center; overflow: hidden; padding: 16px; box-sizing: border-box; border: 1px solid #d7c2ce; border-radius: 6px; background-color: #fff; background-image: linear-gradient(45deg, #f8eef3 25%, transparent 25%), linear-gradient(-45deg, #f8eef3 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #f8eef3 75%), linear-gradient(-45deg, transparent 75%, #f8eef3 75%); background-position: 0 0, 0 8px, 8px -8px, -8px 0; background-size: 16px 16px; }
.workbench-texture-stage img { display: block; flex: 0 1 auto; width: auto; height: auto; max-width: 100%; max-height: 100%; object-fit: contain; object-position: center; }
.workbench-texture-state { display: grid; min-height: 290px; place-items: center; color: #9a808d; font-family: var(--mono); font-size: 10px; }
.workbench-texture-state.is-error { gap: 8px; padding: 24px; border: 1px dashed #d8a8b7; border-radius: 5px; background: #fff4f7; color: #9e3b47; text-align: center; }
.workbench-texture-state.is-error span { display: grid; width: 20px; height: 20px; place-items: center; border: 1px solid currentColor; border-radius: 50%; font-weight: 900; }
.workbench-texture-state.is-error strong { font-size: 11px; }
.workbench-preview-empty { min-height: 290px; display: grid; place-content: center; justify-items: center; padding: 30px; border: 1px dashed #acc6cd; border-radius: 5px; background: radial-gradient(circle at 50% 42%, #fff 0 13%, transparent 38%), linear-gradient(145deg, #edf6f8, #fbf7f8); text-align: center; }
.workbench-preview-empty svg { width: 62px; height: 62px; fill: none; stroke: #6a9cab; stroke-linecap: round; stroke-linejoin: round; stroke-width: 1.6; filter: drop-shadow(2px 3px 0 rgba(116, 79, 94, .12)); }
.workbench-preview-empty strong { margin-top: 13px; color: #315e6c; font-size: 14px; }
.workbench-preview-empty p { max-width: 370px; margin: 6px 0 0; color: #78929a; font-size: 11px; line-height: 1.6; }
.workbench-asset-library { display: grid; grid-template-rows: auto auto minmax(0, 1fr); align-self: start; width: 100%; height: 560px; min-width: 0; min-height: 0; overflow: hidden; padding: 12px; border: 1px solid #c4b4c0; border-radius: 7px; background: linear-gradient(155deg, rgba(255, 255, 255, .97), rgba(252, 246, 249, .93)); box-shadow: 3px 4px 0 rgba(46, 46, 46, .08); }
.workbench-asset-library-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; padding: 1px 2px 10px; border-bottom: 1px solid #eadde2; }
.workbench-asset-library-head > div { min-width: 0; display: grid; gap: 3px; }
.workbench-asset-library-head h3 { margin: 0; color: #684f61; font-size: 17px; }
.workbench-asset-library-head small { overflow: hidden; color: #9a808d; font-family: var(--mono); font-size: 9px; text-overflow: ellipsis; white-space: nowrap; }
.workbench-asset-refresh { display: inline-grid; width: 29px; height: 29px; flex: 0 0 29px; place-items: center; padding: 0; border: 1px solid #c89eb3; border-radius: 4px; background: #fff4f8; color: #9a5774; box-shadow: 1px 2px 0 rgba(46, 46, 46, .14); }
.workbench-asset-refresh:hover:not(:disabled) { border-color: #a85d7c; background: #ffeaf2; color: #87445f; }
.workbench-asset-refresh:focus-visible { outline: 2px solid #78b9d4; outline-offset: 2px; }
.workbench-asset-refresh:disabled { cursor: wait; opacity: .58; }
.workbench-asset-refresh svg { width: 16px; height: 16px; fill: none; stroke: currentColor; stroke-linecap: round; stroke-linejoin: round; stroke-width: 1.7; }
.workbench-asset-refresh:disabled svg { animation: workbench-asset-spin .8s linear infinite; }
@keyframes workbench-asset-spin { to { transform: rotate(360deg); } }
.workbench-asset-state { display: grid; min-height: 150px; place-items: center; color: #9a808d; font-family: var(--mono); font-size: 10px; }
.workbench-asset-error { display: flex; align-items: flex-start; gap: 8px; margin-top: 12px; padding: 10px; border: 1px solid #dfa9ae; border-radius: 5px; background: #fff1f2; color: #9e3b47; font-size: 11px; line-height: 1.5; }
.workbench-asset-error span { display: grid; width: 17px; height: 17px; flex: 0 0 17px; place-items: center; border: 1px solid currentColor; border-radius: 50%; font-family: var(--mono); font-weight: 900; }
.workbench-asset-summary { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)) auto; gap: 7px; align-items: stretch; padding: 11px 0 10px; }
.workbench-asset-summary > div { display: grid; gap: 2px; padding: 7px 9px; border: 1px solid #e2d2db; border-radius: 4px; background: rgba(255, 255, 255, .72); }
.workbench-asset-summary strong { color: #684f61; font-family: var(--mono); font-size: 17px; line-height: 1; }
.workbench-asset-summary span { color: #9a808d; font-size: 10px; }
.workbench-asset-summary > small { align-self: end; padding-bottom: 5px; color: #9a808d; font-family: var(--mono); font-size: 9px; white-space: nowrap; }
.workbench-asset-groups { display: grid; align-content: start; gap: 12px; min-height: 0; overflow-y: auto; padding-right: 3px; }
.workbench-asset-group { display: grid; gap: 6px; min-width: 0; }
.workbench-asset-group:first-child { order: 2; }
.workbench-asset-group:last-child { order: 1; }
.workbench-asset-group-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding-bottom: 4px; border-bottom: 1px solid #eadde2; }
.workbench-asset-group-head h4 { margin: 0; color: #684f61; font-size: 12px; }
.workbench-asset-group-head span { min-width: 20px; padding: 2px 5px; border: 1px solid #d8b8c8; border-radius: 3px; background: #fff4f8; color: #9a5774; font-family: var(--mono); font-size: 9px; text-align: center; }
.workbench-asset-row { display: grid; grid-template-columns: 38px minmax(0, 1fr) 25px 18px; gap: 8px; align-items: center; width: 100%; min-width: 0; padding: 7px; border: 1px solid #e4dadd; border-radius: 4px; background: rgba(255, 255, 255, .74); color: inherit; cursor: pointer; text-align: left; }
.workbench-asset-row-model { grid-template-columns: 38px minmax(0, 1fr) 25px 25px 18px; }
.workbench-asset-row:hover { border-color: #c99ab2; background: #fff4f8; }
.workbench-asset-row:focus-visible { outline: 2px solid #78b9d4; outline-offset: 2px; }
.workbench-asset-file-mark { display: grid; width: 36px; height: 27px; place-items: center; border: 1px solid #b2cbd1; border-radius: 3px; background: #f0f9fb; color: #477987; font-family: var(--mono); font-size: 9px; font-weight: 900; }
.workbench-asset-file-mark.is-texture { border-color: #d7b5c5; background: #fff1f6; color: #9a5774; }
.workbench-asset-file-mark.is-model { border-color: #b8c7d8; background: #f1f5fb; color: #56718e; }
.workbench-asset-file-copy { display: grid; gap: 3px; min-width: 0; }
.workbench-asset-file-copy strong,.workbench-asset-file-copy small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.workbench-asset-file-copy strong { color: #684f61; font-size: 11px; }
.workbench-asset-file-copy small { color: #9a808d; font-family: var(--mono); font-size: 9px; }
.workbench-asset-blender { display: grid; width: 25px; height: 25px; place-items: center; padding: 3px; border: 1px solid #c9b2c0; border-radius: 4px; background: #fff7fa; box-shadow: none; cursor: pointer; }
.workbench-asset-blender img { display: block; width: 17px; height: 17px; object-fit: contain; }
.workbench-asset-blender:hover:not(:disabled) { border-color: #a85d7c; background: #ffeaf2; }
.workbench-asset-blender:focus-visible { outline: 2px solid #78b9d4; outline-offset: 1px; }
.workbench-asset-blender:disabled { cursor: wait; opacity: .58; }
.workbench-asset-sb3 { display: grid; width: 25px; height: 25px; place-items: center; padding: 3px; border: 1px solid #b8cbd0; border-radius: 4px; background: #f1fbfd; box-shadow: none; cursor: pointer; }
.workbench-asset-sb3 img { display: block; width: 17px; height: 17px; object-fit: contain; }
.workbench-asset-sb3:hover:not(:disabled) { border-color: #6f9da8; background: #e3f5f8; }
.workbench-asset-sb3:focus-visible { outline: 2px solid #78b9d4; outline-offset: 1px; }
.workbench-asset-sb3:disabled { cursor: wait; opacity: .58; }
.workbench-asset-locate { display: grid; width: 18px; height: 22px; place-items: center; padding: 0; border: 0; background: transparent; box-shadow: none; color: #a85d7c; cursor: pointer; font-size: 16px; line-height: 1; text-align: center; }
.workbench-asset-locate:hover { color: #71364e; }
.workbench-asset-locate:focus-visible { outline: 2px solid #78b9d4; outline-offset: 1px; border-radius: 2px; }
.workbench-asset-empty { padding: 9px 10px; border: 1px dashed #d8c2cb; border-radius: 4px; color: #a38d96; font-size: 10px; text-align: center; }
.workbench-asset-empty-all { min-height: 160px; display: grid; place-items: center; margin-top: 12px; }
.main-resource-editor { display: grid; gap: 15px; padding: 17px 18px; border: 2px solid #77aab7; border-radius: 8px; background: linear-gradient(155deg, #fff 0%, #f7fcfd 100%); box-shadow: 3px 4px 0 rgba(46, 46, 46, .1); }
.main-resource-editor-body { display: grid; gap: 15px; }
.template-resource-section { display: grid; gap: 14px; }
.template-selected-summary { display: grid; grid-template-columns: 72px minmax(0, 1fr); gap: 13px; align-items: center; padding: 12px; border: 1px solid #b9d5c5; border-radius: 8px; background: linear-gradient(115deg, #eefaf3 0%, #ffffff 72%); }
.template-selected-summary .template-item-thumb { width: 72px; height: 72px; }
.template-selected-copy { display: grid; gap: 4px; min-width: 0; }
.template-selected-copy .field-label-text { color: #328264; font-size: 10px; font-weight: 900; }
.template-selected-copy strong,.template-selected-copy small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.template-selected-copy strong { color: #225d50; font-size: 15px; }
.template-selected-copy small { color: #66837b; font-size: 11px; }
.template-selection-empty { display: grid; gap: 4px; padding: 12px; border: 1px dashed #c6d8d2; border-radius: 7px; background: #f7fcfa; }
.template-selection-empty strong { color: #2e6c5b; font-size: 12px; }
.template-selection-empty small { color: var(--muted); font-size: 11px; }
.template-item-thumb { position: relative; display: grid; width: 52px; height: 52px; place-items: center; overflow: hidden; border: 1px solid #c6d9dc; border-radius: 5px; background: linear-gradient(145deg, #edf8fb, #dff1f4); color: #6e929b; font-family: var(--mono); font-size: 10px; font-weight: 900; }
.template-item-thumb img { position: absolute; inset: 0; width: 100%; height: 100%; display: block; object-fit: cover; }
.template-preprocess-tools { display: grid; gap: 10px; padding: 12px; border: 1px solid #c4d9d2; border-radius: 8px; background: linear-gradient(135deg, #f3fbf7, #fffdfb); }
.template-preprocess-grid { display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(0, 1.4fr); gap: 9px; align-items: stretch; }
.template-preprocess-rename { display: grid; grid-column: 1 / -1; grid-template-columns: minmax(0, 1fr) auto; gap: 9px; align-items: end; }
.template-preprocess-rename .field-label { margin: 0; }
.template-preprocess-rename input { height: 36px; border-color: #b8b1b8; background: #fff; }
.template-preprocess-rename > button { height: 36px; padding: 0 11px; border-radius: 5px; box-shadow: 2px 3px 0 #2e2e2e; font-size: 10px; white-space: nowrap; }
.template-preprocess-rename > button:disabled { cursor: wait; opacity: .56; }
.external-resource-actions { display: grid; gap: 10px; }
.external-resource-action-row { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 9px; }
.external-resource-action-row button { min-height: 36px; padding: 0 11px; border: 1px solid #9ebfc4; border-radius: 5px; background: #f4fbfc; color: #356b75; box-shadow: 2px 3px 0 rgba(46, 46, 46, .8); font-size: 10px; font-weight: 800; }
.external-resource-action-row button:hover:not(:disabled) { border-color: #6f9da8; background: #e3f5f8; }
.external-resource-action-row button:disabled { cursor: wait; opacity: .56; }
.resource-editor-section { display: grid; gap: 8px; }
.resource-editor-section .field-label { margin: 0; }
.resource-editor-path-row { display: flex; align-items: center; justify-content: space-between; gap: 14px; padding: 10px 11px; border: 1px dashed #b6c9ce; border-radius: 5px; background: #f5fbfd; }
.resource-editor-path-row > div { min-width: 0; display: grid; gap: 5px; }
.field-label-text { color: #52636c; font-size: 11px; font-weight: 800; }
.field-label-text em { margin-left: 5px; padding: 2px 4px; border: 1px solid #d9bdc5; border-radius: 3px; background: #fff2f5; color: #a05c6c; font-size: 9px; font-style: normal; }
.resource-editor-path-row code { overflow: hidden; color: #426d78; font-family: var(--mono); font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
.resource-editor-path-row button { flex: 0 0 auto; height: 31px; padding: 0 9px; font-size: 10px; }
.resource-editor-hint { color: var(--muted); font-size: 10px; line-height: 1.5; }
.main-resource-editor-footer { display: flex; justify-content: flex-end; gap: 9px; padding-top: 3px; }
.main-resource-editor-footer button { min-width: 96px; height: 38px; padding: 0 12px; border-radius: 5px; font-size: 11px; }
.main-resource-editor-footer .primary { min-width: 164px; box-shadow: 3px 4px 0 #2e2e2e; }
.process-board,
.coming-board,
.principles-board {
  padding: 21px 22px;
}

.board-head h2 { margin-top: 6px; }
.board-head p { margin: 6px 0 0; color: var(--muted); font-size: 12px; }
.route-progress { padding: 6px 8px; border: 1px solid #b9d5c5; background: #f0fbf4; }
.route-progress b { color: #187354; font-size: 14px; }

.process-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 11px;
  margin-top: 20px;
}

.process-step {
  min-height: 184px;
  display: flex;
  flex-direction: column;
  padding: 14px;
  border: 1px solid #d3ced0;
  border-radius: 5px;
  background: #fff;
}

.process-step.is-ready { border-color: #9fcbb3; background: #f7fdf9; }
.step-top { display: flex; align-items: center; justify-content: space-between; color: #69757b; font-family: var(--mono); font-size: 10px; font-weight: 900; }
.step-top b { color: #8b969a; font-size: 9px; }
.is-ready .step-top b { color: #23805c; }
.step-icon { width: 40px; height: 40px; display: grid; place-items: center; margin-top: 15px; border: 2px solid var(--line-strong); border-radius: 5px; font-size: 21px; }
.icon-profile { background: var(--pink); color: #a84c70; }
.icon-assets { background: #e7f6ff; color: #477f9c; }
.icon-release { background: #fff4c7; color: #a5852f; }
.process-step h3 { margin: 11px 0 5px; font-size: 15px; }
.process-step p { margin: 0; color: var(--muted); font-size: 11px; line-height: 1.55; }
.step-link { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-top: auto; padding-top: 12px; color: #8b969a; font-size: 10px; }
.is-ready .step-link { color: #27825f; }
.step-link strong { font-family: var(--mono); font-size: 14px; }

.workbench-lower-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(270px, .65fr);
  gap: 16px;
}

.board-head.compact { align-items: center; }
.shelf-count { color: #8a787e; }
.tool-preview-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 9px; margin-top: 17px; }
.tool-preview { min-width: 0; display: grid; grid-template-columns: 30px minmax(0, 1fr); gap: 8px; align-items: center; position: relative; padding: 11px 9px; border: 1px dashed #cfc9c1; border-radius: 5px; background: #fffdf9; }
.tool-preview-index { display: grid; place-items: center; width: 30px; height: 30px; border: 1px solid #c4c0bd; border-radius: 4px; color: #8d8986; font-family: var(--mono); font-size: 10px; font-weight: 900; }
.tool-preview div { min-width: 0; display: grid; gap: 3px; }
.tool-preview strong,.tool-preview small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tool-preview strong { color: #6e6865; font-size: 11px; }
.tool-preview small { color: #9a9290; font-size: 10px; }
.tool-preview em { position: absolute; top: 5px; right: 6px; color: #b1a6a1; font-family: var(--mono); font-size: 8px; font-style: normal; }

.principles-board { background: #f5fbfe; }
.principles-board ul { display: grid; gap: 12px; margin: 18px 0 0; padding: 0; list-style: none; }
.principles-board li { display: grid; grid-template-columns: 25px minmax(0, 1fr); gap: 9px; align-items: start; }
.principles-board li > span { color: #78a2ae; font-family: var(--mono); font-size: 10px; font-weight: 900; }
.principles-board p { margin: 0; color: #6b797e; font-size: 11px; line-height: 1.55; }
.principles-board strong { display: block; margin-bottom: 2px; color: #3c565d; font-size: 12px; }

@keyframes spin { to { transform: rotate(360deg); } }
@keyframes pulse { 0%, 100% { opacity: .35; transform: scale(.8); } 50% { opacity: 1; transform: scale(1); } }

@media (max-width: 1260px) {
  .setup-card { padding: 22px; }
  .workbench-lower-grid { grid-template-columns: minmax(0, 1fr); }
  .principles-board { display: none; }
}

@media (max-width: 980px) {
  .process-grid { grid-template-columns: 1fr; }
  .item-resource-grid { grid-template-columns: 1fr; }
  .workbench-preview-row { grid-template-columns: 1fr; }
  .project-row { grid-template-columns: minmax(0, 1fr) auto; }
}

@media (max-width: 760px) {
  .form-footer { align-items: flex-start; flex-direction: column; }
  .setup-submit { width: 100%; }
  .sims4-fbx-prompt { padding: 22px; }
  .fbx-skin-prompt { padding: 22px; }
  .sims4-fbx-fields { grid-template-columns: 1fr; }
  .sims4-fbx-result-summary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .sims4-fbx-result-row { grid-template-columns: 42px minmax(0, 1fr); }
  .sims4-fbx-result-actions { grid-column: 2; justify-content: flex-start; }
  .fbx-skin-source-row { grid-template-columns: 1fr; }
  .fbx-skin-source-row button { width: 100%; }
  .fbx-skin-result-summary { grid-template-columns: 1fr; }
  .hs2-skeleton-result-summary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .fbx-weight-result-summary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .path-picker { grid-template-columns: 1fr; }
  .path-picker button { width: 100%; }
  .item-browser-head { align-items: flex-start; flex-direction: column; }
  .item-browser-actions { width: 100%; justify-content: space-between; }
  .item-workspace-topbar { align-items: flex-start; flex-wrap: wrap; gap: 10px; }
  .item-workspace-content { grid-template-columns: 1fr; gap: 12px; }
  .item-workspace-heading { grid-column: 1; grid-row: 2; }
  .item-workspace-thumbnail { grid-column: 1; grid-row: 1; width: 130px; min-width: 0; }
  .item-workspace-actions { width: auto; margin-left: auto; align-items: center; justify-content: flex-end; flex-direction: row; }
  .item-workspace-actions button { width: auto; }
  .workbench-item-preview { width: 100%; }
  .workbench-asset-summary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .workbench-asset-summary > small { grid-column: 1 / -1; }
  .project-board-actions { width: 100%; align-items: stretch; flex-wrap: wrap; }
  .project-search-control,
  .project-search-control-board { width: 100%; max-width: none; }
  .project-search-control-board { flex-basis: 32px; }
  .project-workbench-toolbar,
  .item-workbench-toolbar { align-items: stretch; flex-direction: column; gap: 8px; }
  .item-workbench-toolbar--project { align-items: center; flex-direction: row; gap: 8px; }
  .project-workbench-toolbar-tools,
  .item-workbench-toolbar-tools { min-height: 28px; padding: 8px 0 0; border-top: 1px solid #d7e7eb; border-left: 0; }
  .item-workbench-toolbar--project .item-workbench-toolbar-tools { min-height: 27px; padding: 0; border-top: 0; }
  .project-workbench-toolbar-tools { flex-wrap: wrap; }
  .project-workbench-toolbar-floating .project-search-control { flex-basis: 100%; max-width: none; }
  .template-preprocess-grid { grid-template-columns: 1fr; }
  .template-preprocess-rename { grid-template-columns: 1fr; }
  .template-preprocess-rename > button { width: 100%; }
  .tool-preview-grid { grid-template-columns: 1fr; }
}
</style>
