<script setup>
import { computed, nextTick, onMounted, ref } from "vue";
import LazyThumbnail from "./LazyThumbnail.vue";

const props = defineProps({
  standalone: { type: Boolean, default: false },
  gameDir: { type: String, default: "" }
});

const PAGE_MODES = {
  character: { label: "人物卡", url: "https://db.bepis.moe/aishoujo", cardType: "AI" },
  scene: { label: "场景卡", url: "https://db.bepis.moe/aiscenes", cardType: "AISCENE" }
};
const selectedMode = ref("character");
const cards = ref([]);
const loading = ref(false);
const open = ref(false);
const error = ref("");
const currentPage = ref(1);
const pageCount = ref(1);
const pageInput = ref("1");
const downloadingId = ref(null);
const downloadState = ref(null);
const pageBody = ref(null);
let requestSerial = 0;
const PAGE_LOAD_TIMEOUT_MS = 5000;
const personalityNames = ["Emotionless", "Friendly", "Confident", "Selfish", "Lazy", "Positive"];
const showLoadingState = computed(() => loading.value && !cards.value.length);

const pageItems = computed(() => {
  const total = Math.max(1, Number(pageCount.value) || 1);
  const current = Math.min(total, Math.max(1, Number(currentPage.value) || 1));
  if (total <= 9) return Array.from({ length: total }, (_value, index) => index + 1);
  const values = [1, 2, "ellipsis-start", current - 1, current, current + 1, "ellipsis-end", total];
  return values.filter((value, index) => {
    if (typeof value === "string") return index === values.indexOf(value);
    return value >= 1 && value <= total && values.indexOf(value) === index;
  });
});

