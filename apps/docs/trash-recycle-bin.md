# 回收站

## 背景

人物卡和 zipmod 原先的删除操作会直接移除源文件。为了让清理操作可撤销，当前应用将这两类文件先移动到应用 runtime 下的回收站，再清理对应索引记录。

## 当前实现

- 回收站根目录：`<runtime>/trash/`。
- 人物卡：`<runtime>/trash/cards/<entry-id>/payload/<file>.png`。
- 模组：`<runtime>/trash/mods/<entry-id>/payload/<file>.zipmod`。
- 每个条目旁保存 `record.json`，记录原始绝对路径、游戏目录、相对路径、GUID、删除时间和删除原因。
- 应用导航新增“回收站”页面，可按“全部 / 人物卡 / 模组”筛选。
- “恢复”会移动回原始路径；如果原位置已有同名文件，恢复会停止并提示用户。
- 恢复模组后会调用单 zipmod 建库流程重新建立数据库记录；人物卡恢复后刷新卡片目录和列表。
- “永久删除”和“清空回收站”才会真正移除 runtime/trash 中的文件。

## 删除边界

- 批量人物卡删除和整包 zipmod 删除都会进入回收站。
- 删除 zipmod 内的单个物品时，应用仍然写回 zipmod 并移除 CSV 行；它不是独立文件，当前不会额外拆分为回收站条目。
- 重复模组清理、主模组替换重复项、合并重复模组产生的文件删除也进入模组回收站。
- 回收站条目不参与模组/人物卡扫描，直到用户恢复它。

## 验证

- `conda run -n mm_env python -m compileall -q backend/app backend/star_manager`
- `npm run build`（同时验证回收站页面的隐藏顶部栏布局）
- `apps/backend/tests/test_trash.py` 覆盖移动、恢复、同名冲突和永久删除。

## 测试残留排查记录

曾出现“每次启动应用，回收站都会新增 `Sample/old.zipmod` 和 `delete-me.png`”的现象。回收站记录中的 `source_path` 指向 `Temp\\tmp...`，说明它们不是启动流程或数据库增量建库产生的删除项，而是后端测试夹具。

根因是 `test_card_library_delete.py` 和 `test_duplicate_cleanup_policy.py` 直接调用真实的删除/重复模组替换逻辑，却没有临时覆盖 `star_manager.services.trash.TRASH_ROOT`。测试夹具被移入开发运行时的 `apps/backend/runtime/trash`，临时源目录随后被清理，导致这些不可恢复的测试文件在应用下次启动时仍被回收站页面读出。

当前两个测试均将 `TRASH_ROOT` 指向各自 `TemporaryDirectory` 下的 `runtime/trash`，测试结束后随临时目录一起清理；生产回收站路径和用户删除行为不变。排查时可通过回收站条目的 `source_path` 判断是否为测试残留：指向 `Temp\\tmp...` 且名称为测试夹具时，可在确认不是用户数据后清理对应条目。

验证：两个受影响测试通过，并确认测试运行前后开发运行时回收站条目数量不增加；`npm run build` 与 Python 编译检查也应继续通过。

## 页面空白排查记录

曾出现“回收站导航已选中，但右侧工作区完全空白”的现象。后端 `/trash` 能正常返回条目，且 `TrashView` 也已挂载；根因是回收站隐藏了全局顶部栏，却仍继承主布局的 `76px minmax(0, 1fr)` 两行网格。回收站页面被放进第一行，随后被工作区的 `overflow: hidden` 裁掉，因此连空状态也不可见。

当前 `.trash-main` 改为单行 `minmax(0, 1fr)` 布局，并让 `.trash-main .workspace` 从顶部开始且允许滚动。该规则与日志、插件、工作台和设置等隐藏顶部栏页面保持一致；它只影响回收站页面，不改变 runtime 路径或回收站接口。

排查时应先检查 `GET /health` 返回的 `runtime_dir`，再检查 `GET /trash` 的 `root` 和 `entries`。开发版默认读取 `apps/backend/runtime/trash`，打包版读取 exe 同级 `runtime/trash`；接口有条目但页面无任何 Hero/空状态时，优先检查主网格和工作区裁切，而不是误判为回收站数据为空。

## 适用边界

回收站是本地 runtime 数据，不会同步到游戏目录或外部云端。用户手动从文件管理器删除 `<runtime>/trash` 内容后，应用无法恢复对应条目；runtime 位置仍受 `STAR_MANAGER_RUNTIME_DIR` 控制，打包版位于 exe 同级的 `runtime`。
