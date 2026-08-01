<script setup>
const { ctx } = defineProps({
  ctx: { type: Object, required: true }
});

const startupViews = [
  { value: "start", label: "开始游戏" },
  { value: "overview", label: "总览" },
  { value: "characters", label: "角色管理" },
  { value: "mods", label: "模组管理" },
  { value: "workbench", label: "工作台" },
  { value: "plugins", label: "插件管理" },
  { value: "logs", label: "运行日志" },
  { value: "settings", label: "设置" }
];

const favoriteCardThemes = [
  { value: "gold", label: "鎏金流彩", description: "暖金卡框、流彩文字与玻璃扫光" },
  { value: "neon", label: "霓虹炫彩", description: "霓虹卡框、白色幻彩字与冷暖扫光" },
  { value: "sakura", label: "樱落绮梦", description: "樱粉漆面、暖白金字与花瓣柔雾" },
  { value: "obsidian", label: "黑曜鎏火", description: "黑曜裂纹、象牙白字与余烬火星" }
];
</script>

<template>
  <section class="view settings-view">
    <div class="settings-page-head">
      <div>
        <span class="settings-eyebrow">MANAGER CONTROL</span>
        <h1>设置</h1>
      </div>
      <span v-if="ctx.settingsNotice.message" class="settings-save-state" :class="ctx.settingsNotice.type">
        <span class="dot"></span>{{ ctx.settingsNotice.message }}
      </span>
    </div>

    <div class="settings-layout">
      <section class="panel settings-section settings-section--startup">
        <div class="settings-section-icon" aria-hidden="true">01</div>
        <div class="settings-section-body">
          <div class="settings-section-head">
            <div><h2>启动与检查</h2><p>决定管理器打开后的落点和资源检查方式。</p></div>
          </div>

          <label class="setting-row setting-row--select">
            <span class="setting-copy"><strong>启动页面</strong><small>下次打开 Star_Manager 时自动进入此页面。</small></span>
            <select :value="ctx.managerSettings.startupView" @change="ctx.updateManagerSetting('startupView', $event.target.value)">
              <option v-for="item in startupViews" :key="item.value" :value="item.value">{{ item.label }}</option>
            </select>
          </label>

          <div class="setting-row">
            <span class="setting-copy"><strong>启动时检查资源变化</strong><small>比较 zipmod 与角色卡索引，必要时执行增量更新。</small></span>
            <button
              class="setting-switch"
              :class="{ on: ctx.managerSettings.checkDatabaseChangesOnStartup }"
              type="button"
              role="switch"
              :aria-checked="ctx.managerSettings.checkDatabaseChangesOnStartup"
              @click="ctx.updateManagerSetting('checkDatabaseChangesOnStartup', !ctx.managerSettings.checkDatabaseChangesOnStartup)"
            ><span></span></button>
          </div>

          <div class="settings-safety-note">
            <span class="safety-lock">SAFE</span>
            <span><strong>文件操作默认使用 Copy</strong><small>移动和删除仍会单独要求确认，避免意外修改游戏目录。</small></span>
          </div>
        </div>
      </section>

      <section class="panel settings-section">
        <div class="settings-section-icon" aria-hidden="true">02</div>
        <div class="settings-section-body">
          <div class="settings-section-head">
            <div><h2>收藏人物卡主题</h2><p>一套主题统一控制卡框、名字字体与详情卡面特效。</p></div>
          </div>

          <div class="frame-theme-picker" role="radiogroup" aria-label="收藏人物卡边框主题">
            <button
              v-for="theme in favoriteCardThemes"
              :key="theme.value"
              type="button"
              class="frame-theme-option"
              :class="[{ selected: ctx.managerSettings.favoriteCardTheme === theme.value }, `frame-theme-option--${theme.value}`]"
              role="radio"
              :aria-checked="ctx.managerSettings.favoriteCardTheme === theme.value"
              @click="ctx.updateManagerSetting('favoriteCardTheme', theme.value)"
            >
              <span class="frame-theme-sample" aria-hidden="true"><i>人物卡</i></span>
              <span class="frame-theme-copy"><strong>{{ theme.label }}</strong><small>{{ theme.description }}</small></span>
              <span class="frame-theme-check" aria-hidden="true">✓</span>
            </button>
          </div>
          <p class="frame-theme-scope">同步应用：网格卡框 · 名字铭牌与字体 · 详情卡框 · 卡面动态光效</p>
        </div>
      </section>

      <section class="panel settings-section">
        <div class="settings-section-icon" aria-hidden="true">03</div>
        <div class="settings-section-body">
          <div class="settings-section-head">
            <div><h2>本地成就</h2><p>这些记录只保存在本机，不联网也不参与排行。</p></div>
            <span class="settings-count">{{ ctx.achievementUnlockedCount }} / {{ ctx.achievements.length }}</span>
          </div>

          <div class="setting-row">
            <span class="setting-copy"><strong>启用成就陈列柜</strong><small>记录资源整理、修复与收藏里程碑。</small></span>
            <button class="setting-switch" :class="{ on: ctx.achievementPreferences.enabled }" type="button" role="switch" :aria-checked="ctx.achievementPreferences.enabled" @click="ctx.updateAchievementPreference('enabled', !ctx.achievementPreferences.enabled)"><span></span></button>
          </div>
          <div class="setting-row" :class="{ disabled: !ctx.achievementPreferences.enabled }">
            <span class="setting-copy"><strong>解锁通知</strong><small>完成新成就时在应用内显示提示。</small></span>
            <button class="setting-switch" :class="{ on: ctx.achievementPreferences.notifications }" type="button" role="switch" :aria-checked="ctx.achievementPreferences.notifications" :disabled="!ctx.achievementPreferences.enabled" @click="ctx.updateAchievementPreference('notifications', !ctx.achievementPreferences.notifications)"><span></span></button>
          </div>
          <div class="setting-row" :class="{ disabled: !ctx.achievementPreferences.enabled }">
            <span class="setting-copy"><strong>隐藏未解锁成就</strong><small>总览仅展示已经完成的成就。</small></span>
            <button class="setting-switch" :class="{ on: ctx.achievementPreferences.hide_locked }" type="button" role="switch" :aria-checked="ctx.achievementPreferences.hide_locked" :disabled="!ctx.achievementPreferences.enabled" @click="ctx.updateAchievementPreference('hide_locked', !ctx.achievementPreferences.hide_locked)"><span></span></button>
          </div>

          <button class="settings-reset-button" type="button" @click="ctx.resetAchievementHistory">重置本地成就记录</button>
        </div>
      </section>

      <section class="panel settings-section settings-section--wide">
        <div class="settings-section-icon" aria-hidden="true">04</div>
        <div class="settings-section-body">
          <div class="settings-section-head">
            <div><h2>默认导出位置</h2><p>各工具仍可在执行时临时选择其他位置。</p></div>
          </div>

          <div class="settings-path-list">
            <div class="settings-path-row">
              <span class="setting-copy"><strong>通用导出目录</strong><small>{{ ctx.paths.outputDir || "尚未设置" }}</small></span>
              <button type="button" @click="ctx.selectSettingsDirectory('output')">选择目录</button>
            </div>
            <div class="settings-path-row">
              <span class="setting-copy"><strong>服装卡导出目录</strong><small>{{ ctx.coordinateExportDir || "尚未设置" }}</small></span>
              <button type="button" @click="ctx.selectSettingsDirectory('coordinate')">选择目录</button>
            </div>
            <div class="settings-path-row">
              <span class="setting-copy"><strong>便携依赖包目录</strong><small>{{ ctx.portablePackageDir || "尚未设置" }}</small></span>
              <button type="button" @click="ctx.selectSettingsDirectory('portable')">选择目录</button>
            </div>
          </div>

          <div class="setting-row setting-row--footer">
            <span class="setting-copy"><strong>依赖包默认压缩为 ZIP</strong><small>关闭后输出为便携文件夹。</small></span>
            <button class="setting-switch" :class="{ on: ctx.portablePackageCompress }" type="button" role="switch" :aria-checked="ctx.portablePackageCompress" @click="ctx.updatePortablePackageCompress(!ctx.portablePackageCompress)"><span></span></button>
          </div>
        </div>
      </section>

      <section class="panel settings-section settings-section--wide settings-section--blender">
        <div class="settings-section-icon" aria-hidden="true">05</div>
        <div class="settings-section-body">
          <div class="settings-section-head">
            <div><h2>Blender 集成</h2><p>用于 Package 导出阶段固化 T-Pose 并清除骨骼蒙皮，也可直接打开导出的 FBX。</p></div>
            <span class="settings-app-status" :class="{ configured: ctx.blenderExecutablePath }">
              <i></i>{{ ctx.blenderExecutablePath ? "已连接" : "未设置" }}
            </span>
          </div>

          <div class="blender-path-panel" :class="{ configured: ctx.blenderExecutablePath }">
            <span class="blender-app-mark" aria-hidden="true"><b>B</b><small>3D</small></span>
            <span class="setting-copy blender-path-copy">
              <strong>Blender 可执行文件</strong>
              <small :title="ctx.blenderExecutablePath">{{ ctx.blenderExecutablePath || "请选择 Blender 安装目录中的 blender.exe" }}</small>
            </span>
            <span class="blender-path-actions">
              <button type="button" class="blender-select-button" @click="ctx.selectBlenderExecutable">
                {{ ctx.blenderExecutablePath ? "更换路径" : "选择 blender.exe" }}
              </button>
              <button v-if="ctx.blenderExecutablePath" type="button" class="blender-clear-button" @click="ctx.clearBlenderExecutable">清除</button>
            </span>
          </div>

          <div class="blender-integration-note">
            <span>RIG + AUTO IMPORT</span>
            <p>导出时使用内置的 165 骨骼 TS4 模板绑定 GEOM 原始权重，并参照 HS2 固化为 T-Pose；打开模型时会保留 <code>textures</code> 相对路径。</p>
          </div>
        </div>
      </section>
    </div>
  </section>
</template>
