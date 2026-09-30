# Electron 进程生命周期

## 背景

Star_Manager 的 Electron 主进程会启动本地 Python HTTP 后端。Windows 下如果只结束 Electron 直接创建的子进程，经过包装进程启动的 Python 后端或其他后端子进程可能继续运行，形成残留的 `star_manager_backend.exe` / Python 进程。重复启动应用还可能创建多个 Electron 与后端实例。

## 解决方案

- Electron 启动时调用 `app.requestSingleInstanceLock()`。第二次启动不会创建新的应用窗口，而是唤起已有窗口。
- Electron 到本地后端的临时网络重试只适用于 `GET`、`HEAD` 和 `OPTIONS`；恢复、删除和其他 `POST` 变更只会提交一次，避免响应丢失时重复执行文件移动。
- Electron 退出统一经过 `before-quit`，先阻止默认退出，再等待后端清理完成。
- Windows 使用 `taskkill.exe /PID <pid> /T /F` 清理后端进程树，覆盖直接启动的 PyInstaller 后端和带包装进程的开发启动路径。
- Electron 本次启动的后端在进程树清理后还会按监听端口复查并重试结束残留进程；即使包装进程先触发 `exit`，也不会丢失清理目标。端口清理同样使用递归进程树结束，并在 Windows PowerShell 查询不可用时回退到 `netstat -ano`。
- Linux/macOS 保留向子进程发送 `SIGTERM` 的行为。
- renderer 崩溃和关闭全部窗口时只请求 Electron 退出，由统一的 `before-quit` 路径负责后端清理，避免多个退出路径互相竞态。
- 后端的父进程监视线程在 Electron 异常退出后关闭 HTTP 服务监听，避免监听套接字继续占用端口。

## 验证

- `npm run test:electron`：验证 Windows 使用 `/T /F`，并验证非 Windows 的 `SIGTERM` 回退。
- `npm run build`：验证新增生命周期模块会被 Electron 打包输入包含。
- Windows 手工验证：启动应用后关闭窗口，确认对应的 `star_manager_backend.exe` 及其子进程退出，并确认后端端口不再处于监听状态；再次启动应用只出现一个主窗口。

## 边界

单实例锁只约束 Star_Manager 自身的 Electron 实例，不会接管用户手动启动的独立 Python 后端。应用复用兼容后端时仍不会拥有该后端的退出责任；生产打包路径通常由当前 Electron 直接启动后端，并会在退出时清理其进程树。
