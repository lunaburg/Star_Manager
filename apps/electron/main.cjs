const { app, BrowserWindow, Menu, dialog, ipcMain, shell } = require("electron");
const { execFile, spawn } = require("node:child_process");
const fs = require("node:fs");
const net = require("node:net");
const path = require("node:path");

const rendererUrl = process.env.ELECTRON_RENDERER_URL || "";
const isDev = Boolean(rendererUrl);
const expectedBackendRevision = "sims4-workbench-tpose-mesh-v2";
const disableGpu = process.env.STAR_MANAGER_DISABLE_GPU === "1";
if (disableGpu) {
  app.disableHardwareAcceleration();
  app.commandLine.appendSwitch("disable-gpu");
  app.commandLine.appendSwitch("disable-gpu-compositing");
  app.commandLine.appendSwitch("disable-d3d11");
}
app.commandLine.appendSwitch("disable-features", "CalculateNativeWinOcclusion");
let backendPort = process.env.STAR_MANAGER_BACKEND_PORT || "8765";
let backendProcess = null;
let backendStopRequested = false;
const gameExecutables = {
  game: "HoneySelect2.exe",
  studio: "StudioNEOV2.exe",
  vr: "HoneySelect2VR.exe"
};

function hrtimeMs(startTime) {
  return Number(process.hrtime.bigint() - startTime) / 1e6;
}

function formatDurationMs(durationMs) {
  return `${durationMs >= 100 ? durationMs.toFixed(0) : durationMs.toFixed(1)} ms`;
}

function logStartupStep(step, startTime, detail = "") {
  const suffix = detail ? ` ${detail}` : "";
  console.log(`[startup] ${step} completed in ${formatDurationMs(hrtimeMs(startTime))}${suffix}`);
}

function settingsPath() {
  return path.join(app.getPath("userData"), "settings.json");
}

function normalizeSettings(settings = {}) {
  const allowedStartupViews = new Set(["start", "overview", "characters", "mods", "workbench", "plugins", "logs", "settings"]);
  const allowedFavoriteCardThemes = new Set(["gold", "neon", "sakura", "obsidian"]);
  const allowedPortablePackageTypes = ["face", "hair", "body", "clothes", "accessory"];
  const startupView = String(settings.startupView || "start");
  const favoriteCardTheme = String(settings.favoriteCardTheme || settings.favoriteCardFrameTheme || "gold");
  const portablePackageTypes = Array.isArray(settings.portablePackageTypes)
    ? allowedPortablePackageTypes.filter((type) => settings.portablePackageTypes.includes(type))
    : [...allowedPortablePackageTypes];
  return {
    gameDir: String(settings.gameDir || ""),
    inputDir: String(settings.inputDir || ""),
    outputDir: String(settings.outputDir || ""),
    coordinateExportDir: String(settings.coordinateExportDir || ""),
    portablePackageDir: String(settings.portablePackageDir || ""),
    blenderExecutablePath: String(settings.blenderExecutablePath || ""),
    portablePackageCompress: settings.portablePackageCompress !== false,
    portablePackageTypes,
    startupView: allowedStartupViews.has(startupView) ? startupView : "start",
    favoriteCardTheme: allowedFavoriteCardThemes.has(favoriteCardTheme) ? favoriteCardTheme : "gold",
    checkDatabaseChangesOnStartup: settings.checkDatabaseChangesOnStartup !== false
  };
}

function loadSettingsFile() {
  const filePath = settingsPath();
  try {
    if (!fs.existsSync(filePath)) {
      const emptySettings = normalizeSettings();
      fs.mkdirSync(path.dirname(filePath), { recursive: true });
      fs.writeFileSync(filePath, JSON.stringify(emptySettings, null, 2), "utf-8");
      return { ok: true, settings: emptySettings, path: filePath };
    }
    const settings = normalizeSettings(JSON.parse(fs.readFileSync(filePath, "utf-8")));
    return { ok: true, settings, path: filePath };
  } catch (error) {
    return { ok: false, settings: normalizeSettings(), path: filePath, error: error.message };
  }
}

