<script setup>
const { ctx } = defineProps({
  ctx: { type: Object, required: true }
});
</script>

<template>
<section class="view start-view">
          <div class="start-grid">
            <section class="panel launch-bar">
              <button type="button" class="primary" :disabled="!ctx.paths.gameDir" @click="ctx.launchExecutable('game')">开始游戏</button>
              <button type="button" :disabled="!ctx.paths.gameDir" @click="ctx.launchExecutable('studio')">开始工作室</button>
              <button type="button" :disabled="!ctx.paths.gameDir" @click="ctx.launchExecutable('vr')">开始 VR</button>
              <span class="badge ok">ctx.setup.xml 已读取</span>
              <span class="badge" :class="ctx.setup.dirty ? 'warn' : 'neutral'">{{ ctx.setup.dirty ? "Unsaved setup" : "Setup unchanged" }}</span>
            </section>

            <div class="start-columns">
              <section class="panel">
                <div class="module-head">
                  <div>
                    <h1>游戏配置</h1>
                    <p class="subtext">读取 UserData/setup.xml</p>
                  </div>
                </div>
                <div class="section">
                  <label class="form-row">
                    <span class="label">语言</span>
                    <select :value="ctx.setup.language" @change="ctx.updateSetup('language', $event.target.value)">
                      <option>中文</option>
                      <option>日文</option>
                      <option>English</option>
                    </select>
                  </label>
                  <label class="form-row">
                    <span class="label">画质</span>
                    <select :value="ctx.setup.quality" @change="ctx.updateSetup('quality', $event.target.value)">
                      <option>高</option>
                      <option>中</option>
                      <option>低</option>
                      <option>超高</option>
                    </select>
                  </label>
                  <label class="form-row">
                    <span class="label">显示器</span>
                    <select :value="ctx.setup.display" @change="ctx.updateSetup('display', $event.target.value)">
                      <option>Display 0</option>
                      <option>Display 1</option>
                    </select>
                  </label>
                  <label class="form-row">
                    <span class="label">分辨率</span>
                    <select :value="ctx.setup.resolution" @change="ctx.updateSetup('resolution', $event.target.value)">
                      <option>1920 x 1080</option>
                      <option>2560 x 1440</option>
                      <option>3840 x 2160</option>
                    </select>
                  </label>
                  <button class="toggle-row" type="button" @click="ctx.updateSetup('fullscreen', !ctx.setup.fullscreen)">
                    <span>全屏</span>
                    <span class="switch" :class="{ on: ctx.setup.fullscreen }"></span>
                  </button>
                  <button class="primary wide-action" type="button" :disabled="!ctx.setup.dirty" @click="ctx.saveSetup">保存配置</button>
                </div>
              </section>

              <section class="panel launcher-card">
                <h2 class="hero-title">HoneySelect2<br>Resource Desk</h2>
                <p class="subtext">启动状态、版本信息与本地资源健康概览。</p>
                <div class="status-strip">
                  <div class="metric"><div class="metric-value">{{ ctx.formatStat(ctx.stats.cards) }}</div><div class="metric-label">角色卡</div></div>
                  <div class="metric"><div class="metric-value">{{ ctx.formatStat(ctx.stats.zipmods) }}</div><div class="metric-label">zipmod</div></div>
                  <div class="metric"><div class="metric-value">Copy</div><div class="metric-label">默认模式</div></div>
                </div>
              </section>

              <aside class="panel">
                <div class="module-head">
                  <div>
                    <h2>目录入口</h2>
                    <p class="subtext">常用游戏目录快捷打开</p>
                  </div>
                </div>
                <div class="quick-list">
                  <button>游戏主目录</button>
                  <button>UserData</button>
                  <button>工作室场景</button>
                  <button>截图</button>
                  <button>人物卡（女）</button>
                  <button>人物卡（男）</button>
                </div>
              </aside>
            </div>

          </div>
        </section>
</template>
