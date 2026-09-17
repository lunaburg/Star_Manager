<script setup>
import { onBeforeUnmount, onMounted, ref } from "vue";

import blenderIcon from "../../assets/blender-icon.png";
import sb3utilityIcon from "../../assets/sb3utility-icon.png";

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

const settingNavGroups = [
  {
    label: "启动与外观",
    items: [
      { id: "startup", label: "启动与检查" },
      { id: "wallpaper", label: "应用壁纸" }
    ]
  },
  {
    label: "性能",
    items: [
      { id: "database", label: "数据库构建" }
    ]
  },
  {
    label: "记录与输出",
    items: [
      { id: "appearance", label: "收藏主题" },
      { id: "achievements", label: "本地成就" },
      { id: "paths", label: "导出位置" }
    ]
  },
  {
    label: "工具",
    items: [
      { id: "tools", label: "外部工具" }
    ]
  }
];

const settingsContentRef = ref(null);
const activeSection = ref("startup");

function updateActiveSection() {
  const content = settingsContentRef.value;
  if (!content) return;

  const sections = [...content.querySelectorAll("[data-settings-section]")];
  if (!sections.length) return;

  const contentTop = content.getBoundingClientRect().top;
  const current = sections.reduce((candidate, section) => {
    if (section.getBoundingClientRect().top <= contentTop + 1) {
      return section;
    }
    return candidate;
  }, null) || sections[0];

  const sectionId = current.dataset.settingsSection;
  if (sectionId) {
    activeSection.value = sectionId;
  }
}

function scrollToSection(id) {
  const section = settingsContentRef.value?.querySelector(`#settings-${id}`);
  section?.scrollIntoView({ behavior: "smooth", block: "start" });
}

onMounted(() => {
  const content = settingsContentRef.value;
  if (!content) return;

  content.addEventListener("scroll", updateActiveSection, { passive: true });
  updateActiveSection();
});

onBeforeUnmount(() => {
  settingsContentRef.value?.removeEventListener("scroll", updateActiveSection);
});
</script>

