# Star_Manager

[English](#english) · [简体中文](#star_manager-概览)

## English

Star_Manager is an open-source desktop manager for Honey Select 2 / AIS, built with Electron, Vue and a local Python backend. It requires no account or membership.

Use it to browse character, outfit and scene cards; manage zipmods and their items; inspect missing dependencies and duplicate resources; manage BepInEx plugins; and create mod projects in the Workbench. Maintenance tools can change game files, so review each operation's confirmation dialog.

### Language

The interface supports **English** and **简体中文**. Open **Settings → Startup and checks → Interface language** to switch immediately. The choice is saved automatically and restored on the next launch. English is the default when no language has been saved. This setting changes Star_Manager's interface; the game's own language option is separate.

File paths, mod/card names, tags, GUIDs and original third-party diagnostics retain their original content. Technical documentation under `apps/docs/` remains available in its original language.

### Getting started

Download a packaged release from this repository's Releases page and extract it to a suitable folder, preferably on a data drive. Launch `Star_Manager.exe`, choose your HS2 game folder, and build the resource database.

To run from source, install Node.js and a Python environment with the dependencies in `apps/backend/requirements.txt`, then:

```powershell
cd apps
npm ci
# Set this to your Python executable.
$env:PYTHON_EXECUTABLE = "C:\path\to\python.exe"
& $env:PYTHON_EXECUTABLE -m pip install -r backend/requirements.txt
npm run dev
```

Build the renderer with `npm run build`. To produce the Windows application, follow the [Windows packaging guide](apps/docs/packaging-windows.md); it also requires PyInstaller, the bundled companion DLLs and the remote mod index. See the [application README](apps/README.md) for architecture and commands, and the [localization guide](apps/docs/frontend-ui/localization.md) for translation maintenance.

You can also ask your coding agent:

> Clone https://github.com/lunaburg/Star_Manager.git, install all required dependencies, and run it locally.

**The author's stated restriction: this project must not be monetized in any form, including sponsorship.**

## Star_Manager 概览

界面支持 English / 简体中文，可在“设置 → 启动与检查 → 界面语言”中即时切换并自动保存。未保存语言时默认使用英语。

本应用无需登陆，没有会员，不用担心作者跑路用不了

自定义游戏管理器，这是一个开源的vibecodeing项目，旨在帮助hs2游戏玩家更快的融入AI

不管你是新手小白还是老东西，希望这个项目能帮到你们

那么这个项目能做什么：帮你管理mod、解决疑难杂症、自定义属于自己独一无二的游戏管理器、修复损坏（破解加密）mod、帮你写插件、在你的不断提问中变得更加聪明。。。

如何开始？

  打开你的agent，然后将下面这段话粘贴到对话栏里
  
  “https://github.com/lunaburg/Star_Manager.git  帮我拉取这个github项目并在本地运行，帮我补全运行该项目所需的全部依赖”
  
  若不想使用ai本地编译部署也没有关系，右方会定时上传打包版应用发布，只需选择合适的文件夹解压即可，推荐放在数据盘

  郑重声明：本项目不得以任何形式收费，包括赞助

## 页面概览
![页面截图 1 (17)](apps/docs/assets/page-screenshots/1%20%2817%29.png)
![页面截图 1 (18)](apps/docs/assets/page-screenshots/1%20%2818%29.png)
![页面截图 1 (19)](apps/docs/assets/page-screenshots/1%20%2819%29.png)
![页面截图 1 (20)](apps/docs/assets/page-screenshots/1%20%2820%29.png)
![页面截图 1 (22)](apps/docs/assets/page-screenshots/1%20%2822%29.png)
![页面截图 1 (23)](apps/docs/assets/page-screenshots/1%20%2823%29.png)
![页面截图 1 (24)](apps/docs/assets/page-screenshots/1%20%2824%29.png)
![页面截图 1 (27)](apps/docs/assets/page-screenshots/1%20%2827%29.png)
![页面截图 1 (25)](apps/docs/assets/page-screenshots/1%20%2825%29.png)
![页面截图 1 (26)](apps/docs/assets/page-screenshots/1%20%2826%29.png)