function backendAssetUrl(path) {
  if (!path) return "";
  if (/^https?:\/\//i.test(path)) return path;
  const baseUrl = window.desktopApi?.backendBaseUrl || "http://127.0.0.1:8765";
  return `${baseUrl}${path}`;
}

function formatCount(value) {
  if (value === null || value === undefined || value === "") return "—";
  const number = Number(value);
  return Number.isFinite(number) ? new Intl.NumberFormat("zh-CN").format(number) : "—";
}

function formatSize(value) {
  if (value === null || value === undefined || value === "") return "—";
  const bytes = Number(value);
  if (!Number.isFinite(bytes) || bytes < 0) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(value) {
  if (!value) return "—";
  const raw = String(value);
  const timestamp = Date.parse(/(?:Z|[+-]\d{2}:\d{2})$/i.test(raw) ? raw : `${raw}Z`);
  if (!Number.isFinite(timestamp)) return "—";
  const ageMinutes = Math.max(0, Math.floor((Date.now() - timestamp) / 60000));
  const relative = ageMinutes < 1 ? "刚刚"
    : ageMinutes < 60 ? `${ageMinutes} 分钟前`
      : ageMinutes < 1440 ? `${Math.floor(ageMinutes / 60)} 小时前`
        : `${Math.floor(ageMinutes / 1440)} 天前`;
  const date = new Intl.DateTimeFormat("zh-CN", { year: "2-digit", month: "2-digit", day: "2-digit" }).format(timestamp);
  return `${relative}（${date}）`;
}

function personalityName(value) {
  const index = Number(value);
  return Number.isInteger(index) && personalityNames[index] ? personalityNames[index] : "—";
}

function genderName(value) {
  if (value === "Male") return "♂ 男";
  if (value === "Female") return "♀ 女";
  return String(value || "—");
}

async function downloadCard(card) {
  if (downloadingId.value !== null) return;
  const activeMode = selectedMode.value;
  downloadingId.value = card.id;
  downloadState.value = null;
  try {
    const result = await window.desktopApi?.downloadRemoteCharacterCard?.({
      id: card.id,
      name: card.name,
      cardType: PAGE_MODES[activeMode].cardType,
      gender: card.gender,
      gameDir: props.gameDir
    });
    if (!result?.ok) throw new Error(result?.error || "卡片下载失败");
    if (!result.canceled) downloadState.value = { mode: activeMode, id: card.id, kind: "success", message: "已保存", path: result.path };
  } catch (downloadError) {
    downloadState.value = { mode: activeMode, id: card.id, kind: "error", message: downloadError?.message || "下载失败" };
  } finally {
    downloadingId.value = null;
  }
}

async function loadPage(targetPage = currentPage.value) {
  const activeMode = selectedMode.value;
  const requestId = ++requestSerial;
  const normalizedPage = Math.max(1, Number(targetPage) || 1);
  const changingPage = normalizedPage !== currentPage.value;
  const url = `${PAGE_MODES[activeMode].url}?page=${normalizedPage}`;
  let timeoutId;
  let requestTimedOut = false;
  loading.value = true;
  error.value = "";
  try {
    const pageRequest = (async () => {
      let result;
      try {
        result = await window.desktopApi?.backendRequest?.(
          `/remote/character-page?url=${encodeURIComponent(url)}`
        );
      } catch {
        // The hidden browser remains available if the local backend request fails.
      }
      if (requestId !== requestSerial || requestTimedOut) return null;
      if (!result?.ok || !Array.isArray(result.cards)) {
        result = await window.desktopApi?.remoteCharacterPage?.(url);
      }
      return result;
    })();
    const timeoutRequest = new Promise((_resolve, reject) => {
      timeoutId = window.setTimeout(() => {
        requestTimedOut = true;
        reject(new Error("网络异常，请检查网络后重试"));
      }, PAGE_LOAD_TIMEOUT_MS);
    });
    const result = await Promise.race([pageRequest, timeoutRequest]);
    if (requestId !== requestSerial) return;
    if (!result?.ok) throw new Error(result?.error || "远程卡片页面读取失败");
    downloadState.value = null;
    cards.value = Array.isArray(result.cards) ? result.cards : [];
    currentPage.value = normalizedPage;
    pageInput.value = String(normalizedPage);
    pageCount.value = Math.max(1, Number(result.page_count) || pageCount.value || 1);
    if (changingPage) {
      await nextTick();
      if (requestId === requestSerial) pageBody.value?.scrollTo(0, 0);
    }
  } catch (requestError) {
    if (requestId !== requestSerial) return;
    cards.value = [];
    error.value = requestError?.message || "远程卡片页面读取失败";
    pageInput.value = String(currentPage.value);
  } finally {
    window.clearTimeout(timeoutId);
    if (requestId === requestSerial) loading.value = false;
  }
}

function switchMode(mode) {
  if (!PAGE_MODES[mode] || mode === selectedMode.value) return;
  selectedMode.value = mode;
  cards.value = [];
  currentPage.value = 1;
  pageCount.value = 1;
  pageInput.value = "1";
  error.value = "";
  downloadState.value = null;
  pageBody.value?.scrollTo(0, 0);
  void loadPage(1);
}

function selectPage(page) {
  if (loading.value || page === currentPage.value || page < 1 || page > pageCount.value) return;
  void loadPage(page);
}

function jumpToPage() {
  if (loading.value) return;
  const requestedPage = Number(pageInput.value);
  if (!Number.isFinite(requestedPage)) {
    pageInput.value = String(currentPage.value);
    return;
  }
  const targetPage = Math.min(pageCount.value, Math.max(1, Math.trunc(requestedPage)));
  pageInput.value = String(targetPage);
  if (targetPage === currentPage.value) return;
  void loadPage(targetPage);
}

function refreshPage() {
  if (loading.value) return;
  void loadPage(currentPage.value);
}

function toggleOpen() {
  open.value = !open.value;
}

onMounted(() => {
  if (props.standalone) void loadPage(1);
});

</script>

<template>
  <section class="remote-character-page" :class="{ standalone: props.standalone, 'scene-mode': selectedMode === 'scene' }">
    <div v-if="props.standalone" class="module-head remote-character-page-standalone-head">
      <div class="remote-character-page-mode-switch" role="group" aria-label="网站卡片类型">
        <button type="button" :class="{ active: selectedMode === 'character' }" :aria-pressed="selectedMode === 'character'" @click="switchMode('character')">人物卡</button>
        <button type="button" :class="{ active: selectedMode === 'scene' }" :aria-pressed="selectedMode === 'scene'" @click="switchMode('scene')">场景卡</button>
      </div>
      <button type="button" class="remote-character-page-refresh-button" :disabled="showLoadingState" @click="refreshPage">
        {{ showLoadingState ? "读取中…" : "刷新当前页" }}
      </button>
    </div>

    <div v-if="!props.standalone" class="remote-character-page-head">
      <div>
        <strong>网站人物卡页面</strong>
        <span class="subtext">读取页面中的卡片封面</span>
      </div>
      <button type="button" class="remote-character-page-toggle" :aria-expanded="open" @click="toggleOpen">
        {{ open ? "收起" : "打开" }}
      </button>
    </div>

    <div v-if="props.standalone || open" ref="pageBody" class="remote-character-page-body" :class="{ 'is-centered-state': showLoadingState || (Boolean(error) && !cards.length) }">
      <div v-if="!props.standalone" class="remote-character-page-source">
        <button type="button" :disabled="showLoadingState" @click="refreshPage">
          {{ showLoadingState ? "读取中…" : "刷新当前页" }}
        </button>
      </div>

      <div v-if="error" class="remote-character-page-state error">{{ error }}</div>
      <div v-else-if="showLoadingState" class="remote-character-page-state loading">正在加载{{ PAGE_MODES[selectedMode].label }}</div>
      <div v-else-if="!cards.length" class="remote-character-page-state">网站当前页没有可显示的{{ PAGE_MODES[selectedMode].label }}。</div>
      <template v-else>
        <div class="remote-character-page-grid" role="list" :aria-label="`网站${PAGE_MODES[selectedMode].label}封面`">
          <article v-for="(card, index) in cards" :key="`${selectedMode}-${card.id}`" class="remote-character-page-card" role="listitem" tabindex="0" :aria-label="`${card.name}，查看卡片信息与下载`">
            <div class="remote-character-page-cover">
              <LazyThumbnail :src="backendAssetUrl(card.cover_url)" :alt="`${card.name} 封面`" :eager="index < (selectedMode === 'scene' ? 4 : 6)" />
              <div class="remote-character-page-hover">
                <dl class="remote-character-page-metadata">
                  <div><dt>上传者</dt><dd :title="card.uploader || 'Anonymous'">{{ card.uploader || "Anonymous" }}</dd></div>
                  <div><dt>下载</dt><dd>{{ formatCount(card.download_count) }}</dd></div>
                  <div><dt>评分</dt><dd>{{ formatCount(card.votes) }}</dd></div>
                  <div><dt>大小</dt><dd>{{ formatSize(card.file_size) }}</dd></div>
                  <div><dt>日期</dt><dd>{{ formatDate(card.date_created_utc) }}</dd></div>
                  <template v-if="selectedMode === 'scene'">
                    <div><dt>男性</dt><dd>{{ formatCount(card.male_count) }}</dd></div>
                    <div><dt>女性</dt><dd>{{ formatCount(card.female_count) }}</dd></div>
                    <div><dt>物件</dt><dd>{{ formatCount(card.object_count) }}</dd></div>
                  </template>
                  <div v-else class="remote-character-page-type"><dt>类型</dt><dd><span>{{ personalityName(card.personality) }}</span><span class="remote-character-page-gender" :class="{ female: card.gender === 'Female' }">{{ genderName(card.gender) }}</span></dd></div>
                </dl>
                <button type="button" class="remote-character-page-download" :disabled="downloadingId !== null" @click.stop="downloadCard(card)">
                  {{ downloadingId === card.id ? "下载中…" : "↓ 下载" }}
                </button>
                <span v-if="downloadState?.mode === selectedMode && downloadState?.id === card.id" class="remote-character-page-download-state" :class="downloadState.kind" :title="downloadState.path || downloadState.message" role="status">{{ downloadState.message }}</span>
              </div>
            </div>
            <strong :title="card.name">{{ card.name }}</strong>
          </article>
        </div>
        <nav class="remote-character-page-pagination" :aria-label="`网站${PAGE_MODES[selectedMode].label}分页`">
          <button type="button" :disabled="currentPage <= 1" aria-label="上一页" @click="selectPage(currentPage - 1)">‹</button>
          <template v-for="item in pageItems" :key="item">
            <span v-if="typeof item === 'string'" class="remote-character-page-ellipsis">…</span>
            <button
              v-else
              type="button"
              :class="{ active: item === currentPage }"
              :aria-current="item === currentPage ? 'page' : undefined"
              @click="selectPage(item)"
            >{{ item }}</button>
          </template>
          <button type="button" :disabled="currentPage >= pageCount" aria-label="下一页" @click="selectPage(currentPage + 1)">›</button>
          <div class="remote-character-page-jump" role="group" aria-label="指定页码">
            <label for="remote-character-page-input">跳至</label>
            <input
              id="remote-character-page-input"
              v-model="pageInput"
              type="number"
              min="1"
              :max="pageCount"
              step="1"
              inputmode="numeric"
              aria-label="页码"
              :disabled="loading"
              @keydown.enter.prevent="jumpToPage"
            >
            <button type="button" :disabled="loading" @click="jumpToPage">跳转</button>
          </div>
        </nav>
      </template>
    </div>
  </section>
</template>

<style scoped>
.remote-character-page {
  margin: 0 18px 14px;
  border: 1px solid rgba(113, 151, 190, 0.24);
  border-radius: 12px;
  background: rgba(242, 248, 255, 0.48);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.72);
}

.remote-character-page.standalone {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
  margin: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.remote-character-page-head,
.remote-character-page-source {
  display: flex;
  align-items: center;
  gap: 10px;
}

.remote-character-page-head {
  justify-content: space-between;
  padding: 10px 12px;
}

.remote-character-page-standalone-head {
  flex: none;
  min-height: 48px;
  padding: 8px 16px;
  margin: 0;
  border-bottom-color: rgba(255, 255, 255, 0.56);
  background: rgba(247, 251, 255, 0.32);
  background: color-mix(in srgb, var(--bg-color) 32%, transparent);
  -webkit-backdrop-filter: blur(24px) saturate(1.08);
  backdrop-filter: blur(24px) saturate(1.08);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.58), 0 5px 14px rgba(69, 88, 112, 0.08);
}

.remote-character-page-mode-switch {
  display: inline-flex;
  gap: 3px;
  padding: 3px;
  border: 1px solid rgba(123, 151, 180, 0.3);
  border-radius: 9px;
  background: rgba(255, 255, 255, 0.2);
}

.remote-character-page-mode-switch button {
  height: 32px;
  padding: 0 13px;
  border: 0;
  border-radius: 6px;
  color: #46617b;
  background: transparent;
  box-shadow: none;
  font-size: 14px;
  font-weight: 700;
}

.remote-character-page-mode-switch button.active {
  color: #1f405e;
  background: rgba(255, 255, 255, 0.76);
  box-shadow: 0 1px 4px rgba(64, 88, 111, 0.13);
}

.remote-character-page-mode-switch button:not(:disabled):hover,
.remote-character-page-mode-switch button:not(:disabled):active {
  transform: none;
}

.remote-character-page-mode-switch button:focus-visible {
  outline: 2px solid #6b9bc7;
  outline-offset: 1px;
}

.remote-character-page-head > div {
  min-width: 0;
}

.remote-character-page-head > div {
  display: grid;
  gap: 2px;
}

.remote-character-page-toggle,
.remote-character-page-refresh-button,
.remote-character-page-source button,
.remote-character-page-pagination button {
  border: 1px solid rgba(76, 119, 161, 0.34);
  border-radius: 8px;
  padding: 6px 11px;
  color: #315273;
  background: rgba(255, 255, 255, 0.64);
  cursor: pointer;
}

.remote-character-page-toggle:hover,
.remote-character-page-toggle:focus-visible,
.remote-character-page-refresh-button:hover:not(:disabled),
.remote-character-page-refresh-button:focus-visible,
.remote-character-page-source button:hover:not(:disabled),
.remote-character-page-source button:focus-visible,
.remote-character-page-pagination button:hover:not(:disabled),
.remote-character-page-pagination button:focus-visible {
  background: rgba(224, 239, 255, 0.94);
  outline: none;
}

.remote-character-page-body {
  padding: 0 12px 12px;
}

.remote-character-page-source {
  justify-content: flex-end;
  padding: 0 2px 10px;
  color: #55708e;
  font-size: 12px;
}

.remote-character-page-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 2px 0 12px;
}

