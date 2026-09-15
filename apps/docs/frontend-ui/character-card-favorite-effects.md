# 人物卡收藏视觉状态

## 当前结论

已收藏人物卡使用回退后的收藏视觉作为主要状态提示：网格与详情预览使用暖橙色边框扫光和轻微阴影，详情预览左上角保留黄色收藏星标。普通卡的名称铭牌继续使用白色半透明模糊玻璃样式；收藏卡使用不透明暖色渐变铭牌。

收藏状态由人物卡边框和详情预览中的收藏星标共同表示。人物卡详情中的收藏按钮继续独立工作，网格卡片不显示额外星标，避免遮挡缩略图。

设置中保留的收藏主题字段继续兼容已有配置；默认收藏卡使用暖橙边框扫光，主题 class 可恢复对应的边框主题特效，但不改变收藏卡的不透明铭牌规则。

## 当前模板结构

人物卡网格位于 `apps/src/components/views/CharactersView.vue`。关键结构为：

```text
.char-card
|-- .portrait
`-- .card-caption
    `-- strong
        `-- .card-name-text
```

收藏卡仍会添加 `favorite` class；旧配置对应的 `favorite-theme-neon`、`favorite-theme-sakura` 和 `favorite-theme-obsidian` class 仍可出现在模板中，用于恢复对应的边框扫光与主题边缘效果。收藏卡铭牌统一使用不透明暖色渐变。

模板不再输出 `data-name-effect`、`data-border-effect` 或 `.card-name-starlights`。

## 名字显示

- 收藏卡和普通卡统一使用 `13px` 字号。
- 名字在标题栏中水平、垂直居中。
- 普通卡名称条使用冷白半透明玻璃背景、轻微背景模糊、细白边和内沿高光；收藏卡名称条使用不透明暖色渐变、暖色边缘和深暖色粗体。
- 名字溢出时继续通过 `v-card-name-scroll` 指令滚动显示。
- `prefers-reduced-motion: reduce` 下名称滚动停止并使用省略显示；收藏卡边框扫光和铭牌动效同步停用。

## 设置与持久化

“开始游戏”页不提供“收藏卡片样式”设置；设置页的“人物卡外观”区域提供边框主题选择。

Electron 设置使用 `favoriteCardTheme` 保存主题，合法值为：

- `gold`：鎏金流彩（默认）
- `neon`：霓虹炫彩
- `sakura`：樱落绮梦
- `obsidian`：黑曜鎏火

前端状态、Electron 设置规范化以及卡片模板均不再读取或保存：

- `cardNameEffect`
- `cardBorderEffect`

旧版 `settings.json` 中即使残留这两个字段，也不会影响当前界面；后续保存设置时会由规范化流程自然丢弃。缺失或非法的 `favoriteCardTheme` 会回退为 `gold`；短期实现中出现过的 `favoriteCardFrameTheme` 会迁移到新字段。

## 修改规则

1. 收藏状态通过暖橙色边框和详情预览左上角的黄色星标表示；网格卡片不显示额外星标。
2. `.char-card.favorite` 与 `.card-detail-preview.favorite` 使用暖橙色 `4px` 边框、浅色卡面、边框扫光和轻微阴影，不对人物图使用滤镜。
3. `favorite-theme-neon`、`favorite-theme-sakura` 和 `favorite-theme-obsidian` 可恢复对应的边框渐变、扫光或边缘反射效果；这些主题不改变收藏卡铭牌的不透明暖色表面。
4. 普通卡的 `.card-caption` 使用共享白色透明玻璃铭牌；收藏卡的 `.card-caption` 使用不透明暖色渐变铭牌，不使用背景模糊。
5. 详情预览中的人物卡图像保持原图清晰度，不使用人物图滤镜或暗色遮罩；收藏星标不能遮挡人物图和其他详情操作。
6. 收藏边框特效保持低频、克制，并在 `prefers-reduced-motion: reduce` 下停用；名称溢出滚动不能阻挡卡片点击或键盘操作。
7. 收藏边框和铭牌不能遮挡选中勾选、缺失依赖徽标或详情操作按钮。

## 关键文件

- `apps/src/components/views/CharactersView.vue`：收藏 class、名字结构与溢出检测。
- `apps/src/components/views/SettingsView.vue`：完整人物卡主题选择与主题范围说明。
- `apps/src/styles.css`：普通卡片视觉、收藏边框与流光、详情预览边框和长名字滚动。
- `apps/src/App.vue`：收藏状态操作与全局上下文。
- `apps/electron/main.cjs`：应用设置规范化与持久化。

完成人物卡前端修改后，从 `apps/` 运行：

```powershell
npm run build
```