function saveSettingsFile(settings = {}) {
  const filePath = settingsPath();
  const normalized = normalizeSettings(settings);
  try {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, JSON.stringify(normalized, null, 2), "utf-8");
    return { ok: true, settings: normalized, path: filePath };
  } catch (error) {
    return { ok: false, settings: normalized, path: filePath, error: error.message };
  }
}

function runtimeDir() {
  if (app.isPackaged) {
    return path.join(path.dirname(app.getPath("exe")), "runtime");
  }
  return path.join(__dirname, "../backend/runtime");
}

function clearModelPreviewCache() {
  const cacheDir = path.join(runtimeDir(), "model_previews");
  try {
    fs.rmSync(cacheDir, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
    console.log(`[cache] cleared 3D model previews: ${cacheDir}`);
  } catch (error) {
    console.warn(`[cache] failed to clear 3D model previews at ${cacheDir}: ${error.message}`);
  }
}

function createWindow() {
  const createWindowStart = process.hrtime.bigint();
  process.env.STAR_MANAGER_BACKEND_BASE_URL = `http://127.0.0.1:${backendPort}`;
  const window = new BrowserWindow({
    width: 1420,
    height: 900,
    minWidth: 1180,
    minHeight: 780,
    title: "Star_Manager",
    icon: path.join(__dirname, "../build-resources/app-icon.png"),
    backgroundColor: "#00000000",
    titleBarStyle: "hidden",
    titleBarOverlay: {
      color: "#00000000",
      symbolColor: "#2d2930",
      height: 38
    },
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });
  logStartupStep("BrowserWindow constructed", createWindowStart);

  const pageLoadStart = process.hrtime.bigint();
  const logPageLoadStep = (step) => {
    console.log(`[startup] renderer ${step} at ${formatDurationMs(hrtimeMs(pageLoadStart))}`);
  };
  window.webContents.once("did-start-loading", () => {
    logPageLoadStep("did-start-loading");
  });
  window.webContents.once("dom-ready", () => {
    logPageLoadStep("dom-ready");
  });
  window.webContents.once("did-finish-load", () => {
    logPageLoadStep("did-finish-load");
  });
  window.webContents.once("did-fail-load", (_event, errorCode, errorDescription) => {
    console.error(
      `[startup] renderer did-fail-load at ${formatDurationMs(hrtimeMs(pageLoadStart))} code=${errorCode} ${errorDescription}`
    );
  });
  window.webContents.on("render-process-gone", (_event, details) => {
    console.error(`[renderer] process gone reason=${details.reason} exitCode=${details.exitCode}`);
    shutdownBackend("renderer process ended");
    if (!app.isQuitting) {
      app.quit();
    }
  });
  window.webContents.on("unresponsive", () => {
    console.warn("[renderer] window became unresponsive");
  });

  if (rendererUrl) {
    window.loadURL(rendererUrl);
  } else {
    window.loadFile(path.join(__dirname, "../dist/index.html"));
  }
  logStartupStep("createWindow load request", createWindowStart, isDev ? "(loadURL)" : "(loadFile)");
}

async function startPythonBackend() {
  const startTime = process.hrtime.bigint();
  console.log(`[startup] startPythonBackend begin (port=${backendPort})`);

  const reuseCheckStart = process.hrtime.bigint();
  if (await reuseCompatibleBackend()) {
    logStartupStep("reuseCompatibleBackend", reuseCheckStart, `(port=${backendPort})`);
    logStartupStep("startPythonBackend", startTime, "(reused existing backend)");
    return;
  }
  logStartupStep("reuseCompatibleBackend", reuseCheckStart, "(no reusable backend)");

  if (!process.env.STAR_MANAGER_BACKEND_PORT && (await isPortInUse(backendPort))) {
    const portProbeStart = process.hrtime.bigint();
    const stalePort = backendPort;
    backendPort = String(await findFreePort());
    console.warn(`[backend] port ${stalePort} is occupied by an incompatible backend; using ${backendPort}`);
    logStartupStep("findFreePort", portProbeStart, `(old=${stalePort}, new=${backendPort})`);
  }

  const backendEntry = path.join(__dirname, "../backend/app/server.py");
  const backendRoot = path.join(__dirname, "../backend");
  const backendExecutable = resolveBackendExecutable();
  const pythonExecutable = resolvePythonExecutable();
  const command = backendExecutable || pythonExecutable || "conda";
  const args = backendExecutable
    ? []
    : pythonExecutable
    ? [backendEntry]
    : ["run", "-n", process.env.STAR_MANAGER_CONDA_ENV || "mm_env", "python", backendEntry];

  console.log(`[backend] starting: ${command} ${args.join(" ")}`);
  const spawnStart = process.hrtime.bigint();
  backendProcess = spawn(command, args, {
    cwd: backendExecutable ? path.dirname(backendExecutable) : backendRoot,
    env: {
      ...process.env,
      STAR_MANAGER_PARENT_PID: String(process.pid),
      STAR_MANAGER_RUNTIME_DIR: runtimeDir(),
      STAR_MANAGER_BACKEND_PORT: backendPort
    },
    stdio: "inherit",
    windowsHide: true
  });
  logStartupStep("spawn backend process", spawnStart, `(pid=${backendProcess.pid || "unknown"}, port=${backendPort})`);

  backendProcess.on("error", (error) => {
    console.error("[backend] failed to start:", error);
  });

  backendProcess.on("exit", (code, signal) => {
    const level = backendStopRequested ? "log" : "error";
    console[level](`[backend] exited code=${code} signal=${signal}`);
    backendProcess = null;
  });

  logStartupStep("startPythonBackend", startTime, `(pid=${backendProcess.pid || "unknown"}, port=${backendPort})`);
}

async function reuseCompatibleBackend() {
  const health = await fetchBackendOnce("/health");
  if (!health.ok) {
    return false;
  }

  const supportedTasks = Array.isArray(health.payload.supported_task_types)
    ? health.payload.supported_task_types
    : [];
  const supportedRoutes = Array.isArray(health.payload.supported_api_routes)
    ? health.payload.supported_api_routes
    : [];
  const backendRevision = String(health.payload.backend_revision || "");
  if (backendRevision !== expectedBackendRevision) {
    console.warn(
      `[backend] existing backend revision ${backendRevision || "(missing)"} does not match ${expectedBackendRevision}`
    );
    if (health.payload.service === "Star_Manager" && !process.env.STAR_MANAGER_BACKEND_PORT) {
      await stopProcessOnPort(backendPort);
      await waitForPortToClose(backendPort);
    }
    return false;
  }
  if (
    supportedTasks.includes("build_mod_database") &&
    supportedRoutes.includes("/library/cards") &&
    supportedRoutes.includes("/library/cards/tree")
  ) {
    const expectedRuntimeDir = path.normalize(runtimeDir());
    const backendRuntimeDir = path.normalize(String(health.payload.runtime_dir || ""));
    if (backendRuntimeDir && backendRuntimeDir !== expectedRuntimeDir) {
      console.warn(
        `[backend] existing backend runtime dir ${backendRuntimeDir} does not match expected runtime dir ${expectedRuntimeDir}`
      );
      if (health.payload.service === "Star_Manager" && !process.env.STAR_MANAGER_BACKEND_PORT) {
        await stopProcessOnPort(backendPort);
        await waitForPortToClose(backendPort);
      }
      return false;
    }
    console.log(`[backend] reusing compatible backend on port ${backendPort}`);
    return true;
  }

  if (process.env.STAR_MANAGER_BACKEND_PORT) {
    console.warn(`[backend] existing backend on port ${backendPort} does not support the current app API`);
    return true;
  }

  if (health.payload.service === "Star_Manager") {
    console.warn(`[backend] stopping incompatible Star_Manager backend on port ${backendPort}`);
    await stopProcessOnPort(backendPort);
    await waitForPortToClose(backendPort);
  }

  return false;
}

async function fetchBackendOnce(route) {
  try {
    const response = await fetch(`http://127.0.0.1:${backendPort}${route}`);
    return { ok: true, payload: await response.json() };
  } catch (error) {
    return { ok: false, error };
  }
}

function isPortInUse(port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.once("error", () => resolve(true));
    server.once("listening", () => {
      server.close(() => resolve(false));
    });
    server.listen(Number(port), "127.0.0.1");
  });
}

function findFreePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once("error", reject);
    server.once("listening", () => {
      const address = server.address();
      server.close(() => resolve(address.port));
    });
    server.listen(0, "127.0.0.1");
  });
}

async function waitForPortToClose(port) {
  for (let attempt = 0; attempt < 20; attempt += 1) {
    if (!(await isPortInUse(port))) {
      return true;
    }
    await sleep(100);
  }

  return false;
}

async function stopProcessOnPort(port) {
  const pids = await findProcessIdsOnPort(port);
  const currentPid = String(process.pid);
  await Promise.all(
    pids
      .filter((pid) => pid && pid !== currentPid)
      .map((pid) => killProcess(pid))
  );
}

function findProcessIdsOnPort(port) {
  if (process.platform === "win32") {
    return execFileText("powershell.exe", [
      "-NoProfile",
      "-Command",
      [
        `$items = Get-NetTCPConnection -LocalPort ${Number(port)} -State Listen -ErrorAction SilentlyContinue`,
        "$items | Select-Object -ExpandProperty OwningProcess -Unique"
      ].join("; ")
    ]).then((output) => output.split(/\s+/).filter(Boolean));
  }

  return execFileText("lsof", ["-ti", `tcp:${port}`]).then(
    (output) => output.split(/\s+/).filter(Boolean),
    () => []
  );
}

