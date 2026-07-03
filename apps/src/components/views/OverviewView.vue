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
              <section class="panel">
                <div class="module-head"><div><h2>游戏目录状态</h2><p class="subtext mono">{{ ctx.gameDirDisplay }}</p></div><span class="badge" :class="ctx.badgeClass(ctx.gameDirStatus)">{{ ctx.gameDirStatus }}</span></div>
                <div class="task-list">
                  <div class="task-item"><span>mods</span><span class="badge ok">OK</span></div>
                  <div class="task-item"><span>abdata</span><span class="badge ok">OK</span></div>
                  <div class="task-item"><span>UserData/chara</span><span class="badge ok">OK</span></div>
                </div>
              </section>
            </div>
            <aside class="overview-stack">
              <section class="panel">
                <div class="module-head"><h2>建议操作</h2></div>
                <div class="action-list">
                  <button class="action-item" @click="ctx.buildModDatabase"><span><strong>重建数据库</strong><small>重新生成角色卡和 zipmod 本地索引。</small></span><span>→</span></button>
                  <button class="action-item"><span><strong>查看依赖问题摘要</strong><small>定位缺失 zipmod。</small></span><span>→</span></button>
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
        </section>
</template>
