<script setup>
const { ctx } = defineProps({
  ctx: { type: Object, required: true }
});
</script>

<template>
<section class="view">
          <section class="panel log-view">
            <div class="module-head">
              <div><h1>运行日志</h1></div>
            </div>
            <div class="toolbar">
              <div class="toolbar-left">
                <button @click="ctx.clearLogs">清空显示</button>
                <button @click="ctx.log('[Clipboard] copy placeholder')">复制全部</button>
                <button disabled>导出日志</button>
              </div>
            </div>
            <pre class="terminal">{{ ctx.logs.join("\n") }}</pre>
          </section>
        </section>
</template>