function killProcess(pid) {
  if (process.platform === "win32") {
    return execFileText("taskkill.exe", ["/PID", pid, "/F"]).catch((error) => {
      console.warn(`[backend] failed to stop process ${pid}: ${error.message}`);
    });
  }

  return execFileText("kill", ["-TERM", pid]).catch((error) => {
    console.warn(`[backend] failed to stop process ${pid}: ${error.message}`);
  });
}

function shutdownBackend(reason = "app shutdown") {
  if (!backendProcess || backendProcess.killed) {
    return;
  }

  backendStopRequested = true;
  console.log(`[backend] stopping because ${reason}`);
  backendProcess.kill();
}

function execFileText(command, args) {
  return new Promise((resolve, reject) => {
    execFile(command, args, { windowsHide: true }, (error, stdout, stderr) => {
      if (error) {
        error.message = stderr || error.message;
        reject(error);
        return;
      }
      resolve(stdout.trim());
    });
  });
}

function resolveBackendExecutable() {
  const candidates = [
    process.env.STAR_MANAGER_BACKEND_EXE,
    app.isPackaged
      ? path.join(process.resourcesPath, "backend", "star_manager_backend.exe")
      : ""
  ].filter(Boolean);

  return candidates.find((candidate) => fs.existsSync(candidate)) || "";
}

