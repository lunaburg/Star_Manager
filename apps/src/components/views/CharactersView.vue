<script setup>
import LazyThumbnail from "../LazyThumbnail.vue";

const { ctx } = defineProps({
  ctx: { type: Object, required: true }
});
</script>

<template>
<section class="view">
          <div class="character-layout">
            <section class="panel browser-panel">
              <div class="module-head">
                <div><h1>人物卡浏览器（已加载 {{ ctx.cards.length }}）</h1><p class="subtext mono">{{ ctx.cardFolderDisplay }}</p></div>
              </div>
              <div class="toolbar">
                <div class="toolbar-left">
                  <button
                    v-if="!ctx.cardBulkMode"
                    class="bulk-select-button"
                    type="button"
                    :disabled="!ctx.cards.length"
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
                  <select><option>大卡片</option><option>紧凑卡片</option></select>
                  <select><option>按文件名</option><option>按修改时间</option></select>
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
                <div v-if="ctx.cardLibrary.loading && ctx.cards.length === 0" class="card-state">
                  <strong>正在加载人物卡</strong>
                </div>
                <div v-else-if="ctx.cardLibrary.checked && !ctx.cardLibrary.validGameDir" class="card-state">
                  <strong>请选择有效的游戏目录</strong>
                </div>
                <div v-else-if="ctx.cardLibrary.error" class="card-state">
                  <strong>{{ ctx.cardLibrary.error }}</strong>
                </div>
                <div v-else-if="ctx.cards.length === 0" class="card-state">
                  <strong>未找到人物卡</strong>
                  <span class="subtext mono">{{ ctx.cardFolderDisplay }}</span>
                </div>
                <template v-else>
                  <div
                    v-for="card in ctx.cards"
                    :key="card.id"
                    role="button"
                    tabindex="0"
                    class="char-card"
                    :class="{ selected: ctx.selectedCards.has(card.absolutePath), 'bulk-mode': ctx.cardBulkMode }"
                    :aria-pressed="ctx.selectedCards.has(card.absolutePath)"
                    @click="ctx.handleCardClick(card)"
                    @keydown.enter.prevent="ctx.handleCardClick(card)"
                    @keydown.space.prevent="ctx.handleCardClick(card)"
                  >
                    <span v-if="ctx.selectedCards.has(card.absolutePath)" class="check">✓</span>
                    <span class="portrait">
                      <LazyThumbnail :src="card.thumbnailUrl" :alt="card.name + ' preview'" />
                    </span>
                    <span class="card-caption"><strong>{{ card.name }}</strong><span>{{ card.modifiedAt }}</span></span>
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
                  <div class="card-detail-preview">
                    <img :src="ctx.selectedCardDetail.thumbnailUrl" :alt="ctx.selectedCardDetail.name + ' preview'">
                  </div>
                  <div class="tabs mod-detail-tabs card-detail-tabs" aria-label="人物卡详情视图">
                    <button :class="{ active: ctx.cardDetailTab === '详情' }" type="button" @click="ctx.cardDetailTab = '详情'">详情</button>
                    <button :class="{ active: ctx.cardDetailTab === '关联' }" type="button" @click="ctx.cardDetailTab = '关联'">关联</button>
                    <button :class="{ active: ctx.cardDetailTab === '工具' }" type="button" @click="ctx.cardDetailTab = '工具'">工具</button>
                  </div>
                  <div v-if="ctx.cardDetailTab === '详情'" class="drawer-tab-panel active">
                    <div class="drawer-section mod-detail-section">
                      <span class="drawer-section-title">人物参数</span>
                      <div v-if="ctx.selectedCardProfileLoading" class="detail-inline-state">正在解析人物卡参数...</div>
                      <div v-else-if="ctx.selectedCardProfileError" class="detail-inline-state">{{ ctx.selectedCardProfileError }}</div>
                      <template v-else>
                        <div class="kv mod-kv"><span>fullname</span><strong>{{ ctx.formatProfileValue(ctx.selectedCardProfile?.fullname) }}</strong></div>
                        <div class="kv mod-kv"><span>sex</span><strong>{{ ctx.formatProfileValue(ctx.selectedCardProfile?.sex) }}</strong></div>
                        <div class="kv mod-kv"><span>personality</span><strong>{{ ctx.formatProfileValue(ctx.selectedCardProfile?.personality) }}</strong></div>
                        <div class="kv mod-kv"><span>birthMonth</span><strong>{{ ctx.formatProfileValue(ctx.selectedCardProfile?.birthMonth) }}</strong></div>
                        <div class="kv mod-kv"><span>birthDay</span><strong>{{ ctx.formatProfileValue(ctx.selectedCardProfile?.birthDay) }}</strong></div>
                        <div class="kv mod-kv"><span>voiceRate</span><strong>{{ ctx.formatProfileValue(ctx.selectedCardProfile?.voiceRate) }}</strong></div>
                        <div class="kv mod-kv"><span>hsWish</span><strong>{{ ctx.formatProfileValue(ctx.selectedCardProfile?.hsWish) }}</strong></div>
                        <div class="kv mod-kv"><span>futanari</span><strong>{{ ctx.formatProfileValue(ctx.selectedCardProfile?.futanari) }}</strong></div>
                      </template>
                    </div>
                  </div>
                  <div v-else-if="ctx.cardDetailTab === '关联'" class="drawer-tab-panel active">
                    <div class="drawer-section mod-detail-section">
                      <span class="drawer-section-title">关联</span>
                      <div v-if="ctx.selectedCardProfileLoading" class="detail-inline-state">正在解析人物卡依赖...</div>
                      <div v-else-if="ctx.selectedCardProfileError" class="detail-inline-state">{{ ctx.selectedCardProfileError }}</div>
                      <div v-else-if="ctx.selectedCardDependencies.length === 0" class="detail-inline-state">暂无关联数据</div>
                      <div v-else class="card-dependency-list">
                        <button
                          v-for="dependency in ctx.selectedCardDependencies"
                          :key="dependency.id"
                          type="button"
                          class="card-dependency-item"
                          :class="{ missing: !dependency.matched }"
                          :title="dependency.matched ? '打开对应物品' : '物品缺失'"
                          @click="ctx.openCardDependencyItem(dependency)"
                        >
                          <span class="item-thumb" :class="dependency.item ? ctx.badgeClass(dependency.item.status) : 'missing'">
                            <LazyThumbnail
                              v-if="dependency.item?.thumbnailUrl"
                              :src="dependency.item.thumbnailUrl"
                              :alt="(dependency.item.name || dependency.name || dependency.mod_id) + ' thumbnail'"
                            />
                            <span v-else>{{ dependency.matched ? "PNG" : "MISS" }}</span>
                          </span>
                          <span class="card-dependency-main">
                            <strong>{{ dependency.item?.name || dependency.name || dependency.mod_id || "未知物品" }}</strong>
                            <small>{{ dependency.item?.source_mod || dependency.zipmod?.name || dependency.mod_id || "-" }}</small>
                            <small>{{ dependency.property || "-" }}</small>
                          </span>
                          <span class="badge" :class="dependency.matched ? 'ok' : 'danger'">
                            {{ dependency.matched ? "已匹配" : "缺失" }}
                          </span>
                        </button>
                      </div>
                    </div>
                  </div>
                  <div v-else class="drawer-tab-panel active">
                    <div class="drawer-section mod-detail-section">
                      <span class="drawer-section-title">工具</span>
                      <div class="detail-inline-state">暂无可用工具</div>
                    </div>
                  </div>
                </template>
              </div>
            </aside>
          </div>
        </section>
</template>
