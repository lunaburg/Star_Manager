<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import StartView from "./components/views/StartView.vue";
import OverviewView from "./components/views/OverviewView.vue";
import CharactersView from "./components/views/CharactersView.vue";
import ModsView from "./components/views/ModsView.vue";
import PluginsView from "./components/views/PluginsView.vue";
import LogsView from "./components/views/LogsView.vue";
import appIcon from "../build-resources/app-icon.png";
import brandLogo from "../build-resources/brand-logo.png";

const views = [
  { id: "start", icon: "ST", label: "开始游戏" },
  { id: "overview", icon: "OV", label: "总览" },
  { id: "characters", icon: "CH", label: "角色管理" },
  { id: "mods", icon: "MD", label: "模组管理" },
  { id: "plugins", icon: "PL", label: "插件管理" },
  { id: "logs", icon: "LG", label: "运行日志" }
];

const activeView = ref("start");
const libraryMode = ref("mods");
const itemTab = ref("详情");
const modTab = ref("详情");
const cardDetailTab = ref("详情");
const selectedCards = ref(new Set());
const backendStatus = ref("checking");
const gameDirStatus = ref("未选择");
const taskName = ref("等待任务");
const progress = ref(0);
const taskId = ref("idle");
const taskHint = ref("请选择有效目录后点击重建");
const extractMode = ref("copy");
const isBusy = ref(false);
const activeAction = ref("");

const paths = reactive({
  gameDir: "",
  inputDir: "",
  outputDir: ""
});

const setup = reactive({
  language: "中文",
  quality: "?",
  display: "Display 0",
  resolution: "1920 x 1080",
  fullscreen: false,
  dirty: false
});

const stats = reactive({
  cards: null,
  zipmods: null,
  missingZipmods: null,
  missingAbdata: null,
  zipmodErrors: null,
  zipmodWarnings: null,
  modItems: null,
  duplicateZipmods: null,
  lastDatabaseBuiltAt: ""
});

const logs = ref([]);
const seenTaskMessages = ref(new Set());
const recentTasks = ref([]);
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
const selectedCardFolder = ref("");
const selectedCardDetailPath = ref("");
const characterSideMode = ref("tree");
const cardBulkMode = ref(false);
const selectedCardProfile = ref(null);
const selectedCardDependencies = ref([]);
const selectedCardProfileLoading = ref(false);
const settingNaviSlot = ref("");
const naviActionNotice = reactive({ type: "", message: "" });
const selectedCardProfileError = ref("");
const cardLibrary = reactive({
  checked: false,
  loading: false,
  error: "",
  validGameDir: false,
  root: ""
});

