<script setup>
import { getAchievementIcon } from "../../achievementIcons";

const { ctx } = defineProps({
  ctx: { type: Object, required: true }
});
</script>

<template>
<section class="view">
          <div class="overview-grid">
            <div class="overview-stack">
              <section class="panel">
                <div class="module-head"><div><h1>总览</h1></div></div>
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
                    <h2>成就陈列柜</h2>
                  </div>
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
                    <span class="achievement-medal">
                      <img v-if="getAchievementIcon(item)" :src="getAchievementIcon(item)" :alt="`${item.title}图标`">
                      <span v-else>{{ item.icon }}</span>
                    </span>
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
                  <button class="action-item" @click="ctx.importExternalZipmods"><span><strong>导入外部模组</strong><small>扫描 zipmod 和标准结构的 zip，诊断并保留更完整版本。</small></span><span>→</span></button>
                  <button class="action-item action-item--organize" @click="ctx.openOrganizeAllPrompt"><span><strong>一键整理</strong><small>将 mods 下全部 zipmod 移入对应的作者子目录。</small></span><span>→</span></button>
                  <button class="action-item" @click="ctx.buildModDatabase"><span><strong>重建数据库</strong><small>重新生成角色卡和 zipmod 本地索引。</small></span><span>→</span></button>
                </div>
              </section>
              <section v-if="ctx.recentTasks.length" class="panel overview-task-panel">
                <div class="module-head"><h2>最近任务</h2></div>
                <div class="task-list">
                  <button
                    v-for="task in ctx.recentTasks"
                    :key="task.id"
                    class="task-item"
                    type="button"
                    :aria-label="`查看任务：${task.title}`"
                    @click="ctx.openTaskDetails(task)"
                  >
                    <span class="task-item-copy"><strong>{{ task.title }}</strong><small>{{ task.summary }}</small></span>
                    <span class="task-item-status"><span class="badge" :class="task.badgeClass">{{ task.label }}</span><span class="task-item-chevron" aria-hidden="true">↗</span></span>
                  </button>
                </div>
              </section>
            </aside>
          </div>
          <div v-if="ctx.selectedTask" class="task-drawer-backdrop" @click.self="ctx.selectedTask = null">
            <aside class="task-drawer" role="dialog" aria-modal="true" aria-labelledby="task-drawer-title">
              <button class="task-drawer-close" type="button" aria-label="关闭任务详情" @click="ctx.selectedTask = null">×</button>
              <div class="task-drawer-heading">
                <div>
                  <h2 id="task-drawer-title">{{ ctx.selectedTask.title || ctx.selectedTask.task_type }}</h2>
                </div>
                <span class="badge" :class="ctx.taskStatusClass(ctx.selectedTask)">{{ ctx.taskStatusLabel(ctx.selectedTask) }}</span>
              </div>
              <div class="task-drawer-summary">
                <strong>{{ ctx.taskSummary(ctx.selectedTask) }}</strong>
                <span v-if="ctx.selectedTask.status === 'completed'">任务已完成，以下为本次执行记录。</span>
                <span v-else-if="ctx.selectedTask.status === 'failed'">任务未完成，请查看错误信息和任务消息。</span>
                <span v-else>任务当前状态：{{ ctx.selectedTask.status }}</span>
              </div>

              <section v-if="ctx.taskTimingRows(ctx.selectedTask).length" class="task-drawer-section">
                <div class="task-drawer-section-head"><h3>耗时汇总</h3><span>{{ ctx.formatTaskDuration(ctx.taskElapsedMs(ctx.selectedTask)) }}</span></div>
                <div class="task-timing-grid">
                  <div v-for="row in ctx.taskTimingRows(ctx.selectedTask)" :key="row[0]" class="task-timing-row" :class="{ 'task-timing-row--total': row[0] === '总耗时' }">
                    <span>{{ row[0] }}</span><strong>{{ ctx.formatTaskDuration(row[1]) }}</strong>
                  </div>
                </div>
              </section>

              <section v-if="ctx.taskResultRows(ctx.selectedTask).length" class="task-drawer-section">
                <div class="task-drawer-section-head"><h3>完成情况</h3></div>
                <div class="task-result-grid">
                  <div v-for="row in ctx.taskResultRows(ctx.selectedTask)" :key="row[0]"><span>{{ row[0] }}</span><strong>{{ ctx.formatStat(row[1]) }}</strong></div>
                </div>
              </section>

              <section class="task-drawer-section task-message-section">
                <div class="task-drawer-section-head"><h3>任务日志</h3><span>{{ ctx.selectedTask.messages?.length || 0 }} 条</span></div>
                <div class="task-message-list">
                  <p v-for="(message, index) in ctx.selectedTask.messages" :key="`${index}-${message}`">{{ message }}</p>
                  <p v-if="ctx.selectedTask.error" class="task-message-error">{{ ctx.selectedTask.error }}</p>
                </div>
              </section>

              <dl class="task-drawer-meta">
                <div><dt>开始时间</dt><dd>{{ ctx.formatTaskTimestamp(ctx.selectedTask.created_at) }}</dd></div>
                <div><dt>结束时间</dt><dd>{{ ctx.formatTaskTimestamp(ctx.selectedTask.finished_at || ctx.selectedTask.updated_at) }}</dd></div>
              </dl>
            </aside>
          </div>
          <div v-if="ctx.selectedAchievement" class="achievement-drawer-backdrop" @click.self="ctx.selectedAchievement = null">
            <aside class="achievement-drawer">
              <button class="achievement-close" type="button" @click="ctx.selectedAchievement = null">×</button>
              <div class="achievement-drawer-hero">
                <span class="achievement-medal large">
                  <img v-if="getAchievementIcon(ctx.selectedAchievement)" :src="getAchievementIcon(ctx.selectedAchievement)" :alt="`${ctx.selectedAchievement.title}图标`">
                  <span v-else>{{ ctx.selectedAchievement.icon }}</span>
                </span>
                <div class="achievement-drawer-heading">
                  <h2>{{ ctx.selectedAchievement.title }}</h2>
                </div>
              </div>
              <p>{{ ctx.selectedAchievement.description }}</p>
              <div class="achievement-detail-stat">
                <strong>{{ ctx.formatAchievementProgress(ctx.selectedAchievement) }}</strong>
                <span>{{ ctx.selectedAchievement.unlocked ? "挑战已经完成" : "继续整理资源库来推进进度" }}</span>
              </div>
              <dl>
                <div><dt>状态</dt><dd>{{ ctx.selectedAchievement.unlocked ? "已解锁" : "未解锁" }}</dd></div>
                <div><dt>首次解锁</dt><dd>{{ ctx.formatDatabaseTime(ctx.selectedAchievement.unlocked_at) }}</dd></div>
              </dl>
            </aside>
          </div>
        </section>
</template>
