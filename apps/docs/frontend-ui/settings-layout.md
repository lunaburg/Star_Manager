# 设置页布局

## 目标

设置页集中管理 Star_Manager 自身的启动行为、资源检查策略、人物卡主题、本地成就偏好、默认导出目录、便携依赖包偏好和 Blender 集成。设置保存在 Electron 用户数据目录的 `settings.json`，不是 HS2 的 `UserData/setup.xml`。

## 当前分区

页面目前包含五个区块：

1. **启动与检查**：启动页面、启动时是否检查 zipmod/人物卡资源变化；默认启动页为“开始游戏”。
2. **收藏人物卡主题**：`gold`、`neon`、`sakura`、`obsidian` 四种主题，统一控制收藏卡框、名字铭牌/字体和详情卡面效果。
3. **本地成就**：启用记录、解锁通知、隐藏未解锁项目，以及重置本地成就记录。
4. **默认导出位置**：通用导出目录、服装卡导出目录、便携依赖包目录；同时设置便携包默认 ZIP/文件夹输出。
5. **Blender 集成**：选择、替换或清除 `blender.exe` 路径，用于工作台 T-Pose 固化和打开导出的 FBX。

所有设置变更都会立即调用 Electron 的 `saveSettings`，页面显示保存成功或失败提示。便携依赖包的五类模组选择在生成弹窗中调整，并与压缩偏好和目录一起持久化。

## 持久化字段

`apps/electron/main.cjs` 的 `normalizeSettings()` 会限制合法值并提供默认值。当前字段为：

```text
gameDir
inputDir
outputDir
coordinateExportDir
portablePackageDir
blenderExecutablePath
portablePackageCompress
portablePackageTypes: face | hair | body | clothes | accessory
startupView: start | overview | characters | mods | workbench | plugins | logs | settings
favoriteCardTheme: gold | neon | sakura | obsidian
checkDatabaseChangesOnStartup
```

旧设置中的 `favoriteCardFrameTheme` 会迁移到 `favoriteCardTheme`；非法主题和启动页会回退到默认值。旧的 `cardNameEffect`、`cardBorderEffect` 不再参与当前界面。

## 本地成就

成就数据单独保存在 SQLite 的 `achievement_progress`、`achievement_events` 和 `achievement_preferences` 表中。成就统计覆盖人物卡数量、零缺失扫描、同 GUID 版本、重复资源清理空间和资源修复次数。关闭成就后不再记录新的事件；重置只清理成就进度和事件，不删除资源索引。

## 与其他页面的边界

- 开始页的 `UserData/setup.xml` 配置区目前仍是前端占位状态，不能把它当作设置页的持久化字段。
- 工作台更换通用导出目录会复用设置页的 `outputDir`。
- 角色卡主题的详细 CSS 和模板规则见[人物卡收藏视觉状态](character-card-favorite-effects.md)。

## 相关代码

- `apps/src/components/views/SettingsView.vue`
- `apps/src/App.vue`：设置加载、保存和页面上下文
- `apps/electron/main.cjs`：设置规范化和用户数据文件读写
- `apps/backend/star_manager/services/achievements.py`：本地成就表和接口
