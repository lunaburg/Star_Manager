<script setup>
defineProps({
  ctx: { type: Object, required: true }
});
</script>

<template>
  <section class="view trash-view">
    <header class="trash-hero">
      <div>
        <h1>回收站</h1>
      </div>
      <div class="trash-hero-actions">
        <button type="button" class="ghost-button" :disabled="ctx.trashLoading" @click="ctx.loadTrash">刷新</button>
        <button v-if="ctx.filteredTrashEntries.length" type="button" class="danger-action" :disabled="Boolean(ctx.trashAction)" @click="ctx.emptyTrash">
          清空回收站
        </button>
      </div>
    </header>

    <div class="trash-toolbar">
      <div class="trash-filter-tabs" role="tablist" aria-label="回收站筛选">
        <button type="button" :class="{ active: ctx.trashFilter === 'all' }" @click="ctx.trashFilter = 'all'">全部 <b>{{ ctx.trashEntries.length }}</b></button>
        <button type="button" :class="{ active: ctx.trashFilter === 'cards' }" @click="ctx.trashFilter = 'cards'">人物卡 <b>{{ ctx.trashEntries.filter((item) => item.kind === 'cards').length }}</b></button>
        <button type="button" :class="{ active: ctx.trashFilter === 'mods' }" @click="ctx.trashFilter = 'mods'">模组 <b>{{ ctx.trashEntries.filter((item) => item.kind === 'mods').length }}</b></button>
      </div>
    </div>

    <div v-if="ctx.trashError" class="trash-notice error">{{ ctx.trashError }}</div>
    <div v-if="ctx.trashNotice" class="trash-notice success">{{ ctx.trashNotice }}</div>

    <section v-if="ctx.pendingDeleteEntries.length" class="pending-delete-panel">
      <div class="pending-delete-copy">
        <strong>{{ ctx.pendingDeleteEntries.length }} 个删除请求等待文件解除占用</strong>
        <span>游戏关闭或释放 zipmod 后，后台会自动继续；也可以立即重试。</span>
      </div>
      <button type="button" class="ghost-button" :disabled="ctx.pendingDeleteAction" @click="ctx.retryPendingDeletes">
        {{ ctx.pendingDeleteAction ? "重试中..." : "立即重试" }}
      </button>
    </section>

    <div v-if="ctx.trashLoading" class="trash-empty-state">
      <span class="trash-pulse"></span>
      <strong>正在读取回收站</strong>
    </div>
    <div v-else-if="!ctx.filteredTrashEntries.length" class="trash-empty-state">
      <div class="trash-empty-icon" aria-hidden="true">
        <svg viewBox="0 0 48 48" focusable="false"><path d="M12 15h24M19 15V10h10v5M16 19v17h16V19M21 24v7M27 24v7" /></svg>
      </div>
      <strong>回收站是空的</strong>
      <span>删除卡片或模组后，它们会出现在这里。</span>
    </div>
    <div v-else class="trash-list">
      <article v-for="item in ctx.filteredTrashEntries" :key="item.kind + ':' + item.id" class="trash-item" :class="`trash-item--${item.kind}`">
        <div class="trash-item-copy">
          <div class="trash-item-title"><strong>{{ item.name || item.file_name }}</strong><span class="trash-kind-chip">{{ item.kind_label }}</span></div>
          <span class="trash-item-meta">{{ item.file_name }} · {{ ctx.formatBytes(item.size) }} · {{ ctx.formatTrashDate(item.deleted_at) }}</span>
          <code>{{ item.source_path }}</code>
        </div>
        <div class="trash-item-actions">
          <button type="button" class="restore-button" :disabled="Boolean(ctx.trashAction)" @click.stop="ctx.restoreTrash(item)">恢复</button>
          <button type="button" class="trash-delete-button" :disabled="Boolean(ctx.trashAction)" @click.stop="ctx.permanentlyDeleteTrash(item)">永久删除</button>
        </div>
      </article>
    </div>
  </section>
</template>