.remote-character-page-pagination button {
  min-width: 30px;
  height: 30px;
  padding: 0 7px;
}

.remote-character-page-jump {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-left: 4px;
  color: #607995;
  font-size: 12px;
  white-space: nowrap;
}

.remote-character-page-jump input {
  box-sizing: border-box;
  width: 52px;
  height: 30px;
  padding: 0 6px;
  border: 1px solid rgba(76, 119, 161, 0.34);
  border-radius: 8px;
  color: #315273;
  background: rgba(255, 255, 255, 0.64);
  text-align: center;
}

.remote-character-page-jump input:focus-visible {
  border-color: rgba(76, 119, 161, 0.62);
  outline: 2px solid rgba(107, 155, 199, 0.42);
  outline-offset: 1px;
}

.remote-character-page-jump input:disabled {
  cursor: default;
  opacity: .48;
}

.remote-character-page-jump button {
  min-width: 44px;
}

.remote-character-page-pagination button.active {
  color: #fff;
  border-color: #a75a35;
  background: #bb6a42;
}

.remote-character-page-pagination button:disabled {
  cursor: default;
  opacity: .48;
}

.remote-character-page-refresh-button:disabled,
.remote-character-page-source button:disabled {
  cursor: default;
  opacity: .48;
}

.remote-character-page-ellipsis {
  width: 22px;
  color: #71849a;
  text-align: center;
}