<template>
  <section class="view settings-view">
    <div class="settings-page-shell">
      <aside class="settings-sidebar" aria-label="设置导航">
        <div class="settings-sidebar-brand">
          <span class="settings-sidebar-brand-copy">
            <strong>设置</strong>
          </span>
        </div>

        <nav class="settings-sidebar-nav">
          <div v-for="group in settingNavGroups" :key="group.label" class="settings-sidebar-group">
            <span class="settings-sidebar-group-label">{{ group.label }}</span>
            <button
              v-for="item in group.items"
              :key="item.id"
              type="button"
              class="settings-sidebar-item"
              :class="{ active: activeSection === item.id }"
              :aria-current="activeSection === item.id ? 'page' : undefined"
              @click="scrollToSection(item.id)"
            >
              <span>{{ item.label }}</span>
            </button>
          </div>
        </nav>

        <div class="settings-sidebar-footer">
          <span class="settings-sidebar-footer-dot" aria-hidden="true"></span>
          <span>本地设置</span>
          <small>自动保存</small>
        </div>
      </aside>

      <main ref="settingsContentRef" class="settings-content">
        <div class="settings-layout">
      <section id="settings-startup" data-settings-section="startup" class="panel settings-section settings-section--startup">
        <div class="settings-section-body">
          <div class="settings-section-head">
            <div>
              <h2>启动与检查</h2>
            </div>
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
        </div>
      </section>

      <section id="settings-wallpaper" data-settings-section="wallpaper" class="panel settings-section settings-section--wallpaper">
        <div class="settings-section-body">
          <div class="settings-section-head">
            <div>
              <h2>应用壁纸</h2>
            </div>
            <span class="settings-app-status" :class="{ configured: ctx.managerSettings.wallpaperPath }">
              <i></i>{{ ctx.managerSettings.wallpaperPath ? "已配置" : "默认壁纸" }}
            </span>
          </div>

          <div class="wallpaper-setting-card">
            <div class="wallpaper-setting-preview" aria-hidden="true">
              <video v-if="ctx.wallpaperIsVideo" :src="ctx.wallpaperSource" muted autoplay loop playsinline></video>
              <img v-else :src="ctx.wallpaperSource" alt="" />
              <span>{{ ctx.wallpaperIsVideo ? "MP4" : "IMAGE" }}</span>
            </div>
            <div class="wallpaper-setting-copy">
              <strong>{{ ctx.managerSettings.wallpaperPath || "使用内置默认壁纸" }}</strong>
              <small>支持 PNG、JPG、WebP、GIF 与 MP4。视频会自动静音循环播放，并始终位于所有页面内容的最底层。</small>
              <div class="wallpaper-setting-actions">
                <button type="button" class="primary" @click="ctx.selectWallpaper">选择图片或 MP4</button>
                <button v-if="ctx.managerSettings.wallpaperPath" type="button" @click="ctx.clearWallpaper">恢复默认</button>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="settings-database" data-settings-section="database" class="panel settings-section settings-section--database">
        <div class="settings-section-body">
          <div class="settings-section-head">
            <div>
              <h2>数据库构建</h2>
            </div>
          </div>

          <label class="setting-row setting-row--select">
            <span class="setting-copy"><strong>建库线程数</strong><small>请选择合适的线程数，不一定越高越好</small></span>
            <select
              :value="ctx.managerSettings.databaseWorkerCount"
              aria-label="数据库构建线程数"
              @change="ctx.updateDatabaseWorkerCount($event.target.value)"
            >
              <option v-for="count in ctx.databaseWorkerOptions" :key="count" :value="count">{{ count }} 线程</option>
            </select>
          </label>

        </div>
      </section>

      <section id="settings-appearance" data-settings-section="appearance" class="panel settings-section">
        <div class="settings-section-body">
          <div class="settings-section-head">
            <div>
              <h2>收藏主题</h2>
            </div>
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
        </div>
      </section>

      <section id="settings-achievements" data-settings-section="achievements" class="panel settings-section settings-section--achievements">
        <div class="settings-section-body">
          <div class="settings-section-head">
            <div>
              <h2>本地成就</h2>
            </div>
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

      <section id="settings-paths" data-settings-section="paths" class="panel settings-section settings-section--wide">
        <div class="settings-section-body">
          <div class="settings-section-head">
            <div>
              <h2>导出位置</h2>
            </div>
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

      <section id="settings-tools" data-settings-section="tools" class="panel settings-section settings-section--wide settings-section--blender">
        <div class="settings-section-body">
          <div class="settings-section-head">
            <div>
              <h2>外部工具</h2>
            </div>
            <span class="settings-app-status" :class="{ configured: ctx.blenderExecutablePath || ctx.sb3utilityExecutablePath }">
              <i></i>{{ ctx.blenderExecutablePath || ctx.sb3utilityExecutablePath ? "已配置" : "未设置" }}
            </span>
          </div>

          <div class="blender-path-panel" :class="{ configured: ctx.blenderExecutablePath }">
            <span class="blender-app-mark blender-app-mark--image" aria-hidden="true"><img class="blender-app-icon" :src="blenderIcon" alt="" /></span>
            <span class="setting-copy blender-path-copy">
              <strong>Blender</strong>
              <small :title="ctx.blenderExecutablePath">{{ ctx.blenderExecutablePath || "请选择 Blender.exe" }}</small>
            </span>
            <span class="blender-path-actions">
              <button type="button" class="blender-select-button" @click="ctx.selectBlenderExecutable">
                选择
              </button>
              <button v-if="ctx.blenderExecutablePath" type="button" class="blender-clear-button" @click="ctx.clearBlenderExecutable">清除</button>
            </span>
          </div>

          <div class="blender-path-panel" :class="{ configured: ctx.sb3utilityExecutablePath }">
            <span class="blender-app-mark blender-app-mark--image" aria-hidden="true"><img class="blender-app-icon" :src="sb3utilityIcon" alt="" /></span>
            <span class="setting-copy blender-path-copy">
              <strong>SB3Utility</strong>
              <small :title="ctx.sb3utilityExecutablePath">{{ ctx.sb3utilityExecutablePath || "请选择 SB3Utility.exe" }}</small>
            </span>
            <span class="blender-path-actions">
              <button type="button" class="blender-select-button" @click="ctx.selectSb3UtilityExecutable">
                选择
              </button>
              <button v-if="ctx.sb3utilityExecutablePath" type="button" class="blender-clear-button" @click="ctx.resetSb3UtilityExecutable">清除</button>
            </span>
          </div>

        </div>
      </section>
        </div>
      </main>
    </div>
  </section>
</template>
