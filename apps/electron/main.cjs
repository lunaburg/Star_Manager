const { app, BrowserWindow, Menu, dialog, ipcMain, shell, screen, protocol, net: electronNet } = require("electron");
const { execFile, spawn } = require("node:child_process");
const { Worker } = require("node:worker_threads");
const crypto = require("node:crypto");
const fs = require("node:fs");
const net = require("node:net");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { terminateProcessTree } = require("./backend-process.cjs");
const {
  STANDARD_RESOLUTIONS,
  formatResolution,
  normalizeSetup,
  readGameSetup,
  writeGameSetup
} = require("./game-setup.cjs");

const rendererUrl = process.env.ELECTRON_RENDERER_URL || "";
const isDev = Boolean(rendererUrl);
const hasSingleInstanceLock = app.requestSingleInstanceLock();
const expectedBackendRevision = "sims4-workbench-tpose-mesh-v2-unity3d-preprocess-v1-game-item-probe-v2-hair-slots-card-load-v1-unity3d-export-v1-trash-v2-card-single-delete-v1-scene-remote-completion-v1";
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
let backendShutdownPromise = null;
let appShutdownStarted = false;
const windowReadiness = new WeakMap();
const gameExecutables = {
  game: "HoneySelect2.exe",
  studio: "StudioNEOV2.exe",
  vr: "HoneySelect2VR.exe"
};
const DEFAULT_SB3UTILITY_EXECUTABLE_PATH = String(process.env.STAR_MANAGER_SB3UTILITY_EXE || "");

if (!hasSingleInstanceLock) {
  app.quit();
} else {
  app.on("second-instance", () => {
    const window = BrowserWindow.getAllWindows()[0];
    if (!window || window.isDestroyed()) return;
    if (window.isMinimized()) window.restore();
    window.show();
    window.focus();
  });
}

protocol.registerSchemesAsPrivileged([{
  scheme: "wallpaper",
  privileges: { standard: true, secure: true, supportFetchAPI: true, corsEnabled: true, stream: true }
}]);
const SETTINGS_DIRECTORY_NAME = "star-manager";

function getGameSetupDisplays(setup) {
  const displays = [];
  try {
    screen.getAllDisplays().forEach((display, index) => {
      const width = Number(display.size?.width || 0);
      const height = Number(display.size?.height || 0);
      displays.push({
        index,
        label: `Display ${index}`,
        width,
        height
      });
    });
  } catch (error) {
    console.warn(`[game setup] display enumeration failed: ${error.message}`);
  }

  const minimumDisplayCount = Math.max(1, Number(setup.display || 0) + 1);
  while (displays.length < minimumDisplayCount) {
    const index = displays.length;
    displays.push({ index, label: `Display ${index}`, width: 0, height: 0 });
  }
  return displays;
}

function getGameSetupResolutions(setup, displays) {
  const resolutionMap = new Map();
  const addResolution = (width, height) => {
    const normalizedWidth = Number(width);
    const normalizedHeight = Number(height);
    if (!Number.isInteger(normalizedWidth) || !Number.isInteger(normalizedHeight)) return;
    if (normalizedWidth <= 0 || normalizedHeight <= 0) return;
    const label = formatResolution(normalizedWidth, normalizedHeight);
    resolutionMap.set(label, { label, width: normalizedWidth, height: normalizedHeight });
  };

  STANDARD_RESOLUTIONS.forEach(([width, height]) => addResolution(width, height));
  addResolution(setup.width, setup.height);
  displays.forEach((display) => addResolution(display.width, display.height));
  return [...resolutionMap.values()];
}

function getGameSetupPayload(gameDir) {
  const result = readGameSetup(gameDir);
  const displays = getGameSetupDisplays(result.setup);
  return {
    ...result,
    displays,
    resolutions: getGameSetupResolutions(result.setup, displays)
  };
}

async function syncUnityRegistry(gameDir, setup) {
  if (process.platform !== "win32") {
    return { ok: true, skipped: true, message: "当前平台不写入 Windows 注册表。" };
  }

  const registryKeys = ["HKCU\\Software\\illusion\\HoneySelect2\\HoneySelect2"];
  if (fs.existsSync(path.join(gameDir, "StudioNEOV2.exe"))) {
    registryKeys.push("HKCU\\Software\\illusion\\Koikatu\\CharaStudio");
  }
  const values = [
    ["Screenmanager Is Fullscreen mode_h3981298716", setup.fullscreen ? 1 : 0],
    ["Screenmanager Resolution Height_h2627697771", setup.height],
    ["Screenmanager Resolution Width_h182942802", setup.width],
    ["UnityGraphicsQuality_h1669003810", 2],
    ["UnitySelectMonitor_h17969598", setup.display]
  ];

  try {
    for (const registryKey of registryKeys) {
      for (const [name, value] of values) {
        await execFileText("reg.exe", [
          "add",
          registryKey,
          "/v",
          name,
          "/t",
          "REG_DWORD",
          "/d",
          String(value),
          "/f"
        ]);
      }
    }
    return { ok: true, keys: registryKeys };
  } catch (error) {
    return { ok: false, keys: registryKeys, error: error.message };
  }
}

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
  return path.join(app.getPath("appData"), SETTINGS_DIRECTORY_NAME, "settings.json");
}

function legacySettingsPath() {
  const candidate = path.join(app.getPath("userData"), "settings.json");
  return candidate.toLowerCase() === settingsPath().toLowerCase() ? "" : candidate;
}

function settingsReadPath() {
  const canonicalPath = settingsPath();
  if (fs.existsSync(canonicalPath)) {
    return canonicalPath;
  }
  const legacyPath = legacySettingsPath();
  return legacyPath && fs.existsSync(legacyPath) ? legacyPath : canonicalPath;
}

function normalizeSettings(settings = {}) {
  const allowedStartupViews = new Set(["start", "overview", "characters", "mods", "workbench", "plugins", "logs", "settings"]);
  const allowedFavoriteCardThemes = new Set(["gold", "neon", "sakura", "obsidian"]);
  const allowedPortablePackageTypes = ["face", "hair", "body", "clothes", "accessory"];
  const allowedCharacterCardLoadOptions = ["face", "body", "hair", "clothes", "accessory", "parameter"];
  const startupView = String(settings.startupView || "start");
  const favoriteCardTheme = String(settings.favoriteCardTheme || settings.favoriteCardFrameTheme || "gold");
  const sb3utilityExecutablePath = String(settings.sb3utilityExecutablePath || "");
  const legacySb3utilityShortcutPath = String(settings.sb3utilityShortcutPath || "");
  const portablePackageTypes = Array.isArray(settings.portablePackageTypes)
    ? allowedPortablePackageTypes.filter((type) => settings.portablePackageTypes.includes(type))
    : [...allowedPortablePackageTypes];
  const characterCardLoadOptions = Array.isArray(settings.characterCardLoadOptions)
    ? allowedCharacterCardLoadOptions.filter((option) => settings.characterCardLoadOptions.includes(option))
    : [...allowedCharacterCardLoadOptions];
  const workbenchProjects = Array.isArray(settings.workbenchProjects)
    ? settings.workbenchProjects
      .map((project) => ({
        id: String(project?.id || "").trim(),
        guid: String(project?.guid || "").trim(),
        name: String(project?.name || "").trim(),
        path: String(project?.path || "").trim(),
        manifestPath: String(project?.manifestPath || "").trim(),
        projectFilePath: String(project?.projectFilePath || "").trim(),
        createdAt: String(project?.createdAt || "").trim()
      }))
      .filter((project) => project.id && project.name && project.path)
    : [];
  return {
    gameDir: String(settings.gameDir || ""),
    inputDir: String(settings.inputDir || ""),
    outputDir: String(settings.outputDir || ""),
    workbenchAuthorId: String(settings.workbenchAuthorId || "").trim(),
    workbenchWorkspacePath: String(settings.workbenchWorkspacePath || "").trim(),
    workbenchActiveProjectId: String(settings.workbenchActiveProjectId || "").trim(),
    workbenchProjects,
    coordinateExportDir: String(settings.coordinateExportDir || ""),
    portablePackageDir: String(settings.portablePackageDir || ""),
    blenderExecutablePath: String(settings.blenderExecutablePath || ""),
    sb3utilityExecutablePath: sb3utilityExecutablePath
      || (legacySb3utilityShortcutPath.toLowerCase().endsWith(".exe") ? legacySb3utilityShortcutPath : DEFAULT_SB3UTILITY_EXECUTABLE_PATH),
    portablePackageCompress: settings.portablePackageCompress !== false,
    portablePackageTypes,
    characterCardLoadOptions,
    startupView: allowedStartupViews.has(startupView) ? startupView : "start",
    favoriteCardTheme: allowedFavoriteCardThemes.has(favoriteCardTheme) ? favoriteCardTheme : "gold",
    checkDatabaseChangesOnStartup: settings.checkDatabaseChangesOnStartup !== false,
    wallpaperPath: String(settings.wallpaperPath || "").trim(),
    wallpaperType: ["image", "video"].includes(String(settings.wallpaperType || ""))
      ? String(settings.wallpaperType)
      : ""
  };
}

function loadSettingsFile() {
  const filePath = settingsPath();
  const readPath = settingsReadPath();
  const backupPath = `${filePath}.bak`;
  const candidatePaths = [readPath, backupPath]
    .filter((candidate, index, candidates) => candidate && candidates.indexOf(candidate) === index)
    .filter((candidate) => fs.existsSync(candidate));
  let lastError = null;

  for (const candidatePath of candidatePaths) {
    try {
      const settings = normalizeSettings(JSON.parse(fs.readFileSync(candidatePath, "utf-8")));
      return {
        ok: true,
        settings,
        path: filePath,
        recoveredFrom: candidatePath === filePath ? "" : candidatePath
      };
    } catch (error) {
      lastError = error;
    }
  }

  if (lastError) {
    return { ok: false, settings: normalizeSettings(), path: filePath, error: lastError.message };
  }

  const emptySettings = normalizeSettings();
  try {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    writeSettingsFileAtomically(filePath, JSON.stringify(emptySettings, null, 2));
    return { ok: true, settings: emptySettings, path: filePath, recoveredFrom: "" };
  } catch (error) {
    return { ok: false, settings: emptySettings, path: filePath, error: error.message };
  }
}

function writeSettingsFileAtomically(filePath, content) {
  const temporaryPath = `${filePath}.star-manager-${process.pid}-${Date.now()}.tmp`;
  const backupPath = `${filePath}.bak`;
  try {
    fs.writeFileSync(temporaryPath, content, "utf-8");
    if (fs.existsSync(filePath)) {
      fs.copyFileSync(filePath, backupPath);
    }
    try {
      fs.renameSync(temporaryPath, filePath);
    } catch (error) {
      if (!["EEXIST", "EPERM"].includes(error.code)) {
        throw error;
      }
      fs.rmSync(filePath, { force: true });
      fs.renameSync(temporaryPath, filePath);
    }
  } finally {
    if (fs.existsSync(temporaryPath)) {
      fs.rmSync(temporaryPath, { force: true });
    }
  }
}

function saveSettingsFile(settings = {}) {
  const filePath = settingsPath();
  const readPath = settingsReadPath();
  const incoming = settings && typeof settings === "object" ? settings : {};
  let existing = {};
  try {
    if (fs.existsSync(readPath)) {
      existing = JSON.parse(fs.readFileSync(readPath, "utf-8"));
    }
  } catch (error) {
    console.warn(`[settings] failed to read existing settings before save: ${error.message}`);
  }

  const merged = { ...existing, ...incoming };
  const incomingGameDir = String(incoming.gameDir || "").trim();
  const existingGameDir = String(existing.gameDir || "").trim();
  if (!incoming.clearGameDir && !incomingGameDir && existingGameDir) {
    merged.gameDir = existingGameDir;
    if (!String(incoming.inputDir || "").trim() && String(existing.inputDir || "").trim()) {
      merged.inputDir = existing.inputDir;
    }
  }
  const clearSb3UtilityExecutablePath = incoming.clearSb3UtilityExecutablePath === true;
  if (!clearSb3UtilityExecutablePath && !String(incoming.sb3utilityExecutablePath || "").trim()) {
    const existingSb3UtilityExecutablePath = String(existing.sb3utilityExecutablePath || "").trim();
    if (existingSb3UtilityExecutablePath) {
      merged.sb3utilityExecutablePath = existingSb3UtilityExecutablePath;
    }
  }

  const normalized = normalizeSettings(merged);
  try {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    writeSettingsFileAtomically(filePath, JSON.stringify(normalized, null, 2));
    return { ok: true, settings: normalized, path: filePath };
  } catch (error) {
    return { ok: false, settings: normalized, path: filePath, error: error.message };
  }
}