.remote-character-page-state {
  padding: 18px 4px 6px;
  color: #607995;
}

.remote-character-page-state.error {
  color: #a64b56;
}

.remote-character-page-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(126px, 1fr));
  gap: 10px;
  max-height: min(45vh, 520px);
  overflow: auto;
  padding: 2px;
}

.remote-character-page.standalone .remote-character-page-grid {
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 4px 6px;
  min-width: 870px;
  max-height: none;
  overflow: visible;
}

.remote-character-page.standalone.scene-mode .remote-character-page-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.remote-character-page.standalone .remote-character-page-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 10px 14px 12px;
}

.remote-character-page.standalone .remote-character-page-body.is-centered-state {
  display: flex;
  align-items: center;
  justify-content: center;
}

.remote-character-page.standalone .remote-character-page-state.loading,
.remote-character-page.standalone .remote-character-page-state.error {
  padding: 0;
  text-align: center;
}

.remote-character-page.standalone .remote-character-page-card {
  gap: 1px;
  padding: 3px;
  border-radius: 7px;
}

.remote-character-page.standalone .remote-character-page-cover {
  position: relative;
  height: auto;
  aspect-ratio: 252 / 352;
}

.remote-character-page.standalone.scene-mode .remote-character-page-cover {
  width: 100%;
  min-width: 0;
  aspect-ratio: 16 / 9;
  min-height: 176px;
}

