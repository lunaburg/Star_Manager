<script setup>
const { ctx } = defineProps({
  ctx: { type: Object, required: true }
});
</script>

<template>
<section class="view">
          <section class="panel log-view">
            <div class="module-head">
              <div><h1>运行日志</h1><p class="subtext">现场记录：任务提交、进度、完成、失败和排障。</p></div>
              <button class="icon" title="关闭" @click="ctx.activeView = 'overview'">X</button>
            </div>
            <div class="toolbar">
              <div class="toolbar-left">
                <button @click="ctx.clearLogs">清空显示</button>
                <button @click="ctx.log('[Clipboard] copy placeholder')">复制全部</button>
                <button disabled>导出日志</button>
              </div>
              <div class="toolbar-right">
                <select><option>全部</option><option>Info</option><option>Warning</option><option>Error</option></select>
                <input class="search" value="Task" aria-label="搜索日志">
              </div>
            </div>
            <pre class="terminal">{{ ctx.logs.join("\n") }}</pre>
          </section>
        </section>
</template>