function resolvePythonExecutable() {
  const candidates = [
    process.env.PYTHON_EXECUTABLE,
    "D:\\desktop_app\\anaconda\\envs\\mm_env\\python.exe"
  ].filter(Boolean);

  return candidates.find((candidate) => fs.existsSync(candidate)) || "";
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function fetchBackend(route, options = {}) {
  const url = `http://127.0.0.1:${backendPort}${route}`;
  const fetchOptions = {
    method: options.method || "GET",
    headers: {
      "content-type": "application/json",
      ...(options.headers || {})
    },
    body: options.body ? JSON.stringify(options.body) : undefined
  };

  let lastError;
  for (let attempt = 0; attempt < 20; attempt += 1) {
    try {
      const response = await fetch(url, fetchOptions);
      return response.json();
    } catch (error) {
      lastError = error;
      await sleep(250);
    }
  }

  return {
    ok: false,
    error: `Python backend unavailable: ${lastError ? lastError.message : "unknown error"}`
  };
}

ipcMain.handle("dialog:selectDirectory", async (_event, title) => {
  const result = await dialog.showOpenDialog({
    title,
    properties: ["openDirectory"]
  });
  return result.canceled ? "" : result.filePaths[0];
});

ipcMain.handle("dialog:selectPackageFile", async (_event, title) => {
  const result = await dialog.showOpenDialog({
    title,
    properties: ["openFile"],
    filters: [
      { name: "The Sims 4 Package", extensions: ["package"] }
    ]
  });
  return result.canceled ? "" : result.filePaths[0];
});

ipcMain.handle("dialog:selectImageFile", async (_event, title) => {
  const result = await dialog.showOpenDialog({
    title,
    properties: ["openFile"],
    filters: [
      { name: "PNG Images", extensions: ["png"] }
    ]
  });
  return result.canceled ? "" : result.filePaths[0];
});

ipcMain.handle("dialog:selectImageForCrop", async (_event, title) => {
  const result = await dialog.showOpenDialog({
    title,
    properties: ["openFile"],
    filters: [
      { name: "Images", extensions: ["png", "jpg", "jpeg", "webp"] }
    ]
  });
  if (result.canceled || !result.filePaths[0]) return null;

  const filePath = result.filePaths[0];
  try {
    const stat = await fs.promises.stat(filePath);
    if (!stat.isFile()) return { ok: false, error: "所选路径不是图片文件。" };
    if (stat.size > 50 * 1024 * 1024) return { ok: false, error: "封面图片不能超过 50 MB。" };
    const extension = path.extname(filePath).toLowerCase();
    const mimeTypes = {
      ".png": "image/png",
      ".jpg": "image/jpeg",
      ".jpeg": "image/jpeg",
      ".webp": "image/webp"
    };
    const mimeType = mimeTypes[extension];
    if (!mimeType) return { ok: false, error: "请选择 PNG、JPG 或 WebP 图片。" };
    const data = await fs.promises.readFile(filePath);
    return {
      ok: true,
      path: filePath,
      name: path.basename(filePath),
      dataUrl: `data:${mimeType};base64,${data.toString("base64")}`
    };
  } catch (error) {
    return { ok: false, error: `图片读取失败：${error.message}` };
  }
});

ipcMain.handle("dialog:selectBlenderExecutable", async (_event, title) => {
  const result = await dialog.showOpenDialog({
    title,
    properties: ["openFile"],
    filters: [
      { name: "Blender Executable", extensions: ["exe"] }
    ]
  });
  return result.canceled ? "" : result.filePaths[0];
});

ipcMain.handle("dialog:promptText", async (_event, title, message, defaultValue = "") => {
  const window = BrowserWindow.getFocusedWindow() || BrowserWindow.getAllWindows()[0];
  if (!window) {
    return "";
  }
  const result = await dialog.showMessageBox(window, {
    type: "question",
    buttons: ["取消", "确定"],
    defaultId: 1,
    cancelId: 0,
    title,
    message,
    detail: defaultValue ? `默认值：${defaultValue}` : ""
  });
  return result.response === 1 ? String(defaultValue || "").trim() : "";
});

ipcMain.handle("backend:request", async (_event, route, options = {}) => {
  return fetchBackend(route, options);
});

ipcMain.handle("settings:load", async () => {
  return loadSettingsFile();
});

ipcMain.handle("settings:save", async (_event, settings) => {
  return saveSettingsFile(settings);
});

ipcMain.handle("shell:showItemInFolder", async (_event, filePath) => {
  if (!filePath || !fs.existsSync(filePath)) {
    return { ok: false, error: "File not found" };
  }
  shell.showItemInFolder(filePath);
  return { ok: true };
});

ipcMain.handle("game:launchExecutable", async (_event, launchType, gameDir) => {
  const executableName = gameExecutables[launchType];
  if (!executableName) {
    return { ok: false, error: "Unknown launcher" };
  }

  if (!gameDir || !fs.existsSync(gameDir)) {
    return { ok: false, error: "Game directory not found" };
  }

  const executablePath = path.join(gameDir, executableName);
  if (!fs.existsSync(executablePath)) {
    return { ok: false, error: `${executableName} not found in game directory` };
  }

  try {
    const child = spawn(executablePath, [], {
      cwd: gameDir,
      detached: true,
      stdio: "ignore",
      windowsHide: false
    });
    child.unref();
    return { ok: true, executable: executableName };
  } catch (error) {
    return { ok: false, error: error.message };
  }
});

app.whenReady().then(async () => {
  const startupStart = process.hrtime.bigint();
  Menu.setApplicationMenu(null);
  logStartupStep("app.whenReady", startupStart, "(menu cleared)");

  const backendStart = process.hrtime.bigint();
  await startPythonBackend();
  logStartupStep("backend startup phase", backendStart, `(port=${backendPort})`);

  const windowStart = process.hrtime.bigint();
  createWindow();
  logStartupStep("createWindow", windowStart, isDev ? "(dev renderer)" : "(dist renderer)");
  logStartupStep("desktop startup", startupStart);

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("before-quit", () => {
  app.isQuitting = true;
  shutdownBackend("app is quitting");
  clearModelPreviewCache();
});

ipcMain.handle("blender:openFbx", async (_event, blenderPath, fbxPath) => {
  const normalizedBlenderPath = path.resolve(String(blenderPath || ""));
  const normalizedFbxPath = path.resolve(String(fbxPath || ""));
  const blenderName = path.basename(normalizedBlenderPath).toLowerCase();

  if (
    !fs.existsSync(normalizedBlenderPath)
    || !fs.statSync(normalizedBlenderPath).isFile()
    || !blenderName.startsWith("blender")
    || path.extname(normalizedBlenderPath).toLowerCase() !== ".exe"
  ) {
    return { ok: false, error: "Blender executable not found" };
  }
  if (
    !fs.existsSync(normalizedFbxPath)
    || !fs.statSync(normalizedFbxPath).isFile()
    || path.extname(normalizedFbxPath).toLowerCase() !== ".fbx"
  ) {
    return { ok: false, error: "FBX file not found" };
  }

  const pythonFbxPath = normalizedFbxPath.replace(/\\/g, "/");
  const blenderSetupScript = [
    "import bpy",
    "bpy.ops.object.select_all(action='SELECT')",
    "bpy.ops.object.delete(use_global=False)",
    "view_preferences=bpy.context.preferences.view",
    "view_preferences.language='zh_HANS'",
    "view_preferences.use_translate_interface=True",
    "view_preferences.use_translate_tooltips=True",
    `bpy.ops.import_scene.fbx(filepath=${JSON.stringify(pythonFbxPath)})`,
    "mesh_objects=[obj for obj in bpy.context.scene.objects if obj.type=='MESH']",
    "if mesh_objects:",
    "    active_object=mesh_objects[0]",
    "    bpy.ops.object.select_all(action='DESELECT')",
    "    active_object.select_set(True)",
    "    bpy.context.view_layer.objects.active=active_object",
    "    if active_object.data.uv_layers:",
    "        active_object.data.uv_layers.active_index=0",
    "    active_material=active_object.active_material",
    "    diffuse_node=None",
    "    if active_material and active_material.node_tree:",
    "        for link in active_material.node_tree.links:",
    "            if link.to_socket.name=='Base Color' and link.from_node.type=='TEX_IMAGE':",
    "                diffuse_node=link.from_node",
    "                break",
    "        if diffuse_node and diffuse_node.image:",
    "            for node in active_material.node_tree.nodes:",
    "                node.select=False",
    "            diffuse_node.select=True",
    "            active_material.node_tree.nodes.active=diffuse_node",
    "            for screen in bpy.data.screens:",
    "                for area in screen.areas:",
    "                    if area.type=='IMAGE_EDITOR':",
    "                        area.spaces.active.image=diffuse_node.image"
  ].join("\n");
  const pythonExpression = `exec(${JSON.stringify(blenderSetupScript)})`;

  try {
    const child = spawn(
      normalizedBlenderPath,
      ["--python-expr", pythonExpression],
      {
        cwd: path.dirname(normalizedFbxPath),
        detached: true,
        stdio: "ignore",
        windowsHide: false
      }
    );
    child.unref();
    return {
      ok: true,
      executable: normalizedBlenderPath,
      fbx: normalizedFbxPath
    };
  } catch (error) {
    return { ok: false, error: error.message };
  }
});

ipcMain.handle("shell:openDirectory", async (_event, directoryPath) => {
  if (!directoryPath || !fs.existsSync(directoryPath) || !fs.statSync(directoryPath).isDirectory()) {
    return { ok: false, error: "Directory not found" };
  }
  const error = await shell.openPath(directoryPath);
  return error ? { ok: false, error } : { ok: true };
});

app.on("window-all-closed", () => {
  shutdownBackend("all windows closed");
  if (process.platform !== "darwin") {
    app.quit();
  }
});