.remote-character-page.scene-mode .remote-character-page-hover {
  gap: 4px;
  padding: 7px;
}

.remote-character-page.scene-mode .remote-character-page-metadata {
  gap: 2px;
  line-height: 1.18;
}

.remote-character-page.standalone .remote-character-page-card strong {
  font-size: 11px;
  line-height: 1.15;
}

.remote-character-page.standalone .remote-character-page-cover :deep(.lazy-thumbnail) {
  position: absolute;
  inset: 0;
  display: block;
  width: 100%;
  height: 100%;
}

.remote-character-page.standalone .remote-character-page-cover :deep(img) {
  position: absolute;
  inset: 0;
  min-width: 0;
  min-height: 0;
  object-fit: contain;
}

.remote-character-page.standalone .remote-character-page-pagination {
  padding: 8px 0 0;
}

.remote-character-page-card {
  display: grid;
  gap: 4px;
  min-width: 0;
  padding: 6px;
  border: 1px solid rgba(115, 151, 186, 0.22);
  border-radius: 9px;
  background: rgba(255, 255, 255, 0.62);
}

.remote-character-page-card:focus-visible {
  outline: 2px solid #6b9bc7;
  outline-offset: 2px;
}

.remote-character-page-hover {
  position: absolute;
  z-index: 1;
  inset: 0;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  gap: 7px;
  padding: 9px;
  color: #fff;
  background: linear-gradient(180deg, rgba(12, 19, 29, 0.08), rgba(12, 19, 29, 0.84) 35%, rgba(12, 19, 29, 0.96));
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  transition: opacity 180ms ease, visibility 180ms ease;
}