const ITEM_PAGE_SIZE = 500;
const MOD_PAGE_SIZE = 200;
const UNKNOWN_AUTHOR_LABEL = "未知作者";
const POSE_ITEM_KIND_CODES = new Set(["500", "501"]);
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
const ITEM_KIND_LABELS = {
  8: "男/身体/人体彩绘",
  110: "男/面部/眼睛",
  111: "男/面部/眉毛",
  112: "男/面部/睫毛",
  121: "男/面部/胡子",
  131: "男/面部/腮红",
  132: "男/面部/口红",
  133: "男/面部/痣",
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
const itemRows = ref([]);
const modRows = ref([]);
const selectedItem = ref(null);
const selectedMod = ref(null);
const modBulkMode = ref(false);
const selectedModIds = ref(new Set());
const modAuthorFilterOpen = ref(false);
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
  status: ""
});
let itemFilterTimer = null;
let modFilterTimer = null;
let itemRowsRequestSeq = 0;
const repairingUnity3dPath = ref("");
const repairingThumbnailItemId = ref(null);
const exportingFbxItemId = ref(null);
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
  name: "",
  modId: "",
  property: ""
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
const selectedCardDetail = computed(() => {
  return cards.value.find((card) => card.absolutePath === selectedCardDetailPath.value) || null;
});
const visibleCardPaths = computed(() => cards.value.map((card) => card.absolutePath).filter(Boolean));
const visibleSelectedCardCount = computed(() => visibleCardPaths.value.filter((path) => selectedCards.value.has(path)).length);
const allVisibleCardsSelected = computed(() => visibleCardPaths.value.length > 0 && visibleSelectedCardCount.value === visibleCardPaths.value.length);
const someVisibleCardsSelected = computed(() => visibleSelectedCardCount.value > 0 && !allVisibleCardsSelected.value);
const gameDirDisplay = computed(() => paths.gameDir || "D:\\HoneySelect2");
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
        note: item.source_path ? `来源：${item.source_path}` : "已复制到 UserData/chara/female"
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
  ];
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
const itemKindOptions = computed(() => {
  const genderOrder = { male: 0, female: 1, neutral: 2 };
  const categoryOrder = {
    "\u9762\u90e8": 0,
    "\u8eab\u4f53": 1,
    "\u670d\u9970": 2,
    "\u5934\u53d1": 3,
    "\u9970\u54c1": 4
  };
  const options = itemFilterKinds.value.map((kind, sourceIndex) => {
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
      caption: "AIS PNG",
      action: "characters"
    });
  }
  if (modDatabase.checked && modDatabase.exists && Number.isFinite(stats.zipmods)) {
    cards.push({
      key: "zipmods",
      label: "模组",
      value: stats.zipmods,
      caption: "本地索引",
      action: "mods",
      libraryMode: "mods"
    });
  }
  if (itemDatabase.checked && itemDatabase.exists && Number.isFinite(stats.modItems)) {
    cards.push({
      key: "items",
      label: "物品",
      value: stats.modItems,
      caption: "模组物品",
      action: "mods",
      libraryMode: "items"
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

async function refreshCharacterCardsAfterDatabaseBuild() {
  if (!backendReady.value || !paths.gameDir || !cardLibrary.checked) return;
  await loadCardTree();
}

function badgeClass(value) {
  if (value === "警告") return "warn";
  if (["ready", "正常", "Done", "目录有效"].includes(value)) return "ok";
  if (["thumb", "missing", "重复标识", "42%"].includes(value)) return "warn";
  if (["error", "parse", "错误", "读取失败", "Error"].includes(value)) return "danger";
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
  if (task.status === "failed") return "Error";
  return formatProgressPercent(task.progress);
}

function taskStatusClass(task) {
  if (task.status === "completed") return "ok";
  if (task.status === "failed") return "danger";
  return "warn";
}

function latestTaskMessage(task) {
  const messages = Array.isArray(task?.messages) ? task.messages : [];
  return messages.length ? String(messages[messages.length - 1] || "") : "";
}

function databaseTaskHint(task) {
  const message = latestTaskMessage(task);
  const prepared = message.match(/^Prepared (\d+)\/(\d+) primary zipmods/);
  if (prepared) return `提取物品与缩略图 ${prepared[1]}/${prepared[2]}`;

  const indexed = message.match(/^Indexed (\d+)\/(\d+) zipmods; (\d+) items/);
  if (indexed) return `已索引 ${indexed[1]}/${indexed[2]} 个 zipmod，${indexed[3]} 个物品`;

  const found = message.match(/^Found (\d+) zipmod files/);
  if (found) return `找到 ${found[1]} 个 zipmod 文件`;

  const cardIndexed = message.match(/^Indexed (\d+)\/(\d+) character cards/);
  if (cardIndexed) return `已索引人物卡依赖 ${cardIndexed[1]}/${cardIndexed[2]}`;

  const preparing = message.match(/^Preparing (\d+) primary zipmods/);
  if (preparing) return `准备解析 ${preparing[1]} 个主 zipmod`;

  if (message.startsWith("Building character card database")) return "正在构建人物卡依赖库";
  if (message.startsWith("Character card database rebuild completed")) return "人物卡数据库已创建";
  if (message.startsWith("Scanning UserData/chara")) return "扫描人物卡";
  if (message.startsWith("Scanning ")) return "扫描 zipmod 文件";
  if (message.startsWith("Prepared zipmod items")) return "物品数据已准备";
  if (message.startsWith("Finalizing ")) return "正在收尾";
  if (message.startsWith("Database rebuild completed")) return "数据库已创建";
  if (message.startsWith("Building mod database")) return "正在读取游戏目录";
  return "正在处理";
}

function taskSummary(task) {
  if (task.task_type === "extract_mods") {
    const count = task.data?.card_paths?.length ?? task.data?.card_count ?? selectedCount.value;
    return `${count} 张人物卡 · ${String(extractMode.value || "copy").toUpperCase()} 模式`;
  }
  if (task.task_type === "build_mod_database") {
    const zipmods = task.data?.stats?.primary_zipmods;
    return zipmods ? `已索引 ${zipmods} 个 zipmod` : taskHint.value;
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
  if (task.task_type === "import_external_zipmods") {
    return `导入 ${task.data?.imported_count ?? 0} 个，替换 ${task.data?.promoted_count ?? 0} 个，补入 ${task.data?.unity3d_repaired_count ?? 0} 个 unity3d，角色卡 ${task.data?.card_imported_count ?? 0} 张`;
  }
  if (task.task_type === "bulk_update_zipmod_authors") {
    return `已更新 ${task.data?.updated_count ?? 0} 个`;
  }
  if (task.task_type === "bulk_apply_item_thumbnail") {
    return `已导入 ${task.data?.imported_count ?? 0} 个`;
  }
  if (task.task_type === "check_game_dir") {
    return task.data?.is_valid ? "目录有效" : "目录无效";
  }
  if (task.task_type === "search_cards") {
    return `找到 ${task.data?.card_count ?? 0} 张人物卡`;
  }
  return task.status || "等待执行";
}

function rememberTask(task) {
  if (!task?.id) return;
  const item = {
    id: task.id,
    title: task.title || task.task_type || "任务",
    summary: taskSummary(task),
    label: taskStatusLabel(task),
    badgeClass: taskStatusClass(task)
  };
  recentTasks.value = [item, ...recentTasks.value.filter((entry) => entry.id !== item.id)].slice(0, 5);
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
    expandedCardFolders.value = new Set([""]);
    refreshVisibleCardFolders();
    stats.cards = Number(result.total || 0);
    await selectCardFolder(selectedCardFolder.value);
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
    cards.value = (result.cards || []).map((card) => ({
      id: card.id,
      name: card.name || card.filename,
      filename: card.filename,
      absolutePath: card.absolute_path,
      relativePath: card.relative_path,
      thumbnailUrl: backendAssetUrl(card.thumbnail_url),
      modifiedAt: card.modified_at ? new Date(card.modified_at * 1000).toLocaleDateString() : ""
    }));
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

function itemFallbackThumbnailUrl(kind) {
  return POSE_ITEM_THUMBNAILS[String(kind || "").trim()] || "";
}

function normalizeItemStatus(status, thumbnailStatus, unity3dStatus = "", kind = "") {
  if (unity3dStatus === "missing" || unity3dStatus === "error") return "error";
  if (status && status !== "ok") return "parse";
  if (isPoseItemKind(kind)) return "ready";
  if (thumbnailStatus && thumbnailStatus !== "ready" && thumbnailStatus !== "ok") return "thumb";
  return "ready";
}

function itemKindLabel(kind) {
  const key = String(kind || "").trim();
  const label = ITEM_KIND_LABELS[key] || key || "-";
  if (label.startsWith("\u7537")) return `\u2642${label.slice(1)}`;
  if (label.startsWith("\u5973")) return `\u2640${label.slice(1)}`;
  return label;
}

function mapModItemRow(row) {
  const thumbnailUrl = backendAssetUrl(row.thumbnail_url) || itemFallbackThumbnailUrl(row.kind);
  return {
    id: row.id,
    zipmodId: row.zipmod_id,
    status: normalizeItemStatus(row.status, row.thumbnail_status, row.unity3d_status, row.kind),
    name: row.name || `(item ${row.item_id || row.id})`,
    kind: itemKindLabel(row.kind),
    kindCode: row.kind || "",
    author: row.author || "-",
    sourceMod: row.source_mod || row.zipmod_guid || "-",
    thumbnailUrl,
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
    usage: String(dependencyUsageFilter.value || "")
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
    unity3dStatus === "in_game" ||
    Number(row?.unity3d_in_game_count || 0) > 0 ||
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
    const result = await window.desktopApi?.backendRequest?.("/mods/items/filters");
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

function selectItem(row) {
  selectedItem.value = row;
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

function showMissingItemPrompt(dependency) {
  const name = dependency?.item?.name || dependency?.name || dependency?.mod_id || "未知物品";
  missingItemPrompt.name = name;
  missingItemPrompt.modId = dependency?.mod_id || dependency?.item?.zipmod_guid || "";
  missingItemPrompt.property = dependency?.property || "";
  missingItemPrompt.open = true;
  log(`[Cards] 物品缺失：${name}`);
}

async function locateSourceMod(row = selectedItem.value) {
  if (!row) return;
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
  await ensureModDatabaseLoaded({ force: true });

  let target = modRows.value.find((mod) => Number(mod.id) === zipmodId);
  while (!target && modDatabase.hasMore) {
    await loadModRows();
    target = modRows.value.find((mod) => Number(mod.id) === zipmodId);
  }

  if (!target) {
    log(`[Items Error] 未找到来源模组：${row.sourceMod || zipmodId}`);
    return;
  }

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
  if (issue.status === "in_game") return "Unity3D \u6587\u4ef6\u5728\u6e38\u620f\u76ee\u5f55\u4e2d\uff0c\u4f46\u4e0d\u5728\u6a21\u7ec4\u5305\u5185";
  if (issue.status === "missing") return "Unity3D \u6587\u4ef6\u65e0\u6cd5\u627e\u5230";
  if (issue.status === "duplicate") return "存在重复模组";
  return "Unity3D \u6587\u4ef6\u5f02\u5e38";
}

function unity3dIssueSummary(issue) {
  if (issue.type === "manifest_author") return "manifest.xml 缺少 author 字段。";
  if (issue.type === "thumbnail") return "部分物品缩略图缺失或读取失败。";
  if (issue.type === "duplicate_zipmod") return "同一 GUID 存在多个 zipmod 文件。";
  if (issue.status === "error") return "Unity3D 文件存在，但没有解析出可用 Unity 资源。";
  if (issue.status === "in_game") return "Unity3D 文件在游戏目录中，但不在 zipmod 内。";
  if (issue.status === "missing") return "Unity3D 文件缺失。";
  if (issue.status === "duplicate") return "存在重复文件。";
  return issue.solution || "-";
}

function unity3dIssueSolution(issue) {
  if (issue.type === "manifest_author") return "补充并保存 manifest.xml 的作者字段。";
  if (issue.type === "thumbnail") return "重新导入或生成物品缩略图。";
  if (issue.type === "duplicate_zipmod") return "分析同 GUID 的 zipmod 并保留推荐项。";
  if (issue.status === "error") return "重新安装来源模组，或替换该 unity3d 文件后重建数据库。";
  if (issue.status === "in_game") return "\u5c06\u8be5\u6587\u4ef6\u590d\u5236\u8fdb zipmod \u5305\u5185\u5bf9\u5e94 abdata \u8def\u5f84\uff0c\u4f7f\u6a21\u7ec4\u5305\u81ea\u5305\u542b\uff1bCSV \u5f15\u7528\u8def\u5f84\u4fdd\u6301\u4e0d\u53d8\u3002";
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
  if (!item?.id) return;
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
    await refreshModDatabaseList();
    await loadAchievements({ notify: true });
    if (libraryMode.value === "items") {
      const updatedItem = itemRows.value.find((row) => row.id === itemId);
      if (updatedItem) selectedItem.value = updatedItem;
    }
    return true;
  } catch (error) {
    if (selectedMod.value) selectedModDiagnosticsError.value = error.message;
    log(`[Mods Error] ${error.message}`);
  } finally {
    repairingThumbnailItemId.value = null;
  }
}

async function deleteSelectedItem(item = selectedItem.value) {
  if (!item?.id) return;
  deleteItemPrompt.item = item;
  deleteItemPrompt.name = item.name || item.raw?.item_id || String(item.id);
  deleteItemPrompt.error = "";
  deleteItemPrompt.open = true;
}

async function exportItemFbx(item = selectedItem.value) {
  if (!item?.id || exportingFbxItemId.value) return false;
  const targetDir = await window.desktopApi?.selectDirectory?.("选择 FBX 模型导出目录");
  if (!targetDir) return false;
  exportingFbxItemId.value = item.id;
  try {
    const result = await window.desktopApi?.backendRequest?.(
      `/mods/items/${item.id}/export-fbx`,
      { method: "POST", body: { target_dir: targetDir } }
    );
    if (!result?.ok) throw new Error(result?.error || "FBX 模型导出失败");
    log(`[Models] ${result.message}: ${result.fbx_path}`);
    await window.desktopApi?.showItemInFolder?.(result.fbx_path);
    return true;
  } catch (error) {
    log(`[Models Error] ${error.message}`);
    return false;
  } finally {
    exportingFbxItemId.value = null;
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
    const result = await window.desktopApi?.backendRequest?.("/mods/database");
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
    itemDatabase.total = Number(database.item_count || 0);
    stats.zipmods = Number(database.zipmod_count ?? stats.zipmods);
    stats.modItems = Number(database.item_count ?? stats.modItems);

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
    itemDatabase.total = Number(data.total || 0);
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
  if (!force && modDatabase.checked && modDatabase.exists && modRows.value.length > 0) return;

  const exists = await checkModDatabase();
  if (exists) {
    await loadModRows({ reset: true });
    await loadZipmodAuthors();
  }
}

async function ensureItemDatabaseLoaded({ force = false } = {}) {
  if (libraryMode.value !== "items") return;
  if (!backendReady.value) return;
  if (!force && itemDatabase.checked && itemDatabase.exists && itemRows.value.length > 0) return;

  const exists = await checkModDatabase();
  if (exists) {
    await loadItemRows({ reset: true });
    void loadItemFilters();
  }
}

async function refreshModDatabaseList() {
  if (libraryMode.value === "items") {
    await ensureItemDatabaseLoaded({ force: true });
    return;
  }
  await ensureModDatabaseLoaded({ force: true });
  await loadZipmodAuthors();
}

function handleModTableScroll(event) {
  const target = event.currentTarget;
  const remaining = target.scrollHeight - target.scrollTop - target.clientHeight;
  if (remaining >= 160) return;

  if (libraryMode.value === "items") {
    loadItemRows();
  } else if (libraryMode.value === "mods") {
    loadModRows();
  }
}

function applyGameDir(selected) {
  paths.gameDir = selected || "";
  paths.inputDir = selected ? `${selected}\\UserData\\chara` : "";
  clearResourceStats();
  modDatabase.checked = false;
  modDatabase.exists = false;
  itemDatabase.checked = false;
  itemDatabase.exists = false;
  selectedCardFolder.value = "";
}

async function saveAppSettings() {
  const result = await window.desktopApi?.saveSettings?.({
    gameDir: paths.gameDir,
    inputDir: paths.inputDir,
    outputDir: paths.outputDir
  });
  if (!result?.ok) {
    log(`[Settings Error] ${result?.error || "settings save failed"}`);
  }
}

async function loadAppSettings() {
  try {
    const result = await measureStep("loadSettings", () => window.desktopApi?.loadSettings?.());
    if (!result?.ok) {
      log(`[Settings Error] ${result?.error || "settings load failed"}`);
      return;
    }
    const gameDir = result.settings?.gameDir || "";
    if (!gameDir) return;
    applyGameDir(gameDir);
    paths.outputDir = result.settings?.outputDir || "";
    log(`[Settings] 已读取游戏目录：${gameDir}`);
    await measureStep("check_game_dir task", () => submitTask("check_game_dir"));
    await measureStep("loadCardTree after settings", () => loadCardTree());
    await measureStep("checkStartupDatabaseChanges", () => checkStartupDatabaseChanges());
  } catch (error) {
    log(`[Settings Error] ${error.message}`);
  }
}

async function selectGameDir() {
  const selected = await window.desktopApi?.selectDirectory?.("选择 HS2 目录");
  if (!selected) return;
  applyGameDir(selected);
  await saveAppSettings();
  log(`[Directory] 选择游戏目录: ${selected}`);
  await submitTask("check_game_dir");
  await loadCardTree();
  await checkStartupDatabaseChanges();
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

  try {
    const result = await window.desktopApi?.launchGameExecutable?.(launchType, paths.gameDir);
    if (!result?.ok) {
      log(`[Launch Error] ${labels[launchType] || "Launch"}: ${result?.error || "Launch failed"}`);
      return;
    }
    log(`[Launch] ${labels[launchType]}: ${result.executable}`);
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

function buildPayload(overrides = {}) {
  return {
    game_dir: String(paths.gameDir || ""),
    input_dir: String(paths.inputDir || ""),
    output_dir: String(paths.outputDir || ""),
    card_paths: Array.from(selectedCards.value),
    zipmod_extract_mode: String(extractMode.value || "copy"),
    ...overrides
  };
}

function applyTask(task) {
  rememberTask(task);
  const isDatabaseTask = task.task_type === "build_mod_database";
  if (isDatabaseTask) {
    taskName.value = "重建数据库";
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
    gameDirStatus.value = task.data?.is_valid ? "目录有效" : "目录无效";
    if (!task.data?.is_valid) {
      taskHint.value = "请选择有效 HS2 目录";
    }
  }
  if (task.task_type === "search_cards") {
    stats.cards = task.data?.card_count ?? stats.cards;
  }
  if (task.task_type === "extract_mods") {
    stats.zipmods = task.data?.matched_mod_count ?? stats.zipmods;
    stats.missingAbdata = task.data?.missing_abdata?.length ?? stats.missingAbdata;
    paths.outputDir = task.data?.output_dir || paths.outputDir;
  }
  if (isDatabaseTask) {
    stats.zipmods = task.data?.stats?.primary_zipmods ?? stats.zipmods;
    stats.modItems = task.data?.stats?.mod_items ?? stats.modItems;
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
        ensureItemDatabaseLoaded({ force: true });
      } else {
        ensureModDatabaseLoaded({ force: true });
      }
      refreshCharacterCardsAfterDatabaseBuild();
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
      "bulk_update_zipmod_authors",
      "bulk_apply_item_thumbnail",
      "bulk_delete_error_items"
    ].includes(task.task_type)
  ) {
    const failureCount = Number(task.data?.failure_count || 0);
    if (failureCount > 0 && task.status === "completed") {
      (task.data?.failures || []).slice(0, 5).forEach((failure) => log(`[Mods Error] #${failure.id}: ${failure.error}`));
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

async function pollTask(id, options = {}) {
  const { manageBusy = true, onDone = null } = options;
  let finalTask = null;
  try {
    for (;;) {
      const result = await window.desktopApi.backendRequest(`/tasks/${id}`);
      if (!result.ok) {
        log(`[Task Error] ${result.error || "unknown error"}`);
        break;
      }
      applyTask(result.task);
      finalTask = result.task;
      if (["completed", "failed"].includes(result.task.status)) break;
      await new Promise((resolve) => window.setTimeout(resolve, 350));
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
  taskHint.value = "正在导入外部 zipmod";
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
    return;
  }
  isBusy.value = true;
  activeAction.value = type;
  if (type === "build_mod_database") {
    taskName.value = "重建数据库";
    progress.value = 1;
    taskId.value = "queued";
    taskHint.value = "等待后端开始处理";
  }
  log(`[UI] ${type} submitted`);
  try {
    const result = await window.desktopApi.backendRequest("/tasks", {
      method: "POST",
      body: { task_type: type, payload: buildPayload(overrides) }
    });
    if (!result.ok) {
      log(`[Task Error] ${result.error || "unknown error"}`);
      isBusy.value = false;
      activeAction.value = "";
      return;
    }
    applyTask(result.task);
    await pollTask(result.task.id);
  } catch (error) {
    log(`[Task Error] ${error.message}`);
    isBusy.value = false;
    activeAction.value = "";
  }
}

async function submitTaskInBackground(type, overrides = {}, onDone = null) {
  if (!(await waitForBackendReady())) {
    throw new Error(`后端未就绪，无法提交任务：${type}`);
  }
  log(`[UI] ${type} submitted`);
  const result = await window.desktopApi.backendRequest("/tasks", {
    method: "POST",
    body: { task_type: type, payload: buildPayload(overrides) }
  });
  if (!result.ok) {
    throw new Error(result.error || "unknown error");
  }
  applyTask(result.task);
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

function toggleCardSelection(id) {
  if (!id) return;
  const next = new Set(selectedCards.value);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  selectedCards.value = next;
}

function handleCardClick(card) {
  if (!card) return;
  naviActionNotice.type = "";
  naviActionNotice.message = "";
  selectedCardDetailPath.value = card.absolutePath;
  loadSelectedCardProfile(card);
  if (cardBulkMode.value) {
    toggleCardSelection(card.absolutePath);
  }
}

async function loadSelectedCardProfile(card = selectedCardDetail.value) {
  if (!card?.relativePath || !backendReady.value || !paths.gameDir) return;
  selectedCardProfileLoading.value = true;
  selectedCardProfileError.value = "";
  selectedCardProfile.value = null;
  selectedCardDependencies.value = [];
  const targetPath = card.absolutePath;

  try {
    const result = await window.desktopApi?.backendRequest?.(
      `/library/cards/detail?game_dir=${encodeQuery(paths.gameDir)}&path=${encodeQuery(card.relativePath)}`
    );
    if (!result?.ok) {
      throw new Error(result?.error || "人物卡详情读取失败");
    }
    if (selectedCardDetailPath.value === targetPath) {
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
  setup[key] = value;
  setup.dirty = true;
}

function saveSetup() {
  setup.dirty = false;
  log("[Setup] setup.xml saved with backup placeholder.");
}

function clearLogs() {
  logs.value = [];
  seenTaskMessages.value = new Set();
}

onMounted(() => {
  const startedAt = performance.now();
  log("Ready.");
  log("[Mode] zipmod extract mode: Copy");
  log("[Backend] Python backend checking.");
  void (async () => {
    if (await waitForBackendReady()) {
      log("[Backend] Python backend is ready.");
      await measureStep("loadAppSettings", () => loadAppSettings());
      await measureStep("loadAchievements", () => loadAchievements());
      log(`[Startup] onMounted startup path completed in ${formatDurationMs(performance.now() - startedAt)}`);
    } else {
      log("[Backend Error] Python backend startup timed out.");
      log(`[Startup] onMounted startup path failed in ${formatDurationMs(performance.now() - startedAt)}`);
    }
  })();
});

const appCtx = reactive({
  activeAction,
  activeView,
  analyzeDuplicateZipmods,
  achievements,
  achievementPreferences,
  achievementUnlockedCount,
  visibleAchievements,
  selectedAchievement,
  formatAchievementProgress,
  loadAchievements,
  resetAchievementHistory,
  updateAchievementPreference,
  allVisibleCardsSelected,
  allVisibleModsSelected,
  badgeClass,
  buildModDatabase,
  importExternalZipmods,
  openOrganizeAllPrompt,
  bulkActionBusy,
  bulkAuthorSuggestions,
  bulkDeletePrompt,
  bulkDeleteErrorItemsPrompt,
  bulkDuplicateCleanupPrompt,
  cardBulkMode,
  cardDependencyExportPrompt,
  cardDetailTab,
  cardFolderDisplay,
  cardFolders,
  cardLibrary,
  cards,
  characterSideMode,
  checkModDatabase,
  cleaningDuplicateZipmods,
  cleanupDuplicateZipmods,
  clearLogs,
  closeModAuthorFilterSoon,
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
  exitCardBulkMode,
  exitModBulkMode,
  filteredZipmodAuthorOptions,
  formatBytes,
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
  handleCardClick,
  handleCardFolderClick,
  handleModTableScroll,
  isBusy,
  itemAuthorOptions,
  itemDatabase,
  itemDatabaseEmpty,
  itemFilterKinds,
  itemFilters,
  itemKindLabel,
  itemKindOptions,
  itemRows,
  itemTab,
  launchExecutable,
  libraryMode,
  loadItemRows,
  loadModRows,
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
  openBulkDuplicateCleanupPrompt,
  openBulkExportPrompt,
  openBulkOrganizePrompt,
  openBulkRepairUnity3dPrompt,
  openCardDependencyExportPrompt,
  openCardDependencyItem,
  openDuplicateZipmodInFolder,
  openDuplicateZipmodPrompt,
  openManifestAuthorPrompt,
  openManifestEditor,
  openGameDirectory,
  openModItemInItemBrowser,
  openSelectedModInFolder,
  openThumbnailToolsPrompt,
  openSummaryCard,
  overviewSummaryCards,
  paths,
  recentTasks,
  repairingThumbnailItemId,
  exportingFbxItemId,
  repairingUnity3dPath,
  repairThumbnailItem,
  exportItemFbx,
  repairUnity3dIssue,
  saveSetup,
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
  settingNaviSlot,
  selectedCards,
  selectedCount,
  selectedItem,
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
  selectBulkAuthorSuggestion,
  selectMod,
  setDependencyUsageFilter,
  setLibraryMode,
  setModTab,
  setup,
  someVisibleCardsSelected,
  someVisibleModsSelected,
  stats,
  syncSelectedModIdsWithVisibleRows,
  taskHint,
  taskName,
  taskPercent,
  toggleAllVisibleCards,
  toggleAllVisibleMods,
  toggleCardFolder,
  toggleModSelection,
  toggleThumbnailTarget,
  thumbnailIssueReason,
  thumbnailToolsPrompt,
  itemUnity3dFileName,
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
  submitBulkDeleteZipmods,
  submitBulkDeleteErrorItems,
  submitBulkDuplicateCleanup
});

watch([activeView, backendStatus], ([view, status]) => {
  if (view === "mods" && status === "ready") {
    if (libraryMode.value === "items") {
      ensureItemDatabaseLoaded();
    } else {
      ensureModDatabaseLoaded();
    }
  }
  if (view === "characters" && status === "ready") {
    if (!cardLibrary.checked || (cardLibrary.validGameDir && !cardTree.value)) {
      loadCardTree();
    }
  }
});
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand">
        <img class="brand-mark" :src="appIcon" alt="Star_Manager" />
        <img class="brand-logo" :src="brandLogo" alt="Star Manager" />
      </div>

      <nav class="nav" aria-label="Main navigation">
        <button
          v-for="view in views"
          :key="view.id"
          type="button"
          :class="{ active: activeView === view.id }"
          @click="activeView = view.id"
        >
          <span class="nav-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" focusable="false">
              <g v-if="view.id === 'start'">
                <path d="M7.5 8h9a4.5 4.5 0 0 1 4.2 6.1l-1.2 3.1a2 2 0 0 1-3.2.8l-2-1.7H9.7l-2 1.7a2 2 0 0 1-3.2-.8l-1.2-3.1A4.5 4.5 0 0 1 7.5 8Z"></path>
                <path d="M7 11v4M5 13h4M16.5 12h.01M18.5 14h.01"></path>
              </g>
              <g v-else-if="view.id === 'overview'">
                <rect x="4" y="4" width="6" height="6" rx="1"></rect>
                <rect x="14" y="4" width="6" height="6" rx="1"></rect>
                <rect x="4" y="14" width="6" height="6" rx="1"></rect>
                <path d="M14 20v-5M17 20v-8M20 20v-3"></path>
              </g>
              <g v-else-if="view.id === 'characters'">
                <circle cx="12" cy="7" r="3.2"></circle>
                <path d="M5.5 20a6.5 6.5 0 0 1 13 0M9 13.8l3 2.2 3-2.2"></path>
              </g>
              <g v-else-if="view.id === 'mods'">
                <path d="m4 8 8-4 8 4-8 4-8-4Z"></path>
                <path d="m4 8 .1 8 7.9 4 7.9-4L20 8M12 12v8M8 6l8 4"></path>
              </g>
              <g v-else-if="view.id === 'plugins'">
                <path d="M9.5 4H4v5.5a2.5 2.5 0 1 1 0 5V20h5.5a2.5 2.5 0 1 1 5 0H20v-5.5a2.5 2.5 0 1 0 0-5V4h-5.5a2.5 2.5 0 1 0-5 0Z"></path>
              </g>
              <g v-else>
                <path d="M6 3h9l3 3v15H6V3Z"></path>
                <path d="M15 3v4h4M9 11h6M9 15h6M9 19h4"></path>
              </g>
            </svg>
          </span>
          <span>{{ view.label }}</span>
        </button>
      </nav>
    </aside>

    <main class="main">
      <header class="topbar">
        <div class="path-box">
          <button type="button" class="primary" @click="selectGameDir">选择 HS2 目录</button>
          <div class="path-value">
            <span class="path-label">当前目录</span>
            <span class="path-text">{{ gameDirDisplay }}</span>
          </div>
          <span class="badge" :class="badgeClass(gameDirStatus)"><span class="dot"></span>{{ gameDirStatus }}</span>
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
      </header>

      <section class="workspace">
        <StartView v-if="activeView === 'start'" :ctx="appCtx" />
        <OverviewView v-else-if="activeView === 'overview'" :ctx="appCtx" />
        <CharactersView v-else-if="activeView === 'characters'" :ctx="appCtx" />
        <ModsView v-else-if="activeView === 'mods'" :ctx="appCtx" />
        <PluginsView v-show="activeView === 'plugins'" :ctx="appCtx" />
        <LogsView v-if="activeView === 'logs'" :ctx="appCtx" />
      </section>

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
              <span><strong>{{ importResultData.imported_count || 0 }}</strong> 正常</span>
              <span><strong>{{ importResultData.promoted_count || 0 }}</strong> 保留更优</span>
              <span><strong>{{ importResultData.cleaned_count || 0 }}</strong> 清理重复</span>
              <span><strong>{{ importResultData.unity3d_repaired_count || 0 }}</strong> Unity3D</span>
              <span><strong>{{ importResultData.card_imported_count || 0 }}</strong> 角色卡</span>
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
            <div class="export-mode-group" role="radiogroup" aria-label="导出方式">
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
            <strong>物品缺失</strong>
            <p class="subtext">当前人物卡依赖的物品没有在本地物品数据库中匹配到。</p>
            <div class="prompt-note missing-item-note">
              <span>物品</span>
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
            <p class="subtext">删除已选 zipmod 文件，并移除相关数据库记录。</p>
            <div class="prompt-note">
              <span>将要改变</span>
              <strong>删除 {{ selectedModCount }} 个已选 zipmod 文件</strong>
            </div>
            <div class="prompt-note">
              <span>可逆性</span>
              <strong>删除文件不可由应用自动恢复</strong>
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
            <div class="export-mode-group" role="radiogroup" aria-label="导出方式">
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
              <div class="thumbnail-target-head">
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
          <span class="achievement-medal">{{ achievementToast.icon }}</span>
          <span><small>成就解锁</small><strong>{{ achievementToast.title }}</strong><em>{{ achievementToast.description }}</em></span>
        </button>

    </main>
  </div>
</template>

