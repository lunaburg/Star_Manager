<script setup>
const { ctx } = defineProps({
  ctx: { type: Object, required: true }
});
</script>

<template>
<section class="view">
          <div class="overview-grid">
            <div class="overview-stack">
              <section class="panel">
                <div class="module-head"><div><h1>总览</h1><p class="subtext">目录校验、资源健康、最近任务和建议操作。</p></div></div>
                <div v-if="ctx.overviewSummaryCards.length" class="summary-grid">
                  <button
                    v-for="card in ctx.overviewSummaryCards"
                    :key="card.key"
                    class="summary-card"
                    type="button"
                    @click="ctx.openSummaryCard(card)"
                  >
                    <span>{{ card.label }}</span>
                    <strong>{{ ctx.formatStat(card.value) }}</strong>
                    <small>{{ card.caption }}</small>
                  </button>
                </div>
                <div v-else class="overview-empty">
                  <strong>暂无可用统计</strong>
                  <span>请选择有效的游戏目录，并在数据库创建完成后查看资源概览。</span>
                </div>
              </section>
              <section class="panel achievement-panel achievement-panel--embedded">
                <div class="module-head achievement-head">
                  <div>
                    <span class="achievement-kicker">LOCAL ARCHIVE</span>
                    <h2>成就陈列柜</h2>
                    <p class="subtext">纯本地记录，不联网、不参与排行。</p>
                  </div>
                  <span class="achievement-count">{{ ctx.achievementUnlockedCount }} / {{ ctx.achievements.length }}</span>
                </div>
                <div v-if="ctx.achievementPreferences.enabled && ctx.visibleAchievements.length" class="achievement-grid">
                  <button
                    v-for="item in ctx.visibleAchievements"
                    :key="item.id"
                    class="achievement-card"
                    :class="{ unlocked: item.unlocked }"
                    type="button"
                    @click="ctx.selectedAchievement = item"
                  >
                    <span class="achievement-medal">{{ item.icon }}</span>
                    <span class="achievement-copy">
                      <span class="achievement-title-row"><strong>{{ item.title }}</strong><small>{{ item.unlocked ? "已解锁" : "进行中" }}</small></span>
                      <span>{{ item.description }}</span>
                      <span class="achievement-progress"><i :style="{ width: `${Math.min(100, item.progress / item.target * 100)}%` }"></i></span>
                      <small>{{ ctx.formatAchievementProgress(item) }}</small>
                    </span>
                  </button>
                </div>
                <div v-else-if="!ctx.achievementPreferences.enabled" class="overview-empty achievement-disabled-state">
                  <strong>本地成就已关闭</strong>
                  <span>开启后才会继续记录新的清理与修复成果。</span>
                  <button type="button" @click="ctx.updateAchievementPreference('enabled', true)">启用成就陈列柜</button>
                </div>
                <div v-else class="overview-empty"><strong>陈列柜还是空的</strong><span>关闭“隐藏未解锁成就”即可查看全部挑战。</span></div>
              </section>
            </div>
            <aside class="overview-stack">
              <section class="panel">
                <div class="module-head"><h2>建议操作</h2></div>
                <div class="action-list">
                  <button class="action-item" @click="ctx.importExternalZipmods"><span><strong>导入外部模组</strong><small>扫描文件夹内 zipmod，诊断并保留更完整版本。</small></span><span>→</span></button>
                  <button class="action-item action-item--organize" @click="ctx.openOrganizeAllPrompt"><span><strong>一键整理</strong><small>将 mods 下全部 zipmod 移入对应的作者子目录。</small></span><span>→</span></button>
                  <button class="action-item" @click="ctx.buildModDatabase"><span><strong>重建数据库</strong><small>重新生成角色卡和 zipmod 本地索引。</small></span><span>→</span></button>
                  <button class="action-item" @click="ctx.activeView = 'characters'"><span><strong>打开角色管理</strong><small>浏览 UserData/chara。</small></span><span>→</span></button>
                  <button class="action-item" @click="ctx.activeView = 'mods'"><span><strong>打开模组管理</strong><small>以表格查看 zipmod。</small></span><span>→</span></button>
                </div>
              </section>
              <section v-if="ctx.recentTasks.length" class="panel">
                <div class="module-head"><h2>最近任务</h2></div>
                <div class="task-list">
                  <div v-for="task in ctx.recentTasks" :key="task.id" class="task-item">
                    <span>{{ task.title }}<br><small>{{ task.summary }}</small></span>
                    <span class="badge" :class="task.badgeClass">{{ task.label }}</span>
                  </div>
                </div>
              </section>
            </aside>
          </div>
          <div v-if="ctx.selectedAchievement" class="achievement-drawer-backdrop" @click.self="ctx.selectedAchievement = null">
            <aside class="achievement-drawer">
              <button class="achievement-close" type="button" @click="ctx.selectedAchievement = null">×</button>
              <span class="achievement-medal large">{{ ctx.selectedAchievement.icon }}</span>
              <span class="achievement-kicker">ACHIEVEMENT RECORD</span>
              <h2>{{ ctx.selectedAchievement.title }}</h2>
              <p>{{ ctx.selectedAchievement.description }}</p>
              <div class="achievement-detail-stat">
                <strong>{{ ctx.formatAchievementProgress(ctx.selectedAchievement) }}</strong>
                <span>{{ ctx.selectedAchievement.unlocked ? "挑战已经完成" : "继续整理资源库来推进进度" }}</span>
              </div>
              <dl>
                <div><dt>状态</dt><dd>{{ ctx.selectedAchievement.unlocked ? "已解锁" : "未解锁" }}</dd></div>
                <div><dt>首次解锁</dt><dd>{{ ctx.formatDatabaseTime(ctx.selectedAchievement.unlocked_at) }}</dd></div>
                <div><dt>统计方式</dt><dd>仅限 Star_Manager 本地数据库与操作记录</dd></div>
              </dl>
            </aside>
          </div>
        </section>
</template>