.remote-character-page-card:hover .remote-character-page-hover,
.remote-character-page-card:focus-within .remote-character-page-hover {
  opacity: 1;
  visibility: visible;
  pointer-events: auto;
}

.remote-character-page-metadata {
  display: grid;
  gap: 3px;
  margin: 0;
  font-size: 10px;
  line-height: 1.25;
}

.remote-character-page-metadata > div {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  gap: 4px;
  align-items: start;
}

.remote-character-page-metadata dt {
  color: rgba(255, 255, 255, 0.72);
}

.remote-character-page-metadata dd {
  min-width: 0;
  margin: 0;
  font-weight: 700;
  overflow-wrap: anywhere;
}

.remote-character-page-metadata > div:first-child dd {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.remote-character-page-type dd {
  display: flex;
  flex-wrap: wrap;
  gap: 3px;
}

.remote-character-page-gender {
  padding: 0 3px;
  border-radius: 3px;
  background: #4686bf;
}

.remote-character-page-gender.female {
  background: #b7467d;
}

.remote-character-page-download {
  width: 100%;
  height: 29px;
  min-height: 29px;
  padding: 0 5px;
  border: 1px solid rgba(255, 220, 196, 0.45);
  border-radius: 5px;
  color: #fff;
  background: #9e6548;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
}

.remote-character-page-download:hover:not(:disabled),
.remote-character-page-download:focus-visible {
  background: #b17755;
  outline: 2px solid rgba(255, 230, 210, 0.9);
  outline-offset: 1px;
}

.remote-character-page-download:disabled {
  cursor: wait;
  opacity: 0.65;
}

.remote-character-page-download-state {
  overflow: hidden;
  font-size: 10px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.remote-character-page-download-state.error {
  color: #ffc0b8;
}

.remote-character-page-download-state.success {
  color: #b9f3d4;
}

.remote-character-page-card strong {
  overflow: hidden;
  color: #385570;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.remote-character-page-cover {
  position: relative;
  aspect-ratio: 252 / 352;
  overflow: hidden;
  border-radius: 6px;
  background: rgba(204, 215, 229, 0.38);
}

.remote-character-page-cover :deep(img) {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

@media (prefers-reduced-motion: reduce) {
  .remote-character-page-hover {
    transition: none;
  }
}

</style>
