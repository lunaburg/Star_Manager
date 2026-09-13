<script setup>
import launcherArtwork from "../../assets/start-launcher-artwork.png";

const { ctx } = defineProps({
  ctx: { type: Object, required: true }
});
</script>

<template>
<section class="view start-view">
          <div class="start-grid">
            <section class="panel launch-bar">
              <button type="button" class="primary" :disabled="!ctx.paths.gameDir || ctx.setup.loading || !ctx.setup.loaded" @click="ctx.launchExecutable('game')">开始游戏</button>
              <button type="button" :disabled="!ctx.paths.gameDir || ctx.setup.loading || !ctx.setup.loaded" @click="ctx.launchExecutable('studio')">开始工作室</button>
              <button type="button" :disabled="!ctx.paths.gameDir || ctx.setup.loading || !ctx.setup.loaded" @click="ctx.launchExecutable('vr')">开始 VR</button>
              <span class="badge" :class="ctx.setup.loaded ? 'ok' : ctx.setup.error ? 'danger' : 'neutral'">
                {{ ctx.setup.loading ? "正在读取 setup.xml" : ctx.setup.loaded ? (ctx.setup.exists ? "setup.xml 已读取" : "将创建 setup.xml") : "setup.xml 未读取" }}
              </span>
              <span class="badge" :class="ctx.setup.dirty ? 'warn' : 'neutral'">
                {{ ctx.setup.dirty ? "有未保存修改" : "配置已同步" }}
              </span>
            </section>

            <div class="start-columns">
              <section class="panel">
                <div class="module-head">
                  <div>
                    <h1>游戏配置</h1>
                  </div>
                </div>
                <div class="section">
                  <label class="form-row">
                    <span class="label">语言</span>
                    <select :value="ctx.setup.language" :disabled="!ctx.setup.loaded || ctx.setup.saving" @change="ctx.updateSetup('language', $event.target.value)">
                      <option v-for="option in ctx.setupLanguageOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                    </select>
                  </label>
                  <label class="form-row">
                    <span class="label">画质</span>
                    <select :value="ctx.setup.quality" :disabled="!ctx.setup.loaded || ctx.setup.saving" @change="ctx.updateSetup('quality', $event.target.value)">
                      <option v-for="option in ctx.setupQualityOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                    </select>
                  </label>
                  <label class="form-row">
                    <span class="label">显示器</span>
                    <select :value="ctx.setup.display" :disabled="!ctx.setup.loaded || ctx.setup.saving" @change="ctx.updateSetup('display', $event.target.value)">
                      <option v-for="display in ctx.setup.displays" :key="display.index" :value="display.index">{{ display.label }}</option>
                    </select>
                  </label>
                  <label class="form-row">
                    <span class="label">分辨率</span>
                    <select :value="ctx.setup.resolution" :disabled="!ctx.setup.loaded || ctx.setup.saving" @change="ctx.updateSetup('resolution', $event.target.value)">
                      <option v-for="resolution in ctx.setup.resolutions" :key="resolution.label" :value="resolution.label">{{ resolution.label }}</option>
                    </select>
                  </label>
                  <button class="toggle-row" type="button" :disabled="!ctx.setup.loaded || ctx.setup.saving" @click="ctx.updateSetup('fullscreen', !ctx.setup.fullscreen)">
                    <span>全屏</span>
                    <span class="switch" :class="{ on: ctx.setup.fullscreen }"></span>
                  </button>
                  <p v-if="ctx.setup.error" class="setup-message error">{{ ctx.setup.error }}</p>
                  <p v-else-if="ctx.setup.warning" class="setup-message warning">{{ ctx.setup.warning }}</p>
                  <button class="primary wide-action" type="button" :disabled="!ctx.setup.dirty || ctx.setup.saving || !ctx.setup.loaded" @click="ctx.saveSetup">
                    {{ ctx.setup.saving ? "保存中…" : "保存配置" }}
                  </button>
                </div>
              </section>

              <section class="panel launcher-card">
                <img :src="launcherArtwork" alt="Star Manager 樱花街景插画">
              </section>

              <aside class="panel">
                <div class="module-head">
                  <div>
                    <h2>目录入口</h2>
                  </div>
                </div>
                <div class="quick-list">
                  <button type="button" :disabled="!ctx.paths.gameDir" @click="ctx.openGameDirectory('.')">游戏主目录</button>
                  <button type="button" :disabled="!ctx.paths.gameDir" @click="ctx.openGameDirectory('UserData')">UserData</button>
                  <button type="button" :disabled="!ctx.paths.gameDir" @click="ctx.openGameDirectory('UserData\\Studio\\scene')">工作室场景</button>
                  <button type="button" :disabled="!ctx.paths.gameDir" @click="ctx.openGameDirectory('UserData\\cap')">截图</button>
                  <button type="button" :disabled="!ctx.paths.gameDir" @click="ctx.openGameDirectory('UserData\\chara\\female')">人物卡（女）</button>
                  <button type="button" :disabled="!ctx.paths.gameDir" @click="ctx.openGameDirectory('UserData\\chara\\male')">人物卡（男）</button>
                </div>
              </aside>
            </div>

          </div>
        </section>
</template>