function getStartupWallpaperSettings() {
  const result = loadSettingsFile();
  const settings = result?.settings || normalizeSettings();
  return {
    wallpaperPath: String(settings.wallpaperPath || "").trim(),
    wallpaperType: ["image", "video"].includes(String(settings.wallpaperType || ""))
      ? String(settings.wallpaperType)
      : ""
  };
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
  const nativeSurfaceColor = "#ffffff";
  const transparentTitleBarColor = "rgba(0, 0, 0, 0)";
  const window = new BrowserWindow({
    width: 1420,
    height: 900,
    minWidth: 1180,
    minHeight: 780,
    title: "Star_Manager",
    icon: path.join(__dirname, "../build-resources/app-icon.png"),
    // Keep the native surface opaque while the renderer and external wallpaper
    // are warming up. Transparent BrowserWindows can composite as black on
    // Windows before the first renderer frame is available.
    backgroundColor: nativeSurfaceColor,
    show: false,
    titleBarStyle: "hidden",
    titleBarOverlay: {
      // Keep the native caption buttons transparent so the renderer's
      // wallpaper remains visible underneath them.
      color: transparentTitleBarColor,
      symbolColor: "#2d2930",
      height: 38
    },
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });
  const readiness = {
    nativeReady: false,
    rendererReady: false,
    revealed: false,
    fallbackTimer: null,
    revealWindow: null,
    logPageLoadStep: null
  };
  windowReadiness.set(window, readiness);
  const revealWindow = (trigger = "unknown") => {
    if (readiness.revealed || window.isDestroyed()) return;
    readiness.revealed = true;
    if (readiness.fallbackTimer) clearTimeout(readiness.fallbackTimer);
    window.show();
    logPageLoadStep("first-screen-shown", "renderer", `(trigger=${trigger})`);
    window.focus();
  };
  readiness.revealWindow = revealWindow;
  logStartupStep("BrowserWindow constructed", createWindowStart);

  const pageLoadStart = process.hrtime.bigint();
  const logPageLoadStep = (step, origin = "renderer", detail = "") => {
    const message = `[startup] ${origin} ${step} at ${formatDurationMs(hrtimeMs(pageLoadStart))}${detail ? ` ${detail}` : ""}`;
    console.log(message);
    if (["ready-to-show", "renderer-ready", "first-screen-shown"].includes(step) && !window.isDestroyed()) {
      window.webContents.send("startup:log", { message });
    }
  };
  readiness.logPageLoadStep = logPageLoadStep;
  window.webContents.once("did-start-loading", () => {
    logPageLoadStep("did-start-loading");
  });
  window.once("ready-to-show", () => {
    readiness.nativeReady = true;
    logPageLoadStep("ready-to-show", "electron");
    revealWindow("ready-to-show");
  });
  window.webContents.once("dom-ready", () => {
    logPageLoadStep("dom-ready");
  });
  window.webContents.once("did-finish-load", () => {
    logPageLoadStep("did-finish-load");
    revealWindow("did-finish-load");
  });
  window.webContents.once("did-fail-load", (_event, errorCode, errorDescription) => {
    console.error(
      `[startup] renderer did-fail-load at ${formatDurationMs(hrtimeMs(pageLoadStart))} code=${errorCode} ${errorDescription}`
    );
  });
  window.webContents.on("render-process-gone", (_event, details) => {
    console.error(`[renderer] process gone reason=${details.reason} exitCode=${details.exitCode}`);
    if (!app.isQuitting) {
      app.quit();
    }
  });
  window.webContents.on("unresponsive", () => {
    console.warn("[renderer] window became unresponsive");
  });
  readiness.fallbackTimer = setTimeout(() => {
    if (readiness.revealed || window.isDestroyed()) return;
    console.warn("[startup] renderer readiness timed out; revealing window");
    revealWindow("timeout");
  }, 5000);
  window.once("closed", () => {
    if (readiness.fallbackTimer) clearTimeout(readiness.fallbackTimer);
    windowReadiness.delete(window);
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

async function shutdownBackend(reason = "app shutdown") {
  if (backendShutdownPromise) {
    return backendShutdownPromise;
  }

  const child = backendProcess;
  if (!child || child.exitCode !== null || child.signalCode !== null) {
    backendProcess = null;
    return;
  }

  backendStopRequested = true;
  console.log(`[backend] stopping because ${reason}`);
  backendShutdownPromise = terminateProcessTree(child, {
    platform: process.platform,
    execFileImpl: execFile
  })
    .catch((error) => {
      console.warn(`[backend] failed to stop process tree: ${error.message}`);
    })
    .finally(() => {
      if (backendProcess === child) {
        backendProcess = null;
      }
    });
  return backendShutdownPromise;
}

function decodeExternalProcessOutput(value, outputEncoding = "utf8") {
  if (typeof value === "string") return value;
  const buffer = Buffer.isBuffer(value) ? value : Buffer.from(value || "");
  if (outputEncoding !== "auto") return buffer.toString(outputEncoding);
  try {
    return new TextDecoder("utf-8", { fatal: true }).decode(buffer);
  } catch {
    return new TextDecoder("gb18030").decode(buffer);
  }
}

function execFileText(command, args, options = {}) {
  const { outputEncoding = "utf8", ...execOptions } = options;
  const encoding = outputEncoding === "auto" ? "buffer" : outputEncoding;
  return new Promise((resolve, reject) => {
    execFile(command, args, { windowsHide: true, encoding, ...execOptions }, (error, stdout, stderr) => {
      const stdoutText = decodeExternalProcessOutput(stdout, outputEncoding);
      const stderrText = decodeExternalProcessOutput(stderr, outputEncoding);
      if (error) {
        const processMessage = [stderrText, stdoutText]
          .map((value) => String(value || "").trim())
          .filter(Boolean)
          .join("\n");
        error.message = processMessage || error.message;
        reject(error);
        return;
      }
      resolve(stdoutText.trim());
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

function escapeXml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&apos;");
}

function safeProjectDirectoryName(projectName) {
  const cleaned = String(projectName || "")
    .trim()
    .replace(/[<>:"/\\|?*\u0000-\u001f]/g, " ")
    .replace(/[. ]+$/g, "")
    .trim();
  return cleaned || "untitled-mod";
}

function safeGuidSegment(value, fallback) {
  const cleaned = String(value || "")
    .trim()
    .toLocaleLowerCase()
    .replace(/[^\p{L}\p{N}_-]+/gu, "-")
    .replace(/^-+|-+$/g, "");
  return cleaned || fallback;
}

const WORKBENCH_PROJECT_FILE_NAME = "star-manager.project.json";
const WORKBENCH_PROJECT_FORMAT = "star-manager.hs2-mod-project";
const WORKBENCH_PROJECT_SCHEMA_VERSION = 1;
const WORKBENCH_LIST_DIRECTORY = path.join("abdata", "list");
const WORKBENCH_RESOURCE_DIRECTORY = path.join("abdata", "chara");
const WORKBENCH_TEMPLATE_PATH = path.join(
  __dirname,
  "..",
  "build-resources",
  "workbench-templates",
  "workbench-template.unity3d"
);
const WORKBENCH_TEMPLATE_DEFAULT_MAIN_DATA = "sjjpl_Bikini_005";

const WORKBENCH_CSV_HEADER = [
  "ID",
  "Kind",
  "Possess",
  "Name",
  "EN_US",
  "MainManifest",
  "MainAB",
  "MainData",
  "StateType",
  "MainTex",
  "ColorMaskTex",
  "ThumbAB",
  "ThumbTex"
];
const WORKBENCH_ACCESSORY_KIND = "361";
const WORKBENCH_ACCESSORY_CSV_HEADER = [
  "ID",
  "Kind",
  "Possess",
  "Name",
  "EN_US",
  "MainManifest",
  "MainAB",
  "MainData",
  "Parent",
  "ThumbAB",
  "ThumbTex"
];
const WORKBENCH_ACCESSORY_METADATA_REFERENCE =
  "Assets/in-house/assetbundle/list/characustom/00/ao_hand_00.bytes";
const WORKBENCH_TEXTURE_FIELDS = [
  "MainTex",
  "ColorMaskTex",
  "MainTex02",
  "ColorMask02Tex",
  "MainTex03",
  "ColorMask03Tex"
];
const WORKBENCH_ASSET_TEXTURE_EXTENSIONS = new Set([
  ".png",
  ".jpg",
  ".jpeg",
  ".webp",
  ".bmp",
  ".tga",
  ".dds",
  ".tif",
  ".tiff",
  ".ktx",
  ".ktx2"
]);
const WORKBENCH_ASSET_MODEL_EXTENSIONS = new Set([".fbx"]);
const WORKBENCH_BROWSER_TEXTURE_MIME_TYPES = new Map([
  [".png", "image/png"],
  [".jpg", "image/jpeg"],
  [".jpeg", "image/jpeg"],
  [".webp", "image/webp"],
  [".bmp", "image/bmp"]
]);
const WORKBENCH_THUMBNAIL_DIRECTORY = path.join("abdata", "thumbnail", "star_manager");
const WORKBENCH_THUMBNAIL_FIELDS = ["ThumbAB", "ThumbTex"];
const WORKBENCH_ZERO_AS_EMPTY_FIELDS = new Set([
  "MainManifest",
  "MainAB",
  "MainData",
  ...WORKBENCH_TEXTURE_FIELDS,
  "ThumbAB",
  "ThumbTex"
]);

function workbenchCsvDisplayValue(field, value) {
  const text = String(value ?? "").trim();
  return WORKBENCH_ZERO_AS_EMPTY_FIELDS.has(field) && text === "0" ? "" : text;
}

function workbenchCsvStoredValue(field, value) {
  const text = String(value ?? "").trim();
  return WORKBENCH_ZERO_AS_EMPTY_FIELDS.has(field) && !text ? "0" : text;
}

function normalizeWorkbenchCategory(value) {
  return String(value || "")
    .trim()
    .replace(/[\r\n]+/g, " ")
    .replace(/\s+/g, " ");
}

function workbenchCsvTemplateForCategory(category) {
  const normalizedCategory = normalizeWorkbenchCategory(category);
  if (normalizedCategory === WORKBENCH_ACCESSORY_KIND) {
    return {
      header: WORKBENCH_ACCESSORY_CSV_HEADER,
      metadataRows: [
        normalizedCategory,
        "0",
        WORKBENCH_ACCESSORY_METADATA_REFERENCE
      ],
      defaults: {
        Parent: "N_Hand_R"
      }
    };
  }
  return {
    header: WORKBENCH_CSV_HEADER,
    metadataRows: [normalizedCategory, "0", "ABCDEFG"],
    defaults: {}
  };
}

function csvCell(value) {
  const text = String(value || "");
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

function csvFieldsForRecord(header, record) {
  return header
    .map((key) => ({ key, value: record?.[key] || "" }))
    .filter((field) => field.value !== "");
}

function readWorkbenchCsvCategory(csvPath) {
  try {
    const content = fs.readFileSync(csvPath, "utf-8");
    const firstLine = String(content).split(/\r?\n/, 1)[0] || "";
    const firstCell = firstLine
      .split(",", 1)[0]
      .replace(/^\uFEFF/, "")
      .trim()
      .replace(/^"(.*)"$/, "$1")
      .replaceAll('""', '"');
    return firstCell && firstCell.toLocaleLowerCase() !== "id" ? normalizeWorkbenchCategory(firstCell) : "";
  } catch {
    return "";
  }
}

function collectWorkbenchCsvFiles(directoryPath, files = []) {
  if (!fs.existsSync(directoryPath) || !fs.statSync(directoryPath).isDirectory()) return files;
  for (const entry of fs.readdirSync(directoryPath, { withFileTypes: true })) {
    const entryPath = path.join(directoryPath, entry.name);
    if (entry.isDirectory()) {
      collectWorkbenchCsvFiles(entryPath, files);
    } else if (entry.isFile() && path.extname(entry.name).toLocaleLowerCase() === ".csv") {
      files.push(entryPath);
    }
  }
  return files;
}

function parseWorkbenchCsvRows(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;

  for (let index = 0; index < text.length; index += 1) {
    const character = text[index];
    if (quoted) {
      if (character === '"' && text[index + 1] === '"') {
        cell += '"';
        index += 1;
      } else if (character === '"') {
        quoted = false;
      } else {
        cell += character;
      }
      continue;
    }

    if (character === '"' && cell.length === 0) {
      quoted = true;
    } else if (character === ",") {
      row.push(cell);
      cell = "";
    } else if (character === "\n") {
      row.push(cell.replace(/\r$/, ""));
      if (row.some((value) => value.trim())) rows.push(row);
      row = [];
      cell = "";
    } else {
      cell += character;
    }
  }

  if (cell.length || row.length) {
    row.push(cell.replace(/\r$/, ""));
    if (row.some((value) => value.trim())) rows.push(row);
  }
  return rows;
}

function readWorkbenchCsvData(projectPath, csvRelativePath, itemName) {
  const relativePath = String(csvRelativePath || "").trim();
  const csvPath = path.resolve(projectPath, relativePath);
  const baseResult = {
    path: relativePath,
    header: [],
    fields: [],
    record: null,
    records: [],
    rowCount: 0,
    error: ""
  };
  if (
    !relativePath
    || path.isAbsolute(relativePath)
    || !isPathInside(projectPath, csvPath)
    || !fs.existsSync(csvPath)
    || !fs.statSync(csvPath).isFile()
  ) {
    return { ...baseResult, error: "CSV 文件不存在" };
  }

  try {
    const rows = parseWorkbenchCsvRows(fs.readFileSync(csvPath, "utf-8").replace(/^\uFEFF/, ""));
    const headerIndex = rows.findIndex((row) => {
      const columns = new Set(row.map((value) => value.trim()));
      return columns.has("ID") && columns.has("Name");
    });
    if (headerIndex < 0) return { ...baseResult, error: "CSV 表头未找到" };

    const header = rows[headerIndex].map((value) => value.trim());
    const records = rows
      .slice(headerIndex + 1)
      .filter((row) => row.some((value) => value.trim()))
      .map((row) => header.reduce((record, key, index) => {
        record[key] = workbenchCsvDisplayValue(key, row[index]);
        return record;
      }, {}));
    const normalizedName = String(itemName || "").trim().toLocaleLowerCase();
    const matchingRecord = records.find((record) => (
      normalizedName && String(record.Name || "").trim().toLocaleLowerCase() === normalizedName
    ));
    const record = matchingRecord || (records.length === 1 ? records[0] : null);
    const fields = csvFieldsForRecord(header, record);
    return {
      path: relativePath,
      header,
      fields,
      record,
      records,
      rowCount: records.length,
      error: ""
    };
  } catch (error) {
    return { ...baseResult, error: `CSV 读取失败：${error.message}` };
  }
}

function appendWorkbenchCsvItem(csvPath, itemName, category) {
  const text = fs.readFileSync(csvPath, "utf-8").replace(/^\uFEFF/, "");
  const rows = parseWorkbenchCsvRows(text);
  const headerIndex = rows.findIndex((row) => {
    const columns = new Set(row.map((value) => value.trim()));
    return columns.has("ID") && columns.has("Name");
  });
  if (headerIndex < 0) throw new Error("CSV 表头未找到");

  const header = rows[headerIndex].map((value) => value.trim());
  const template = workbenchCsvTemplateForCategory(category);
  const idIndex = header.indexOf("ID");
  const numericIds = rows
    .slice(headerIndex + 1)
    .map((row) => Number.parseInt(String(row[idIndex] || "").trim(), 10))
    .filter((value) => Number.isInteger(value) && value >= 0);
  const nextId = String(numericIds.length ? Math.max(...numericIds) + 1 : 0);
  const row = header.map((key) => {
    if (key === "ID") return nextId;
    if (key === "Kind") return "0";
    if (key === "Possess") return "1";
    if (key === "Name") return itemName;
    if (key === "EN_US") return "0";
    if (key === "MainManifest") return "abdata";
    if (key === "MainData") return `${itemName}_obj`;
    if (Object.prototype.hasOwnProperty.call(template.defaults, key)) {
      return template.defaults[key];
    }
    if (key === "StateType") return "0";
    if (key === "MainTex") return `${itemName}_diffuse1`;
    if (key === "ColorMaskTex") return "mc_1";
    return "0";
  });
  rows.push(row);
  const output = rows.map((currentRow) => currentRow.map(csvCell).join(",")).join("\n") + "\n";
  fs.writeFileSync(csvPath, output, "utf-8");
  return { itemId: nextId };
}

function workbenchRelativePath(rootPath, filePath) {
  return path.relative(rootPath, filePath).replaceAll(path.sep, "/");
}

function workbenchSafeResourceSegment(value, fallback) {
  const cleaned = String(value || "")
    .trim()
    .replace(/[<>:"/\\|?*\u0000-\u001f]/g, "_")
    .replace(/[. ]+$/g, "")
    .trim();
  return cleaned || fallback;
}

function validateWorkbenchProject(payload = {}) {
  const rawProjectPath = String(payload.projectPath || "").trim();
  const projectPath = path.resolve(rawProjectPath);
  const expectedProjectId = String(payload.projectId || "").trim();
  if (!rawProjectPath || !fs.existsSync(projectPath) || !fs.statSync(projectPath).isDirectory()) {
    throw new Error("当前工程目录不存在");
  }
  const project = readWorkbenchProject(projectPath);
  if (!project || (expectedProjectId && project.id !== expectedProjectId)) {
    throw new Error("当前目录不是有效的 Star_Manager 工程");
  }
  return { projectPath, project };
}

function resolveWorkbenchFbxSkinScript() {
  const candidates = [
    app.isPackaged
      ? path.join(process.resourcesPath, "workbench", "blender_remove_fbx_skin.py")
      : "",
    path.join(__dirname, "..", "build-resources", "workbench-templates", "blender_remove_fbx_skin.py")
  ].filter(Boolean);
  return candidates.find((candidate) => fs.existsSync(candidate) && fs.statSync(candidate).isFile()) || "";
}

function resolveWorkbenchFbxTransformScript() {
  const candidates = [
    app.isPackaged
      ? path.join(process.resourcesPath, "workbench", "blender_transform_fbx.py")
      : "",
    path.join(__dirname, "..", "build-resources", "workbench-templates", "blender_transform_fbx.py")
  ].filter(Boolean);
  return candidates.find((candidate) => fs.existsSync(candidate) && fs.statSync(candidate).isFile()) || "";
}

function resolveWorkbenchFbxSkeletonScript() {
  const candidates = [
    app.isPackaged
      ? path.join(process.resourcesPath, "workbench", "blender_bind_hs2_skeleton.py")
      : "",
    path.join(__dirname, "..", "build-resources", "workbench-templates", "blender_bind_hs2_skeleton.py")
  ].filter(Boolean);
  return candidates.find((candidate) => fs.existsSync(candidate) && fs.statSync(candidate).isFile()) || "";
}

function resolveWorkbenchFbxWeightsScript() {
  const candidates = [
    app.isPackaged
      ? path.join(process.resourcesPath, "workbench", "blender_transfer_fbx_weights.py")
      : "",
    path.join(__dirname, "..", "build-resources", "workbench-templates", "blender_transfer_fbx_weights.py")
  ].filter(Boolean);
  return candidates.find((candidate) => fs.existsSync(candidate) && fs.statSync(candidate).isFile()) || "";
}

function validateWorkbenchFbxFile(projectPath, sourcePath) {
  const normalizedPath = path.resolve(String(sourcePath || ""));
  if (
    !isPathInside(projectPath, normalizedPath)
    || !fs.existsSync(normalizedPath)
    || !fs.statSync(normalizedPath).isFile()
    || path.extname(normalizedPath).toLowerCase() !== ".fbx"
  ) {
    throw new Error("请选择当前项目目录内有效的 .fbx 文件");
  }
  return normalizedPath;
}

function nextWorkbenchFbxSkinOutput(sourcePath) {
  const parsed = path.parse(sourcePath);
  const baseName = `${parsed.name}_mesh-only`;
  let suffix = 0;
  let candidate = path.join(parsed.dir, `${baseName}${parsed.ext}`);
  while (fs.existsSync(candidate)) {
    suffix += 1;
    candidate = path.join(parsed.dir, `${baseName}_${suffix}${parsed.ext}`);
  }
  return candidate;
}

function nextWorkbenchFbxTransformOutput(sourcePath) {
  const parsed = path.parse(sourcePath);
  const baseName = `${parsed.name}_transformed`;
  let suffix = 0;
  let candidate = path.join(parsed.dir, `${baseName}${parsed.ext}`);
  while (fs.existsSync(candidate)) {
    suffix += 1;
    candidate = path.join(parsed.dir, `${baseName}_${suffix}${parsed.ext}`);
  }
  return candidate;
}

function nextWorkbenchFbxSkeletonOutput(sourcePath) {
  const parsed = path.parse(sourcePath);
  const baseName = `${parsed.name}_with-hs2-skeleton`;
  let suffix = 0;
  let candidate = path.join(parsed.dir, `${baseName}${parsed.ext}`);
  while (fs.existsSync(candidate)) {
    suffix += 1;
    candidate = path.join(parsed.dir, `${baseName}_${suffix}${parsed.ext}`);
  }
  return candidate;
}

function nextWorkbenchFbxWeightsOutput(sourcePath) {
  const parsed = path.parse(sourcePath);
  const baseName = `${parsed.name}_weights-transferred`;
  let suffix = 0;
  let candidate = path.join(parsed.dir, `${baseName}${parsed.ext}`);
  while (fs.existsSync(candidate)) {
    suffix += 1;
    candidate = path.join(parsed.dir, `${baseName}_${suffix}${parsed.ext}`);
  }
  return candidate;
}

function nextWorkbenchFbxBackupPath(sourcePath) {
  const parsed = path.parse(sourcePath);
  const baseName = `${parsed.name}_backup`;
  let suffix = 0;
  let candidate = path.join(parsed.dir, `${baseName}${parsed.ext}`);
  while (fs.existsSync(candidate)) {
    suffix += 1;
    candidate = path.join(parsed.dir, `${baseName}_${suffix}${parsed.ext}`);
  }
  return candidate;
}

function runWorkbenchFbxSkinScript(blenderPath, scriptPath, sourcePath, outputPath) {
  return new Promise((resolve, reject) => {
    const child = spawn(
      blenderPath,
      ["--background", "--factory-startup", "--python", scriptPath, "--", "--input", sourcePath, "--output", outputPath],
      { cwd: path.dirname(sourcePath), windowsHide: true, stdio: ["ignore", "pipe", "pipe"] }
    );
    let stdout = "";
    let stderr = "";
    child.stdout?.on("data", (chunk) => { stdout += String(chunk); });
    child.stderr?.on("data", (chunk) => { stderr += String(chunk); });
    child.once("error", reject);
    child.once("close", (code) => {
      const lines = `${stdout}\n${stderr}`
        .split(/\r?\n/)
        .map((line) => line.trim())
        .filter(Boolean);
      let report = null;
      for (let index = lines.length - 1; index >= 0; index -= 1) {
        try {
          const parsed = JSON.parse(lines[index]);
          if (parsed && typeof parsed === "object" && ("ok" in parsed || "output" in parsed)) {
            report = parsed;
            break;
          }
        } catch {
          // Blender emits informational lines around the script's JSON report.
        }
      }
      if (code !== 0 || !report?.ok) {
        const detail = report?.error || stderr.trim() || stdout.trim() || `Blender exited with code ${code}`;
        reject(new Error(detail.slice(-2000)));
        return;
      }
      resolve(report);
    });
  });
}

function runWorkbenchFbxTransformScript(blenderPath, scriptPath, sourcePath, outputPath) {
  return new Promise((resolve, reject) => {
    const child = spawn(
      blenderPath,
      [
        "--background",
        "--factory-startup",
        "--python",
        scriptPath,
        "--",
        "--input",
        sourcePath,
        "--output",
        outputPath
      ],
      { cwd: path.dirname(sourcePath), windowsHide: true, stdio: ["ignore", "pipe", "pipe"] }
    );
    let stdout = "";
    let stderr = "";
    child.stdout?.on("data", (chunk) => { stdout += String(chunk); });
    child.stderr?.on("data", (chunk) => { stderr += String(chunk); });
    child.once("error", reject);
    child.once("close", (code) => {
      const lines = `${stdout}\n${stderr}`
        .split(/\r?\n/)
        .map((line) => line.trim())
        .filter(Boolean);
      let report = null;
      for (let index = lines.length - 1; index >= 0; index -= 1) {
        try {
          const parsed = JSON.parse(lines[index]);
          if (parsed && typeof parsed === "object" && ("ok" in parsed || "output" in parsed)) {
            report = parsed;
            break;
          }
        } catch {
          // Blender emits informational lines around the script's JSON report.
        }
      }
      if (code !== 0 || !report?.ok) {
        const detail = report?.error || stderr.trim() || stdout.trim() || `Blender exited with code ${code}`;
        reject(new Error(detail.slice(-2000)));
        return;
      }
      resolve(report);
    });
  });
}

function runWorkbenchFbxSkeletonScript(blenderPath, scriptPath, sourcePath, skeletonPath, outputPath) {
  return new Promise((resolve, reject) => {
    const child = spawn(
      blenderPath,
      ["--background", "--factory-startup", "--python", scriptPath, "--", "--input", sourcePath, "--skeleton", skeletonPath, "--output", outputPath],
      { cwd: path.dirname(sourcePath), windowsHide: true, stdio: ["ignore", "pipe", "pipe"] }
    );
    let stdout = "";
    let stderr = "";
    child.stdout?.on("data", (chunk) => { stdout += String(chunk); });
    child.stderr?.on("data", (chunk) => { stderr += String(chunk); });
    child.once("error", reject);
    child.once("close", (code) => {
      const lines = `${stdout}\n${stderr}`
        .split(/\r?\n/)
        .map((line) => line.trim())
        .filter(Boolean);
      let report = null;
      for (let index = lines.length - 1; index >= 0; index -= 1) {
        try {
          const parsed = JSON.parse(lines[index]);
          if (parsed && typeof parsed === "object" && ("ok" in parsed || "output" in parsed)) {
            report = parsed;
            break;
          }
        } catch {
          // Blender emits informational lines around the script's JSON report.
        }
      }
      if (code !== 0 || !report?.ok) {
        const detail = report?.error || stderr.trim() || stdout.trim() || `Blender exited with code ${code}`;
        reject(new Error(detail.slice(-2000)));
        return;
      }
      resolve(report);
    });
  });
}

function runWorkbenchFbxWeightsScript(blenderPath, scriptPath, sourcePath, targetPath, outputPath) {
  return new Promise((resolve, reject) => {
    const child = spawn(
      blenderPath,
      ["--background", "--factory-startup", "--python", scriptPath, "--", "--source", sourcePath, "--target", targetPath, "--output", outputPath],
      { cwd: path.dirname(targetPath), windowsHide: true, stdio: ["ignore", "pipe", "pipe"] }
    );
    let stdout = "";
    let stderr = "";
    child.stdout?.on("data", (chunk) => { stdout += String(chunk); });
    child.stderr?.on("data", (chunk) => { stderr += String(chunk); });
    child.once("error", reject);
    child.once("close", (code) => {
      const lines = `${stdout}\n${stderr}`
        .split(/\r?\n/)
        .map((line) => line.trim())
        .filter(Boolean);
      let report = null;
      for (let index = lines.length - 1; index >= 0; index -= 1) {
        try {
          const parsed = JSON.parse(lines[index]);
          if (parsed && typeof parsed === "object" && ("ok" in parsed || "output" in parsed)) {
            report = parsed;
            break;
          }
        } catch {
          // Blender emits informational lines around the script's JSON report.
        }
      }
      if (code !== 0 || !report?.ok) {
        const detail = report?.error || stderr.trim() || stdout.trim() || `Blender exited with code ${code}`;
        reject(new Error(detail.slice(-2000)));
        return;
      }
      resolve(report);
    });
  });
}

function validateWorkbenchProjectForDeletion(payload = {}) {
  const rawWorkspacePath = String(payload.workspacePath || "").trim();
  const workspacePath = path.resolve(rawWorkspacePath);
  if (!rawWorkspacePath || !fs.existsSync(workspacePath) || !fs.statSync(workspacePath).isDirectory()) {
    throw new Error("工具台工作空间不存在");
  }

  const validated = validateWorkbenchProject(payload);
  const relativeProjectPath = path.relative(workspacePath, validated.projectPath);
  if (
    !relativeProjectPath
    || path.isAbsolute(relativeProjectPath)
    || relativeProjectPath.startsWith("..")
    || relativeProjectPath.includes(path.sep)
  ) {
    throw new Error("只能删除当前工作空间下的工程");
  }
  return { ...validated, workspacePath };
}

function deleteWorkbenchProject(payload = {}) {
  try {
    const { projectPath, project } = validateWorkbenchProjectForDeletion(payload);
    fs.rmSync(projectPath, {
      recursive: true,
      force: false,
      maxRetries: 5,
      retryDelay: 200
    });
    return { ok: true, projectId: project.id };
  } catch (error) {
    const lockHint = ["EBUSY", "EPERM", "EACCES"].includes(error?.code)
      ? "；请关闭 SB3Utility、文件预览窗口后重试"
      : "";
    return { ok: false, error: "删除工程失败：" + error.message + lockHint };
  }
}

function deleteSims4ResultDirectory(directoryPath) {
  try {
    const rawDirectoryPath = String(directoryPath || "").trim();
    const outputPath = path.resolve(rawDirectoryPath);
    if (!rawDirectoryPath || !fs.existsSync(outputPath)) {
      throw new Error("导出结果目录不存在");
    }
    const directoryStats = fs.lstatSync(outputPath);
    if (!directoryStats.isDirectory() || directoryStats.isSymbolicLink()) {
      throw new Error("导出结果路径不是有效目录");
    }
    if (!/_lod0_fbx(?:_\d+)?$/i.test(path.basename(outputPath))) {
      throw new Error("只能删除 Package → FBX 生成的结果目录");
    }

    const manifestPath = path.join(outputPath, "extraction_manifest.json");
    if (!fs.existsSync(manifestPath) || !fs.statSync(manifestPath).isFile()) {
      throw new Error("找不到有效的导出清单，已拒绝删除");
    }
    let manifest;
    try {
      manifest = JSON.parse(fs.readFileSync(manifestPath, "utf-8"));
    } catch {
      throw new Error("导出清单无效，已拒绝删除");
    }
    const declaredOutputPath = path.resolve(String(manifest?.output_dir || ""));
    if (!declaredOutputPath || declaredOutputPath.toLowerCase() !== outputPath.toLowerCase()) {
      throw new Error("导出清单与当前目录不匹配，已拒绝删除");
    }
    if (path.extname(String(manifest?.source || "")).toLowerCase() !== ".package") {
      throw new Error("当前目录不是有效的 Package → FBX 导出结果");
    }

    fs.rmSync(outputPath, {
      recursive: true,
      force: false,
      maxRetries: 5,
      retryDelay: 200
    });
    return { ok: true, outputDir: outputPath };
  } catch (error) {
    const lockHint = ["EBUSY", "EPERM", "EACCES"].includes(error?.code)
      ? "；请先关闭正在使用导出文件的 Blender 或文件预览窗口后重试"
      : "";
    return { ok: false, error: `删除导出结果失败：${error.message}${lockHint}` };
  }
}

function collectWorkbenchUnity3dFiles(directoryPath, files = []) {
  if (!fs.existsSync(directoryPath) || !fs.statSync(directoryPath).isDirectory()) return files;
  for (const entry of fs.readdirSync(directoryPath, { withFileTypes: true })) {
    const entryPath = path.join(directoryPath, entry.name);
    if (entry.isDirectory()) {
      collectWorkbenchUnity3dFiles(entryPath, files);
    } else if (entry.isFile() && path.extname(entry.name).toLocaleLowerCase() === ".unity3d") {
      files.push(entryPath);
    }
  }
  return files;
}

function scanWorkbenchUnity3d(payload = {}) {
  try {
    const { projectPath } = validateWorkbenchProject(payload);
    const abdataPath = path.join(projectPath, "abdata");
    const files = collectWorkbenchUnity3dFiles(abdataPath)
      .sort((left, right) => left.localeCompare(right, undefined, { sensitivity: "base" }))
      .map((filePath) => {
        const stat = fs.statSync(filePath);
        return {
          path: filePath,
          relativePath: workbenchRelativePath(abdataPath, filePath),
          projectRelativePath: workbenchRelativePath(projectPath, filePath),
          name: path.basename(filePath),
          size: stat.size
        };
      });
    return {
      ok: true,
      files,
      template: {
        available: fs.existsSync(WORKBENCH_TEMPLATE_PATH),
        path: WORKBENCH_TEMPLATE_PATH,
        name: path.basename(WORKBENCH_TEMPLATE_PATH),
        defaultMainData: WORKBENCH_TEMPLATE_DEFAULT_MAIN_DATA
      }
    };
  } catch (error) {
    return { ok: false, error: error.message, files: [] };
  }
}

function collectWorkbenchAssetFiles(directoryPath, projectPath, files = []) {
  let entries;
  try {
    entries = fs.readdirSync(directoryPath, { withFileTypes: true });
  } catch {
    return files;
  }

  for (const entry of entries) {
    const entryPath = path.join(directoryPath, entry.name);
    if (entry.isDirectory()) {
      collectWorkbenchAssetFiles(entryPath, projectPath, files);
      continue;
    }
    if (!entry.isFile()) continue;

    const extension = path.extname(entry.name).toLocaleLowerCase();
    const kind = WORKBENCH_ASSET_TEXTURE_EXTENSIONS.has(extension)
      ? "texture"
      : WORKBENCH_ASSET_MODEL_EXTENSIONS.has(extension)
        ? "model"
        : "";
    if (!kind) continue;

    try {
      const stat = fs.statSync(entryPath);
      files.push({
        kind,
        path: entryPath,
        relativePath: workbenchRelativePath(projectPath, entryPath),
        name: entry.name,
        extension: extension.slice(1).toUpperCase(),
        size: stat.size,
        modifiedAt: stat.mtimeMs
      });
    } catch {
      // A file can disappear while the project is being edited; skip only that file.
    }
  }
  return files;
}

function scanWorkbenchAssetFiles(payload = {}) {
  try {
    const { projectPath, project } = validateWorkbenchProject(payload);
    const files = collectWorkbenchAssetFiles(projectPath, projectPath)
      .sort((left, right) => left.relativePath.localeCompare(right.relativePath, undefined, { sensitivity: "base" }));
    return {
      ok: true,
      projectId: project.id,
      textures: files.filter((file) => file.kind === "texture"),
      models: files.filter((file) => file.kind === "model"),
      total: files.length
    };
  } catch (error) {
    return { ok: false, error: error.message, textures: [], models: [], total: 0 };
  }
}

function loadWorkbenchAssetPreview(payload = {}) {
  try {
    const { projectPath } = validateWorkbenchProject(payload);
    const relativePath = String(payload.relativePath || "").trim().replaceAll("\\", "/");
    const assetPath = path.resolve(projectPath, relativePath);
    const extension = path.extname(assetPath).toLocaleLowerCase();
    if (
      !relativePath
      || path.isAbsolute(relativePath)
      || !isPathInside(projectPath, assetPath)
      || !WORKBENCH_BROWSER_TEXTURE_MIME_TYPES.has(extension)
      || !fs.existsSync(assetPath)
      || !fs.statSync(assetPath).isFile()
    ) {
      throw new Error("当前贴图格式不支持直接预览");
    }
    const stat = fs.statSync(assetPath);
    if (stat.size > 25 * 1024 * 1024) throw new Error("贴图超过 25 MB，无法直接预览");
    const data = fs.readFileSync(assetPath);
    return {
      ok: true,
      name: path.basename(assetPath),
      relativePath: workbenchRelativePath(projectPath, assetPath),
      dataUrl: `data:${WORKBENCH_BROWSER_TEXTURE_MIME_TYPES.get(extension)};base64,${data.toString("base64")}`
    };
  } catch (error) {
    return { ok: false, error: error.message };
  }
}

function normalizeWorkbenchAbdataReference(value, description = "资源") {
  const raw = String(value || "").trim().replaceAll("\\", "/");
  if (!raw || path.posix.isAbsolute(raw) || path.win32.isAbsolute(raw) || /^[a-zA-Z]:/.test(raw)) {
    throw new Error(`${description}引用路径无效`);
  }
  let normalized = path.posix.normalize(raw).replace(/^\.\//, "");
  if (normalized.toLocaleLowerCase().startsWith("abdata/")) normalized = normalized.slice("abdata/".length);
  if (!normalized || normalized === "." || normalized === ".." || normalized.startsWith("../")) {
    throw new Error(`${description}引用路径无效`);
  }
  return normalized;
}

function resolveWorkbenchAbdataReference(projectPath, reference, description = "资源") {
  const normalized = normalizeWorkbenchAbdataReference(reference, description);
  const abdataPath = path.resolve(projectPath, "abdata");
  const resolved = path.resolve(abdataPath, ...normalized.split("/"));
  if (!isPathInside(abdataPath, resolved)) throw new Error(`${description}不能离开工程 abdata 目录`);
  return { normalized, path: resolved };
}

function workbenchThumbnailImageCandidates(projectPath, thumbAB, thumbTex) {
  const reference = resolveWorkbenchAbdataReference(projectPath, thumbAB, "缩略图");
  const extension = path.extname(reference.path).toLocaleLowerCase();
  if (WORKBENCH_BROWSER_TEXTURE_MIME_TYPES.has(extension)) {
    return { imagePaths: [reference.path], bundlePath: "" };
  }
  if (extension === ".unity3d") {
    return { imagePaths: [], bundlePath: reference.path };
  }

  const texture = String(thumbTex || "").trim().replaceAll("\\", "/");
  if (!texture || path.posix.isAbsolute(texture) || path.win32.isAbsolute(texture) || /^[a-zA-Z]:/.test(texture)) {
    return { imagePaths: [], bundlePath: "" };
  }
  const normalizedTexture = path.posix.normalize(texture).replace(/^\.\//, "");
  const base = path.resolve(reference.path);
  const candidates = [path.resolve(base, ...normalizedTexture.split("/"))];
  if (!path.extname(normalizedTexture)) {
    for (const extensionName of WORKBENCH_BROWSER_TEXTURE_MIME_TYPES.keys()) {
      candidates.push(path.resolve(base, ...`${normalizedTexture}${extensionName}`.split("/")));
    }
  }
  return {
    imagePaths: candidates.filter((candidate, index, paths) => (
      isPathInside(path.resolve(projectPath, "abdata"), candidate) && paths.indexOf(candidate) === index
    )),
    bundlePath: ""
  };
}

function workbenchImageDataUrl(filePath) {
  const extension = path.extname(filePath).toLocaleLowerCase();
  const mimeType = WORKBENCH_BROWSER_TEXTURE_MIME_TYPES.get(extension);
  if (!mimeType || !fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) return "";
  const stat = fs.statSync(filePath);
  if (stat.size > 25 * 1024 * 1024) throw new Error("缩略图超过 25 MB，无法直接预览");
  return `data:${mimeType};base64,${fs.readFileSync(filePath).toString("base64")}`;
}

async function loadWorkbenchThumbnail(payload = {}) {
  try {
    const { projectPath, project } = validateWorkbenchProject(payload);
    const thumbAB = String(payload.thumbAB || "").trim();
    const thumbTex = String(payload.thumbTex || "").trim();
    if (!thumbAB) return { ok: true, projectId: project.id, dataUrl: "", missing: true };

    const candidates = workbenchThumbnailImageCandidates(projectPath, thumbAB, thumbTex);
    const imagePath = candidates.imagePaths.find((candidate) => (
      fs.existsSync(candidate) && fs.statSync(candidate).isFile()
    ));
    if (imagePath) {
      return {
        ok: true,
        projectId: project.id,
        dataUrl: workbenchImageDataUrl(imagePath),
        missing: false,
        sourcePath: workbenchRelativePath(projectPath, imagePath)
      };
    }
    if (candidates.bundlePath && fs.existsSync(candidates.bundlePath)) {
      const result = await fetchBackend("/workbench/unity3d/thumbnail", {
        method: "POST",
        body: { path: candidates.bundlePath, texture: thumbTex }
      });
      return result?.ok
        ? {
            ...result,
            projectId: project.id,
            dataUrl: String(result.dataUrl || result.data_url || ""),
            sourcePath: workbenchRelativePath(projectPath, candidates.bundlePath),
            missing: false
          }
        : { ok: true, projectId: project.id, dataUrl: "", missing: true, error: result?.error || "缩略图资源无法读取" };
    }
    return { ok: true, projectId: project.id, dataUrl: "", missing: true };
  } catch (error) {
    return { ok: false, dataUrl: "", missing: true, error: error.message };
  }
}

function decodeWorkbenchScreenshot(imageData) {
  const prefix = "data:image/png;base64,";
  const value = String(imageData || "");
  const encoded = value.startsWith(prefix) ? value.slice(prefix.length) : "";
  if (!encoded || encoded.length > 3_000_000 || encoded.length % 4 === 1 || !/^[A-Za-z0-9+/]*={0,2}$/.test(encoded)) {
    throw new Error("截图数据不是有效的 PNG");
  }
  const buffer = Buffer.from(encoded, "base64");
  if (buffer.length > 2_000_000 || !buffer.subarray(0, 8).equals(Buffer.from("89504e470d0a1a0a", "hex"))) {
    throw new Error("截图数据不是有效的 PNG");
  }
  return buffer;
}

function saveWorkbenchThumbnail(payload = {}) {
  let savedPath = "";
  let temporaryPath = "";
  try {
    const { projectPath, project } = validateWorkbenchProject(payload);
    const csvRelativePath = String(payload.csvPath || "").trim().replaceAll("\\", "/");
    const itemId = String(payload.itemId || "").trim();
    if (!csvRelativePath || !itemId) throw new Error("物品 CSV 定位信息不完整");
    const csvPath = path.resolve(projectPath, csvRelativePath);
    if (
      path.isAbsolute(csvRelativePath)
      || path.extname(csvPath).toLocaleLowerCase() !== ".csv"
      || !isPathInside(projectPath, csvPath)
      || !fs.existsSync(csvPath)
      || !fs.statSync(csvPath).isFile()
    ) {
      throw new Error("物品 CSV 路径无效");
    }

    const image = decodeWorkbenchScreenshot(payload.imageData);
    const thumbnailDirectory = path.join(projectPath, WORKBENCH_THUMBNAIL_DIRECTORY);
    const fileName = `item-${workbenchSafeResourceSegment(itemId, "new")}-${Date.now()}.png`;
    const thumbnailPath = path.join(thumbnailDirectory, fileName);
    temporaryPath = `${thumbnailPath}.${process.pid}.tmp`;
    fs.mkdirSync(thumbnailDirectory, { recursive: true });
    fs.writeFileSync(temporaryPath, image);
    fs.renameSync(temporaryPath, thumbnailPath);
    temporaryPath = "";
    savedPath = thumbnailPath;
    const textureName = path.basename(fileName, path.extname(fileName));

    updateWorkbenchCsvItem(csvPath, itemId, {
      ThumbAB: "thumbnail/star_manager",
      ThumbTex: textureName
    });
    const data = readWorkbenchCsvData(projectPath, csvRelativePath);
    const rowIndex = data.records.findIndex((record) => String(record.ID || "") === itemId);
    if (rowIndex < 0) throw new Error("CSV 更新后无法重新读取物品行");
    return {
      ok: true,
      projectId: project.id,
      item: createWorkbenchCsvItem(
        project,
        projectPath,
        csvRelativePath,
        readWorkbenchCsvCategory(csvPath),
        data,
        data.records[rowIndex],
        rowIndex
      ),
      dataUrl: `data:image/png;base64,${image.toString("base64")}`,
      sourcePath: workbenchRelativePath(projectPath, thumbnailPath)
    };
  } catch (error) {
    if (temporaryPath) fs.rmSync(temporaryPath, { force: true });
    if (savedPath) fs.rmSync(savedPath, { force: true });
    return { ok: false, error: `缩略图写入失败：${error.message}` };
  }
}

function normalizeWorkbenchUnityName(value) {
  return String(value || "")
    .normalize("NFKC")
    .replace(/[\u0000-\u001f\u007f\u009f\u200b-\u200d\u2060\ufeff]/g, "")
    .trim()
    .toLocaleLowerCase();
}

function findWorkbenchUnityCandidate(candidates, value) {
  const normalized = normalizeWorkbenchUnityName(value);
  if (!normalized || !Array.isArray(candidates)) return null;
  return candidates.find((candidate) => (
    normalizeWorkbenchUnityName(typeof candidate === "string" ? candidate : candidate?.value || "") === normalized
  )) || null;
}

async function validateWorkbenchMainResource(payload = {}) {
  try {
    const { projectPath } = validateWorkbenchProject(payload);
    const mainAB = String(payload.mainAB || "").trim();
    const mainData = String(payload.mainData || "").trim();
    const suppliedTextureFields = payload.textureFields && typeof payload.textureFields === "object"
      ? payload.textureFields
      : {};
    const textureFields = WORKBENCH_TEXTURE_FIELDS.map((key) => ({
      key,
      value: String(
        suppliedTextureFields[key]
          ?? (key === "MainTex" ? payload.mainTex : key === "ColorMaskTex" ? payload.colorMaskTex : "")
          ?? ""
      ).trim()
    }));
    const checks = {
      MainAB: { value: mainAB, status: mainAB ? "missing" : "empty" },
      MainData: { value: mainData, status: mainData ? "pending" : "empty" }
    };
    for (const field of textureFields) {
      checks[field.key] = { value: field.value, status: field.value ? "pending" : "empty" };
    }

    if (!mainAB) {
      return { ok: true, status: "incomplete", message: "MainAB 待填写", checks };
    }

    let resource;
    try {
      resource = resolveWorkbenchExistingResource(projectPath, mainAB);
    } catch (_error) {
      return {
        ok: true,
        status: "missing_file",
        message: "MainAB 文件不存在",
        checks,
        resource: { relativePath: mainAB }
      };
    }

    checks.MainAB = { value: mainAB, status: "found" };
    const result = await fetchBackend("/workbench/unity3d/assets", {
      method: "POST",
      body: { path: resource.path }
    });
    if (!result?.ok) {
      return {
        ok: true,
        status: "unreadable",
        message: "Unity3D 无法读取",
        checks,
        resource
      };
    }

    const mainDataCandidate = findWorkbenchUnityCandidate(result.game_object_names, mainData)
      || findWorkbenchUnityCandidate(result.candidates, mainData);
    checks.MainData = {
      value: mainData,
      status: mainData ? (mainDataCandidate ? "found" : "missing") : "empty",
      candidate: mainDataCandidate
    };

    const textureCandidates = Array.isArray(result.texture_candidates)
      ? result.texture_candidates
      : [];
    for (const field of textureFields) {
      const candidate = findWorkbenchUnityCandidate(textureCandidates, field.value);
      checks[field.key] = {
        value: field.value,
        status: field.value ? (candidate ? "found" : "missing") : "empty",
        candidate
      };
    }

    const missingTextures = textureFields
      .filter((field) => checks[field.key].status === "missing")
      .map((field) => field.key);
    let status = "ready";
    let message = "Unity3D 资源已找到";
    if (!mainData) {
      status = "incomplete";
      message = "MainData 待填写";
    } else if (!mainDataCandidate) {
      status = "main_data_missing";
      message = "MainData 不存在于 Unity3D";
    } else if (missingTextures.length) {
      status = "texture_missing";
      message = `${missingTextures.join("、")} 不存在于 Unity3D`;
    }

    return {
      ok: true,
      status,
      message,
      checks,
      resource,
      objectCount: Number(result.object_count || 0),
      gameObjectCount: Number(result.game_object_count || 0),
      textureCount: Number(result.texture_count || textureCandidates.length)
    };
  } catch (error) {
    return { ok: false, error: error.message };
  }
}

function updateWorkbenchCsvItem(csvPath, itemId, updates = {}) {
  const text = fs.readFileSync(csvPath, "utf-8").replace(/^\uFEFF/, "");
  const rows = parseWorkbenchCsvRows(text);
  const headerIndex = rows.findIndex((row) => {
    const columns = new Set(row.map((value) => value.trim()));
    return columns.has("ID") && columns.has("Name");
  });
  if (headerIndex < 0) throw new Error("CSV 表头未找到");

  const header = rows[headerIndex].map((value) => value.trim());
  const requiredFields = ["ID", "MainManifest", "MainAB", "MainData"];
  const missingFields = requiredFields.filter((field) => !header.includes(field));
  if (missingFields.length) {
    throw new Error(`CSV 缺少必要字段：${missingFields.join(", ")}`);
  }

  const additionalResourceFields = Object.keys(updates)
    .filter((field) => (
      (WORKBENCH_TEXTURE_FIELDS.includes(field) || WORKBENCH_THUMBNAIL_FIELDS.includes(field))
      && !header.includes(field)
    ));
  for (const field of additionalResourceFields) {
    if (WORKBENCH_THUMBNAIL_FIELDS.includes(field)) {
      const thumbABIndex = header.indexOf("ThumbAB");
      const thumbTexIndex = header.indexOf("ThumbTex");
      const thumbnailInsertIndex = field === "ThumbAB"
        ? (thumbTexIndex >= 0 ? thumbTexIndex : header.length)
        : (thumbABIndex >= 0 ? thumbABIndex + 1 : header.length);
      header.splice(thumbnailInsertIndex, 0, field);
      continue;
    }
    const fieldIndex = WORKBENCH_TEXTURE_FIELDS.includes(field)
      ? WORKBENCH_TEXTURE_FIELDS.indexOf(field)
      : WORKBENCH_TEXTURE_FIELDS.length;
    const followingField = WORKBENCH_TEXTURE_FIELDS
      .slice(fieldIndex + 1)
      .find((candidate) => header.includes(candidate));
    const thumbnailIndex = header.findIndex((candidate) => WORKBENCH_THUMBNAIL_FIELDS.includes(candidate));
    const insertIndex = followingField
      ? header.indexOf(followingField)
      : (thumbnailIndex >= 0 ? thumbnailIndex : header.length);
    header.splice(insertIndex, 0, field);
  }
  if (additionalResourceFields.length) {
    rows[headerIndex] = header;
    for (let index = headerIndex + 1; index < rows.length; index += 1) {
      while (rows[index].length < header.length) rows[index].push("0");
    }
  }

  const idIndex = header.indexOf("ID");
  const targetId = String(itemId || "").trim();
  const rowIndex = rows.findIndex((row, index) => (
    index > headerIndex && String(row[idIndex] || "").trim() === targetId
  ));
  if (rowIndex < 0) throw new Error(`CSV 中找不到物品 ID：${targetId}`);

  const row = [...rows[rowIndex]];
  while (row.length < header.length) row.push("0");
  for (const [key, value] of Object.entries(updates)) {
    const index = header.indexOf(key);
    if (index >= 0) row[index] = workbenchCsvStoredValue(key, value);
  }
  for (let index = 0; index < header.length; index += 1) {
    row[index] = workbenchCsvStoredValue(header[index], row[index]);
  }
  rows[rowIndex] = row;
  const output = rows.map((currentRow) => currentRow.map(csvCell).join(",")).join("\n") + "\n";
  const temporaryPath = `${csvPath}.star-manager-${process.pid}-${Date.now()}.tmp`;
  try {
    fs.writeFileSync(temporaryPath, output, "utf-8");
    fs.renameSync(temporaryPath, csvPath);
  } catch (error) {
    fs.rmSync(temporaryPath, { force: true });
    throw error;
  }
}

function updateWorkbenchItemResourceFields(payload = {}) {
  try {
    const { projectPath, project } = validateWorkbenchProject(payload);
    const csvRelativePath = String(payload.csvPath || "").trim();
    const itemId = String(payload.itemId || "").trim();
    if (!csvRelativePath || !itemId) throw new Error("物品 CSV 定位信息不完整");

    const csvPath = path.resolve(projectPath, csvRelativePath);
    if (!isPathInside(projectPath, csvPath) || !fs.existsSync(csvPath) || !fs.statSync(csvPath).isFile()) {
      throw new Error("物品 CSV 文件不存在");
    }

    const allowedFields = ["Name", "MainData", ...WORKBENCH_TEXTURE_FIELDS, ...WORKBENCH_THUMBNAIL_FIELDS];
    const sourceFields = payload.fields && typeof payload.fields === "object" ? payload.fields : {};
    const updates = {};
    for (const field of allowedFields) {
      if (Object.prototype.hasOwnProperty.call(sourceFields, field)) {
        updates[field] = String(sourceFields[field] ?? "").trim();
      }
    }
    if (!Object.keys(updates).length) throw new Error("没有可更新的资源字段");

    updateWorkbenchCsvItem(csvPath, itemId, updates);
    const data = readWorkbenchCsvData(projectPath, csvRelativePath);
    const rowIndex = data.records.findIndex((record) => String(record.ID || "") === itemId);
    if (rowIndex < 0) throw new Error("CSV 更新后无法重新读取物品行");
    return {
      ok: true,
      item: createWorkbenchCsvItem(
        project,
        projectPath,
        csvRelativePath,
        readWorkbenchCsvCategory(csvPath),
        data,
        data.records[rowIndex],
        rowIndex
      ),
      updatedFields: Object.keys(updates)
    };
  } catch (error) {
    return { ok: false, error: `资源字段更新失败：${error.message}` };
  }
}

function nextWorkbenchResourceTarget(projectPath, project) {
  const author = workbenchSafeResourceSegment(project.author, "author");
  const modName = workbenchSafeResourceSegment(project.name, "mod");
  const targetDirectory = path.join(
    projectPath,
    WORKBENCH_RESOURCE_DIRECTORY,
    author
  );
  fs.mkdirSync(targetDirectory, { recursive: true });

  let sequence = 1;
  let targetPath;
  do {
    targetPath = path.join(targetDirectory, `${author}_${modName}_${sequence}.unity3d`);
    sequence += 1;
  } while (fs.existsSync(targetPath));

  const abdataPath = path.join(projectPath, "abdata");
  return {
    path: targetPath,
    relativePath: workbenchRelativePath(abdataPath, targetPath),
    fileName: path.basename(targetPath)
  };
}

function resolveWorkbenchExistingResource(projectPath, relativePath) {
  const normalized = String(relativePath || "").trim().replaceAll("\\", "/");
  const abdataPath = path.resolve(projectPath, "abdata");
  const candidate = path.resolve(abdataPath, normalized);
  if (
    !normalized
    || path.isAbsolute(normalized)
    || !isPathInside(abdataPath, candidate)
    || path.extname(candidate).toLocaleLowerCase() !== ".unity3d"
    || !fs.existsSync(candidate)
    || !fs.statSync(candidate).isFile()
  ) {
    throw new Error("请选择当前工程 abdata 下存在的 Unity3D 文件");
  }
  return {
    path: candidate,
    relativePath: workbenchRelativePath(abdataPath, candidate),
    fileName: path.basename(candidate)
  };
}

function validateWorkbenchSourceFile(sourcePath) {
  const resolved = path.resolve(String(sourcePath || "").trim());
  if (
    !resolved
    || path.extname(resolved).toLocaleLowerCase() !== ".unity3d"
    || !fs.existsSync(resolved)
    || !fs.statSync(resolved).isFile()
  ) {
    throw new Error("请选择有效的 Unity3D 文件");
  }
  return resolved;
}

function validateWorkbenchImageFile(sourcePath) {
  const resolved = path.resolve(String(sourcePath || "").trim());
  if (
    !resolved
    || ![".png", ".jpg", ".jpeg", ".webp"].includes(path.extname(resolved).toLocaleLowerCase())
    || !fs.existsSync(resolved)
    || !fs.statSync(resolved).isFile()
  ) {
    throw new Error("请选择有效的 PNG、JPG 或 WebP 贴图");
  }
  if (fs.statSync(resolved).size > 50 * 1024 * 1024) {
    throw new Error("外部贴图不能超过 50 MB");
  }
  return resolved;
}

function sb3ScriptString(value) {
  const normalized = String(value || "");
  if (!normalized || /[\r\n\u0000]/.test(normalized)) {
    throw new Error("SB3Utility 脚本参数不能为空或包含控制字符");
  }
  if (normalized.includes('"')) {
    throw new Error("SB3Utility 脚本参数不能包含双引号");
  }
  return `"${normalized}"`;
}

function resolveSb3UtilityScriptExecutable() {
  const savedSettings = loadSettingsFile();
  const configured = String(savedSettings.settings?.sb3utilityExecutablePath || DEFAULT_SB3UTILITY_EXECUTABLE_PATH).trim();
  if (!configured) throw new Error("请先在设置中配置 SB3Utility 可执行文件");
  const selectedPath = path.resolve(configured);
  const candidates = [
    path.basename(selectedPath).toLowerCase() === "sb3utilityscript.exe"
      ? selectedPath
      : path.join(path.dirname(selectedPath), "SB3UtilityScript.exe"),
    selectedPath
  ];
  const executablePath = candidates.find((candidate) => fs.existsSync(candidate) && fs.statSync(candidate).isFile());
  if (!executablePath) {
    throw new Error(`SB3UtilityScript.exe 未找到：${path.join(path.dirname(selectedPath), "SB3UtilityScript.exe")}`);
  }
  return executablePath;
}

async function runSb3UtilityScript(lines) {
  if (process.platform !== "win32") throw new Error("SB3UtilityScript 仅支持 Windows");
  const executablePath = resolveSb3UtilityScriptExecutable();
  const scriptDirectory = path.join(app.getPath("temp"), "star-manager-sb3utility");
  fs.mkdirSync(scriptDirectory, { recursive: true });
  const scriptPath = path.join(scriptDirectory, `workbench-${crypto.randomUUID()}.txt`);
  fs.writeFileSync(scriptPath, `${lines.filter(Boolean).join("\r\n")}\r\n`, "utf-8");
  try {
    await execFileText(executablePath, [scriptPath], {
      cwd: path.dirname(executablePath),
      outputEncoding: "auto"
    });
    return { ok: true, executable: executablePath, script: scriptPath };
  } catch (error) {
    throw new Error(`SB3UtilityScript 执行失败：${error.message}`);
  } finally {
    fs.rmSync(scriptPath, { force: true });
  }
}

async function runWorkbenchSb3Mutation({ sourcePath, outputPath, operation, selectedName = "", componentIndex = 1, imagePath = "", textureName = "", replaceExisting = false }) {
  const source = path.resolve(String(sourcePath || ""));
  const requestedOutput = path.resolve(String(outputPath || source));
  if (!fs.existsSync(source) || path.extname(source).toLowerCase() !== ".unity3d") throw new Error("Unity3D 文件不存在");
  const jobRoot = path.join(app.getPath("temp"), "star-manager-sb3utility", `job-${crypto.randomUUID()}`);
  const scriptInput = path.join(jobRoot, "abdata", "chara", path.basename(source));
  const scriptOutput = path.join(jobRoot, "abdata", "chara", `.star-manager-sb3-${crypto.randomUUID()}.unity3d`);
  fs.mkdirSync(path.dirname(scriptInput), { recursive: true });
  fs.copyFileSync(source, scriptInput);
  const executablePath = resolveSb3UtilityScriptExecutable();
  const pluginPath = path.join(path.dirname(executablePath), "plugins", "UnityPlugin.dll");
  if (!fs.existsSync(pluginPath)) throw new Error(`SB3Utility UnityPlugin.dll 未找到：${pluginPath}`);
  const lines = [
    `LoadPlugin(path=${sb3ScriptString(pluginPath)})`,
    `unityParser0 = OpenUnity3d(path=${sb3ScriptString(scriptInput)})`,
    "unityEditor0 = Unity3dEditor(parser=unityParser0)",
    "unityEditor0.GetAssetNames(filter=True)"
  ];
  if (operation === "unique_cab") {
    lines.push(`unityEditor0.RenameCabinet(cabinetIndex=0, name=${sb3ScriptString(`CAB-${crypto.randomUUID().replaceAll("-", "")}`)})`);
  } else if (operation === "rename_selected") {
    if (!selectedName) throw new Error("请先选择 MainData 模型对象");
    const selectedComponentIndex = Number(componentIndex);
    if (!Number.isInteger(selectedComponentIndex) || selectedComponentIndex < 0) {
      throw new Error("MainData 缺少有效的 GameObject 组件索引，请重新选择模板对象");
    }
    // SetFrameName(id=0) relies on the GUI-created root frame and throws a
    // NullReferenceException in SB3UtilityScript.exe. SetAssetName edits the
    // serialized GameObject directly and keeps custom MonoBehaviours intact.
    lines.push(
      `unityEditor0.SetAssetName(componentIndex=${selectedComponentIndex}, name=${sb3ScriptString(textureName || selectedName)})`
    );
  } else if (operation === "duplicate_selected") {
    if (!selectedName) throw new Error("请先选择 MainData 模型对象");
    lines.push(
      `sourceParser0 = OpenUnity3d(path=${sb3ScriptString(scriptInput)})`,
      "sourceEditor0 = Unity3dEditor(parser=sourceParser0)",
      `sourceVirtualAnimator0 = sourceEditor0.OpenVirtualAnimator(componentIndex=${Math.max(0, Number(componentIndex) || 1)})`,
      "sourceAnimatorEditor0 = AnimatorEditor(parser=sourceVirtualAnimator0)",
      `sourceFrameId0 = sourceAnimatorEditor0.GetFrameId(name=${sb3ScriptString(selectedName)})`,
      `virtualAnimator0 = unityEditor0.OpenVirtualAnimator(componentIndex=${Math.max(0, Number(componentIndex) || 1)})`,
      "animatorEditor0 = AnimatorEditor(parser=virtualAnimator0)",
      // Use a separately parsed source editor so AddFrame treats the source
      // mesh/material/texture collections as external and copies them into
      // the destination instead of reusing the destination assets.
      "animatorEditor0.AddFrame(srcFrame=sourceAnimatorEditor0.Frames[sourceFrameId0], srcMaterials=sourceAnimatorEditor0.Materials, srcTextures=sourceAnimatorEditor0.Textures, appendIfMissing=true, destParentId=-1)"
    );
  } else if (operation === "import_texture" || operation === "replace_texture") {
    if (!imagePath || !textureName) throw new Error("贴图路径或资源名不能为空");
    lines.push(
      `virtualAnimator0 = unityEditor0.OpenVirtualAnimator(componentIndex=${Math.max(0, Number(componentIndex) || 1)})`,
      "animatorEditor0 = AnimatorEditor(parser=virtualAnimator0)",
      `image0 = ImportTexture(path=${sb3ScriptString(imagePath)})`
    );
    if (operation === "replace_texture" || replaceExisting) {
      lines.push(`textureId0 = animatorEditor0.GetTextureId(name=${sb3ScriptString(textureName)})`, `animatorEditor0.ReplaceTexture(id=textureId0, image=image0)`);
    } else {
      lines.push(`animatorEditor0.AddTexture(image=image0)`, `animatorEditor0.SetTextureName(id=animatorEditor0.Textures.Count - 1, name=${sb3ScriptString(textureName)})`);
    }
  } else {
    throw new Error(`不支持的 SB3Utility 工作台操作：${operation}`);
  }
  // Refresh the cabinet after mutation. Without this GUI-equivalent refresh,
  // SB3UtilityScript may lazily serialize a custom MonoBehaviour and report
  // UnityPlugin.NotLoaded (for example CmpAccessory PathID 50).
  lines.push("unityEditor0.GetAssetNames(filter=True)");
  lines.push(`unityEditor0.SaveUnity3d(path=${sb3ScriptString(scriptOutput)}, keepBackup=False, backupExtension=".unit-y3d", background=False, clearMainAsset=True, pathIDsMode=-1, compressionLevel=3, compressionBufferSize=262144)`);
  try {
    await runSb3UtilityScript(lines);
    if (!fs.existsSync(scriptOutput) || fs.statSync(scriptOutput).size <= 0) throw new Error("SB3UtilityScript 未生成有效的 Unity3D 输出");
    const destination = requestedOutput.toLowerCase() === source.toLowerCase() ? source : requestedOutput;
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    const replacementPath = path.join(path.dirname(destination), `.${path.basename(destination)}-${crypto.randomUUID()}.tmp`);
    try {
      fs.copyFileSync(scriptOutput, replacementPath);
      fs.copyFileSync(replacementPath, destination);
    } finally {
      fs.rmSync(replacementPath, { force: true });
    }
    return { ok: true, path: destination, operation };
  } finally {
    const tempRoot = path.resolve(app.getPath("temp"));
    const resolvedJobRoot = path.resolve(jobRoot);
    if (resolvedJobRoot.toLocaleLowerCase().startsWith(`${tempRoot.toLocaleLowerCase()}${path.sep}`)) {
      fs.rmSync(resolvedJobRoot, { recursive: true, force: true });
    }
  }
}

async function runWorkbenchPythonPreprocess({ sourcePath, operation, selectedName = "", selectedPathId = 0, selectedAssetFile = "", newName = "" }) {
  const result = await fetchBackend("/workbench/unity3d/preprocess", {
    method: "POST",
    body: {
      path: sourcePath,
      operation,
      selected_path_id: Number(selectedPathId || 0),
      selected_asset_file: String(selectedAssetFile || ""),
      selected_name: String(selectedName || ""),
      new_name: String(newName || "")
    }
  });
  if (!result?.ok) {
    throw new Error(result?.error || "Unity3D 对象处理失败");
  }
  const resultPath = String(result.path || "").trim();
  const derivedPath = path.resolve(resultPath);
  if (!resultPath || path.extname(derivedPath).toLowerCase() !== ".unity3d" || !fs.existsSync(derivedPath) || fs.statSync(derivedPath).size <= 0) {
    throw new Error("Unity3D 对象处理未生成有效文件");
  }
  return { ...result, path: derivedPath };
}

async function runWorkbenchSb3DuplicateAndRename({
  sourcePath,
  outputPath,
  selectedName,
  newName,
  selectedPathId = 0,
  selectedAssetFile = "",
  componentIndex = 1
}) {
  const duplicated = await fetchBackend("/workbench/unity3d/duplicate", {
    method: "POST",
    body: {
      path: sourcePath,
      selected_path_id: Number(selectedPathId || 0),
      selected_asset_file: String(selectedAssetFile || ""),
      selected_name: String(selectedName || ""),
      new_name: String(newName || "")
    }
  });
  if (!duplicated?.ok) {
    throw new Error(duplicated?.error || "Unity3D 对象复制失败");
  }
  const derivedPath = path.resolve(String(duplicated.path || ""));
  if (!derivedPath || !fs.existsSync(derivedPath) || fs.statSync(derivedPath).size <= 0) {
    throw new Error("Unity3D 对象复制未生成有效文件");
  }
  const destination = path.resolve(String(outputPath || ""));
  fs.mkdirSync(path.dirname(destination), { recursive: true });
  const replacementPath = path.join(
    path.dirname(destination),
    `.${path.basename(destination)}-${crypto.randomUUID()}.tmp`
  );
  try {
    fs.copyFileSync(derivedPath, replacementPath);
    fs.copyFileSync(replacementPath, destination);
  } finally {
    fs.rmSync(replacementPath, { force: true });
  }
  return {
    ...duplicated,
    ok: true,
    path: destination,
    operation: "duplicate_and_rename_selected"
  };

  // Kept below for the other SB3Utility-based mutation experiments during
  // development; the return above is the production copy path.
  const duplicateOutputPath = path.join(
    app.getPath("temp"),
    "star-manager-sb3utility",
    `duplicate-${crypto.randomUUID()}.unity3d`
  );
  try {
    const originalAssets = await fetchBackend("/workbench/unity3d/assets", {
      method: "POST",
      body: { path: sourcePath }
    });
    if (!originalAssets?.ok) throw new Error(originalAssets?.error || "无法读取当前 Unity3D 对象");
    const candidateKey = (candidate) => `${String(candidate?.asset_file || "").toLocaleLowerCase()}:${Number(candidate?.path_id || 0)}`;
    const originalCandidateKeys = new Set((originalAssets.candidates || []).map(candidateKey));
    await runWorkbenchSb3Mutation({
      sourcePath,
      outputPath: duplicateOutputPath,
      operation: "duplicate_selected",
      selectedName,
      componentIndex
    });
    const duplicatedAssets = await fetchBackend("/workbench/unity3d/assets", {
      method: "POST",
      body: { path: duplicateOutputPath }
    });
    if (!duplicatedAssets?.ok) throw new Error(duplicatedAssets?.error || "无法定位复制后的对象");
    const normalizedSelectedName = String(selectedName || "").trim();
    const duplicatedCandidatePool = [
      ...(duplicatedAssets.candidates || []),
      ...(duplicatedAssets.game_object_candidates || [])
    ];
    const seenDuplicatedCandidateKeys = new Set();
    const duplicatedCandidates = duplicatedCandidatePool.filter((candidate) => {
      const candidateName = String(candidate?.value || "").trim();
      const key = candidateKey(candidate);
      if (
        !candidateName
        || originalCandidateKeys.has(key)
        || seenDuplicatedCandidateKeys.has(key)
        || String(candidate?.kind || "").toLocaleLowerCase() !== "gameobject"
      ) {
        return false;
      }
      seenDuplicatedCandidateKeys.add(key);
      return true;
    });
    const selectedNameLower = normalizedSelectedName.toLocaleLowerCase();
    const duplicatedCandidate = duplicatedCandidates
      .sort((left, right) => {
        const score = (candidate) => {
          const candidateName = String(candidate?.value || "").trim().toLocaleLowerCase();
          let value = 0;
          if (candidateName === selectedNameLower) value += 100;
          else if (candidateName.startsWith(selectedNameLower)) value += 70;
          if (candidate?.is_renderer_root) value += 10;
          return value;
        };
        return score(right) - score(left);
      })
      .find((candidate) => {
        const candidateName = String(candidate?.value || "").trim().toLocaleLowerCase();
        return candidateName === selectedNameLower || candidateName.startsWith(selectedNameLower);
      });
    if (!duplicatedCandidate) throw new Error("无法定位复制后的 MainData 对象");
    const duplicatedComponentIndex = Number(duplicatedCandidate.component_index);
    if (!Number.isInteger(duplicatedComponentIndex) || duplicatedComponentIndex < 0) {
      throw new Error("复制后的对象缺少有效的组件索引");
    }
    return await runWorkbenchSb3Mutation({
      sourcePath: duplicateOutputPath,
      outputPath,
      operation: "rename_selected",
      selectedName: String(duplicatedCandidate.value || "").trim(),
      textureName: newName,
      componentIndex: duplicatedComponentIndex
    });
  } finally {
    fs.rmSync(duplicateOutputPath, { force: true });
  }
}

async function applyWorkbenchMainResource(payload = {}) {
  let copiedTarget = null;
  try {
    const { projectPath, project } = validateWorkbenchProject(payload);
    const mode = String(payload.mode || "").trim().toLocaleLowerCase();
    let mainData = String(payload.mainData || "").trim();
    const csvRelativePath = String(payload.csvPath || "").trim();
    const itemId = String(payload.itemId || "").trim();
    if (!csvRelativePath || !itemId) throw new Error("物品 CSV 定位信息不完整");

    const csvPath = path.resolve(projectPath, csvRelativePath);
    if (!isPathInside(projectPath, csvPath) || !fs.existsSync(csvPath) || !fs.statSync(csvPath).isFile()) {
      throw new Error("物品 CSV 文件不存在");
    }

    if (mode === "template") {
      const data = readWorkbenchCsvData(projectPath, csvRelativePath);
      const record = data.records.find((candidate) => String(candidate.ID || "") === itemId);
      const itemName = String(record?.Name || "").trim();
      mainData = itemName ? `${itemName}_obj` : "";
    }
    if (!mainData) throw new Error("MainData 无法从当前物品名称生成");

    let resource;
    if (mode === "existing") {
      resource = resolveWorkbenchExistingResource(projectPath, payload.relativePath);
    } else if (mode === "import" || mode === "template" || mode === "database") {
      const sourcePath = mode === "template"
        ? WORKBENCH_TEMPLATE_PATH
        : validateWorkbenchSourceFile(payload.sourcePath);
      if (mode === "template" && !fs.existsSync(sourcePath)) {
        throw new Error("应用内置 Unity3D 模板不存在");
      }
      resource = nextWorkbenchResourceTarget(projectPath, project);
      fs.copyFileSync(sourcePath, resource.path);
      copiedTarget = resource.path;
      await runWorkbenchSb3Mutation({
        sourcePath: resource.path,
        outputPath: resource.path,
        operation: "unique_cab"
      });
    } else {
      throw new Error("未知的 Unity3D 资源处理方式");
    }

    updateWorkbenchCsvItem(csvPath, itemId, {
      MainManifest: "abdata",
      MainAB: resource.relativePath,
      MainData: mainData,
      StateType: "0"
    });

    const data = readWorkbenchCsvData(projectPath, csvRelativePath);
    const rowIndex = data.records.findIndex((record) => String(record.ID || "") === itemId);
    if (rowIndex < 0) throw new Error("CSV 更新后无法重新读取物品行");
    const item = createWorkbenchCsvItem(
      project,
      projectPath,
      csvRelativePath,
      readWorkbenchCsvCategory(csvPath),
      data,
      data.records[rowIndex],
      rowIndex
    );
    return {
      ok: true,
      item,
      resource: {
        mode,
        path: resource.path,
        relativePath: resource.relativePath,
        fileName: resource.fileName,
        mainData
      }
    };
  } catch (error) {
    if (copiedTarget) fs.rmSync(copiedTarget, { force: true });
    return { ok: false, error: `主资源处理失败：${error.message}` };
  }
}

function ensureWorkbenchCategoryCsv(projectPath, projectName, category) {
  const normalizedCategory = normalizeWorkbenchCategory(category);
  const listRootPath = path.join(projectPath, WORKBENCH_LIST_DIRECTORY);
  const existingCsv = collectWorkbenchCsvFiles(listRootPath)
    .find((csvPath) => readWorkbenchCsvCategory(csvPath).toLocaleLowerCase() === normalizedCategory.toLocaleLowerCase());
  if (existingCsv) {
    return {
      path: existingCsv,
      relativePath: path.relative(projectPath, existingCsv).replaceAll(path.sep, "/"),
      created: false
    };
  }

  const listPath = path.join(listRootPath, "characustom");
  fs.mkdirSync(listPath, { recursive: true });
  const fileName = `${safeProjectDirectoryName(projectName)}_${safeProjectDirectoryName(normalizedCategory)}.csv`;
  const csvPath = path.join(listPath, fileName);
  if (fs.existsSync(csvPath)) {
    throw new Error(`类别 CSV 已存在但无法识别类别：${fileName}`);
  }

  const template = workbenchCsvTemplateForCategory(normalizedCategory);
  const csvContent = [
    ...template.metadataRows.map(csvCell),
    template.header.map(csvCell).join(","),
    ""
  ].join("\n");
  fs.writeFileSync(csvPath, csvContent, "utf-8");
  return {
    path: csvPath,
    relativePath: path.relative(projectPath, csvPath).replaceAll(path.sep, "/"),
    created: true
  };
}

function unescapeXml(value) {
  return String(value || "")
    .replaceAll("&lt;", "<")
    .replaceAll("&gt;", ">")
    .replaceAll("&quot;", '"')
    .replaceAll("&apos;", "'")
    .replaceAll("&amp;", "&");
}

function readManifestField(manifest, fieldName) {
  const match = String(manifest || "").match(new RegExp(
    "<" + fieldName + ">([\\s\\S]*?)</" + fieldName + ">",
    "i"
  ));
  return match ? unescapeXml(match[1]).trim() : "";
}

function isPathInside(parentPath, childPath) {
  const relativePath = path.relative(parentPath, childPath);
  return Boolean(relativePath) && !relativePath.startsWith("..") && !path.isAbsolute(relativePath);
}

function readWorkbenchManifest(projectPath, manifestRelativePath = "manifest.xml") {
  const manifestPath = path.resolve(projectPath, manifestRelativePath);
  if (
    path.isAbsolute(manifestRelativePath)
    || !isPathInside(projectPath, manifestPath)
    || !fs.existsSync(manifestPath)
    || !fs.statSync(manifestPath).isFile()
  ) {
    return null;
  }

  let manifest;
  try {
    manifest = fs.readFileSync(manifestPath, "utf-8");
  } catch {
    return null;
  }
  const guid = readManifestField(manifest, "guid");
  const name = readManifestField(manifest, "name");
  const version = readManifestField(manifest, "version");
  const author = readManifestField(manifest, "author");
  if (!guid || !name || !version || !author || !/^com\.[^.]+\.[^.]+$/.test(guid)) return null;
  return { manifestPath, guid, name, version, author };
}

function writeWorkbenchProjectFile(projectPath, projectId, createdAt) {
  const projectFilePath = path.join(projectPath, WORKBENCH_PROJECT_FILE_NAME);
  fs.writeFileSync(projectFilePath, JSON.stringify({
    format: WORKBENCH_PROJECT_FORMAT,
    schemaVersion: WORKBENCH_PROJECT_SCHEMA_VERSION,
    projectId,
    manifest: "manifest.xml",
    createdAt,
    generator: "Star_Manager"
  }, null, 2) + "\n", "utf-8");
  return projectFilePath;
}

function readWorkbenchProject(projectPath) {
  const projectFilePath = path.join(projectPath, WORKBENCH_PROJECT_FILE_NAME);
  if (!fs.existsSync(projectFilePath) || !fs.statSync(projectFilePath).isFile()) return null;

  let projectFile;
  try {
    projectFile = JSON.parse(fs.readFileSync(projectFilePath, "utf-8"));
  } catch {
    return null;
  }
  if (
    projectFile?.format !== WORKBENCH_PROJECT_FORMAT
    || Number(projectFile?.schemaVersion) !== WORKBENCH_PROJECT_SCHEMA_VERSION
    || !String(projectFile?.projectId || "").trim()
  ) {
    return null;
  }

  const manifestData = readWorkbenchManifest(
    projectPath,
    String(projectFile.manifest || "manifest.xml").trim()
  );
  if (!manifestData) return null;

  return {
    id: String(projectFile.projectId).trim(),
    guid: manifestData.guid,
    name: manifestData.name,
    path: projectPath,
    manifestPath: manifestData.manifestPath,
    projectFilePath,
    createdAt: String(projectFile.createdAt || "").trim(),
    version: manifestData.version,
    author: manifestData.author
  };
}

function createWorkbenchCsvItem(project, projectPath, csvRelativePath, category, data, record, rowIndex) {
  const csvPath = path.resolve(projectPath, csvRelativePath);
  return {
    id: `${csvRelativePath}#${rowIndex + 1}`,
    projectId: project.id,
    name: String(record?.Name || "").trim(),
    category,
    csvPath: csvRelativePath,
    csvData: {
      path: csvRelativePath,
      header: data.header,
      fields: csvFieldsForRecord(data.header, record),
      record,
      rowNumber: rowIndex + 1,
      rowCount: data.rowCount,
      error: data.error
    },
    path: path.dirname(csvPath),
    csvFilePath: csvPath,
    createdAt: ""
  };
}

function scanWorkbenchItems(payload = {}) {
  const rawProjectPath = String(payload.projectPath || "").trim();
  const projectPath = path.resolve(rawProjectPath);
  const expectedProjectId = String(payload.projectId || "").trim();
  if (!rawProjectPath || !fs.existsSync(projectPath) || !fs.statSync(projectPath).isDirectory()) {
    return { ok: false, error: "当前工程目录不存在", items: [] };
  }
  const project = readWorkbenchProject(projectPath);
  if (!project || (expectedProjectId && project.id !== expectedProjectId)) {
    return { ok: false, error: "当前目录不是有效的 Star_Manager 工程", items: [] };
  }

  const items = [];
  const listPath = path.join(projectPath, WORKBENCH_LIST_DIRECTORY);
  for (const csvPath of collectWorkbenchCsvFiles(listPath)) {
    const csvRelativePath = path.relative(projectPath, csvPath).replaceAll(path.sep, "/");
    const category = readWorkbenchCsvCategory(csvPath);
    const data = readWorkbenchCsvData(projectPath, csvRelativePath);
    if (data.error || !category) continue;
    data.records.forEach((record, rowIndex) => {
      items.push(createWorkbenchCsvItem(project, projectPath, csvRelativePath, category, data, record, rowIndex));
    });
  }
  return { ok: true, items };
}

function createWorkbenchItem(payload = {}) {
  const rawProjectPath = String(payload.projectPath || "").trim();
  const projectPath = path.resolve(rawProjectPath);
  const projectId = String(payload.projectId || "").trim();
  const itemName = String(payload.name || "").trim();
  const itemCategory = normalizeWorkbenchCategory(payload.category);
  if (!itemName) return { ok: false, error: "请输入物品名称" };
  if (!itemCategory) return { ok: false, error: "请输入物品类别" };
  if (!rawProjectPath || !fs.existsSync(projectPath) || !fs.statSync(projectPath).isDirectory()) {
    return { ok: false, error: "当前工程目录不存在" };
  }

  const project = readWorkbenchProject(projectPath);
  if (!project || project.id !== projectId) {
    return { ok: false, error: "当前工程无效，请重新选择工程" };
  }

  let categoryCsv = null;
  try {
    categoryCsv = ensureWorkbenchCategoryCsv(projectPath, project.name, itemCategory);
    const appended = appendWorkbenchCsvItem(categoryCsv.path, itemName, itemCategory);
    const data = readWorkbenchCsvData(projectPath, categoryCsv.relativePath);
    const rowIndex = data.records.findIndex((record) => String(record.ID || "") === appended.itemId);
    const record = rowIndex >= 0 ? data.records[rowIndex] : data.records[data.records.length - 1];
    const item = createWorkbenchCsvItem(
      project,
      projectPath,
      categoryCsv.relativePath,
      itemCategory,
      data,
      record,
      rowIndex >= 0 ? rowIndex : data.records.length - 1
    );
    return {
      ok: true,
      item: {
        ...item,
        csvPath: categoryCsv.relativePath,
        csvCreated: categoryCsv.created
      }
    };
  } catch (error) {
    if (categoryCsv?.created) {
      fs.rmSync(categoryCsv.path, { force: true });
    }
    return { ok: false, error: "创建物品失败：" + error.message };
  }
}

function deleteWorkbenchItem(payload = {}) {
  try {
    const { projectPath, project } = validateWorkbenchProject(payload);
    const csvRelativePath = String(payload.csvPath || "").trim().replaceAll("\\", "/");
    const itemId = String(payload.itemId || "").trim();
    const listPath = path.join(projectPath, WORKBENCH_LIST_DIRECTORY);
    const csvPath = path.resolve(projectPath, csvRelativePath);
    if (
      !csvRelativePath
      || path.isAbsolute(csvRelativePath)
      || path.extname(csvPath).toLocaleLowerCase() !== ".csv"
      || !isPathInside(listPath, csvPath)
      || !fs.existsSync(csvPath)
      || !fs.statSync(csvPath).isFile()
    ) {
      throw new Error("物品 CSV 路径无效");
    }

    const separatorIndex = itemId.lastIndexOf("#");
    const itemPath = separatorIndex >= 0 ? itemId.slice(0, separatorIndex).replaceAll("\\", "/") : "";
    const rowNumber = separatorIndex >= 0 ? Number.parseInt(itemId.slice(separatorIndex + 1), 10) : NaN;
    const normalizedCsvPath = workbenchRelativePath(projectPath, csvPath);
    if (
      !itemPath
      || itemPath.toLocaleLowerCase() !== normalizedCsvPath.toLocaleLowerCase()
      || !Number.isInteger(rowNumber)
      || rowNumber < 1
    ) {
      throw new Error("物品定位信息无效");
    }

    const rows = parseWorkbenchCsvRows(fs.readFileSync(csvPath, "utf-8").replace(/^\uFEFF/, ""));
    const headerIndex = rows.findIndex((row) => {
      const columns = new Set(row.map((value) => value.trim()));
      return columns.has("ID") && columns.has("Name");
    });
    if (headerIndex < 0) throw new Error("CSV 表头未找到");
    const recordRows = rows.slice(headerIndex + 1).filter((row) => row.some((value) => value.trim()));
    const targetRowIndex = rowNumber - 1;
    if (targetRowIndex >= recordRows.length) throw new Error("CSV 中找不到对应物品");

    rows.splice(headerIndex + 1 + targetRowIndex, 1);
    const output = rows.map((row) => row.map(csvCell).join(",")).join("\n") + "\n";
    const temporaryPath = `${csvPath}.star-manager-${process.pid}-${Date.now()}.tmp`;
    try {
      fs.writeFileSync(temporaryPath, output, "utf-8");
      fs.renameSync(temporaryPath, csvPath);
    } catch (error) {
      fs.rmSync(temporaryPath, { force: true });
      throw error;
    }
    return { ok: true, projectId: project.id, itemId };
  } catch (error) {
    return { ok: false, error: "删除物品失败：" + error.message };
  }
}

function scanWorkbenchProjects(payload = {}) {
  const workspacePathValue = typeof payload === "string" ? payload : payload.workspacePath;
  const knownProjects = typeof payload === "string" ? [] : (Array.isArray(payload.knownProjects) ? payload.knownProjects : []);
  const workspacePath = path.resolve(String(workspacePathValue || "").trim());
  if (!workspacePath || !fs.existsSync(workspacePath) || !fs.statSync(workspacePath).isDirectory()) {
    return { ok: false, error: "工具台工作空间不存在，请重新选择文件夹", projects: [] };
  }

  const knownProjectsByPath = new Map(
    knownProjects
      .filter((project) => project?.path && project?.id)
      .map((project) => [path.resolve(String(project.path)).toLocaleLowerCase(), project])
  );
  const projects = [];
  for (const entry of fs.readdirSync(workspacePath, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    const projectPath = path.join(workspacePath, entry.name);
    let project = readWorkbenchProject(projectPath);
    if (!project && !fs.existsSync(path.join(projectPath, WORKBENCH_PROJECT_FILE_NAME))) {
      const knownProject = knownProjectsByPath.get(path.resolve(projectPath).toLocaleLowerCase());
      const manifestData = readWorkbenchManifest(projectPath);
      if (knownProject && manifestData) {
        try {
          writeWorkbenchProjectFile(
            projectPath,
            String(knownProject.id).trim(),
            String(knownProject.createdAt || "").trim() || new Date().toISOString()
          );
          project = readWorkbenchProject(projectPath);
        } catch {
          // An existing project remains usable from the settings cache when migration is not writable.
        }
      }
    }
    if (project) projects.push(project);
  }
  return { ok: true, projects };
}

function createWorkbenchProject(payload = {}) {
  const workspacePath = path.resolve(String(payload.workspacePath || "").trim());
  const projectName = String(payload.name || "").trim();
  const authorId = String(payload.authorId || "").trim();
  if (!projectName) return { ok: false, error: "请输入模组名称" };
  if (!workspacePath || !fs.existsSync(workspacePath) || !fs.statSync(workspacePath).isDirectory()) {
    return { ok: false, error: "工具台工作空间不存在，请重新选择文件夹" };
  }

  const projectId = crypto.randomUUID();
  const projectGuid = `com.${safeGuidSegment(authorId, "author")}.${safeGuidSegment(projectName, "mod")}`;
  const baseDirectoryName = safeProjectDirectoryName(projectName);
  let directoryName = baseDirectoryName;
  let projectPath = path.join(workspacePath, directoryName);
  let suffix = 2;
  while (fs.existsSync(projectPath)) {
    directoryName = `${baseDirectoryName} (${suffix})`;
    projectPath = path.join(workspacePath, directoryName);
    suffix += 1;
  }

  const relativeProjectPath = path.relative(workspacePath, projectPath);
  if (!relativeProjectPath || relativeProjectPath.startsWith("..") || path.isAbsolute(relativeProjectPath)) {
    return { ok: false, error: "模组目录必须位于工作空间内" };
  }

  try {
    fs.mkdirSync(projectPath);
    fs.mkdirSync(path.join(projectPath, "abdata", "list"), { recursive: true });
    const manifestPath = path.join(projectPath, "manifest.xml");
    const createdAt = new Date().toISOString();
    const manifest = [
      '<?xml version="1.0" encoding="utf-8"?>',
      '<manifest schema-ver="1">',
      `\t<guid>${escapeXml(projectGuid)}</guid>`,
      `\t<name>${escapeXml(projectName)}</name>`,
      '\t<version>1.0.0</version>',
      `\t<author>${escapeXml(authorId)}</author>`,
      '\t<description></description>',
      '</manifest>',
      ""
    ].join("\n");
    fs.writeFileSync(manifestPath, manifest, "utf-8");
    const projectFilePath = writeWorkbenchProjectFile(projectPath, projectId, createdAt);
    return {
      ok: true,
      project: {
        id: projectId,
        guid: projectGuid,
        name: projectName,
        path: projectPath,
        manifestPath,
        projectFilePath,
        createdAt
      }
    };
  } catch (error) {
    return { ok: false, error: `创建模组工程失败：${error.message}` };
  }
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

ipcMain.handle("dialog:selectUnity3dFile", async (_event, title) => {
  const result = await dialog.showOpenDialog({
    title,
    properties: ["openFile"],
    filters: [
      { name: "Unity3D AssetBundle", extensions: ["unity3d"] }
    ]
  });
  return result.canceled ? "" : result.filePaths[0];
});

ipcMain.handle("dialog:saveUnity3dFile", async (_event, title, defaultName) => {
  const rawName = String(defaultName || "export.unity3d").trim();
  const safeName = rawName
    .replace(/[<>:"/\\|?*\u0000-\u001f]/g, "_")
    .replace(/[. ]+$/g, "") || "export.unity3d";
  const suggestedName = safeName.toLowerCase().endsWith(".unity3d") ? safeName : `${safeName}.unity3d`;
  const result = await dialog.showSaveDialog({
    title: title || "导出 Unity3D",
    defaultPath: suggestedName,
    filters: [
      { name: "Unity3D AssetBundle", extensions: ["unity3d"] }
    ]
  });
  if (result.canceled || !result.filePath) return "";
  return result.filePath.toLowerCase().endsWith(".unity3d")
    ? result.filePath
    : `${result.filePath}.unity3d`;
});

ipcMain.handle("dialog:selectImageFile", async (_event, title, defaultPath) => {
  const resolvedDefaultPath = defaultPath ? path.resolve(String(defaultPath)) : undefined;
  const result = await dialog.showOpenDialog({
    title,
    defaultPath: resolvedDefaultPath
      && fs.existsSync(resolvedDefaultPath)
      && fs.statSync(resolvedDefaultPath).isDirectory()
      ? resolvedDefaultPath
      : undefined,
    properties: ["openFile"],
    filters: [
      { name: "Images", extensions: ["png", "jpg", "jpeg", "webp"] }
    ]
  });
  return result.canceled ? "" : result.filePaths[0];
});

ipcMain.handle("dialog:selectWallpaperFile", async (_event, title, defaultPath) => {
  const resolvedDefaultPath = defaultPath ? path.resolve(String(defaultPath)) : undefined;
  const result = await dialog.showOpenDialog({
    title: title || "选择应用壁纸",
    defaultPath: resolvedDefaultPath
      && fs.existsSync(resolvedDefaultPath)
      && fs.statSync(resolvedDefaultPath).isDirectory()
      ? resolvedDefaultPath
      : undefined,
    properties: ["openFile"],
    filters: [
      { name: "图片与视频", extensions: ["png", "jpg", "jpeg", "webp", "gif", "mp4"] },
      { name: "图片", extensions: ["png", "jpg", "jpeg", "webp", "gif"] },
      { name: "MP4 视频", extensions: ["mp4"] }
    ]
  });
  if (result.canceled || !result.filePaths[0]) return null;
  const filePath = result.filePaths[0];
  const extension = path.extname(filePath).toLowerCase();
  return {
    path: filePath,
    type: extension === ".mp4" ? "video" : "image"
  };
});

ipcMain.handle("wallpaper:readImage", async (_event, filePath) => {
  const target = path.resolve(String(filePath || ""));
  const extension = path.extname(target).toLowerCase();
  const mimeTypes = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif"
  };
  const mimeType = mimeTypes[extension];
  if (!mimeType) return { ok: false, error: "仅支持图片壁纸预览。" };
  try {
    const stat = await fs.promises.stat(target);
    if (!stat.isFile()) return { ok: false, error: "壁纸路径不是文件。" };
    if (stat.size > 100 * 1024 * 1024) return { ok: false, error: "图片壁纸不能超过 100 MB。" };
    const data = await fs.promises.readFile(target);
    return { ok: true, dataUrl: `data:${mimeType};base64,${data.toString("base64")}` };
  } catch (error) {
    return { ok: false, error: error.message };
  }
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
    if (stat.size > 50 * 1024 * 1024) return { ok: false, error: "图片不能超过 50 MB。" };
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

ipcMain.handle("dialog:selectWorkbenchFbx", async (_event, payload = {}) => {
  try {
    const { projectPath } = validateWorkbenchProject(payload);
    const result = await dialog.showOpenDialog({
      title: "选择要去除骨骼的 FBX",
      defaultPath: projectPath,
      properties: ["openFile"],
      filters: [{ name: "FBX Model", extensions: ["fbx"] }]
    });
    if (result.canceled || !result.filePaths[0]) return { ok: true, canceled: true };
    const sourcePath = validateWorkbenchFbxFile(projectPath, result.filePaths[0]);
    return {
      ok: true,
      canceled: false,
      path: sourcePath,
      name: path.basename(sourcePath),
      relativePath: workbenchRelativePath(projectPath, sourcePath)
    };
  } catch (error) {
    return { ok: false, error: error.message };
  }
});

ipcMain.handle("dialog:selectFbxReference", async (_event, payload = {}) => {
  try {
    const defaultPath = path.resolve(String(payload.defaultPath || ""));
    const result = await dialog.showOpenDialog({
      title: String(payload.title || "选择 FBX 骨架来源"),
      defaultPath: fs.existsSync(defaultPath) && fs.statSync(defaultPath).isDirectory()
        ? defaultPath
        : undefined,
      properties: ["openFile"],
      filters: [{ name: "FBX Model", extensions: ["fbx"] }]
    });
    if (result.canceled || !result.filePaths[0]) return { ok: true, canceled: true };
    const referencePath = path.resolve(result.filePaths[0]);
    if (
      !fs.existsSync(referencePath)
      || !fs.statSync(referencePath).isFile()
      || path.extname(referencePath).toLowerCase() !== ".fbx"
    ) {
      throw new Error("请选择有效的 .fbx 骨架来源文件");
    }
    return { ok: true, canceled: false, path: referencePath, name: path.basename(referencePath) };
  } catch (error) {
    return { ok: false, error: error.message };
  }
});

ipcMain.handle("dialog:selectSb3UtilityExecutable", async (_event, title) => {
  const result = await dialog.showOpenDialog({
    title,
    properties: ["openFile"],
    filters: [
      { name: "SB3Utility Executable", extensions: ["exe"] }
    ]
  });
  if (result.canceled || !result.filePaths[0]) {
    return "";
  }
  const selectedPath = result.filePaths[0];
  const saved = saveSettingsFile({ sb3utilityExecutablePath: selectedPath });
  if (!saved.ok) {
    console.error(`[settings] failed to persist SB3Utility path: ${saved.error || "unknown error"}`);
  }
  return selectedPath;
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

ipcMain.handle("workbench:createProject", async (_event, payload = {}) => createWorkbenchProject(payload));
ipcMain.handle("workbench:deleteProject", async (_event, payload = {}) => deleteWorkbenchProject(payload));
ipcMain.handle("sims4:deleteResultDirectory", async (_event, directoryPath) => deleteSims4ResultDirectory(directoryPath));
ipcMain.handle("workbench:scanProjects", async (_event, workspacePath) => scanWorkbenchProjects(workspacePath));
ipcMain.handle("workbench:scanItems", async (_event, payload = {}) => scanWorkbenchItems(payload));
ipcMain.handle("workbench:scanAssetFiles", async (_event, payload = {}) => scanWorkbenchAssetFiles(payload));
ipcMain.handle("workbench:loadAssetPreview", async (_event, payload = {}) => loadWorkbenchAssetPreview(payload));
ipcMain.handle("workbench:loadThumbnail", async (_event, payload = {}) => loadWorkbenchThumbnail(payload));
ipcMain.handle("workbench:saveThumbnail", async (_event, payload = {}) => saveWorkbenchThumbnail(payload));
ipcMain.handle("workbench:createItem", async (_event, payload = {}) => createWorkbenchItem(payload));
ipcMain.handle("workbench:deleteItem", async (_event, payload = {}) => deleteWorkbenchItem(payload));
ipcMain.handle("workbench:scanUnity3d", async (_event, payload = {}) => scanWorkbenchUnity3d(payload));
ipcMain.handle("workbench:validateMainResource", async (_event, payload = {}) => validateWorkbenchMainResource(payload));
ipcMain.handle("workbench:previewItem", async (_event, payload = {}) => {
  try {
    const { projectPath } = validateWorkbenchProject(payload);
    const resource = resolveWorkbenchExistingResource(projectPath, payload.mainAB);
    const mainData = String(payload.mainData || "").trim();
    if (!mainData) throw new Error("MainData 不能为空");
    return await fetchBackend("/workbench/unity3d/model-preview", {
      method: "POST",
      body: {
        unity3d_path: resource.path,
        main_data: mainData,
        kind: String(payload.kind || "").trim()
      }
    });
  } catch (error) {
    return { ok: false, error: error.message };
  }
});
ipcMain.handle("workbench:openMainResourceInSb3Utility", async (_event, payload = {}) => {
  try {
    const { projectPath } = validateWorkbenchProject(payload);
    const resource = resolveWorkbenchExistingResource(projectPath, payload.mainAB);
    return launchUnity3dInSb3Utility(resource.path);
  } catch (error) {
    return { ok: false, error: error.message };
  }
});
ipcMain.handle("workbench:openAssetInSb3Utility", async (_event, payload = {}) => {
  try {
    const { projectPath } = validateWorkbenchProject(payload);
    const relativePath = String(payload.relativePath || "").trim().replaceAll("\\", "/");
    const assetPath = path.resolve(projectPath, relativePath);
    const allowedExtensions = new Set([
      ...WORKBENCH_ASSET_TEXTURE_EXTENSIONS,
      ...WORKBENCH_ASSET_MODEL_EXTENSIONS
    ]);
    if (
      !relativePath
      || path.isAbsolute(relativePath)
      || !isPathInside(projectPath, assetPath)
      || !allowedExtensions.has(path.extname(assetPath).toLowerCase())
    ) {
      throw new Error("请选择当前项目目录内的图片或 FBX 文件");
    }
    return launchFileInSb3Utility(assetPath, allowedExtensions, "图片或 FBX 文件不存在");
  } catch (error) {
    return { ok: false, error: error.message };
  }
});
ipcMain.handle("workbench:importTexture", async (_event, payload = {}) => {
  try {
    const { projectPath } = validateWorkbenchProject(payload);
    const resource = resolveWorkbenchExistingResource(projectPath, payload.mainAB);
    const imagePath = validateWorkbenchImageFile(payload.sourcePath);
    const textureName = String(payload.textureName || "").trim();
    const replaceExisting = payload.replaceExisting === true;
    // UnityPy-created Unity3D files can contain valid serialized resources
    // that SB3Utility rejects while recomputing an Animator Avatar. Use the
    // UnityPy writer for texture mutations so this operation never reopens
    // the file through SB3Utility.
    const unityPyResult = await fetchBackend("/workbench/unity3d/import-texture", {
      method: "POST",
      body: {
        path: resource.path,
        image_path: imagePath,
        texture_name: textureName,
        replace_existing: replaceExisting
      }
    });
    if (!unityPyResult?.ok) {
      throw new Error(unityPyResult?.error || (replaceExisting ? "Texture replacement failed" : "Texture import failed"));
    }
    const unityPyVerification = await fetchBackend("/workbench/unity3d/assets", {
      method: "POST",
      body: { path: resource.path }
    });
    if (!unityPyVerification?.ok) {
      throw new Error(unityPyVerification?.error || "The Unity3D file could not be read after the texture write");
    }
    if (!findWorkbenchUnityCandidate(unityPyVerification.texture_candidates, textureName)) {
      throw new Error(`Texture write verification failed: ${textureName}`);
    }
    return {
      ok: true,
      path: resource.path,
      texture_name: textureName,
      replaced: replaceExisting
    };

    /*

    if (!textureName) throw new Error("贴图资源名不能为空");
    const assets = await fetchBackend("/workbench/unity3d/assets", {
      method: "POST",
      body: { path: resource.path }
    });
    if (!assets?.ok) throw new Error(assets?.error || "无法读取 Unity3D 资源");

    const resolvedTextureTarget = resolveTextureAnimatorComponent(assets, {
      textureName,
      mainData,
      componentIndex: payload.componentIndex
    });
    const { matchingTexture, componentIndex } = resolvedTextureTarget;
    if (replaceExisting && !matchingTexture) {
      throw new Error(`Unity3D 中未找到要替换的贴图：${textureName}`);
    }
    if (!Number.isInteger(componentIndex) || componentIndex < 0) {
      throw new Error("无法定位 MainData 对应的 Animator，不能安全写入贴图");
    }

    const outputPath = path.join(app.getPath("temp"), "star-manager-sb3utility", `texture-${crypto.randomUUID()}.unity3d`);
    await runWorkbenchSb3Mutation({
      sourcePath: resource.path,
      outputPath,
      operation: replaceExisting ? "replace_texture" : "import_texture",
      imagePath,
      textureName,
      replaceExisting,
      componentIndex
    });
    const verification = await fetchBackend("/workbench/unity3d/assets", {
      method: "POST",
      body: { path: outputPath }
    });
    if (!verification?.ok) {
      fs.rmSync(outputPath, { force: true });
      throw new Error(verification?.error || "贴图写入后的 Unity3D 无法重新读取");
    }
    if (!findWorkbenchUnityCandidate(verification.texture_candidates, textureName)) {
      fs.rmSync(outputPath, { force: true });
      throw new Error(`贴图写入验证失败：${textureName}`);
    }
    const replacementPath = path.join(path.dirname(resource.path), `.${path.basename(resource.path)}-${crypto.randomUUID()}.tmp`);
    try {
      fs.copyFileSync(outputPath, replacementPath);
      fs.copyFileSync(replacementPath, resource.path);
    } finally {
      fs.rmSync(replacementPath, { force: true });
      fs.rmSync(outputPath, { force: true });
    }
    return { ok: true, path: resource.path, texture_name: textureName, replaced: replaceExisting };
    */
  } catch (error) {
    return { ok: false, error: error.message };
  }
});
ipcMain.handle("workbench:exportProcessedTexture", async (_event, payload = {}) => {
  try {
    const { projectPath } = validateWorkbenchProject(payload);
    const dataUrl = String(payload.dataUrl || "");
    const match = /^data:image\/png;base64,([A-Za-z0-9+/=]+)$/.exec(dataUrl);
    if (!match) throw new Error("输出数据不是有效的 PNG");
    const imageData = Buffer.from(match[1], "base64");
    if (imageData.length < 8 || imageData.length > 128 * 1024 * 1024) {
      throw new Error("PNG 数据为空或超过 128 MB");
    }
    if (!imageData.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]))) {
      throw new Error("PNG 文件头校验失败");
    }
    const rawName = String(payload.suggestedName || "texture.png").trim();
    const safeName = (rawName || "texture.png")
      .replace(/[<>:"/\\|?*\u0000-\u001f]/g, "_")
      .replace(/[. ]+$/g, "") || "texture.png";
    const suggestedName = safeName.toLowerCase().endsWith(".png") ? safeName : `${safeName}.png`;
    const result = await dialog.showSaveDialog({
      title: "导出 SB3Utility PNG 贴图",
      defaultPath: path.join(projectPath, suggestedName),
      filters: [{ name: "PNG Texture", extensions: ["png"] }]
    });
    if (result.canceled || !result.filePath) return { ok: true, canceled: true };
    const outputPath = result.filePath.toLowerCase().endsWith(".png")
      ? result.filePath
      : `${result.filePath}.png`;
    await fs.promises.writeFile(outputPath, imageData);
    return {
      ok: true,
      canceled: false,
      path: outputPath,
      width: Number(payload.width || 0),
      height: Number(payload.height || 0),
      bytes: imageData.length
    };
  } catch (error) {
    return { ok: false, error: error.message };
  }
});
ipcMain.handle("workbench:preprocessTemplate", async (_event, payload = {}) => {
  let temporaryOutputPath = "";
  let preserveTemporaryOutput = false;
  try {
    const writeBack = payload.writeBack === true;
    let sourcePath = path.resolve(String(payload.sourcePath || ""));
    let resource = null;
    if (writeBack) {
      const validated = validateWorkbenchProject(payload);
      resource = resolveWorkbenchExistingResource(validated.projectPath, payload.mainAB);
      sourcePath = resource.path;
    }
    const operation = String(payload.operation || "").trim().toLowerCase();
    temporaryOutputPath = path.join(app.getPath("temp"), "star-manager-sb3utility", `preprocess-${crypto.randomUUID()}.unity3d`);
    const selectedName = String(payload.selectedName || "").trim();
    const nextName = String(payload.newName || "").trim();
    if (["duplicate_and_rename_selected", "rename_selected"].includes(operation) && !nextName) throw new Error("请输入新的对象名称");
    const mutationPayload = {
      sourcePath,
      operation,
      outputPath: temporaryOutputPath,
      selectedName,
      selectedPathId: Number(payload.selectedPathId ?? 0),
      selectedAssetFile: String(payload.selectedAssetFile || ""),
      componentIndex: Number(payload.componentIndex ?? -1)
    };
    let mutationResult;
    let mutationOutputPath = temporaryOutputPath;
    if (operation === "duplicate_and_rename_selected" || operation === "duplicate_selected") {
      mutationResult = await runWorkbenchSb3DuplicateAndRename({
        ...mutationPayload,
        newName: operation === "duplicate_and_rename_selected" ? nextName : ""
      });
    } else if (operation === "keep_selected") {
      // Removing other objects can span several independent Animator roots.
      // AnimatorEditor only sees the currently opened Animator, so delegate
      // this whole-file operation to the backend graph remover.
      mutationResult = await runWorkbenchPythonPreprocess(mutationPayload);
      mutationOutputPath = mutationResult.path;
    } else {
      mutationResult = await runWorkbenchSb3Mutation({
        ...mutationPayload,
        operation,
        textureName: operation === "rename_selected" ? nextName : ""
      });
    }
    const candidates = await fetchBackend("/workbench/unity3d/assets", {
      method: "POST",
      body: { path: mutationOutputPath }
    });
    if (!candidates?.ok) throw new Error(candidates?.error || "无法重新读取 SB3Utility 输出");
    if (writeBack) {
      const replacementPath = path.join(path.dirname(resource.path), `.${path.basename(resource.path)}-${crypto.randomUUID()}.tmp`);
      try {
        fs.copyFileSync(mutationOutputPath, replacementPath);
        fs.copyFileSync(replacementPath, resource.path);
      } finally {
        fs.rmSync(replacementPath, { force: true });
      }
    }
    const result = {
      ...candidates,
      path: writeBack ? resource.path : mutationOutputPath,
      operation,
      main_data: mutationResult?.main_data
        || (operation === "duplicate_and_rename_selected" || operation === "rename_selected"
          ? nextName
          : (candidates.default || selectedName)),
      selected_path_id: Number(mutationResult?.selected_path_id || 0),
      selected_asset_file: String(mutationResult?.selected_asset_file || "")
    };
    preserveTemporaryOutput = !writeBack;
    return result;
  } catch (error) {
    return { ok: false, error: `Unity3D 预处理失败：${error.message}` };
  } finally {
    if (temporaryOutputPath && !preserveTemporaryOutput) fs.rmSync(temporaryOutputPath, { force: true });
  }
});
ipcMain.handle("workbench:updateItemResourceFields", async (_event, payload = {}) => updateWorkbenchItemResourceFields(payload));
ipcMain.handle("workbench:applyMainResource", async (_event, payload = {}) => applyWorkbenchMainResource(payload));
ipcMain.handle("workbench:transformFbx", async (_event, payload = {}) => {
  try {
    const { projectPath } = validateWorkbenchProject(payload);
    const sourcePath = validateWorkbenchFbxFile(projectPath, payload.sourcePath);
    const blenderPath = path.resolve(String(payload.blenderPath || ""));
    const blenderName = path.basename(blenderPath).toLowerCase();
    if (
      !fs.existsSync(blenderPath)
      || !fs.statSync(blenderPath).isFile()
      || !blenderName.startsWith("blender")
      || path.extname(blenderPath).toLowerCase() !== ".exe"
    ) {
      throw new Error("Blender executable not found，请先在设置中配置 Blender");
    }
    const scriptPath = resolveWorkbenchFbxTransformScript();
    if (!scriptPath) throw new Error("FBX 变换脚本未找到，请重启应用或重新安装");
    const backupOriginal = payload.backupOriginal === true;
    const backupPath = backupOriginal ? nextWorkbenchFbxBackupPath(sourcePath) : "";
    if (backupPath) fs.copyFileSync(sourcePath, backupPath);
    const outputPath = backupOriginal ? nextWorkbenchFbxTransformOutput(sourcePath) : sourcePath;
    const report = await runWorkbenchFbxTransformScript(
      blenderPath,
      scriptPath,
      sourcePath,
      outputPath
    );
    return {
      ok: true,
      input: sourcePath,
      inputRelativePath: workbenchRelativePath(projectPath, sourcePath),
      output: outputPath,
      outputRelativePath: workbenchRelativePath(projectPath, outputPath),
      overwroteInput: outputPath === sourcePath,
      backup: backupPath || null,
      backupRelativePath: backupPath ? workbenchRelativePath(projectPath, backupPath) : "",
      objectCount: Number(report.object_count || 0),
      changedObjectCount: Number(report.changed_object_count || 0),
      meshCount: Number(report.mesh_count || 0),
      armatureCount: Number(report.armature_count || 0),
      alignmentIssueDetected: report.alignment_issue_detected === true,
      alignmentRepairApplied: report.alignment_repair_applied === true,
      translationIssueCount: Number(report.translation_issue_count || 0),
      translationRepairedCount: Number(report.translation_repaired_count || 0),
      translationRepairedMeshNames: Array.isArray(report.translation_repaired_mesh_names)
        ? report.translation_repaired_mesh_names.map((name) => String(name || "").trim()).filter(Boolean)
        : []
    };
  } catch (error) {
    return { ok: false, error: error.message };
  }
});
ipcMain.handle("workbench:removeFbxSkin", async (_event, payload = {}) => {
  try {
    const { projectPath } = validateWorkbenchProject(payload);
    const sourcePath = validateWorkbenchFbxFile(projectPath, payload.sourcePath);
    const blenderPath = path.resolve(String(payload.blenderPath || ""));
    const blenderName = path.basename(blenderPath).toLowerCase();
    if (
      !fs.existsSync(blenderPath)
      || !fs.statSync(blenderPath).isFile()
      || !blenderName.startsWith("blender")
      || path.extname(blenderPath).toLowerCase() !== ".exe"
    ) {
      throw new Error("Blender executable not found，请先在设置中配置 Blender");
    }
    const scriptPath = resolveWorkbenchFbxSkinScript();
    if (!scriptPath) throw new Error("FBX 处理脚本未找到，请重启应用或重新安装");
    const backupOriginal = payload.backupOriginal === true;
    const backupPath = backupOriginal ? nextWorkbenchFbxBackupPath(sourcePath) : "";
    if (backupPath) fs.copyFileSync(sourcePath, backupPath);
    const outputPath = backupOriginal ? nextWorkbenchFbxSkinOutput(sourcePath) : sourcePath;
    const report = await runWorkbenchFbxSkinScript(blenderPath, scriptPath, sourcePath, outputPath);
    return {
      ok: true,
      input: sourcePath,
      inputRelativePath: workbenchRelativePath(projectPath, sourcePath),
      output: outputPath,
      outputRelativePath: workbenchRelativePath(projectPath, outputPath),
      overwroteInput: outputPath === sourcePath,
      backup: backupPath || null,
      backupRelativePath: backupPath ? workbenchRelativePath(projectPath, backupPath) : "",
      meshCount: Number(report.mesh_count || 0),
      removedArmatureModifiers: Number(report.removed_armature_modifiers || 0),
      removedVertexGroups: Number(report.removed_vertex_groups || 0)
    };
  } catch (error) {
    return { ok: false, error: error.message };
  }
});
ipcMain.handle("workbench:bindHs2Skeleton", async (_event, payload = {}) => {
  try {
    const { projectPath } = validateWorkbenchProject(payload);
    const sourcePath = validateWorkbenchFbxFile(projectPath, payload.sourcePath);
    const skeletonPath = path.resolve(String(payload.skeletonPath || ""));
    if (
      !fs.existsSync(skeletonPath)
      || !fs.statSync(skeletonPath).isFile()
      || path.extname(skeletonPath).toLowerCase() !== ".fbx"
    ) {
      throw new Error("HS2 骨架来源必须是有效的 .fbx 文件");
    }
    if (sourcePath.toLowerCase() === skeletonPath.toLowerCase()) {
      throw new Error("Mesh FBX 和骨架来源不能是同一个文件");
    }
    const blenderPath = path.resolve(String(payload.blenderPath || ""));
    const blenderName = path.basename(blenderPath).toLowerCase();
    if (
      !fs.existsSync(blenderPath)
      || !fs.statSync(blenderPath).isFile()
      || !blenderName.startsWith("blender")
      || path.extname(blenderPath).toLowerCase() !== ".exe"
    ) {
      throw new Error("Blender executable not found，请先在设置中配置 Blender");
    }
    const scriptPath = resolveWorkbenchFbxSkeletonScript();
    if (!scriptPath) throw new Error("HS2 骨架绑定脚本未找到，请重启应用或重新安装");
    const backupOriginal = payload.backupOriginal === true;
    const backupPath = backupOriginal ? nextWorkbenchFbxBackupPath(sourcePath) : "";
    if (backupPath) fs.copyFileSync(sourcePath, backupPath);
    const outputPath = backupOriginal ? nextWorkbenchFbxSkeletonOutput(sourcePath) : sourcePath;
    const report = await runWorkbenchFbxSkeletonScript(
      blenderPath,
      scriptPath,
      sourcePath,
      skeletonPath,
      outputPath
    );
    return {
      ok: true,
      input: sourcePath,
      inputRelativePath: workbenchRelativePath(projectPath, sourcePath),
      skeleton: skeletonPath,
      output: outputPath,
      outputRelativePath: workbenchRelativePath(projectPath, outputPath),
      overwroteInput: outputPath === sourcePath,
      backup: backupPath || null,
      backupRelativePath: backupPath ? workbenchRelativePath(projectPath, backupPath) : "",
      meshCount: Number(report.mesh_count || 0),
      armatureCount: Number(report.armature_count || 0),
      boneCount: Number(report.bone_count || 0),
      armatureModifiers: Number(report.armature_modifiers || 0),
      vertexGroups: Number(report.vertex_groups || 0),
      skinned: report.skinned === true
    };
  } catch (error) {
    return { ok: false, error: error.message };
  }
});
ipcMain.handle("workbench:transferFbxWeights", async (_event, payload = {}) => {
  try {
    const { projectPath } = validateWorkbenchProject(payload);
    const targetPath = validateWorkbenchFbxFile(projectPath, payload.targetPath);
    const sourcePath = path.resolve(String(payload.sourcePath || ""));
    if (
      !fs.existsSync(sourcePath)
      || !fs.statSync(sourcePath).isFile()
      || path.extname(sourcePath).toLowerCase() !== ".fbx"
    ) {
      throw new Error("权重来源必须是有效的 .fbx 文件");
    }
    if (sourcePath.toLowerCase() === targetPath.toLowerCase()) {
      throw new Error("权重来源和目标 FBX 不能是同一个文件");
    }
    const blenderPath = path.resolve(String(payload.blenderPath || ""));
    const blenderName = path.basename(blenderPath).toLowerCase();
    if (
      !fs.existsSync(blenderPath)
      || !fs.statSync(blenderPath).isFile()
      || !blenderName.startsWith("blender")
      || path.extname(blenderPath).toLowerCase() !== ".exe"
    ) {
      throw new Error("Blender executable not found，请先在设置中配置 Blender");
    }
    const scriptPath = resolveWorkbenchFbxWeightsScript();
    if (!scriptPath) throw new Error("FBX 权重转移脚本未找到，请重启应用或重新安装");
    const backupOriginal = payload.backupOriginal === true;
    const backupPath = backupOriginal ? nextWorkbenchFbxBackupPath(targetPath) : "";
    if (backupPath) fs.copyFileSync(targetPath, backupPath);
    const outputPath = backupOriginal ? nextWorkbenchFbxWeightsOutput(targetPath) : targetPath;
    const report = await runWorkbenchFbxWeightsScript(
      blenderPath,
      scriptPath,
      sourcePath,
      targetPath,
      outputPath
    );
    return {
      ok: true,
      source: sourcePath,
      target: targetPath,
      targetRelativePath: workbenchRelativePath(projectPath, targetPath),
      output: outputPath,
      outputRelativePath: workbenchRelativePath(projectPath, outputPath),
      overwroteInput: outputPath === targetPath,
      backup: backupPath || null,
      backupRelativePath: backupPath ? workbenchRelativePath(projectPath, backupPath) : "",
      meshCount: Number(report.mesh_count || 0),
      boneCount: Number(report.bone_count || 0),
      mappedGroupCount: Number(report.mapped_group_count || 0),
      weightedVertexCount: Number(report.weighted_vertex_count || 0),
      averageNearestDistance: Number(report.average_nearest_distance || 0),
      armatureModifiers: Number(report.armature_modifiers || 0)
    };
  } catch (error) {
    return { ok: false, error: error.message };
  }
});

function packageWorkbenchModInWorker(payload, onProgress) {
  return new Promise((resolve) => {
    let settled = false;
    const worker = new Worker(path.join(__dirname, "workbench-packager-worker.cjs"), {
      workerData: payload
    });
    const finish = (result) => {
      if (settled) return;
      settled = true;
      resolve(result);
    };

    worker.on("message", (message) => {
      if (message?.type === "progress") {
        onProgress?.(message.progress);
        return;
      }
      finish(message?.type === "result" ? message.result : message);
    });
    worker.once("error", (error) => {
      finish({ ok: false, error: error?.message || String(error) });
    });
    worker.once("exit", (code) => {
      if (!settled) {
        finish({
          ok: false,
          error: code === 0 ? "模组打包未返回结果" : `模组打包进程异常退出（${code}）`
        });
      }
    });
  });
}

async function findWorkbenchOldZipmodsByGuid(guid, gameDir) {
  const query = `?guid=${encodeURIComponent(String(guid || ""))}&game_dir=${encodeURIComponent(String(gameDir || ""))}`;
  const result = await fetchBackend(`/mods/zipmods/by-guid${query}`);
  if (!result?.ok || !Array.isArray(result.paths)) return [];
  return result.paths.map((filePath) => String(filePath || "").trim()).filter(Boolean);
}

async function indexWorkbenchModDatabase(gameDir, zipmodPath, onProgress) {
  const normalizedGameDir = path.resolve(String(gameDir || ""));
  const normalizedZipmodPath = path.resolve(String(zipmodPath || ""));
  const submitted = await fetchBackend("/tasks", {
    method: "POST",
    body: {
      task_type: "index_single_zipmod",
      payload: {
        game_dir: normalizedGameDir,
        zipmod_path: normalizedZipmodPath
      }
    }
  });
  if (!submitted?.ok || !submitted.task?.id) {
    return {
      ok: false,
      error: submitted?.error || "模组已打包，但无法提交单个模组数据库任务"
    };
  }

  const taskId = String(submitted.task.id);
  onProgress?.({
    stage: "database",
    current: 0,
    total: 100,
    message: "正在将当前模组同步到数据库（不扫描其它模组）"
  });

  for (;;) {
    const polled = await fetchBackend(`/tasks/${encodeURIComponent(taskId)}`);
    if (!polled?.ok || !polled.task) {
      return {
        ok: false,
        error: polled?.error || "无法读取单个模组数据库任务状态"
      };
    }

    const task = polled.task;
    const progress = Math.max(0, Math.min(100, Number(task.progress || 0)));
    const messages = Array.isArray(task.messages) ? task.messages : [];
    onProgress?.({
      stage: "database",
      current: Math.round(progress),
      total: 100,
      message: String(messages[messages.length - 1] || "正在更新当前模组数据库")
    });

    if (task.status === "completed") {
      onProgress?.({
        stage: "database",
        current: 100,
        total: 100,
        message: "当前模组数据库同步完成"
      });
      return { ok: true, task };
    }
    if (task.status === "failed") {
      return {
        ok: false,
        error: task.error || "模组已打包，但当前模组数据库同步失败",
        task
      };
    }

    await sleep(350);
  }
}

ipcMain.handle("workbench:packageMod", async (event, payload = {}) => {
  try {
    const { projectPath, project } = validateWorkbenchProject(payload);
    event.sender.send("workbench:packageProgress", {
      stage: "scanning",
      message: "正在使用模组数据库定位旧版本"
    });
    const oldZipmodPaths = await findWorkbenchOldZipmodsByGuid(project.guid, payload.gameDir);
    const packageResult = await packageWorkbenchModInWorker(
      {
        projectPath,
        gameDir: payload.gameDir,
        project,
        oldZipmodPaths
      },
      (progress) => event.sender.send("workbench:packageProgress", progress)
    );
    if (!packageResult?.ok) return packageResult;

    const databaseResult = await indexWorkbenchModDatabase(
      packageResult.gameDir || payload.gameDir,
      packageResult.zipmodPath,
      (progress) => event.sender.send("workbench:packageProgress", progress)
    );
    return {
      ...packageResult,
      databaseUpdated: databaseResult.ok,
      databaseError: databaseResult.ok ? "" : databaseResult.error,
      databaseTask: databaseResult.task || null
    };
  } catch (error) {
    return { ok: false, error: error.message };
  }
});

ipcMain.handle("settings:load", async () => {
  return loadSettingsFile();
});

ipcMain.on("settings:getStartupWallpaper", (event) => {
  try {
    event.returnValue = getStartupWallpaperSettings();
  } catch (error) {
    console.warn(`[settings] failed to load startup wallpaper: ${error.message}`);
    event.returnValue = { wallpaperPath: "", wallpaperType: "" };
  }
});

ipcMain.on("renderer:ready", (event) => {
  const window = BrowserWindow.fromWebContents(event.sender);
  const readiness = window ? windowReadiness.get(window) : null;
  if (!window || !readiness || window.isDestroyed()) return;
  readiness.rendererReady = true;
  readiness.logPageLoadStep?.("renderer-ready", "renderer");
  readiness.revealWindow?.("renderer-ready");
});

ipcMain.handle("settings:save", async (_event, settings) => {
  return saveSettingsFile(settings);
});

ipcMain.handle("game:loadSetup", async (_event, gameDir) => {
  try {
    const rawGameDir = String(gameDir || "").trim();
    if (!rawGameDir) return { ok: false, error: "Game directory not found" };
    const normalizedGameDir = path.resolve(rawGameDir);
    if (!fs.existsSync(normalizedGameDir) || !fs.statSync(normalizedGameDir).isDirectory()) {
      return { ok: false, error: "Game directory not found" };
    }
    return { ok: true, ...getGameSetupPayload(normalizedGameDir) };
  } catch (error) {
    return { ok: false, error: `读取 setup.xml 失败：${error.message}` };
  }
});

ipcMain.handle("game:saveSetup", async (_event, gameDir, setup) => {
  try {
    const rawGameDir = String(gameDir || "").trim();
    if (!rawGameDir) return { ok: false, error: "Game directory not found" };
    const normalizedGameDir = path.resolve(rawGameDir);
    if (!fs.existsSync(normalizedGameDir) || !fs.statSync(normalizedGameDir).isDirectory()) {
      return { ok: false, error: "Game directory not found" };
    }

    const saved = writeGameSetup(normalizedGameDir, setup);
    const normalizedSetup = normalizeSetup(saved.setup);
    const registry = await syncUnityRegistry(normalizedGameDir, normalizedSetup);
    const displays = getGameSetupDisplays(normalizedSetup);
    return {
      ok: true,
      ...saved,
      setup: normalizedSetup,
      displays,
      resolutions: getGameSetupResolutions(normalizedSetup, displays),
      registry
    };
  } catch (error) {
    return { ok: false, error: `保存 setup.xml 失败：${error.message}` };
  }
});

ipcMain.handle("shell:showItemInFolder", async (_event, filePath) => {
  if (!filePath || !fs.existsSync(filePath)) {
    return { ok: false, error: "File not found" };
  }
  shell.showItemInFolder(filePath);
  return { ok: true };
});

function launchUnity3dInSb3Utility(unity3dPath) {
  return launchFileInSb3Utility(unity3dPath, new Set([".unity3d"]), "Unity3D file not found", "unity3d");
}

function launchFileInSb3Utility(filePath, allowedExtensions, missingError, resultKey = "filePath") {
  if (process.platform !== "win32") {
    return { ok: false, error: "SB3Utility is only supported on Windows" };
  }

  const savedSettings = loadSettingsFile();
  const configuredExecutablePath = savedSettings.settings?.sb3utilityExecutablePath || DEFAULT_SB3UTILITY_EXECUTABLE_PATH;
  const executablePath = path.resolve(configuredExecutablePath);
  const normalizedFilePath = path.resolve(String(filePath || ""));
  if (
    !fs.existsSync(executablePath)
    || !fs.statSync(executablePath).isFile()
    || path.extname(executablePath).toLowerCase() !== ".exe"
  ) {
    return { ok: false, error: `SB3Utility executable not found: ${executablePath}` };
  }
  if (
    !fs.existsSync(normalizedFilePath)
    || !fs.statSync(normalizedFilePath).isFile()
    || !allowedExtensions.has(path.extname(normalizedFilePath).toLowerCase())
  ) {
    return { ok: false, error: missingError };
  }

  try {
    const child = spawn(executablePath, [normalizedFilePath], {
      cwd: path.dirname(executablePath),
      detached: true,
      stdio: "ignore",
      windowsHide: false
    });
    child.unref();
    return { ok: true, executable: executablePath, [resultKey]: normalizedFilePath };
  } catch (error) {
    return { ok: false, error: error.message };
  }
}

ipcMain.handle("sb3utility:openUnity3d", async (_event, unity3dPath) => {
  return launchUnity3dInSb3Utility(unity3dPath);
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
    const ipaPath = path.join(gameDir, "IPA.exe");
    const hasIpa = fs.existsSync(ipaPath);
    const hasBepInEx = fs.existsSync(path.join(gameDir, "BepInEx", "core"));
    if (hasIpa && hasBepInEx) {
      return {
        ok: false,
        error: "同时检测到 IPA 和 BepInEx，已停止启动以避免框架冲突。"
      };
    }

    const launcherPath = hasIpa ? ipaPath : executablePath;
    const launchArgs = hasIpa ? [executablePath, "--launch"] : [];
    const child = spawn(launcherPath, launchArgs, {
      cwd: gameDir,
      detached: true,
      stdio: "ignore",
      windowsHide: false
    });
    child.unref();
    return {
      ok: true,
      executable: executableName,
      launcher: hasIpa ? "IPA.exe" : executableName,
      mode: hasIpa ? "ipa" : "direct"
    };
  } catch (error) {
    return { ok: false, error: error.message };
  }
});

app.whenReady().then(async () => {
  if (!hasSingleInstanceLock) return;
  const startupStart = process.hrtime.bigint();
  Menu.setApplicationMenu(null);
  logStartupStep("app.whenReady", startupStart, "(menu cleared)");

  protocol.handle("wallpaper", async (request) => {
    try {
      const requestUrl = new URL(request.url);
      const filePath = requestUrl.searchParams.get("path");
      if (!filePath) return new Response("Missing wallpaper path", { status: 400 });
      const target = path.resolve(filePath);
      const stat = await fs.promises.stat(target);
      if (!stat.isFile()) return new Response("Wallpaper is not a file", { status: 404 });
      return electronNet.fetch(pathToFileURL(target).toString());
    } catch (error) {
      console.warn(`[wallpaper] failed to serve media: ${error.message}`);
      return new Response("Wallpaper not found", { status: 404 });
    }
  });

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

app.on("before-quit", (event) => {
  if (!hasSingleInstanceLock || appShutdownStarted) return;
  event.preventDefault();
  appShutdownStarted = true;
  app.isQuitting = true;
  clearModelPreviewCache();
  void shutdownBackend("app is quitting").finally(() => {
    app.quit();
  });
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
  if (process.platform !== "darwin") {
    app.quit();
  }
});
