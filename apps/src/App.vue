<script setup>
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import StartView from "./components/views/StartView.vue";
import CardCoverCropper from "./components/CardCoverCropper.vue";
import ViewLoading from "./components/ViewLoading.vue";
import { getAchievementIcon } from "./achievementIcons";
import characterCardTypeIcon from "./assets/card-type-character.svg";
import clothesCardTypeIcon from "./assets/card-type-clothes.svg";
import sceneCardTypeIcon from "./assets/card-type-scene.svg";
import itemKindBottom from "./assets/item-kind-bottom.png";
import itemKindGloves from "./assets/item-kind-gloves.png";
import itemKindPanties from "./assets/item-kind-panties.png";
import itemKindShoes from "./assets/item-kind-shoes.png";
import itemKindSocks from "./assets/item-kind-socks.png";
import itemKindTights from "./assets/item-kind-tights.png";
import itemKindTop from "./assets/item-kind-top.png";
import itemKindUnderwear from "./assets/item-kind-underwear.png";
import mapSceneDefaultThumbnail from "./assets/item-kind-map-default.png";
import studioItemDefaultThumbnail from "./assets/item-kind-studio-default.png";
import brandLogo from "../build-resources/brand-logo.png";
import wallpaperDefault from "./assets/wallpaper-default.jpg";

const views = [
  { id: "start", icon: "ST", label: "开始游戏" },
  { id: "overview", icon: "OV", label: "总览" },
  { id: "characters", icon: "CH", label: "卡片" },
  { id: "mods", icon: "MD", label: "模组" },
  { id: "plugins", icon: "PL", label: "插件" },
  { id: "workbench", icon: "WB", label: "工作台" },
  { id: "trash", icon: "TR", label: "回收站" },
  { id: "logs", icon: "LG", label: "日志" }
];

const activeView = ref("start");
const lazyView = (loader) => defineAsyncComponent({
  loader,
  loadingComponent: ViewLoading,
  delay: 0,
  timeout: 30000
});
const pageComponents = {
  start: StartView,
  overview: lazyView(() => import("./components/views/OverviewView.vue")),
  characters: lazyView(() => import("./components/views/CharactersView.vue")),
  mods: lazyView(() => import("./components/views/ModsView.vue")),
  plugins: lazyView(() => import("./components/views/PluginsView.vue")),
  workbench: lazyView(() => import("./components/views/WorkbenchView.vue")),
  logs: lazyView(() => import("./components/views/LogsView.vue")),
  settings: lazyView(() => import("./components/views/SettingsView.vue")),
  trash: lazyView(() => import("./components/views/TrashView.vue"))
};
const activePageComponent = computed(() => pageComponents[activeView.value] || StartView);
const cardBrowserMode = ref("character");
const libraryMode = ref("mods");
const modLibraryScrollPositions = reactive({ mods: 0, items: 0 });
const modTableScrollTarget = ref(null);
let modTableScrollRestoreToken = 0;
let modTableScrollRestoring = false;

const cardLibraryScrollPositions = reactive({ character: 0, clothes: 0, scene: 0 });
const cardLibraryScrollTargets = reactive({ character: null, clothes: null, scene: null });
let cardLibraryScrollRestoreToken = 0;
let cardLibraryScrollRestoring = false;

function captureModTableScrollPosition(mode = libraryMode.value, target = modTableScrollTarget.value, options = {}) {
  if (activeView.value !== "mods" && !options.allowInactive) return;
  if ((mode !== "mods" && mode !== "items") || !target) return;
  // A delayed restore can temporarily clamp scrollTop to the currently loaded
  // content height. Do not overwrite the intended session position with that
  // transient value while the item list is still growing.
  if (modTableScrollRestoring) return;
  const scrollTop = Number(target.scrollTop);
  if (!Number.isFinite(scrollTop)) return;
  if (!modTableScrollRestoring) modTableScrollRestoreToken += 1;
  modLibraryScrollPositions[mode] = Math.max(0, scrollTop);
}

function restoreModTableScrollPosition(mode = libraryMode.value) {
  if (activeView.value !== "mods" || mode !== libraryMode.value || !modTableScrollTarget.value) return;
  const scrollTop = Number(modLibraryScrollPositions[mode]);
  if (!Number.isFinite(scrollTop) || scrollTop < 0) return;
  modTableScrollRestoring = true;
  modTableScrollTarget.value.scrollTop = scrollTop;
  window.requestAnimationFrame(() => {
    modTableScrollRestoring = false;
  });
}

function scheduleModTableScrollRestore(mode = libraryMode.value) {
  if (activeView.value !== "mods" || mode !== libraryMode.value) return;
  const restoreToken = ++modTableScrollRestoreToken;
  for (const delay of [0, 50, 150, 300, 600, 1000]) {
    window.setTimeout(() => {
      if (
        restoreToken !== modTableScrollRestoreToken
        || activeView.value !== "mods"
        || mode !== libraryMode.value
        || !modTableScrollTarget.value
      ) return;
      restoreModTableScrollPosition(mode);
    }, delay);
  }
}

function registerModTableScrollContainer(target) {
  if (!target) return;
  modTableScrollTarget.value = target;
  scheduleModTableScrollRestore();
}

function unregisterModTableScrollContainer(target) {
  if (modTableScrollTarget.value !== target) return;
  modTableScrollTarget.value = null;
  modTableScrollRestoreToken += 1;
}

function isCardLibraryMode(mode) {
  return mode === "character" || mode === "clothes" || mode === "scene";
}

function captureCardLibraryScrollPosition(
  mode = cardBrowserMode.value,
  target = cardLibraryScrollTargets[mode],
  options = {}
) {
  if (activeView.value !== "characters" && !options.allowInactive) return;
  if (!isCardLibraryMode(mode) || !target || cardLibraryScrollRestoring) return;
  const scrollTop = Number(target.scrollTop);
  if (!Number.isFinite(scrollTop)) return;
  cardLibraryScrollPositions[mode] = Math.max(0, scrollTop);
  cardLibraryScrollRestoreToken += 1;
}

function restoreCardLibraryScrollPosition(mode = cardBrowserMode.value) {
  const target = cardLibraryScrollTargets[mode];
  if (
    activeView.value !== "characters"
    || mode !== cardBrowserMode.value
    || !target
  ) return;
  const scrollTop = Number(cardLibraryScrollPositions[mode]);
  if (!Number.isFinite(scrollTop) || scrollTop < 0) return;
  cardLibraryScrollRestoring = true;
  target.scrollTop = scrollTop;
  window.requestAnimationFrame(() => {
    cardLibraryScrollRestoring = false;
  });
}

function scheduleCardLibraryScrollRestore(mode = cardBrowserMode.value) {
  if (activeView.value !== "characters" || mode !== cardBrowserMode.value) return;
  const restoreToken = ++cardLibraryScrollRestoreToken;
  for (const delay of [0, 50, 150, 300, 600, 1000]) {
    window.setTimeout(() => {
      if (
        restoreToken !== cardLibraryScrollRestoreToken
        || activeView.value !== "characters"
        || mode !== cardBrowserMode.value
        || !cardLibraryScrollTargets[mode]
      ) return;
      restoreCardLibraryScrollPosition(mode);
    }, delay);
  }
}

function registerCardLibraryScrollContainer(mode, target) {
  if (!isCardLibraryMode(mode) || !target) return;
  cardLibraryScrollTargets[mode] = target;
  scheduleCardLibraryScrollRestore(mode);
}

function unregisterCardLibraryScrollContainer(mode, target = null) {
  if (!isCardLibraryMode(mode)) return;
  const registeredTarget = cardLibraryScrollTargets[mode];
  if (target && registeredTarget !== target) return;
  cardLibraryScrollTargets[mode] = null;
  cardLibraryScrollRestoreToken += 1;
}

function resetCardLibraryScrollPosition(mode = cardBrowserMode.value) {
  if (!isCardLibraryMode(mode)) return;
  cardLibraryScrollPositions[mode] = 0;
  cardLibraryScrollRestoreToken += 1;
  const target = cardLibraryScrollTargets[mode];
  if (!target) return;
  cardLibraryScrollRestoring = true;
  target.scrollTop = 0;
  window.requestAnimationFrame(() => {
    cardLibraryScrollRestoring = false;
  });
}

const itemViewMode = ref("table");
const isItemLibraryView = computed(() => activeView.value === "mods" && libraryMode.value === "items");
const itemKindLevel = ref("categories");
const itemKindGroup = ref("male");
const itemKindCategory = ref("");
const itemTab = ref("详情");
const modTab = ref("详情");
const cardDetailTab = ref("详情");
const selectedCards = ref(new Set());

try {
  const savedItemViewMode = window.localStorage.getItem("star-manager:item-view-mode");
  if (["table", "compact"].includes(savedItemViewMode)) itemViewMode.value = savedItemViewMode;
} catch {
  // The view switch still works for the current session when storage is unavailable.
}

function setItemViewMode(mode) {
  if (!["table", "compact"].includes(mode)) return;
  itemViewMode.value = mode;
  try {
    window.localStorage.setItem("star-manager:item-view-mode", mode);
  } catch {
    // Ignore storage failures; the in-memory preference remains active.
  }
}

const backendStatus = ref("checking");
const gameDirStatus = ref("未选择");
const taskName = ref("等待任务");
const progress = ref(0);
const taskId = ref("idle");
const taskHint = ref("请选择有效目录后点击重建");
const extractMode = ref("copy");
const isBusy = ref(false);
const activeAction = ref("");
const settingsNotice = reactive({ type: "", message: "" });
const blenderExecutablePath = ref("");
const sb3utilityExecutablePath = ref("");
const workbenchAuthorId = ref("");
const workbenchWorkspacePath = ref("");
const workbenchActiveProjectId = ref("");
const workbenchProjects = ref([]);
const WORKBENCH_PROFILE_CACHE_KEY = "star-manager.workbench-profile";
const startupWallpaper = window.desktopApi?.startupWallpaper || {};
const gamePluginSetup = reactive({ checking: false, status: "未检查", installedCount: 0, error: "" });
const START_PLUGIN_DEFINITIONS = Object.freeze([
  {
    key: "splashScreen",
    label: "Enable SplashScreen",
    relativePath: "BepInEx/patchers/BepInEx.SplashScreen/BepInEx.SplashScreen.Patcher.BepInEx5.dll"
  },
  {
    key: "graphicsMod",
    label: "激活 GraphicsMod",
    relativePath: "BepInEx/Plugins/Graphics/HS2Graphics.dll"
  },
  {
    key: "dhh",
    label: "激活 DHH",
    relativePath: "BepInEx/Plugins/DHH_AI4.dll"
  },
  {
    key: "autosave",
    label: "启动自动保存",
    relativePath: "BepInEx/Plugins/HS2_Plugins/HS2_Autosave.dll"
  },
  {
    key: "betterAA",
    label: "启动更好的抗锯齿",
    relativePath: "BepInEx/Plugins/HS2_BetterAA.dll"
  },
  {
    key: "povX",
    label: "Activate PoVX",
    relativePath: "BepInEx/Plugins/HS2_PovX.dll"
  }
]);
const START_SPECIAL_SETTING_DEFINITIONS = Object.freeze([
  {
    key: "console",
    kind: "special",
    label: "激活控制台",
    relativePath: "BepInEx/config/BepInEx.cfg"
  },
  {
    key: "experimental",
    kind: "special",
    label: "实验模式",
    relativePath: "BepInEx/LauncherEN/ilikebleeding.txt"
  }
]);
const startPluginSettings = reactive({ loading: false, error: "", items: [] });

function resetStartPluginSettings() {
  startPluginSettings.loading = false;
  startPluginSettings.error = "";
  startPluginSettings.items = [...START_PLUGIN_DEFINITIONS.map((definition) => ({ ...definition, kind: "plugin" })), ...START_SPECIAL_SETTING_DEFINITIONS].map((definition) => ({
    ...definition,
    installed: false,
    enabled: false,
    actualPath: definition.relativePath,
    busy: false
  }));
}

function pluginPathIdentity(value) {
  return String(value || "")
    .replaceAll("\\", "/")
    .replace(/\.dll\.dl_$/i, ".dll")
    .replace(/\.disabled$/i, "")
    .replace(/\.dl_$/i, ".dll")
    .toLocaleLowerCase();
}

resetStartPluginSettings();

const managerSettings = reactive({
  startupView: "start",
  favoriteCardTheme: "gold",
  checkDatabaseChangesOnStartup: true,
  databaseWorkerCount: 1,
  databaseWorkerLimit: 1,
  databaseLogicalProcessorCount: 1,
  wallpaperPath: String(startupWallpaper.wallpaperPath || "").trim(),
  wallpaperType: ["image", "video"].includes(String(startupWallpaper.wallpaperType || ""))
    ? String(startupWallpaper.wallpaperType)
    : ""
});
const wallpaperReady = ref(!startupWallpaper.wallpaperPath);
const wallpaperLoadFailed = ref(false);
const databaseWorkerOptions = computed(() => Array.from(
  { length: Math.max(1, Number(managerSettings.databaseWorkerLimit) || 1) },
  (_value, index) => index + 1
));
let rendererReadyNotified = false;
let removeStartupLogListener = null;
let backendRetryTimer = 0;
let backendRetryInFlight = false;

function wallpaperUrl(value) {
  const raw = String(value || "").trim();
  if (!raw) return "";
  if (/^(?:file|https?|data):/i.test(raw)) return raw;
  // Route local media through Electron's wallpaper:// protocol so both the
  // dev HTTP renderer and the packaged file renderer can stream local files
  // without waiting for a second IPC read into a data URL.
  return `wallpaper://file?path=${encodeURIComponent(raw)}`;
}

const wallpaperSource = computed(() => {
  if (!managerSettings.wallpaperPath || wallpaperLoadFailed.value) return wallpaperDefault;
  return wallpaperUrl(managerSettings.wallpaperPath);
});
const wallpaperIsVideo = computed(() => managerSettings.wallpaperType === "video"
  || /\.mp4$/i.test(managerSettings.wallpaperPath || ""));

function notifyRendererReady() {
  if (rendererReadyNotified) return;
  rendererReadyNotified = true;
  window.desktopApi?.notifyRendererReady?.();
}

function handleWallpaperReady() {
  wallpaperReady.value = true;
}

function handleWallpaperError() {
  if (managerSettings.wallpaperPath && !wallpaperLoadFailed.value) {
    log(`[Wallpaper Error] 无法加载壁纸：${managerSettings.wallpaperPath}`);
  }
  wallpaperLoadFailed.value = true;
  wallpaperReady.value = true;
}

const paths = reactive({
  gameDir: "",
  inputDir: "",
  outputDir: ""
});
const directoryShortcuts = ref([]);
const directoryShortcutPrompt = reactive({ open: false, name: "", path: "", error: "", saving: false, editingIndex: -1 });
let settingsSaveQueue = Promise.resolve();

function readWorkbenchProfileCache() {
  try {
    const cached = JSON.parse(window.localStorage?.getItem(WORKBENCH_PROFILE_CACHE_KEY) || "{}");
    return {
      authorId: String(cached?.authorId || "").trim(),
      workspacePath: String(cached?.workspacePath || "").trim()
    };
  } catch {
    return { authorId: "", workspacePath: "" };
  }
}

function writeWorkbenchProfileCache(authorId, workspacePath) {
  try {
    window.localStorage?.setItem(WORKBENCH_PROFILE_CACHE_KEY, JSON.stringify({
      authorId: String(authorId || "").trim(),
      workspacePath: String(workspacePath || "").trim()
    }));
  } catch {
    // LocalStorage may be unavailable in a restricted renderer; Electron settings remain the source of truth.
  }
}

function comparableWorkbenchPath(value) {
  return String(value || "")
    .trim()
    .replace(/[\\/]+$/g, "")
    .replaceAll("/", "\\")
    .toLocaleLowerCase();
}

function serializeWorkbenchProjects(projects = workbenchProjects.value) {
  return (Array.isArray(projects) ? projects : []).map((project) => ({
    id: String(project?.id || ""),
    guid: String(project?.guid || ""),
    name: String(project?.name || ""),
    path: String(project?.path || ""),
    manifestPath: String(project?.manifestPath || ""),
    projectFilePath: String(project?.projectFilePath || ""),
    createdAt: String(project?.createdAt || "")
  }));
}

function serializeDirectoryShortcuts(shortcuts = directoryShortcuts.value) {
  return (Array.isArray(shortcuts) ? shortcuts : [])
    .map((shortcut) => ({
      name: String(shortcut?.name || "").trim(),
      path: String(shortcut?.path || "").trim()
    }))
    .filter((shortcut) => shortcut.name && shortcut.path);
}

function mergeWorkbenchProjects(scannedProjects) {
  const scanned = Array.isArray(scannedProjects) ? scannedProjects : [];
  const scannedByPath = new Map(
    scanned
      .filter((project) => project?.path)
      .map((project) => [comparableWorkbenchPath(project.path), project])
  );
  const knownPaths = new Set();
  const merged = [];

  for (const existing of workbenchProjects.value) {
    const key = comparableWorkbenchPath(existing?.path);
    const discovered = scannedByPath.get(key);
    if (discovered) {
      merged.push({ ...existing, ...discovered });
      knownPaths.add(key);
    } else if (!existing?.projectFilePath) {
      merged.push(existing);
    }
  }
  for (const project of scanned) {
    const key = comparableWorkbenchPath(project?.path);
    if (key && !knownPaths.has(key)) {
      merged.push(project);
      knownPaths.add(key);
    }
  }
  return merged;
}

function workbenchProjectsInCurrentWorkspace() {
  const workspacePath = comparableWorkbenchPath(workbenchWorkspacePath.value);
  if (!workspacePath) return [];
  return workbenchProjects.value.filter((project) => {
    const projectPath = comparableWorkbenchPath(project?.path);
    return projectPath === workspacePath || projectPath.startsWith(`${workspacePath}\\`);
  });
}

function syncWorkbenchActiveProject() {
  const projects = workbenchProjectsInCurrentWorkspace();
  const currentId = String(workbenchActiveProjectId.value || "").trim();
  if (projects.some((project) => String(project?.id || "") === currentId)) return false;
  const nextId = String(projects[0]?.id || "");
  if (currentId === nextId) return false;
  workbenchActiveProjectId.value = nextId;
  return true;
}

async function refreshWorkbenchProjects({ persist = false } = {}) {
  const workspacePath = String(workbenchWorkspacePath.value || "").trim();
  if (!workspacePath) return { ok: true, projects: workbenchProjects.value };
  const result = await window.desktopApi?.scanWorkbenchProjects?.({
    workspacePath,
    knownProjects: serializeWorkbenchProjects()
  });
  if (!result?.ok) {
    log("[Workbench Scan] " + (result?.error || "workbench project scan failed"));
    return result || { ok: false, error: "工程扫描失败", projects: [] };
  }
  const previous = JSON.stringify(workbenchProjects.value);
  workbenchProjects.value = mergeWorkbenchProjects(result.projects);
  const activeProjectChanged = syncWorkbenchActiveProject();
  if (persist && (previous !== JSON.stringify(workbenchProjects.value) || activeProjectChanged)) {
    await saveAppSettings();
  }
  return { ...result, projects: workbenchProjects.value };
}

const setupLanguageOptions = [
  { value: 0, label: "中文" },
  { value: 1, label: "日文" },
  { value: 2, label: "English" }
];
const setupQualityOptions = [
  { value: 0, label: "性能" },
  { value: 1, label: "普通" },
  { value: 2, label: "质量" }
];
const setup = reactive({
  language: 0,
  quality: 1,
  display: 0,
  width: 1280,
  height: 720,
  resolution: "1280 x 720",
  fullscreen: false,
  dirty: false,
  loading: false,
  saving: false,
  loaded: false,
  exists: false,
  error: "",
  warning: "",
  filePath: "",
  backupPath: "",
  displays: [{ index: 0, label: "Display 0" }],
  resolutions: [{ label: "1280 x 720", width: 1280, height: 720 }]
});

const stats = reactive({
  cards: null,
  zipmods: null,
  missingZipmods: null,
  missingAbdata: null,
  zipmodErrors: null,
  zipmodWarnings: null,
  modItems: null,
  builtinItems: null,
  clothesCards: null,
  sceneCards: null,
  plugins: null,
  duplicateZipmods: null,
  lastDatabaseBuiltAt: ""
});

const logs = ref([]);
const trashEntries = ref([]);
const trashLoading = ref(false);
const trashAction = ref("");
const trashError = ref("");
const trashNotice = ref("");
const trashRoot = ref("");
const trashFilter = ref("all");
const filteredTrashEntries = computed(() => {
  if (trashFilter.value === "all") return trashEntries.value;
  return trashEntries.value.filter((item) => item.kind === trashFilter.value);
});
const seenTaskMessages = ref(new Set());
const recentTasks = ref([]);
let nextTaskSubmissionOrder = 0;
const selectedTask = ref(null);
const achievements = ref([]);
const achievementPreferences = reactive({ enabled: true, notifications: true, hide_locked: false });
const selectedAchievement = ref(null);
const achievementToast = ref(null);
const achievementInitialized = ref(false);
let achievementToastTimer = null;

const visibleAchievements = computed(() => achievementPreferences.hide_locked
  ? achievements.value.filter((item) => item.unlocked)
  : achievements.value);
const achievementUnlockedCount = computed(() => achievements.value.filter((item) => item.unlocked).length);


const cardFolders = ref([]);
const cardTree = ref(null);
const expandedCardFolders = ref(new Set());
const cards = ref([]);
const clothesFolders = ref([]);
const clothesTree = ref(null);
const expandedClothesFolders = ref(new Set());
const clothesCards = ref([]);
const selectedClothesFolder = ref("");
const selectedClothesDetailPath = ref("");
const selectedClothesDetail = ref(null);
const clothesDetailTab = ref("详情");
const clothesSearch = ref("");
const clothesSort = ref("name");
const sceneFolders = ref([]);
const sceneTree = ref(null);
const expandedSceneFolders = ref(new Set());
const sceneCards = ref([]);
const selectedSceneFolder = ref("");
const selectedSceneDetailPath = ref("");
const selectedSceneDetail = ref(null);
const sceneDetailTab = ref("详情");
const sceneSideMode = ref("tree");
const cardDependencyFilter = ref("all");
const cardFavoriteFilter = ref(false);
const selectedCardFolder = ref("");
const selectedCardDetailPath = ref("");
const characterSideMode = ref("tree");
const clothesSideMode = ref("tree");
const cardBulkMode = ref(false);
const selectedCardProfile = ref(null);
const selectedCardDependencies = ref([]);
const selectedCardProfileLoading = ref(false);
const settingNaviSlot = ref("");
const naviActionNotice = reactive({ type: "", message: "" });
const exportingCoordinateCard = ref(false);
const coordinateExportDir = ref("");
const coordinateExportPrompt = reactive({ open: false, draft: "", error: "" });
const coordinateExportNotice = reactive({ type: "", message: "", path: "" });
const exportingPortablePackage = ref(false);
const portablePackageDir = ref("");
const portablePackageCompress = ref(true);
const PORTABLE_PACKAGE_TYPES = [
  { key: "face", label: "面部与五官", description: "脸型、眉眼、妆容与面部细节" },
  { key: "hair", label: "发型", description: "前发、后发、侧发与扩展发型" },
  { key: "body", label: "身体与肌肤", description: "身体肌肤、细节、晒痕与人体彩绘" },
  { key: "clothes", label: "服装", description: "上衣、下装、内衣、袜子与鞋子" },
  { key: "accessory", label: "配饰", description: "头部、脸部、身体与四肢配饰" }
];
const portablePackageTypes = ref(PORTABLE_PACKAGE_TYPES.map((type) => type.key));
const portablePackagePrompt = reactive({ open: false, draftDir: "", compress: true, types: [], error: "" });
const portablePackageNotice = reactive({ type: "", message: "", path: "" });
const CARD_LOAD_OPTIONS = [
  { key: "face", label: "脸部", description: "脸型、眉眼、妆容与面部细节" },
  { key: "body", label: "身体", description: "身体比例、肌肤、细节与彩绘" },
  { key: "hair", label: "头发", description: "后发、前发、侧发与扩展发型" },
  { key: "clothes", label: "衣服", description: "服装栏位；不会改变配饰" },
  { key: "accessory", label: "装饰", description: "配饰栏位；不会改变衣服" },
  { key: "parameter", label: "人物设定", description: "姓名、性格、生日、声线等参数" }
];
const cardLoadPrompt = reactive({
  open: false,
  busy: false,
  error: "",
  selected: CARD_LOAD_OPTIONS.map((option) => option.key)
});
const cardLoadNotice = reactive({ type: "", message: "" });
const cardDependencyRemote = reactive({
  loading: false,
  error: "",
  byGuid: {},
  busyGuids: {},
  notices: {},
  installingAll: false,
  taskIds: {},
  taskGuids: {},
  progress: {},
  statuses: {},
  phase: "",
  phaseProgress: 0,
  downloadSpeedBps: 0,
  downloadedBytes: 0,
  totalBytes: 0,
  currentFile: "",
  allTaskId: "",
  allProgress: 0,
  allStatus: "",
  allPhase: "",
  allPhaseProgress: 0,
  allDownloadSpeedBps: 0,
  allDownloadedBytes: 0,
  allTotalBytes: 0,
  allCurrentFile: ""
});
let cardDependencyRemoteRequestId = 0;
const replacingCardCover = ref(false);
const cardCoverNotice = reactive({ type: "", message: "" });
const cardCoverCrop = reactive({
  open: false,
  imagePath: "",
  imageData: "",
  imageName: ""
});
const favoritingCardPath = ref("");
const cardFavoriteNotice = reactive({ type: "", message: "" });
const ratingCardPath = ref("");
const cardRatingNotice = reactive({ type: "", message: "" });
const cardTagNotice = reactive({ type: "", message: "" });
const cardTagPrompt = reactive({
  open: false,
  busy: false,
  loading: false,
  error: "",
  draft: "",
  selected: [],
  current: [],
  available: []
});
const bulkCardTagPrompt = reactive({
  open: false,
  busy: false,
  loading: false,
  error: "",
  draft: "",
  selected: [],
  available: []
});
const cardTagCatalog = reactive({ gameDir: "", loaded: false, tags: [] });
const cardTagFilter = reactive({
  open: false,
  loading: false,
  error: "",
  search: "",
  available: [],
  scope: "directory",
  resultsLoading: false,
  resultsError: "",
  libraryTag: "",
  libraryCards: []
});
let cardTagLibraryRequestId = 0;
let clothesListRequestId = 0;
let clothesIndexRetryTimer = 0;
let clothesTreeRefreshTimer = 0;
let sceneListRequestId = 0;
const selectedCardProfileError = ref("");
const cardProfileEditor = reactive({
  editing: false,
  busy: false,
  error: "",
  message: "",
  values: {
    fullname: "",
    personality: 0,
    birthMonth: 1,
    birthDay: 1,
    voiceRate: 0.5,
    futanari: false
  }
});
const cardLibrary = reactive({
  checked: false,
  loading: false,
  error: "",
  validGameDir: false,
  root: ""
});
const clothesLibrary = reactive({
  checked: false,
  loading: false,
  loadingMore: false,
  detailLoading: false,
  error: "",
  validGameDir: false,
  root: "",
  total: null,
  indexing: false,
  treeIndexing: false,
  nextOffset: 0,
  hasMore: false
});
const sceneLibrary = reactive({
  checked: false,
  loading: false,
  loadingMore: false,
  detailLoading: false,
  error: "",
  validGameDir: false,
  root: "",
  total: null,
  nextOffset: 0,
  hasMore: false
});

// Keep each incremental response small. The compact item view virtualizes its
// DOM window, so this controls request/JSON work rather than rendered nodes.
const ITEM_PAGE_SIZE = 96;
// The grid is image-first. LazyThumbnail still requests only rows near the
// viewport; card payload parsing happens only when a user opens a detail view.
const CLOTHES_CARD_PAGE_SIZE = 96;
const SCENE_CARD_PAGE_SIZE = 96;
const MOD_PAGE_SIZE = 200;
const UNKNOWN_AUTHOR_LABEL = "未知作者";
const POSE_ITEM_KIND_CODES = new Set(["500", "501"]);
const MAP_SCENE_KIND = "__map_scene__";
const GAME_MAP_SCENE_KIND = "__game_map_scene__";
const DUAL_MAP_SCENE_KIND = "__game_studio_map_scene__";
const STUDIO_ITEM_KIND = "__studio_item__";
const MAP_SCENE_KIND_CODES = new Set([MAP_SCENE_KIND, GAME_MAP_SCENE_KIND, DUAL_MAP_SCENE_KIND]);
const MAP_SCENE_FILTER_KIND = "__map_filter__";
const MAP_SCENE_FILTER_KINDS = [MAP_SCENE_FILTER_KIND];
const GAME_CLOTHING_CATEGORY_NOS = new Set([
  "140", "141", "144", "147",
  "240", "241", "242", "243", "244", "245", "246", "247"
]);
const GAME_CLOTHING_SLOT_LABELS = {
  140: "上衣",
  141: "下衣",
  144: "手套",
  147: "鞋子",
  240: "上衣",
  241: "下衣",
  242: "内衣",
  243: "内裤",
  244: "手套",
  245: "裤袜",
  246: "袜子",
  247: "鞋子"
};
const GAME_ACCESSORY_CATEGORY_NOS = new Set([
  "351", "352", "353", "354", "355", "356", "357", "358", "359", "360", "361", "362", "363"
]);
const GAME_HAIR_CATEGORY_NOS = new Set(["300", "301", "302", "303"]);
const GAME_FACE_CATEGORY_NOS = new Set([
  "110", "111", "112", "121", "210", "211", "212",
  "314", "315", "316", "317", "318", "319", "320", "322", "323"
]);
const GAME_FACE_EYE_CATEGORY_NOS = new Set(["317", "318"]);
const GAME_BODY_CATEGORY_NOS = new Set([
  "8", "131", "132", "133",
  "231", "232", "233", "313", "334", "335"
]);
const GAME_BODY_PAINT_CATEGORY_NOS = new Set(["8", "313"]);
const GAME_BODY_SLOT_LABELS = {
  8: "身体彩绘",
  131: "身体肌肤",
  132: "身体细节",
  133: "身体晒痕",
  231: "身体肌肤",
  232: "身体细节",
  233: "身体晒痕",
  313: "身体彩绘",
  334: "乳头",
  335: "阴毛"
};
const GAME_BODY_PAINT_SLOT_OPTIONS = [
  { value: 0, label: "彩绘层 1" },
  { value: 1, label: "彩绘层 2" }
];
const GAME_HAIR_SLOT_OPTIONS = [
  { value: 0, categoryNo: 300, label: "后发", apiName: "HairBack" },
  { value: 1, categoryNo: 301, label: "前发", apiName: "HairFront" },
  { value: 2, categoryNo: 302, label: "侧发", apiName: "HairSide" },
  { value: 3, categoryNo: 303, label: "扩展发", apiName: "HairOption" }
];
const GAME_CURRENT_SLOT_LABELS = {
  8: "身体彩绘",
  110: "脸模",
  111: "脸部肌肤",
  112: "脸部细节",
  121: "胡子",
  131: "身体肌肤",
  132: "身体细节",
  133: "身体晒痕",
  210: "脸模",
  211: "脸部肌肤",
  212: "脸部细节",
  231: "身体肌肤",
  232: "身体细节",
  233: "身体晒痕",
  313: "身体彩绘",
  314: "眉毛",
  315: "睫毛",
  316: "眼影",
  317: "美瞳",
  318: "瞳孔",
  319: "眼睛高光",
  320: "腮红",
  322: "口红",
  323: "痣/雀斑",
  334: "乳头",
  335: "阴毛"
};
const GAME_FACE_SLOT_LABELS = {
  110: "脸模",
  111: "脸部肌肤",
  112: "脸部细节",
  121: "胡子",
  210: "脸模",
  211: "脸部肌肤",
  212: "脸部细节",
  314: "眉毛",
  315: "睫毛",
  316: "眼影",
  317: "美瞳",
  318: "瞳孔",
  319: "眼睛高光",
  320: "腮红",
  322: "口红",
  323: "痣/雀斑"
};
const GAME_ACCESSORY_SLOT_LABELS = {
  351: "头部",
  352: "耳朵",
  353: "眼镜",
  354: "脸部",
  355: "脖子",
  356: "肩部",
  357: "胸部",
  358: "腰部",
  359: "后背",
  360: "胯部",
  361: "手部",
  362: "腿部",
  363: "脚部"
};
const GAME_CURRENT_GROUPS = [
  { key: "clothes", label: "服装栏位", description: "上衣、下衣、内衣与鞋袜" },
  { key: "hairs", label: "头发栏位", description: "后发、前发、侧发与扩展发" },
  { key: "faces", label: "面部栏位", description: "脸模、眼睛与妆容细节" },
  { key: "bodies", label: "身体栏位", description: "身体肌肤、彩绘与身体细节" },
  { key: "accessories", label: "配饰栏位", description: "20 个通用饰品槽，每个槽可装配 13 种部位之一" }
];
const GAME_ACCESSORY_NONE_CATEGORY_NO = 350;
const GAME_ACCESSORY_PART_OPTIONS = Object.entries(GAME_ACCESSORY_SLOT_LABELS).map(([categoryNo, label]) => ({
  categoryNo: Number(categoryNo),
  label
}));
const GAME_ACCESSORY_SLOT_OPTIONS = Array.from({ length: 20 }, (_, slotNo) => ({
  value: slotNo,
  label: `配饰槽 ${slotNo + 1}（slotNo ${slotNo}）`
}));
const PERSONALITY_LABELS = [
  "\u9177\u59b9",
  "\u6807\u51c6",
  "\u5fa1\u59d0",
  "\u5973\u53cb",
  "\u8fa3\u59b9",
  "\u5f31\u59b9",
  "\u4eba\u59bb",
  "\u5973\u738b",
  "\u8150\u5973",
  "\u6b63\u59b9",
  "\u8ba4\u771f\u59b9",
  "\u8f6f\u59b9\u7eb8",
  "\u6b63\u592a",
  "\u75c5\u5a07"
];
const personalityOptions = PERSONALITY_LABELS.map((label, value) => ({ label, value }));
const ITEM_KIND_LABELS = {
  [MAP_SCENE_FILTER_KIND]: "地图",
  [MAP_SCENE_KIND]: "地图 / 工作室",
  [GAME_MAP_SCENE_KIND]: "地图 / 本体",
  [DUAL_MAP_SCENE_KIND]: "地图 / 本体 + 工作室",
  [STUDIO_ITEM_KIND]: "Studio",
  8: "男/身体/人体彩绘",
  110: "男/面部/眼睛",
  111: "男/面部/眉毛",
  112: "男/面部/睫毛",
  121: "男/面部/胡子",
  131: "男/身体/身体肌肤",
  132: "男/身体/身体细节",
  133: "男/身体/身体晒痕",
  140: "男/服饰/上衣",
  141: "男/服饰/下衣",
  144: "男/服饰/手套",
  147: "男/服饰/鞋子",
  210: "女/面部/脸模",
  211: "女/面部/脸部肌肤",
  212: "女/面部/脸部皱纹",
  231: "女/身体/身体肌肤",
  232: "女/身体/肉感",
  233: "女/身体/晒痕",
  240: "女/服饰/上衣",
  241: "女/服饰/下衣",
  242: "女/服饰/内衣",
  243: "女/服饰/内裤",
  244: "女/服饰/手套",
  245: "女/服饰/裤袜",
  246: "女/服饰/袜子",
  247: "女/服饰/鞋子",
  300: "头发/后发",
  301: "头发/前发",
  302: "头发/侧发",
  303: "头发/后侧发",
  313: "女/身体/人体彩绘",
  314: "女/面部/眉毛",
  315: "女/面部/睫毛",
  316: "女/面部/眼影",
  317: "女/面部/美瞳种类",
  318: "女/面部/瞳孔",
  319: "女/面部/眼睛亮点",
  320: "女/面部/腮红",
  322: "女/面部/口红",
  323: "女/面部/痣",
  334: "女/身体/乳头",
  335: "女/身体/阴毛",
  348: "图案",
  351: "饰品/头部",
  352: "饰品/耳朵",
  353: "饰品/眼镜",
  354: "饰品/脸部",
  355: "饰品/脖子",
  356: "饰品/肩部",
  357: "饰品/胸部",
  358: "饰品/腰部",
  359: "饰品/后背",
  360: "饰品/胯部",
  361: "饰品/手部",
  362: "饰品/腿部",
  363: "饰品/脚部",
  500: "男姿势",
  501: "女姿势"
};

// The top bar is intentionally a small taxonomy rather than a dump of every
// database Kind. A category opens the second level, where the concrete Kinds
// are shown as selectable children.
const TOPBAR_KIND_GROUPS = [
  {
    key: "female",
    label: "女性",
    tone: "female",
    categories: [
      { key: "face", label: "面部", kinds: ["210", "211", "212", "314", "315", "316", "317", "318", "319", "320", "322", "323"] },
      { key: "body", label: "身体", kinds: ["231", "232", "233", "313", "334", "335"] },
      { key: "clothes", label: "服饰", kinds: ["240", "241", "242", "243", "244", "245", "246", "247"] },
      { key: "pose", label: "姿势", kinds: ["501"] }
    ]
  },
  {
    key: "male",
    label: "男性",
    tone: "male",
    categories: [
      { key: "face", label: "面部", kinds: ["110", "111", "112", "121"] },
      { key: "body", label: "身体", kinds: ["8", "131", "132", "133"] },
      { key: "clothes", label: "服饰", kinds: ["140", "141", "144", "147"] },
      { key: "pose", label: "姿势", kinds: ["500"] }
    ]
  },
  {
    key: "common",
    label: "通用",
    tone: "common",
    categories: [
      { key: "hair", label: "头发", kinds: ["300", "301", "302", "303"] },
      { key: "accessory", label: "饰品", kinds: ["351", "352", "353", "354", "355", "356", "357", "358", "359", "360", "361", "362", "363"] }
    ]
  },
  {
    key: "other",
    label: "其它",
    tone: "neutral",
    categories: [
      { key: "map", label: "地图", kinds: [MAP_SCENE_FILTER_KIND] },
      { key: "pattern", label: "图案", kinds: ["348"] }
    ]
  },
  {
    key: "studio",
    label: "Studio",
    tone: "studio",
    categories: [
      { key: "studio", label: "Studio", kinds: [STUDIO_ITEM_KIND] }
    ]
  }
];

const TOPBAR_KIND_ICON_URLS = {
  "240": itemKindTop,
  "241": itemKindBottom,
  "242": itemKindUnderwear,
  "243": itemKindPanties,
  "244": itemKindGloves,
  "245": itemKindTights,
  "246": itemKindSocks,
  "247": itemKindShoes
};

function topbarKindIcon(kind) {
  return TOPBAR_KIND_ICON_URLS[String(kind)] || "";
}

function svgDataUrl(svg) {
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}

const POSE_ITEM_THUMBNAILS = {
  500: svgDataUrl(`
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96">
  <defs>
    <linearGradient id="bg" x1="10" y1="8" x2="86" y2="88" gradientUnits="userSpaceOnUse">
      <stop stop-color="#d7f0ff"/>
      <stop offset="1" stop-color="#395a74"/>
    </linearGradient>
  </defs>
  <rect width="96" height="96" rx="14" fill="url(#bg)"/>
  <path d="M18 75h60" stroke="#f8fbff" stroke-width="5" stroke-linecap="round" opacity=".35"/>
  <circle cx="51" cy="22" r="8" fill="#f8fbff"/>
  <path d="M50 32 39 49l13 7 14-13" fill="none" stroke="#f8fbff" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="m39 49-17 4" fill="none" stroke="#17354b" stroke-width="7" stroke-linecap="round"/>
  <path d="m53 56 15 16" fill="none" stroke="#17354b" stroke-width="7" stroke-linecap="round"/>
  <path d="M53 56 41 75" fill="none" stroke="#f8fbff" stroke-width="7" stroke-linecap="round"/>
  <text x="14" y="24" fill="#17354b" font-family="Verdana, sans-serif" font-size="14" font-weight="700">M</text>
</svg>`),
  501: svgDataUrl(`
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96">
  <defs>
    <linearGradient id="bg" x1="12" y1="10" x2="84" y2="86" gradientUnits="userSpaceOnUse">
      <stop stop-color="#ffe1ec"/>
      <stop offset="1" stop-color="#8b4163"/>
    </linearGradient>
  </defs>
  <rect width="96" height="96" rx="14" fill="url(#bg)"/>
  <path d="M19 76h58" stroke="#fff8fb" stroke-width="5" stroke-linecap="round" opacity=".35"/>
  <circle cx="46" cy="21" r="8" fill="#fff8fb"/>
  <path d="M47 31c-5 8-8 16-7 23 1 8 8 13 19 15" fill="none" stroke="#fff8fb" stroke-width="7" stroke-linecap="round"/>
  <path d="M40 45 24 35" fill="none" stroke="#55233a" stroke-width="7" stroke-linecap="round"/>
  <path d="M42 54 28 71" fill="none" stroke="#fff8fb" stroke-width="7" stroke-linecap="round"/>
  <path d="M52 65 70 48" fill="none" stroke="#55233a" stroke-width="7" stroke-linecap="round"/>
  <path d="M55 39c6 3 11 7 15 14" fill="none" stroke="#fff8fb" stroke-width="5" stroke-linecap="round" opacity=".9"/>
  <text x="14" y="24" fill="#55233a" font-family="Verdana, sans-serif" font-size="14" font-weight="700">F</text>
</svg>`)
};
const MAP_SCENE_THUMBNAIL = mapSceneDefaultThumbnail;
const STUDIO_ITEM_THUMBNAIL = studioItemDefaultThumbnail;
const itemRows = ref([]);
const modRows = ref([]);
const selectedItem = ref(null);
const itemContextMenu = reactive({ open: false, x: 0, y: 0, item: null });
const itemAccessoryPrompt = reactive({ open: false, item: null, slotNo: 0, busy: false, error: "" });
const itemGameApply = reactive({ busy: false, itemId: null, commandId: "", status: "", error: "" });
const itemGameNotice = reactive({ type: "", message: "" });
const itemFacePrompt = reactive({ open: false, item: null, facePartNo: 0, busy: false, error: "" });
const itemBodyPrompt = reactive({ open: false, item: null, bodyPartNo: 0, busy: false, error: "" });
const assemblyMode = ref(false);
const assemblyUiActive = computed(() => assemblyMode.value && isItemLibraryView.value);
watch([isItemLibraryView, assemblyMode], () => {
  if (!isItemLibraryView.value || assemblyMode.value) {
    itemKindLevel.value = "categories";
    itemKindCategory.value = "";
  }
});
const assemblyTargetSlot = reactive({
  active: false,
  groupKey: "",
  partIndex: null,
  categoryNo: null,
  label: "",
  accessorySlotNo: null,
  hairSlotNo: null,
  facePartNo: null,
  bodyPartNo: null
});
const assemblyAccessorySlotTypes = reactive({});
const assemblyAccessoryPartMenu = reactive({
  open: false,
  x: 0,
  y: 0,
  slotNo: null,
  groupKey: "accessories",
  categoryNo: null,
  item: null
});
const currentGameState = reactive({
  loading: false,
  error: "",
  available: false,
  source: "",
  characterId: 0,
  sex: 0,
  characterName: "",
  characterFileName: "",
  coordinateName: "",
  hairs: [],
  clothes: [],
  faces: [],
  bodies: [],
  accessories: []
});
const assemblyContext = reactive({
  loading: false,
  error: "",
  available: false,
  scene: "none",
  editor: null,
  hscene: {
    available: false,
    femaleCount: 0,
    maleCount: 0,
    totalCount: 0,
    females: [],
    males: []
  }
});
const assemblyCharacterTarget = reactive({
  target: "editor",
  sex: null,
  characterIndex: null,
  characterId: null
});
const assemblyCharacterPickerOpen = ref(false);

function assemblySexLabel(sex) {
  const value = Number(sex);
  return value === 1 ? "女性" : value === 0 ? "男性" : "未知";
}

function isAssemblyCharacterSelected(option) {
  if (option.target === "editor") return assemblyCharacterTarget.target === "editor";
  return assemblyCharacterTarget.target === "hscene"
    && assemblyCharacterTarget.sex === option.character?.sex
    && assemblyCharacterTarget.characterIndex === option.character?.characterIndex
    && assemblyCharacterTarget.characterId === option.character?.characterId;
}

const assemblyCharacterOptions = computed(() => {
  const options = [];
  if (assemblyContext.editor?.available) {
    options.push({
      key: "editor",
      target: "editor",
      character: null,
      name: assemblyContext.editor.characterName || "角色编辑器角色",
      meta: `角色编辑器 · ${assemblySexLabel(assemblyContext.editor.sex)}`
    });
  }
  if (assemblyContext.scene === "hscene") {
    for (const character of assemblyContext.hscene?.females || []) {
      options.push({
        key: `female-${character.characterIndex}-${character.characterId}`,
        target: "hscene",
        character,
        name: character.characterName || `女性角色 ${character.characterIndex + 1}`,
        meta: `女性 · 角色 ${character.characterIndex + 1}`
      });
    }
    for (const character of assemblyContext.hscene?.males || []) {
      options.push({
        key: `male-${character.characterIndex}-${character.characterId}`,
        target: "hscene",
        character,
        name: character.characterName || `男性角色 ${character.characterIndex + 1}`,
        meta: `男性 · 角色 ${character.characterIndex + 1}`
      });
    }
  }
  return options;
});

const selectedAssemblyCharacter = computed(() => (
  assemblyCharacterOptions.value.find(isAssemblyCharacterSelected)
  || assemblyCharacterOptions.value[0]
  || { name: "未选择角色", meta: "等待角色信息同步", target: "none", character: null }
));

const assemblyStatusNotice = computed(() => {
  const itemMessage = String(itemGameNotice.message || "").trim();
  const syncMessage = currentGameState.available
    ? String(currentGameState.error || "").trim()
    : "";
  if (!itemMessage && !syncMessage) return null;
  const itemType = String(itemGameNotice.type || "info");
  const hasSyncIssue = Boolean(syncMessage);
  const tone = itemType === "error" || hasSyncIssue ? "error" : itemType;
  return {
    tone,
    title: hasSyncIssue && itemMessage ? "同步与操作提示" : hasSyncIssue ? "同步异常" : itemType === "error" ? "换装失败" : "操作提示",
    message: syncMessage || itemMessage,
    detail: hasSyncIssue && itemMessage
      ? `最近操作：${itemMessage}`
      : hasSyncIssue
        ? "已保留最近一次成功同步的数据。"
        : "",
    showRetry: hasSyncIssue,
    showClose: Boolean(itemMessage)
  };
});

function toggleAssemblyCharacterPicker() {
  if (!assemblyContext.available || !assemblyCharacterOptions.value.length) return;
  assemblyCharacterPickerOpen.value = !assemblyCharacterPickerOpen.value;
}

async function handleAssemblyCharacterSelect(option) {
  if (!option) return;
  const selected = await selectAssemblyCharacter(option.target, option.character);
  if (selected) assemblyCharacterPickerOpen.value = false;
}

watch(assemblyMode, () => {
  assemblyCharacterPickerOpen.value = false;
});

watch(assemblyUiActive, (active) => {
  if (!active) {
    assemblyCharacterPickerOpen.value = false;
    closeAssemblyAccessoryPartMenu();
  }
});

watch([
  () => assemblyContext.scene,
  () => assemblyContext.available,
  () => currentGameState.available
], () => {
  assemblyCharacterPickerOpen.value = false;
  if (!assemblyContext.available || !currentGameState.available) {
    resetAssemblyAccessorySlotTypes();
    closeAssemblyAccessoryPartMenu();
  }
});
let currentGameStatePollTimer = null;
let currentGameStateRequestSeq = 0;
const selectedMod = ref(null);
const workbenchTemplateSelection = reactive({
  active: false,
  busy: false,
  error: "",
  request: null,
  result: null
});
const modBulkMode = ref(false);
const selectedModIds = ref(new Set());
const modAuthorFilterOpen = ref(false);
const itemAuthorFilterOpen = ref(false);
const selectedModItems = ref([]);
const selectedModItemsLoading = ref(false);
const selectedModItemsError = ref("");
const selectedModDiagnostics = ref(null);
const selectedModDiagnosticsLoading = ref(false);
const selectedModDiagnosticsError = ref("");
const zipmodAuthors = ref([]);
const itemFilterAuthors = ref([]);
const itemFilterKinds = ref([]);
const modFilters = reactive({
  author: "",
  status: ""
});
const dependencyUsageFilter = ref("");
const dependencyUsageOptions = [
  { value: "used", label: "已使用" },
  { value: "unused", label: "未使用" },
  { value: "", label: "全部" }
];
const itemFilters = reactive({
  search: "",
  kind: "",
  author: "",
  status: "",
  source: ""
});
let itemFilterTimer = null;
let modFilterTimer = null;
let itemRowsRequestSeq = 0;
const repairingUnity3dPath = ref("");
const repairingThumbnailItemId = ref(null);
const openingUnity3dItemId = ref(null);
const exportingUnity3dItemId = ref(null);
const deletingItemId = ref(null);
const bulkActionBusy = ref("");
const cleaningDuplicateZipmods = ref(false);
const duplicateZipmodPrompt = reactive({
  open: false,
  items: [],
  analysis: null,
  analysisLoading: false,
  busyId: null,
  busyAll: false,
  error: ""
});
const duplicateZipmodDeleteConfirm = reactive({
  open: false,
  keepLabel: "",
  keepRole: "",
  duplicateId: null,
  primaryZipmodId: null
});
const manifestAuthorPrompt = reactive({
  open: false,
  value: "",
  zipmodId: null,
  busy: false,
  error: ""
});
const manifestEditor = reactive({
  open: false,
  zipmodId: null,
  loading: false,
  busy: false,
  error: "",
  fields: {
    guid: "",
    name: "",
    version: "",
    author: ""
  }
});
const bulkAuthorPrompt = reactive({
  open: false,
  value: "",
  error: ""
});
const bulkExportPrompt = reactive({
  open: false,
  targetDir: "",
  mode: "copy",
  confirmMove: false,
  error: ""
});
const cardDependencyExportPrompt = reactive({
  open: false,
  targetDir: "",
  mode: "copy",
  confirmMove: false,
  error: ""
});
const cardDeletePrompt = reactive({
  open: false,
  busy: false,
  error: ""
});
const cardSingleDeletePrompt = reactive({
  open: false,
  busy: false,
  error: "",
  card: null
});
const cardMovePrompt = reactive({
  open: false,
  busy: false,
  folderBusy: false,
  error: "",
  sourceGender: "",
  targetPath: "",
  expanded: new Set(),
  editMode: "",
  nameDraft: ""
});
const deleteItemPrompt = reactive({
  open: false,
  item: null,
  name: "",
  error: ""
});
const bulkDeleteErrorItemsPrompt = reactive({
  open: false,
  count: 0,
  error: ""
});
const deleteModPrompt = reactive({
  open: false,
  mod: null,
  name: "",
  error: ""
});
const missingItemPrompt = reactive({
  open: false,
  kind: "item",
  name: "",
  modId: "",
  property: "",
  remoteLoading: false,
  remoteCandidate: null,
  remoteEntry: null,
  remoteError: ""
});
const bulkOrganizePrompt = reactive({
  open: false,
  targetDir: "",
  error: ""
});
const organizeAllPrompt = reactive({ open: false, error: "" });
const bulkUnity3dPrompt = reactive({
  open: false
});
const bulkDuplicateCleanupPrompt = reactive({
  open: false,
  error: ""
});
const bulkDeletePrompt = reactive({
  open: false,
  error: ""
});
const importResultPrompt = reactive({
  open: false,
  task: null
});
const thumbnailToolsPrompt = reactive({
  open: false,
  targetDir: "",
  selectedTargetIds: new Set(),
  error: ""
});

const itemDatabase = reactive({
  checked: false,
  exists: false,
  loading: false,
  loadingMore: false,
  error: "",
  offset: 0,
  limit: ITEM_PAGE_SIZE,
  total: 0,
  hasMore: false
});

const modDatabase = reactive({
  checked: false,
  exists: false,
  loading: false,
  loadingMore: false,
  error: "",
  offset: 0,
  limit: MOD_PAGE_SIZE,
  total: 0,
  hasMore: false
});

const selectedCount = computed(() => selectedCards.value.size);
const cardTagOptions = computed(() => {
  const tags = new Map();
  for (const card of cards.value) {
    for (const tag of card.tags || []) tags.set(String(tag).toLocaleLowerCase(), String(tag));
  }
  if (cardDependencyFilter.value.startsWith("tag:")) {
    const activeTag = cardDependencyFilter.value.slice(4);
    if (activeTag) tags.set(activeTag.toLocaleLowerCase(), activeTag);
  }
  return [...tags.values()].sort((left, right) => left.localeCompare(right, "zh-CN"));
});
const cardTagFilterSuggestions = computed(() => {
  const query = cardTagFilter.search.trim().toLocaleLowerCase();
  const matchedTags = uniqueCardTags([
    ...(cardTagCatalog.gameDir === paths.gameDir ? cardTagCatalog.tags : []),
    ...cardTagOptions.value
  ])
    .filter((tag) => !query || tag.toLocaleLowerCase().includes(query))
    .sort((left, right) => left.localeCompare(right, "zh-CN"));
  return query ? matchedTags.slice(0, 12) : matchedTags;
});
const cardTagPromptLibraryTags = computed(() => {
  const query = cardTagPrompt.draft.trim().toLocaleLowerCase();
  return uniqueCardTags(cardTagPrompt.available)
    .filter((tag) => !query || tag.toLocaleLowerCase().includes(query))
    .sort((left, right) => left.localeCompare(right, "zh-CN"));
});
const baseVisibleCards = computed(() => {
  if (cardDependencyFilter.value === "missing") {
    return cards.value.filter((card) => Number(card.missingCount || 0) > 0);
  }
  if (cardDependencyFilter.value === "normal") {
    return cards.value.filter((card) => Number(card.missingCount || 0) === 0);
  }
  if (cardDependencyFilter.value.startsWith("tag:")) {
    const targetTag = cardDependencyFilter.value.slice(4).toLocaleLowerCase();
    const sourceCards = cardTagFilter.scope === "library" ? cardTagFilter.libraryCards : cards.value;
    return sourceCards.filter((card) => (card.tags || []).some(
      (tag) => String(tag).toLocaleLowerCase() === targetTag
    ));
  }
  return cards.value;
});
const visibleCards = computed(() => {
  if (!cardFavoriteFilter.value) return baseVisibleCards.value;
  return baseVisibleCards.value.filter((card) => card.favorite);
});
const cardBrowserCountText = computed(() => {
  if (cardFavoriteFilter.value) {
    return `收藏 ${visibleCards.value.length} / ${baseVisibleCards.value.length}`;
  }
  if (cardDependencyFilter.value === "missing") {
    return `依赖缺失 ${visibleCards.value.length} / ${cards.value.length}`;
  }
  if (cardDependencyFilter.value === "normal") {
    return `正常 ${visibleCards.value.length} / ${cards.value.length}`;
  }
  if (cardDependencyFilter.value.startsWith("tag:")) {
    if (cardTagFilter.scope === "library") {
      return `全库标签“${cardDependencyFilter.value.slice(4)}” ${visibleCards.value.length}`;
    }
    return `标签“${cardDependencyFilter.value.slice(4)}” ${visibleCards.value.length} / ${cards.value.length}`;
  }
  return `已加载 ${cards.value.length}`;
});
const selectedCardDetail = computed(() => {
  return visibleCards.value.find((card) => card.absolutePath === selectedCardDetailPath.value) || null;
});
const visibleClothesCards = computed(() => {
  const query = String(clothesSearch.value || "").trim().toLocaleLowerCase();
  const filtered = query
    ? clothesCards.value.filter((card) => [card.name, card.filename, card.relativePath]
      .some((value) => String(value || "").toLocaleLowerCase().includes(query)))
    : [...clothesCards.value];
  return filtered.sort((left, right) => {
    if (clothesSort.value === "modified") return right.modifiedTimestamp - left.modifiedTimestamp;
    if (clothesSort.value === "size") return right.fileSize - left.fileSize;
    return String(left.name || "").localeCompare(String(right.name || ""), "zh-CN", { numeric: true });
  });
});
const selectedClothesCard = computed(() => (
  selectedClothesDetail.value
  || clothesCards.value.find((card) => card.relativePath === selectedClothesDetailPath.value)
  || null
));
const selectedClothesFolderRow = computed(() => (
  clothesFolders.value.find((folder) => folder.relativePath === selectedClothesFolder.value) || null
));
const clothesCardCountText = computed(() => {
  const total = clothesLibrary.total ?? selectedClothesFolderRow.value?.count;
  if (Number.isFinite(Number(total)) && Number(total) > clothesCards.value.length) {
    return `${clothesCards.value.length} / ${Number(total)}`;
  }
  return String(clothesCards.value.length);
});
const visibleSceneCards = computed(() => [...sceneCards.value]);
const selectedSceneCard = computed(() => (
  selectedSceneDetail.value
  || sceneCards.value.find((card) => card.relativePath === selectedSceneDetailPath.value)
  || null
));
const selectedSceneFolderRow = computed(() => (
  sceneFolders.value.find((folder) => folder.relativePath === selectedSceneFolder.value) || null
));
const sceneCardCountText = computed(() => {
  const total = sceneLibrary.total ?? selectedSceneFolderRow.value?.count;
  if (Number.isFinite(Number(total)) && Number(total) > sceneCards.value.length) {
    return `${sceneCards.value.length} / ${Number(total)}`;
  }
  return String(sceneCards.value.length);
});
const visibleCardPaths = computed(() => visibleCards.value.map((card) => card.absolutePath).filter(Boolean));
const visibleSelectedCardCount = computed(() => visibleCardPaths.value.filter((path) => selectedCards.value.has(path)).length);
const allVisibleCardsSelected = computed(() => visibleCardPaths.value.length > 0 && visibleSelectedCardCount.value === visibleCardPaths.value.length);
const someVisibleCardsSelected = computed(() => visibleSelectedCardCount.value > 0 && !allVisibleCardsSelected.value);
const cardMoveAvailable = computed(() => (
  cardTagFilter.scope !== "library"
  && /^(female|male)(\/|$)/i.test(selectedCardFolder.value)
));
const cardMoveDestinationReady = computed(() => Boolean(cardMovePrompt.targetPath) && cardMovePrompt.targetPath !== selectedCardFolder.value);
const cardMoveFolderRows = computed(() => flattenManagedMoveTree(cardTree.value));
const gameDirDisplay = computed(() => paths.gameDir);
const backendReady = computed(() => backendStatus.value === "ready");
function formatProgressPercent(value) {
  const percent = Math.max(0, Math.min(100, Number(value || 0)));
  if (Number.isInteger(percent)) return `${percent}%`;
  return `${percent.toFixed(1)}%`;
}

const taskPercent = computed(() => formatProgressPercent(progress.value));
const itemDatabaseEmpty = computed(() => itemDatabase.checked && itemDatabase.exists && itemDatabase.total === 0);
const modDatabaseEmpty = computed(() => modDatabase.checked && modDatabase.exists && modDatabase.total === 0);
const importResultData = computed(() => importResultPrompt.task?.data || {});
const importResultGroups = computed(() => {
  const data = importResultData.value;
  return [
    {
      key: "imported",
      label: "正常导入模组",
      count: Number(data.imported_count || 0),
      tone: "ok",
      empty: "没有新的非重复模组。",
      items: (data.imported || []).map((item) => ({
        title: item.file_name || item.guid || "zipmod",
        meta: item.guid || "",
        detail: item.target_path || item.source_path || "",
        note: "已复制到当前游戏 mods/Imported"
      }))
    },
    {
      key: "promoted",
      label: "重复中保留更优",
      count: Number(data.promoted_count || 0),
      tone: "warn",
      empty: "没有需要替换为更优版本的重复模组。",
      items: (data.promoted || []).map((item) => ({
        title: item.file_name || item.guid || "zipmod",
        meta: item.guid || "",
        detail: item.promoted_file_path || "",
        note: item.removed_primary_path ? `已移除旧主文件：${item.removed_primary_path}` : "已提升为主记录"
      }))
    },
    {
      key: "cleaned",
      label: "重复清理",
      count: Number(data.cleaned_count || 0),
      tone: "danger",
      empty: "没有自动清理重复文件。",
      items: (data.cleaned || []).flatMap((item) => {
        const removed = item.removed?.length ? item.removed : [];
        if (!removed.length) {
          return [{
            title: item.kept_file_name || item.guid || "zipmod",
            meta: item.guid || "",
            detail: item.kept_file_path || "",
            note: "保留该模组，重复记录已整理"
          }];
        }
        return removed.map((path) => ({
          title: path.split(/[\\/]/).pop() || item.guid || "zipmod",
          meta: item.guid || "",
          detail: path,
          note: item.kept_file_path ? `已清理，保留：${item.kept_file_path}` : "已清理重复文件"
        }));
      })
    },
    {
      key: "cards",
      label: "角色卡",
      count: Number(data.card_imported_count || 0),
      tone: "ok",
      empty: "没有识别到可导入的角色卡。",
      items: (data.imported_cards || []).map((item) => ({
        title: item.target_path?.split(/[\\/]/).pop() || "角色卡",
        meta: "AIS/HS2 PNG",
        detail: item.target_path || "",
        note: item.source_path ? `来源：${item.source_path}` : "已复制到 UserData/chara/female/imported"
      }))
    },
    {
      key: "coordinates",
      label: "服装卡",
      count: Number(data.coordinate_imported_count || 0),
      tone: "ok",
      empty: "没有识别到可导入的服装卡。",
      items: (data.imported_coordinates || []).map((item) => ({
        title: item.target_path?.split(/[\\/]/).pop() || "服装卡",
        meta: "AIS/HS2 Clothes PNG",
        detail: item.target_path || "",
        note: item.source_path ? `来源：${item.source_path}` : "已复制到 UserData/coordinate/female/imoprted"
      }))
    },
    {
      key: "unity3d",
      label: "补入 Unity3D",
      count: Number(data.unity3d_repaired_count || 0),
      tone: "warn",
      empty: "没有从外部 abdata 补入 unity3d。",
      items: (data.unity3d_repaired || []).flatMap((item) => {
        const moved = item.moved?.length ? item.moved : [];
        return moved.map((movedItem) => ({
          title: movedItem.path?.split(/[\\/]/).pop() || item.guid || "unity3d",
          meta: item.guid || "",
          detail: movedItem.path || "",
          note: movedItem.source_path ? `已从外部 abdata 移入 zipmod：${movedItem.source_path}` : `已写入：${item.zipmod_path || ""}`
        }));
      })
    },
    {
      key: "skipped",
      label: "跳过",
      count: Number(data.skipped_count || 0) + Number(data.invalid_count || 0) + Number(data.non_card_png_count || 0),
      tone: "neutral",
      empty: "没有跳过项。",
      items: [
        ...(data.skipped || []).map((item) => ({
          title: item.guid || item.id || "zipmod",
          meta: "需要人工确认",
          detail: "",
          note: item.reason || "未自动处理"
        })),
        ...(data.invalid || []).map((item) => ({
          title: item.source_path?.split(/[\\/]/).pop() || "zipmod",
          meta: item.status || "invalid",
          detail: item.source_path || "",
          note: item.error || "manifest 无效"
        })),
        ...(data.non_card_pngs || []).map((path) => ({
          title: path.split(/[\\/]/).pop() || "PNG",
          meta: "普通 PNG",
          detail: path,
          note: "未检测到角色卡标记"
        }))
      ]
    },
    {
      key: "failures",
      label: "失败",
      count: Number(data.failure_count || 0),
      tone: "danger",
      empty: "没有失败项。",
      items: (data.failures || []).map((item) => ({
        title: item.guid || item.source_path?.split(/[\\/]/).pop() || item.id || "失败项",
        meta: item.id ? `#${item.id}` : "",
        detail: item.source_path || "",
        note: item.error || "处理失败"
      }))
    }
  ].filter((group) => group.count > 0);
});
const zipmodAuthorOptions = computed(() => ["", ...zipmodAuthors.value, UNKNOWN_AUTHOR_LABEL]);
const filteredZipmodAuthorOptions = computed(() => {
  const query = String(modFilters.author || "").trim().toLowerCase();
  const options = zipmodAuthorOptions.value;
  if (!query) return options;
  return options.filter((author) => {
    const label = author || "All authors";
    return label.toLowerCase().includes(query);
  });
});
const bulkAuthorSuggestions = computed(() => {
  const query = String(bulkAuthorPrompt.value || "").trim().toLowerCase();
  const options = zipmodAuthors.value;
  const matched = query
    ? options.filter((author) => String(author || "").toLowerCase().includes(query))
    : options;
  return matched.slice(0, 40);
});
const itemAuthorOptions = computed(() => ["", ...itemFilterAuthors.value, UNKNOWN_AUTHOR_LABEL]);
const filteredItemAuthorOptions = computed(() => {
  const query = String(itemFilters.author || "").trim().toLowerCase();
  const options = itemAuthorOptions.value;
  if (!query) return options;
  return options.filter((author) => {
    const label = author || "全部作者";
    return label.toLowerCase().includes(query);
  });
});
const itemKindOptions = computed(() => {
  const genderOrder = { male: 0, female: 1, neutral: 2 };
  const categoryOrder = {
    "\u9762\u90e8": 0,
    "\u8eab\u4f53": 1,
    "\u670d\u9970": 2,
    "\u5934\u53d1": 3,
    "\u9970\u54c1": 4
  };
  const databaseKinds = itemFilterKinds.value.filter((kind) => !MAP_SCENE_KIND_CODES.has(String(kind)));
  const options = [...MAP_SCENE_FILTER_KINDS, ...databaseKinds].map((kind, sourceIndex) => {
    const label = itemKindLabel(kind);
    const gender = label.startsWith("\u2642")
      ? "male"
      : label.startsWith("\u2640")
        ? "female"
        : "neutral";
    const segments = label.split("/");
    const category = gender === "neutral" ? segments[0] : segments[1];
    return {
      value: kind,
      label,
      gender,
      category,
      categoryIndex: categoryOrder[category] ?? 99,
      sourceIndex
    };
  });
  options.sort((left, right) => (
    genderOrder[left.gender] - genderOrder[right.gender]
    || left.categoryIndex - right.categoryIndex
    || left.sourceIndex - right.sourceIndex
  ));
  return [{ value: "", label: "全部 Kind", gender: "all" }, ...options];
});
const workbenchItemCategoryOptions = computed(() => {
  const options = [
    ...itemKindOptions.value,
    ...Object.keys(ITEM_KIND_LABELS)
      .filter((kind) => /^\d+$/.test(String(kind)))
      .map((kind) => ({ value: kind, label: itemKindLabel(kind) }))
  ];
  const seen = new Set();
  return options.filter((option) => {
    const value = String(option?.value || "").trim();
    if (!value || value.startsWith("__") || seen.has(value)) return false;
    seen.add(value);
    return true;
  });
});

const activeTopbarKindGroup = computed(() => (
  TOPBAR_KIND_GROUPS.find((group) => group.key === itemKindGroup.value) || TOPBAR_KIND_GROUPS[0]
));
const activeTopbarKindCategory = computed(() => (
  activeTopbarKindGroup.value.categories.find((category) => category.key === itemKindCategory.value) || null
));
const activeTopbarKindChildren = computed(() => (
  activeTopbarKindCategory.value?.kinds.map((kind) => ({
    value: kind,
    label: kind === MAP_SCENE_FILTER_KIND ? "地图" : String(ITEM_KIND_LABELS[kind] || kind).split("/").pop()
  })) || []
));

function topbarKindFilterIsActive(kind) {
  return String(itemFilters.kind || "") === String(kind || "");
}

function resetTopbarKindNavigation() {
  itemKindLevel.value = "categories";
  itemKindCategory.value = "";
}

function openTopbarKindCategory(group, category) {
  itemKindGroup.value = group.key;
  itemKindCategory.value = category.key;
  if (category.kinds.length === 1) {
    // 地图、图案本身就是末级类别，不需要再打开一个空的二级页面。
    itemKindLevel.value = "categories";
    selectTopbarKindChild(category.kinds[0]);
    return;
  }
  itemKindLevel.value = "children";
}

function selectTopbarKindChild(kind) {
  itemFilters.kind = String(kind);
  void applyItemFilters();
}

function clearTopbarKindFilter() {
  itemFilters.kind = "";
  resetTopbarKindNavigation();
  void applyItemFilters();
}

const selectedModDiagnosticGroups = computed(() => {
  const issues = selectedModDiagnostics.value?.issues || [];
  return issues.map((issue) => ({
    ...issue,
    badgeStatus: diagnosticIssueBadgeStatus(issue),
    title: unity3dIssueTitle(issue),
    summary: unity3dIssueSummary(issue)
  }));
});
const selectedModDiagnosticSummary = computed(() => {
  if (selectedModDiagnosticGroups.value.length === 0) return "?";
  const [first] = selectedModDiagnosticGroups.value;
  return selectedModDiagnosticGroups.value.length === 1
    ? first.summary
    : `${first.summary} 等 ${selectedModDiagnosticGroups.value.length} 项`;
});
const selectedModCanDelete = computed(() => Boolean(selectedModDiagnostics.value?.can_delete));
const selectedModCount = computed(() => selectedModIds.value.size);
const visibleModIds = computed(() => modRows.value.map((row) => Number(row.id)).filter((id) => Number.isFinite(id)));
const visibleSelectedModCount = computed(() => visibleModIds.value.filter((id) => selectedModIds.value.has(id)).length);
const allVisibleModsSelected = computed(() => visibleModIds.value.length > 0 && visibleSelectedModCount.value === visibleModIds.value.length);
const someVisibleModsSelected = computed(() => visibleSelectedModCount.value > 0 && !allVisibleModsSelected.value);
const duplicateRecommendation = computed(() => duplicateZipmodPrompt.analysis?.recommendation || null);
const duplicateRecommendedKeep = computed(() => duplicateRecommendation.value?.keep || null);
const duplicateRecommendedDelete = computed(() => duplicateRecommendation.value?.delete || []);
const duplicateRecommendedDuplicateIds = computed(() => {
  return duplicateRecommendedDelete.value
    .filter((item) => item.role === "duplicate" && item.duplicate_id)
    .map((item) => Number(item.duplicate_id))
    .filter((id) => Number.isFinite(id));
});
const duplicateRecommendedMerge = computed(() => {
  const directMerge = (duplicateZipmodPrompt.analysis?.candidates || []).filter(
    (item) => item.role === "duplicate" && item.recommended_action === "merge" && item.duplicate_id
  );
  if (directMerge.length > 0) return directMerge;
  const primaryNeedsMerge = (duplicateZipmodPrompt.analysis?.candidates || []).some(
    (item) => item.role === "primary" && item.recommended_action === "merge"
  );
  if (!primaryNeedsMerge) return [];
  return duplicateRecommendedKeep.value?.role === "duplicate" && duplicateRecommendedKeep.value?.duplicate_id
    ? [duplicateRecommendedKeep.value]
    : [];
});
const duplicateHasRecommendedMerge = computed(() => {
  return (duplicateZipmodPrompt.analysis?.candidates || []).some((item) => item.recommended_action === "merge");
});
const duplicateRecommendsPrimaryDeletion = computed(() => Boolean(duplicateRecommendation.value?.primary_should_delete));
function duplicateCompareValue(candidate, key) {
  const value = Number(candidate?.[key]);
  return Number.isFinite(value) ? value : null;
}

function duplicateBestValue(key) {
  const values = (duplicateZipmodPrompt.analysis?.candidates || [])
    .map((candidate) => duplicateCompareValue(candidate, key))
    .filter((value) => value !== null);
  return values.length ? Math.max(...values) : null;
}

function duplicateIsStrictBest(candidate, key) {
  const current = duplicateCompareValue(candidate, key);
  const best = duplicateBestValue(key);
  if (current === null || best === null || current !== best) return false;
  return (duplicateZipmodPrompt.analysis?.candidates || []).every((other) => {
    if (other === candidate) return true;
    const otherValue = duplicateCompareValue(other, key);
    return otherValue === null || current > otherValue;
  });
}

function duplicatePrimaryReason(candidate) {
  if (!candidate) return "";
  const reasons = new Set(candidate.recommendation_reasons || []);
  const deleteReasons = new Set(candidate.delete_reasons || []);
  if (candidate.recommended_action === "merge") {
    return "双方都有独有物品，建议合并后再清理";
  }
  if (deleteReasons.has("older_unity3d_average")) return "依赖 Unity3D 平均修改时间更旧";
  if (deleteReasons.has("missing_items")) return "缺少其它候选包含的物品";
  if (deleteReasons.has("no_unique_items")) {
    if (deleteReasons.has("smaller_file")) return "没有独有物品，且文件更小";
    if (reasons.has("largest_file") === false) return "没有独有物品";
  }
  if (deleteReasons.has("lower_completeness")) return "完整度低于推荐保留项";
  if (deleteReasons.has("older_version")) return "版本低于推荐保留项";
  if (deleteReasons.has("smaller_file")) return "文件小于推荐保留项";
  if (reasons.has("newer_unity3d_average") && duplicateIsStrictBest(candidate, "unity3d_average_modified_score")) return "依赖 Unity3D 平均修改时间更新";
  if (reasons.has("most_complete") && duplicateIsStrictBest(candidate, "completeness_score")) return "完整度最高";
  if (candidate.is_strict_latest_version) return "版本最新";
  if (candidate.is_latest_version) return "版本并列最新";
  if (reasons.has("largest_file") && duplicateIsStrictBest(candidate, "file_size")) return "文件更大";
  if (reasons.has("most_complete")) return "并列最完整";
  if (reasons.has("largest_file")) return "并列文件最大";
  if (candidate.recommended_action === "review") return "存在无法自动判断的差异";
  return "";
}

const overviewSummaryCards = computed(() => {
  if (gameDirStatus.value !== "目录有效") return [];

  const cards = [];
  if (cardLibrary.checked && cardLibrary.validGameDir && Number.isFinite(stats.cards)) {
    cards.push({
      key: "cards",
      label: "人物卡",
      value: stats.cards,
      action: "characters"
    });
  }
  if (Number.isFinite(stats.clothesCards)) {
    cards.push({
      key: "clothes",
      label: "服装卡",
      value: stats.clothesCards,
      action: "characters",
      cardBrowserMode: "clothes"
    });
  }
  if (Number.isFinite(stats.sceneCards)) {
    cards.push({
      key: "scene",
      label: "场景卡",
      value: stats.sceneCards,
      action: "characters",
      cardBrowserMode: "scene"
    });
  }
  if (modDatabase.checked && modDatabase.exists && Number.isFinite(modDatabase.total)) {
    cards.push({
      key: "zipmods",
      label: "模组",
      value: modDatabase.total,
      action: "mods",
      libraryMode: "mods"
    });
  }
  if (itemDatabase.checked && itemDatabase.exists && Number.isFinite(stats.modItems)) {
    cards.push({
      key: "items",
      label: "物品",
      value: Number(stats.modItems || 0) + Number(stats.builtinItems || 0),
      action: "mods",
      libraryMode: "items"
    });
  }
  if (Number.isFinite(stats.plugins)) {
    cards.push({
      key: "plugins",
      label: "插件",
      value: stats.plugins,
      action: "plugins"
    });
  }
  return cards;
});
const cardFolderDisplay = computed(() => {
  const suffix = selectedCardFolder.value ? `/${selectedCardFolder.value}` : "";
  return `UserData/chara${suffix}`;
});

function backendAssetUrl(path) {
  if (!path) return "";
  if (/^https?:\/\//i.test(path)) return path;
  const baseUrl = window.desktopApi?.backendBaseUrl || "http://127.0.0.1:8765";
  return `${baseUrl}${path}`;
}

function mapCharacterCardRows(rows) {
  return (rows || []).map((card) => ({
    id: card.id,
    name: card.name || card.filename,
    filename: card.filename,
    absolutePath: card.absolute_path,
    relativePath: card.relative_path,
    thumbnailUrl: backendAssetUrl(card.thumbnail_url),
    coverUrl: backendAssetUrl(card.cover_url || card.thumbnail_url),
    modifiedAt: card.modified_at ? new Date(card.modified_at * 1000).toLocaleDateString() : "",
    dependencyCount: card.dependency_count == null ? null : Number(card.dependency_count),
    missingCount: card.missing_count == null ? null : Number(card.missing_count),
    favorite: Boolean(card.favorite),
    rating: Math.min(5, Math.max(0, Number(card.rating) || 0)),
    tags: Array.isArray(card.tags) ? card.tags.map((tag) => String(tag)) : []
  }));
}

function mapClothesCardRows(rows) {
  return (rows || []).map((card) => ({
    id: card.id,
    name: card.name || card.filename,
    filename: card.filename,
    absolutePath: card.absolute_path,
    relativePath: card.relative_path,
    directory: card.directory || "",
    thumbnailUrl: backendAssetUrl(card.thumbnail_url),
    coverUrl: backendAssetUrl(card.cover_url || card.thumbnail_url),
    modifiedAt: card.modified_at ? new Date(card.modified_at * 1000).toLocaleDateString() : "",
    modifiedTimestamp: Number(card.modified_at || 0),
    fileSize: Number(card.file_size || 0),
    clothesPartCount: Number(card.clothes_part_count || 0),
    accessoryPartCount: Number(card.accessory_part_count || 0),
    dependencyCount: Number(card.dependency_count || 0),
    pluginCount: Number(card.plugin_count || 0)
  }));
}

function mapSceneCardRows(rows) {
  return (rows || []).map((card) => ({
    id: card.id,
    name: card.name || card.filename,
    filename: card.filename,
    absolutePath: card.absolute_path,
    relativePath: card.relative_path,
    directory: card.directory || "",
    thumbnailUrl: backendAssetUrl(card.thumbnail_url),
    coverUrl: backendAssetUrl(card.cover_url || card.thumbnail_url),
    modifiedAt: card.modified_at ? new Date(card.modified_at * 1000).toLocaleDateString() : "",
    modifiedTimestamp: Number(card.modified_at || 0),
    fileSize: Number(card.file_size || 0),
    dependencyCount: Number(card.dependency_count || 0)
  }));
}

function flattenClothesTree(node, depth = 0, expanded = expandedClothesFolders.value) {
  if (!node) return [];
  const relativePath = node.relative_path || "";
  const children = Array.isArray(node.children) ? node.children : [];
  const hasChildren = Boolean(node.has_children || children.length);
  const row = {
    id: node.id,
    name: node.name,
    relativePath,
    count: Number(node.count || 0),
    depth,
    hasChildren,
    expanded: hasChildren && expanded.has(relativePath)
  };
  if (!row.expanded) return [row];
  return [row, ...children.flatMap((child) => flattenClothesTree(child, depth + 1, expanded))];
}

function collectExpandableClothesFolderPaths(node, output = new Set()) {
  if (!node) return output;
  const children = Array.isArray(node.children) ? node.children : [];
  if (node.has_children || children.length) output.add(node.relative_path || "");
  for (const child of children) collectExpandableClothesFolderPaths(child, output);
  return output;
}

function flattenSceneTree(node, depth = 0, expanded = expandedSceneFolders.value) {
  if (!node) return [];
  const relativePath = node.relative_path || "";
  const children = Array.isArray(node.children) ? node.children : [];
  const hasChildren = Boolean(node.has_children || children.length);
  const row = {
    id: node.id,
    name: node.name,
    relativePath,
    count: Number(node.count || 0),
    depth,
    hasChildren,
    expanded: hasChildren && expanded.has(relativePath)
  };
  if (!row.expanded) return [row];
  return [row, ...children.flatMap((child) => flattenSceneTree(child, depth + 1, expanded))];
}

function collectExpandableSceneFolderPaths(node, output = new Set()) {
  if (!node) return output;
  const children = Array.isArray(node.children) ? node.children : [];
  if (node.has_children || children.length) output.add(node.relative_path || "");
  for (const child of children) collectExpandableSceneFolderPaths(child, output);
  return output;
}

function refreshVisibleSceneFolders() {
  sceneFolders.value = flattenSceneTree(sceneTree.value);
}

function resetSceneTree() {
  sceneTree.value = null;
  sceneFolders.value = [];
  expandedSceneFolders.value = new Set();
}

function refreshVisibleClothesFolders() {
  clothesFolders.value = flattenClothesTree(clothesTree.value);
}

function resetClothesTree() {
  clothesTree.value = null;
  clothesFolders.value = [];
  expandedClothesFolders.value = new Set();
}

function scheduleClothesTreeRefresh() {
  window.clearTimeout(clothesTreeRefreshTimer);
  clothesTreeRefreshTimer = window.setTimeout(() => {
    clothesTreeRefreshTimer = 0;
    if (!clothesLibrary.treeIndexing || !backendReady.value || !paths.gameDir) return;
    void refreshClothesTreeCounts();
  }, 500);
}

async function refreshClothesTreeCounts() {
  if (!clothesLibrary.validGameDir || !backendReady.value || !paths.gameDir) return;
  try {
    const result = await window.desktopApi?.backendRequest?.(
      `/library/clothes/tree?game_dir=${encodeQuery(paths.gameDir)}`
    );
    if (!result?.ok || !result.is_valid_game_dir) return;
    clothesTree.value = result.tree || null;
    clothesLibrary.treeIndexing = Boolean(result.indexing);
    stats.clothesCards = clothesLibrary.treeIndexing ? null : Number(result.total || 0);
    refreshVisibleClothesFolders();
    const selectedFolder = clothesFolders.value.find(
      (folder) => folder.relativePath === selectedClothesFolder.value
    );
    if (selectedFolder) {
      clothesLibrary.total = selectedFolder.count;
    }
    if (clothesLibrary.treeIndexing) scheduleClothesTreeRefresh();
  } catch (error) {
    log(`[Clothes Tree Error] ${error.message}`);
  }
}

function toggleClothesFolder(folder) {
  if (!folder?.hasChildren) return;
  const next = new Set(expandedClothesFolders.value);
  if (next.has(folder.relativePath)) next.delete(folder.relativePath);
  else next.add(folder.relativePath);
  expandedClothesFolders.value = next;
  refreshVisibleClothesFolders();
}

async function selectClothesFolder(relativePath = "") {
  resetCardLibraryScrollPosition("clothes");
  const requestId = ++clothesListRequestId;
  window.clearTimeout(clothesIndexRetryTimer);
  clothesIndexRetryTimer = 0;
  selectedClothesFolder.value = relativePath || "";
  selectedClothesDetailPath.value = "";
  selectedClothesDetail.value = null;
  clothesDetailTab.value = "详情";
  clothesCards.value = [];
  clothesLibrary.total = selectedClothesFolderRow.value?.count ?? null;
  clothesLibrary.indexing = false;
  clothesLibrary.nextOffset = 0;
  clothesLibrary.hasMore = false;
  clothesLibrary.loadingMore = false;
  if (!backendReady.value || !paths.gameDir || !clothesLibrary.validGameDir) return;

  clothesLibrary.loading = true;
  clothesLibrary.error = "";
  try {
    const result = await window.desktopApi?.backendRequest?.(
      `/library/clothes?game_dir=${encodeQuery(paths.gameDir)}&path=${encodeQuery(selectedClothesFolder.value)}&offset=0&limit=${CLOTHES_CARD_PAGE_SIZE}`
    );
    if (requestId !== clothesListRequestId) return;
    if (!result?.ok) throw new Error(result?.error || "服装卡列表读取失败");
    clothesCards.value = mapClothesCardRows(result.cards);
    if (result.total != null) {
      clothesLibrary.total = Number(result.total);
    }
    clothesLibrary.indexing = Boolean(result.indexing);
    clothesLibrary.nextOffset = clothesCards.value.length;
    clothesLibrary.hasMore = Boolean(result.has_more);
    if (clothesLibrary.indexing && clothesCards.value.length < CLOTHES_CARD_PAGE_SIZE) {
      scheduleClothesIndexRetry(requestId);
    }
  } catch (error) {
    if (requestId !== clothesListRequestId) return;
    clothesLibrary.error = error.message;
    clothesCards.value = [];
    log(`[Clothes Cards Error] ${error.message}`);
  } finally {
    if (requestId === clothesListRequestId) clothesLibrary.loading = false;
  }
}

function scheduleClothesIndexRetry(requestId) {
  window.clearTimeout(clothesIndexRetryTimer);
  clothesIndexRetryTimer = window.setTimeout(() => {
    clothesIndexRetryTimer = 0;
    if (requestId !== clothesListRequestId || !clothesLibrary.indexing) return;
    void loadMoreClothesCards();
  }, 280);
}

async function loadMoreClothesCards() {
  if (
    clothesLibrary.loading
    || clothesLibrary.loadingMore
    || !clothesLibrary.hasMore
    || !backendReady.value
    || !paths.gameDir
    || !clothesLibrary.validGameDir
  ) return;

  const requestId = clothesListRequestId;
  const offset = clothesLibrary.nextOffset || clothesCards.value.length;
  clothesLibrary.loadingMore = true;
  try {
    const result = await window.desktopApi?.backendRequest?.(
      `/library/clothes?game_dir=${encodeQuery(paths.gameDir)}&path=${encodeQuery(selectedClothesFolder.value)}&offset=${offset}&limit=${CLOTHES_CARD_PAGE_SIZE}`
    );
    if (requestId !== clothesListRequestId) return;
    if (!result?.ok) throw new Error(result?.error || "更多服装卡读取失败");
    const nextCards = mapClothesCardRows(result.cards);
    clothesCards.value = [...clothesCards.value, ...nextCards];
    if (result.total != null) {
      clothesLibrary.total = Number(result.total);
    }
    clothesLibrary.indexing = Boolean(result.indexing);
    clothesLibrary.nextOffset = offset + nextCards.length;
    clothesLibrary.hasMore = Boolean(result.has_more);
    if (clothesLibrary.indexing && nextCards.length < CLOTHES_CARD_PAGE_SIZE) {
      scheduleClothesIndexRetry(requestId);
    }
  } catch (error) {
    if (requestId !== clothesListRequestId) return;
    clothesLibrary.error = error.message;
    log(`[Clothes Cards Error] ${error.message}`);
  } finally {
    if (requestId === clothesListRequestId) clothesLibrary.loadingMore = false;
  }
}

function handleClothesCardGridScroll(event) {
  const element = event?.currentTarget;
  if (!element || element.scrollHeight - element.scrollTop - element.clientHeight > 900) return;
  void loadMoreClothesCards();
}

async function loadClothesTree({ force = false } = {}) {
  if (clothesLibrary.loading) return;
  clothesLibrary.checked = true;
  clothesLibrary.loading = true;
  clothesLibrary.error = "";
  if (!backendReady.value || !paths.gameDir) {
    clothesLibrary.validGameDir = false;
    stats.clothesCards = null;
    clothesCards.value = [];
    resetClothesTree();
    clothesLibrary.loading = false;
    return;
  }

  try {
    const refreshQuery = force ? "&refresh=1" : "";
    const result = await window.desktopApi?.backendRequest?.(
      `/library/clothes/tree?game_dir=${encodeQuery(paths.gameDir)}${refreshQuery}`
    );
    if (!result?.ok) throw new Error(result?.error || "服装卡目录读取失败");
    clothesLibrary.validGameDir = Boolean(result.is_valid_game_dir);
    clothesLibrary.root = result.root || "";
    if (!clothesLibrary.validGameDir) {
      stats.clothesCards = null;
      clothesLibrary.error = result.error || "未找到 UserData/coordinate 服装卡目录";
      clothesCards.value = [];
      resetClothesTree();
      return;
    }
    clothesTree.value = result.tree || null;
    clothesLibrary.treeIndexing = Boolean(result.indexing);
    stats.clothesCards = clothesLibrary.treeIndexing ? null : Number(result.total || 0);
    expandedClothesFolders.value = collectExpandableClothesFolderPaths(clothesTree.value);
    refreshVisibleClothesFolders();
    if (clothesLibrary.treeIndexing) scheduleClothesTreeRefresh();
    const folderExists = clothesFolders.value.some((folder) => folder.relativePath === selectedClothesFolder.value);
    await selectClothesFolder(folderExists ? selectedClothesFolder.value : "");
  } catch (error) {
    stats.clothesCards = null;
    clothesLibrary.validGameDir = false;
    clothesLibrary.error = error.message;
    clothesCards.value = [];
    resetClothesTree();
    log(`[Clothes Cards Error] ${error.message}`);
  } finally {
    clothesLibrary.loading = false;
  }
}

async function ensureClothesLibraryLoaded({ force = false } = {}) {
  if (!backendReady.value || !paths.gameDir) return false;
  if (!force && clothesLibrary.checked && clothesLibrary.validGameDir && clothesTree.value) return true;
  if (clothesLibrary.loading) return false;
  await loadClothesTree({ force });
  return clothesLibrary.validGameDir && Boolean(clothesTree.value);
}

async function refreshClothesCards() {
  if (clothesLibrary.loading || !clothesLibrary.validGameDir) return;
  await ensureClothesLibraryLoaded({ force: true });
}

async function handleClothesCardClick(card) {
  if (!card?.relativePath || clothesLibrary.detailLoading) return;
  clothesSideMode.value = "detail";
  selectedClothesDetailPath.value = card.relativePath;
  selectedClothesDetail.value = card;
  clothesLibrary.detailLoading = true;
  try {
    const result = await window.desktopApi?.backendRequest?.(
      `/library/clothes/detail?game_dir=${encodeQuery(paths.gameDir)}&path=${encodeQuery(card.relativePath)}`
    );
    if (!result?.ok) throw new Error(result?.error || "服装卡详情读取失败");
    const detail = result.card || {};
    selectedClothesDetail.value = {
      ...card,
      ...detail,
      thumbnailUrl: backendAssetUrl(detail.thumbnail_url || detail.thumbnailUrl || card.thumbnailUrl),
      coverUrl: backendAssetUrl(detail.cover_url || detail.coverUrl || card.coverUrl),
      dependencies: Array.isArray(detail.dependencies)
        ? detail.dependencies.map((dependency) => ({
            ...dependency,
            item: dependency.item
              ? {
                  ...dependency.item,
                  kind: itemKindLabel(dependency.item.kind),
                  thumbnailUrl: backendAssetUrl(dependency.item.thumbnail_url)
                }
              : null
          }))
        : [],
      modifiedAt: detail.modified_at ? new Date(detail.modified_at * 1000).toLocaleDateString() : card.modifiedAt,
      modifiedTimestamp: Number(detail.modified_at || card.modifiedTimestamp),
      fileSize: Number(detail.file_size || card.fileSize)
    };
  } catch (error) {
    clothesLibrary.error = error.message;
    log(`[Clothes Card Detail Error] ${error.message}`);
  } finally {
    clothesLibrary.detailLoading = false;
  }
}

function toggleSceneFolder(folder) {
  if (!folder?.hasChildren) return;
  const next = new Set(expandedSceneFolders.value);
  if (next.has(folder.relativePath)) next.delete(folder.relativePath);
  else next.add(folder.relativePath);
  expandedSceneFolders.value = next;
  refreshVisibleSceneFolders();
}

async function selectSceneFolder(relativePath = "") {
  resetCardLibraryScrollPosition("scene");
  const requestId = ++sceneListRequestId;
  selectedSceneFolder.value = relativePath || "";
  selectedSceneDetailPath.value = "";
  selectedSceneDetail.value = null;
  sceneDetailTab.value = "详情";
  sceneCards.value = [];
  sceneLibrary.total = selectedSceneFolderRow.value?.count ?? null;
  sceneLibrary.nextOffset = 0;
  sceneLibrary.hasMore = false;
  sceneLibrary.loadingMore = false;
  if (!backendReady.value || !paths.gameDir || !sceneLibrary.validGameDir) return;

  sceneLibrary.loading = true;
  sceneLibrary.error = "";
  try {
    const result = await window.desktopApi?.backendRequest?.(
      `/library/scene?game_dir=${encodeQuery(paths.gameDir)}&path=${encodeQuery(selectedSceneFolder.value)}&offset=0&limit=${SCENE_CARD_PAGE_SIZE}`
    );
    if (requestId !== sceneListRequestId) return;
    if (!result?.ok) throw new Error(result?.error || "场景卡列表读取失败");
    sceneCards.value = mapSceneCardRows(result.cards);
    if (result.total != null) sceneLibrary.total = Number(result.total);
    sceneLibrary.nextOffset = sceneCards.value.length;
    sceneLibrary.hasMore = Boolean(result.has_more);
  } catch (error) {
    if (requestId !== sceneListRequestId) return;
    sceneLibrary.error = error.message;
    sceneCards.value = [];
    log(`[Scene Cards Error] ${error.message}`);
  } finally {
    if (requestId === sceneListRequestId) sceneLibrary.loading = false;
  }
}

async function loadMoreSceneCards() {
  if (
    sceneLibrary.loading
    || sceneLibrary.loadingMore
    || !sceneLibrary.hasMore
    || !backendReady.value
    || !paths.gameDir
    || !sceneLibrary.validGameDir
  ) return;

  const requestId = sceneListRequestId;
  const offset = sceneLibrary.nextOffset || sceneCards.value.length;
  sceneLibrary.loadingMore = true;
  try {
    const result = await window.desktopApi?.backendRequest?.(
      `/library/scene?game_dir=${encodeQuery(paths.gameDir)}&path=${encodeQuery(selectedSceneFolder.value)}&offset=${offset}&limit=${SCENE_CARD_PAGE_SIZE}`
    );
    if (requestId !== sceneListRequestId) return;
    if (!result?.ok) throw new Error(result?.error || "更多场景卡读取失败");
    const nextCards = mapSceneCardRows(result.cards);
    sceneCards.value = [...sceneCards.value, ...nextCards];
    if (result.total != null) sceneLibrary.total = Number(result.total);
    sceneLibrary.nextOffset = offset + nextCards.length;
    sceneLibrary.hasMore = Boolean(result.has_more);
  } catch (error) {
    if (requestId !== sceneListRequestId) return;
    sceneLibrary.error = error.message;
    log(`[Scene Cards Error] ${error.message}`);
  } finally {
    if (requestId === sceneListRequestId) sceneLibrary.loadingMore = false;
  }
}

function handleSceneCardGridScroll(event) {
  const element = event?.currentTarget;
  if (!element || element.scrollHeight - element.scrollTop - element.clientHeight > 900) return;
  void loadMoreSceneCards();
}

async function loadSceneTree({ force = false } = {}) {
  if (!force && sceneLibrary.loading) return;
  sceneLibrary.checked = true;
  sceneLibrary.loading = true;
  sceneLibrary.error = "";
  if (!backendReady.value || !paths.gameDir) {
    sceneLibrary.validGameDir = false;
    stats.sceneCards = null;
    sceneCards.value = [];
    resetSceneTree();
    sceneLibrary.loading = false;
    return;
  }

  try {
    const result = await window.desktopApi?.backendRequest?.(
      `/library/scene/tree?game_dir=${encodeQuery(paths.gameDir)}`
    );
    if (!result?.ok) throw new Error(result?.error || "场景卡目录读取失败");
    sceneLibrary.validGameDir = Boolean(result.is_valid_game_dir);
    sceneLibrary.root = result.root || "";
    if (!sceneLibrary.validGameDir) {
      stats.sceneCards = null;
      sceneLibrary.error = result.error || "未找到 UserData/studio/scene 场景卡目录";
      sceneCards.value = [];
      resetSceneTree();
      return;
    }
    sceneTree.value = result.tree || null;
    stats.sceneCards = Number(result.total || 0);
    expandedSceneFolders.value = collectExpandableSceneFolderPaths(sceneTree.value);
    refreshVisibleSceneFolders();
    const folderExists = sceneFolders.value.some((folder) => folder.relativePath === selectedSceneFolder.value);
    await selectSceneFolder(folderExists ? selectedSceneFolder.value : "");
  } catch (error) {
    stats.sceneCards = null;
    sceneLibrary.validGameDir = false;
    sceneLibrary.error = error.message;
    sceneCards.value = [];
    resetSceneTree();
    log(`[Scene Cards Error] ${error.message}`);
  } finally {
    sceneLibrary.loading = false;
  }
}

async function ensureSceneLibraryLoaded({ force = false } = {}) {
  if (!backendReady.value || !paths.gameDir) return false;
  if (!force && sceneLibrary.checked && sceneLibrary.validGameDir && sceneTree.value) return true;
  if (sceneLibrary.loading) return false;
  await loadSceneTree({ force });
  return sceneLibrary.validGameDir && Boolean(sceneTree.value);
}

async function refreshSceneCards() {
  if (sceneLibrary.loading || !sceneLibrary.validGameDir) return;
  await ensureSceneLibraryLoaded({ force: true });
}

async function loadSelectedSceneDetail(card = selectedSceneCard.value) {
  if (!card?.relativePath || sceneLibrary.detailLoading) return;
  sceneLibrary.detailLoading = true;
  const targetPath = card.relativePath;
  try {
    const result = await window.desktopApi?.backendRequest?.(
      `/library/scene/detail?game_dir=${encodeQuery(paths.gameDir)}&path=${encodeQuery(card.relativePath)}`
    );
    if (!result?.ok) throw new Error(result?.error || "场景卡详情读取失败");
    const detail = result.card || {};
    if (selectedSceneDetailPath.value === targetPath) {
      selectedSceneDetail.value = {
        ...card,
        ...detail,
        thumbnailUrl: backendAssetUrl(detail.thumbnail_url || detail.thumbnailUrl || card.thumbnailUrl),
        coverUrl: backendAssetUrl(detail.cover_url || detail.coverUrl || card.coverUrl),
        dependencies: Array.isArray(detail.dependencies)
          ? detail.dependencies.map((dependency) => ({
              ...dependency,
              item: dependency.item
                ? {
                    ...dependency.item,
                    kind: itemKindLabel(dependency.item.kind),
                    thumbnailUrl: backendAssetUrl(dependency.item.thumbnail_url)
                  }
                : null
            }))
          : [],
        modifiedAt: detail.modified_at ? new Date(detail.modified_at * 1000).toLocaleDateString() : card.modifiedAt,
        modifiedTimestamp: Number(detail.modified_at || card.modifiedTimestamp),
        fileSize: Number(detail.file_size || card.fileSize)
      };
      void loadCardDependencyRemoteCandidates(targetPath, selectedSceneDetail.value.dependencies, { scene: true });
    }
  } catch (error) {
    sceneLibrary.error = error.message;
    log(`[Scene Card Detail Error] ${error.message}`);
  } finally {
    sceneLibrary.detailLoading = false;
  }
}

async function handleSceneCardClick(card) {
  if (!card?.relativePath || sceneLibrary.detailLoading) return;
  sceneSideMode.value = "detail";
  selectedSceneDetailPath.value = card.relativePath;
  selectedSceneDetail.value = card;
  cardDependencyRemote.loading = false;
  cardDependencyRemote.error = "";
  cardDependencyRemote.byGuid = {};
  cardDependencyRemote.busyGuids = {};
  cardDependencyRemote.notices = {};
  await loadSelectedSceneDetail(card);
}

async function refreshCharacterCardsAfterDatabaseBuild() {
  if (!backendReady.value || !paths.gameDir || !cardLibrary.checked) return;
  await loadCardTree();
}

function badgeClass(value) {
  if (value === "警告") return "warn";
  if (["ready", "正常", "Done", "目录有效"].includes(value)) return "ok";
  if (["thumb", "missing", "重复标识", "42%"].includes(value)) return "warn";
  if (["error", "parse", "错误", "读取失败", "检查失败", "Error"].includes(value)) return "danger";
  return "neutral";
}

function diagnosticIssueBadgeStatus(issue) {
  if (issue?.type === "unity3d" && ["missing", "error"].includes(issue?.status)) return "error";
  return "thumb";
}

function timestampLogMessage(message) {
  const now = new Date();
  const timestamp = new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false
  }).format(now);
  return `[${timestamp}] ${message}`;
}

function log(message) {
  logs.value = [...logs.value, timestampLogMessage(message)];
}

function formatDurationMs(durationMs) {
  return `${durationMs >= 100 ? durationMs.toFixed(0) : durationMs.toFixed(1)} ms`;
}

function formatTaskDuration(durationMs) {
  const value = Number(durationMs);
  if (!Number.isFinite(value) || value < 0) return "-";
  if (value < 1000) return formatDurationMs(value);
  const seconds = value / 1000;
  if (seconds < 60) return `${seconds.toFixed(1)} 秒`;
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds - minutes * 60;
  return `${minutes} 分 ${remainder.toFixed(1)} 秒`;
}

function taskElapsedMs(task) {
  const recorded = Number(task?.data?.timings?.total_ms);
  if (Number.isFinite(recorded) && recorded >= 0) return recorded;
  const started = Number(task?.created_at);
  const finished = Number(task?.finished_at || task?.updated_at);
  if (!Number.isFinite(started) || !Number.isFinite(finished)) return 0;
  return Math.max(0, (finished - started) * 1000);
}

function formatTaskTimestamp(value) {
  const timestamp = Number(value);
  if (!Number.isFinite(timestamp) || timestamp <= 0) return "-";
  return new Date(timestamp * 1000).toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false
  });
}

function taskTimingRows(task) {
  const timings = task?.data?.timings || {};
  if (task?.task_type === "build_mod_database") {
    return [
      ["原版资源索引", timings.builtin_resource_index_ms],
      ["zipmod 扫描", timings.zipmod_scan_ms],
      ["物品解析与缩略图", timings.item_parse_ms],
      ["模组数据库写入", timings.database_write_ms],
      ["人物卡数据库", timings.character_card_database_ms],
      ["总耗时", timings.total_ms]
    ].filter(([, value]) => Number.isFinite(Number(value)));
  }
  return Number.isFinite(Number(timings.total_ms))
    ? [["总耗时", timings.total_ms]]
    : [];
}

function taskResultRows(task) {
  if (task?.task_type !== "build_mod_database") return [];
  const stats = task.data?.stats || {};
  const cardStats = task.data?.card_stats || {};
  return [
    ["主 zipmod", stats.primary_zipmods],
    ["物品", stats.mod_items],
    ["重复 zipmod", stats.duplicate_zipmods],
    ["人物卡", cardStats.cards],
    ["人物卡依赖", cardStats.dependencies],
    ["缺失依赖", cardStats.missing_dependencies]
  ].filter(([, value]) => value !== undefined && value !== null);
}

function snapshotTask(task) {
  if (!task) return null;
  return {
    ...task,
    messages: Array.isArray(task.messages) ? [...task.messages] : [],
    data: task.data && typeof task.data === "object" ? { ...task.data } : {}
  };
}

function openTaskDetails(task) {
  selectedTask.value = snapshotTask(task?.task || task);
}

async function measureStep(label, action, { logStart = false } = {}) {
  const startedAt = performance.now();
  if (logStart) {
    log(`[Startup] ${label} started`);
  }
  try {
    const result = await action();
    log(`[Startup] ${label} completed in ${formatDurationMs(performance.now() - startedAt)}`);
    return result;
  } catch (error) {
    log(
      `[Startup] ${label} failed in ${formatDurationMs(performance.now() - startedAt)}: ${
        error?.message || error
      }`
    );
    throw error;
  }
}

function taskStatusLabel(task) {
  if (task.status === "completed") return "Done";
  if (task.status === "cancelled") return "已取消";
  if (task.status === "failed") return "Error";
  return formatProgressPercent(task.progress);
}

function taskStatusClass(task) {
  if (task.status === "completed") return "ok";
  if (task.status === "cancelled") return "danger";
  if (task.status === "failed") return "danger";
  return "warn";
}

function latestTaskMessage(task) {
  const messages = Array.isArray(task?.messages) ? task.messages : [];
  return messages.length ? String(messages[messages.length - 1] || "") : "";
}

const DATABASE_TASK_STAGE_DURATIONS = [
  { label: "原版资源索引", seconds: 2.5 },
  { label: "zipmod 扫描", seconds: 70.6 },
  { label: "物品解析与缩略图", seconds: 472.9 },
  { label: "模组数据库写入", seconds: 1.1 },
  { label: "人物卡数据库", seconds: 65.9 }
];
const DATABASE_TASK_TOTAL_SECONDS = DATABASE_TASK_STAGE_DURATIONS.reduce(
  (total, stage) => total + stage.seconds,
  0
);
let databaseTaskElapsedSeconds = 0;
const DATABASE_TASK_STAGE_BOUNDARIES = DATABASE_TASK_STAGE_DURATIONS.map((stage) => {
  databaseTaskElapsedSeconds += stage.seconds;
  return {
    label: stage.label,
    // The backend task state is rounded to one decimal place. Keep the
    // label boundary in the same space so a boundary update does not switch
    // stages one polling tick too early or too late.
    end: Number((databaseTaskElapsedSeconds / DATABASE_TASK_TOTAL_SECONDS * 100).toFixed(1))
  };
});

function databaseTaskStage(task) {
  const rawProgress = Number(task?.progress);
  const progress = Number.isFinite(rawProgress) ? Math.max(0, Math.min(100, rawProgress)) : 0;
  return DATABASE_TASK_STAGE_BOUNDARIES.find((stage) => progress <= stage.end)?.label
    || DATABASE_TASK_STAGE_BOUNDARIES.at(-1).label;
}

function databaseTaskHint(task) {
  if (task?.status === "queued") return "等待后端开始处理";
  return databaseTaskStage(task);
}

function taskSummary(task) {
  if (task.task_type === "export_character_dependency_package") {
    const archive = task.data?.compressed ? "压缩包" : "文件夹";
    return `已生成${archive}，包含 ${task.data?.exported_zipmod_count ?? 0} 个 zipmod`;
  }
  if (task.task_type === "extract_mods") {
    const count = task.data?.card_paths?.length ?? task.data?.card_count ?? selectedCount.value;
    return `${count} 张人物卡 · ${String(extractMode.value || "copy").toUpperCase()} 模式`;
  }
  if (task.task_type === "build_mod_database") {
    const zipmods = task.data?.stats?.primary_zipmods;
    const elapsed = task.data?.timings?.total_ms;
    if (!zipmods) return taskHint.value;
    return `已索引 ${zipmods} 个 zipmod${elapsed ? ` · ${formatTaskDuration(elapsed)}` : ""}`;
  }
  if (task.task_type === "build_card_database") {
    const cards = task.data?.stats?.changed_cards;
    return cards == null ? taskHint.value : `已重新扫描 ${cards} 张人物卡`;
  }
  if (task.task_type === "bulk_export_zipmods") {
    const unity3dCount = task.data?.exported_unity3d_count ?? 0;
    return `已导出 ${task.data?.exported_count ?? task.data?.selected_count ?? 0} 个 zipmod，包含 ${unity3dCount} 个 unity3d`;
  }
  if (task.task_type === "bulk_organize_zipmods") {
    return `按作者整理 ${task.data?.exported_count ?? task.data?.selected_count ?? 0} 个 zipmod`;
  }
  if (task.task_type === "organize_all_zipmods_by_author") {
    return `已移动 ${task.data?.moved_count ?? 0} 个 zipmod，删除 ${task.data?.removed_empty_dir_count ?? 0} 个空目录`;
  }
  if (task.task_type === "bulk_repair_zipmods_unity3d") {
    return `已修复 ${task.data?.repaired_count ?? 0} 个，跳过 ${task.data?.skipped_count ?? 0} 个`;
  }
  if (task.task_type === "bulk_cleanup_duplicate_zipmods") {
    return `已清理 ${task.data?.cleaned_duplicate_count ?? 0} 个重复文件，跳过 ${task.data?.skipped_count ?? 0} 个`;
  }
  if (task.task_type === "bulk_delete_character_cards") {
    return `已删除 ${task.data?.deleted_count ?? 0} 张，失败 ${task.data?.failure_count ?? 0} 张`;
  }
  if (task.task_type === "bulk_add_character_card_tags") {
    return `已添加 ${task.data?.updated_count ?? 0} 张，失败 ${task.data?.failure_count ?? 0} 张`;
  }
  if (task.task_type === "import_external_zipmods") {
    return `导入 ${task.data?.imported_count ?? 0} 个（zip→zipmod ${task.data?.zip_renamed_count ?? 0} 个），替换 ${task.data?.promoted_count ?? 0} 个，补入 ${task.data?.unity3d_repaired_count ?? 0} 个 unity3d，角色卡 ${task.data?.card_imported_count ?? 0} 张，服装卡 ${task.data?.coordinate_imported_count ?? 0} 张`;
  }
  if (task.task_type === "bulk_update_zipmod_authors") {
    return `已更新 ${task.data?.updated_count ?? 0} 个`;
  }
  if (task.task_type === "bulk_apply_item_thumbnail") {
    return `已导入 ${task.data?.imported_count ?? 0} 个`;
  }
  if (task.task_type === "check_game_dir") {
    if (typeof task.data?.is_valid !== "boolean") return "检查中";
    return task.data.is_valid ? "目录有效" : "目录无效";
  }
  return task.status || "等待执行";
}

function reserveTaskSubmissionOrder() {
  const order = nextTaskSubmissionOrder;
  nextTaskSubmissionOrder += 1;
  return order;
}

function rememberTask(task, submissionOrder = null) {
  if (!task?.id) return;
  const snapshot = snapshotTask(task);
  const existingIndex = recentTasks.value.findIndex((entry) => entry.id === task.id);
  const existing = existingIndex >= 0 ? recentTasks.value[existingIndex] : null;
  const order = Number.isFinite(existing?.submissionOrder)
    ? existing.submissionOrder
    : Number.isFinite(submissionOrder)
      ? submissionOrder
      : reserveTaskSubmissionOrder();
  const item = {
    id: task.id,
    title: task.title || task.task_type || "任务",
    summary: taskSummary(task),
    label: taskStatusLabel(task),
    badgeClass: taskStatusClass(task),
    submissionOrder: order,
    task: snapshot
  };
  if (existingIndex >= 0) {
    const nextTasks = [...recentTasks.value];
    nextTasks[existingIndex] = item;
    recentTasks.value = nextTasks;
  } else {
    const insertIndex = recentTasks.value.findIndex(
      (entry) => !Number.isFinite(entry.submissionOrder) || entry.submissionOrder < order
    );
    const nextTasks = [...recentTasks.value];
    if (insertIndex < 0) {
      nextTasks.push(item);
    } else {
      nextTasks.splice(insertIndex, 0, item);
    }
    recentTasks.value = nextTasks;
  }
  if (selectedTask.value?.id === task.id) selectedTask.value = snapshot;
}

function encodeQuery(value) {
  return encodeURIComponent(String(value || ""));
}

function formatProfileValue(value) {
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "boolean") return value ? "true" : "false";
  if (value === null || value === undefined || value === "") return "-";
  return String(value);
}

function formatStat(value) {
  return Number.isFinite(value) ? value.toLocaleString() : "-";
}

function formatBytes(value) {
  const bytes = Number(value || 0);
  if (!Number.isFinite(bytes) || bytes <= 0) return "-";
  const units = ["B", "KB", "MB", "GB"];
  let size = bytes;
  let index = 0;
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024;
    index += 1;
  }
  return `${size.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function formatDatabaseTime(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function openSummaryCard(card) {
  if (card.cardBrowserMode) {
    setCardBrowserMode(card.cardBrowserMode);
    return;
  }
  if (card.libraryMode) setLibraryMode(card.libraryMode);
  if (card.action) activeView.value = card.action;
}

function formatPersonality(value) {
  const personalityId = Number(value);
  if (Number.isInteger(personalityId) && PERSONALITY_LABELS[personalityId]) {
    return PERSONALITY_LABELS[personalityId];
  }
  return formatProfileValue(value);
}

function formatCharacterSex(value) {
  const sexId = Number(value);
  if (sexId === 0) return "\u7537";
  if (sexId === 1) return "\u5973";
  return formatProfileValue(value);
}

function formatAchievementProgress(item) {
  if (!item) return "-";
  if (item.unit === "bytes") return `${formatBytes(item.progress)} / 10 GB`;
  if (item.unit === "milestone") return item.unlocked ? "已完成" : "等待完整扫描";
  return `${formatStat(item.progress)} / ${formatStat(item.target)}`;
}

async function loadAchievements({ notify = false } = {}) {
  try {
    const previousUnlocked = new Set(achievements.value.filter((item) => item.unlocked).map((item) => item.id));
    const result = await window.desktopApi?.backendRequest?.("/achievements");
    if (!result?.ok) throw new Error(result?.error || "成就读取失败");
    achievements.value = Array.isArray(result.achievements) ? result.achievements : [];
    Object.assign(achievementPreferences, result.preferences || {});
    if (notify && achievementInitialized.value && achievementPreferences.notifications) {
      const unlocked = achievements.value.find((item) => item.unlocked && !previousUnlocked.has(item.id));
      if (unlocked) {
        achievementToast.value = unlocked;
        window.clearTimeout(achievementToastTimer);
        achievementToastTimer = window.setTimeout(() => { achievementToast.value = null; }, 5000);
      }
    }
    achievementInitialized.value = true;
  } catch (error) {
    log(`[Achievements Error] ${error.message}`);
  }
}

async function updateAchievementPreference(key, value) {
  const result = await window.desktopApi?.backendRequest?.("/achievements/preferences", {
    method: "POST",
    body: { [key]: Boolean(value) }
  });
  if (!result?.ok) return;
  achievements.value = result.achievements || achievements.value;
  Object.assign(achievementPreferences, result.preferences || {});
}

async function resetAchievementHistory() {
  if (!window.confirm("确认重置全部本地成就记录？资源数据库和游戏文件不会被删除。")) return;
  const result = await window.desktopApi?.backendRequest?.("/achievements/reset", { method: "POST", body: {} });
  if (result?.ok) {
    achievements.value = result.achievements || [];
    selectedAchievement.value = null;
  }
}

function clearResourceStats() {
  stats.cards = null;
  stats.zipmods = null;
  stats.missingZipmods = null;
  stats.missingAbdata = null;
  stats.zipmodErrors = null;
  stats.zipmodWarnings = null;
  stats.modItems = null;
  stats.builtinItems = null;
  stats.clothesCards = null;
  stats.sceneCards = null;
  stats.plugins = null;
  stats.duplicateZipmods = null;
  stats.lastDatabaseBuiltAt = "";
}

function flattenCardTree(node, depth = 0, expanded = expandedCardFolders.value) {
  if (!node) return [];
  const relativePath = node.relative_path || "";
  const children = Array.isArray(node.children) ? node.children : [];
  const hasChildren = Boolean(node.has_children || children.length);
  const row = {
    id: node.id,
    name: node.name,
    relativePath,
    count: Number(node.count || 0),
    depth,
    hasChildren,
    expanded: hasChildren && expanded.has(relativePath)
  };
  if (!row.expanded) return [row];
  return [
    row,
    ...children.flatMap((child) => flattenCardTree(child, depth + 1, expanded))
  ];
}

function refreshVisibleCardFolders() {
  cardFolders.value = flattenCardTree(cardTree.value);
}

function collectExpandableCardFolderPaths(node, output = new Set()) {
  if (!node) return output;
  const children = Array.isArray(node.children) ? node.children : [];
  if (node.has_children || children.length) output.add(node.relative_path || "");
  for (const child of children) collectExpandableCardFolderPaths(child, output);
  return output;
}

function flattenManagedMoveTree(node, depth = 0) {
  if (!node) return [];
  const relativePath = String(node.relative_path || "");
  const children = Array.isArray(node.children) ? node.children : [];
  const isManagedRoot = /^(female|male)$/i.test(relativePath);
  const isManagedChild = /^(female|male)\//i.test(relativePath);
  if (!relativePath) {
    return children.flatMap((child) => flattenManagedMoveTree(child, 0));
  }
  if (!isManagedRoot && !isManagedChild) return [];
  if (cardMovePrompt.sourceGender && !new RegExp(`^${cardMovePrompt.sourceGender}(\\/|$)`, "i").test(relativePath)) {
    return [];
  }
  const managedChildren = children.filter((child) => /^(female|male)(\/|$)/i.test(String(child.relative_path || "")));
  const row = {
    id: node.id,
    name: node.name,
    relativePath,
    count: Number(node.count || 0),
    depth,
    hasChildren: managedChildren.length > 0,
    expanded: cardMovePrompt.expanded.has(relativePath),
    isGenderRoot: isManagedRoot
  };
  if (!row.expanded) return [row];
  return [row, ...managedChildren.flatMap((child) => flattenManagedMoveTree(child, depth + 1))];
}

function collectManagedFolderPaths(node, output = [], gender = "") {
  if (!node) return output;
  const relativePath = String(node.relative_path || "");
  const managed = /^(female|male)(\/|$)/i.test(relativePath);
  if (managed && (!gender || new RegExp(`^${gender}(\\/|$)`, "i").test(relativePath))) output.push(relativePath);
  for (const child of node.children || []) collectManagedFolderPaths(child, output, gender);
  return output;
}

async function refreshCardTreeStructure() {
  const result = await window.desktopApi?.backendRequest?.(
    `/library/cards/tree?game_dir=${encodeQuery(paths.gameDir)}`
  );
  if (!result?.ok || !result.is_valid_game_dir) {
    throw new Error(result?.error || "人物卡目录读取失败");
  }
  cardTree.value = result.tree || null;
  expandedCardFolders.value = collectExpandableCardFolderPaths(cardTree.value);
  stats.cards = Number(result.total || 0);
  refreshVisibleCardFolders();
}

function resetCardTree() {
  cardTree.value = null;
  cardFolders.value = [];
  expandedCardFolders.value = new Set();
}

function toggleCardFolder(folder) {
  if (!folder?.hasChildren) return;
  const next = new Set(expandedCardFolders.value);
  if (next.has(folder.relativePath)) {
    next.delete(folder.relativePath);
  } else {
    next.add(folder.relativePath);
  }
  expandedCardFolders.value = next;
  refreshVisibleCardFolders();
}

async function handleCardFolderClick(folder) {
  await selectCardFolder(folder.relativePath);
}

async function loadCardTree() {
  cardLibrary.checked = true;
  cardLibrary.loading = true;
  cardLibrary.error = "";
  const startedAt = performance.now();

  if (!backendReady.value || !paths.gameDir) {
    clearResourceStats();
    cardLibrary.validGameDir = false;
    resetCardTree();
    cards.value = [];
    selectedCards.value = new Set();
    cardLibrary.loading = false;
    return;
  }

  try {
    const result = await window.desktopApi?.backendRequest?.(
      `/library/cards/tree?game_dir=${encodeQuery(paths.gameDir)}`
    );
    if (!result?.ok) {
      throw new Error(result?.error || "人物卡目录读取失败");
    }

    cardLibrary.validGameDir = Boolean(result.is_valid_game_dir);
    cardLibrary.root = result.root || "";
    if (!cardLibrary.validGameDir) {
      cardLibrary.error = result.error || "不是有效的 HS2 目录";
      clearResourceStats();
      resetCardTree();
      cards.value = [];
      selectedCards.value = new Set();
      stats.cards = 0;
      return;
    }

    cardTree.value = result.tree || null;
    expandedCardFolders.value = collectExpandableCardFolderPaths(cardTree.value);
    refreshVisibleCardFolders();
    stats.cards = Number(result.total || 0);
    await selectCardFolder(selectedCardFolder.value);
    if (cardTagFilter.scope === "library" && cardDependencyFilter.value.startsWith("tag:")) {
      await loadLibraryCardsByTag(cardDependencyFilter.value.slice(4));
    }
    log(
      `[Startup] loadCardTree completed in ${formatDurationMs(
        performance.now() - startedAt
      )} (folders=${cardFolders.value.length}, cards=${stats.cards ?? 0})`
    );
  } catch (error) {
    cardLibrary.validGameDir = false;
    cardLibrary.error = error.message;
    resetCardTree();
    cards.value = [];
    selectedCards.value = new Set();
    log(
      `[Startup] loadCardTree failed in ${formatDurationMs(performance.now() - startedAt)}: ${
        error.message
      }`
    );
    log(`[Cards Error] ${error.message}`);
  } finally {
    cardLibrary.loading = false;
  }
}

async function selectCardFolder(relativePath = "") {
  resetCardLibraryScrollPosition("character");
  selectedCardFolder.value = relativePath || "";
  selectedCards.value = new Set();
  selectedCardDetailPath.value = "";
  selectedCardProfile.value = null;
  selectedCardDependencies.value = [];
  selectedCardProfileError.value = "";
  cardBulkMode.value = false;
  const startedAt = performance.now();

  if (!backendReady.value || !paths.gameDir) return;
  if (!cardLibrary.validGameDir && cardLibrary.checked) return;

  cardLibrary.loading = true;
  cardLibrary.error = "";

  try {
    const result = await window.desktopApi?.backendRequest?.(
      `/library/cards?game_dir=${encodeQuery(paths.gameDir)}&path=${encodeQuery(selectedCardFolder.value)}`
    );
    if (!result?.ok) {
      throw new Error(result?.error || "人物卡列表读取失败");
    }
    if (!result.is_valid_game_dir) {
      cardLibrary.validGameDir = false;
      cardLibrary.error = result.error || "不是有效的 HS2 目录";
      clearResourceStats();
      cards.value = [];
      stats.cards = 0;
      return;
    }

    cardLibrary.validGameDir = true;
    cards.value = mapCharacterCardRows(result.cards);
    log(
      `[Startup] selectCardFolder(${selectedCardFolder.value || "/"}) completed in ${formatDurationMs(
        performance.now() - startedAt
      )} (cards=${cards.value.length})`
    );
  } catch (error) {
    cardLibrary.error = error.message;
    cards.value = [];
    log(
      `[Startup] selectCardFolder(${selectedCardFolder.value || "/"}) failed in ${formatDurationMs(
        performance.now() - startedAt
      )}: ${error.message}`
    );
    log(`[Cards Error] ${error.message}`);
  } finally {
    cardLibrary.loading = false;
  }
}

function rebuildCharacterCardDatabase() {
  isBusy.value = true;
  activeAction.value = "build_card_database";
  taskName.value = "扫描人物卡";
  progress.value = 1;
  taskId.value = "queued";
  taskHint.value = "等待人物卡扫描开始";

  const scanPromise = new Promise((resolve, reject) => {
    let settled = false;
    const settle = (callback, value) => {
      if (settled) return;
      settled = true;
      callback(value);
    };

    submitTaskInBackground(
      "build_card_database",
      { mode: "incremental" },
      async (task) => {
        if (task.status === "completed") {
          settle(resolve, task);
        } else {
          settle(reject, new Error(task.error || "人物卡数据扫描失败"));
        }
      }
    ).catch((error) => settle(reject, error));
  });
  return scanPromise.finally(() => {
    isBusy.value = false;
    activeAction.value = "";
  });
}

async function refreshCurrentCardFolder() {
  if (cardLibrary.loading || !cardLibrary.validGameDir || !backendReady.value || !paths.gameDir) return;
  const currentFolder = selectedCardFolder.value;
  cardLibrary.loading = true;
  cardLibrary.error = "";

  try {
    const changes = await window.desktopApi?.backendRequest?.(
      `/library/cards/changes?game_dir=${encodeQuery(paths.gameDir)}&path=${encodeQuery(currentFolder)}`
    );
    if (!changes?.ok) {
      throw new Error(changes?.error || "人物卡变动检查失败");
    }
    if (!changes.is_valid_game_dir) {
      cardLibrary.validGameDir = false;
      cardLibrary.error = changes.error || "不是有效的 HS2 目录";
      cards.value = [];
      return;
    }

    if (changes.changed) {
      const changedTotal = Number(changes.changed_total || 0);
      taskHint.value = `检测到当前目录 ${changedTotal} 张人物卡变动，正在重新扫描`;
      log(
        `[Cards] 当前目录检测到人物卡变动：新增 ${changes.added || 0}，删除 ${changes.removed || 0}，修改 ${changes.modified || 0}`
      );
      await rebuildCharacterCardDatabase();
      await loadCardTree();
    } else {
      await selectCardFolder(currentFolder);
      if (cardTagFilter.scope === "library" && cardDependencyFilter.value.startsWith("tag:")) {
        await loadLibraryCardsByTag(cardDependencyFilter.value.slice(4));
      }
      log(`[Cards] 当前目录未检测到人物卡变动，已重新读取列表`);
    }
  } catch (error) {
    cardLibrary.error = error.message;
    log(`[Cards Error] ${error.message}`);
  } finally {
    cardLibrary.loading = false;
  }
}

function setLibraryMode(mode) {
  libraryMode.value = mode;
  if (mode === "items") {
    exitModBulkMode();
    itemTab.value = "详情";
    ensureItemDatabaseLoaded();
    return;
  }
  modTab.value = "详情";
  ensureModDatabaseLoaded();
}

function isPoseItemKind(kind) {
  return POSE_ITEM_KIND_CODES.has(String(kind || "").trim());
}

const NO_MODEL_PREVIEW_KIND_CODES = new Set(
  TOPBAR_KIND_GROUPS.flatMap((group) =>
    group.categories
      .filter((category) => ["face", "body", "pose", "pattern"].includes(category.key))
      .flatMap((category) => category.kinds.map((kind) => String(kind)))
  )
);

function itemKindCode(item) {
  return String(item?.kindCode || item?.raw?.kind || "").trim();
}

function itemSupportsModelPreview(item) {
  if (!item) return false;
  if (isMapSceneItem(item)) return true;
  return !NO_MODEL_PREVIEW_KIND_CODES.has(itemKindCode(item));
}

function itemFallbackThumbnailUrl(kind, itemDomain = "") {
  const key = String(kind || "").trim();
  if (String(itemDomain || "").trim() === "studio" || key === STUDIO_ITEM_KIND) return STUDIO_ITEM_THUMBNAIL;
  if (MAP_SCENE_KIND_CODES.has(key)) return MAP_SCENE_THUMBNAIL;
  return POSE_ITEM_THUMBNAILS[key] || "";
}

function setCardBrowserMode(mode) {
  const nextMode = ["character", "clothes", "scene"].includes(String(mode))
    ? String(mode)
    : "character";
  cardBrowserMode.value = nextMode;
  activeView.value = "characters";
  if (nextMode === "clothes") void ensureClothesLibraryLoaded();
  if (nextMode === "scene") void ensureSceneLibraryLoaded();
}

function normalizeItemStatus(status, thumbnailStatus, unity3dStatus = "", kind = "", itemDomain = "mod") {
  if (unity3dStatus === "missing" || unity3dStatus === "error") return "error";
  if (status && status !== "ok") return "parse";
  if (itemDomain === "studio") return "ready";
  if (isPoseItemKind(kind)) return "ready";
  if (thumbnailStatus && thumbnailStatus !== "ready" && thumbnailStatus !== "ok") return "thumb";
  return "ready";
}

function isMapSceneItem(item) {
  return MAP_SCENE_KIND_CODES.has(String(item?.kindCode || item?.raw?.kind || "").trim());
}

function isStudioItem(item) {
  return String(item?.itemDomain || item?.raw?.item_domain || "").trim() === "studio";
}

function relatedItemCategoryLabel(item) {
  if (!isStudioItem(item)) return item?.kind || "-";
  const group = String(item?.raw?.studio_group_name || item?.raw?.studio_group_id || "").trim();
  const category = String(item?.raw?.studio_category_name || item?.raw?.studio_category_id || "").trim();
  if (group && category) return group + "/" + category;
  return group || category || item?.kind || "Studio";
}

function itemKindLabel(kind) {
  const key = String(kind || "").trim();
  const label = ITEM_KIND_LABELS[key] || key || "-";
  if (label.startsWith("\u7537")) return `\u2642${label.slice(1)}`;
  if (label.startsWith("\u5973")) return `\u2640${label.slice(1)}`;
  return label;
}

function mapModItemRow(row) {
  const sourceType = String(row.source_type || "mod").trim() || "mod";
  const isBuiltin = sourceType === "builtin";
  const itemDomain = String(row.item_domain || (isBuiltin ? "builtin" : "mod")).trim() || "mod";
  const thumbnailUrl = itemDomain === "studio"
    ? itemFallbackThumbnailUrl(row.kind, itemDomain)
    : backendAssetUrl(row.thumbnail_url) || itemFallbackThumbnailUrl(row.kind, itemDomain);
  return {
    id: isBuiltin ? `builtin:${row.id}` : row.id,
    dbId: row.id,
    zipmodId: row.zipmod_id || null,
    sourceType,
    isBuiltin,
    status: normalizeItemStatus(row.status, row.thumbnail_status, row.unity3d_status, row.kind, itemDomain),
    name: row.name || `(item ${row.item_id || row.id})`,
    kind: itemKindLabel(row.kind),
    kindCode: row.kind || "",
    author: row.author || (isBuiltin ? "游戏本体" : "-"),
    sourceMod: row.source_mod || (isBuiltin ? "游戏本体" : row.zipmod_guid) || "-",
    thumbnailUrl,
    itemDomain,
    isStudio: itemDomain === "studio",
    fallbackThumbnail: !backendAssetUrl(row.thumbnail_url) && Boolean(thumbnailUrl),
    raw: row
  };
}

function currentErrorItemFilterPayload() {
  return {
    search: String(itemFilters.search || "").trim(),
    kind: String(itemFilters.kind || ""),
    author: String(itemFilters.author || ""),
    status: "error",
    usage: String(dependencyUsageFilter.value || ""),
    source: "mod"
  };
}

async function fetchCurrentErrorItemCount() {
  const query = new URLSearchParams({
    offset: "0",
    limit: "1",
    ...currentErrorItemFilterPayload()
  });
  const result = await window.desktopApi?.backendRequest?.(`/mods/items?${query.toString()}`);
  if (!result?.ok) {
    throw new Error(result?.error || "错误物品数量读取失败");
  }
  return Number(result.data?.total || 0);
}

function normalizeZipmodStatus(row) {
  const status = row?.status || "";
  const unity3dStatus = row?.unity3d_status || "";
  const duplicateZipmodCount = Number(row?.duplicate_zipmod_count || 0);
  const thumbnailIssueCount = Number(row?.thumbnail_issue_count || 0);
  const author = String(row?.author || "").trim();
  const missingAuthor = !author || author === UNKNOWN_AUTHOR_LABEL;
  if (
    ["missing_manifest", "invalid_manifest", "read_error"].includes(status) ||
    unity3dStatus === "missing" ||
    unity3dStatus === "error" ||
    Number(row?.unity3d_missing_count || 0) > 0
  ) return "错误";
  if (
    missingAuthor ||
    ["in_game", "not_in_mod"].includes(unity3dStatus) ||
    Number(row?.unity3d_not_in_mod_count || 0) > 0 ||
    Number(row?.unity3d_in_game_count || 0) > 0 ||
    Number(row?.unity3d_other_mod_count || 0) > 0 ||
    duplicateZipmodCount > 0 ||
    thumbnailIssueCount > 0
  ) return "警告";
  if (status === "ok") return "正常";
  if (status === "error") return "读取错误";
  if (status === "stale") return "已失效";
  if (["invalid", "invalid_manifest"].includes(status)) return "错误";
  return status || "未知";
}

function mapZipmodRow(row) {
  return {
    id: row.id,
    status: normalizeZipmodStatus(row),
    name: row.name || row.file_name || "(未命名 zipmod)",
    author: row.author || "-",
    version: row.version || "-",
    itemCount: row.item_count ?? 0,
    guid: row.guid || row.file_name || String(row.id),
    duplicateZipmodCount: Number(row.duplicate_zipmod_count || 0),
    raw: row
  };
}

async function loadZipmodAuthors() {
  try {
    const result = await window.desktopApi?.backendRequest?.("/mods/zipmods/authors");
    if (!result?.ok) return;
    zipmodAuthors.value = Array.isArray(result.data?.authors)
      ? [...new Set(result.data.authors.map((author) => String(author || "").trim()).filter(Boolean))]
      : [];
  } catch (error) {
    log(`[Mods Error] ${error.message}`);
  }
}

async function loadItemFilters() {
  try {
    const query = paths.gameDir ? `?game_dir=${encodeQuery(paths.gameDir)}` : "";
    const result = await window.desktopApi?.backendRequest?.(`/mods/items/filters${query}`);
    if (!result?.ok) return;
    itemFilterAuthors.value = Array.isArray(result.data?.authors) ? result.data.authors : [];
    itemFilterKinds.value = Array.isArray(result.data?.kinds) ? result.data.kinds : [];
  } catch (error) {
    log(`[Items Error] ${error.message}`);
  }
}

async function applyModFilters() {
  if (libraryMode.value !== "mods") return;
  await ensureModDatabaseLoaded();
  await loadModRows({ reset: true });
}

async function applyItemFilters() {
  if (libraryMode.value !== "items") return;
  itemRows.value = [];
  selectedItem.value = null;
  itemDatabase.offset = 0;
  itemDatabase.hasMore = false;
  const exists = await checkModDatabase();
  if (exists) await loadItemRows({ reset: true });
}

async function setDependencyUsageFilter(value) {
  dependencyUsageFilter.value = value;
  if (libraryMode.value === "items") {
    await applyItemFilters();
    return;
  }
  await applyModFilters();
}

function scheduleItemSearch() {
  window.clearTimeout(itemFilterTimer);
  itemFilterTimer = window.setTimeout(() => {
    applyItemFilters();
  }, 220);
}

function scheduleModAuthorFilter() {
  window.clearTimeout(modFilterTimer);
  modFilterTimer = window.setTimeout(() => {
    applyModFilters();
  }, 220);
}

function selectModAuthorFilter(author) {
  modFilters.author = author;
  modAuthorFilterOpen.value = false;
  applyModFilters();
}

function closeModAuthorFilterSoon() {
  window.setTimeout(() => {
    modAuthorFilterOpen.value = false;
  }, 120);
}

function selectItemAuthorFilter(author) {
  itemFilters.author = author;
  itemAuthorFilterOpen.value = false;
  applyItemFilters();
}

function closeItemAuthorFilterSoon() {
  window.setTimeout(() => {
    itemAuthorFilterOpen.value = false;
  }, 120);
}

function selectItem(row) {
  selectedItem.value = row;
  if (row?.isBuiltin) {
    itemTab.value = "详情";
    itemGameNotice.type = "";
    itemGameNotice.message = "";
  }
}

function itemGameApplySpec(item) {
  const raw = item?.raw || {};
  const isBuiltin = Boolean(item?.isBuiltin || raw.source_type === "builtin");
  const categoryText = String(item?.kindCode || raw.kind || "").trim();
  const categoryNo = Number.parseInt(categoryText, 10);
  const guid = String(raw.zipmod_guid || "").trim();
  const originalSlotText = String(raw.item_id ?? "").trim();
  const originalSlot = Number.parseInt(originalSlotText, 10);

  if (!Number.isSafeInteger(categoryNo) || categoryNo < 0) {
    return { supported: false, reason: "当前物品没有可用的游戏类别编号。" };
  }
  const isHair = GAME_HAIR_CATEGORY_NOS.has(categoryText);
  const isAccessory = GAME_ACCESSORY_CATEGORY_NOS.has(categoryText);
  const isClothing = GAME_CLOTHING_CATEGORY_NOS.has(categoryText);
  const isFace = GAME_FACE_CATEGORY_NOS.has(categoryText);
  const isBody = GAME_BODY_CATEGORY_NOS.has(categoryText);
  if (!isClothing && !isAccessory && !isHair && !isFace && !isBody) {
    return { supported: false, reason: "当前插件只支持服饰、结构头发（300–303）、面部栏位、身体栏位和饰品换装；发色预设、发网格/发型选项、姿势和地图不能直接换装。" };
  }
  if (!/^\d+$/.test(originalSlotText) || !Number.isSafeInteger(originalSlot) || originalSlot < 0) {
    return { supported: false, reason: `${isBuiltin ? "该原版物品的 ID" : "该物品的 CSV slot"} 不是有效的数字，无法进行严格运行时映射。` };
  }
  if (!isBuiltin && !guid) {
    return { supported: false, reason: "该物品缺少模组 GUID，无法进行严格运行时映射。" };
  }

  return {
    supported: true,
    isBuiltin,
    type: isHair ? "hair" : isAccessory ? "accessory" : isFace ? "face" : isBody ? "body" : "clothes",
    categoryNo,
    originalSlot,
    localSlot: isBuiltin ? originalSlot : null,
    guid,
    hairSlotNo: isHair ? GAME_HAIR_SLOT_OPTIONS.find((option) => option.categoryNo === categoryNo)?.value ?? null : null,
    facePartNo: null
  };
}

function gameHairSlotOption(categoryNo) {
  return GAME_HAIR_SLOT_OPTIONS.find((option) => option.categoryNo === Number(categoryNo)) || null;
}

function itemGameApplyLabel(item) {
  const spec = itemGameApplySpec(item);
  if (spec.type === "accessory") return "应用到角色配饰槽…";
  if (spec.type === "hair") {
    const hairSlotLabel = gameHairSlotOption(spec.categoryNo)?.label;
    return hairSlotLabel ? `应用到${hairSlotLabel}栏位` : "应用到对应头发栏位";
  }
  if (spec.type === "face") {
    return `应用到${GAME_FACE_SLOT_LABELS[spec.categoryNo] || "面部"}栏位`;
  }
  if (spec.type === "body") {
    return `应用到${GAME_BODY_SLOT_LABELS[spec.categoryNo] || "身体"}栏位`;
  }
  if (spec.type === "clothes") {
    const clothingSlotLabel = GAME_CLOTHING_SLOT_LABELS[spec.categoryNo];
    return clothingSlotLabel ? `应用到${clothingSlotLabel}栏位` : "应用到对应服饰栏位";
  }
  return "让当前角色穿上";
}

function normalizeCurrentGameItems(items, partType) {
  return (Array.isArray(items) ? items : []).map((item) => ({
    ...item,
    partType: String(item?.partType || partType || ""),
    partIndex: Number.isFinite(Number(item?.partIndex)) ? Number(item.partIndex) : 0,
    categoryNo: Number.isFinite(Number(item?.categoryNo)) ? Number(item.categoryNo) : 0,
    localSlot: Number.isFinite(Number(item?.localSlot)) ? Number(item.localSlot) : 0,
    listId: Number.isFinite(Number(item?.listId)) ? Number(item.listId) : 0,
    originalId: item?.originalId == null ? null : Number(item.originalId),
    kind: Number.isFinite(Number(item?.kind)) ? Number(item.kind) : 0,
    name: String(item?.name || "").trim(),
    partLabel: String(item?.partLabel || "").trim(),
    thumbnailUrl: backendAssetUrl(item?.thumbnailUrl || item?.thumbnail_url),
    resolverRecords: Array.isArray(item?.resolverRecords) ? item.resolverRecords : []
  }));
}

function normalizeCurrentGameState(data) {
  const current = data && typeof data === "object" ? data : {};
  return {
    available: Boolean(current.available),
    source: String(current.source || ""),
    characterId: Number.isFinite(Number(current.characterId)) ? Number(current.characterId) : 0,
    sex: Number.isFinite(Number(current.sex)) ? Number(current.sex) : 0,
    characterName: String(current.characterName || "").trim(),
    characterFileName: String(current.characterFileName || "").trim(),
    coordinateName: String(current.coordinateName || "").trim(),
    hairs: normalizeCurrentGameItems(current.hairs, "hair"),
    clothes: normalizeCurrentGameItems(current.clothes, "clothes"),
    faces: normalizeCurrentGameItems(current.faces, "face"),
    bodies: normalizeCurrentGameItems(current.bodies, "body"),
    accessories: normalizeCurrentGameItems(current.accessories, "accessory")
  };
}

function normalizeContextCharacter(data) {
  const character = data && typeof data === "object" ? data : {};
  const current = normalizeCurrentGameState(character.current);
  return {
    ...character,
    available: Boolean(character.available),
    active: Boolean(character.active),
    characterIndex: Number.isFinite(Number(character.characterIndex)) ? Number(character.characterIndex) : -1,
    characterId: Number.isFinite(Number(character.characterId)) ? Number(character.characterId) : 0,
    sex: Number.isFinite(Number(character.sex)) ? Number(character.sex) : -1,
    characterName: String(character.characterName || "").trim(),
    characterFileName: String(character.characterFileName || "").trim(),
    current
  };
}

function normalizeAssemblyContext(data) {
  const context = data && typeof data === "object" ? data : {};
  const hscene = context.hscene && typeof context.hscene === "object" ? context.hscene : {};
  return {
    loading: false,
    error: "",
    available: Boolean(context.available),
    scene: String(context.scene || "none"),
    editor: context.editor ? normalizeContextCharacter(context.editor) : null,
    hscene: {
      available: Boolean(hscene.available),
      femaleCount: Number.isFinite(Number(hscene.femaleCount)) ? Number(hscene.femaleCount) : 0,
      maleCount: Number.isFinite(Number(hscene.maleCount)) ? Number(hscene.maleCount) : 0,
      totalCount: Number.isFinite(Number(hscene.totalCount)) ? Number(hscene.totalCount) : 0,
      females: Array.isArray(hscene.females) ? hscene.females.map(normalizeContextCharacter) : [],
      males: Array.isArray(hscene.males) ? hscene.males.map(normalizeContextCharacter) : []
    }
  };
}

function resetAssemblyCharacterTarget() {
  Object.assign(assemblyCharacterTarget, {
    target: "editor",
    sex: null,
    characterIndex: null,
    characterId: null
  });
}

function currentStateForAssemblyTarget() {
  if (assemblyCharacterTarget.target === "hscene") {
    const roles = assemblyCharacterTarget.sex === 1
      ? assemblyContext.hscene.females
      : assemblyContext.hscene.males;
    const role = roles.find((candidate) => (
      candidate.characterIndex === assemblyCharacterTarget.characterIndex
      && candidate.characterId === assemblyCharacterTarget.characterId
    ));
    return role?.current || null;
  }
  return assemblyContext.editor?.current || null;
}

function resetAssemblyContext(error = "") {
  Object.assign(assemblyContext, normalizeAssemblyContext(null), { error });
  resetAssemblyCharacterTarget();
  resetAssemblyTargetSlot();
  resetAssemblyAccessorySlotTypes();
  closeAssemblyAccessoryPartMenu();
  resetCurrentGameState();
  itemGameNotice.type = "";
  itemGameNotice.message = "";
  itemGameApply.error = "";
  currentGameState.error = error;
}

async function refreshAssemblyContext({ silent = false } = {}) {
  const requestSeq = ++currentGameStateRequestSeq;
  const request = window.desktopApi?.backendRequest;
  if (typeof request !== "function") {
    const error = "资源通信接口尚未加载，请重启应用后再试。";
    if (requestSeq === currentGameStateRequestSeq) resetAssemblyContext(error);
    return false;
  }
  if (!silent) {
    assemblyContext.loading = true;
    assemblyContext.error = "";
    currentGameState.loading = true;
    currentGameState.error = "";
  }
  try {
    const contextQuery = paths.gameDir
      ? `?game_dir=${encodeQuery(paths.gameDir)}`
      : "";
    const result = await request(`/game-item-probe/context${contextQuery}`);
    if (!result?.ok) throw new Error(formatGameItemProbeError(result));
    if (requestSeq !== currentGameStateRequestSeq) return false;
    Object.assign(assemblyContext, normalizeAssemblyContext(result.data));
    if (assemblyContext.scene === "hscene") {
      const target = assemblyCharacterTarget;
      const roles = target.sex === 1 ? assemblyContext.hscene.females : assemblyContext.hscene.males;
      const selected = target.target === "hscene"
        ? roles.find((role) => role.characterIndex === target.characterIndex && role.characterId === target.characterId)
        : null;
      if (!selected) {
        const first = assemblyContext.hscene.females[0] || assemblyContext.hscene.males[0] || null;
        if (first) {
          Object.assign(assemblyCharacterTarget, {
            target: "hscene",
            sex: first.sex,
            characterIndex: first.characterIndex,
            characterId: first.characterId
          });
        } else {
          resetAssemblyCharacterTarget();
        }
      }
    } else if (assemblyContext.scene === "editor") {
      resetAssemblyCharacterTarget();
    } else {
      resetAssemblyCharacterTarget();
    }
    const state = currentStateForAssemblyTarget();
    if (state) Object.assign(currentGameState, state);
    else resetCurrentGameState();
    currentGameState.error = "";
    return assemblyContext.available;
  } catch (error) {
    if (requestSeq !== currentGameStateRequestSeq) return false;
    assemblyContext.error = error instanceof Error ? error.message : String(error);
    resetAssemblyContext(assemblyContext.error);
    if (!silent) log(`[Game Context Error] ${assemblyContext.error}`);
    return false;
  } finally {
    if (requestSeq === currentGameStateRequestSeq) {
      if (!silent) assemblyContext.loading = false;
      if (!silent) currentGameState.loading = false;
    }
  }
}

async function selectAssemblyCharacter(target, character = null) {
  if (!assemblyMode.value) return false;
  if (target === "hscene" && !character) return false;
  if (target === "hscene") {
    Object.assign(assemblyCharacterTarget, {
      target: "hscene",
      sex: character.sex,
      characterIndex: character.characterIndex,
      characterId: character.characterId
    });
  } else {
    resetAssemblyCharacterTarget();
  }
  resetAssemblyTargetSlot();
  resetAssemblyAccessorySlotTypes();
  closeAssemblyAccessoryPartMenu();
  itemGameNotice.type = "";
  itemGameNotice.message = "";
  const state = currentStateForAssemblyTarget();
  if (state) Object.assign(currentGameState, state);
  else resetCurrentGameState();
  await applyItemFilters();
  return true;
}

function resetCurrentGameState() {
  Object.assign(currentGameState, {
    loading: false,
    error: "",
    ...normalizeCurrentGameState(null)
  });
}

function resetAssemblyTargetSlot() {
  Object.assign(assemblyTargetSlot, {
    active: false,
    groupKey: "",
    partIndex: null,
    categoryNo: null,
    label: "",
    accessorySlotNo: null,
    hairSlotNo: null,
    facePartNo: null,
    bodyPartNo: null
  });
}

function resetAssemblyAccessorySlotTypes() {
  Object.keys(assemblyAccessorySlotTypes).forEach((slotNo) => {
    delete assemblyAccessorySlotTypes[slotNo];
  });
}

function closeAssemblyAccessoryPartMenu() {
  assemblyAccessoryPartMenu.open = false;
  assemblyAccessoryPartMenu.slotNo = null;
  assemblyAccessoryPartMenu.groupKey = "accessories";
  assemblyAccessoryPartMenu.categoryNo = null;
  assemblyAccessoryPartMenu.item = null;
}

function accessorySlotNoFromItem(item) {
  const slotNo = Number(item?.partIndex);
  return Number.isInteger(slotNo) && slotNo >= 0 && slotNo <= 19 ? slotNo : null;
}

function isAccessoryCategoryNo(categoryNo) {
  return GAME_ACCESSORY_CATEGORY_NOS.has(String(categoryNo));
}

function isAccessorySlotItem(item, groupKey = "") {
  return String(groupKey || "") === "accessories"
    || String(item?.partType || "") === "accessory"
    || Number(item?.categoryNo) === GAME_ACCESSORY_NONE_CATEGORY_NO
    || isAccessoryCategoryNo(item?.categoryNo);
}

function assignedAccessoryCategoryNo(slotNo) {
  const assigned = Number(assemblyAccessorySlotTypes[slotNo]);
  return isAccessoryCategoryNo(assigned) ? assigned : null;
}

function accessoryCategoryNoForItem(item) {
  const slotNo = accessorySlotNoFromItem(item);
  const assigned = slotNo == null ? null : assignedAccessoryCategoryNo(slotNo);
  if (assigned != null) return assigned;
  const current = Number(item?.categoryNo);
  return isAccessoryCategoryNo(current) ? current : null;
}

function openAssemblyAccessoryPartMenu(item, event, groupKey = "accessories") {
  if (!assemblyMode.value || !item || !event) return;
  const slotNo = accessorySlotNoFromItem(item);
  if (slotNo == null) return;
  const menuWidth = 332;
  const menuHeight = 236;
  assemblyAccessoryPartMenu.item = item;
  assemblyAccessoryPartMenu.slotNo = slotNo;
  assemblyAccessoryPartMenu.groupKey = String(groupKey || "accessories");
  assemblyAccessoryPartMenu.categoryNo = accessoryCategoryNoForItem(item);
  assemblyAccessoryPartMenu.x = Math.max(8, Math.min(Number(event.clientX) || 8, window.innerWidth - menuWidth - 8));
  assemblyAccessoryPartMenu.y = Math.max(8, Math.min(Number(event.clientY) || 8, window.innerHeight - menuHeight - 8));
  assemblyAccessoryPartMenu.open = true;
}

async function assignAssemblyAccessoryPart(categoryNo) {
  const nextCategoryNo = Number(categoryNo);
  const slotNo = assemblyAccessoryPartMenu.slotNo;
  const item = assemblyAccessoryPartMenu.item;
  const groupKey = assemblyAccessoryPartMenu.groupKey || "accessories";
  if (!isAccessoryCategoryNo(nextCategoryNo) || slotNo == null || !item) return false;
  assemblyAccessorySlotTypes[slotNo] = nextCategoryNo;
  assemblyAccessoryPartMenu.categoryNo = nextCategoryNo;
  closeAssemblyAccessoryPartMenu();
  return selectAssemblySlot(item, groupKey);
}

function facePartNoFromCurrentItem(item) {
  const categoryNo = Number(item?.categoryNo);
  const partIndex = Number(item?.partIndex);
  if (categoryNo === 317 && partIndex >= 20 && partIndex <= 21) return partIndex - 20;
  if (categoryNo === 318 && partIndex >= 30 && partIndex <= 31) return partIndex - 30;
  return null;
}

function bodyPartNoFromCurrentItem(item) {
  const categoryNo = Number(item?.categoryNo);
  const partIndex = Number(item?.partIndex);
  if (GAME_BODY_PAINT_CATEGORY_NOS.has(String(categoryNo))
      && partIndex >= 10 && partIndex <= 11) {
    return partIndex - 10;
  }
  return null;
}

function gameCurrentSlotLabel(item) {
  if (isAccessorySlotItem(item)) {
    const accessoryCategoryNo = accessoryCategoryNoForItem(item);
    if (accessoryCategoryNo != null) return `${GAME_ACCESSORY_SLOT_LABELS[accessoryCategoryNo]}配饰`;
    const slotNo = accessorySlotNoFromItem(item);
    return slotNo == null ? "配饰栏位" : `配饰槽 ${slotNo + 1}`;
  }
  const categoryNo = Number(item?.categoryNo);
  if (GAME_CLOTHING_SLOT_LABELS[categoryNo]) return `${GAME_CLOTHING_SLOT_LABELS[categoryNo]}栏位`;
  const hairSlot = gameHairSlotOption(categoryNo);
  if (hairSlot) return `${hairSlot.label}栏位`;
  return GAME_CURRENT_SLOT_LABELS[categoryNo] || `CategoryNo ${categoryNo || "-"}`;
}

function gameCurrentItemName(item) {
  if (Number(item?.localSlot || 0) === 0) return "未装配";
  return String(item?.name || "").trim() || "原生物品（名称未读取）";
}

async function refreshCurrentGameState({ silent = false } = {}) {
  return refreshAssemblyContext({ silent });
}

function stopCurrentGameStatePolling() {
  if (currentGameStatePollTimer != null) {
    window.clearInterval(currentGameStatePollTimer);
    currentGameStatePollTimer = null;
  }
  currentGameStateRequestSeq += 1;
}

function setAssemblyMode(enabled) {
  const nextValue = Boolean(enabled);
  if (nextValue === assemblyMode.value) return;
  stopCurrentGameStatePolling();
  assemblyMode.value = nextValue;
  resetAssemblyTargetSlot();
  resetAssemblyAccessorySlotTypes();
  closeAssemblyAccessoryPartMenu();
  itemGameNotice.type = "";
  itemGameNotice.message = "";
  itemGameApply.error = "";
  if (!nextValue) {
    resetAssemblyCharacterTarget();
    resetCurrentGameState();
    return;
  }
  itemFilters.kind = "";
  itemFilters.source = "";
  void applyItemFilters();
  currentGameState.error = "";
  void refreshAssemblyContext();
  currentGameStatePollTimer = window.setInterval(() => {
    if (!assemblyContext.loading) void refreshAssemblyContext({ silent: true });
  }, 1000);
}

async function selectAssemblySlot(item, groupKey = "") {
  if (!assemblyMode.value || !item) return false;
  const normalizedGroupKey = String(groupKey || {
    hair: "hairs",
    clothes: "clothes",
    face: "faces",
    body: "bodies",
    accessory: "accessories"
  }[String(item.partType || "")] || "");
  const isAccessoryGroup = isAccessorySlotItem(item, normalizedGroupKey);
  let categoryNo = Number(item.categoryNo);
  let accessorySlotNo = null;
  if (isAccessoryGroup) {
    accessorySlotNo = accessorySlotNoFromItem(item);
    if (accessorySlotNo == null) return false;
    const resolvedCategoryNo = accessoryCategoryNoForItem(item);
    if (resolvedCategoryNo == null) {
      itemGameNotice.type = "info";
      itemGameNotice.message = "请先右键该配饰栏，选择要装配的饰品部位。";
      return false;
    }
    categoryNo = resolvedCategoryNo;
  } else if (!Number.isSafeInteger(categoryNo) || categoryNo <= 0) {
    return false;
  }

  const hairSlot = gameHairSlotOption(categoryNo);
  const facePartNo = facePartNoFromCurrentItem(item);
  const bodyPartNo = bodyPartNoFromCurrentItem(item);
  Object.assign(assemblyTargetSlot, {
    active: true,
    groupKey: normalizedGroupKey,
    partIndex: Number.isSafeInteger(Number(item.partIndex)) ? Number(item.partIndex) : null,
    categoryNo,
    label: gameCurrentSlotLabel(item),
    accessorySlotNo: isAccessoryGroup ? accessorySlotNo : null,
    hairSlotNo: hairSlot?.value ?? null,
    facePartNo: GAME_FACE_EYE_CATEGORY_NOS.has(String(categoryNo)) ? facePartNo : null,
    bodyPartNo: GAME_BODY_PAINT_CATEGORY_NOS.has(String(categoryNo)) ? bodyPartNo : null
  });
  itemFilters.kind = String(categoryNo);
  await applyItemFilters();
  itemGameApply.error = "";
  itemGameNotice.type = "info";
  itemGameNotice.message = `已选择${assemblyTargetSlot.label}，左侧单击物品即可直接穿戴。`;
  return true;
}

async function applyAssemblyItem(item) {
  if (!assemblyMode.value || !item?.id || itemGameApply.busy) return false;
  selectItem(item);

  if (!assemblyTargetSlot.active) {
    itemGameNotice.type = "error";
    itemGameNotice.message = "请先点击右侧角色栏位，再从左侧选择要穿戴的物品。";
    itemGameApply.error = itemGameNotice.message;
    return false;
  }

  const targetGroupKey = assemblyTargetSlot.groupKey;
  if (!["clothes", "hairs", "faces", "bodies", "accessories"].includes(targetGroupKey)) {
    itemGameNotice.type = "error";
    itemGameNotice.message = "当前目标栏位不支持直接换装。";
    itemGameApply.error = itemGameNotice.message;
    return false;
  }

  const spec = itemGameApplySpec(item);
  if (!spec.supported) {
    itemGameNotice.type = "error";
    itemGameNotice.message = spec.reason;
    itemGameApply.error = spec.reason;
    return false;
  }

  const expectedType = targetGroupKey === "clothes"
    ? "clothes"
    : targetGroupKey === "hairs"
      ? "hair"
      : targetGroupKey === "faces"
        ? "face"
        : targetGroupKey === "bodies"
          ? "body"
          : "accessory";
  if (spec.type !== expectedType || spec.categoryNo !== Number(assemblyTargetSlot.categoryNo)) {
    itemGameNotice.type = "error";
    itemGameNotice.message = `「${item.name}」与当前${assemblyTargetSlot.label}不匹配，请从该栏位筛选结果中选择物品。`;
    itemGameApply.error = itemGameNotice.message;
    return false;
  }

  if (expectedType === "hair" && spec.hairSlotNo !== assemblyTargetSlot.hairSlotNo) {
    itemGameNotice.type = "error";
    itemGameNotice.message = `头发物品只能装配到类别对应的${gameHairSlotOption(spec.categoryNo)?.label || "头发"}栏位。`;
    itemGameApply.error = itemGameNotice.message;
    return false;
  }
  if (expectedType === "face" && GAME_FACE_EYE_CATEGORY_NOS.has(String(spec.categoryNo))) {
    if (spec.categoryNo !== Number(assemblyTargetSlot.categoryNo)
      || !Number.isInteger(assemblyTargetSlot.facePartNo)
      || assemblyTargetSlot.facePartNo < 0
      || assemblyTargetSlot.facePartNo > 1) {
      itemGameNotice.type = "error";
      itemGameNotice.message = "当前面部物品需要明确的左眼或右眼栏位，已拒绝换装。";
      itemGameApply.error = itemGameNotice.message;
      return false;
    }
  }
  if (expectedType === "accessory" && !Number.isInteger(assemblyTargetSlot.accessorySlotNo)) {
    itemGameNotice.type = "error";
    itemGameNotice.message = "当前配饰栏位缺少有效的角色配饰槽位，已拒绝换装。";
    itemGameApply.error = itemGameNotice.message;
    return false;
  }
  if (expectedType === "body" && GAME_BODY_PAINT_CATEGORY_NOS.has(String(spec.categoryNo))
    && (!Number.isInteger(assemblyTargetSlot.bodyPartNo)
      || assemblyTargetSlot.bodyPartNo < 0
      || assemblyTargetSlot.bodyPartNo > 1)) {
    itemGameNotice.type = "error";
    itemGameNotice.message = "当前身体彩绘缺少有效的彩绘层，已拒绝换装。";
    itemGameApply.error = itemGameNotice.message;
    return false;
  }

  if (expectedType === "hair") {
    return applyItemToGame(item, { hairSlotNo: assemblyTargetSlot.hairSlotNo });
  }
  if (expectedType === "accessory") {
    return applyItemToGame(item, { accessorySlotNo: assemblyTargetSlot.accessorySlotNo });
  }
  if (expectedType === "face") {
    return applyItemToGame(item, { facePartNo: assemblyTargetSlot.facePartNo });
  }
  if (expectedType === "body") {
    return applyItemToGame(item, { bodyPartNo: assemblyTargetSlot.bodyPartNo });
  }
  return applyItemToGame(item);
}

function formatGameItemProbeError(payload) {
  const code = String(payload?.error_code || payload?.errorCode || payload?.data?.errorCode || payload?.data?.error_code || "");
  const details = String(payload?.error || payload?.data?.error || "").trim();
  const labels = {
    probe_unavailable: "游戏物品探针未连接",
    invalid_probe_response: "游戏物品探针响应无效",
    not_in_editor: "当前不在角色制作器中",
    invalid_category: "当前物品类别不支持换装",
    item_not_found: "游戏当前列表中找不到该物品",
    ambiguous_mapping: "该物品的运行时映射不唯一，已拒绝自动选择",
    invalid_accessory_slot: "配饰槽位无效",
    invalid_hair_slot: "头发栏位无效或与物品类别不匹配",
    invalid_face_slot: "面部栏位无效或缺少眼别",
    invalid_body_slot: "身体栏位无效或缺少彩绘层",
    invalid_card_path: "人物卡路径无效",
    invalid_card: "不是有效的 AIS 人物卡",
    invalid_card_selection: "人物卡读取内容选择无效",
    card_sex_mismatch: "人物卡性别与当前角色不一致",
    card_load_failed: "游戏无法读取这张人物卡",
    target_unavailable: "当前角色数据尚未就绪",
    queue_full: "游戏换装队列已满",
    execution_error: "游戏执行换装失败",
    command_expired: "游戏换装命令已超时",
    probe_request_failed: "游戏物品探针请求失败"
  };
  const label = labels[code] || details || "游戏换装失败";
  return details && details !== label ? `${label}：${details}` : label;
}

function closeItemContextMenu() {
  itemContextMenu.open = false;
  itemContextMenu.item = null;
}

function openItemContextMenu(item, event) {
  if (!item?.id || !event) return;
  selectItem(item);
  const menuWidth = 286;
  const menuHeight = 210;
  itemContextMenu.item = item;
  itemContextMenu.x = Math.max(8, Math.min(Number(event.clientX) || 8, window.innerWidth - menuWidth - 8));
  itemContextMenu.y = Math.max(8, Math.min(Number(event.clientY) || 8, window.innerHeight - menuHeight - 8));
  itemContextMenu.open = true;
}

function requestItemGameApply() {
  const item = itemContextMenu.item;
  const spec = itemGameApplySpec(item);
  closeItemContextMenu();
  if (!spec.supported) {
    itemGameNotice.type = "error";
    itemGameNotice.message = spec.reason;
    return;
  }
  if (spec.type === "accessory") {
    itemAccessoryPrompt.item = item;
    itemAccessoryPrompt.slotNo = 0;
    itemAccessoryPrompt.error = "";
    itemAccessoryPrompt.open = true;
    return;
  }
  if (spec.type === "face" && GAME_FACE_EYE_CATEGORY_NOS.has(String(spec.categoryNo))) {
    itemFacePrompt.item = item;
    itemFacePrompt.facePartNo = 0;
    itemFacePrompt.error = "";
    itemFacePrompt.open = true;
    return;
  }
  if (spec.type === "body" && GAME_BODY_PAINT_CATEGORY_NOS.has(String(spec.categoryNo))) {
    itemBodyPrompt.item = item;
    itemBodyPrompt.bodyPartNo = 0;
    itemBodyPrompt.error = "";
    itemBodyPrompt.open = true;
    return;
  }
  if (spec.type === "hair") {
    void applyItemToGame(item, { hairSlotNo: spec.hairSlotNo });
    return;
  }
  void applyItemToGame(item);
}

function closeItemFacePrompt() {
  if (itemFacePrompt.busy) return;
  itemFacePrompt.open = false;
  itemFacePrompt.item = null;
  itemFacePrompt.error = "";
}

async function confirmItemFaceApply() {
  const item = itemFacePrompt.item;
  if (!item || itemFacePrompt.busy || itemGameApply.busy) return;
  itemFacePrompt.busy = true;
  itemFacePrompt.error = "";
  try {
    const applied = await applyItemToGame(item, { facePartNo: Number(itemFacePrompt.facePartNo) });
    if (applied) {
      itemFacePrompt.busy = false;
      closeItemFacePrompt();
    } else {
      itemFacePrompt.error = itemGameApply.error || itemGameNotice.message || "游戏换装失败";
    }
  } finally {
    itemFacePrompt.busy = false;
  }
}

function closeItemBodyPrompt() {
  if (itemBodyPrompt.busy) return;
  itemBodyPrompt.open = false;
  itemBodyPrompt.item = null;
  itemBodyPrompt.error = "";
}

async function confirmItemBodyApply() {
  const item = itemBodyPrompt.item;
  if (!item || itemBodyPrompt.busy || itemGameApply.busy) return;
  itemBodyPrompt.busy = true;
  itemBodyPrompt.error = "";
  try {
    const applied = await applyItemToGame(item, { bodyPartNo: Number(itemBodyPrompt.bodyPartNo) });
    if (applied) {
      itemBodyPrompt.busy = false;
      closeItemBodyPrompt();
    } else {
      itemBodyPrompt.error = itemGameApply.error || itemGameNotice.message || "游戏换装失败";
    }
  } finally {
    itemBodyPrompt.busy = false;
  }
}

function closeItemAccessoryPrompt() {
  if (itemAccessoryPrompt.busy) return;
  itemAccessoryPrompt.open = false;
  itemAccessoryPrompt.item = null;
  itemAccessoryPrompt.error = "";
}

async function confirmItemAccessoryApply() {
  const item = itemAccessoryPrompt.item;
  if (!item || itemAccessoryPrompt.busy || itemGameApply.busy) return;
  itemAccessoryPrompt.busy = true;
  itemAccessoryPrompt.error = "";
  try {
    const applied = await applyItemToGame(item, {
      accessorySlotNo: Number(itemAccessoryPrompt.slotNo)
    });
    if (applied) {
      itemAccessoryPrompt.busy = false;
      closeItemAccessoryPrompt();
    } else {
      itemAccessoryPrompt.error = itemGameApply.error || itemGameNotice.message || "游戏换装失败";
    }
  } finally {
    itemAccessoryPrompt.busy = false;
  }
}

async function applyItemToGame(item, { accessorySlotNo = null, hairSlotNo = null, facePartNo = null, bodyPartNo = null } = {}) {
  if (!item?.id || itemGameApply.busy) return false;
  const spec = itemGameApplySpec(item);
  if (!spec.supported) {
    itemGameNotice.type = "error";
    itemGameNotice.message = spec.reason;
    itemGameApply.error = spec.reason;
    return false;
  }
  if (spec.type === "accessory" && (!Number.isInteger(accessorySlotNo) || accessorySlotNo < 0 || accessorySlotNo > 19)) {
    itemGameNotice.type = "error";
    itemGameNotice.message = "请选择 0–19 范围内的角色配饰槽位。";
    itemGameApply.error = itemGameNotice.message;
    return false;
  }
  if (spec.type === "hair" && (!Number.isInteger(hairSlotNo) || hairSlotNo < 0 || hairSlotNo > 3 || hairSlotNo !== spec.hairSlotNo)) {
    const hairSlot = GAME_HAIR_SLOT_OPTIONS.find((option) => option.value === spec.hairSlotNo);
    itemGameNotice.type = "error";
    itemGameNotice.message = `头发栏位由物品类别固定决定：${hairSlot?.label || "对应栏位"}；请求已拒绝。`;
    itemGameApply.error = itemGameNotice.message;
    return false;
  }
  if (spec.type === "face" && GAME_FACE_EYE_CATEGORY_NOS.has(String(spec.categoryNo))
    && (!Number.isInteger(facePartNo) || facePartNo < 0 || facePartNo > 1)) {
    itemGameNotice.type = "error";
    itemGameNotice.message = "请选择左眼或右眼面部栏位。";
    itemGameApply.error = itemGameNotice.message;
    return false;
  }
  if (spec.type === "body" && GAME_BODY_PAINT_CATEGORY_NOS.has(String(spec.categoryNo))
    && (!Number.isInteger(bodyPartNo) || bodyPartNo < 0 || bodyPartNo > 1)) {
    itemGameNotice.type = "error";
    itemGameNotice.message = "请选择 0–1 范围内的身体彩绘层。";
    itemGameApply.error = itemGameNotice.message;
    return false;
  }

  const request = window.desktopApi?.backendRequest;
  if (typeof request !== "function") {
    itemGameNotice.type = "error";
    itemGameNotice.message = "资源通信接口尚未加载，请重启应用后再试。";
    itemGameApply.error = itemGameNotice.message;
    return false;
  }

  const body = {
    type: spec.type,
    categoryNo: spec.categoryNo
  };
  if (assemblyCharacterTarget.target === "hscene") {
    body.target = "hscene";
    body.sex = assemblyCharacterTarget.sex;
    body.characterIndex = assemblyCharacterTarget.characterIndex;
    body.targetCharacterId = assemblyCharacterTarget.characterId;
  }
  if (spec.isBuiltin) {
    // Native list IDs are already the runtime localSlot. Do not send a fake
    // GUID or route original items through the UAR resolver path.
    body.localSlot = spec.localSlot;
  } else {
    body.guid = spec.guid;
    body.slot = spec.originalSlot;
  }
  if (spec.type === "accessory") body.slotNo = accessorySlotNo;
  if (spec.type === "hair") body.hairSlotNo = hairSlotNo;
  if (spec.type === "face" && GAME_FACE_EYE_CATEGORY_NOS.has(String(spec.categoryNo))) body.facePartNo = facePartNo;
  if (spec.type === "body" && GAME_BODY_PAINT_CATEGORY_NOS.has(String(spec.categoryNo))) body.bodyPartNo = bodyPartNo;

  itemGameApply.busy = true;
  itemGameApply.itemId = item.id;
  itemGameApply.commandId = "";
  itemGameApply.status = "submitting";
  itemGameApply.error = "";
  itemGameNotice.type = "info";
  itemGameNotice.message = `正在向游戏提交「${item.name}」的换装请求…`;
  try {
    const submitted = await request("/game-item-probe/apply", {
      method: "POST",
      body
    });
    if (!submitted?.ok) throw new Error(formatGameItemProbeError(submitted));
    const accepted = submitted.data || {};
    const commandId = String(accepted.commandId || "").trim();
    if (!accepted.accepted || !commandId) {
      throw new Error(formatGameItemProbeError(accepted));
    }
    itemGameApply.commandId = commandId;
    itemGameApply.status = String(accepted.status || "queued");

    for (let attempt = 0; attempt < 70; attempt += 1) {
      await sleep(attempt === 0 ? 80 : 250);
      const polled = await request(`/game-item-probe/command?id=${encodeURIComponent(commandId)}`);
      if (!polled?.ok) throw new Error(formatGameItemProbeError(polled));
      const command = polled.data || {};
      itemGameApply.status = String(command.status || "");
      if (command.status === "succeeded") {
        itemGameNotice.type = "success";
        itemGameNotice.message = `已将「${item.name}」发送到当前角色。游戏资源加载可能还需要片刻。`;
        if (spec.type === "accessory" && Number.isInteger(accessorySlotNo)) {
          assemblyAccessorySlotTypes[accessorySlotNo] = spec.categoryNo;
        }
        if (assemblyMode.value) void refreshCurrentGameState({ silent: true });
        const mappingLabel = spec.isBuiltin ? `localSlot=${spec.localSlot}` : `slot=${spec.originalSlot}`;
        const slotLabel = spec.type === "accessory"
          ? `，slotNo=${accessorySlotNo}`
          : spec.type === "hair"
            ? `，hairSlotNo=${hairSlotNo}`
            : spec.type === "face" && GAME_FACE_EYE_CATEGORY_NOS.has(String(spec.categoryNo))
              ? `，facePartNo=${facePartNo}`
              : spec.type === "body" && GAME_BODY_PAINT_CATEGORY_NOS.has(String(spec.categoryNo))
                ? `，bodyPartNo=${bodyPartNo}`
                : "";
        log(`[Game] 已请求换装：${item.name}（${spec.type}，categoryNo=${spec.categoryNo}，${mappingLabel}${slotLabel}）`);
        return true;
      }
      if (["failed", "expired"].includes(command.status)) {
        throw new Error(formatGameItemProbeError(command));
      }
    }
    throw new Error("游戏换装命令超过 15 秒未完成，请确认角色制作器仍处于打开状态。");
  } catch (error) {
    itemGameApply.error = error instanceof Error ? error.message : String(error);
    itemGameNotice.type = "error";
    itemGameNotice.message = itemGameApply.error;
    log(`[Game Error] ${itemGameApply.error}`);
    return false;
  } finally {
    itemGameApply.busy = false;
    itemGameApply.itemId = null;
  }
}

function beginWorkbenchTemplateSelection(request = {}) {
  if (!request?.projectId || !request?.itemId) return false;

  workbenchTemplateSelection.active = true;
  workbenchTemplateSelection.busy = false;
  workbenchTemplateSelection.error = "";
  workbenchTemplateSelection.result = null;
  workbenchTemplateSelection.request = {
    projectId: String(request.projectId),
    projectPath: String(request.projectPath || ""),
    csvPath: String(request.csvPath || ""),
    itemId: String(request.itemId),
    targetItem: request.targetItem || null
  };

  libraryMode.value = "items";
  itemTab.value = "工具";
  selectedItem.value = null;
  selectedMod.value = null;
  activeView.value = "mods";
  void applyItemFilters();
  return true;
}

function workbenchTemplateItemSnapshot(item) {
  const raw = item?.raw || {};
  return {
    id: item?.id,
    name: item?.name || raw.item_name || "",
    item_id: raw.item_id || "",
    zipmod_guid: raw.zipmod_guid || item?.sourceMod || "",
    main_ab: raw.main_ab || "",
    main_data: raw.main_data || "",
    unity3d_status: raw.unity3d_status || "",
    thumbnail_url: raw.thumbnail_url || item?.thumbnailUrl || "",
    author: item?.author || "",
    source_mod: item?.sourceMod || ""
  };
}

async function selectWorkbenchTemplateFromItem(item) {
  if (!workbenchTemplateSelection.active || !item?.id || workbenchTemplateSelection.busy) return false;

  const mainAb = String(item.raw?.main_ab || "").trim();
  if (isMapSceneItem(item) || !/\.unity3d$/i.test(mainAb)) {
    workbenchTemplateSelection.error = "当前物品没有可用的 Unity3D 主资源，无法作为模板。";
    return false;
  }

  const request = window.desktopApi?.backendRequest;
  if (typeof request !== "function") {
    workbenchTemplateSelection.error = "资源读取接口尚未加载，请重启应用后再试。";
    return false;
  }

  workbenchTemplateSelection.busy = true;
  workbenchTemplateSelection.error = "";
  try {
    const prepared = await request(`/mods/items/${item.id}/open-unity3d`, {
      method: "POST",
      body: {}
    });
    if (!prepared?.ok || !prepared.unity3d_path) {
      throw new Error(prepared?.error || "无法准备所选物品的 Unity3D 文件");
    }

    const assets = await request("/workbench/unity3d/assets", {
      method: "POST",
      body: { path: prepared.unity3d_path }
    });
    if (!assets?.ok) throw new Error(assets?.error || "无法读取 Unity3D 内部模型对象");
    const candidates = Array.isArray(assets.candidates) ? assets.candidates : [];
    if (!candidates.length) throw new Error("所选 Unity3D 中没有可用的模型对象");

    const preferred = String(item.raw?.main_data || "").trim();
    const preferredCandidate = candidates.find((candidate) => candidate.value === preferred);
    const mainData = preferredCandidate?.value
      || assets.default
      || candidates[0]?.value
      || preferred;

    workbenchTemplateSelection.result = {
      sourceItemId: item.id,
      templateItem: workbenchTemplateItemSnapshot(item),
      preparedPath: prepared.unity3d_path,
      candidates,
      objectCount: Number(assets.object_count || 0),
      gameObjectCount: Number(assets.game_object_count || 0),
      mainData,
      mainDataPathId: Number(preferredCandidate?.path_id || candidates[0]?.path_id || 0),
      mainDataAssetFile: String(preferredCandidate?.asset_file || candidates[0]?.asset_file || "")
    };
    workbenchTemplateSelection.active = false;
    activeView.value = "workbench";
    return true;
  } catch (error) {
    workbenchTemplateSelection.error = error?.message || String(error);
    return false;
  } finally {
    workbenchTemplateSelection.busy = false;
  }
}

function cancelWorkbenchTemplateSelection() {
  if (!workbenchTemplateSelection.active) return;
  workbenchTemplateSelection.result = { cancelled: true };
  workbenchTemplateSelection.active = false;
  workbenchTemplateSelection.busy = false;
  workbenchTemplateSelection.error = "";
  activeView.value = "workbench";
}

function consumeWorkbenchTemplateSelection() {
  if (!workbenchTemplateSelection.request) return null;
  const payload = {
    request: workbenchTemplateSelection.request,
    result: workbenchTemplateSelection.result
  };
  workbenchTemplateSelection.request = null;
  workbenchTemplateSelection.result = null;
  workbenchTemplateSelection.error = "";
  workbenchTemplateSelection.busy = false;
  return payload;
}

function selectMod(row) {
  selectedMod.value = row;
  selectedModItems.value = [];
  selectedModItemsError.value = "";
  selectedModDiagnostics.value = null;
  selectedModDiagnosticsError.value = "";
  if (modTab.value === "物品") {
    loadSelectedModItems();
  } else if (modTab.value === "诊断") {
    loadSelectedModDiagnostics();
  }
}

function enterModBulkMode() {
  modBulkMode.value = true;
}

function exitModBulkMode() {
  modBulkMode.value = false;
  selectedModIds.value = new Set();
}

function toggleModSelection(row) {
  if (!row?.id) return;
  const id = Number(row.id);
  const next = new Set(selectedModIds.value);
  if (next.has(id)) {
    next.delete(id);
  } else {
    next.add(id);
  }
  selectedModIds.value = next;
}

function toggleAllVisibleMods() {
  const next = new Set(selectedModIds.value);
  if (allVisibleModsSelected.value) {
    visibleModIds.value.forEach((id) => next.delete(id));
  } else {
    visibleModIds.value.forEach((id) => next.add(id));
  }
  selectedModIds.value = next;
}

function syncSelectedModIdsWithVisibleRows() {
  const visible = new Set(visibleModIds.value);
  selectedModIds.value = new Set([...selectedModIds.value].filter((id) => visible.has(id)));
}

async function openModItemInItemBrowser(item) {
  if (!item || !selectedMod.value) return;
  const guid = selectedMod.value.guid || item.raw?.zipmod_guid || "";
  if (!guid) return;

  libraryMode.value = "items";
  itemTab.value = "详情";
  itemFilters.search = guid;
  itemFilters.kind = "";
  itemFilters.author = "";
  itemFilters.status = "";
  itemFilters.source = "mod";
  dependencyUsageFilter.value = "";

  await ensureItemDatabaseLoaded({ force: true });

  let target = itemRows.value.find((row) => Number(row.id) === Number(item.id));
  while (!target && itemDatabase.hasMore) {
    await loadItemRows();
    target = itemRows.value.find((row) => Number(row.id) === Number(item.id));
  }

  if (target) {
    selectItem(target);
  } else {
    log(`[Items Error] 未找到关联物品：${item.name || item.id}`);
  }
}

async function openCardDependencyItem(dependency) {
  if (dependency?.dependency_type === "scene") {
    if (dependency.matched) {
      await openPackagedMod(dependency.mod_id);
    } else {
      showMissingItemPrompt(dependency);
    }
    return;
  }
  if (dependency?.source_type === "builtin" || dependency?.item?.source_type === "builtin") {
    return;
  }
  if (!dependency?.matched || !dependency.item?.id) {
    showMissingItemPrompt(dependency);
    return;
  }

  activeView.value = "mods";
  libraryMode.value = "items";
  itemTab.value = "详情";
  itemFilters.search = dependency.item.zipmod_guid || dependency.mod_id || "";
  itemFilters.kind = "";
  itemFilters.author = "";
  itemFilters.status = "";
  itemFilters.source = "mod";
  dependencyUsageFilter.value = "";

  await ensureItemDatabaseLoaded({ force: true });

  const targetId = Number(dependency.item.id);
  let target = itemRows.value.find((row) => Number(row.id) === targetId);
  while (!target && itemDatabase.hasMore) {
    await loadItemRows();
    target = itemRows.value.find((row) => Number(row.id) === targetId);
  }

  if (target) {
    selectItem(target);
  } else {
    showMissingItemPrompt(dependency);
  }
}

async function openPackagedMod(guid) {
  const targetGuid = String(guid || "").trim();
  if (!targetGuid) return { ok: false, error: "缺少已打包模组的 GUID" };

  window.clearTimeout(modFilterTimer);
  activeView.value = "mods";
  libraryMode.value = "mods";
  modTab.value = "详情";
  modFilters.author = "";
  modFilters.status = "";
  dependencyUsageFilter.value = "";
  modRows.value = [];
  selectedMod.value = null;
  selectedModItems.value = [];
  selectedModDiagnostics.value = null;
  modDatabase.hasMore = false;

  const findTarget = async () => {
    const query = new URLSearchParams({ guid: targetGuid, offset: "0", limit: "1" });
    const response = await window.desktopApi?.backendRequest?.(`/mods/zipmods?${query.toString()}`);
    if (!response?.ok) throw new Error(response?.error || "模组数据库查询失败");
    const row = response.data?.rows?.[0];
    return row ? mapZipmodRow(row) : null;
  };

  try {
    const target = await findTarget();
    if (!target) {
      return { ok: false, error: `模组数据库中暂时找不到 GUID：${targetGuid}；请重试单个模组同步` };
    }

    modRows.value = [target];
    modDatabase.checked = true;
    modDatabase.exists = true;
    modDatabase.offset = 1;
    modDatabase.total = 1;
    modDatabase.hasMore = false;
    selectMod(target);
    return { ok: true, mod: target };
  } catch (error) {
    log(`[Workbench Error] 跳转模组管理失败：${error.message}`);
    return { ok: false, error: error.message || String(error) };
  }
}

function syncMissingItemPromptRemote() {
  if (!missingItemPrompt.open || !missingItemPrompt.modId) {
    missingItemPrompt.remoteLoading = false;
    missingItemPrompt.remoteCandidate = null;
    missingItemPrompt.remoteEntry = null;
    missingItemPrompt.remoteError = "";
    return;
  }
  const guid = String(missingItemPrompt.modId).trim().toLocaleLowerCase();
  const entry = cardDependencyRemote.byGuid[guid] || null;
  missingItemPrompt.remoteLoading = Boolean(cardDependencyRemote.loading && !entry);
  missingItemPrompt.remoteEntry = entry;
  missingItemPrompt.remoteCandidate = entry?.candidates?.[0] || null;
  missingItemPrompt.remoteError = cardDependencyRemote.error || "";
}

function resetMissingItemPromptRemote() {
  missingItemPrompt.remoteLoading = false;
  missingItemPrompt.remoteCandidate = null;
  missingItemPrompt.remoteEntry = null;
  missingItemPrompt.remoteError = "";
}

function showMissingItemPrompt(dependency) {
  const name = dependency?.item?.name || dependency?.name || dependency?.mod_id || "未知物品";
  missingItemPrompt.kind = dependency?.displayMode === "mod" ? "mod" : "item";
  missingItemPrompt.name = name;
  missingItemPrompt.modId = dependency?.mod_id || dependency?.item?.zipmod_guid || "";
  missingItemPrompt.property = dependency?.property || "";
  missingItemPrompt.open = true;
  syncMissingItemPromptRemote();
  log(`[Cards] 物品缺失：${name}`);
}

async function locateSourceMod(row = selectedItem.value) {
  if (!row || row.isBuiltin || row.raw?.source_type === "builtin") return;
  const zipmodId = Number(row.zipmodId || row.raw?.zipmod_id || 0);
  const sourceAuthor = String(row.raw?.author || row.author || "").trim();
  if (!zipmodId) {
    log("[Items Error] 缺少关联模组 ID");
    return;
  }

  window.clearTimeout(modFilterTimer);
  libraryMode.value = "mods";
  modTab.value = "详情";
  modFilters.author = sourceAuthor && sourceAuthor !== "-" ? sourceAuthor : UNKNOWN_AUTHOR_LABEL;
  modFilters.status = "";
  dependencyUsageFilter.value = "";
  const query = new URLSearchParams({ zipmod_id: String(zipmodId), limit: "1" });
  const result = await window.desktopApi?.backendRequest?.(`/mods/zipmods?${query.toString()}`);
  const targetRow = result?.data?.rows?.[0];
  const target = targetRow ? mapZipmodRow(targetRow) : null;

  if (!target) {
    log(`[Items Error] 未找到来源模组：${row.sourceMod || zipmodId}`);
    return;
  }
  modRows.value = [target];
  modDatabase.checked = true;
  modDatabase.exists = true;
  modDatabase.offset = 1;
  modDatabase.total = 1;
  modDatabase.hasMore = false;
  selectMod(target);
}

async function loadSelectedModItems() {
  if (!selectedMod.value || selectedModItemsLoading.value) return;
  selectedModItemsLoading.value = true;
  selectedModItemsError.value = "";
  try {
    const result = await window.desktopApi?.backendRequest?.(
      `/mods/items?zipmod_id=${selectedMod.value.id}&offset=0&limit=1000`
    );
    if (!result?.ok) {
      throw new Error(result?.error || "关联物品读取失败");
    }
    selectedModItems.value = (result.data?.rows || []).map(mapModItemRow);
  } catch (error) {
    selectedModItemsError.value = error.message;
    selectedModItems.value = [];
    log(`[Mods Error] ${error.message}`);
  } finally {
    selectedModItemsLoading.value = false;
  }
}

function setModTab(tab) {
  modTab.value = tab;
  if (tab === "\u8bca\u65ad") {
    loadSelectedModDiagnostics();
  }
  if (tab === "物品") {
    loadSelectedModItems();
  }
}

async function loadSelectedModDiagnostics() {
  if (!selectedMod.value) return;
  const zipmodId = selectedMod.value.id;
  selectedModDiagnosticsLoading.value = true;
  selectedModDiagnosticsError.value = "";
  try {
    const result = await window.desktopApi?.backendRequest?.(
      `/mods/zipmods/${zipmodId}/diagnostics`
    );
    if (!selectedMod.value || selectedMod.value.id !== zipmodId) return;
    if (!result?.ok) {
      throw new Error(result?.error || "\u8bca\u65ad\u8bfb\u53d6\u5931\u8d25");
    }
    selectedModDiagnostics.value = result;
  } catch (error) {
    if (!selectedMod.value || selectedMod.value.id !== zipmodId) return;
    selectedModDiagnosticsError.value = error.message;
    selectedModDiagnostics.value = null;
    log(`[Mods Error] ${error.message}`);
  } finally {
    if (selectedMod.value?.id === zipmodId) {
      selectedModDiagnosticsLoading.value = false;
    }
  }
}

function unity3dIssueTitle(issue) {
  if (issue.type === "manifest_author") return "缺少模组作者";
  if (issue.type === "thumbnail") return "缩略图异常";
  if (issue.type === "duplicate_zipmod") return "存在重复模组";
  if (issue.status === "error") return "Unity3D 文件资源读取异常";
  if (["in_game", "not_in_mod"].includes(issue.status)) return "Unity3D 文件不在当前 zipmod 内";
  if (issue.status === "missing") return "Unity3D \u6587\u4ef6\u65e0\u6cd5\u627e\u5230";
  if (issue.status === "duplicate") return "存在重复模组";
  return "Unity3D \u6587\u4ef6\u5f02\u5e38";
}

function unity3dIssueSummary(issue) {
  if (issue.type === "manifest_author") return "manifest.xml 缺少 author 字段。";
  if (issue.type === "thumbnail") return "部分物品缩略图缺失或读取失败。";
  if (issue.type === "duplicate_zipmod") return "同一 GUID 存在多个 zipmod 文件。";
  if (issue.status === "error") return "Unity3D 文件存在，但没有解析出可用 Unity 资源。";
  if (["in_game", "not_in_mod"].includes(issue.status)) {
    if (issue.source === "other_zipmod") return "Unity3D 文件不在当前 zipmod 内，由其它 zipmod 提供。";
    return "Unity3D 文件不在当前 zipmod 内。";
  }
  if (issue.status === "missing") return "Unity3D 文件缺失。";
  if (issue.status === "duplicate") return "存在重复文件。";
  return issue.solution || "-";
}

function unity3dIssueSolution(issue) {
  if (issue.type === "manifest_author") return "补充并保存 manifest.xml 的作者字段。";
  if (issue.type === "thumbnail") return "重新导入或生成物品缩略图。";
  if (issue.type === "duplicate_zipmod") return "分析同 GUID 的 zipmod 并保留推荐项。";
  if (issue.status === "error") return "重新安装来源模组，或替换该 unity3d 文件后重建数据库。";
  if (["in_game", "not_in_mod"].includes(issue.status)) {
    if (issue.source === "other_zipmod") return "当前 zipmod 不含该文件，但其它 zipmod 已提供，无需补入。";
    return "将该文件复制进 zipmod 包内对应 abdata 路径，使模组包自包含；CSV 引用路径保持不变。";
  }
  if (issue.status === "missing") return "\u91cd\u65b0\u5b89\u88c5\u6765\u6e90\u6a21\u7ec4\uff0c\u6216\u624b\u52a8\u627e\u56de\u8be5 unity3d \u6587\u4ef6\u540e\u91cd\u5efa\u6570\u636e\u5e93\u3002";
  if (issue.status === "duplicate") return "分析同 GUID 的 zipmod 并保留推荐项。";
  return issue.solution || "-";
}

function unity3dIssueFileName(issue) {
  const path = String(issue?.path || "").trim();
  if (!path) return "-";
  return path.split(/[\\/]/).filter(Boolean).pop() || path;
}

function itemUnity3dFileName(item) {
  const path = String(item?.raw?.main_ab || "").trim();
  if (!path) return "-";
  return path.split(/[\\/]/).filter(Boolean).pop() || path;
}

function thumbnailMissingSourceType(item, detail) {
  const sourcePath = String(detail || "")
    .replace(/^.*source not found:\s*/i, "")
    .trim();
  const candidates = [sourcePath, item?.thumb_ab, item?.thumb_tex]
    .map((value) => String(value || "").toLowerCase().trim())
    .filter(Boolean);
  if (candidates.some((value) => value.endsWith(".unity3d"))) return "unity3d";
  if (candidates.some((value) => /\.(png|jpe?g|bmp|gif|webp|tga|dds)$/.test(value))) return "image";
  return "";
}

function thumbnailIssueReason(item) {
  const detail = String(item?.thumbnail_error_detail || item?.thumbnail_error || "").trim();
  if (!detail) return "缩略图未生成";
  if (detail.includes("ThumbAB/ThumbTex") || detail.includes("ThumbAB and ThumbTex are empty")) {
    return "缺少 ThumbAB/ThumbTex";
  }
  if (detail.includes("source not found") || detail.includes("源文件不存在")) {
    const sourceType = thumbnailMissingSourceType(item, detail);
    if (sourceType === "unity3d") return "Unity3D 源文件不存在";
    if (sourceType === "image") return "图片源文件不存在";
    return "源文件不存在";
  }
  if (detail.includes("UnityPy load failed") || detail.includes("Unity3D 文件无法打开")) {
    return "Unity3D 文件读取失败";
  }
  if (detail.includes("UnityPy loaded no objects") || detail.includes("没有解析出任何资源")) {
    return "Unity3D 未解析出资源";
  }
  if (detail.includes("asset not found") || detail.includes("贴图资源")) {
    return "图片解码失败";
  }
  if (detail.includes("extract failed") || detail.includes("提取") || detail.includes("解码")) {
    return "提取失败";
  }
  if (detail.includes("CRC")) return "文件校验失败";
  return detail.length > 22 ? `${detail.slice(0, 22)}...` : detail;
}

async function repairUnity3dIssue(issue) {
  if (!selectedMod.value || !issue?.path) return;
  repairingUnity3dPath.value = issue.path;
  try {
    const result = await window.desktopApi?.backendRequest?.(
      `/mods/zipmods/${selectedMod.value.id}/repair-unity3d`,
      {
        method: "POST",
        body: { path: issue.path }
      }
    );
    if (!result?.ok) {
      throw new Error(result?.error || "\u4fee\u590d\u5931\u8d25");
    }
    log(`[Mods] ${result.message || "unity3d repair completed"}`);
    selectedModDiagnostics.value = null;
    await loadSelectedModDiagnostics();
    await refreshModDatabaseList();
    await loadAchievements({ notify: true });
  } catch (error) {
    selectedModDiagnosticsError.value = error.message;
    log(`[Mods Error] ${error.message}`);
  } finally {
    repairingUnity3dPath.value = "";
  }
}

async function bulkRepairUnity3dFromGame() {
  const zipmodIds = [...selectedModIds.value];
  if (zipmodIds.length === 0 || bulkActionBusy.value) return;

  bulkUnity3dPrompt.open = true;
}

const openBulkRepairUnity3dPrompt = bulkRepairUnity3dFromGame;

async function submitBulkRepairUnity3dFromGame() {
  const zipmodIds = [...selectedModIds.value];
  if (zipmodIds.length === 0 || bulkActionBusy.value) return;

  bulkUnity3dPrompt.open = false;
  bulkActionBusy.value = "unity3d";

  try {
    await submitTask("bulk_repair_zipmods_unity3d", { zipmod_ids: zipmodIds });
    selectedModDiagnostics.value = null;
    await refreshModDatabaseList();
  } catch (error) {
    log(`[Mods Error] ${error.message}`);
  } finally {
    bulkActionBusy.value = "";
  }
}

function openBulkDuplicateCleanupPrompt() {
  if (selectedModCount.value === 0 || bulkActionBusy.value) return;
  bulkDuplicateCleanupPrompt.error = "";
  bulkDuplicateCleanupPrompt.open = true;
}

function openBulkDeletePrompt() {
  if (selectedModCount.value === 0 || bulkActionBusy.value) return;
  bulkDeletePrompt.error = "";
  bulkDeletePrompt.open = true;
}

async function submitBulkDuplicateCleanup() {
  const zipmodIds = [...selectedModIds.value];
  if (zipmodIds.length === 0 || bulkActionBusy.value) return;

  bulkActionBusy.value = "duplicates";
  bulkDuplicateCleanupPrompt.error = "";
  try {
    await submitTaskInBackground("bulk_cleanup_duplicate_zipmods", { zipmod_ids: zipmodIds }, async (task) => {
      if (task.status === "completed") {
        selectedModDiagnostics.value = null;
        await refreshModDatabaseList();
      } else if (task.status === "failed") {
        bulkDuplicateCleanupPrompt.error = task.error || "智能清理重复模组失败";
        log(`[Mods Error] ${bulkDuplicateCleanupPrompt.error}`);
      }
      bulkActionBusy.value = "";
    });
    bulkDuplicateCleanupPrompt.open = false;
  } catch (error) {
    bulkDuplicateCleanupPrompt.error = error.message;
    bulkActionBusy.value = "";
    log(`[Mods Error] ${error.message}`);
  }
}

async function submitBulkDeleteZipmods() {
  const zipmodIds = [...selectedModIds.value];
  if (zipmodIds.length === 0 || bulkActionBusy.value) return;

  bulkActionBusy.value = "delete";
  bulkDeletePrompt.error = "";
  try {
    await submitTaskInBackground("bulk_delete_zipmods", { zipmod_ids: zipmodIds }, async (task) => {
      if (task.status === "completed") {
        selectedModDiagnostics.value = null;
        selectedMod.value = null;
        selectedModIds.value = new Set();
        await refreshModDatabaseList();
      } else if (task.status === "failed") {
        bulkDeletePrompt.error = task.error || "批量删除模组失败";
        log(`[Mods Error] ${bulkDeletePrompt.error}`);
      }
      bulkActionBusy.value = "";
    });
    bulkDeletePrompt.open = false;
  } catch (error) {
    bulkDeletePrompt.error = error.message;
    bulkActionBusy.value = "";
    log(`[Mods Error] ${error.message}`);
  }
}

async function openBulkAuthorPrompt() {
  const zipmodIds = [...selectedModIds.value];
  if (zipmodIds.length === 0 || bulkActionBusy.value) return;
  bulkAuthorPrompt.value = "";
  bulkAuthorPrompt.error = "";
  bulkAuthorPrompt.open = true;
  await loadZipmodAuthors();
}

async function bulkUpdateModAuthors() {
  const zipmodIds = [...selectedModIds.value];
  if (zipmodIds.length === 0 || bulkActionBusy.value) return;

  const author = String(bulkAuthorPrompt.value || "").trim();
  if (!author) {
    bulkAuthorPrompt.error = "请输入作者名称";
    return;
  }

  bulkActionBusy.value = "author";
  bulkAuthorPrompt.error = "";

  try {
    await submitTaskInBackground("bulk_update_zipmod_authors", { zipmod_ids: zipmodIds, author }, async (task) => {
      if (task.status === "completed") {
        selectedModDiagnostics.value = null;
        await refreshModDatabaseList();
      }
    });
    bulkAuthorPrompt.open = false;
    log("[Mods] bulk author update completed");
  } catch (error) {
    bulkAuthorPrompt.error = error.message;
  } finally {
    bulkActionBusy.value = "";
  }
}

function openBulkExportPrompt() {
  if (selectedModCount.value === 0 || bulkActionBusy.value) return;
  bulkExportPrompt.targetDir = paths.outputDir || "";
  bulkExportPrompt.mode = "copy";
  bulkExportPrompt.confirmMove = false;
  bulkExportPrompt.error = "";
  bulkExportPrompt.open = true;
}

function selectBulkAuthorSuggestion(author) {
  bulkAuthorPrompt.value = author;
  bulkAuthorPrompt.error = "";
}

async function selectBulkExportDir() {
  const selected = await window.desktopApi?.selectDirectory?.("选择模组导出目录");
  if (!selected) return;
  bulkExportPrompt.targetDir = selected;
  bulkExportPrompt.confirmMove = false;
}

async function submitBulkExport() {
  const zipmodIds = [...selectedModIds.value];
  if (zipmodIds.length === 0 || bulkActionBusy.value) return;

  const targetDir = String(bulkExportPrompt.targetDir || "").trim();
  if (!targetDir) {
    bulkExportPrompt.error = "请选择导出目录";
    return;
  }

  const mode = bulkExportPrompt.mode === "move" ? "move" : "copy";
  if (mode === "move" && !bulkExportPrompt.confirmMove) {
    bulkExportPrompt.confirmMove = true;
    bulkExportPrompt.error = "";
    return;
  }

  bulkActionBusy.value = "export";
  bulkExportPrompt.confirmMove = false;
  bulkExportPrompt.error = "";
  try {
    await submitTaskInBackground("bulk_export_zipmods", {
      zipmod_ids: zipmodIds,
      target_dir: targetDir,
      mode
    }, async (task) => {
      if (task.status === "completed") {
        await refreshModDatabaseList();
      } else if (task.status === "failed") {
        bulkExportPrompt.error = task.error || "批量导出模组失败";
        log(`[Mods Error] ${bulkExportPrompt.error}`);
      }
      bulkActionBusy.value = "";
    });
    bulkExportPrompt.open = false;
    window.requestAnimationFrame(() => document.activeElement?.blur?.());
    paths.outputDir = targetDir;
    await saveAppSettings();
  } catch (error) {
    bulkExportPrompt.error = error.message;
    bulkActionBusy.value = "";
    log(`[Mods Error] ${error.message}`);
  }
}

function openBulkOrganizePrompt() {
  if (selectedModCount.value === 0 || bulkActionBusy.value) return;
  bulkOrganizePrompt.targetDir = paths.outputDir || "";
  bulkOrganizePrompt.error = "";
  bulkOrganizePrompt.open = true;
}

async function selectBulkOrganizeDir() {
  const selected = await window.desktopApi?.selectDirectory?.("选择模组整理目录");
  if (!selected) return;
  bulkOrganizePrompt.targetDir = selected;
}

async function submitBulkOrganize() {
  const zipmodIds = [...selectedModIds.value];
  if (zipmodIds.length === 0 || bulkActionBusy.value) return;

  const targetDir = String(bulkOrganizePrompt.targetDir || "").trim();
  if (!targetDir) {
    bulkOrganizePrompt.error = "请选择整理目录";
    return;
  }

  bulkActionBusy.value = "organize";
  bulkOrganizePrompt.error = "";
  try {
    await submitTask("bulk_organize_zipmods", {
      zipmod_ids: zipmodIds,
      target_dir: targetDir
    });
    bulkOrganizePrompt.open = false;
    paths.outputDir = targetDir;
    await saveAppSettings();
  } catch (error) {
    bulkOrganizePrompt.error = error.message;
    log(`[Mods Error] ${error.message}`);
  } finally {
    bulkActionBusy.value = "";
  }
}

const missingThumbnailTargetItems = computed(() => {
  const sourceId = Number(selectedItem.value?.id || 0);
  return itemRows.value.filter((item) => {
    if (Number(item.id) === sourceId) return false;
    if (item.itemDomain === "studio") return false;
    const thumbnailStatus = String(item.raw?.thumbnail_status || "");
    return item.status === "thumb" || !["ready", "ok"].includes(thumbnailStatus);
  });
});

const selectedThumbnailTargetCount = computed(() => thumbnailToolsPrompt.selectedTargetIds.size);

function openThumbnailToolsPrompt() {
  if (!selectedItem.value || bulkActionBusy.value) return;
  thumbnailToolsPrompt.targetDir = thumbnailToolsPrompt.targetDir || paths.outputDir || "";
  thumbnailToolsPrompt.selectedTargetIds = new Set();
  thumbnailToolsPrompt.error = "";
  thumbnailToolsPrompt.open = true;
}

async function selectThumbnailToolDir() {
  const selected = await window.desktopApi?.selectDirectory?.("选择缩略图导出目录");
  if (!selected) return;
  thumbnailToolsPrompt.targetDir = selected;
  thumbnailToolsPrompt.error = "";
}

function toggleThumbnailTarget(item) {
  if (!item?.id || bulkActionBusy.value) return;
  const next = new Set(thumbnailToolsPrompt.selectedTargetIds);
  const id = Number(item.id);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  thumbnailToolsPrompt.selectedTargetIds = next;
}

function setAllThumbnailTargets(selected) {
  thumbnailToolsPrompt.selectedTargetIds = selected
    ? new Set(missingThumbnailTargetItems.value.map((item) => Number(item.id)))
    : new Set();
}

async function exportCurrentItemThumbnail() {
  if (bulkActionBusy.value || !selectedItem.value?.id) return;
  const targetDir = String(thumbnailToolsPrompt.targetDir || "").trim();
  if (!targetDir) {
    thumbnailToolsPrompt.error = "请选择缩略图导出目录";
    return;
  }
  if (selectedItem.value.status !== "ready" || !selectedItem.value.raw?.thumbnail_cache_path) {
    thumbnailToolsPrompt.error = "当前物品没有可导出的缩略图";
    return;
  }

  bulkActionBusy.value = "thumb-export";
  thumbnailToolsPrompt.error = "";
  try {
    const result = await window.desktopApi?.backendRequest?.(
      `/mods/items/${selectedItem.value.id}/export-thumbnail`,
      {
        method: "POST",
        body: { target_dir: targetDir }
      }
    );
    if (!result?.ok) {
      throw new Error(result?.error || "缩略图导出失败");
    }
    paths.outputDir = targetDir;
    await saveAppSettings();
    log(`[Items] ${result.message || "thumbnail exported"}: ${result.target_path || targetDir}`);
  } catch (error) {
    thumbnailToolsPrompt.error = error.message;
  } finally {
    bulkActionBusy.value = "";
  }
}

async function applyCurrentThumbnailToTargets() {
  if (bulkActionBusy.value || !selectedItem.value?.id) return;
  const targetItemIds = [...thumbnailToolsPrompt.selectedTargetIds];
  if (targetItemIds.length === 0) {
    thumbnailToolsPrompt.error = "请选择要导入缩略图的目标物品";
    return;
  }
  const sourceImagePath = String(selectedItem.value.raw?.thumbnail_cache_path || "");
  if (selectedItem.value.status !== "ready" || !sourceImagePath) {
    thumbnailToolsPrompt.error = "当前物品没有可导入的缩略图";
    return;
  }

  bulkActionBusy.value = "thumb-import";
  thumbnailToolsPrompt.error = "";
  try {
    await submitTaskInBackground("bulk_apply_item_thumbnail", {
      source_item_id: selectedItem.value.id,
      source_image_path: sourceImagePath,
      target_item_ids: targetItemIds
    }, async (task) => {
      if (task.status === "completed") {
        await refreshModDatabaseList();
      }
    });
    thumbnailToolsPrompt.open = false;
    log(`[Items] thumbnail imported to ${targetItemIds.length} items`);
  } catch (error) {
    thumbnailToolsPrompt.error = error.message;
  } finally {
    bulkActionBusy.value = "";
  }
}

async function openBulkDeleteErrorItemsPrompt() {
  if (libraryMode.value !== "items" || bulkActionBusy.value) return;
  bulkDeleteErrorItemsPrompt.error = "";
  try {
    const count = await fetchCurrentErrorItemCount();
    bulkDeleteErrorItemsPrompt.count = count;
    if (count <= 0) {
      bulkDeleteErrorItemsPrompt.error = "当前筛选下没有错误物品";
    } else if (count > 1000) {
      bulkDeleteErrorItemsPrompt.error = "当前筛选下错误物品超过 1000 个，请先缩小筛选范围";
    }
    bulkDeleteErrorItemsPrompt.open = true;
  } catch (error) {
    bulkDeleteErrorItemsPrompt.count = 0;
    bulkDeleteErrorItemsPrompt.error = error.message;
    bulkDeleteErrorItemsPrompt.open = true;
  }
}

async function submitBulkDeleteErrorItems() {
  if (bulkActionBusy.value || bulkDeleteErrorItemsPrompt.count <= 0 || bulkDeleteErrorItemsPrompt.count > 1000) return;

  bulkActionBusy.value = "items-delete";
  bulkDeleteErrorItemsPrompt.error = "";
  try {
    await submitTaskInBackground("bulk_delete_error_items", currentErrorItemFilterPayload(), async (task) => {
      if (task.status === "completed") {
        selectedItem.value = null;
        selectedModDiagnostics.value = null;
        await refreshModDatabaseList();
      } else if (task.status === "failed") {
        bulkDeleteErrorItemsPrompt.error = task.error || "批量删除错误物品失败";
        log(`[Items Error] ${bulkDeleteErrorItemsPrompt.error}`);
      }
      bulkActionBusy.value = "";
    });
    bulkDeleteErrorItemsPrompt.open = false;
  } catch (error) {
    bulkDeleteErrorItemsPrompt.error = error.message;
    bulkActionBusy.value = "";
    log(`[Items Error] ${error.message}`);
  }
}

async function repairThumbnailItem(item = selectedItem.value, options = {}) {
  if (!item?.id || item.isBuiltin) return false;
  const imageData = String(options.imageData || "");
  const imagePath = imageData ? "" : await window.desktopApi?.selectImageFile?.("选择 PNG 图片");
  if (!imageData && !imagePath) return false;

  const itemId = item.id;
  repairingThumbnailItemId.value = itemId;
  try {
    const result = await window.desktopApi?.backendRequest?.(
      `/mods/items/${itemId}/import-thumbnail`,
      {
        method: "POST",
        body: imageData ? { image_data: imageData } : { image_path: imagePath }
      }
    );
    if (!result?.ok) {
      throw new Error(result?.error || "缩略图导入失败");
    }
    log(`[Mods] ${result.message || "thumbnail imported"}`);

    if (selectedMod.value) {
      selectedModDiagnostics.value = null;
      if (modTab.value === "诊断") await loadSelectedModDiagnostics();
      if (modTab.value === "物品") await loadSelectedModItems();
    }
    // Importing one thumbnail updates one zipmod and reindexes only that
    // zipmod's item rows. Update the visible row/detail in place instead of
    // resetting and reloading the entire item database list.
    const updatedRow = result.item ? mapModItemRow(result.item) : null;
    if (updatedRow && libraryMode.value === "items") {
      const rowIndex = itemRows.value.findIndex((row) => (
        Number(row.id) === Number(item.id)
        || (
          String(row.raw?.item_id || "") === String(item.raw?.item_id || "")
          && Number(row.raw?.zipmod_id || row.zipmodId) === Number(item.raw?.zipmod_id || item.zipmodId)
          && String(row.raw?.csv_path || "") === String(item.raw?.csv_path || "")
        )
      ));
      if (rowIndex >= 0) {
        itemRows.value[rowIndex] = updatedRow;
      }
      if (selectedItem.value && (rowIndex >= 0 || Number(selectedItem.value.id) === Number(item.id))) {
        selectedItem.value = updatedRow;
      }
    }
    await loadAchievements({ notify: true });
    return true;
  } catch (error) {
    if (selectedMod.value) selectedModDiagnosticsError.value = error.message;
    log(`[Mods Error] ${error.message}`);
  } finally {
    repairingThumbnailItemId.value = null;
  }
}

async function deleteSelectedItem(item = selectedItem.value) {
  if (!item?.id || item.isBuiltin) return;
  deleteItemPrompt.item = item;
  deleteItemPrompt.name = item.name || item.raw?.item_id || String(item.id);
  deleteItemPrompt.error = "";
  deleteItemPrompt.open = true;
}

async function openItemUnity3d(item = selectedItem.value) {
  if (!item?.id || item.isBuiltin || openingUnity3dItemId.value) return false;
  openingUnity3dItemId.value = item.id;
  try {
    const result = await window.desktopApi?.backendRequest?.(
      `/mods/items/${item.id}/open-unity3d`,
      { method: "POST" }
    );
    if (!result?.ok) throw new Error(result?.error || "Unity3D 文件准备失败");
    const launched = await window.desktopApi?.openUnity3dInSb3Utility?.(result.unity3d_path);
    if (!launched?.ok) throw new Error(launched?.error || "SB3Utility 打开失败");
    log(`[Unity3D] ${result.message || "已打开 Unity3D 文件"}: ${result.unity3d_path}`);
    return true;
  } catch (error) {
    log(`[Unity3D Error] ${error.message}`);
    return false;
  } finally {
    openingUnity3dItemId.value = null;
  }
}

async function exportItemUnity3d(item = selectedItem.value) {
  if (!item?.id || item.isBuiltin || exportingUnity3dItemId.value) return false;
  const defaultName = itemUnity3dFileName(item) === "-"
    ? `item_${item.id}.unity3d`
    : itemUnity3dFileName(item);
  const targetPath = await window.desktopApi?.selectUnity3dExportPath?.(
    "导出 Unity3D（复制）",
    defaultName
  );
  if (!targetPath) return false;

  exportingUnity3dItemId.value = item.id;
  try {
    const result = await window.desktopApi?.backendRequest?.(
      `/mods/items/${item.id}/export-unity3d`,
      {
        method: "POST",
        body: { target_path: targetPath }
      }
    );
    if (!result?.ok) throw new Error(result?.error || "Unity3D 导出失败");
    log(`[Unity3D] ${result.message || "已复制导出 Unity3D"}: ${result.target_path || targetPath}`);
    return true;
  } catch (error) {
    log(`[Unity3D Error] ${error.message}`);
    return false;
  } finally {
    exportingUnity3dItemId.value = null;
  }
}

async function confirmDeleteSelectedItem() {
  const item = deleteItemPrompt.item;
  if (!item?.id) return;
  const itemId = item.id;
  deletingItemId.value = itemId;
  deleteItemPrompt.error = "";
  try {
    const result = await window.desktopApi?.backendRequest?.(
      `/mods/items/${itemId}/delete`,
      { method: "POST" }
    );
    if (!result?.ok) {
      throw new Error(result?.error || "删除物品失败");
    }
    log(`[Items] ${result.message || "item deleted"}`);
    deleteItemPrompt.open = false;
    deleteItemPrompt.item = null;
    selectedItem.value = null;
    if (selectedMod.value) {
      selectedModDiagnostics.value = null;
      if (modTab.value === "诊断") await loadSelectedModDiagnostics();
      if (modTab.value === "物品") await loadSelectedModItems();
    }
    await refreshModDatabaseList();
  } catch (error) {
    deleteItemPrompt.error = error.message;
    itemDatabase.error = error.message;
    log(`[Items Error] ${error.message}`);
  } finally {
    deletingItemId.value = null;
  }
}

const deleteModItemRow = deleteSelectedItem;

function openDuplicateZipmodPrompt(issue) {
  duplicateZipmodPrompt.items = [...(issue?.affected_items || [])];
  duplicateZipmodPrompt.analysis = null;
  duplicateZipmodPrompt.analysisLoading = false;
  duplicateZipmodPrompt.error = "";
  duplicateZipmodPrompt.busyId = null;
  duplicateZipmodPrompt.busyAll = false;
  duplicateZipmodPrompt.open = true;
  analyzeDuplicateZipmods();
}

async function openDuplicateZipmodInFolder(item) {
  const filePath = item?.file_path || "";
  if (!filePath) {
    duplicateZipmodPrompt.error = "请先选择一个模组";
    return;
  }
  try {
    const result = await window.desktopApi?.showItemInFolder?.(filePath);
    if (!result?.ok) {
      duplicateZipmodPrompt.error = result?.error || "重复模组分析失败";
    }
  } catch (error) {
    duplicateZipmodPrompt.error = error.message;
  }
}

async function analyzeDuplicateZipmods() {
  if (!selectedMod.value || duplicateZipmodPrompt.analysisLoading) return;
  duplicateZipmodPrompt.analysisLoading = true;
  duplicateZipmodPrompt.error = "";
  try {
    const result = await window.desktopApi?.backendRequest?.(
      `/mods/zipmods/${selectedMod.value.id}/duplicate-analysis`
    );
    if (!result?.ok) {
      throw new Error(result?.error || "重复模组分析失败");
    }
    duplicateZipmodPrompt.analysis = result;
  } catch (error) {
    duplicateZipmodPrompt.error = error.message;
  } finally {
    duplicateZipmodPrompt.analysisLoading = false;
  }
}

async function cleanupDuplicateZipmods(duplicateIds = null, zipmodIdOverride = null) {
  const zipmodId = Number(zipmodIdOverride || selectedMod.value?.id || 0);
  if (!zipmodId) return;
  const ids = Array.isArray(duplicateIds) ? duplicateIds.map((id) => Number(id)).filter(Boolean) : null;
  cleaningDuplicateZipmods.value = true;
  if (ids?.length === 1) {
    duplicateZipmodPrompt.busyId = ids[0];
  } else {
    duplicateZipmodPrompt.busyAll = true;
  }
  duplicateZipmodPrompt.error = "";
  try {
    const result = await window.desktopApi?.backendRequest?.(
      `/mods/zipmods/${zipmodId}/cleanup-duplicates`,
      {
        method: "POST",
        body: ids ? { duplicate_ids: ids } : {}
      }
    );
    if (!result?.ok) {
      throw new Error(result?.error || "清理重复模组失败");
    }
    log(`[Mods] ${result.message || "duplicate zipmods cleaned"}`);
    const clearedIds = new Set((result.cleared_ids || ids || []).map((id) => Number(id)));
    if (clearedIds.size > 0) {
      duplicateZipmodPrompt.items = duplicateZipmodPrompt.items.filter((item) => !clearedIds.has(Number(item.id)));
      if (duplicateZipmodPrompt.analysis?.candidates) {
        duplicateZipmodPrompt.analysis = {
          ...duplicateZipmodPrompt.analysis,
          candidates: duplicateZipmodPrompt.analysis.candidates.filter((item) => !clearedIds.has(Number(item.duplicate_id)))
        };
      }
    }
    if (duplicateZipmodPrompt.items.length === 0) {
      duplicateZipmodPrompt.open = false;
    }
    selectedModDiagnostics.value = null;
    await loadSelectedModDiagnostics();
    await refreshModDatabaseList();
    await loadAchievements({ notify: true });
  } catch (error) {
    duplicateZipmodPrompt.error = error.message;
    log(`[Mods Error] ${error.message}`);
  } finally {
    cleaningDuplicateZipmods.value = false;
    duplicateZipmodPrompt.busyId = null;
    duplicateZipmodPrompt.busyAll = false;
  }
}

async function cleanupRecommendedDuplicateZipmods() {
  const ids = duplicateRecommendedDuplicateIds.value;
  if (ids.length === 0) {
    duplicateZipmodPrompt.error = "当前推荐没有可直接删除的重复文件";
    return;
  }
  await cleanupDuplicateZipmods(ids);
}

async function mergeDuplicateZipmod(candidate) {
  if (!selectedMod.value || !candidate) return;
  const duplicateId = Number(candidate.duplicate_id || 0);
  if (!duplicateId) {
    duplicateZipmodPrompt.error = "没有找到要合并的重复模组";
    return;
  }
  duplicateZipmodPrompt.busyId = duplicateId;
  duplicateZipmodPrompt.error = "";
  try {
    const result = await window.desktopApi?.backendRequest?.(
      `/mods/zipmods/${selectedMod.value.id}/merge-duplicate`,
      {
        method: "POST",
        body: { duplicate_id: duplicateId }
      }
    );
    if (!result?.ok) {
      throw new Error(result?.error || "合并重复模组失败");
    }
    log(`[Mods] ${result.message || "duplicate zipmod merged"}`);
    duplicateZipmodPrompt.open = false;
    duplicateZipmodDeleteConfirm.open = false;
    selectedModDiagnostics.value = null;
    await refreshModDatabaseList();
    await loadSelectedModDiagnostics();
  } catch (error) {
    duplicateZipmodPrompt.error = error.message;
    log(`[Mods Error] ${error.message}`);
    return false;
  } finally {
    duplicateZipmodPrompt.busyId = null;
  }
}

async function cleanupAllExceptRecommendedZipmod() {
  if (duplicateZipmodPrompt.analysisLoading) return;
  if (!duplicateZipmodPrompt.analysis) {
    duplicateZipmodPrompt.error = "请先完成重复模组分析";
    return;
  }
  if (!duplicateRecommendedKeep.value) {
    duplicateZipmodPrompt.error = "没有可用的推荐保留项";
    return;
  }

  if (duplicateRecommendsPrimaryDeletion.value) {
    openDuplicateZipmodDeleteConfirm(duplicateRecommendedKeep.value);
    return;
  }

  if (duplicateRecommendedMerge.value.length > 0) {
    await mergeDuplicateZipmod(duplicateRecommendedMerge.value[0]);
    return;
  }

  await cleanupRecommendedDuplicateZipmods();
}

function openDuplicateZipmodDeleteConfirm(candidate = duplicateRecommendedKeep.value) {
  if (!selectedMod.value || !candidate) return;
  if (candidate.role === "duplicate" && !Number(candidate.duplicate_id || 0)) {
    duplicateZipmodPrompt.error = "没有找到要保留的重复模组";
    return;
  }
  duplicateZipmodDeleteConfirm.keepLabel = candidate.file_name || candidate.file_path || "保留文件";
  duplicateZipmodDeleteConfirm.keepRole = candidate.role || "";
  duplicateZipmodDeleteConfirm.duplicateId = candidate.role === "duplicate" ? Number(candidate.duplicate_id) : null;
  duplicateZipmodDeleteConfirm.primaryZipmodId = Number(selectedMod.value.id);
  duplicateZipmodDeleteConfirm.open = true;
}

async function confirmKeepDuplicateZipmodCandidate() {
  if (!selectedMod.value) return;
  const primaryZipmodId = Number(duplicateZipmodDeleteConfirm.primaryZipmodId || selectedMod.value.id || 0);
  if (!primaryZipmodId) {
    duplicateZipmodPrompt.error = "没有找到当前主记录";
    return;
  }
  const keepDuplicateId = Number(duplicateZipmodDeleteConfirm.duplicateId || 0);
  if (duplicateZipmodDeleteConfirm.keepRole === "duplicate" && !keepDuplicateId) {
    duplicateZipmodPrompt.error = "没有找到要保留的重复模组";
    return;
  }

  const ids = (duplicateZipmodPrompt.analysis?.candidates || [])
    .filter((candidate) => candidate.role === "duplicate")
    .map((candidate) => Number(candidate.duplicate_id))
    .filter((id) => Number.isFinite(id) && id > 0 && id !== keepDuplicateId);

  if (duplicateZipmodDeleteConfirm.keepRole !== "duplicate") {
    if (ids.length) {
      await cleanupDuplicateZipmods(ids);
    }
    duplicateZipmodDeleteConfirm.open = false;
    return;
  }

  duplicateZipmodDeleteConfirm.open = false;
  duplicateZipmodPrompt.busyAll = true;
  duplicateZipmodPrompt.error = "";
  try {
    const result = await window.desktopApi?.backendRequest?.(
      `/mods/zipmods/${primaryZipmodId}/promote-duplicate`,
      {
        method: "POST",
        body: { duplicate_id: keepDuplicateId }
      }
    );
    if (!result?.ok) {
      throw new Error(result?.error || "删除重复模组失败");
    }
    log(`[Mods] ${result.message || "primary zipmod deleted"}`);
    duplicateZipmodPrompt.open = false;
    selectedModDiagnostics.value = null;
    await refreshModDatabaseList();
    if (result.promoted_zipmod_id) {
      const promoted = modRows.value.find((row) => Number(row.id) === Number(result.promoted_zipmod_id));
      if (promoted) selectMod(promoted);
    } else {
      selectedMod.value = null;
    }
    if (ids.length && result.promoted_zipmod_id) {
      await cleanupDuplicateZipmods(ids, result.promoted_zipmod_id);
    }
  } catch (error) {
    duplicateZipmodPrompt.error = error.message;
    log(`[Mods Error] ${error.message}`);
  } finally {
    duplicateZipmodPrompt.busyAll = false;
  }
}

async function deleteSelectedMod() {
  if (!selectedMod.value) return;
  deleteModPrompt.mod = selectedMod.value;
  deleteModPrompt.name = selectedMod.value.name || selectedMod.value.raw?.file_name || String(selectedMod.value.id);
  deleteModPrompt.error = "";
  deleteModPrompt.open = true;
}

async function confirmDeleteSelectedMod() {
  const mod = deleteModPrompt.mod;
  if (!mod?.id) return;
  deleteModPrompt.error = "";
  try {
    const result = await window.desktopApi?.backendRequest?.(
      `/mods/zipmods/${mod.id}/delete`,
      { method: "POST" }
    );
    if (!result?.ok) {
      throw new Error(result?.error || "删除模组失败");
    }
    log(`[Mods] ${result.message || "zipmod deleted"}`);
    deleteModPrompt.open = false;
    deleteModPrompt.mod = null;
    selectedModDiagnostics.value = null;
    selectedMod.value = null;
    await refreshModDatabaseList();
  } catch (error) {
    deleteModPrompt.error = error.message;
    selectedModDiagnosticsError.value = error.message;
    log(`[Mods Error] ${error.message}`);
  }
}

function openManifestAuthorPrompt(issue) {
  manifestAuthorPrompt.value = issue.affected_items?.[0]?.author || "";
  manifestAuthorPrompt.zipmodId = selectedMod.value?.id || null;
  manifestAuthorPrompt.error = "";
  manifestAuthorPrompt.open = true;
}

async function submitManifestAuthor() {
  if (!manifestAuthorPrompt.zipmodId) return;
  const author = String(manifestAuthorPrompt.value || "").trim();
  if (!author) {
    manifestAuthorPrompt.error = "请输入作者名称";
    return;
  }

  manifestAuthorPrompt.busy = true;
  manifestAuthorPrompt.error = "";
  try {
    const result = await window.desktopApi?.backendRequest?.(
      `/mods/zipmods/${manifestAuthorPrompt.zipmodId}/update-author`,
      {
        method: "POST",
        body: { author }
      }
    );
    if (!result?.ok) {
      throw new Error(result?.error || "保存作者失败");
    }
    log(`[Mods] ${result.message || "manifest author updated"}`);
    manifestAuthorPrompt.open = false;
    selectedModDiagnostics.value = null;
    await loadSelectedModDiagnostics();
    await refreshModDatabaseList();
  } catch (error) {
    manifestAuthorPrompt.error = error.message;
  } finally {
    manifestAuthorPrompt.busy = false;
  }
}

function applyUpdatedZipmodRow(row) {
  if (!row?.id) return;
  const mapped = mapZipmodRow(row);
  modRows.value = modRows.value.map((mod) => (Number(mod.id) === Number(mapped.id) ? mapped : mod));
  if (selectedMod.value && Number(selectedMod.value.id) === Number(mapped.id)) {
    selectedMod.value = mapped;
  }
}

async function openManifestEditor() {
  if (!selectedMod.value || manifestEditor.loading) return;
  manifestEditor.open = true;
  manifestEditor.zipmodId = selectedMod.value.id;
  manifestEditor.loading = true;
  manifestEditor.busy = false;
  manifestEditor.error = "";
  manifestEditor.fields = {
    guid: selectedMod.value.guid || "",
    name: selectedMod.value.name || "",
    version: selectedMod.value.version === "-" ? "" : selectedMod.value.version || "",
    author: selectedMod.value.author === UNKNOWN_AUTHOR_LABEL ? "" : selectedMod.value.author || ""
  };

  try {
    const result = await window.desktopApi?.backendRequest?.(
      `/mods/zipmods/${selectedMod.value.id}/manifest`
    );
    if (!result?.ok) {
      throw new Error(result?.error || "manifest 读取失败");
    }
    const fields = Object.fromEntries(
      (result.fields || []).map((field) => [field.key, field.value || ""])
    );
    manifestEditor.fields = {
      guid: fields.guid || "",
      name: fields.name || "",
      version: fields.version || "",
      author: fields.author || ""
    };
  } catch (error) {
    manifestEditor.error = error.message;
  } finally {
    manifestEditor.loading = false;
  }
}

async function submitManifestEditor() {
  if (!manifestEditor.zipmodId || manifestEditor.busy) return;
  const fields = {
    guid: String(manifestEditor.fields.guid || "").trim(),
    name: String(manifestEditor.fields.name || "").trim(),
    version: String(manifestEditor.fields.version || "").trim(),
    author: String(manifestEditor.fields.author || "").trim()
  };
  const missingLabel = [
    ["name", "名称"],
    ["version", "版本"],
    ["author", "作者"],
  ].find(([key]) => !fields[key])?.[1];
  if (missingLabel) {
    manifestEditor.error = `请输入${missingLabel}`;
    return;
  }

  manifestEditor.busy = true;
  manifestEditor.error = "";
  try {
    const result = await window.desktopApi?.backendRequest?.(
      `/mods/zipmods/${manifestEditor.zipmodId}/manifest`,
      {
        method: "POST",
        body: { fields }
      }
    );
    if (!result?.ok) {
      throw new Error(result?.error || "manifest 保存失败");
    }
    applyUpdatedZipmodRow(result.zipmod);
    log(`[Mods] ${result.message || "manifest.xml updated"}`);
    manifestEditor.open = false;
    selectedModDiagnostics.value = null;
    await loadSelectedModDiagnostics();
    await loadZipmodAuthors();
  } catch (error) {
    manifestEditor.error = error.message;
  } finally {
    manifestEditor.busy = false;
  }
}

async function openSelectedModInFolder() {
  const filePath = selectedMod.value?.raw?.file_path || "";
  if (!filePath) {
    log("[Mods Error] 当前模组没有文件路径");
    return;
  }

  try {
    const result = await window.desktopApi?.showItemInFolder?.(filePath);
    if (!result?.ok) {
      log(`[Mods Error] ${result?.error || "无法打开所在文件夹"}`);
    }
  } catch (error) {
    log(`[Mods Error] ${error.message}`);
  }
}

async function checkModDatabase() {
  modDatabase.loading = true;
  modDatabase.error = "";
  try {
    const databaseQuery = paths.gameDir ? `?game_dir=${encodeQuery(paths.gameDir)}` : "";
    const result = await window.desktopApi?.backendRequest?.(`/mods/database${databaseQuery}`);
    if (!result?.ok) {
      throw new Error(result?.error || "模组数据库读取失败");
    }

    const database = result.database || {};
    modDatabase.checked = true;
    modDatabase.exists = Boolean(database.exists);
    modDatabase.total = Number(database.zipmod_count || 0);
    stats.zipmodErrors = Number(database.zipmod_error_count ?? stats.zipmodErrors);
    stats.zipmodWarnings = Number(database.zipmod_warning_count ?? stats.zipmodWarnings);
    stats.duplicateZipmods = Number(database.duplicate_guid_count ?? stats.duplicateZipmods);
    stats.lastDatabaseBuiltAt = database.last_built_at || stats.lastDatabaseBuiltAt;
    itemDatabase.checked = true;
    itemDatabase.exists = Boolean(database.exists);
    itemDatabase.total = Number(database.item_count || 0) + Number(database.builtin_item_count || 0);
    stats.zipmods = Number(database.zipmod_count ?? stats.zipmods);
    stats.modItems = Number(database.item_count ?? stats.modItems);
    stats.builtinItems = Number(database.builtin_item_count ?? stats.builtinItems);

    if (!modDatabase.exists || modDatabase.total === 0) {
      modRows.value = [];
      selectedMod.value = null;
      selectedModIds.value = new Set();
      selectedModItems.value = [];
      modDatabase.offset = 0;
      modDatabase.hasMore = false;
    }

    if (!itemDatabase.exists || itemDatabase.total === 0) {
      itemRows.value = [];
      selectedItem.value = null;
      itemDatabase.offset = 0;
      itemDatabase.hasMore = false;
    }

    if (!modDatabase.exists) {
      log("[Mods] database changes checked");
    } else if (modDatabase.total === 0) {
      log("[Mods] database is fresh");
    }

    return modDatabase.exists;
  } catch (error) {
    modDatabase.checked = true;
    modDatabase.exists = false;
    modDatabase.error = error.message;
    itemDatabase.checked = true;
    itemDatabase.exists = false;
    itemDatabase.error = error.message;
    modRows.value = [];
    itemRows.value = [];
    selectedMod.value = null;
    selectedItem.value = null;
    selectedModIds.value = new Set();
    selectedModItems.value = [];
    log(`[Mods Error] ${error.message}`);
    return false;
  } finally {
    modDatabase.loading = false;
  }
}

async function checkStartupDatabaseChanges() {
  if (!paths.gameDir) return;
  if (isBusy.value) return;
  try {
    await checkModDatabase();
    const result = await window.desktopApi?.backendRequest?.(
      `/mods/database/changes?game_dir=${encodeQuery(paths.gameDir)}`
    );
    if (!result?.ok) {
      throw new Error(result?.error || "检查数据库变化失败");
    }
    const data = result.data || {};
    if (!data.needs_rebuild) {
      log("[Database] 数据库已是最新状态");
      return;
    }
    if (data.recommended_action === "auto_incremental") {
      const totalChanges = Number(data.total_changes || 0);
      taskHint.value = `检测到 ${totalChanges} 个文件变化，正在更新数据库`;
      log(`[Database] detected ${totalChanges} file changes; rebuilding database`);
      await submitTask("build_mod_database", { mode: "incremental" });
      return;
    }
    taskHint.value = "检测到较大变化，请手动重建数据库";
    const changes = data.changes || {};
    log(
      `[Database] 检测到较大变动，请手动重建数据库。zipmods=${changes.zipmods?.changed_total ?? 0}, cards=${changes.cards?.changed_total ?? 0}`
    );
  } catch (error) {
    log(`[Database Error] ${error.message}`);
  }
}

async function loadModRows({ reset = false } = {}) {
  if (libraryMode.value !== "mods") return;
  if (modDatabase.loading || modDatabase.loadingMore) return;
  if (!modDatabase.exists) return;
  if (!reset && modDatabase.total === 0) return;
  if (!reset && !modDatabase.hasMore && modRows.value.length > 0) return;

  const offset = reset ? 0 : modRows.value.length;
  modDatabase.loading = reset;
  modDatabase.loadingMore = !reset;
  modDatabase.error = "";

  try {
    const query = new URLSearchParams({
      offset: String(offset),
      limit: String(modDatabase.limit)
    });
    if (modFilters.author) query.set("author", modFilters.author);
    if (modFilters.status) query.set("status", modFilters.status);
    if (dependencyUsageFilter.value) query.set("usage", dependencyUsageFilter.value);
    const result = await window.desktopApi?.backendRequest?.(`/mods/zipmods?${query.toString()}`);
    if (!result?.ok) {
      throw new Error(result?.error || "模组列表读取失败");
    }

    const data = result.data || {};
    if (!data.exists) {
      modDatabase.checked = true;
      modDatabase.exists = false;
      modRows.value = [];
      selectedMod.value = null;
      selectedModIds.value = new Set();
      selectedModItems.value = [];
      modDatabase.offset = 0;
      modDatabase.total = 0;
      modDatabase.hasMore = false;
      log("[Mods] database changes checked");
      return;
    }

    const rows = (data.rows || []).map(mapZipmodRow);
    modRows.value = reset ? rows : [...modRows.value, ...rows];
    if (reset) selectedMod.value = null;
    if (reset) selectedModItems.value = [];
    if (modBulkMode.value) syncSelectedModIdsWithVisibleRows();
    modDatabase.offset = modRows.value.length;
    modDatabase.total = Number(data.total || 0);
    modDatabase.hasMore = Boolean(data.has_more);
    stats.zipmods = modDatabase.total;
  } catch (error) {
    modDatabase.error = error.message;
    log(`[Mods Error] ${error.message}`);
  } finally {
    modDatabase.loading = false;
    modDatabase.loadingMore = false;
  }
}

async function loadItemRows({ reset = false } = {}) {
  if (libraryMode.value !== "items") return;
  if (!reset && (itemDatabase.loading || itemDatabase.loadingMore)) return;
  if (!itemDatabase.exists) return;
  if (!reset && itemDatabase.total === 0) return;
  if (!reset && !itemDatabase.hasMore && itemRows.value.length > 0) return;

  const offset = reset ? 0 : itemRows.value.length;
  const requestSeq = ++itemRowsRequestSeq;
  if (reset) {
    itemRows.value = [];
    selectedItem.value = null;
    itemDatabase.offset = 0;
    itemDatabase.total = 0;
    itemDatabase.hasMore = false;
    itemDatabase.loadingMore = false;
  }
  itemDatabase.loading = reset;
  itemDatabase.loadingMore = !reset;
  itemDatabase.error = "";

  try {
    const query = new URLSearchParams({
      offset: String(offset),
      limit: String(itemDatabase.limit)
    });
    if (itemFilters.search.trim()) query.set("search", itemFilters.search.trim());
    if (itemFilters.kind) query.set("kind", itemFilters.kind);
    if (itemFilters.author) query.set("author", itemFilters.author);
    if (itemFilters.status) query.set("status", itemFilters.status);
    if (dependencyUsageFilter.value) query.set("usage", dependencyUsageFilter.value);
    query.set("source", itemFilters.source || "all");
    query.set("include_total", reset ? "1" : "0");
    if (paths.gameDir) query.set("game_dir", paths.gameDir);
    const result = await window.desktopApi?.backendRequest?.(`/mods/items?${query.toString()}`);
    if (requestSeq !== itemRowsRequestSeq) return;
    if (!result?.ok) {
      throw new Error(result?.error || "物品列表读取失败");
    }

    const data = result.data || {};
    if (!data.exists) {
      itemDatabase.checked = true;
      itemDatabase.exists = false;
      itemRows.value = [];
      selectedItem.value = null;
      itemDatabase.offset = 0;
      itemDatabase.total = 0;
      itemDatabase.hasMore = false;
      log("[Items] database changes checked");
      return;
    }

    const rows = (data.rows || []).map(mapModItemRow);
    itemRows.value = reset ? rows : [...itemRows.value, ...rows];
    if (reset) selectedItem.value = null;
    itemDatabase.offset = itemRows.value.length;
    if (data.total != null) itemDatabase.total = Number(data.total || 0);
    itemDatabase.hasMore = Boolean(data.has_more);
  } catch (error) {
    if (requestSeq !== itemRowsRequestSeq) return;
    itemDatabase.error = error.message;
    log(`[Items Error] ${error.message}`);
  } finally {
    if (requestSeq === itemRowsRequestSeq) {
      itemDatabase.loading = false;
      itemDatabase.loadingMore = false;
    }
  }
}

async function ensureModDatabaseLoaded({ force = false } = {}) {
  if (libraryMode.value !== "mods") return;
  if (!backendReady.value) return;
  // Do not restart an initial page or continuation request when KeepAlive
  // activates this view again. A reset request would clear modRows, clamp the
  // scroll container to the top, and lose the session position.
  if (!force && (modDatabase.loading || modDatabase.loadingMore)) return;
  if (!force && modDatabase.checked && modDatabase.exists && modRows.value.length > 0) {
    await loadZipmodAuthors();
    return;
  }

  const exists = await checkModDatabase();
  if (exists) {
    await loadModRows({ reset: true });
    await loadZipmodAuthors();
  }
}

async function ensureItemDatabaseLoaded({ force = false } = {}) {
  if (libraryMode.value !== "items") return;
  if (!backendReady.value) return;
  // Keep an in-flight first page or continuation request alive when the user
  // navigates away and returns before it finishes. Restarting it would clear
  // the already accumulated rows and reset the virtual list's load state.
  if (!force && (itemDatabase.loading || itemDatabase.loadingMore)) return;
  if (!force && itemDatabase.checked && itemDatabase.exists && itemRows.value.length > 0) {
    await loadItemFilters();
    return;
  }

  const exists = await checkModDatabase();
  if (exists) {
    await loadItemRows({ reset: true });
    void loadItemFilters();
  }
}

function selectedItemRefreshSnapshot() {
  const row = selectedItem.value;
  if (!row?.id) return null;
  return {
    id: row.id,
    sourceType: String(row.sourceType || row.raw?.source_type || "mod"),
    itemId: String(row.raw?.item_id || ""),
    kind: String(row.raw?.kind || row.kindCode || ""),
    zipmodId: Number(row.raw?.zipmod_id || row.zipmodId || 0),
    zipmodGuid: String(row.raw?.zipmod_guid || ""),
    csvPath: String(row.raw?.csv_path || "")
  };
}

function itemMatchesRefreshSnapshot(row, snapshot) {
  if (!row || !snapshot) return false;
  const raw = row.raw || {};
  const sourceType = String(row.sourceType || raw.source_type || "mod");
  if (sourceType !== snapshot.sourceType) return false;
  if (sourceType === "builtin") {
    return Boolean(
      snapshot.itemId
      && String(raw.item_id || "") === snapshot.itemId
      && String(raw.kind || row.kindCode || "") === snapshot.kind
    );
  }
  const stableMatch = Boolean(
    snapshot.itemId
    && snapshot.zipmodId
    && String(raw.item_id || "") === snapshot.itemId
    && Number(raw.zipmod_id || row.zipmodId || 0) === snapshot.zipmodId
    && (!snapshot.csvPath || String(raw.csv_path || "") === snapshot.csvPath)
  ) || Boolean(
    snapshot.itemId
    && snapshot.zipmodGuid
    && String(raw.item_id || "") === snapshot.itemId
    && String(raw.zipmod_guid || "") === snapshot.zipmodGuid
  );
  if (snapshot.itemId && (snapshot.zipmodId || snapshot.zipmodGuid)) {
    return stableMatch;
  }
  return Boolean(snapshot.id && Number(row.id) === snapshot.id);
}

async function restoreSelectedItemAfterRefresh(snapshot) {
  if (!snapshot || libraryMode.value !== "items") return;
  // A user click that happens while the list is loading takes precedence.
  if (selectedItem.value) return;

  let target = itemRows.value.find((row) => itemMatchesRefreshSnapshot(row, snapshot));
  while (!target && itemDatabase.hasMore) {
    const loadedCount = itemRows.value.length;
    await loadItemRows();
    if (itemRows.value.length === loadedCount) break;
    target = itemRows.value.find((row) => itemMatchesRefreshSnapshot(row, snapshot));
  }
  if (target && !selectedItem.value) {
    selectedItem.value = target;
  }
}

async function refreshModDatabaseList() {
  if (libraryMode.value === "items") {
    const snapshot = selectedItemRefreshSnapshot();
    await ensureItemDatabaseLoaded({ force: true });
    await restoreSelectedItemAfterRefresh(snapshot);
    return;
  }
  await ensureModDatabaseLoaded({ force: true });
  await loadZipmodAuthors();
}

function handleModTableScroll(event) {
  const target = event.currentTarget;
  const remaining = target.scrollHeight - target.scrollTop - target.clientHeight;
  // Start item requests before the user reaches the absolute end so the
  // network/database work can overlap with the last visible rows.
  const preloadDistance = libraryMode.value === "items" ? 480 : 160;
  if (remaining >= preloadDistance) return;

  if (libraryMode.value === "items") {
    loadItemRows();
  } else if (libraryMode.value === "mods") {
    loadModRows();
  }
}

function applyGameDir(selected) {
  window.clearTimeout(clothesIndexRetryTimer);
  clothesIndexRetryTimer = 0;
  window.clearTimeout(clothesTreeRefreshTimer);
  clothesTreeRefreshTimer = 0;
  paths.gameDir = selected || "";
  gamePluginSetup.checking = false;
  gamePluginSetup.status = selected ? "待检查" : "未检查";
  gamePluginSetup.installedCount = 0;
  gamePluginSetup.error = "";
  resetStartPluginSettings();
  paths.inputDir = selected ? `${selected}\\UserData\\chara` : "";
  clearResourceStats();
  modDatabase.checked = false;
  modDatabase.exists = false;
  itemDatabase.checked = false;
  itemDatabase.exists = false;
  zipmodAuthors.value = [];
  itemFilterAuthors.value = [];
  itemFilterKinds.value = [];
  selectedCardFolder.value = "";
  clothesLibrary.checked = false;
  clothesLibrary.loading = false;
  clothesLibrary.loadingMore = false;
  clothesLibrary.detailLoading = false;
  clothesLibrary.error = "";
  clothesLibrary.validGameDir = false;
  clothesLibrary.root = "";
  clothesLibrary.total = null;
  clothesLibrary.indexing = false;
  clothesLibrary.treeIndexing = false;
  clothesLibrary.nextOffset = 0;
  clothesLibrary.hasMore = false;
  resetClothesTree();
  clothesCards.value = [];
  selectedClothesFolder.value = "";
  selectedClothesDetailPath.value = "";
  selectedClothesDetail.value = null;
  clothesSideMode.value = "tree";
  sceneLibrary.checked = false;
  sceneLibrary.loading = false;
  sceneLibrary.loadingMore = false;
  sceneLibrary.detailLoading = false;
  sceneLibrary.error = "";
  sceneLibrary.validGameDir = false;
  sceneLibrary.root = "";
  sceneLibrary.total = null;
  sceneLibrary.nextOffset = 0;
  sceneLibrary.hasMore = false;
  resetSceneTree();
  sceneCards.value = [];
  selectedSceneFolder.value = "";
  selectedSceneDetailPath.value = "";
  selectedSceneDetail.value = null;
  sceneSideMode.value = "tree";
  gameDirStatus.value = selected ? "检查中" : "未选择";
  taskHint.value = selected ? "正在检查游戏目录" : "请选择有效目录后点击重建";
}

async function ensureGamePlugins(gameDir = paths.gameDir) {
  const normalizedGameDir = String(gameDir || "").trim();
  if (!normalizedGameDir) return { ok: false, error: "未选择游戏目录" };
  gamePluginSetup.checking = true;
  gamePluginSetup.status = "检查中";
  gamePluginSetup.installedCount = 0;
  gamePluginSetup.error = "";
  try {
    const result = await window.desktopApi?.ensureGamePlugins?.(normalizedGameDir);
    if (!result?.ok) {
      gamePluginSetup.status = "安装失败";
      gamePluginSetup.error = result?.error || "插件检查失败";
      log(`[Plugins] ${gamePluginSetup.error}`);
      return result || { ok: false, error: gamePluginSetup.error };
    }
    gamePluginSetup.status = "已就绪";
    gamePluginSetup.installedCount = Number(result.installed_count || 0);
    const installed = gamePluginSetup.installedCount;
    log(installed > 0
      ? `[Plugins] 已自动安装 ${installed} 个 Star Manager 插件到 ${result.destination_dir}`
      : "[Plugins] Star Manager 三个插件均已存在（保留现有启用/禁用状态）");
    return result;
  } catch (error) {
    gamePluginSetup.status = "安装失败";
    gamePluginSetup.error = error.message;
    log(`[Plugins] ${error.message}`);
    return { ok: false, error: error.message };
  } finally {
    gamePluginSetup.checking = false;
  }
}

async function loadStartPluginSettings(gameDir = paths.gameDir) {
  resetStartPluginSettings();
  const normalizedGameDir = String(gameDir || "").trim();
  if (!normalizedGameDir) return { ok: false, error: "未选择游戏目录" };
  startPluginSettings.loading = true;
  try {
    const query = new URLSearchParams({ game_dir: normalizedGameDir });
    const [pluginResult, specialResult] = await Promise.all([
      window.desktopApi?.backendRequest(`/plugins/status?${query.toString()}`),
      window.desktopApi?.backendRequest(`/game/special-settings?${query.toString()}`)
    ]);
    if (!pluginResult?.ok) throw new Error(pluginResult?.error || "插件状态读取失败");
    if (!specialResult?.ok) throw new Error(specialResult?.error || "特殊设置读取失败");
    const files = Array.isArray(pluginResult.data?.items) ? pluginResult.data.items : [];
    const byPath = new Map(files.map((item) => [pluginPathIdentity(item.relative_path), item]));
    const pluginItems = START_PLUGIN_DEFINITIONS.map((definition) => {
      const item = byPath.get(pluginPathIdentity(definition.relativePath));
      return {
        ...definition,
        kind: "plugin",
        installed: Boolean(item),
        enabled: Boolean(item?.enabled),
        actualPath: item?.relative_path || definition.relativePath,
        busy: false
      };
    });
    const specialByKey = new Map((Array.isArray(specialResult.data?.items) ? specialResult.data.items : []).map((item) => [item.key, item]));
    const specialItems = START_SPECIAL_SETTING_DEFINITIONS.map((definition) => {
      const item = specialByKey.get(definition.key);
      return {
        ...definition,
        installed: Boolean(item?.available),
        enabled: Boolean(item?.enabled),
        actualPath: item?.relative_path || definition.relativePath,
        itemError: item?.error || "",
        busy: false
      };
    });
    startPluginSettings.items = [...pluginItems, ...specialItems];
    return { ok: true, data: { items: startPluginSettings.items } };
  } catch (error) {
    startPluginSettings.error = error?.message || String(error);
    return { ok: false, error: startPluginSettings.error };
  } finally {
    startPluginSettings.loading = false;
  }
}

async function loadPluginStats(gameDir = paths.gameDir) {
  const normalizedGameDir = String(gameDir || "").trim();
  stats.plugins = null;
  if (!backendReady.value || !normalizedGameDir) return;

  try {
    const query = new URLSearchParams({ game_dir: normalizedGameDir, limit: "1" });
    const result = await window.desktopApi?.backendRequest?.(`/plugins?${query.toString()}`);
    if (!result?.ok) throw new Error(result?.error || "插件统计读取失败");
    const total = Number(result.data?.summary?.total ?? result.data?.total);
    if (!Number.isFinite(total)) throw new Error("插件扫描未返回有效数量");
    if (String(paths.gameDir || "").trim() !== normalizedGameDir) return;
    stats.plugins = total;
  } catch (error) {
    log(`[Plugins] 总览统计读取失败：${error.message}`);
  }
}

async function toggleStartPlugin(plugin) {
  if (!plugin?.installed || plugin.busy || !paths.gameDir) return;
  const enabled = !plugin.enabled;
  plugin.busy = true;
  startPluginSettings.error = "";
  try {
    const result = await window.desktopApi?.backendRequest(
      plugin.kind === "special" ? "/game/special-settings/toggle" : "/plugins/toggle",
      {
        method: "POST",
        body: {
          game_dir: paths.gameDir,
          ...(plugin.kind === "special"
            ? { key: plugin.key, enabled }
            : { relative_path: plugin.actualPath, enabled })
        }
      }
    );
    if (!result?.ok) throw new Error(result?.error || "插件状态修改失败");
    const data = result.data || {};
    plugin.enabled = typeof data.enabled === "boolean" ? data.enabled : enabled;
    plugin.actualPath = data.relative_path || plugin.actualPath;
  } catch (error) {
    startPluginSettings.error = error?.message || String(error);
  } finally {
    plugin.busy = false;
  }
}

function applyGameSetupPayload(payload) {
  const gameSetup = payload?.setup || {};
  const width = Number(gameSetup.width) || 1280;
  const height = Number(gameSetup.height) || 720;
  setup.language = Number.isFinite(Number(gameSetup.language)) ? Number(gameSetup.language) : 0;
  setup.quality = Number.isFinite(Number(gameSetup.quality)) ? Number(gameSetup.quality) : 1;
  setup.display = Number.isFinite(Number(gameSetup.display)) ? Number(gameSetup.display) : 0;
  setup.width = width;
  setup.height = height;
  setup.resolution = gameSetup.resolution || `${width} x ${height}`;
  setup.fullscreen = Boolean(gameSetup.fullscreen);
  setup.loaded = true;
  setup.exists = Boolean(payload.exists);
  setup.loading = false;
  setup.saving = false;
  setup.dirty = false;
  setup.error = "";
  setup.warning = payload.registry?.ok === false ? `配置已保存，但注册表同步失败：${payload.registry.error}` : "";
  setup.filePath = payload.filePath || "";
  setup.backupPath = payload.backupPath || "";
  setup.displays = Array.isArray(payload.displays) && payload.displays.length
    ? payload.displays
    : [{ index: 0, label: "Display 0" }];
  setup.resolutions = Array.isArray(payload.resolutions) && payload.resolutions.length
    ? payload.resolutions
    : [{ label: setup.resolution, width, height }];
}

async function loadGameSetup() {
  if (!paths.gameDir) return false;
  setup.loading = true;
  setup.error = "";
  setup.warning = "";
  try {
    const result = await window.desktopApi?.loadGameSetup?.(paths.gameDir);
    if (!result?.ok) {
      throw new Error(result?.error || "读取 setup.xml 失败");
    }
    applyGameSetupPayload(result);
    log(`[Setup] 已读取 ${result.filePath}${result.exists ? "" : "（文件不存在，将按默认值创建）"}`);
    return true;
  } catch (error) {
    setup.loading = false;
    setup.loaded = false;
    setup.dirty = false;
    setup.error = error.message;
    log(`[Setup Error] ${error.message}`);
    return false;
  }
}

async function saveAppSettings(options = {}) {
  const saveOperation = settingsSaveQueue
    .catch(() => undefined)
    .then(async () => {
      const result = await window.desktopApi?.saveSettings?.({
        gameDir: paths.gameDir,
        inputDir: paths.inputDir,
        outputDir: paths.outputDir,
        directoryShortcuts: serializeDirectoryShortcuts(),
        workbenchAuthorId: workbenchAuthorId.value,
        workbenchWorkspacePath: workbenchWorkspacePath.value,
        workbenchActiveProjectId: workbenchActiveProjectId.value,
        workbenchProjects: serializeWorkbenchProjects(),
        coordinateExportDir: coordinateExportDir.value,
        portablePackageDir: portablePackageDir.value,
        blenderExecutablePath: blenderExecutablePath.value,
        sb3utilityExecutablePath: sb3utilityExecutablePath.value,
        portablePackageCompress: portablePackageCompress.value,
        portablePackageTypes: [...portablePackageTypes.value],
        characterCardLoadOptions: [...cardLoadPrompt.selected],
        startupView: managerSettings.startupView,
        favoriteCardTheme: managerSettings.favoriteCardTheme,
        checkDatabaseChangesOnStartup: managerSettings.checkDatabaseChangesOnStartup,
        databaseWorkerCount: managerSettings.databaseWorkerCount,
        wallpaperPath: managerSettings.wallpaperPath,
        wallpaperType: managerSettings.wallpaperType,
        clearSb3UtilityExecutablePath: options.clearSb3UtilityExecutablePath === true
      });
      if (!result?.ok) {
        log(`[Settings Error] ${result?.error || "settings save failed"}`);
      }
      return result;
    });
  settingsSaveQueue = saveOperation.catch(() => undefined);
  return saveOperation;
}

async function loadAppSettingsInternal({ loadBackendData = true } = {}) {
  try {
    const result = await measureStep("loadSettings", () => window.desktopApi?.loadSettings?.());
    if (!result?.ok) {
      log(`[Settings Error] ${result?.error || "settings load failed"}`);
      return;
    }
    coordinateExportDir.value = result.settings?.coordinateExportDir || "";
    portablePackageDir.value = result.settings?.portablePackageDir || "";
    blenderExecutablePath.value = result.settings?.blenderExecutablePath || "";
    sb3utilityExecutablePath.value = result.settings?.sb3utilityExecutablePath || "";
    portablePackageCompress.value = result.settings?.portablePackageCompress !== false;
    portablePackageTypes.value = Array.isArray(result.settings?.portablePackageTypes)
      ? PORTABLE_PACKAGE_TYPES.map((type) => type.key).filter((type) => result.settings.portablePackageTypes.includes(type))
      : PORTABLE_PACKAGE_TYPES.map((type) => type.key);
    cardLoadPrompt.selected = Array.isArray(result.settings?.characterCardLoadOptions)
      ? CARD_LOAD_OPTIONS.map((option) => option.key).filter((optionKey) => result.settings.characterCardLoadOptions.includes(optionKey))
      : CARD_LOAD_OPTIONS.map((option) => option.key);
    managerSettings.startupView = result.settings?.startupView || "start";
    managerSettings.favoriteCardTheme = ["gold", "neon", "sakura", "obsidian"].includes(result.settings?.favoriteCardTheme)
      ? result.settings.favoriteCardTheme
      : "gold";
    managerSettings.checkDatabaseChangesOnStartup = result.settings?.checkDatabaseChangesOnStartup !== false;
    managerSettings.databaseWorkerLimit = Math.max(
      1,
      Number(result.settings?.databaseWorkerLimit) || 1
    );
    managerSettings.databaseLogicalProcessorCount = Math.max(
      1,
      Number(result.settings?.databaseLogicalProcessorCount) || managerSettings.databaseWorkerLimit * 2
    );
    const savedDatabaseWorkerCount = Number(result.settings?.databaseWorkerCount);
    managerSettings.databaseWorkerCount = Number.isInteger(savedDatabaseWorkerCount)
      ? Math.min(managerSettings.databaseWorkerLimit, Math.max(1, savedDatabaseWorkerCount))
      : managerSettings.databaseWorkerLimit;
    const previousWallpaperPath = managerSettings.wallpaperPath;
    const previousWallpaperType = managerSettings.wallpaperType;
    wallpaperLoadFailed.value = false;
    managerSettings.wallpaperPath = result.settings?.wallpaperPath || "";
    managerSettings.wallpaperType = result.settings?.wallpaperType || "";
    if (
      previousWallpaperPath !== managerSettings.wallpaperPath
      || previousWallpaperType !== managerSettings.wallpaperType
    ) {
      wallpaperReady.value = !managerSettings.wallpaperPath;
    }
    const cachedWorkbenchProfile = readWorkbenchProfileCache();
    workbenchAuthorId.value = result.settings?.workbenchAuthorId || cachedWorkbenchProfile.authorId;
    workbenchWorkspacePath.value = result.settings?.workbenchWorkspacePath || cachedWorkbenchProfile.workspacePath;
    workbenchActiveProjectId.value = result.settings?.workbenchActiveProjectId || "";
    workbenchProjects.value = Array.isArray(result.settings?.workbenchProjects)
      ? result.settings.workbenchProjects
      : [];
    paths.outputDir = result.settings?.outputDir || "";
    directoryShortcuts.value = Array.isArray(result.settings?.directoryShortcuts)
      ? result.settings.directoryShortcuts
      : [];
    const gameDir = result.settings?.gameDir || "";
    applyGameDir(gameDir);
    activeView.value = managerSettings.startupView;
    if (!gameDir) return;
    if (!loadBackendData) return;
    log(`[Settings] 已读取游戏目录：${gameDir}`);
    await measureStep("check_game_dir task", () => validateGameDir());
    await measureStep("ensureGamePlugins after settings", () => ensureGamePlugins(gameDir));
    await measureStep("loadStartPluginSettings after settings", () => loadStartPluginSettings(gameDir));
    await measureStep("refreshWorkbenchProjects after settings", () => refreshWorkbenchProjects({ persist: true }));
    await measureStep("loadGameSetup after settings", () => loadGameSetup());
    await measureStep("loadCardTree after settings", () => loadCardTree());
    await Promise.all([
      measureStep("loadClothesTree after settings", () => ensureClothesLibraryLoaded()),
      measureStep("loadSceneTree after settings", () => ensureSceneLibraryLoaded()),
      measureStep("loadPluginStats after settings", () => loadPluginStats(gameDir))
    ]);
    if (managerSettings.checkDatabaseChangesOnStartup) {
      await measureStep("checkStartupDatabaseChanges", () => checkStartupDatabaseChanges());
    }
  } catch (error) {
    log(`[Settings Error] ${error.message}`);
  }
}

let appSettingsLoadPromise = null;
let appSettingsLoadNeedsBackend = false;
let appSettingsLoadRunningWithBackend = false;

async function loadAppSettings(options = {}) {
  const requestsBackend = options.loadBackendData !== false;
  if (requestsBackend && !appSettingsLoadRunningWithBackend) appSettingsLoadNeedsBackend = true;
  if (appSettingsLoadPromise) return appSettingsLoadPromise;

  const operation = (async () => {
    try {
      do {
        const loadBackendData = appSettingsLoadNeedsBackend;
        appSettingsLoadNeedsBackend = false;
        appSettingsLoadRunningWithBackend = loadBackendData;
        await loadAppSettingsInternal({ loadBackendData });
      } while (appSettingsLoadNeedsBackend);
    } finally {
      appSettingsLoadRunningWithBackend = false;
      appSettingsLoadPromise = null;
    }
  })();
  appSettingsLoadPromise = operation;
  return operation;
}

async function selectWallpaper() {
  const selected = await window.desktopApi?.selectWallpaperFile?.("选择应用壁纸", managerSettings.wallpaperPath);
  if (!selected?.path) return;
  const nextPath = String(selected.path || "").trim();
  const nextType = selected.type || (/\.mp4$/i.test(nextPath) ? "video" : "image");
  const wallpaperChanged = managerSettings.wallpaperPath !== nextPath || managerSettings.wallpaperType !== nextType;
  wallpaperLoadFailed.value = false;
  wallpaperReady.value = !wallpaperChanged;
  managerSettings.wallpaperPath = nextPath;
  managerSettings.wallpaperType = nextType;
  const result = await saveAppSettings();
  settingsNotice.type = result?.ok ? "success" : "error";
  settingsNotice.message = result?.ok ? "壁纸已保存" : `保存失败：${result?.error || "未知错误"}`;
}

async function clearWallpaper() {
  managerSettings.wallpaperPath = "";
  managerSettings.wallpaperType = "";
  wallpaperReady.value = true;
  wallpaperLoadFailed.value = false;
  const result = await saveAppSettings();
  settingsNotice.type = result?.ok ? "success" : "error";
  settingsNotice.message = result?.ok ? "已恢复默认壁纸" : `保存失败：${result?.error || "未知错误"}`;
}

async function updateManagerSetting(key, value) {
  if (!(key in managerSettings)) return;
  managerSettings[key] = value;
  const result = await saveAppSettings();
  settingsNotice.type = result?.ok ? "success" : "error";
  settingsNotice.message = result?.ok ? "设置已保存" : `保存失败：${result?.error || "未知错误"}`;
}

async function updateDatabaseWorkerCount(value) {
  const requested = Number(value);
  const limit = Math.max(1, Number(managerSettings.databaseWorkerLimit) || 1);
  const normalized = Number.isInteger(requested)
    ? Math.min(limit, Math.max(1, requested))
    : limit;
  await updateManagerSetting("databaseWorkerCount", normalized);
}

async function updatePortablePackageCompress(value) {
  portablePackageCompress.value = Boolean(value);
  const result = await saveAppSettings();
  settingsNotice.type = result?.ok ? "success" : "error";
  settingsNotice.message = result?.ok ? "设置已保存" : `保存失败：${result?.error || "未知错误"}`;
}

async function selectSettingsDirectory(kind) {
  const config = {
    output: { title: "选择默认导出目录", apply: (value) => { paths.outputDir = value; } },
    coordinate: { title: "选择服装卡导出目录", apply: (value) => { coordinateExportDir.value = value; } },
    portable: { title: "选择便携依赖包导出目录", apply: (value) => { portablePackageDir.value = value; } }
  }[kind];
  if (!config) return;
  const selected = await window.desktopApi?.selectDirectory?.(config.title);
  if (!selected) return;
  config.apply(selected);
  const result = await saveAppSettings();
  settingsNotice.type = result?.ok ? "success" : "error";
  settingsNotice.message = result?.ok ? "默认目录已更新" : `保存失败：${result?.error || "未知错误"}`;
}

async function saveDefaultOutputDirectory(directoryPath) {
  paths.outputDir = String(directoryPath || "");
  const result = await saveAppSettings();
  if (!result?.ok) {
    log(`[Settings Error] ${result?.error || "default output directory save failed"}`);
  }
  return result;
}

async function saveWorkbenchProfile(authorId, workspacePath) {
  workbenchAuthorId.value = String(authorId || "").trim();
  workbenchWorkspacePath.value = String(workspacePath || "").trim();
  writeWorkbenchProfileCache(workbenchAuthorId.value, workbenchWorkspacePath.value);
  const result = await saveAppSettings();
  if (!result?.ok) {
    log(`[Settings Error] ${result?.error || "workbench profile save failed"}`);
    return result;
  }
  await refreshWorkbenchProjects({ persist: true });
  return result;
}

async function setWorkbenchActiveProject(projectId) {
  const nextId = String(projectId || "").trim();
  const project = workbenchProjectsInCurrentWorkspace().find((item) => String(item?.id || "") === nextId);
  if (!project) return { ok: false, error: "工程不在当前工作空间内" };

  const previousId = workbenchActiveProjectId.value;
  workbenchActiveProjectId.value = nextId;
  const result = await saveAppSettings();
  if (!result?.ok) {
    workbenchActiveProjectId.value = previousId;
    return result;
  }
  return { ok: true, project };
}

async function createWorkbenchProject(name) {
  const result = await window.desktopApi?.createWorkbenchProject?.({
    name: String(name || "").trim(),
    authorId: workbenchAuthorId.value,
    workspacePath: workbenchWorkspacePath.value
  });
  if (!result?.ok || !result.project) {
    log(`[Workbench Error] ${result?.error || "workbench project creation failed"}`);
    return result || { ok: false, error: "模组工程创建失败" };
  }

  workbenchProjects.value = [...workbenchProjects.value, result.project];
  syncWorkbenchActiveProject();
  const saved = await saveAppSettings();
  if (!saved?.ok) {
    log(`[Settings Error] ${saved?.error || "workbench project save failed"}`);
    return { ok: false, error: `工程已创建，但项目记录保存失败：${saved?.error || "未知错误"}`, project: result.project };
  }
  log(`[Workbench] Created project: ${result.project.path}`);
  return result;
}

async function deleteWorkbenchProject(project) {
  const projectId = String(project?.id || "").trim();
  const target = workbenchProjects.value.find((item) => String(item?.id || "") === projectId);
  if (!target) return { ok: false, error: "工程不存在或已被删除" };

  const result = await window.desktopApi?.deleteWorkbenchProject?.({
    projectId,
    projectPath: target.path,
    workspacePath: workbenchWorkspacePath.value
  });
  if (!result?.ok) {
    log(`[Workbench Error] ${result?.error || "workbench project deletion failed"}`);
    return result || { ok: false, error: "工程删除失败" };
  }

  workbenchProjects.value = workbenchProjects.value.filter((item) => String(item?.id || "") !== projectId);
  syncWorkbenchActiveProject();
  const saved = await saveAppSettings();
  if (!saved?.ok) {
    log(`[Settings Error] ${saved?.error || "workbench project save failed"}`);
    return { ok: true, warning: `工程已删除，但项目记录保存失败：${saved?.error || "未知错误"}`, project: target };
  }
  log(`[Workbench] Deleted project: ${target.path}`);
  return { ok: true, project: target };
}

async function selectBlenderExecutable() {
  const selected = await window.desktopApi?.selectBlenderExecutable?.("选择 Blender 可执行文件（blender.exe）");
  if (!selected) return;
  blenderExecutablePath.value = selected;
  const result = await saveAppSettings();
  settingsNotice.type = result?.ok ? "success" : "error";
  settingsNotice.message = result?.ok ? "Blender 路径已保存" : `保存失败：${result?.error || "未知错误"}`;
}

async function clearBlenderExecutable() {
  blenderExecutablePath.value = "";
  const result = await saveAppSettings();
  settingsNotice.type = result?.ok ? "success" : "error";
  settingsNotice.message = result?.ok ? "Blender 路径已清除" : `保存失败：${result?.error || "未知错误"}`;
}

async function selectSb3UtilityExecutable() {
  const selected = await window.desktopApi?.selectSb3UtilityExecutable?.("选择 SB3Utility 可执行文件（.exe）");
  if (!selected) return;
  sb3utilityExecutablePath.value = selected;
  const result = await saveAppSettings();
  settingsNotice.type = result?.ok ? "success" : "error";
  settingsNotice.message = result?.ok ? "SB3Utility 路径已保存" : `保存失败：${result?.error || "未知错误"}`;
}

async function resetSb3UtilityExecutable() {
  sb3utilityExecutablePath.value = "";
  const result = await saveAppSettings({ clearSb3UtilityExecutablePath: true });
  if (result?.ok) {
    sb3utilityExecutablePath.value = result.settings?.sb3utilityExecutablePath || "";
  }
  settingsNotice.type = result?.ok ? "success" : "error";
  settingsNotice.message = result?.ok ? "SB3Utility 路径已恢复默认" : `保存失败：${result?.error || "未知错误"}`;
}

async function validateGameDir() {
  if (!paths.gameDir) {
    gameDirStatus.value = "未选择";
    taskHint.value = "请选择有效目录后点击重建";
    return null;
  }
  gameDirStatus.value = "检查中";
  taskHint.value = "正在检查游戏目录";
  log(`[Game Dir Check] submit: ${paths.gameDir}`);
  const task = await submitTask("check_game_dir");
  if (!task && gameDirStatus.value === "检查中") {
    gameDirStatus.value = "检查失败";
    taskHint.value = "后端未就绪，无法检查目录";
  }
  return task;
}

async function selectGameDir() {
  const selected = await window.desktopApi?.selectDirectory?.("选择 HS2 目录");
  if (!selected) return;
  applyGameDir(selected);
  await ensureGamePlugins(selected);
  await loadStartPluginSettings(selected);
  await saveAppSettings();
  log(`[Directory] 选择游戏目录: ${selected}`);
  await loadGameSetup();
  await validateGameDir();
  await loadCardTree();
  await Promise.all([
    ensureClothesLibraryLoaded({ force: true }),
    ensureSceneLibraryLoaded({ force: true }),
    loadPluginStats(selected)
  ]);
  await checkStartupDatabaseChanges();
  await loadItemFilters();
}

async function launchExecutable(launchType) {
  const labels = {
    game: "开始游戏",
    studio: "开始工作室",
    vr: "开始 VR"
  };

  if (!paths.gameDir) {
    log("[Launch Error] Please select an HS2 directory first.");
    return;
  }

  if (!setup.loaded) {
    log(`[Launch Error] ${labels[launchType] || "启动"}: setup.xml 尚未成功读取。`);
    return;
  }

  if (setup.dirty && !(await saveSetup())) {
    log(`[Launch Error] ${labels[launchType] || "启动"}: 请先修复配置保存错误。`);
    return;
  }

  try {
    const result = await window.desktopApi?.launchGameExecutable?.(launchType, paths.gameDir);
    if (!result?.ok) {
      log(`[Launch Error] ${labels[launchType] || "Launch"}: ${result?.error || "Launch failed"}`);
      return;
    }
    const route = result.mode === "ipa" ? "IPA.exe --launch" : result.executable;
    log(`[Launch] ${labels[launchType]}: ${route}`);
  } catch (error) {
    log(`[Launch Error] ${labels[launchType] || "启动"}: ${error.message}`);
  }
}

function sleep(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

async function pingBackend({ silent = false } = {}) {
  const startedAt = performance.now();
  try {
    const result = await window.desktopApi?.backendRequest?.("/health");
    backendStatus.value = result?.ok ? "ready" : "error";
    if (!silent) log(`[Backend] ${result?.message || "Python backend is ready."}`);
    if (!silent) {
      log(`[Startup] pingBackend completed in ${formatDurationMs(performance.now() - startedAt)}`);
    }
    return backendStatus.value === "ready";
  } catch (error) {
    backendStatus.value = "error";
    if (!silent) log(`[Backend Error] ${error.message}`);
    if (!silent) {
      log(
        `[Startup] pingBackend failed in ${formatDurationMs(performance.now() - startedAt)}: ${
          error.message
        }`
      );
    }
    return false;
  }
}

function stopBackendRetry() {
  if (!backendRetryTimer) return;
  window.clearInterval(backendRetryTimer);
  backendRetryTimer = 0;
}

function startBackendRetry() {
  if (backendRetryTimer || backendReady.value) return;
  backendRetryTimer = window.setInterval(async () => {
    if (backendReady.value) {
      stopBackendRetry();
      return;
    }
    if (backendRetryInFlight) return;
    backendRetryInFlight = true;
    try {
      if (await pingBackend({ silent: true })) {
        stopBackendRetry();
        await loadAppSettings({ loadBackendData: true });
      }
    } finally {
      backendRetryInFlight = false;
    }
  }, 1500);
}

async function waitForBackendReady(timeoutMs = 20000) {
  if (backendReady.value) return true;
  const startedAt = performance.now();
  let attempts = 0;
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    attempts += 1;
    if (await pingBackend({ silent: true })) {
      log(
        `[Startup] waitForBackendReady completed in ${formatDurationMs(
          performance.now() - startedAt
        )} (attempts=${attempts})`
      );
      return true;
    }
    await sleep(350);
  }
  log(
    `[Startup] waitForBackendReady timed out in ${formatDurationMs(
      performance.now() - startedAt
    )} (attempts=${attempts})`
  );
  return false;
}

function toPlainTaskPayload(value) {
  if (Array.isArray(value)) return value.map((item) => toPlainTaskPayload(item));
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [key, toPlainTaskPayload(item)])
    );
  }
  return value;
}

function buildPayload(overrides = {}) {
  return toPlainTaskPayload({
    game_dir: String(paths.gameDir || ""),
    input_dir: String(paths.inputDir || ""),
    output_dir: String(paths.outputDir || ""),
    card_paths: Array.from(selectedCards.value),
    zipmod_extract_mode: String(extractMode.value || "copy"),
    ...overrides
  });
}

const DATABASE_WORKER_TASK_TYPES = new Set([
  "build_mod_database",
  "build_card_database",
  "index_single_zipmod",
  "download_card_missing_mods",
  "import_external_zipmods",
  "organize_all_zipmods_by_author"
]);

function buildTaskPayload(type, overrides = {}) {
  const taskOverrides = DATABASE_WORKER_TASK_TYPES.has(type)
    ? { worker_count: managerSettings.databaseWorkerCount, ...overrides }
    : overrides;
  return buildPayload(taskOverrides);
}

function applyTask(task, submissionOrder = null) {
  rememberTask(task, submissionOrder);
  if (task.task_type === "download_card_missing_mods") {
    const guids = cardDependencyRemote.taskGuids[task.id] || [];
    if (guids.length) {
      const taskProgress = Math.max(0, Math.min(100, Number(task.progress || 0)));
      const taskPhaseProgress = Math.max(0, Math.min(100, Number(task.phase_progress || 0)));
      const nextProgress = { ...cardDependencyRemote.progress };
      const nextStatuses = { ...cardDependencyRemote.statuses };
      for (const guid of guids) {
        nextProgress[guid] = taskProgress;
        nextStatuses[guid] = task.status;
      }
      cardDependencyRemote.progress = nextProgress;
      cardDependencyRemote.statuses = nextStatuses;
      cardDependencyRemote.phase = String(task.phase || "");
      cardDependencyRemote.phaseProgress = taskPhaseProgress;
      cardDependencyRemote.downloadSpeedBps = Math.max(0, Number(task.download_speed_bps || 0));
      cardDependencyRemote.downloadedBytes = Math.max(0, Number(task.downloaded_bytes || 0));
      cardDependencyRemote.totalBytes = Math.max(0, Number(task.total_bytes || 0));
      cardDependencyRemote.currentFile = String(task.current_file || "");
      if (cardDependencyRemote.allTaskId === task.id) {
        cardDependencyRemote.allProgress = taskProgress;
        cardDependencyRemote.allStatus = task.status;
        cardDependencyRemote.allPhase = String(task.phase || "");
        cardDependencyRemote.allPhaseProgress = taskPhaseProgress;
        cardDependencyRemote.allDownloadSpeedBps = Math.max(0, Number(task.download_speed_bps || 0));
        cardDependencyRemote.allDownloadedBytes = Math.max(0, Number(task.downloaded_bytes || 0));
        cardDependencyRemote.allTotalBytes = Math.max(0, Number(task.total_bytes || 0));
        cardDependencyRemote.allCurrentFile = String(task.current_file || "");
      }
    }
  }
  const isDatabaseTask = task.task_type === "build_mod_database";
  const isCardDatabaseTask = task.task_type === "build_card_database";
  if (isDatabaseTask || isCardDatabaseTask) {
    taskName.value = isDatabaseTask ? "重建数据库" : "扫描人物卡";
    progress.value = Number(task.progress || 0);
    taskId.value = task.id || taskId.value;
  }

  for (const message of task.messages || []) {
    const formatted = `[Task] ${message}`;
    if (!seenTaskMessages.value.has(formatted)) {
      seenTaskMessages.value.add(formatted);
      log(formatted);
    }
  }

  if (task.error && task.status === "failed") log(`[Task Error] ${task.error}`);
  if (task.task_type === "check_game_dir") {
    if (typeof task.data?.is_valid === "boolean") {
      gameDirStatus.value = task.data.is_valid ? "目录有效" : "目录无效";
      taskHint.value = task.data.is_valid ? "目录有效" : "请选择有效 HS2 目录";
    } else if (["completed", "failed", "cancelled"].includes(task.status)) {
      gameDirStatus.value = "检查失败";
      taskHint.value = task.error || "目录校验任务未返回结果";
    }
  }
  if (task.task_type === "extract_mods") {
    stats.zipmods = task.data?.matched_mod_count ?? stats.zipmods;
    stats.missingAbdata = task.data?.missing_abdata?.length ?? stats.missingAbdata;
    paths.outputDir = task.data?.output_dir || paths.outputDir;
  }
  if (isDatabaseTask) {
    stats.zipmods = task.data?.stats?.primary_zipmods ?? stats.zipmods;
    stats.modItems = task.data?.stats?.mod_items ?? stats.modItems;
    stats.builtinItems = task.data?.stats?.builtin_items ?? stats.builtinItems;
    if (task.status === "completed") {
      taskHint.value = "数据库已创建";
    } else if (task.status === "failed") {
      taskHint.value = "数据库创建失败";
    } else {
      taskHint.value = databaseTaskHint(task);
    }
    if (task.status === "completed") {
      modDatabase.checked = false;
      itemDatabase.checked = false;
      if (libraryMode.value === "items") {
        void refreshModDatabaseList();
      } else {
        ensureModDatabaseLoaded({ force: true });
      }
      refreshCharacterCardsAfterDatabaseBuild();
    }
  }
  if (isCardDatabaseTask) {
    if (task.status === "completed") {
      taskHint.value = "人物卡数据已更新";
    } else if (task.status === "failed") {
      taskHint.value = "人物卡数据扫描失败";
    }
  }
  if (
    [
      "bulk_export_zipmods",
      "bulk_organize_zipmods",
      "organize_all_zipmods_by_author",
      "bulk_repair_zipmods_unity3d",
      "bulk_cleanup_duplicate_zipmods",
      "import_external_zipmods",
      "bulk_delete_zipmods",
      "bulk_delete_character_cards",
      "bulk_update_zipmod_authors",
      "bulk_apply_item_thumbnail",
      "bulk_delete_error_items"
    ].includes(task.task_type)
  ) {
    const failureCount = Number(task.data?.failure_count || 0);
    if (failureCount > 0 && task.status === "completed") {
      const scope = task.task_type === "bulk_delete_character_cards" ? "Cards" : "Mods";
      (task.data?.failures || []).slice(0, 5).forEach((failure) => log(`[${scope} Error] #${failure.id}: ${failure.error}`));
    }
    if (task.task_type === "bulk_cleanup_duplicate_zipmods" && task.status === "completed") {
      (task.data?.skipped || []).slice(0, 5).forEach((item) => {
        log(`[Mods] 跳过 #${item.id}: ${item.reason || "智能分析建议保留人工处理"}`);
      });
    }
    if (task.task_type === "import_external_zipmods" && task.status === "completed") {
      importResultPrompt.task = task;
      importResultPrompt.open = true;
      (task.data?.skipped || []).slice(0, 5).forEach((item) => {
        log(`[Import] 跳过 ${item.guid || item.id || ""}: ${item.reason || "需要人工确认"}`);
      });
    }
    if (task.task_type === "organize_all_zipmods_by_author" && task.status === "completed") {
      modDatabase.checked = false;
      itemDatabase.checked = false;
      void refreshModDatabaseList();
    }
  }
}

async function openGameDirectory(relativePath) {
  if (!paths.gameDir) return;
  const suffix = relativePath === "." ? "" : `\\${relativePath}`;
  const directoryPath = `${paths.gameDir}${suffix}`;
  const result = await window.desktopApi?.openDirectory?.(directoryPath);
  if (!result?.ok) log(`[Directory Error] ${result?.error || "无法打开目录"}: ${directoryPath}`);
}

async function openRepository() {
  const result = await window.desktopApi?.openRepository?.();
  if (!result?.ok) log(`[External Link Error] ${result?.error || "无法打开 GitHub 仓库"}`);
}

function openDirectoryShortcutPrompt() {
  directoryShortcutPrompt.open = true;
  directoryShortcutPrompt.name = "";
  directoryShortcutPrompt.path = "";
  directoryShortcutPrompt.error = "";
  directoryShortcutPrompt.saving = false;
  directoryShortcutPrompt.editingIndex = -1;
}

function openDirectoryShortcutEditor(index) {
  if (directoryShortcutPrompt.saving) return;
  const shortcut = directoryShortcuts.value[index];
  if (!shortcut) return;
  directoryShortcutPrompt.open = true;
  directoryShortcutPrompt.name = String(shortcut.name || "");
  directoryShortcutPrompt.path = String(shortcut.path || "");
  directoryShortcutPrompt.error = "";
  directoryShortcutPrompt.saving = false;
  directoryShortcutPrompt.editingIndex = index;
}

async function selectDirectoryShortcutPath() {
  const selected = await window.desktopApi?.selectDirectory?.("选择目录");
  if (selected) directoryShortcutPrompt.path = selected;
}

function closeDirectoryShortcutPrompt() {
  if (directoryShortcutPrompt.saving) return;
  directoryShortcutPrompt.open = false;
  directoryShortcutPrompt.error = "";
  directoryShortcutPrompt.editingIndex = -1;
}

async function saveDirectoryShortcut() {
  if (directoryShortcutPrompt.saving) return;
  const name = String(directoryShortcutPrompt.name || "").trim();
  const selectedPath = String(directoryShortcutPrompt.path || "").trim();
  if (!name || !selectedPath) {
    directoryShortcutPrompt.error = "请填写按钮名并选择目录";
    return;
  }
  const editingIndex = Number.isInteger(directoryShortcutPrompt.editingIndex)
    ? directoryShortcutPrompt.editingIndex
    : -1;
  if (editingIndex < 0 && directoryShortcuts.value.length >= 24) {
    directoryShortcutPrompt.error = "最多添加 24 个快捷目录";
    return;
  }
  if (editingIndex >= directoryShortcuts.value.length) {
    directoryShortcutPrompt.error = "快捷目录不存在或已被移除";
    return;
  }

  const previousShortcuts = serializeDirectoryShortcuts();
  const nextShortcuts = [...previousShortcuts];
  if (editingIndex >= 0) nextShortcuts[editingIndex] = { name, path: selectedPath };
  else nextShortcuts.push({ name, path: selectedPath });
  directoryShortcuts.value = nextShortcuts;
  directoryShortcutPrompt.saving = true;
  directoryShortcutPrompt.error = "";
  try {
    const result = await saveAppSettings();
    if (!result?.ok) {
      directoryShortcuts.value = previousShortcuts;
      directoryShortcutPrompt.error = result?.error || "保存失败";
      return;
    }
    directoryShortcuts.value = Array.isArray(result.settings?.directoryShortcuts)
      ? result.settings.directoryShortcuts
      : nextShortcuts;
    directoryShortcutPrompt.open = false;
    directoryShortcutPrompt.error = "";
    directoryShortcutPrompt.editingIndex = -1;
  } catch (error) {
    directoryShortcuts.value = previousShortcuts;
    directoryShortcutPrompt.error = error?.message || "保存失败";
  } finally {
    directoryShortcutPrompt.saving = false;
  }
}

async function deleteDirectoryShortcut() {
  if (directoryShortcutPrompt.saving) return;
  const index = Number.isInteger(directoryShortcutPrompt.editingIndex)
    ? directoryShortcutPrompt.editingIndex
    : -1;
  const shortcut = index >= 0 ? directoryShortcuts.value[index] : null;
  if (!shortcut) {
    closeDirectoryShortcutPrompt();
    return;
  }
  const previousShortcuts = serializeDirectoryShortcuts();
  const nextShortcuts = previousShortcuts.filter((_item, itemIndex) => itemIndex !== index);
  directoryShortcuts.value = nextShortcuts;
  directoryShortcutPrompt.saving = true;
  directoryShortcutPrompt.error = "";
  try {
    const result = await saveAppSettings();
    if (!result?.ok) {
      directoryShortcuts.value = previousShortcuts;
      directoryShortcutPrompt.error = result?.error || "删除失败";
      return;
    }
    directoryShortcuts.value = Array.isArray(result.settings?.directoryShortcuts)
      ? result.settings.directoryShortcuts
      : nextShortcuts;
    directoryShortcutPrompt.open = false;
    directoryShortcutPrompt.error = "";
    directoryShortcutPrompt.editingIndex = -1;
  } catch (error) {
    directoryShortcuts.value = previousShortcuts;
    directoryShortcutPrompt.error = error?.message || "删除失败";
  } finally {
    directoryShortcutPrompt.saving = false;
  }
}

async function openDirectoryShortcut(directoryPath) {
  const targetPath = String(directoryPath || "").trim();
  if (!targetPath) return;
  const result = await window.desktopApi?.openDirectory?.(targetPath);
  if (!result?.ok) log(`[Directory Error] ${result?.error || "无法打开目录"}: ${targetPath}`);
}

async function openClothesDirectory(relativePath = "") {
  const suffix = relativePath ? `\\${relativePath}` : "";
  return openGameDirectory(`UserData\\coordinate${suffix}`);
}

async function openSceneDirectory(relativePath = "") {
  const suffix = relativePath ? `\\${relativePath}` : "";
  return openGameDirectory(`UserData\\studio\\scene${suffix}`);
}

async function pollTask(id, options = {}) {
  const {
    manageBusy = true,
    onDone = null,
    timeoutMs = 0,
    initialTask = null
  } = options;
  let finalTask = initialTask;
  const deadline = timeoutMs > 0 ? Date.now() + timeoutMs : 0;

  function finishPollingWithFailure(reason) {
    const failedTask = {
      ...(finalTask || {}),
      id,
      task_type: finalTask?.task_type || "unknown",
      status: "failed",
      error: reason,
      messages: [...(finalTask?.messages || []), `[Error] ${reason}`],
      data: finalTask?.data && typeof finalTask.data === "object" ? finalTask.data : {}
    };
    log(`[Task Error] ${reason}`);
    applyTask(failedTask);
    finalTask = failedTask;
  }

  try {
    for (;;) {
      if (deadline && Date.now() >= deadline) {
        finishPollingWithFailure(`任务 ${finalTask?.task_type || id} 检查超时，未返回最终结果`);
        break;
      }
      let result;
      try {
        result = await window.desktopApi.backendRequest(`/tasks/${id}`);
      } catch (error) {
        finishPollingWithFailure(`任务轮询失败：${error.message}`);
        break;
      }
      if (!result?.ok || !result.task) {
        finishPollingWithFailure(result?.error || "无法读取任务最终结果");
        break;
      }
      applyTask(result.task);
      finalTask = result.task;
      if (["completed", "failed", "cancelled"].includes(result.task.status)) break;
      const waitMs = deadline
        ? Math.min(350, Math.max(0, deadline - Date.now()))
        : 350;
      await new Promise((resolve) => window.setTimeout(resolve, waitMs));
    }
    if (finalTask?.status === "completed") await loadAchievements({ notify: true });
    if (typeof onDone === "function" && finalTask) {
      await onDone(finalTask);
    }
    return finalTask;
  } finally {
    if (manageBusy) {
      isBusy.value = false;
      activeAction.value = "";
    }
  }
}

async function buildModDatabase() {
  if (gameDirStatus.value !== "目录有效") {
    taskHint.value = "请选择有效 HS2 目录";
    log("[Task Error] 请先选择有效 HS2 目录");
    return;
  }
  taskHint.value = "准备重建数据库";
  await submitTask("build_mod_database", { mode: "incremental" });
}

async function importExternalZipmods() {
  if (gameDirStatus.value !== "目录有效") {
    taskHint.value = "请选择有效 HS2 目录";
    log("[Task Error] 请先选择有效 HS2 目录");
    return;
  }
  const sourceDir = await window.desktopApi?.selectDirectory?.("选择外部模组文件夹");
  if (!sourceDir) return;
  taskHint.value = "正在导入外部 zipmod / zip";
  await submitTask("import_external_zipmods", { source_dir: sourceDir });
}

function openOrganizeAllPrompt() {
  if (gameDirStatus.value !== "目录有效") {
    taskHint.value = "请选择有效 HS2 目录";
    log("[Task Error] 请先选择有效 HS2 目录");
    return;
  }
  organizeAllPrompt.error = "";
  organizeAllPrompt.open = true;
}

async function submitOrganizeAllZipmods() {
  if (isBusy.value) return;
  organizeAllPrompt.open = false;
  taskHint.value = "正在按作者整理全部模组";
  await submitTask("organize_all_zipmods_by_author");
}

async function submitTask(type, overrides = {}) {
  if (!(await waitForBackendReady())) {
    log(`[Task Error] 后端启动超时，无法执行 ${type}`);
    return null;
  }
  isBusy.value = true;
  activeAction.value = type;
  if (type === "build_mod_database") {
    taskName.value = "重建数据库";
    progress.value = 1;
    taskId.value = "queued";
    taskHint.value = "等待后端开始处理";
  }
  const submissionOrder = reserveTaskSubmissionOrder();
  log(`[UI] ${type} submitted`);
  try {
    const result = await window.desktopApi.backendRequest("/tasks", {
      method: "POST",
      body: { task_type: type, payload: buildTaskPayload(type, overrides) }
    });
    if (!result?.ok) {
      log(`[Task Error] ${result?.error || "unknown error"}`);
      isBusy.value = false;
      activeAction.value = "";
      return null;
    }
    if (!result.task?.id) {
      log("[Task Error] 后端未返回有效的目录校验任务");
      isBusy.value = false;
      activeAction.value = "";
      return null;
    }
    if (type === "check_game_dir") {
      log(`[Game Dir Check] task: ${result.task.id}`);
    }
    applyTask(result.task, submissionOrder);
    return await pollTask(result.task.id, {
      initialTask: result.task,
      timeoutMs: type === "check_game_dir" ? 10000 : 0
    });
  } catch (error) {
    log(`[Task Error] ${error.message}`);
    isBusy.value = false;
    activeAction.value = "";
    return null;
  }
}

async function submitTaskInBackground(type, overrides = {}, onDone = null, onStarted = null) {
  if (!(await waitForBackendReady())) {
    throw new Error(`后端未就绪，无法提交任务：${type}`);
  }
  const submissionOrder = reserveTaskSubmissionOrder();
  log(`[UI] ${type} submitted`);
  const result = await window.desktopApi.backendRequest("/tasks", {
    method: "POST",
    body: { task_type: type, payload: buildTaskPayload(type, overrides) }
  });
  if (!result.ok) {
    throw new Error(result.error || "unknown error");
  }
  applyTask(result.task, submissionOrder);
  if (typeof onStarted === "function") onStarted(result.task);
  void pollTask(result.task.id, { manageBusy: false, onDone }).catch((error) => {
    log(`[Task Error] ${error.message}`);
    if (typeof onDone === "function") {
      void onDone({
        ...result.task,
        status: "failed",
        error: error.message
      }).catch((callbackError) => {
        log(`[Task Error] ${callbackError.message}`);
      });
    }
  });
  return result.task;
}

function openCardDependencyExportPrompt() {
  if (selectedCount.value === 0 || isBusy.value) return;
  cardDependencyExportPrompt.targetDir = paths.outputDir || "";
  cardDependencyExportPrompt.mode = extractMode.value || "copy";
  cardDependencyExportPrompt.confirmMove = false;
  cardDependencyExportPrompt.error = "";
  cardDependencyExportPrompt.open = true;
}

async function selectCardDependencyExportDir() {
  const selected = await window.desktopApi?.selectDirectory?.("选择依赖模组导出目录");
  if (!selected) return;
  cardDependencyExportPrompt.targetDir = selected;
  cardDependencyExportPrompt.confirmMove = false;
  cardDependencyExportPrompt.error = "";
}

async function submitCardDependencyExport() {
  if (selectedCount.value === 0 || isBusy.value) return;
  const targetDir = String(cardDependencyExportPrompt.targetDir || "").trim();
  if (!targetDir) {
    cardDependencyExportPrompt.error = "请选择导出目录";
    return;
  }

  const mode = cardDependencyExportPrompt.mode === "move" ? "move" : "copy";
  if (mode === "move" && !cardDependencyExportPrompt.confirmMove) {
    cardDependencyExportPrompt.confirmMove = true;
    cardDependencyExportPrompt.error = "";
    return;
  }

  paths.outputDir = targetDir;
  extractMode.value = mode;
  cardDependencyExportPrompt.confirmMove = false;
  cardDependencyExportPrompt.open = false;
  await saveAppSettings();
  await submitTask("extract_mods", {
    output_dir: targetDir,
    zipmod_extract_mode: mode,
    card_paths: Array.from(selectedCards.value)
  });
}

function enterCardBulkMode() {
  cardBulkMode.value = true;
}

function exitCardBulkMode() {
  cardBulkMode.value = false;
  selectedCards.value = new Set();
}

function openCardDeletePrompt() {
  if (selectedCount.value === 0 || cardDeletePrompt.busy) return;
  cardDeletePrompt.error = "";
  cardDeletePrompt.open = true;
}

function openSelectedCardDeletePrompt() {
  const card = selectedCardDetail.value;
  if (!card?.relativePath || cardSingleDeletePrompt.busy) return;
  cardSingleDeletePrompt.card = {
    name: card.name,
    relativePath: card.relativePath,
    coverUrl: card.coverUrl
  };
  cardSingleDeletePrompt.error = "";
  cardSingleDeletePrompt.open = true;
}

function selectedCardRelativePaths() {
  const selectedPaths = new Set(selectedCards.value);
  return visibleCards.value
    .filter((card) => selectedPaths.has(card.absolutePath))
    .map((card) => card.relativePath)
    .filter(Boolean);
}

function openCardMovePrompt() {
  if (selectedCount.value === 0 || cardMovePrompt.busy) return;
  const sourceGender = selectedCardFolder.value.split("/")[0]?.toLowerCase() || "";
  if (!/^(female|male)$/.test(sourceGender)) return;
  cardMovePrompt.sourceGender = sourceGender;
  const managedPaths = collectManagedFolderPaths(cardTree.value, [], sourceGender);
  const currentPath = new RegExp(`^${sourceGender}(\\/|$)`, "i").test(selectedCardFolder.value)
    ? selectedCardFolder.value
    : "";
  cardMovePrompt.targetPath = currentPath || managedPaths[0] || "";
  cardMovePrompt.expanded = new Set(managedPaths);
  cardMovePrompt.editMode = "";
  cardMovePrompt.nameDraft = "";
  cardMovePrompt.error = "";
  cardMovePrompt.open = true;
}

function closeCardMovePrompt() {
  if (cardMovePrompt.busy || cardMovePrompt.folderBusy) return;
  cardMovePrompt.open = false;
  cardMovePrompt.editMode = "";
  cardMovePrompt.error = "";
}

function toggleCardMoveFolder(folder) {
  if (!folder?.hasChildren) return;
  const next = new Set(cardMovePrompt.expanded);
  if (next.has(folder.relativePath)) next.delete(folder.relativePath);
  else next.add(folder.relativePath);
  cardMovePrompt.expanded = next;
}

function selectCardMoveFolder(folder) {
  cardMovePrompt.targetPath = folder.relativePath;
  cardMovePrompt.editMode = "";
  cardMovePrompt.nameDraft = "";
  cardMovePrompt.error = "";
}

function beginCardMoveFolderEdit(mode) {
  if (!cardMovePrompt.targetPath || cardMovePrompt.folderBusy) return;
  if (mode === "rename" && /^(female|male)$/i.test(cardMovePrompt.targetPath)) {
    cardMovePrompt.error = "female 和 male 根目录不能重命名。";
    return;
  }
  cardMovePrompt.editMode = mode;
  cardMovePrompt.nameDraft = mode === "rename"
    ? cardMovePrompt.targetPath.split("/").pop() || ""
    : "";
  cardMovePrompt.error = "";
}

function replaceFolderPathPrefix(path, oldPrefix, newPrefix) {
  if (path === oldPrefix) return newPrefix;
  return path.startsWith(`${oldPrefix}/`) ? `${newPrefix}${path.slice(oldPrefix.length)}` : path;
}

async function submitCardMoveFolderEdit() {
  const name = String(cardMovePrompt.nameDraft || "").trim();
  if (!name) {
    cardMovePrompt.error = "请输入目录名称。";
    return;
  }
  cardMovePrompt.folderBusy = true;
  cardMovePrompt.error = "";
  try {
    const isRename = cardMovePrompt.editMode === "rename";
    const oldPath = cardMovePrompt.targetPath;
    const result = await window.desktopApi?.backendRequest?.(
      isRename ? "/library/cards/folders/rename" : "/library/cards/folders/create",
      {
        method: "POST",
        body: isRename
          ? { game_dir: paths.gameDir, path: oldPath, name }
          : { game_dir: paths.gameDir, parent_path: oldPath, name }
      }
    );
    if (!result?.ok) throw new Error(result?.error || (isRename ? "目录重命名失败" : "新建目录失败"));

    const nextPath = String(result.relative_path || oldPath);
    if (isRename && (selectedCardFolder.value === oldPath || selectedCardFolder.value.startsWith(`${oldPath}/`))) {
      selectedCardFolder.value = replaceFolderPathPrefix(selectedCardFolder.value, oldPath, nextPath);
      cardMovePrompt.open = false;
      await loadCardTree();
      return;
    }
    await refreshCardTreeStructure();
    cardMovePrompt.expanded = new Set(collectManagedFolderPaths(cardTree.value, [], cardMovePrompt.sourceGender));
    cardMovePrompt.targetPath = nextPath;
    cardMovePrompt.editMode = "";
    cardMovePrompt.nameDraft = "";
  } catch (error) {
    cardMovePrompt.error = error.message;
  } finally {
    cardMovePrompt.folderBusy = false;
  }
}

async function submitBulkMoveCharacterCards() {
  if (selectedCount.value === 0 || cardMovePrompt.busy) return;
  const cardPaths = selectedCardRelativePaths();
  if (cardPaths.length !== selectedCount.value) {
    cardMovePrompt.error = "选中的人物卡已发生变化，请退出多选后重试。";
    return;
  }
  if (!cardMovePrompt.targetPath) {
    cardMovePrompt.error = "请选择目标目录。";
    return;
  }
  if (cardMovePrompt.targetPath === selectedCardFolder.value) {
    cardMovePrompt.error = "请选择不同于当前目录的目标目录。";
    return;
  }

  cardMovePrompt.busy = true;
  cardMovePrompt.error = "";
  try {
    await submitTaskInBackground(
      "bulk_move_character_cards",
      { card_paths: cardPaths, target_directory: cardMovePrompt.targetPath },
      async (task) => {
        cardMovePrompt.busy = false;
        if (task.status === "completed") {
          cardMovePrompt.open = false;
          await loadCardTree();
        } else {
          cardMovePrompt.open = true;
          cardMovePrompt.error = task.error || "批量移动人物卡失败";
        }
      }
    );
  } catch (error) {
    cardMovePrompt.busy = false;
    cardMovePrompt.error = error.message;
    log(`[Cards Error] ${error.message}`);
  }
}

async function submitBulkDeleteCharacterCards() {
  if (selectedCount.value === 0 || cardDeletePrompt.busy) return;
  const cardPaths = selectedCardRelativePaths();
  if (cardPaths.length !== selectedCount.value) {
    cardDeletePrompt.error = "选中的人物卡已发生变化，请退出多选后重试。";
    return;
  }

  cardDeletePrompt.busy = true;
  cardDeletePrompt.error = "";
  try {
    await submitTaskInBackground("bulk_delete_character_cards", { card_paths: cardPaths }, async (task) => {
      cardDeletePrompt.busy = false;
      if (task.status === "completed") {
        cardDeletePrompt.open = false;
        await loadCardTree();
      } else {
        cardDeletePrompt.open = true;
        cardDeletePrompt.error = task.error || "批量删除人物卡失败";
      }
    });
    cardDeletePrompt.open = false;
  } catch (error) {
    cardDeletePrompt.busy = false;
    cardDeletePrompt.error = error.message;
    log(`[Cards Error] ${error.message}`);
  }
}

function toggleCardSelection(id) {
  if (!id) return;
  const next = new Set(selectedCards.value);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  selectedCards.value = next;
}

function handleCardClick(card) {
  if (!card) return;
  cardLoadPrompt.open = false;
  cardLoadPrompt.error = "";
  cardLoadNotice.type = "";
  cardLoadNotice.message = "";
  naviActionNotice.type = "";
  naviActionNotice.message = "";
  coordinateExportNotice.type = "";
  coordinateExportNotice.message = "";
  coordinateExportNotice.path = "";
  portablePackageNotice.type = "";
  portablePackageNotice.message = "";
  portablePackageNotice.path = "";
  cardCoverNotice.type = "";
  cardCoverNotice.message = "";
  cardFavoriteNotice.type = "";
  cardFavoriteNotice.message = "";
  cardRatingNotice.type = "";
  cardRatingNotice.message = "";
  cardTagNotice.type = "";
  cardTagNotice.message = "";
  cardDependencyRemote.loading = false;
  cardDependencyRemote.error = "";
  cardDependencyRemote.byGuid = {};
  cardDependencyRemote.busyGuids = {};
  cardDependencyRemote.notices = {};
  selectedCardDetailPath.value = card.absolutePath;
  loadSelectedCardProfile(card);
  if (cardBulkMode.value) {
    toggleCardSelection(card.absolutePath);
  } else {
    characterSideMode.value = "detail";
  }
}

async function replaceSelectedCardCover() {
  const card = selectedCardDetail.value;
  if (!card?.relativePath || replacingCardCover.value) return;
  const selected = await window.desktopApi?.selectImageForCrop?.("选择人物卡封面图片");
  if (!selected) return;
  if (!selected.ok) {
    cardCoverNotice.type = "error";
    cardCoverNotice.message = selected.error || "封面图片读取失败";
    return;
  }

  cardCoverNotice.type = "";
  cardCoverNotice.message = "";
  cardCoverCrop.imagePath = selected.path;
  cardCoverCrop.imageData = selected.dataUrl;
  cardCoverCrop.imageName = selected.name;
  cardCoverCrop.open = true;
}

function clearCardCoverCrop() {
  cardCoverCrop.open = false;
  cardCoverCrop.imagePath = "";
  cardCoverCrop.imageData = "";
  cardCoverCrop.imageName = "";
}

function cancelCardCoverCrop() {
  if (!replacingCardCover.value) clearCardCoverCrop();
}

async function confirmCardCoverCrop(crop) {
  const card = selectedCardDetail.value;
  if (!card?.relativePath || !cardCoverCrop.imagePath || replacingCardCover.value) return;

  replacingCardCover.value = true;
  cardCoverNotice.type = "";
  cardCoverNotice.message = "";
  try {
    const result = await window.desktopApi?.backendRequest?.("/library/cards/replace-cover", {
      method: "POST",
      body: {
        game_dir: paths.gameDir,
        path: card.relativePath,
        image_path: cardCoverCrop.imagePath,
        crop
      }
    });
    if (!result?.ok) throw new Error(result?.error || "人物卡封面替换失败");
    const cacheBuster = `cover=${encodeURIComponent(result.image_version || Date.now())}`;
    card.thumbnailUrl = `${card.thumbnailUrl}${card.thumbnailUrl.includes("?") ? "&" : "?"}${cacheBuster}`;
    card.coverUrl = `${card.coverUrl}${card.coverUrl.includes("?") ? "&" : "?"}${cacheBuster}`;
    card.modifiedAt = result.modified_at ? new Date(result.modified_at * 1000).toLocaleDateString() : card.modifiedAt;
    cardCoverNotice.type = result.warning ? "warning" : "success";
    cardCoverNotice.message = result.warning || `封面已按 63:88 裁剪为 ${result.width} × ${result.height}`;
    log(`[Cards] 人物卡封面已替换：${card.relativePath}`);
    if (result.warning) log(`[Cards Warning] ${result.warning}`);
    clearCardCoverCrop();
  } catch (error) {
    cardCoverNotice.type = "error";
    cardCoverNotice.message = error.message;
    log(`[Cards Error] ${error.message}`);
  } finally {
    replacingCardCover.value = false;
  }
}

async function toggleSelectedCardFavorite() {
  const card = selectedCardDetail.value;
  if (!card?.relativePath || favoritingCardPath.value) return;
  const targetFavorite = !card.favorite;
  favoritingCardPath.value = card.absolutePath;
  cardFavoriteNotice.type = "";
  cardFavoriteNotice.message = "";
  try {
    const result = await window.desktopApi?.backendRequest?.("/library/cards/set-favorite", {
      method: "POST",
      body: {
        game_dir: paths.gameDir,
        path: card.relativePath,
        favorite: targetFavorite
      }
    });
    if (!result?.ok) throw new Error(result?.error || "人物卡收藏状态保存失败");
    card.favorite = Boolean(result.favorite);
    card.modifiedAt = result.modified_at ? new Date(result.modified_at * 1000).toLocaleDateString() : card.modifiedAt;
    cardFavoriteNotice.type = result.warning ? "warning" : "success";
    cardFavoriteNotice.message = result.warning || (card.favorite ? "已收藏，状态已写入人物卡" : "已取消收藏");
    log(`[Cards] ${card.favorite ? "已收藏" : "已取消收藏"}：${card.relativePath}`);
    if (result.warning) log(`[Cards Warning] ${result.warning}`);
  } catch (error) {
    cardFavoriteNotice.type = "error";
    cardFavoriteNotice.message = error.message;
    log(`[Cards Error] ${error.message}`);
  } finally {
    favoritingCardPath.value = "";
  }
}

async function setSelectedCardRating(rating) {
  const card = selectedCardDetail.value;
  const targetRating = Number(rating);
  if (
    !card?.relativePath ||
    ratingCardPath.value ||
    !Number.isInteger(targetRating) ||
    targetRating < 1 ||
    targetRating > 5
  ) return;

  ratingCardPath.value = card.absolutePath;
  cardRatingNotice.type = "";
  cardRatingNotice.message = "";
  try {
    const result = await window.desktopApi?.backendRequest?.("/library/cards/set-rating", {
      method: "POST",
      body: {
        game_dir: paths.gameDir,
        path: card.relativePath,
        rating: targetRating
      }
    });
    if (!result?.ok) throw new Error(result?.error || "人物卡评分保存失败");
    card.rating = Math.min(5, Math.max(0, Number(result.rating) || 0));
    card.modifiedAt = result.modified_at ? new Date(result.modified_at * 1000).toLocaleDateString() : card.modifiedAt;
    cardRatingNotice.type = result.warning ? "warning" : "success";
    cardRatingNotice.message = result.warning || `已评为 ${card.rating} 星，评分已写入人物卡`;
    log(`[Cards] 已评为 ${card.rating} 星：${card.relativePath}`);
    if (result.warning) log(`[Cards Warning] ${result.warning}`);
  } catch (error) {
    cardRatingNotice.type = "error";
    cardRatingNotice.message = error.message;
    log(`[Cards Error] ${error.message}`);
  } finally {
    ratingCardPath.value = "";
  }
}

function uniqueCardTags(values) {
  const tags = new Map();
  for (const value of values || []) {
    const tag = String(value || "").trim();
    if (tag) tags.set(tag.toLocaleLowerCase(), tag);
  }
  return [...tags.values()];
}

async function openCardTagPrompt() {
  const card = selectedCardDetail.value;
  if (!card?.relativePath || cardTagPrompt.busy) return;
  cardTagPrompt.current = uniqueCardTags(card.tags);
  cardTagPrompt.selected = [...cardTagPrompt.current];
  cardTagPrompt.available = uniqueCardTags([...cardTagOptions.value, ...cardTagPrompt.current]);
  cardTagPrompt.draft = "";
  cardTagPrompt.error = "";
  cardTagPrompt.open = true;
  await loadCardTagCatalogForPrompt(cardTagPrompt);
}

async function loadCardTagCatalogForPrompt(prompt) {
  prompt.loading = false;
  if (cardTagCatalog.loaded && cardTagCatalog.gameDir === paths.gameDir) {
    prompt.available = uniqueCardTags([
      ...cardTagCatalog.tags,
      ...prompt.available
    ]).sort((left, right) => left.localeCompare(right, "zh-CN"));
    return;
  }
  prompt.loading = true;
  try {
    const result = await window.desktopApi?.backendRequest?.(
      `/library/cards/tags?game_dir=${encodeQuery(paths.gameDir)}`
    );
    if (!result?.ok) throw new Error(result?.error || "人物卡库标签读取失败");
    prompt.available = uniqueCardTags([
      ...(result.tags || []),
      ...prompt.available
    ]).sort((left, right) => left.localeCompare(right, "zh-CN"));
    cardTagCatalog.gameDir = paths.gameDir;
    cardTagCatalog.loaded = true;
    cardTagCatalog.tags = [...prompt.available];
  } catch (error) {
    prompt.error = error.message;
    log(`[Cards Error] ${error.message}`);
  } finally {
    prompt.loading = false;
  }
}

async function openCardTagFilter() {
  cardTagFilter.open = true;
  cardTagFilter.error = "";
  cardTagFilter.available = uniqueCardTags(cardTagOptions.value);
  if (!cardTagFilter.loading) await loadCardTagCatalogForPrompt(cardTagFilter);
}

function updateCardTagFilterSearch(value) {
  cardTagFilter.search = String(value || "");
  cardTagFilter.open = true;
}

function closeCardTagFilter() {
  cardTagFilter.open = false;
}

function closeCardTagFilterSoon() {
  window.setTimeout(closeCardTagFilter, 120);
}

async function loadLibraryCardsByTag(tag) {
  const selectedTag = String(tag || "").trim();
  const requestId = ++cardTagLibraryRequestId;
  cardTagFilter.libraryTag = selectedTag;
  cardTagFilter.libraryCards = [];
  cardTagFilter.resultsError = "";
  if (!selectedTag || !backendReady.value || !paths.gameDir) {
    cardTagFilter.resultsLoading = false;
    return;
  }

  cardTagFilter.resultsLoading = true;
  try {
    const result = await window.desktopApi?.backendRequest?.(
      `/library/cards?game_dir=${encodeQuery(paths.gameDir)}&scope=library&tag=${encodeQuery(selectedTag)}`
    );
    if (requestId !== cardTagLibraryRequestId) return;
    if (!result?.ok) throw new Error(result?.error || "全库人物卡读取失败");
    cardTagFilter.libraryCards = mapCharacterCardRows(result.cards);
  } catch (error) {
    if (requestId !== cardTagLibraryRequestId) return;
    cardTagFilter.resultsError = error.message;
    log(`[Cards Error] ${error.message}`);
  } finally {
    if (requestId === cardTagLibraryRequestId) cardTagFilter.resultsLoading = false;
  }
}

function setCardTagScope(scope) {
  const normalizedScope = scope === "library" ? "library" : "directory";
  if (cardTagFilter.scope === normalizedScope) return;
  cardTagFilter.scope = normalizedScope;
  setCardDependencyFilter(cardDependencyFilter.value);
}

function selectCardTagFilter(tag) {
  const selectedTag = String(tag || "").trim();
  if (!selectedTag) return;
  cardTagFilter.search = selectedTag;
  setCardDependencyFilter(`tag:${selectedTag}`);
}

function applyFirstCardTagFilterSuggestion() {
  const firstTag = cardTagFilterSuggestions.value[0];
  if (firstTag) selectCardTagFilter(firstTag);
}

function clearCardTagFilter() {
  cardTagFilter.search = "";
  cardTagFilter.error = "";
  cardTagFilter.open = true;
  if (cardDependencyFilter.value.startsWith("tag:")) setCardDependencyFilter("all");
}

function toggleTagPromptValue(prompt, tag) {
  if (prompt.busy) return;
  const key = String(tag).toLocaleLowerCase();
  const index = prompt.selected.findIndex(
    (item) => String(item).toLocaleLowerCase() === key
  );
  if (index >= 0) {
    prompt.selected.splice(index, 1);
  } else if (prompt.selected.length >= 12) {
    prompt.error = "一次最多选择 12 个标签。";
    return;
  } else {
    prompt.selected.push(tag);
  }
  prompt.error = "";
}

function toggleCardTagPromptTag(tag) {
  toggleTagPromptValue(cardTagPrompt, tag);
}

function addTagPromptDraft(prompt) {
  const tag = String(prompt.draft || "").trim();
  if (!tag) {
    prompt.error = "请输入新标签名称。";
    return;
  }
  if (tag.length > 24) {
    prompt.error = "单个标签不能超过 24 个字符。";
    return;
  }
  const existing = prompt.available.find(
    (item) => String(item).toLocaleLowerCase() === tag.toLocaleLowerCase()
  );
  const value = existing || tag;
  if (!existing) prompt.available.push(value);
  if (!prompt.selected.some((item) => String(item).toLocaleLowerCase() === value.toLocaleLowerCase())) {
    if (prompt.selected.length >= 12) {
      prompt.error = "一次最多选择 12 个标签。";
      return;
    }
    prompt.selected.push(value);
  }
  prompt.available.sort((left, right) => left.localeCompare(right, "zh-CN"));
  prompt.draft = "";
  prompt.error = "";
}

function addCardTagDraft() {
  addTagPromptDraft(cardTagPrompt);
}

async function openBulkCardTagPrompt() {
  if (selectedCount.value === 0 || bulkCardTagPrompt.busy) return;
  bulkCardTagPrompt.selected = [];
  bulkCardTagPrompt.available = uniqueCardTags(cardTagOptions.value);
  bulkCardTagPrompt.draft = "";
  bulkCardTagPrompt.error = "";
  bulkCardTagPrompt.open = true;
  await loadCardTagCatalogForPrompt(bulkCardTagPrompt);
}

function toggleBulkCardTagPromptTag(tag) {
  toggleTagPromptValue(bulkCardTagPrompt, tag);
}

function addBulkCardTagDraft() {
  addTagPromptDraft(bulkCardTagPrompt);
}

async function submitBulkAddCharacterCardTags() {
  if (selectedCount.value === 0 || bulkCardTagPrompt.busy) return;
  const cardPaths = selectedCardRelativePaths();
  if (cardPaths.length !== selectedCount.value) {
    bulkCardTagPrompt.error = "选中的人物卡已发生变化，请退出多选后重试。";
    return;
  }
  const tags = uniqueCardTags(bulkCardTagPrompt.selected);
  if (!tags.length) {
    bulkCardTagPrompt.error = "请至少选择一个要添加的标签。";
    return;
  }

  bulkCardTagPrompt.busy = true;
  bulkCardTagPrompt.error = "";
  try {
    await submitTaskInBackground(
      "bulk_add_character_card_tags",
      { card_paths: cardPaths, tags },
      async (task) => {
        bulkCardTagPrompt.busy = false;
        if (task.status === "completed") {
          const updatedByPath = new Map(
            (task.data?.updated || []).map((item) => [String(item.relative_path || ""), item])
          );
          for (const card of [...cards.value, ...cardTagFilter.libraryCards]) {
            const updated = updatedByPath.get(card.relativePath);
            if (!updated) continue;
            card.tags = Array.isArray(updated.tags) ? updated.tags.map((tag) => String(tag)) : card.tags;
            card.modifiedAt = updated.modified_at
              ? new Date(updated.modified_at * 1000).toLocaleDateString()
              : card.modifiedAt;
          }
          if (cardTagCatalog.loaded && cardTagCatalog.gameDir === paths.gameDir) {
            cardTagCatalog.tags = uniqueCardTags([...cardTagCatalog.tags, ...tags])
              .sort((left, right) => left.localeCompare(right, "zh-CN"));
          }
          const failureCount = Number(task.data?.failure_count || 0);
          bulkCardTagPrompt.open = failureCount > 0;
          bulkCardTagPrompt.error = failureCount > 0
            ? `已完成 ${task.data?.updated_count || 0} 张，${failureCount} 张添加失败；可查看运行日志。`
            : "";
          log(`[Cards] ${task.data?.message || "批量人物卡标签添加完成"}`);
        } else {
          bulkCardTagPrompt.open = true;
          bulkCardTagPrompt.error = task.error || "批量添加人物卡标签失败";
        }
      }
    );
    bulkCardTagPrompt.open = false;
  } catch (error) {
    bulkCardTagPrompt.busy = false;
    bulkCardTagPrompt.open = true;
    bulkCardTagPrompt.error = error.message;
    log(`[Cards Error] ${error.message}`);
  }
}

async function saveSelectedCardTags() {
  const card = selectedCardDetail.value;
  if (!card?.relativePath || cardTagPrompt.busy) return;
  cardTagPrompt.busy = true;
  cardTagPrompt.error = "";
  try {
    const result = await window.desktopApi?.backendRequest?.("/library/cards/set-tags", {
      method: "POST",
      body: {
        game_dir: paths.gameDir,
        path: card.relativePath,
        tags: [...cardTagPrompt.selected]
      }
    });
    if (!result?.ok) throw new Error(result?.error || "人物卡标签保存失败");
    card.tags = Array.isArray(result.tags) ? result.tags.map((tag) => String(tag)) : [];
    if (cardTagCatalog.loaded && cardTagCatalog.gameDir === paths.gameDir) {
      cardTagCatalog.tags = uniqueCardTags([...cardTagCatalog.tags, ...card.tags])
        .sort((left, right) => left.localeCompare(right, "zh-CN"));
    }
    card.modifiedAt = result.modified_at ? new Date(result.modified_at * 1000).toLocaleDateString() : card.modifiedAt;
    cardTagNotice.type = result.warning ? "warning" : "success";
    cardTagNotice.message = result.warning || (card.tags.length ? "人物卡标签已保存" : "已清空人物卡标签");
    cardTagPrompt.open = false;
    log(`[Cards] 人物卡标签已保存：${card.relativePath}`);
    if (result.warning) log(`[Cards Warning] ${result.warning}`);
  } catch (error) {
    cardTagPrompt.error = error.message;
    log(`[Cards Error] ${error.message}`);
  } finally {
    cardTagPrompt.busy = false;
  }
}

async function loadSelectedCardProfile(card = selectedCardDetail.value) {
  if (!card?.relativePath || !backendReady.value || !paths.gameDir) return;
  selectedCardProfileLoading.value = true;
  selectedCardProfileError.value = "";
  selectedCardProfile.value = null;
  selectedCardDependencies.value = [];
  cardProfileEditor.editing = false;
  cardProfileEditor.error = "";
  cardProfileEditor.message = "";
  const targetPath = card.absolutePath;

  try {
    const result = await window.desktopApi?.backendRequest?.(
      `/library/cards/detail?game_dir=${encodeQuery(paths.gameDir)}&path=${encodeQuery(card.relativePath)}`
    );
    if (!result?.ok) {
      throw new Error(result?.error || "人物卡详情读取失败");
    }
    if (selectedCardDetailPath.value === targetPath) {
      card.favorite = Boolean(result.card?.favorite);
      card.rating = Math.min(5, Math.max(0, Number(result.card?.rating) || 0));
      card.tags = Array.isArray(result.card?.tags) ? result.card.tags.map((tag) => String(tag)) : [];
      selectedCardProfile.value = result.card?.profile || {};
      selectedCardDependencies.value = (result.card?.dependencies || []).map((dependency) => ({
        ...dependency,
        item: dependency.item
          ? {
              ...dependency.item,
              kind: itemKindLabel(dependency.item.kind),
              thumbnailUrl: backendAssetUrl(dependency.item.thumbnail_url)
            }
          : null
      }));
      card.dependencyCount = selectedCardDependencies.value.length;
      card.missingCount = selectedCardDependencies.value.filter((dependency) => !dependency.matched).length;
      void loadCardDependencyRemoteCandidates(targetPath, selectedCardDependencies.value);
    }
  } catch (error) {
    if (selectedCardDetailPath.value === targetPath) {
      selectedCardProfileError.value = error.message;
    }
    log(`[Cards Error] ${error.message}`);
  } finally {
    if (selectedCardDetailPath.value === targetPath) {
      selectedCardProfileLoading.value = false;
    }
  }
}

function normalizeCardDependencyGuid(dependency) {
  return String(dependency?.mod_id || dependency?.zipmod?.guid || dependency?.item?.zipmod_guid || "")
    .trim()
    .toLocaleLowerCase();
}

function cardDependencyRemoteState(dependency) {
  const guid = normalizeCardDependencyGuid(dependency);
  if (!guid || dependency?.matched) return null;
  const entry = cardDependencyRemote.byGuid[guid];
  if (cardDependencyRemote.loading && !entry) return { status: "loading", label: "检查中" };
  if (entry?.can_download) return { status: "available", label: "安装", candidate: entry.candidates?.[0] };
  if (entry && !entry.can_download) return { status: "unavailable", label: "无法获取", reason: entry.reason };
  return { status: "unavailable", label: "无法获取", reason: "远程索引中没有有效记录" };
}

function cardDependencyRemoteFor(dependency) {
  return cardDependencyRemoteState(dependency);
}

function cardDependencyGuidFromCandidate(candidate) {
  return String(candidate?.guid_norm || candidate?.guid || "").trim().toLocaleLowerCase();
}

function registerCardDependencyDownloadTask(task, guids, { all = false } = {}) {
  const taskId = String(task?.id || "").trim();
  const normalizedGuids = [...new Set((guids || []).map((guid) => String(guid || "").trim().toLocaleLowerCase()).filter(Boolean))];
  if (!taskId || !normalizedGuids.length) return;
  cardDependencyRemote.taskGuids = { ...cardDependencyRemote.taskGuids, [taskId]: normalizedGuids };
  const nextTaskIds = { ...cardDependencyRemote.taskIds };
  const nextProgress = { ...cardDependencyRemote.progress };
  const nextStatuses = { ...cardDependencyRemote.statuses };
  for (const guid of normalizedGuids) {
    nextTaskIds[guid] = taskId;
    nextProgress[guid] = Number(task?.progress || 0);
    nextStatuses[guid] = task?.status || "queued";
  }
  cardDependencyRemote.taskIds = nextTaskIds;
  cardDependencyRemote.progress = nextProgress;
  cardDependencyRemote.statuses = nextStatuses;
  cardDependencyRemote.phase = String(task?.phase || "preparing");
  cardDependencyRemote.phaseProgress = Math.max(0, Math.min(100, Number(task?.phase_progress || 0)));
  cardDependencyRemote.downloadSpeedBps = Math.max(0, Number(task?.download_speed_bps || 0));
  cardDependencyRemote.downloadedBytes = Math.max(0, Number(task?.downloaded_bytes || 0));
  cardDependencyRemote.totalBytes = Math.max(0, Number(task?.total_bytes || 0));
  cardDependencyRemote.currentFile = String(task?.current_file || "");
  if (all) {
    cardDependencyRemote.allTaskId = taskId;
    cardDependencyRemote.allProgress = Number(task?.progress || 0);
    cardDependencyRemote.allStatus = task?.status || "queued";
    cardDependencyRemote.allPhase = String(task?.phase || "preparing");
    cardDependencyRemote.allPhaseProgress = Math.max(0, Math.min(100, Number(task?.phase_progress || 0)));
    cardDependencyRemote.allDownloadSpeedBps = Math.max(0, Number(task?.download_speed_bps || 0));
    cardDependencyRemote.allDownloadedBytes = Math.max(0, Number(task?.downloaded_bytes || 0));
    cardDependencyRemote.allTotalBytes = Math.max(0, Number(task?.total_bytes || 0));
    cardDependencyRemote.allCurrentFile = String(task?.current_file || "");
  }
  applyTask(task);
}

function clearCardDependencyDownloadTask(taskId, guids) {
  const normalizedTaskId = String(taskId || "").trim();
  const normalizedGuids = [...new Set((guids || []).map((guid) => String(guid || "").trim().toLocaleLowerCase()).filter(Boolean))];
  const nextTaskIds = { ...cardDependencyRemote.taskIds };
  const nextProgress = { ...cardDependencyRemote.progress };
  const nextStatuses = { ...cardDependencyRemote.statuses };
  const nextBusy = { ...cardDependencyRemote.busyGuids };
  for (const guid of normalizedGuids) {
    if (nextTaskIds[guid] === normalizedTaskId) delete nextTaskIds[guid];
    delete nextProgress[guid];
    delete nextStatuses[guid];
    delete nextBusy[guid];
  }
  const nextTaskGuids = { ...cardDependencyRemote.taskGuids };
  if (normalizedTaskId) delete nextTaskGuids[normalizedTaskId];
  cardDependencyRemote.taskIds = nextTaskIds;
  cardDependencyRemote.taskGuids = nextTaskGuids;
  cardDependencyRemote.progress = nextProgress;
  cardDependencyRemote.statuses = nextStatuses;
  cardDependencyRemote.busyGuids = nextBusy;
  if (cardDependencyRemote.allTaskId === normalizedTaskId) {
    cardDependencyRemote.allTaskId = "";
    cardDependencyRemote.allProgress = 0;
    cardDependencyRemote.allStatus = "";
    cardDependencyRemote.allPhase = "";
    cardDependencyRemote.allPhaseProgress = 0;
    cardDependencyRemote.allDownloadSpeedBps = 0;
    cardDependencyRemote.allDownloadedBytes = 0;
    cardDependencyRemote.allTotalBytes = 0;
    cardDependencyRemote.allCurrentFile = "";
    cardDependencyRemote.installingAll = false;
  }
  if (!Object.keys(nextTaskIds).length) {
    cardDependencyRemote.phase = "";
    cardDependencyRemote.phaseProgress = 0;
    cardDependencyRemote.downloadSpeedBps = 0;
    cardDependencyRemote.downloadedBytes = 0;
    cardDependencyRemote.totalBytes = 0;
    cardDependencyRemote.currentFile = "";
  }
}

async function toggleCardDependencyDownload(dependency) {
  const guid = normalizeCardDependencyGuid(dependency);
  const taskId = cardDependencyRemote.taskIds[guid];
  if (!taskId) return false;
  return toggleCardDependencyDownloadTask(taskId, [guid]);
}

async function toggleCardDependencyDownloadTask(taskId, guids = cardDependencyRemote.taskGuids[taskId] || []) {
  const normalizedTaskId = String(taskId || "").trim();
  if (!normalizedTaskId) return false;
  const currentStatus = cardDependencyRemote.statuses[guids[0]] || cardDependencyRemote.allStatus;
  const action = currentStatus === "paused" ? "resume" : "pause";
  const result = await window.desktopApi?.backendRequest?.(`/tasks/${encodeURIComponent(normalizedTaskId)}/control`, {
    method: "POST",
    body: { action }
  });
  if (!result?.ok) {
    const nextNotices = { ...cardDependencyRemote.notices };
    for (const guid of guids) nextNotices[guid] = result?.error || "无法控制下载";
    cardDependencyRemote.notices = nextNotices;
    return false;
  }
  applyTask(result.task);
  return true;
}

async function cancelCardDependency(dependency) {
  const guid = normalizeCardDependencyGuid(dependency);
  const taskId = cardDependencyRemote.taskIds[guid];
  if (!taskId) return false;
  const result = await window.desktopApi?.backendRequest?.(`/tasks/${encodeURIComponent(taskId)}/control`, {
    method: "POST",
    body: { action: "cancel" }
  });
  if (!result?.ok) {
    cardDependencyRemote.notices = {
      ...cardDependencyRemote.notices,
      [guid]: result?.error || "无法取消下载"
    };
    return false;
  }
  applyTask(result.task);
  return true;
}

async function toggleAllCardDependencies() {
  const taskId = cardDependencyRemote.allTaskId;
  if (!taskId) return false;
  return toggleCardDependencyDownloadTask(taskId, cardDependencyRemote.taskGuids[taskId] || []);
}

function buildDependencyRemoteSummary(dependencies) {
  const available = new Map();
  let missingCount = 0;
  for (const dependency of dependencies || []) {
    if (dependency?.matched) continue;
    missingCount += 1;
    const guid = normalizeCardDependencyGuid(dependency);
    const candidate = cardDependencyRemote.byGuid[guid]?.candidates?.[0];
    if (guid && candidate?.remote_id && !available.has(guid)) {
      available.set(guid, candidate);
    }
  }
  return {
    missingCount,
    availableCount: available.size,
    candidates: [...available.values()]
  };
}
const cardDependencyRemoteSummary = computed(() => (
  buildDependencyRemoteSummary(selectedCardDependencies.value)
));
const sceneDependencyRemoteSummary = computed(() => (
  buildDependencyRemoteSummary(selectedSceneCard.value?.dependencies)
));
const cardDependencyRemoteBusy = computed(() => Object.keys(cardDependencyRemote.busyGuids).length > 0);

function formatDownloadSpeed(bytesPerSecond) {
  const speed = Math.max(0, Number(bytesPerSecond || 0)) / (1024 * 1024);
  return `${speed >= 10 ? speed.toFixed(1) : speed.toFixed(2)} MB/s`;
}

function cardDependencyInlineProgress(dependency) {
  const guid = normalizeCardDependencyGuid(dependency);
  if (!guid || !cardDependencyRemote.taskIds[guid]) return null;
  const phaseValue = String(cardDependencyRemote.phase || "");
  const phase = phaseValue === "preparing" || !phaseValue ? "download" : phaseValue;
  if (!["download", "install"].includes(phase)) return null;
  const phaseProgress = Math.max(0, Math.min(100, Number(cardDependencyRemote.phaseProgress || 0)));
  return {
    phase,
    downloadProgress: phase === "download" ? phaseProgress : 100,
    installProgress: phase === "install" ? phaseProgress : (phase === "completed" ? 100 : 0),
    downloadSpeedBps: Math.max(0, Number(cardDependencyRemote.downloadSpeedBps || 0))
  };
}

async function loadCardDependencyRemoteCandidates(targetPath, dependencies, { scene = false } = {}) {
  const requestId = ++cardDependencyRemoteRequestId;
  const card = scene ? selectedSceneCard.value : selectedCardDetail.value;
  const selectedPath = scene ? selectedSceneDetailPath.value : selectedCardDetailPath.value;
  if (!card?.relativePath || selectedPath !== targetPath) return;
  const missingGuids = [...new Set(
    (dependencies || [])
      .filter((dependency) => !dependency?.matched)
      .map(normalizeCardDependencyGuid)
      .filter(Boolean)
  )];
  cardDependencyRemote.loading = true;
  cardDependencyRemote.error = "";
  cardDependencyRemote.byGuid = {};
  syncMissingItemPromptRemote();
  try {
    const query = new URLSearchParams({
      game_dir: String(paths.gameDir || ""),
      path: String(card.relativePath || "")
    });
    const endpoint = scene ? "/library/scene/missing-mods" : "/library/cards/missing-mods";
    const result = await window.desktopApi?.backendRequest?.(`${endpoint}?${query.toString()}`);
    if (!result?.ok) throw new Error(result?.error || "无法读取远程模组候选");
    if (requestId !== cardDependencyRemoteRequestId) return;
    const entries = {};
    for (const group of result.groups || []) entries[String(group.guid_norm || "").toLocaleLowerCase()] = group;
    cardDependencyRemote.byGuid = Object.fromEntries(missingGuids.map((guid) => [guid, entries[guid] || { can_download: false, reason: "远程索引中没有有效记录" }]));
    syncMissingItemPromptRemote();
  } catch (error) {
    if (requestId !== cardDependencyRemoteRequestId) return;
    cardDependencyRemote.error = error.message;
    syncMissingItemPromptRemote();
    log(`[Cards Completion Error] ${error.message}`);
  } finally {
    if (requestId === cardDependencyRemoteRequestId) {
      cardDependencyRemote.loading = false;
      syncMissingItemPromptRemote();
    }
  }
}

async function installCardDependency(dependency) {
  const isScene = cardBrowserMode.value === "scene";
  const card = isScene ? selectedSceneCard.value : selectedCardDetail.value;
  const guid = normalizeCardDependencyGuid(dependency);
  if (cardDependencyRemote.taskIds[guid]) {
    await toggleCardDependencyDownload(dependency);
    return;
  }
  const remote = cardDependencyRemote.byGuid[guid];
  const remoteId = remote?.candidates?.[0]?.remote_id;
  if (!card?.relativePath || !remoteId || cardDependencyRemote.busyGuids[guid]) return;
  cardDependencyRemote.busyGuids = { ...cardDependencyRemote.busyGuids, [guid]: true };
  cardDependencyRemote.notices = { ...cardDependencyRemote.notices, [guid]: "正在安装..." };
  try {
    const task = await submitTaskInBackground(
      "download_card_missing_mods",
      { remote_ids: [remoteId] },
      async (finalTask) => {
        const data = finalTask.data || {};
        if (finalTask.status === "completed") {
          cardDependencyRemote.notices = { ...cardDependencyRemote.notices, [guid]: "安装完成" };
          if (isScene) await loadSelectedSceneDetail(card);
          else await loadSelectedCardProfile(card);
          const currentCard = isScene ? selectedSceneCard.value : selectedCardDetail.value;
          if (currentCard) {
            const dependencies = isScene
              ? (currentCard.dependencies || [])
              : (selectedCardDependencies.value || []);
            currentCard.missingCount = dependencies.filter((item) => !item.matched).length;
            currentCard.dependencyCount = dependencies.length;
          }
        } else {
          cardDependencyRemote.notices = { ...cardDependencyRemote.notices, [guid]: finalTask.error || data.message || "安装失败" };
        }
        clearCardDependencyDownloadTask(finalTask.id, [guid]);
      },
      (startedTask) => registerCardDependencyDownloadTask(startedTask, [guid])
    );
    void task;
  } catch (error) {
    const nextBusy = { ...cardDependencyRemote.busyGuids };
    delete nextBusy[guid];
    cardDependencyRemote.busyGuids = nextBusy;
    cardDependencyRemote.notices = { ...cardDependencyRemote.notices, [guid]: error.message };
    log(`[Cards Completion Error] ${error.message}`);
  }
}

async function installAllCardDependencies() {
  const isScene = cardBrowserMode.value === "scene";
  const card = isScene ? selectedSceneCard.value : selectedCardDetail.value;
  const summary = isScene ? sceneDependencyRemoteSummary.value : cardDependencyRemoteSummary.value;
  if (!card?.relativePath || !summary.candidates.length || cardDependencyRemote.installingAll || cardDependencyRemoteBusy.value) return;

  const candidates = summary.candidates;
  const remoteIds = candidates.map((candidate) => candidate.remote_id);
  const guids = candidates.map(cardDependencyGuidFromCandidate);
  const nextBusy = { ...cardDependencyRemote.busyGuids };
  const nextNotices = { ...cardDependencyRemote.notices };
  for (const candidate of candidates) {
    const guid = String(candidate.guid_norm || candidate.guid || "").trim().toLocaleLowerCase();
    if (!guid) continue;
    nextBusy[guid] = true;
    nextNotices[guid] = "等待安装...";
  }
  cardDependencyRemote.busyGuids = nextBusy;
  cardDependencyRemote.notices = nextNotices;
  cardDependencyRemote.installingAll = true;

  try {
    await submitTaskInBackground(
      "download_card_missing_mods",
      { remote_ids: remoteIds },
      async (finalTask) => {
        const data = finalTask.data || {};
        const message = finalTask.status === "completed"
          ? "安装完成"
          : finalTask.error || data.message || "安装失败";
        const completedNotices = { ...cardDependencyRemote.notices };
        for (const candidate of candidates) {
          const guid = String(candidate.guid_norm || candidate.guid || "").trim().toLocaleLowerCase();
          if (guid) completedNotices[guid] = message;
        }
        cardDependencyRemote.notices = completedNotices;
        if (finalTask.status === "completed") {
          if (isScene) await loadSelectedSceneDetail(card);
          else await loadSelectedCardProfile(card);
          const currentCard = isScene ? selectedSceneCard.value : selectedCardDetail.value;
          if (currentCard) {
            const dependencies = isScene
              ? (currentCard.dependencies || [])
              : (selectedCardDependencies.value || []);
            currentCard.missingCount = dependencies.filter((item) => !item.matched).length;
            currentCard.dependencyCount = dependencies.length;
          }
        }
        clearCardDependencyDownloadTask(finalTask.id, guids);
      },
      (startedTask) => registerCardDependencyDownloadTask(startedTask, guids, { all: true })
    );
  } catch (error) {
    const failedNotices = { ...cardDependencyRemote.notices };
    for (const guid of guids) {
      if (guid) {
        failedNotices[guid] = error.message;
      }
    }
    cardDependencyRemote.notices = failedNotices;
    clearCardDependencyDownloadTask(cardDependencyRemote.allTaskId, guids);
    log(`[Cards Completion Error] ${error.message}`);
  }
}

function openCardProfileEditor() {
  const profile = selectedCardProfile.value;
  if (!profile || cardProfileEditor.busy) return;
  cardProfileEditor.values = {
    fullname: String(profile.fullname || ""),
    personality: Number(profile.personality ?? 0),
    birthMonth: Number(profile.birthMonth ?? 1),
    birthDay: Number(profile.birthDay ?? 1),
    voiceRate: Number(profile.voiceRate ?? 0.5),
    futanari: Boolean(profile.futanari)
  };
  cardProfileEditor.error = "";
  cardProfileEditor.message = "";
  cardProfileEditor.editing = true;
}

function cancelCardProfileEditor() {
  if (cardProfileEditor.busy) return;
  cardProfileEditor.editing = false;
  cardProfileEditor.error = "";
}

async function saveCardProfile() {
  const card = selectedCardDetail.value;
  if (!card?.relativePath || cardProfileEditor.busy) return;
  cardProfileEditor.busy = true;
  cardProfileEditor.error = "";
  cardProfileEditor.message = "";
  try {
    const result = await window.desktopApi?.backendRequest?.("/library/cards/update-profile", {
      method: "POST",
      body: {
        game_dir: paths.gameDir,
        path: card.relativePath,
        profile: { ...cardProfileEditor.values }
      }
    });
    if (!result?.ok) throw new Error(result?.error || "人物参数保存失败");
    selectedCardProfile.value = result.profile || selectedCardProfile.value;
    cardProfileEditor.editing = false;
    cardProfileEditor.message = result.warning || "人物参数已保存";
    log(`[Cards] 人物参数已保存：${card.relativePath}`);
    if (result.warning) log(`[Cards Warning] ${result.warning}`);
  } catch (error) {
    cardProfileEditor.error = error.message;
    log(`[Cards Error] ${error.message}`);
  } finally {
    cardProfileEditor.busy = false;
  }
}

async function setSelectedCardAsNavi(slot) {
  const card = selectedCardDetail.value;
  if (!card?.relativePath || !paths.gameDir || settingNaviSlot.value) return;
  settingNaviSlot.value = slot;
  naviActionNotice.type = "";
  naviActionNotice.message = "";
  try {
    const result = await window.desktopApi?.backendRequest?.("/library/cards/set-navi", {
      method: "POST",
      body: { game_dir: paths.gameDir, path: card.relativePath, slot }
    });
    if (!result?.ok) throw new Error(result?.error || "替换看板娘失败");
    log(`[Cards] 已将 ${card.name} 设为看板娘 ${slot}: ${result.target_path}`);
    naviActionNotice.type = "success";
    naviActionNotice.message = `已替换 ${slot}.png`;
  } catch (error) {
    log(`[Cards Error] ${error.message}`);
    naviActionNotice.type = "error";
    naviActionNotice.message = error.message;
  } finally {
    settingNaviSlot.value = "";
  }
}

function openCardLoadPrompt() {
  const card = selectedCardDetail.value;
  if (!card?.relativePath || cardLoadPrompt.busy) return;
  cardLoadPrompt.error = "";
  cardLoadNotice.type = "";
  cardLoadNotice.message = "";
  cardLoadPrompt.open = true;
}

function toggleCardLoadOption(key) {
  if (cardLoadPrompt.busy || !CARD_LOAD_OPTIONS.some((option) => option.key === key)) return;
  const selected = new Set(cardLoadPrompt.selected);
  if (selected.has(key)) selected.delete(key);
  else selected.add(key);
  cardLoadPrompt.selected = CARD_LOAD_OPTIONS
    .map((option) => option.key)
    .filter((optionKey) => selected.has(optionKey));
  cardLoadPrompt.error = "";
  void saveAppSettings().catch((error) => {
    log(`[Settings Error] ${error instanceof Error ? error.message : String(error)}`);
  });
}

async function loadSelectedCardToGame() {
  const card = selectedCardDetail.value;
  if (!card?.relativePath || cardLoadPrompt.busy) return;
  if (!cardLoadPrompt.selected.length) {
    cardLoadPrompt.error = "请至少选择一项人物卡内容。";
    return;
  }

  const request = window.desktopApi?.backendRequest;
  if (typeof request !== "function") {
    cardLoadPrompt.error = "资源通信接口尚未加载，请重启应用后再试。";
    return;
  }

  const body = {
    game_dir: paths.gameDir,
    path: card.relativePath
  };
  for (const option of CARD_LOAD_OPTIONS) {
    body[option.key] = cardLoadPrompt.selected.includes(option.key);
  }

  cardLoadPrompt.busy = true;
  cardLoadPrompt.error = "";
  cardLoadNotice.type = "info";
  cardLoadNotice.message = `正在读取人物卡「${card.name}」…`;
  try {
    const submitted = await request("/game-card-loader/load", {
      method: "POST",
      body
    });
    if (!submitted?.ok) throw new Error(formatGameItemProbeError(submitted));
    const accepted = submitted.data || {};
    const commandId = String(accepted.commandId || "").trim();
    if (!accepted.accepted || !commandId) {
      throw new Error(formatGameItemProbeError(accepted));
    }

    for (let attempt = 0; attempt < 70; attempt += 1) {
      await sleep(attempt === 0 ? 80 : 250);
      const polled = await request(`/game-item-probe/command?id=${encodeURIComponent(commandId)}`);
      if (!polled?.ok) throw new Error(formatGameItemProbeError(polled));
      const command = polled.data || {};
      if (command.status === "succeeded") {
        cardLoadPrompt.open = false;
        cardLoadNotice.type = "success";
        cardLoadNotice.message = `已将人物卡「${card.name}」的所选内容读取到当前角色。`;
        log(`[Game] 已读取人物卡：${card.relativePath}（${cardLoadPrompt.selected.join(", ")}）`);
        return;
      }
      if (["failed", "expired"].includes(command.status)) {
        throw new Error(formatGameItemProbeError(command));
      }
    }
    throw new Error("人物卡读取命令超过 15 秒未完成，请确认角色制作器仍处于打开状态。");
  } catch (error) {
    cardLoadPrompt.error = error instanceof Error ? error.message : String(error);
    cardLoadNotice.type = "error";
    cardLoadNotice.message = cardLoadPrompt.error;
    log(`[Game Card Error] ${cardLoadPrompt.error}`);
  } finally {
    cardLoadPrompt.busy = false;
  }
}

function setCardDependencyFilter(value) {
  const normalizedValue = String(value || "");
  cardDependencyFilter.value = ["missing", "normal"].includes(normalizedValue) || normalizedValue.startsWith("tag:")
    ? normalizedValue
    : "all";
  cardTagFilter.search = cardDependencyFilter.value.startsWith("tag:")
    ? cardDependencyFilter.value.slice(4)
    : "";
  cardTagFilter.open = false;
  cardTagLibraryRequestId += 1;
  cardTagFilter.resultsLoading = false;
  cardTagFilter.resultsError = "";
  if (cardTagFilter.scope === "library" && cardDependencyFilter.value.startsWith("tag:")) {
    void loadLibraryCardsByTag(cardDependencyFilter.value.slice(4));
  }
  resetCardFilterSelectionState();
}

function resetCardFilterSelectionState() {
  selectedCards.value = new Set();
  selectedCardDetailPath.value = "";
  selectedCardProfile.value = null;
  selectedCardDependencies.value = [];
  selectedCardProfileError.value = "";
  cardDependencyRemote.loading = false;
  cardDependencyRemote.error = "";
  cardDependencyRemote.byGuid = {};
  cardDependencyRemote.busyGuids = {};
  cardDependencyRemote.notices = {};
  cardDependencyRemote.installingAll = false;
  cardDependencyRemote.taskIds = {};
  cardDependencyRemote.taskGuids = {};
  cardDependencyRemote.progress = {};
  cardDependencyRemote.statuses = {};
  cardDependencyRemote.phase = "";
  cardDependencyRemote.phaseProgress = 0;
  cardDependencyRemote.downloadSpeedBps = 0;
  cardDependencyRemote.downloadedBytes = 0;
  cardDependencyRemote.totalBytes = 0;
  cardDependencyRemote.currentFile = "";
  cardDependencyRemote.allTaskId = "";
  cardDependencyRemote.allProgress = 0;
  cardDependencyRemote.allStatus = "";
  cardDependencyRemote.allPhase = "";
  cardDependencyRemote.allPhaseProgress = 0;
  cardDependencyRemote.allDownloadSpeedBps = 0;
  cardDependencyRemote.allDownloadedBytes = 0;
  cardDependencyRemote.allTotalBytes = 0;
  cardDependencyRemote.allCurrentFile = "";
  missingItemPrompt.open = false;
  missingItemPrompt.kind = "item";
  missingItemPrompt.name = "";
  missingItemPrompt.modId = "";
  missingItemPrompt.property = "";
  resetMissingItemPromptRemote();
  cardBulkMode.value = false;
}

function toggleCardFavoriteFilter() {
  cardFavoriteFilter.value = !cardFavoriteFilter.value;
  resetCardFilterSelectionState();
}

async function exportSelectedCardCoordinate() {
  const card = selectedCardDetail.value;
  if (!card?.relativePath || !paths.gameDir || exportingCoordinateCard.value) return;

  exportingCoordinateCard.value = true;
  coordinateExportNotice.type = "";
  coordinateExportNotice.message = "";
  coordinateExportNotice.path = "";
  try {
    const result = await window.desktopApi?.backendRequest?.("/library/cards/export-coordinate", {
      method: "POST",
      body: {
        game_dir: paths.gameDir,
        path: card.relativePath,
        output_dir: coordinateExportDir.value
      }
    });
    if (!result?.ok) throw new Error(result?.error || "服装卡导出失败");
    const skippedCount = Array.isArray(result.skipped_plugins) ? result.skipped_plugins.length : 0;
    const skippedHint = skippedCount > 0 ? `，已跳过 ${skippedCount} 个非服装插件` : "";
    coordinateExportNotice.type = "success";
    coordinateExportNotice.message = `已导出服装卡，包含 ${result.coordinate_dependencies || 0} 条模组依赖${skippedHint}`;
    coordinateExportNotice.path = result.target_path || "";
    log(`[Cards] 已导出服装卡 ${result.coordinate_name || card.name}: ${result.target_path}`);
  } catch (error) {
    coordinateExportNotice.type = "error";
    coordinateExportNotice.message = error.message;
    coordinateExportNotice.path = "";
    log(`[Cards Error] ${error.message}`);
  } finally {
    exportingCoordinateCard.value = false;
  }
}

function openCoordinateExportSettings() {
  coordinateExportPrompt.draft = coordinateExportDir.value;
  coordinateExportPrompt.error = "";
  coordinateExportPrompt.open = true;
}

async function selectCoordinateExportDir() {
  const selected = await window.desktopApi?.selectDirectory?.("选择服装卡导出目录");
  if (!selected) return;
  coordinateExportPrompt.draft = selected;
  coordinateExportPrompt.error = "";
}

async function saveCoordinateExportSettings() {
  const previousDir = coordinateExportDir.value;
  coordinateExportDir.value = String(coordinateExportPrompt.draft || "").trim();
  const result = await saveAppSettings();
  if (!result?.ok) {
    coordinateExportDir.value = previousDir;
    coordinateExportPrompt.error = result?.error || "无法保存导出路径";
    return;
  }
  coordinateExportPrompt.open = false;
}

async function revealExportedCoordinate() {
  if (!coordinateExportNotice.path) return;
  const result = await window.desktopApi?.showItemInFolder?.(coordinateExportNotice.path);
  if (!result?.ok) {
    coordinateExportNotice.type = "error";
    coordinateExportNotice.message = result?.error || "无法打开导出位置";
  }
}

function openPortablePackageSettings() {
  portablePackagePrompt.draftDir = portablePackageDir.value;
  portablePackagePrompt.compress = portablePackageCompress.value;
  portablePackagePrompt.types = [...portablePackageTypes.value];
  portablePackagePrompt.error = "";
  portablePackagePrompt.open = true;
}

async function selectPortablePackageDir() {
  const selected = await window.desktopApi?.selectDirectory?.("选择便携依赖包导出目录");
  if (!selected) return;
  portablePackagePrompt.draftDir = selected;
  portablePackagePrompt.error = "";
}

async function savePortablePackageSettings() {
  const draftDir = String(portablePackagePrompt.draftDir || "").trim();
  if (!draftDir) {
    portablePackagePrompt.error = "请选择导出目录。";
    return;
  }
  const previousDir = portablePackageDir.value;
  const previousCompress = portablePackageCompress.value;
  const previousTypes = [...portablePackageTypes.value];
  portablePackageDir.value = draftDir;
  portablePackageCompress.value = Boolean(portablePackagePrompt.compress);
  portablePackageTypes.value = PORTABLE_PACKAGE_TYPES
    .map((type) => type.key)
    .filter((type) => portablePackagePrompt.types.includes(type));
  const result = await saveAppSettings();
  if (!result?.ok) {
    portablePackageDir.value = previousDir;
    portablePackageCompress.value = previousCompress;
    portablePackageTypes.value = previousTypes;
    portablePackagePrompt.error = result?.error || "无法保存便携包配置";
    return;
  }
  portablePackagePrompt.open = false;
}

async function exportSelectedCardPortablePackage() {
  const card = selectedCardDetail.value;
  if (!card?.relativePath || !paths.gameDir || exportingPortablePackage.value) return;
  if (!portablePackageDir.value) {
    openPortablePackageSettings();
    portablePackagePrompt.error = "请先选择导出目录，再生成便携依赖包。";
    return;
  }

  exportingPortablePackage.value = true;
  portablePackageNotice.type = "";
  portablePackageNotice.message = "正在解析依赖并复制文件…";
  portablePackageNotice.path = "";
  try {
    await submitTaskInBackground(
      "export_character_dependency_package",
      {
        path: card.relativePath,
        target_dir: portablePackageDir.value,
        compress: portablePackageCompress.value,
        dependency_types: portablePackageTypes.value
      },
      async (task) => {
        exportingPortablePackage.value = false;
        if (task.status !== "completed") {
          portablePackageNotice.type = "error";
          portablePackageNotice.message = task.error || "便携依赖包生成失败";
          return;
        }
        const missingCount = task.data?.missing_mod_ids?.length || 0;
        const failureCount = task.data?.failure_count || 0;
        const issueHint = missingCount || failureCount
          ? `，${missingCount} 个依赖缺失，${failureCount} 个文件复制失败`
          : "";
        portablePackageNotice.type = missingCount || failureCount ? "warning" : "success";
        portablePackageNotice.message = `已生成${task.data?.compressed ? "压缩包" : "便携文件夹"}，包含 ${task.data?.exported_zipmod_count || 0} 个 zipmod 和 ${task.data?.exported_unity3d_count || 0} 个外部 Unity3D${issueHint}`;
        portablePackageNotice.path = task.data?.target_path || "";
        log(`[Cards] 便携依赖包已生成: ${portablePackageNotice.path}`);
      }
    );
  } catch (error) {
    exportingPortablePackage.value = false;
    portablePackageNotice.type = "error";
    portablePackageNotice.message = error.message;
    log(`[Cards Error] ${error.message}`);
  }
}

async function revealPortablePackage() {
  if (!portablePackageNotice.path) return;
  const result = await window.desktopApi?.showItemInFolder?.(portablePackageNotice.path);
  if (!result?.ok) {
    portablePackageNotice.type = "error";
    portablePackageNotice.message = result?.error || "无法打开导出位置";
  }
}

function toggleAllVisibleCards() {
  const next = new Set(selectedCards.value);
  if (allVisibleCardsSelected.value) {
    visibleCardPaths.value.forEach((path) => next.delete(path));
  } else {
    visibleCardPaths.value.forEach((path) => next.add(path));
  }
  selectedCards.value = next;
}

function clearSelectedCards() {
  selectedCards.value = new Set();
}

function updateSetup(key, value) {
  if (key === "resolution") {
    const match = String(value || "").match(/(\d+)\s*x\s*(\d+)/i);
    if (!match) return;
    setup.width = Number(match[1]);
    setup.height = Number(match[2]);
    setup.resolution = `${setup.width} x ${setup.height}`;
  } else if (["language", "quality", "display"].includes(key)) {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) return;
    setup[key] = Math.max(0, Math.round(parsed));
  } else if (key === "fullscreen") {
    setup.fullscreen = Boolean(value);
  } else {
    setup[key] = value;
  }
  setup.error = "";
  setup.warning = "";
  setup.dirty = true;
}

async function saveSetup() {
  if (!paths.gameDir || !setup.loaded || setup.saving) return false;
  setup.saving = true;
  setup.error = "";
  setup.warning = "";
  try {
    const result = await window.desktopApi?.saveGameSetup?.(paths.gameDir, {
      language: setup.language,
      quality: setup.quality,
      display: setup.display,
      width: setup.width,
      height: setup.height,
      fullscreen: setup.fullscreen
    });
    if (!result?.ok) {
      throw new Error(result?.error || "保存 setup.xml 失败");
    }
    applyGameSetupPayload(result);
    setup.dirty = false;
    if (result.registry?.ok === false) {
      log(`[Setup Warning] setup.xml 已保存，但注册表同步失败：${result.registry.error}`);
    } else {
      log(`[Setup] 已保存 ${result.filePath}${result.backupPath ? "，已生成 .bak 备份" : ""}`);
    }
    return true;
  } catch (error) {
    setup.error = error.message;
    log(`[Setup Error] ${error.message}`);
    return false;
  } finally {
    setup.saving = false;
  }
}

function clearLogs() {
  logs.value = [];
  seenTaskMessages.value = new Set();
}

function formatTrashDate(value) {
  const date = new Date(value || "");
  if (Number.isNaN(date.getTime())) return "时间未知";
  return date.toLocaleString("zh-CN", { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

async function loadTrash() {
  if (trashLoading.value) return;
  trashLoading.value = true;
  trashError.value = "";
  try {
    const result = await window.desktopApi?.backendRequest?.("/trash");
    if (!result?.ok) throw new Error(result?.error || "读取回收站失败");
    trashEntries.value = Array.isArray(result.entries) ? result.entries : [];
    trashRoot.value = String(result.root || "runtime/trash");
  } catch (error) {
    trashError.value = error.message;
  } finally {
    trashLoading.value = false;
  }
}

async function submitSelectedCardDelete() {
  const card = cardSingleDeletePrompt.card;
  if (!card?.relativePath || cardSingleDeletePrompt.busy) return;

  cardSingleDeletePrompt.busy = true;
  cardSingleDeletePrompt.error = "";
  try {
    const result = await window.desktopApi?.backendRequest?.("/library/cards/delete", {
      method: "POST",
      body: {
        game_dir: paths.gameDir,
        path: card.relativePath
      }
    });
    if (!result?.ok) throw new Error(result?.error || "人物卡删除失败");
    cardSingleDeletePrompt.open = false;
    log(`[Cards] 人物卡已移入回收站：${card.relativePath}`);
    await loadCardTree();
  } catch (error) {
    cardSingleDeletePrompt.error = error.message;
    log(`[Cards Error] ${error.message}`);
  } finally {
    cardSingleDeletePrompt.busy = false;
  }
}

async function restoreTrash(item) {
  if (!item?.id || trashAction.value) return;
  trashAction.value = `${item.kind}:${item.id}`;
  trashError.value = "";
  trashNotice.value = "";
  try {
    const restoreRoute = `/trash/${encodeURIComponent(item.kind)}/${encodeURIComponent(item.id)}/restore`;
    let result = await window.desktopApi?.backendRequest?.(restoreRoute, { method: "POST" });
    if (!result?.ok) {
      if (result?.stale) {
        // The list can be a stale filesystem snapshot while the backend is changing over.
        // Retry once only when a fresh backend read still confirms this exact entry is recoverable.
        await loadTrash();
        const refreshedItem = trashEntries.value.find(
          (entry) => entry.kind === item.kind && entry.id === item.id && entry.can_restore
        );
        if (refreshedItem) {
          result = await window.desktopApi?.backendRequest?.(restoreRoute, { method: "POST" });
        }
      }
    }
    if (!result?.ok) {
      throw new Error(result?.error || "恢复失败");
    }
    if (item.kind === "mods") {
      await refreshModDatabaseList();
    } else if (item.kind === "cards") {
      await loadCardTree();
      await refreshCurrentCardFolder();
    }
    trashNotice.value = result.index_warning || `已恢复：${item.name || item.file_name}`;
    await loadTrash();
  } catch (error) {
    trashError.value = error.message;
  } finally {
    trashAction.value = "";
  }
}

async function permanentlyDeleteTrash(item) {
  if (!item?.id || trashAction.value) return;
  if (!window.confirm(`永久删除“${item.name || item.file_name}”？此操作无法恢复。`)) return;
  trashAction.value = `${item.kind}:${item.id}`;
  trashError.value = "";
  trashNotice.value = "";
  try {
    const result = await window.desktopApi?.backendRequest?.(`/trash/${encodeURIComponent(item.kind)}/${encodeURIComponent(item.id)}/delete`, { method: "POST" });
    if (!result?.ok) {
      if (result?.stale) await loadTrash();
      throw new Error(result?.error || "永久删除失败");
    }
    trashNotice.value = `已永久删除：${item.name || item.file_name}`;
    await loadTrash();
  } catch (error) {
    trashError.value = error.message;
  } finally {
    trashAction.value = "";
  }
}

async function emptyTrash() {
  if (!trashEntries.value.length || trashAction.value) return;
  if (!window.confirm(`确定清空回收站中的 ${trashEntries.value.length} 个项目？此操作无法恢复。`)) return;
  trashAction.value = "empty";
  trashError.value = "";
  trashNotice.value = "";
  try {
    const result = await window.desktopApi?.backendRequest?.("/trash/empty", { method: "POST" });
    if (!result?.ok) throw new Error(result?.error || "清空回收站失败");
    trashNotice.value = `已永久删除 ${result.removed_count || 0} 个项目`;
    await loadTrash();
  } catch (error) {
    trashError.value = error.message;
  } finally {
    trashAction.value = "";
  }
}

onMounted(() => {
  const startedAt = performance.now();
  removeStartupLogListener = window.desktopApi?.onStartupLog?.((payload) => {
    const message = String(payload?.message || "").trim();
    if (message) log(message);
  });
  log("Ready.");
  log("[Mode] zipmod extract mode: Copy");
  log("[Backend] Python backend checking.");
  // Reveal the shell after its first render. Backend and wallpaper warm-up can
  // continue in the background without blocking the first usable frame.
  window.requestAnimationFrame(() => notifyRendererReady());
  void (async () => {
    const backendIsReady = await waitForBackendReady();
    if (backendIsReady) {
      log("[Backend] Python backend is ready.");
    } else {
      log("[Backend Error] Python backend startup timed out.");
      startBackendRetry();
    }
    await measureStep("loadAppSettings", () => loadAppSettings({ loadBackendData: backendIsReady }));
    if (!backendIsReady && backendReady.value && !setup.loaded) {
      await measureStep("loadAppSettings after backend recovery", () => loadAppSettings({ loadBackendData: true }));
    }
    if (backendIsReady) {
      await measureStep("loadAchievements", () => loadAchievements());
    }
    log(`[Startup] onMounted startup path ${backendIsReady ? "completed" : "completed without backend"} in ${formatDurationMs(performance.now() - startedAt)}`);
  })();
});

onBeforeUnmount(() => {
  removeStartupLogListener?.();
  removeStartupLogListener = null;
  stopBackendRetry();
  stopCurrentGameStatePolling();
});

const appCtx = reactive({
  activeAction,
  activeView,
  backendStatus,
  cardBrowserMode,
  analyzeDuplicateZipmods,
  achievements,
  achievementPreferences,
  achievementUnlockedCount,
  visibleAchievements,
  selectedAchievement,
  selectedTask,
  openTaskDetails,
  managerSettings,
  databaseWorkerOptions,
  formatAchievementProgress,
  loadAchievements,
  resetAchievementHistory,
  updateAchievementPreference,
  updateManagerSetting,
  updateDatabaseWorkerCount,
  wallpaperSource,
  wallpaperIsVideo,
  selectWallpaper,
  clearWallpaper,
  updatePortablePackageCompress,
  blenderExecutablePath,
  selectBlenderExecutable,
  clearBlenderExecutable,
  sb3utilityExecutablePath,
  selectSb3UtilityExecutable,
  resetSb3UtilityExecutable,
  allVisibleCardsSelected,
  allVisibleModsSelected,
  badgeClass,
  buildModDatabase,
  importExternalZipmods,
  openOrganizeAllPrompt,
  bulkActionBusy,
  bulkAuthorSuggestions,
  bulkDeletePrompt,
  cardDeletePrompt,
  cardSingleDeletePrompt,
  cardMovePrompt,
  cardMoveAvailable,
  cardMoveDestinationReady,
  cardMoveFolderRows,
  bulkDeleteErrorItemsPrompt,
  bulkCardTagPrompt,
  bulkDuplicateCleanupPrompt,
  cardBulkMode,
  cardBrowserCountText,
  cardCoverNotice,
  cardFavoriteNotice,
  cardRatingNotice,
  cardTagNotice,
  cardTagPrompt,
  cardTagPromptLibraryTags,
  cardTagFilter,
  cardTagFilterSuggestions,
  cardTagOptions,
  cardDependencyFilter,
  cardFavoriteFilter,
  cardDependencyExportPrompt,
  cardDetailTab,
  cardDependencyRemote,
  cardDependencyRemoteSummary,
  sceneDependencyRemoteSummary,
  cardDependencyRemoteBusy,
  formatDownloadSpeed,
  cardDependencyInlineProgress,
  cardDependencyRemoteFor,
  normalizeCardDependencyGuid,
  cancelCardDependency,
  installCardDependency,
  installAllCardDependencies,
  toggleAllCardDependencies,
  coordinateExportDir,
  coordinateExportPrompt,
  coordinateExportNotice,
  portablePackageDir,
  portablePackageCompress,
  portablePackagePrompt,
  portablePackageNotice,
  managerSettings,
  settingsNotice,
  cardFolderDisplay,
  refreshCurrentCardFolder,
  cardFolders,
  cardLibrary,
  clothesLibrary,
  clothesFolders,
  clothesCards,
  visibleClothesCards,
  clothesCardCountText,
  selectedClothesFolder,
  selectedClothesCard,
  selectedClothesDetailPath,
  clothesDetailTab,
  clothesSearch,
  clothesSort,
  toggleClothesFolder,
  selectClothesFolder,
  loadClothesTree,
  refreshClothesCards,
  handleClothesCardClick,
  loadMoreClothesCards,
  handleClothesCardGridScroll,
  clothesSideMode,
  sceneLibrary,
  sceneFolders,
  sceneCards,
  visibleSceneCards,
  sceneCardCountText,
  selectedSceneFolder,
  selectedSceneCard,
  selectedSceneDetailPath,
  sceneDetailTab,
  toggleSceneFolder,
  selectSceneFolder,
  loadSceneTree,
  refreshSceneCards,
  handleSceneCardClick,
  loadMoreSceneCards,
  handleSceneCardGridScroll,
  sceneSideMode,
  cardProfileEditor,
  cards,
  characterSideMode,
  checkModDatabase,
  cleaningDuplicateZipmods,
  cleanupDuplicateZipmods,
  clearLogs,
  trashEntries,
  filteredTrashEntries,
  trashLoading,
  trashAction,
  trashError,
  trashNotice,
  trashRoot,
  trashFilter,
  loadTrash,
  restoreTrash,
  permanentlyDeleteTrash,
  emptyTrash,
  formatTrashDate,
  closeModAuthorFilterSoon,
  closeItemAuthorFilterSoon,
  confirmDeleteSelectedItem,
  confirmDeleteSelectedMod,
  deleteItemPrompt,
  deleteModPrompt,
  deletingItemId,
  dependencyUsageFilter,
  dependencyUsageOptions,
  deleteModItemRow,
  deleteSelectedMod,
  duplicateZipmodDeleteConfirm,
  duplicateZipmodPrompt,
  enterCardBulkMode,
  enterModBulkMode,
  exportSelectedCardCoordinate,
  exportingCoordinateCard,
  exportingPortablePackage,
  exportSelectedCardPortablePackage,
  openCoordinateExportSettings,
  openPortablePackageSettings,
  CARD_LOAD_OPTIONS,
  cardLoadPrompt,
  cardLoadNotice,
  openCardLoadPrompt,
  toggleCardLoadOption,
  loadSelectedCardToGame,
  exitCardBulkMode,
  exitModBulkMode,
  filteredZipmodAuthorOptions,
  filteredItemAuthorOptions,
  favoritingCardPath,
  ratingCardPath,
  formatBytes,
  formatTaskDuration,
  formatTaskTimestamp,
  taskElapsedMs,
  taskTimingRows,
  taskResultRows,
  formatDatabaseTime,
  formatProfileValue,
  formatPersonality,
  formatCharacterSex,
  formatStat,
  importResultData,
  importResultGroups,
  importResultPrompt,
  organizeAllPrompt,
  gameDirDisplay,
  gameDirStatus,
  gamePluginSetup,
  startPluginSettings,
  loadStartPluginSettings,
  toggleStartPlugin,
  handleCardClick,
  handleCardFolderClick,
  handleModTableScroll,
  captureModTableScrollPosition,
  scheduleModTableScrollRestore,
  registerModTableScrollContainer,
  unregisterModTableScrollContainer,
  captureCardLibraryScrollPosition,
  scheduleCardLibraryScrollRestore,
  registerCardLibraryScrollContainer,
  unregisterCardLibraryScrollContainer,
  isBusy,
  itemAuthorOptions,
  itemAuthorFilterOpen,
  itemDatabase,
  itemDatabaseEmpty,
  itemFilterKinds,
  itemFilters,
  itemViewMode,
  itemKindLabel,
  itemKindOptions,
  loadItemFilters,
  workbenchItemCategoryOptions,
  isMapSceneItem,
  isStudioItem,
  itemSupportsModelPreview,
  relatedItemCategoryLabel,
  itemRows,
  itemTab,
  launchExecutable,
  libraryMode,
  loadItemRows,
  loadModRows,
  loadZipmodAuthors,
  loadGameSetup,
  locateSourceMod,
  log,
  logs,
  manifestEditor,
  missingThumbnailTargetItems,
  modAuthorFilterOpen,
  modBulkMode,
  modDatabase,
  modDatabaseEmpty,
  modFilters,
  modRows,
  modTab,
  normalizeZipmodStatus,
  openBulkAuthorPrompt,
  openBulkDeletePrompt,
  openBulkDeleteErrorItemsPrompt,
  openBulkCardTagPrompt,
  openBulkDuplicateCleanupPrompt,
  openBulkExportPrompt,
  openBulkOrganizePrompt,
  openBulkRepairUnity3dPrompt,
  openCardDependencyExportPrompt,
  openCardDeletePrompt,
  openSelectedCardDeletePrompt,
  openCardMovePrompt,
  openCardDependencyItem,
  openCardProfileEditor,
  openCardTagPrompt,
  openDuplicateZipmodInFolder,
  openDuplicateZipmodPrompt,
  openManifestAuthorPrompt,
  openManifestEditor,
  openGameDirectory,
  openRepository,
  openDirectoryShortcut,
  openDirectoryShortcutPrompt,
  openDirectoryShortcutEditor,
  selectDirectoryShortcutPath,
  closeDirectoryShortcutPrompt,
  saveDirectoryShortcut,
  deleteDirectoryShortcut,
  directoryShortcuts,
  directoryShortcutPrompt,
  openClothesDirectory,
  openSceneDirectory,
  openModItemInItemBrowser,
  openPackagedMod,
  openSelectedModInFolder,
  openThumbnailToolsPrompt,
  openSummaryCard,
  overviewSummaryCards,
  paths,
  workbenchAuthorId,
  workbenchWorkspacePath,
  workbenchActiveProjectId,
  workbenchProjects,
  saveWorkbenchProfile,
  setWorkbenchActiveProject,
  createWorkbenchProject,
  deleteWorkbenchProject,
  personalityOptions,
  recentTasks,
  repairingThumbnailItemId,
  openingUnity3dItemId,
  exportingUnity3dItemId,
  repairingUnity3dPath,
  repairThumbnailItem,
  openItemUnity3d,
  exportItemUnity3d,
  repairUnity3dIssue,
  replaceSelectedCardCover,
  replacingCardCover,
  revealExportedCoordinate,
  revealPortablePackage,
  saveCardProfile,
  saveSelectedCardTags,
  addCardTagDraft,
  addBulkCardTagDraft,
  saveSetup,
  saveDefaultOutputDirectory,
  selectSettingsDirectory,
  scheduleItemSearch,
  scheduleModAuthorFilter,
  selectGameDir,
  selectThumbnailToolDir,
  selectedThumbnailTargetCount,
  selectedCardDependencies,
  selectedCardDetail,
  selectedCardFolder,
  selectedCardProfile,
  selectedCardProfileError,
  selectedCardProfileLoading,
  naviActionNotice,
  setSelectedCardAsNavi,
  submitSelectedCardDelete,
  settingNaviSlot,
  selectedCards,
  selectedCount,
  selectedItem,
  itemContextMenu,
  itemAccessoryPrompt,
  itemFacePrompt,
  itemBodyPrompt,
  itemGameApply,
  itemGameNotice,
  assemblyMode,
  assemblyTargetSlot,
  assemblyContext,
  assemblyCharacterTarget,
  currentGameState,
  gameCurrentGroups: GAME_CURRENT_GROUPS,
  gameAccessorySlotOptions: GAME_ACCESSORY_SLOT_OPTIONS,
  gameAccessoryPartOptions: GAME_ACCESSORY_PART_OPTIONS,
  assemblyAccessoryPartMenu,
  itemGameApplySpec,
  itemGameApplyLabel,
  gameCurrentSlotLabel,
  gameCurrentItemName,
  setAssemblyMode,
  selectAssemblyCharacter,
  selectAssemblySlot,
  openAssemblyAccessoryPartMenu,
  closeAssemblyAccessoryPartMenu,
  assignAssemblyAccessoryPart,
  applyAssemblyItem,
  refreshCurrentGameState,
  openItemContextMenu,
  closeItemContextMenu,
  requestItemGameApply,
  closeItemAccessoryPrompt,
  confirmItemAccessoryApply,
  closeItemFacePrompt,
  confirmItemFaceApply,
  GAME_BODY_PAINT_SLOT_OPTIONS,
  closeItemBodyPrompt,
  confirmItemBodyApply,
  workbenchTemplateSelection,
  selectedMod,
  selectedModCanDelete,
  selectedModCount,
  selectedModDiagnosticGroups,
  selectedModDiagnostics,
  selectedModDiagnosticsError,
  selectedModDiagnosticsLoading,
  selectedModDiagnosticSummary,
  selectedModIds,
  selectedModItems,
  selectedModItemsError,
  selectedModItemsLoading,
  selectItem,
  beginWorkbenchTemplateSelection,
  selectWorkbenchTemplateFromItem,
  cancelWorkbenchTemplateSelection,
  consumeWorkbenchTemplateSelection,
  selectBulkAuthorSuggestion,
  selectMod,
  applyFirstCardTagFilterSuggestion,
  clearCardTagFilter,
  closeCardTagFilter,
  closeCardTagFilterSoon,
  openCardTagFilter,
  selectCardTagFilter,
  setDependencyUsageFilter,
  setItemViewMode,
  setCardBrowserMode,
  setCardDependencyFilter,
  toggleCardFavoriteFilter,
  setCardTagScope,
  toggleCardTagPromptTag,
  toggleBulkCardTagPromptTag,
  setLibraryMode,
  setModTab,
  setup,
  setupLanguageOptions,
  setupQualityOptions,
  someVisibleCardsSelected,
  someVisibleModsSelected,
  stats,
  syncSelectedModIdsWithVisibleRows,
  taskHint,
  taskName,
  taskPercent,
  taskStatusClass,
  taskStatusLabel,
  taskSummary,
  toggleAllVisibleCards,
  toggleSelectedCardFavorite,
  setSelectedCardRating,
  toggleAllVisibleMods,
  toggleCardFolder,
  toggleModSelection,
  toggleThumbnailTarget,
  updateCardTagFilterSearch,
  thumbnailIssueReason,
  thumbnailToolsPrompt,
  itemUnity3dFileName,
  visibleCards,
  unity3dIssueFileName,
  unity3dIssueSolution,
  updateSetup,
  views,
  zipmodAuthors,
  applyCurrentThumbnailToTargets,
  applyItemFilters,
  applyModFilters,
  exportCurrentItemThumbnail,
  refreshModDatabaseList,
  setAllThumbnailTargets,
  selectModAuthorFilter,
  selectItemAuthorFilter,
  submitBulkDeleteZipmods,
  submitBulkDeleteCharacterCards,
  submitBulkAddCharacterCardTags,
  submitBulkMoveCharacterCards,
  submitCardMoveFolderEdit,
  beginCardMoveFolderEdit,
  closeCardMovePrompt,
  selectCardMoveFolder,
  toggleCardMoveFolder,
  submitBulkDeleteErrorItems,
  submitBulkDuplicateCleanup,
  cancelCardProfileEditor
});

watch(activeView, (view, previousView) => {
  if (previousView === "mods" && view !== "mods") {
    captureModTableScrollPosition(libraryMode.value, modTableScrollTarget.value, { allowInactive: true });
  }
  if (view === "mods") {
    scheduleModTableScrollRestore();
  }
  if (previousView === "characters" && view !== "characters") {
    captureCardLibraryScrollPosition(
      cardBrowserMode.value,
      cardLibraryScrollTargets[cardBrowserMode.value],
      { allowInactive: true }
    );
  }
  if (view === "characters") {
    scheduleCardLibraryScrollRestore(cardBrowserMode.value);
  }
}, { flush: "sync" });

watch(libraryMode, (mode, previousMode) => {
  captureModTableScrollPosition(previousMode);
  scheduleModTableScrollRestore(mode);
}, { flush: "sync" });

watch(cardBrowserMode, (mode, previousMode) => {
  if (activeView.value === "characters") {
    captureCardLibraryScrollPosition(previousMode, cardLibraryScrollTargets[previousMode]);
  }
  scheduleCardLibraryScrollRestore(mode);
}, { flush: "sync" });

watch([activeView, cardBrowserMode, backendStatus], ([view, mode, status]) => {
  if (view === "trash" && status === "ready") {
    void loadTrash();
  }
  if (view === "mods" && status === "ready") {
    if (libraryMode.value === "items") {
      ensureItemDatabaseLoaded();
    } else {
      ensureModDatabaseLoaded();
    }
  }
  if (view === "characters" && status === "ready") {
    if (mode === "clothes") {
      if (!clothesLibrary.checked || !clothesLibrary.validGameDir || !clothesTree.value) {
        void ensureClothesLibraryLoaded();
      }
    } else if (mode === "scene") {
      if (!sceneLibrary.checked || !sceneLibrary.validGameDir || !sceneTree.value) {
        void ensureSceneLibraryLoaded();
      }
    } else if (mode === "character" && (!cardLibrary.checked || (cardLibrary.validGameDir && !cardTree.value))) {
      loadCardTree();
    }
  }
});

watch(backendStatus, (status, previousStatus) => {
  if (status !== "ready" || previousStatus === "ready") return;
  stopBackendRetry();
  if (paths.gameDir && !setup.loaded) {
    void loadAppSettings({ loadBackendData: true });
  }
});
</script>

<template>
  <div class="app-shell">
    <div class="wallpaper-layer" :class="{ 'wallpaper-layer--media-pending': !wallpaperReady }" aria-hidden="true">
      <video
        v-if="wallpaperIsVideo"
        class="wallpaper-media"
        :src="wallpaperSource"
        autoplay
        muted
        loop
        playsinline
        @canplay="handleWallpaperReady"
        @error="handleWallpaperError"
      ></video>
      <img
        v-else
        class="wallpaper-media"
        :src="wallpaperSource"
        alt=""
        @load="handleWallpaperReady"
        @error="handleWallpaperError"
      />
      <div class="wallpaper-scrim"></div>
    </div>
    <aside class="sidebar">
      <div class="brand">
        <img class="brand-logo" :src="brandLogo" alt="Star Manager" />
      </div>

      <nav class="nav" aria-label="Main navigation">
        <div
          v-for="view in views"
          :key="view.id"
          class="nav-entry"
          :class="{ active: activeView === view.id, 'nav-entry--cards': view.id === 'characters' }"
        >
          <button
            class="nav-main-button"
            type="button"
            @click="activeView = view.id"
          >
            <span class="nav-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" focusable="false">
                <g v-if="view.id === 'start'">
                  <path d="M7.5 8h9a4.5 4.5 0 0 1 4.2 6.1l-1.2 3.1a2 2 0 0 1-3.2.8l-2-1.7H9.7l-2 1.7a2 2 0 0 1-3.2-.8l-1.2-3.1A4.5 4.5 0 0 1 7.5 8Z"></path>
                  <path d="M7 11v4M5 13h4M16.5 12h.01M18.5 14h.01"></path>
                </g>
                <g v-else-if="view.id === 'overview'">
                  <rect x="4" y="4" width="6" height="6" rx="1"></rect><rect x="14" y="4" width="6" height="6" rx="1"></rect><rect x="4" y="14" width="6" height="6" rx="1"></rect><path d="M14 20v-5M17 20v-8M20 20v-3"></path>
                </g>
                <g v-else-if="view.id === 'characters'">
                  <path d="M7 5.5 18.2 4a1.8 1.8 0 0 1 2 1.5l1.5 10.8a1.8 1.8 0 0 1-1.5 2L9 19.8a1.8 1.8 0 0 1-2-1.5L5.5 7.5a1.8 1.8 0 0 1 1.5-2Z"></path>
                  <path d="M5.2 8.5 4 9a1.8 1.8 0 0 0-1 2.3l3.7 9.5a1.8 1.8 0 0 0 2.3 1l10-3.9M10 8.8l7.3-1M10.6 12.5l6.1-.8M11.2 16l3.8-.5"></path>
                </g>
                <g v-else-if="view.id === 'mods'">
                  <path d="m4 8 8-4 8 4-8 4-8-4Z"></path>
                  <path d="m4 8 .1 8 7.9 4 7.9-4L20 8M12 12v8M8 6l8 4"></path>
                </g>
                <g v-else-if="view.id === 'workbench'">
                  <rect x="3" y="7" width="18" height="13" rx="2"></rect>
                  <path d="M8 7V4h8v3M3 12h18M10 12v3h4v-3"></path>
                </g>
                <g v-else-if="view.id === 'plugins'">
                  <path d="M9.5 4H4v5.5a2.5 2.5 0 1 1 0 5V20h5.5a2.5 2.5 0 1 1 5 0H20v-5.5a2.5 2.5 0 1 0 0-5V4h-5.5a2.5 2.5 0 1 0-5 0Z"></path>
                </g>
                <g v-else-if="view.id === 'trash'">
                  <path d="M6.5 8.5h11l-.7 11a1.7 1.7 0 0 1-1.7 1.5H8.9a1.7 1.7 0 0 1-1.7-1.5l-.7-11Z"></path>
                  <path d="M4 8.5h16M9 5h6l1 3.5H8L9 5ZM10 12v5M14 12v5"></path>
                </g>
                <g v-else>
                  <path d="M6 3h9l3 3v15H6V3Z"></path>
                  <path d="M15 3v4h4M9 11h6M9 15h6M9 19h4"></path>
                </g>
              </svg>
            </span>
            <span>{{ view.label }}</span>
          </button>
          <div v-if="view.id === 'characters'" class="nav-card-type-actions" role="group" aria-label="卡片类型">
            <button
              class="nav-card-type-button"
              :class="{ active: cardBrowserMode === 'character' }"
              type="button"
              aria-label="人物卡"
              title="人物卡"
              :aria-pressed="cardBrowserMode === 'character'"
              @click="setCardBrowserMode('character')"
            >
              <img class="nav-card-type-image" :src="characterCardTypeIcon" alt="" aria-hidden="true">
            </button>
            <button
              class="nav-card-type-button"
              :class="{ active: cardBrowserMode === 'clothes' }"
              type="button"
              aria-label="服装卡"
              title="服装卡"
              :aria-pressed="cardBrowserMode === 'clothes'"
              @click="setCardBrowserMode('clothes')"
            >
              <img class="nav-card-type-image" :src="clothesCardTypeIcon" alt="" aria-hidden="true">
            </button>
            <button
              class="nav-card-type-button"
              :class="{ active: cardBrowserMode === 'scene' }"
              type="button"
              aria-label="场景卡"
              title="场景卡"
              :aria-pressed="cardBrowserMode === 'scene'"
              @click="setCardBrowserMode('scene')"
            >
              <img class="nav-card-type-image" :src="sceneCardTypeIcon" alt="" aria-hidden="true">
            </button>
          </div>
        </div>
      </nav>

      <nav class="nav nav-secondary" aria-label="Manager navigation">
        <button
          type="button"
          :class="{ active: activeView === 'settings' }"
          @click="activeView = 'settings'"
        >
          <span class="nav-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" focusable="false">
              <path d="M12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7Z"></path>
              <path d="M19.4 15a1.7 1.7 0 0 0 .34 1.87l.06.06-2.83 2.83-.06-.06a1.7 1.7 0 0 0-1.87-.34 1.7 1.7 0 0 0-1.04 1.56V21h-4v-.08a1.7 1.7 0 0 0-1.04-1.56 1.7 1.7 0 0 0-1.87.34l-.06.06-2.83-2.83.06-.06A1.7 1.7 0 0 0 4.6 15 1.7 1.7 0 0 0 3.08 14H3v-4h.08A1.7 1.7 0 0 0 4.6 9a1.7 1.7 0 0 0-.34-1.87l-.06-.06 2.83-2.83.06.06A1.7 1.7 0 0 0 8.96 4.6 1.7 1.7 0 0 0 10 3.08V3h4v.08a1.7 1.7 0 0 0 1.04 1.56 1.7 1.7 0 0 0 1.87-.34l.06-.06 2.83 2.83-.06.06A1.7 1.7 0 0 0 19.4 9 1.7 1.7 0 0 0 20.92 10H21v4h-.08A1.7 1.7 0 0 0 19.4 15Z"></path>
            </svg>
          </span>
          <span>设置</span>
        </button>
      </nav>
    </aside>

    <main class="main" :class="{ 'assembly-mode-main': assemblyUiActive, 'item-library-main': isItemLibraryView && !assemblyMode, 'character-library-main': activeView === 'characters', 'plugin-library-main': activeView === 'plugins', 'workbench-main': activeView === 'workbench', 'runtime-log-main': activeView === 'logs', 'settings-main': activeView === 'settings', 'trash-main': activeView === 'trash' }">
      <header v-if="activeView !== 'characters' && activeView !== 'plugins' && activeView !== 'workbench' && activeView !== 'logs' && activeView !== 'settings' && activeView !== 'trash'" class="topbar" :class="{ 'assembly-topbar': assemblyUiActive, 'topbar-item-library': isItemLibraryView && !assemblyMode }">
        <template v-if="assemblyUiActive">
          <div class="assembly-topbar-context">
            <div class="assembly-hero">
              <div class="assembly-hero-copy">
                <h3>{{ assemblyCharacterTarget.target === 'hscene' ? 'H 场景角色' : '角色编辑器' }}</h3>
                <small v-if="assemblyContext.scene === 'hscene'">选择一个角色后查看并编辑其当前装配。</small>
                <small v-else>读取当前角色的实时装配状态。</small>
              </div>
              <div v-if="assemblyContext.available" class="assembly-character-picker assembly-character-picker-topbar" aria-label="装配目标角色">
                <button
                  type="button"
                  class="assembly-character-picker-toggle"
                  :class="{ open: assemblyCharacterPickerOpen }"
                  aria-haspopup="listbox"
                  :aria-expanded="assemblyCharacterPickerOpen"
                  aria-controls="assembly-character-options"
                  @click="toggleAssemblyCharacterPicker"
                >
                  <span class="assembly-character-picker-current">
                    <strong>{{ selectedAssemblyCharacter.name }}</strong>
                    <small>{{ selectedAssemblyCharacter.meta }}</small>
                  </span>
                  <span class="assembly-character-picker-chevron" :class="{ open: assemblyCharacterPickerOpen }" aria-hidden="true">⌄</span>
                </button>
                <div v-if="assemblyCharacterPickerOpen" id="assembly-character-options" class="assembly-character-options" role="listbox" aria-label="可选装配角色">
                  <button
                    v-for="option in assemblyCharacterOptions"
                    :key="option.key"
                    type="button"
                    class="assembly-character-option"
                    :class="{ selected: isAssemblyCharacterSelected(option) }"
                    role="option"
                    :aria-selected="isAssemblyCharacterSelected(option)"
                    @click="handleAssemblyCharacterSelect(option)"
                  >
                    <span class="assembly-character-option-copy">
                      <strong>{{ option.name }}</strong>
                      <small>{{ option.meta }}</small>
                    </span>
                    <span v-if="isAssemblyCharacterSelected(option)" class="assembly-character-option-check" aria-hidden="true">✓</span>
                  </button>
                  <div v-if="!assemblyCharacterOptions.length" class="assembly-character-picker-empty">当前没有可用角色。</div>
                </div>
              </div>
              <span class="assembly-sync-state" :class="{ ready: currentGameState.available && !currentGameState.loading, loading: currentGameState.loading }">
                {{ currentGameState.loading ? '同步中' : currentGameState.available ? '已连接' : '未连接' }}
              </span>
            </div>
          </div>
          <div v-if="currentGameState.available && assemblyStatusNotice" class="assembly-status-banner assembly-topbar-notice" :class="assemblyStatusNotice.tone" role="status" aria-live="polite">
            <div class="assembly-status-copy">
              <strong>{{ assemblyStatusNotice.title }}</strong>
              <span>{{ assemblyStatusNotice.message }}</span>
              <small v-if="assemblyStatusNotice.detail">{{ assemblyStatusNotice.detail }}</small>
            </div>
            <div class="assembly-status-actions">
              <button v-if="assemblyStatusNotice.showRetry" type="button" class="assembly-status-retry" @click="refreshCurrentGameState">重试</button>
              <button v-if="assemblyStatusNotice.showClose" type="button" class="assembly-status-close" aria-label="关闭换装提示" @click="itemGameNotice.message = ''">×</button>
            </div>
          </div>
          <div v-else-if="currentGameState.loading && !currentGameState.available" class="assembly-state-card loading assembly-topbar-state" role="status">
            <strong>正在读取角色当前装配</strong>
            <span>等待游戏角色制作器返回实际栏位信息。</span>
          </div>
          <div v-else-if="currentGameState.error && !currentGameState.available" class="assembly-state-card error assembly-topbar-state" role="alert">
            <strong>无法读取游戏角色状态</strong>
            <span>{{ currentGameState.error }}</span>
            <button type="button" @click="refreshCurrentGameState">重试</button>
          </div>
          <div v-else-if="!currentGameState.available" class="assembly-state-card assembly-topbar-state" role="status">
            <strong>{{ assemblyContext.scene === 'hscene' ? '当前角色没有可用装配数据' : '当前没有可用的角色编辑器' }}</strong>
            <span>{{ assemblyContext.scene === 'hscene' ? '请确认 H 场景角色已经完成加载，并确认 Game Item Probe 已加载。' : '请启动 HS2 并进入角色制作器，同时确认 Game Item Probe 已加载。' }}</span>
            <button type="button" @click="refreshCurrentGameState">重新读取</button>
          </div>
        </template>
        <template v-else-if="!isItemLibraryView">
        <div class="path-box">
          <button type="button" class="primary" @click="selectGameDir">选择 HS2 目录</button>
          <div class="path-value">
            <span class="path-label">当前目录</span>
            <span class="path-text">{{ gameDirDisplay }}</span>
          </div>
          <span class="badge" :class="badgeClass(gameDirStatus)"><span class="dot"></span>{{ gameDirStatus }}</span>
          <span class="badge" :class="gamePluginSetup.status === '安装失败' ? 'danger' : gamePluginSetup.status === '已就绪' ? 'ok' : gamePluginSetup.status === '检查中' ? 'warn' : 'neutral'"><span class="dot"></span>{{ gamePluginSetup.checking ? "检查 Star Manager 插件" : gamePluginSetup.status }}</span>
        </div>

        <button class="system-status" type="button" @click="activeView = 'logs'">
          <span class="status-main">
            <span class="status-title">{{ taskName }}</span>
            <span class="status-percent">{{ taskPercent }}</span>
          </span>
          <span class="progress-rail"><span class="progress-fill" :style="{ width: taskPercent }"></span></span>
          <span class="status-meta">
            <span>{{ taskHint }}</span>
          </span>
        </button>

        <div class="top-actions">
          <span class="badge" :class="backendReady ? 'ok' : 'danger'"><span class="dot"></span>Backend {{ backendStatus }}</span>
          <button
            type="button"
            :disabled="isBusy && activeAction === 'build_mod_database'"
            @click="buildModDatabase"
          >重建数据库</button>
        </div>
        </template>
        <template v-else-if="isItemLibraryView">
          <div class="topbar-item-kind-filter" aria-label="物品类别筛选">
            <div class="topbar-item-kind-heading">
              <button type="button" class="topbar-kind-clear" :class="{ active: !itemFilters.kind }" @click="clearTopbarKindFilter">全部 Kind</button>
              <div class="item-view-switch" role="group" aria-label="物品视图">
                <button type="button" :class="{ active: itemViewMode === 'table' }" :aria-pressed="itemViewMode === 'table'" title="表格视图" @click="setItemViewMode('table')">
                  <span>表格</span>
                </button>
                <button type="button" :class="{ active: itemViewMode === 'compact' }" :aria-pressed="itemViewMode === 'compact'" title="紧凑缩略图视图" @click="setItemViewMode('compact')">
                  <span>紧凑</span>
                </button>
              </div>
            </div>

            <div v-if="itemKindLevel === 'categories'" class="topbar-kind-groups" role="navigation" aria-label="物品类别分区">
              <section
                v-for="group in TOPBAR_KIND_GROUPS"
                :key="group.key"
                class="topbar-kind-group"
                :class="`topbar-kind-group-${group.tone}`"
              >
                <div class="topbar-kind-group-title">
                  <span>{{ group.label }}</span>
                </div>
                <div class="topbar-kind-category-row" role="group" :aria-label="`${group.label}一级类别`">
                  <button
                    v-for="category in group.categories"
                    :key="category.key"
                    type="button"
                    class="topbar-kind-category"
                    :class="{ active: (category.kinds.length === 1 && topbarKindFilterIsActive(category.kinds[0])) || (itemKindGroup === group.key && itemKindCategory === category.key && itemKindLevel === 'children') }"
                    :title="category.kinds.length === 1 ? `筛选${category.label}` : `打开${group.label} / ${category.label}子类`"
                    @click="openTopbarKindCategory(group, category)"
                  >{{ category.label }}</button>
                </div>
              </section>
            </div>

            <div v-else class="topbar-kind-subview" :class="`topbar-kind-subview-${activeTopbarKindGroup.tone}`">
              <button type="button" class="topbar-kind-back" title="返回物品类别分区" @click="resetTopbarKindNavigation">
                <span aria-hidden="true">‹</span> 返回类别
              </button>
              <div class="topbar-kind-breadcrumb" aria-label="当前物品类别路径">
                <span class="topbar-kind-gender">{{ activeTopbarKindGroup.label }}</span>
                <span aria-hidden="true">/</span>
                <strong>{{ activeTopbarKindCategory?.label }}</strong>
              </div>
              <div class="topbar-kind-children" role="group" :aria-label="`${activeTopbarKindGroup.label}${activeTopbarKindCategory?.label}子类`">
                <button
                  v-for="child in activeTopbarKindChildren"
                  :key="child.value"
                  type="button"
                  class="topbar-kind-child"
                  :class="{ active: topbarKindFilterIsActive(child.value) }"
                  :aria-pressed="topbarKindFilterIsActive(child.value)"
                  :title="`筛选${child.label}`"
                  @click="selectTopbarKindChild(child.value)"
                >
                  <img v-if="topbarKindIcon(child.value)" class="topbar-kind-child-icon" :src="topbarKindIcon(child.value)" alt="" aria-hidden="true">
                  <span>{{ child.label }}</span>
                </button>
              </div>
            </div>
          </div>
        </template>
      </header>

      <section class="workspace" :class="{ 'start-workspace': activeView === 'start', 'item-library-workspace': isItemLibraryView && !assemblyMode }">
        <KeepAlive>
          <component :is="activePageComponent" :ctx="appCtx" />
        </KeepAlive>
      </section>

      <CardCoverCropper
        :open="cardCoverCrop.open"
        :image-data="cardCoverCrop.imageData"
        :image-name="cardCoverCrop.imageName"
        :busy="replacingCardCover"
        @cancel="cancelCardCoverCrop"
        @confirm="confirmCardCoverCrop"
      />

      <div
        v-if="directoryShortcutPrompt.open"
        class="prompt-backdrop directory-shortcut-backdrop"
        @click.self="!directoryShortcutPrompt.saving && closeDirectoryShortcutPrompt()"
      >
        <div
          class="prompt-panel directory-shortcut-panel"
          role="dialog"
          aria-modal="true"
          :aria-label="directoryShortcutPrompt.editingIndex >= 0 ? '编辑目录快捷入口' : '添加目录快捷入口'"
          :aria-busy="directoryShortcutPrompt.saving"
        >
          <input
            v-model="directoryShortcutPrompt.name"
            class="search"
            type="text"
            aria-label="按钮名"
            placeholder="按钮名"
            maxlength="32"
            autocomplete="off"
            autofocus
            :disabled="directoryShortcutPrompt.saving"
            @keydown.enter.prevent="saveDirectoryShortcut"
          >
          <div class="prompt-field-row">
            <input
              v-model="directoryShortcutPrompt.path"
              class="search"
              type="text"
              aria-label="目录路径"
              placeholder="目录路径"
              readonly
              :disabled="directoryShortcutPrompt.saving"
            >
            <button type="button" :disabled="directoryShortcutPrompt.saving" @click="selectDirectoryShortcutPath">选择</button>
          </div>
          <div v-if="directoryShortcutPrompt.error" class="prompt-error">{{ directoryShortcutPrompt.error }}</div>
          <div class="prompt-actions">
            <button
              v-if="directoryShortcutPrompt.editingIndex >= 0"
              type="button"
              class="danger-action directory-shortcut-delete"
              :disabled="directoryShortcutPrompt.saving"
              @click="deleteDirectoryShortcut"
            >删除</button>
            <button type="button" :disabled="directoryShortcutPrompt.saving" @click="closeDirectoryShortcutPrompt">取消</button>
            <button type="button" class="primary" :disabled="directoryShortcutPrompt.saving" @click="saveDirectoryShortcut">
              {{ directoryShortcutPrompt.saving ? "保存中…" : "保存" }}
            </button>
          </div>
        </div>
      </div>

        <div v-if="organizeAllPrompt.open" class="prompt-backdrop" @click.self="organizeAllPrompt.open = false">
          <div class="prompt-panel organize-all-panel">
            <span class="risk-kicker">会移动游戏文件</span>
            <strong>按作者整理全部模组</strong>
            <p class="subtext">将扫描并移动当前 <code>mods</code> 下的全部 zipmod，结构为 <code>mods/作者/模组.zipmod</code>。</p>
            <dl class="organize-impact">
              <div><dt>源路径</dt><dd>{{ paths.gameDir }}\mods</dd></div>
              <div><dt>未知作者</dt><dd>归入“未知作者”目录</dd></div>
              <div><dt>重名处理</dt><dd>自动编号，不覆盖已有文件</dd></div>
              <div><dt>空目录</dt><dd>整理完成后自动删除</dd></div>
              <div><dt>完成后</dt><dd>自动刷新模组数据库</dd></div>
            </dl>
            <div v-if="organizeAllPrompt.error" class="prompt-error">{{ organizeAllPrompt.error }}</div>
            <div class="prompt-actions">
              <button type="button" @click="organizeAllPrompt.open = false">取消</button>
              <button type="button" class="danger-action" :disabled="isBusy" @click="submitOrganizeAllZipmods">确认整理当前 mods 目录</button>
            </div>
          </div>
        </div>

        <div v-if="importResultPrompt.open" class="prompt-backdrop" @click.self="importResultPrompt.open = false">
          <div class="prompt-panel import-result-panel">
            <div class="import-result-head">
              <div>
                <strong>导入结果</strong>
                <p class="subtext">{{ importResultData.source_dir || "外部目录" }}</p>
              </div>
              <button type="button" @click="importResultPrompt.open = false">关闭</button>
            </div>
            <div class="import-result-metrics">
              <span><strong>{{ importResultData.scanned_count || 0 }}</strong> zipmod</span>
              <span><strong>{{ importResultData.zip_renamed_count || 0 }}</strong> zip→zipmod</span>
              <span><strong>{{ importResultData.imported_count || 0 }}</strong> 正常</span>
              <span><strong>{{ importResultData.promoted_count || 0 }}</strong> 保留更优</span>
              <span><strong>{{ importResultData.cleaned_count || 0 }}</strong> 清理重复</span>
              <span><strong>{{ importResultData.unity3d_repaired_count || 0 }}</strong> Unity3D</span>
              <span><strong>{{ importResultData.card_imported_count || 0 }}</strong> 角色卡</span>
              <span><strong>{{ importResultData.coordinate_imported_count || 0 }}</strong> 服装卡</span>
              <span><strong>{{ importResultData.failure_count || 0 }}</strong> 失败</span>
            </div>
            <div class="import-result-list">
              <section
                v-for="group in importResultGroups"
                :key="group.key"
                class="import-result-group"
                :class="group.tone"
              >
                <header>
                  <span>{{ group.label }}</span>
                  <strong>{{ group.count }}</strong>
                </header>
                <p v-if="!group.items.length" class="subtext">{{ group.empty }}</p>
                <article v-for="item in group.items" :key="group.key + ':' + item.title + ':' + item.detail" class="import-result-row">
                  <div>
                    <strong>{{ item.title }}</strong>
                    <small v-if="item.meta">{{ item.meta }}</small>
                  </div>
                  <p>{{ item.note }}</p>
                  <code v-if="item.detail">{{ item.detail }}</code>
                </article>
              </section>
            </div>
          </div>
        </div>

        <div v-if="coordinateExportPrompt.open" class="prompt-backdrop" @click.self="coordinateExportPrompt.open = false">
          <div class="prompt-panel coordinate-export-settings-panel" role="dialog" aria-modal="true" aria-labelledby="coordinate-export-settings-title">
            <strong id="coordinate-export-settings-title">配置服装卡导出路径</strong>
            <p class="subtext">未配置时，服装卡会按人物性别保存到游戏目录下的 <code>UserData/coordinate/female</code> 或 <code>male</code>。</p>
            <label class="coordinate-path-field">
              <span>自定义导出目录</span>
              <div class="prompt-field-row">
                <input
                  v-model="coordinateExportPrompt.draft"
                  class="search"
                  type="text"
                  placeholder="使用游戏默认目录"
                  readonly
                >
                <button type="button" @click="selectCoordinateExportDir">选择目录</button>
              </div>
            </label>
            <button
              v-if="coordinateExportPrompt.draft"
              class="coordinate-use-default"
              type="button"
              @click="coordinateExportPrompt.draft = ''; coordinateExportPrompt.error = ''"
            >
              恢复默认路径
            </button>
            <div v-if="coordinateExportPrompt.error" class="prompt-error">{{ coordinateExportPrompt.error }}</div>
            <div class="prompt-actions">
              <button type="button" @click="coordinateExportPrompt.open = false">取消</button>
              <button class="primary" type="button" @click="saveCoordinateExportSettings">保存配置</button>
            </div>
          </div>
        </div>

        <div v-if="portablePackagePrompt.open" class="prompt-backdrop" @click.self="portablePackagePrompt.open = false">
          <div class="prompt-panel portable-package-settings-panel" role="dialog" aria-modal="true" aria-labelledby="portable-package-settings-title">
            <strong id="portable-package-settings-title">配置便携依赖包</strong>
            <p class="subtext">打包当前人物卡、已匹配的 zipmod 与外部 Unity3D。包内保留游戏目录结构，原文件不会被移动。</p>
            <label class="coordinate-path-field">
              <span>导出目录</span>
              <div class="prompt-field-row">
                <input
                  v-model="portablePackagePrompt.draftDir"
                  class="search"
                  type="text"
                  placeholder="请选择导出目录"
                  readonly
                >
                <button type="button" @click="selectPortablePackageDir">选择目录</button>
              </div>
            </label>
            <label class="portable-compress-option">
              <input v-model="portablePackagePrompt.compress" type="checkbox">
              <span>
                <strong>压缩为 ZIP</strong>
                <small>{{ portablePackagePrompt.compress ? '生成便于分享的单个文件' : '生成可直接浏览的文件夹' }}</small>
              </span>
            </label>
            <fieldset class="portable-type-picker">
              <legend>
                <span>导出的模组类型</span>
                <small>已选 {{ portablePackagePrompt.types.length }} / {{ PORTABLE_PACKAGE_TYPES.length }}</small>
              </legend>
              <div class="portable-type-grid">
                <label
                  v-for="type in PORTABLE_PACKAGE_TYPES"
                  :key="type.key"
                  class="portable-type-option"
                  :class="{ selected: portablePackagePrompt.types.includes(type.key) }"
                >
                  <input v-model="portablePackagePrompt.types" type="checkbox" :value="type.key">
                  <span class="portable-type-copy">
                    <strong>{{ type.label }}</strong>
                    <small>{{ type.description }}</small>
                  </span>
                  <span class="portable-type-check" aria-hidden="true">✓</span>
                </label>
              </div>
              <small v-if="portablePackagePrompt.types.length === 0" class="portable-type-empty">未选择模组类型时，只导出人物卡与依赖清单。</small>
            </fieldset>
            <div v-if="portablePackagePrompt.error" class="prompt-error">{{ portablePackagePrompt.error }}</div>
            <div class="prompt-actions">
              <button type="button" @click="portablePackagePrompt.open = false">取消</button>
              <button class="primary" type="button" @click="savePortablePackageSettings">保存配置</button>
            </div>
          </div>
        </div>

        <div v-if="cardDependencyExportPrompt.open" class="prompt-backdrop" @click.self="cardDependencyExportPrompt.open = false">
          <div class="prompt-panel">
            <strong>导出依赖模组</strong>
            <p class="subtext">导出已选人物卡依赖的 zipmod。</p>
            <div class="prompt-field-row">
              <input
                v-model="cardDependencyExportPrompt.targetDir"
                class="search"
                type="text"
                placeholder="请选择导出目录"
                readonly
              >
              <button type="button" :disabled="isBusy" @click="selectCardDependencyExportDir">选择目录</button>
            </div>
            <div class="export-mode-group two-column-grid" role="radiogroup" aria-label="导出方式">
              <label>
                <input v-model="cardDependencyExportPrompt.mode" type="radio" value="copy" @change="cardDependencyExportPrompt.confirmMove = false">
                <span>复制</span>
              </label>
              <label>
                <input v-model="cardDependencyExportPrompt.mode" type="radio" value="move" @change="cardDependencyExportPrompt.confirmMove = false">
                <span>剪切</span>
              </label>
            </div>
            <div v-if="cardDependencyExportPrompt.confirmMove" class="prompt-error">
              将剪切 {{ selectedCount }} 张人物卡依赖的 zipmod，原文件会被移动。请再次确认。
            </div>
            <div v-if="cardDependencyExportPrompt.error" class="prompt-error">{{ cardDependencyExportPrompt.error }}</div>
            <div class="prompt-actions">
              <button type="button" :disabled="isBusy" @click="cardDependencyExportPrompt.open = false; cardDependencyExportPrompt.confirmMove = false">取消</button>
              <button type="button" :disabled="isBusy" @click="submitCardDependencyExport">
                {{ isBusy && activeAction === "extract_mods" ? "导出中..." : cardDependencyExportPrompt.confirmMove ? `确认剪切 ${selectedCount} 张人物卡依赖` : `导出 ${selectedCount} 张人物卡依赖` }}
              </button>
            </div>
          </div>
        </div>

        <div v-if="cardMovePrompt.open" class="prompt-backdrop" @click.self="closeCardMovePrompt">
          <div class="prompt-panel card-move-panel" role="dialog" aria-modal="true" aria-labelledby="card-move-title">
            <header class="card-move-head">
              <div>
                <span class="card-move-kicker">{{ cardMovePrompt.sourceGender }} card library</span>
                <strong id="card-move-title">移动人物卡</strong>
              </div>
              <button type="button" :disabled="cardMovePrompt.busy || cardMovePrompt.folderBusy" aria-label="关闭" @click="closeCardMovePrompt">×</button>
            </header>

            <div class="card-move-toolbar">
              <div class="card-move-target">
                <span>目标目录</span>
                <strong class="mono">{{ cardMovePrompt.targetPath || "尚未选择" }}</strong>
              </div>
              <div class="card-move-folder-actions">
                <button type="button" :disabled="!cardMovePrompt.targetPath || cardMovePrompt.folderBusy" @click="beginCardMoveFolderEdit('create')">+ 新建子目录</button>
                <button type="button" :disabled="!cardMovePrompt.targetPath || cardMovePrompt.folderBusy" @click="beginCardMoveFolderEdit('rename')">重命名</button>
              </div>
            </div>

            <form v-if="cardMovePrompt.editMode" class="card-move-edit" @submit.prevent="submitCardMoveFolderEdit">
              <label>
                <span>{{ cardMovePrompt.editMode === 'create' ? '新目录名称' : '新的目录名称' }}</span>
                <input v-model="cardMovePrompt.nameDraft" class="search" type="text" maxlength="120" autofocus :placeholder="cardMovePrompt.editMode === 'create' ? '在当前选中目录下创建' : '输入新名称'">
              </label>
              <button type="button" :disabled="cardMovePrompt.folderBusy" @click="cardMovePrompt.editMode = ''; cardMovePrompt.error = ''">取消</button>
              <button type="submit" :disabled="cardMovePrompt.folderBusy">{{ cardMovePrompt.folderBusy ? '处理中...' : '确认' }}</button>
            </form>

            <div class="card-move-tree" role="tree" :aria-label="`${cardMovePrompt.sourceGender} 人物卡目录`">
              <button
                v-for="folder in cardMoveFolderRows"
                :key="folder.id"
                type="button"
                class="card-move-tree-row"
                :class="{ selected: cardMovePrompt.targetPath === folder.relativePath }"
                :style="{ '--folder-depth': folder.depth }"
                role="treeitem"
                :aria-selected="cardMovePrompt.targetPath === folder.relativePath"
                :aria-expanded="folder.hasChildren ? folder.expanded : undefined"
                @click="selectCardMoveFolder(folder)"
              >
                <span
                  class="card-move-tree-toggle"
                  :class="{ placeholder: !folder.hasChildren }"
                  role="button"
                  :aria-label="folder.hasChildren ? (folder.expanded ? '收起目录' : '展开目录') : undefined"
                  @click.stop="toggleCardMoveFolder(folder)"
                >{{ folder.hasChildren ? (folder.expanded ? '−' : '+') : '' }}</span>
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 7h7l2 2h9v10H3Z" /></svg>
                <span>{{ folder.name }}</span>
                <small>{{ folder.count }}</small>
              </button>
              <div v-if="cardMoveFolderRows.length === 0" class="card-move-empty">未找到可用目录</div>
            </div>

            <div v-if="cardMovePrompt.error" class="prompt-error">{{ cardMovePrompt.error }}</div>
            <div class="prompt-actions card-move-submit">
              <button type="button" :disabled="cardMovePrompt.busy || cardMovePrompt.folderBusy" @click="closeCardMovePrompt">取消</button>
              <button type="button" class="primary" :disabled="!cardMoveDestinationReady || cardMovePrompt.busy || cardMovePrompt.folderBusy" @click="submitBulkMoveCharacterCards">
                {{ cardMovePrompt.busy ? "移动中..." : `移动 ${selectedCount} 张人物卡` }}
              </button>
            </div>
          </div>
        </div>

        <div v-if="cardDeletePrompt.open" class="prompt-backdrop" @click.self="!cardDeletePrompt.busy && (cardDeletePrompt.open = false)">
          <div class="prompt-panel duplicate-delete-confirm-panel" role="dialog" aria-modal="true" aria-labelledby="card-delete-title">
            <span class="risk-kicker">文件将进入回收站</span>
            <strong id="card-delete-title">批量删除人物卡</strong>
            <p class="subtext">将把已选择的 PNG 文件移入 runtime/trash/cards，原目录不会继续保留。</p>
            <div class="prompt-note">
              <span>将要删除</span>
              <strong>{{ selectedCount }} 张人物卡</strong>
            </div>
            <div class="prompt-note">
              <span>所在目录</span>
              <strong class="mono">{{ cardFolderDisplay }}</strong>
            </div>
            <div class="prompt-note">
              <span>可逆性</span>
              <strong>可在回收站恢复或永久删除</strong>
            </div>
            <div v-if="cardDeletePrompt.error" class="prompt-error">{{ cardDeletePrompt.error }}</div>
            <div class="prompt-actions">
              <button type="button" :disabled="cardDeletePrompt.busy" @click="cardDeletePrompt.open = false">取消</button>
              <button type="button" class="danger-action" :disabled="cardDeletePrompt.busy" @click="submitBulkDeleteCharacterCards">
                {{ cardDeletePrompt.busy ? "删除中..." : `确认删除 ${selectedCount} 张人物卡` }}
              </button>
            </div>
          </div>
        </div>

        <div v-if="cardSingleDeletePrompt.open" class="prompt-backdrop" @click.self="!cardSingleDeletePrompt.busy && (cardSingleDeletePrompt.open = false)">
          <div class="prompt-panel duplicate-delete-confirm-panel character-card-delete-confirm-panel" role="dialog" aria-modal="true" aria-labelledby="single-card-delete-title">
            <span class="risk-kicker">文件将进入回收站</span>
            <strong id="single-card-delete-title">删除人物卡</strong>
            <p class="subtext">将把当前人物卡移入 runtime/trash/cards，原目录不会继续保留。</p>
            <div v-if="cardSingleDeletePrompt.card" class="card-load-target character-card-delete-target">
              <img :src="cardSingleDeletePrompt.card.coverUrl" :alt="cardSingleDeletePrompt.card.name + ' preview'">
              <span>
                <small>当前人物卡</small>
                <strong>{{ cardSingleDeletePrompt.card.name }}</strong>
                <small class="mono">{{ cardSingleDeletePrompt.card.relativePath }}</small>
              </span>
            </div>
            <div class="prompt-note">
              <span>将要删除</span>
              <strong>1 张人物卡</strong>
            </div>
            <div class="prompt-note">
              <span>可逆性</span>
              <strong>可在回收站恢复或永久删除</strong>
            </div>
            <div v-if="cardSingleDeletePrompt.error" class="prompt-error" role="alert">{{ cardSingleDeletePrompt.error }}</div>
            <div class="prompt-actions">
              <button type="button" :disabled="cardSingleDeletePrompt.busy" @click="cardSingleDeletePrompt.open = false">取消</button>
              <button type="button" class="danger-action" :disabled="cardSingleDeletePrompt.busy" @click="submitSelectedCardDelete">
                {{ cardSingleDeletePrompt.busy ? "删除中..." : "确认删除人物卡" }}
              </button>
            </div>
          </div>
        </div>

        <div v-if="deleteItemPrompt.open" class="prompt-backdrop" @click.self="deleteItemPrompt.open = false">
          <div class="prompt-panel duplicate-delete-confirm-panel">
            <strong>删除物品</strong>
            <p class="subtext">该操作会写回 zipmod。</p>
            <div class="prompt-note duplicate-delete-keep">
              <span>物品</span>
              <strong>{{ deleteItemPrompt.name }}</strong>
            </div>
            <p class="duplicate-delete-warning">删除后不可由应用自动恢复，请确认后继续。</p>
            <div v-if="deleteItemPrompt.error" class="prompt-error">{{ deleteItemPrompt.error }}</div>
            <div class="prompt-actions">
              <button type="button" :disabled="Boolean(deletingItemId)" @click="deleteItemPrompt.open = false">取消</button>
              <button type="button" class="danger-action" :disabled="Boolean(deletingItemId)" @click="confirmDeleteSelectedItem">
                {{ deletingItemId ? "删除中..." : "确认删除物品" }}
              </button>
            </div>
          </div>
        </div>

        <div v-if="bulkDeleteErrorItemsPrompt.open" class="prompt-backdrop" @click.self="bulkDeleteErrorItemsPrompt.open = false">
          <div class="prompt-panel duplicate-delete-confirm-panel">
            <strong>批量删除错误物品</strong>
            <p class="subtext">将按当前物品浏览筛选条件删除所有错误物品，并写回对应 zipmod。</p>
            <div class="prompt-note duplicate-delete-keep">
              <span>错误物品</span>
              <strong>{{ bulkDeleteErrorItemsPrompt.count }} 个</strong>
            </div>
            <div class="prompt-note duplicate-delete-keep">
              <span>筛选范围</span>
              <strong>{{ itemFilters.search || "全部名称" }} · {{ itemFilters.kind || "全部 Kind" }} · {{ itemFilters.author || "全部作者" }}</strong>
            </div>
            <p class="duplicate-delete-warning">删除后不可由应用自动恢复。若某个物品是 zipmod 内最后一个物品，会连同来源 zipmod 一起删除。</p>
            <div v-if="bulkDeleteErrorItemsPrompt.error" class="prompt-error">{{ bulkDeleteErrorItemsPrompt.error }}</div>
            <div class="prompt-actions">
              <button type="button" :disabled="bulkActionBusy === 'items-delete'" @click="bulkDeleteErrorItemsPrompt.open = false">取消</button>
              <button
                type="button"
                class="danger-action"
                :disabled="bulkActionBusy === 'items-delete' || bulkDeleteErrorItemsPrompt.count <= 0 || bulkDeleteErrorItemsPrompt.count > 1000"
                @click="submitBulkDeleteErrorItems"
              >
                {{ bulkActionBusy === "items-delete" ? "删除中..." : `确认删除 ${bulkDeleteErrorItemsPrompt.count} 个错误物品` }}
              </button>
            </div>
          </div>
        </div>

        <div v-if="deleteModPrompt.open" class="prompt-backdrop" @click.self="deleteModPrompt.open = false">
          <div class="prompt-panel duplicate-delete-confirm-panel">
            <strong>删除模组</strong>
            <p class="subtext">该操作会删除 zipmod 文件。</p>
            <div class="prompt-note duplicate-delete-keep">
              <span>模组</span>
              <strong>{{ deleteModPrompt.name }}</strong>
            </div>
            <p class="duplicate-delete-warning">删除后不可由应用自动恢复，请确认后继续。</p>
            <div v-if="deleteModPrompt.error" class="prompt-error">{{ deleteModPrompt.error }}</div>
            <div class="prompt-actions">
              <button type="button" @click="deleteModPrompt.open = false">取消</button>
              <button type="button" class="danger-action" @click="confirmDeleteSelectedMod">确认删除模组</button>
            </div>
          </div>
        </div>

        <div v-if="missingItemPrompt.open" class="prompt-backdrop" @click.self="missingItemPrompt.open = false">
          <div class="prompt-panel missing-item-panel">
            <div class="missing-item-panel-head">
              <div>
                <span class="missing-item-kicker">DEPENDENCY CHECK</span>
                <strong>{{ missingItemPrompt.kind === 'mod' ? '模组缺失' : '物品缺失' }}</strong>
              </div>
              <span class="missing-item-alert-mark">!</span>
            </div>
            <p class="subtext">{{ missingItemPrompt.kind === 'mod' ? '当前场景卡依赖的模组没有在本地模组数据库中匹配到。' : '当前卡片依赖的物品没有在本地物品数据库中匹配到。' }}</p>
            <div class="prompt-note missing-item-note">
              <span>{{ missingItemPrompt.kind === 'mod' ? '模组' : '物品' }}</span>
              <strong>{{ missingItemPrompt.name }}</strong>
            </div>
            <div v-if="missingItemPrompt.modId" class="prompt-note">
              <span>ModID</span>
              <strong>{{ missingItemPrompt.modId }}</strong>
            </div>
            <div v-if="missingItemPrompt.property" class="prompt-note">
              <span>属性</span>
              <strong>{{ missingItemPrompt.property }}</strong>
            </div>
            <section v-if="missingItemPrompt.modId" class="missing-item-remote-card">
              <div class="missing-item-remote-head">
                <div>
                  <span class="missing-item-kicker remote-kicker">REMOTE INDEX</span>
                  <strong>远端模组信息</strong>
                </div>
                <span
                  class="missing-item-remote-status"
                  :class="missingItemPrompt.remoteLoading ? 'loading' : (missingItemPrompt.remoteCandidate ? 'available' : 'unavailable')"
                >
                  {{ missingItemPrompt.remoteLoading ? '查询中' : (missingItemPrompt.remoteCandidate ? '可下载' : '无法获取') }}
                </span>
              </div>
              <div v-if="missingItemPrompt.remoteLoading" class="missing-item-remote-loading">
                正在从远程索引读取模组信息…
              </div>
              <template v-else-if="missingItemPrompt.remoteCandidate">
                <div class="missing-item-remote-name">
                  {{ missingItemPrompt.remoteCandidate.name || missingItemPrompt.remoteCandidate.file_name || '未命名模组' }}
                </div>
                <div class="missing-item-remote-grid two-column-grid">
                  <div>
                    <span>作者</span>
                    <strong>{{ missingItemPrompt.remoteCandidate.author || '未知作者' }}</strong>
                  </div>
                  <div>
                    <span>版本</span>
                    <strong>{{ missingItemPrompt.remoteCandidate.version || '未标注' }}</strong>
                  </div>
                  <div>
                    <span>文件大小</span>
                    <strong>{{ formatBytes(missingItemPrompt.remoteCandidate.file_size) }}</strong>
                  </div>
                  <div>
                    <span>候选版本</span>
                    <strong>{{ missingItemPrompt.remoteEntry?.candidate_count || missingItemPrompt.remoteEntry?.candidates?.length || 1 }} 个</strong>
                  </div>
                </div>
                <div class="missing-item-remote-file">
                  <span>文件</span>
                  <code>{{ missingItemPrompt.remoteCandidate.file_name || '-' }}</code>
                </div>
                <div v-if="missingItemPrompt.remoteCandidate.relative_path" class="missing-item-remote-file">
                  <span>远程路径</span>
                  <code>{{ missingItemPrompt.remoteCandidate.relative_path }}</code>
                </div>
              </template>
              <div v-else class="missing-item-remote-empty">
                <strong>{{ missingItemPrompt.remoteError ? '远程索引查询失败' : '远程索引中没有可下载模组' }}</strong>
                <span>{{ missingItemPrompt.remoteError || missingItemPrompt.remoteEntry?.reason || '该 ModID 暂无有效的 manifest 记录。' }}</span>
              </div>
            </section>
            <div class="prompt-actions">
              <button type="button" @click="missingItemPrompt.open = false">确定</button>
            </div>
          </div>
        </div>

        <div v-if="manifestAuthorPrompt.open" class="prompt-backdrop" @click.self="manifestAuthorPrompt.open = false">
          <div class="prompt-panel">
            <strong>补充作者</strong>
            <p class="subtext">输入后将写入对应 zipmod 的 manifest.xml。</p>
            <input
              v-model="manifestAuthorPrompt.value"
              class="search"
              type="text"
              placeholder="请输入作者名称"
              list="zipmod-author-list"
              @keydown.enter="submitManifestAuthor"
            >
            <div v-if="manifestAuthorPrompt.error" class="prompt-error">{{ manifestAuthorPrompt.error }}</div>
            <div class="prompt-actions">
              <button type="button" @click="manifestAuthorPrompt.open = false">取消</button>
              <button type="button" :disabled="manifestAuthorPrompt.busy" @click="submitManifestAuthor">
                {{ manifestAuthorPrompt.busy ? "保存中..." : "保存作者" }}
              </button>
            </div>
          </div>
        </div>

        <div v-if="duplicateZipmodPrompt.open" class="prompt-backdrop" @click.self="duplicateZipmodPrompt.open = false">
          <div class="prompt-panel duplicate-zipmod-panel">
            <strong>清理重复模组</strong>
            <div v-if="duplicateZipmodPrompt.analysisLoading" class="detail-inline-state">正在分析重复模组...</div>
            <div v-if="duplicateZipmodPrompt.analysis" class="duplicate-analysis">
              <div class="duplicate-analysis-list">
                <article
                  v-for="candidate in duplicateZipmodPrompt.analysis.candidates"
                  :key="candidate.role + ':' + (candidate.duplicate_id || 'primary')"
                  class="duplicate-analysis-card"
                  :class="{
                    recommended: candidate.recommended_action === 'keep',
                    delete: candidate.recommended_action === 'delete',
                    merge: candidate.recommended_action === 'merge',
                    review: candidate.recommended_action === 'review'
                  }"
                >
                  <div class="duplicate-analysis-head">
                    <div class="duplicate-analysis-title">
                      <strong>{{ candidate.role === "primary" ? "当前主记录" : "重复文件" }}</strong>
                      <span v-if="candidate.recommended_action" class="badge" :class="candidate.recommended_action === 'delete' ? 'danger' : candidate.recommended_action === 'keep' ? 'success' : 'warn'">
                        {{ candidate.recommended_action === "keep" ? "推荐保留" : candidate.recommended_action === "delete" ? "建议删除" : candidate.recommended_action === "merge" ? "建议合并" : "需要复核" }}
                      </span>
                      <span v-else-if="candidate.recommendation_reasons?.includes('most_complete') || candidate.recommendation_reasons?.includes('latest_version')" class="badge warn">
                        {{ candidate.recommendation_reasons.includes("most_complete") ? "最完整" : "最新版本" }}
                      </span>
                    </div>
                    <button
                      type="button"
                      class="keep-action"
                      :disabled="duplicateZipmodPrompt.busyAll || duplicateZipmodPrompt.busyId"
                      @click="openDuplicateZipmodDeleteConfirm(candidate)"
                    >
                      保留此项
                    </button>
                  </div>
                  <button
                    type="button"
                    class="duplicate-analysis-path"
                    :title="candidate.file_path"
                    @click="openDuplicateZipmodInFolder(candidate)"
                  >
                    {{ candidate.file_path }}
                  </button>
                  <div class="duplicate-analysis-grid">
                    <span v-if="duplicatePrimaryReason(candidate)" class="duplicate-primary-reason">
                      首要理由 <strong>{{ duplicatePrimaryReason(candidate) }}</strong>
                    </span>
                    <span>版本 <strong>{{ candidate.version || "-" }}</strong></span>
                    <span>作者 <strong>{{ candidate.author || "-" }}</strong></span>
                    <span>大小 <strong>{{ formatBytes(candidate.file_size) }}</strong></span>
                    <span>修改 <strong>{{ candidate.modified_at || "-" }}</strong></span>
                    <span>物品 <strong>{{ candidate.ok_item_count }}/{{ candidate.item_count }}</strong></span>
                    <span>缺少物品 <strong>{{ candidate.missing_item_count_vs_union }}</strong></span>
                    <span>独有物品 <strong>{{ candidate.unique_item_count }}</strong></span>
                    <span>完整度 <strong>{{ candidate.completeness_score }}</strong></span>
                    <span>引用 Unity3D <strong>{{ candidate.unity3d_member_count }}/{{ candidate.unity3d_referenced_member_count }}</strong></span>
                    <span>Unity3D 平均修改 <strong>{{ candidate.unity3d_average_modified_at || "-" }}</strong></span>
                    <span>缩略图问题 <strong>{{ candidate.thumbnail_issue_count }}</strong></span>
                    <span>解析错误 <strong>{{ candidate.parse_error_count }}</strong></span>
                  </div>
                  <div v-if="candidate.sample_items?.length" class="duplicate-analysis-items">
                    <span v-for="item in candidate.sample_items" :key="item.csv_path + ':' + item.item_id" class="badge neutral">
                      {{ item.name || item.item_id }}
                    </span>
                  </div>
                  <p v-if="candidate.scan_error" class="prompt-error">{{ candidate.scan_error }}</p>
                  <p v-if="candidate.unity3d_signature_error" class="prompt-error">{{ candidate.unity3d_signature_error }}</p>
                </article>
              </div>
            </div>
            <div v-if="duplicateZipmodPrompt.error" class="prompt-error">{{ duplicateZipmodPrompt.error }}</div>
            <div class="prompt-actions">
              <button type="button" :disabled="duplicateZipmodPrompt.busyAll || duplicateZipmodPrompt.busyId" @click="duplicateZipmodPrompt.open = false">取消</button>
              <button
                type="button"
                :class="duplicateHasRecommendedMerge ? 'merge-action' : 'danger-action'"
                :disabled="!duplicateRecommendedKeep || duplicateZipmodPrompt.analysisLoading || duplicateZipmodPrompt.busyAll || duplicateZipmodPrompt.busyId"
                @click="cleanupAllExceptRecommendedZipmod"
              >
                {{ duplicateZipmodPrompt.busyAll ? "处理中..." : duplicateHasRecommendedMerge ? "合并重复模组" : "删除重复模组" }}
              </button>
            </div>
          </div>
        </div>

        <div v-if="duplicateZipmodDeleteConfirm.open" class="prompt-backdrop" @click.self="duplicateZipmodDeleteConfirm.open = false">
          <div class="prompt-panel duplicate-delete-confirm-panel">
            <strong>确认删除重复模组</strong>
            <p class="subtext">将删除当前模组中除所选保留项外的所有重复 zipmod。</p>
            <div class="prompt-note duplicate-delete-keep">
              <span>所选保留</span>
              <strong>{{ duplicateZipmodDeleteConfirm.keepLabel }}</strong>
            </div>
            <p class="duplicate-delete-warning">删除文件不可由应用自动恢复，请确认后继续。</p>
            <div class="prompt-actions">
              <button type="button" :disabled="duplicateZipmodPrompt.busyAll" @click="duplicateZipmodDeleteConfirm.open = false">取消</button>
              <button
                type="button"
                class="danger-action"
                :disabled="duplicateZipmodPrompt.busyAll"
                @click="confirmKeepDuplicateZipmodCandidate"
              >
                {{ duplicateZipmodPrompt.busyAll ? "删除中..." : "删除重复模组" }}
              </button>
            </div>
          </div>
        </div>

        <div v-if="manifestEditor.open" class="prompt-backdrop" @click.self="manifestEditor.open = false">
          <div class="prompt-panel manifest-editor-panel">
            <strong>修改 manifest</strong>
            <p class="subtext">编辑当前 zipmod 的 manifest.xml 基础字段。</p>
            <div v-if="manifestEditor.loading" class="detail-inline-state">正在读取 manifest...</div>
            <div v-else class="manifest-field-list">
              <label class="manifest-field">
                <span>包标识</span>
                <strong class="manifest-locked-value">{{ manifestEditor.fields.guid || "-" }}</strong>
              </label>
              <label class="manifest-field">
                <span>名称</span>
                <input v-model="manifestEditor.fields.name" class="search" type="text" autocomplete="off">
              </label>
              <label class="manifest-field">
                <span>版本</span>
                <input v-model="manifestEditor.fields.version" class="search" type="text" autocomplete="off">
              </label>
              <label class="manifest-field">
                <span>作者</span>
                <input
                  v-model="manifestEditor.fields.author"
                  class="search"
                  type="text"
                  autocomplete="off"
                  list="zipmod-author-list"
                  @keydown.enter="submitManifestEditor"
                >
              </label>
            </div>
            <div v-if="manifestEditor.error" class="prompt-error">{{ manifestEditor.error }}</div>
            <div class="prompt-actions">
              <button type="button" :disabled="manifestEditor.busy" @click="manifestEditor.open = false">取消</button>
              <button type="button" :disabled="manifestEditor.loading || manifestEditor.busy" @click="submitManifestEditor">
                {{ manifestEditor.busy ? "保存中..." : "保存 manifest" }}
              </button>
            </div>
          </div>
        </div>

        <div v-if="bulkAuthorPrompt.open" class="prompt-backdrop" @click.self="bulkAuthorPrompt.open = false">
          <div class="prompt-panel">
            <strong>批量修改作者</strong>
            <p class="subtext">将作者名写入已选 zipmod 的 manifest.xml。</p>
            <div class="author-combobox prompt-author-combobox">
              <input
                v-model="bulkAuthorPrompt.value"
                class="search"
                type="text"
                placeholder="请输入作者名称"
                autocomplete="off"
                spellcheck="false"
                autofocus
                @keydown.enter="bulkUpdateModAuthors"
              >
              <div
                v-if="bulkAuthorSuggestions.length > 0"
                class="author-option-list prompt-author-option-list"
                role="listbox"
              >
                <button
                  v-for="author in bulkAuthorSuggestions"
                  :key="author"
                  type="button"
                  :class="{ active: bulkAuthorPrompt.value === author }"
                  @mousedown.prevent="selectBulkAuthorSuggestion(author)"
                >
                  {{ author }}
                </button>
              </div>
            </div>
            <div v-if="bulkAuthorPrompt.error" class="prompt-error">{{ bulkAuthorPrompt.error }}</div>
            <div class="prompt-actions">
              <button type="button" :disabled="bulkActionBusy === 'author'" @click="bulkAuthorPrompt.open = false">取消</button>
              <button type="button" :disabled="bulkActionBusy === 'author'" @click="bulkUpdateModAuthors">
                {{ bulkActionBusy === "author" ? "修改中..." : `修改 ${selectedModCount} 个模组作者` }}
              </button>
            </div>
          </div>
        </div>

        <div v-if="bulkUnity3dPrompt.open" class="prompt-backdrop" @click.self="bulkUnity3dPrompt.open = false">
          <div class="prompt-panel">
            <strong>批量补入 unity3d</strong>
            <p class="subtext">将诊断为在游戏目录中的 unity3d 文件补入已选 zipmod；共享文件会复制，独占文件才会移入。</p>
            <div class="prompt-note">
              <span>已选模组</span>
              <strong>{{ selectedModCount }} 个</strong>
            </div>
            <div class="prompt-actions">
              <button type="button" :disabled="bulkActionBusy === 'unity3d'" @click="bulkUnity3dPrompt.open = false">取消</button>
              <button type="button" :disabled="bulkActionBusy === 'unity3d'" @click="submitBulkRepairUnity3dFromGame">
                {{ bulkActionBusy === "unity3d" ? "补入中..." : `补入 ${selectedModCount} 个模组` }}
              </button>
            </div>
          </div>
        </div>

        <div v-if="bulkDuplicateCleanupPrompt.open" class="prompt-backdrop" @click.self="bulkDuplicateCleanupPrompt.open = false">
          <div class="prompt-panel">
            <strong>智能清理重复模组</strong>
            <p class="subtext">对已选模组逐个分析重复 GUID 候选，并清理安全项。</p>
            <div class="prompt-note">
              <span>将改变</span>
              <strong>删除通过分析判定安全的重复 zipmod 文件</strong>
            </div>
            <div class="prompt-note">
              <span>不会改变</span>
              <strong>当前主记录 zipmod 与需要人工判断的重复项</strong>
            </div>
            <div class="prompt-note">
              <span>可逆性</span>
              <strong>删除文件不可由应用自动恢复</strong>
            </div>
            <div v-if="bulkDuplicateCleanupPrompt.error" class="prompt-error">{{ bulkDuplicateCleanupPrompt.error }}</div>
            <div class="prompt-actions">
              <button type="button" :disabled="bulkActionBusy === 'duplicates'" @click="bulkDuplicateCleanupPrompt.open = false">取消</button>
              <button type="button" class="danger-action" :disabled="bulkActionBusy === 'duplicates'" @click="submitBulkDuplicateCleanup">
                {{ bulkActionBusy === "duplicates" ? "分析清理中..." : `确认智能清理 ${selectedModCount} 个已选模组` }}
              </button>
            </div>
          </div>
        </div>

        <div v-if="bulkDeletePrompt.open" class="prompt-backdrop" @click.self="bulkDeletePrompt.open = false">
          <div class="prompt-panel">
            <strong>批量删除模组</strong>
            <p class="subtext">将已选 zipmod 文件移入 runtime/trash/mods，并移除相关数据库记录。</p>
            <div class="prompt-note">
              <span>将要改变</span>
              <strong>删除 {{ selectedModCount }} 个已选 zipmod 文件</strong>
            </div>
            <div class="prompt-note">
              <span>可逆性</span>
              <strong>可在回收站恢复或永久删除</strong>
            </div>
            <div class="prompt-note">
              <span>更安全替代</span>
              <strong>先用导出功能备份到其它目录</strong>
            </div>
            <div v-if="bulkDeletePrompt.error" class="prompt-error">{{ bulkDeletePrompt.error }}</div>
            <div class="prompt-actions">
              <button type="button" :disabled="bulkActionBusy === 'delete'" @click="bulkDeletePrompt.open = false">取消</button>
              <button type="button" class="danger-action" :disabled="bulkActionBusy === 'delete'" @click="submitBulkDeleteZipmods">
                {{ bulkActionBusy === "delete" ? "删除中..." : `确认删除 ${selectedModCount} 个 zipmod` }}
              </button>
            </div>
          </div>
        </div>

        <div v-if="bulkOrganizePrompt.open" class="prompt-backdrop" @click.self="bulkOrganizePrompt.open = false">
          <div class="prompt-panel">
            <strong>按作者整理已选模组</strong>
            <p class="subtext">选择目录后，会按模组作者创建子目录并复制已选 zipmod。</p>
            <div class="prompt-field-row">
              <input
                v-model="bulkOrganizePrompt.targetDir"
                class="search"
                type="text"
                placeholder="请选择整理目录"
                readonly
              >
              <button type="button" :disabled="bulkActionBusy === 'organize'" @click="selectBulkOrganizeDir">选择目录</button>
            </div>
            <div v-if="bulkOrganizePrompt.error" class="prompt-error">{{ bulkOrganizePrompt.error }}</div>
            <div class="prompt-actions">
              <button type="button" :disabled="bulkActionBusy === 'organize'" @click="bulkOrganizePrompt.open = false">取消</button>
              <button type="button" :disabled="bulkActionBusy === 'organize'" @click="submitBulkOrganize">
                {{ bulkActionBusy === "organize" ? "整理中..." : `整理 ${selectedModCount} 个模组` }}
              </button>
            </div>
          </div>
        </div>

        <div v-if="bulkExportPrompt.open" class="prompt-backdrop" @click.self="bulkExportPrompt.open = false">
          <div class="prompt-panel">
            <strong>导出已选模组</strong>
            <p class="subtext">将已选 zipmod 导出到指定目录，并保留原 mods 下的相对路径。</p>
            <div class="prompt-field-row">
              <input
                v-model="bulkExportPrompt.targetDir"
                class="search"
                type="text"
                placeholder="请选择导出目录"
                readonly
              >
              <button type="button" :disabled="bulkActionBusy === 'export'" @click="selectBulkExportDir">选择目录</button>
            </div>
            <div class="export-mode-group two-column-grid" role="radiogroup" aria-label="导出方式">
              <label>
                <input v-model="bulkExportPrompt.mode" type="radio" value="copy" @change="bulkExportPrompt.confirmMove = false">
                <span>复制</span>
              </label>
              <label>
                <input v-model="bulkExportPrompt.mode" type="radio" value="move" @change="bulkExportPrompt.confirmMove = false">
                <span>剪切</span>
              </label>
            </div>
            <div v-if="bulkExportPrompt.confirmMove" class="prompt-error">
              将剪切 {{ selectedModCount }} 个 zipmod，原文件会被移动。请再次确认。
            </div>
            <div v-if="bulkExportPrompt.error" class="prompt-error">{{ bulkExportPrompt.error }}</div>
            <div class="prompt-actions">
              <button type="button" :disabled="bulkActionBusy === 'export'" @click="bulkExportPrompt.open = false; bulkExportPrompt.confirmMove = false">取消</button>
              <button type="button" :disabled="bulkActionBusy === 'export'" @click="submitBulkExport">
                {{ bulkActionBusy === "export" ? "导出中..." : bulkExportPrompt.confirmMove ? `确认剪切 ${selectedModCount} 个模组` : `导出 ${selectedModCount} 个模组` }}
              </button>
            </div>
          </div>
        </div>

        <div v-if="thumbnailToolsPrompt.open" class="prompt-backdrop" @click.self="thumbnailToolsPrompt.open = false">
          <div class="prompt-panel thumbnail-tools-panel">
            <strong>导出缩略图</strong>
            <p class="subtext">以当前选中的单个物品作为缩略图来源，可导出到目录，也可导入到缺失缩略图的物品。</p>
            <div class="prompt-note">
              <span>来源物品</span>
              <strong>{{ selectedItem?.name || "-" }}</strong>
            </div>
            <div class="thumbnail-tool-block">
              <span class="drawer-section-title">导出当前物品</span>
              <div class="prompt-field-row">
                <input
                  v-model="thumbnailToolsPrompt.targetDir"
                  class="search"
                  type="text"
                  placeholder="请选择缩略图导出目录"
                  readonly
                >
                <button type="button" :disabled="Boolean(bulkActionBusy)" @click="selectThumbnailToolDir">选择目录</button>
              </div>
              <button type="button" :disabled="Boolean(bulkActionBusy)" @click="exportCurrentItemThumbnail">
                {{ bulkActionBusy === "thumb-export" ? "导出中..." : "导出该物品缩略图" }}
              </button>
            </div>
            <div class="thumbnail-tool-block">
              <div class="thumbnail-target-head flex-between">
                <span class="drawer-section-title">导入到缺失物品</span>
                <button type="button" :disabled="Boolean(bulkActionBusy) || missingThumbnailTargetItems.length === 0" @click="setAllThumbnailTargets(selectedThumbnailTargetCount !== missingThumbnailTargetItems.length)">
                  {{ selectedThumbnailTargetCount === missingThumbnailTargetItems.length && missingThumbnailTargetItems.length > 0 ? "清空" : "全选" }}
                </button>
              </div>
              <div v-if="missingThumbnailTargetItems.length === 0" class="detail-inline-state">当前已加载列表中没有缺失缩略图的物品</div>
              <div v-else class="thumbnail-target-list">
                <label v-for="item in missingThumbnailTargetItems" :key="item.id" class="thumbnail-target-item">
                  <input
                    type="checkbox"
                    :checked="thumbnailToolsPrompt.selectedTargetIds.has(Number(item.id))"
                    :disabled="Boolean(bulkActionBusy)"
                    @change="toggleThumbnailTarget(item)"
                  >
                  <span>
                    <strong>{{ item.name }}</strong>
                    <small>{{ item.kind }} · {{ item.author }} · {{ item.sourceMod }}</small>
                  </span>
                </label>
              </div>
              <button type="button" :disabled="Boolean(bulkActionBusy) || selectedThumbnailTargetCount === 0" @click="applyCurrentThumbnailToTargets">
                {{ bulkActionBusy === "thumb-import" ? "导入中..." : `导入到 ${selectedThumbnailTargetCount} 个缺失物品` }}
              </button>
            </div>
            <div v-if="thumbnailToolsPrompt.error" class="prompt-error">{{ thumbnailToolsPrompt.error }}</div>
            <div class="prompt-actions">
              <button type="button" :disabled="Boolean(bulkActionBusy)" @click="thumbnailToolsPrompt.open = false">取消</button>
            </div>
          </div>
        </div>

        <datalist id="zipmod-author-list">
          <option v-for="author in zipmodAuthors" :key="author" :value="author" />
        </datalist>

        <button v-if="achievementToast" class="achievement-toast" type="button" @click="activeView = 'overview'; selectedAchievement = achievementToast; achievementToast = null">
          <span class="achievement-medal">
            <img v-if="getAchievementIcon(achievementToast)" :src="getAchievementIcon(achievementToast)" :alt="`${achievementToast.title}图标`">
            <span v-else>{{ achievementToast.icon }}</span>
          </span>
          <span class="achievement-toast-copy">
            <span class="achievement-toast-kicker">成就解锁</span>
            <strong>{{ achievementToast.title }}</strong>
            <span class="achievement-toast-description">{{ achievementToast.description }}</span>
          </span>
          <span class="achievement-toast-arrow" aria-hidden="true">→</span>
        </button>

    </main>
  </div>
</template>

