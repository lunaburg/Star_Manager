const { contextBridge, ipcRenderer } = require("electron");

const pendingStartupLogs = [];
const startupLogListeners = new Set();

ipcRenderer.on("startup:log", (_event, payload) => {
  if (startupLogListeners.size === 0) {
    pendingStartupLogs.push(payload);
    return;
  }
  for (const listener of startupLogListeners) listener(payload);
});

function loadStartupWallpaper() {
  try {
    const result = ipcRenderer.sendSync("settings:getStartupWallpaper");
    return {
      wallpaperPath: String(result?.wallpaperPath || "").trim(),
      wallpaperType: ["image", "video"].includes(String(result?.wallpaperType || ""))
        ? String(result.wallpaperType)
        : ""
    };
  } catch {
    return { wallpaperPath: "", wallpaperType: "" };
  }
}

const startupWallpaper = loadStartupWallpaper();

contextBridge.exposeInMainWorld("desktopApi", {
  startupWallpaper,
  notifyRendererReady: () => ipcRenderer.send("renderer:ready"),
  onStartupLog: (callback) => {
    if (typeof callback !== "function") return () => {};
    startupLogListeners.add(callback);
    while (pendingStartupLogs.length) callback(pendingStartupLogs.shift());
    return () => startupLogListeners.delete(callback);
  },
  selectDirectory: (title) => ipcRenderer.invoke("dialog:selectDirectory", title),
  selectPackageFile: (title) => ipcRenderer.invoke("dialog:selectPackageFile", title),
  selectUnity3dFile: (title) => ipcRenderer.invoke("dialog:selectUnity3dFile", title),
  selectUnity3dExportPath: (title, defaultName) => ipcRenderer.invoke("dialog:saveUnity3dFile", title, defaultName),
  selectImageFile: (title, defaultPath) => ipcRenderer.invoke("dialog:selectImageFile", title, defaultPath),
  selectWallpaperFile: (title, defaultPath) => ipcRenderer.invoke("dialog:selectWallpaperFile", title, defaultPath),
  readWallpaperImage: (filePath) => ipcRenderer.invoke("wallpaper:readImage", filePath),
  selectImageForCrop: (title) => ipcRenderer.invoke("dialog:selectImageForCrop", title),
  selectBlenderExecutable: (title) => ipcRenderer.invoke("dialog:selectBlenderExecutable", title),
  selectWorkbenchFbxFile: (payload) => ipcRenderer.invoke("dialog:selectWorkbenchFbx", payload),
  selectFbxReferenceFile: (payload) => ipcRenderer.invoke("dialog:selectFbxReference", payload),
  selectSb3UtilityExecutable: (title) => ipcRenderer.invoke("dialog:selectSb3UtilityExecutable", title),
  promptText: (title, message, defaultValue) => ipcRenderer.invoke("dialog:promptText", title, message, defaultValue),
  showItemInFolder: (filePath) => ipcRenderer.invoke("shell:showItemInFolder", filePath),
  openUnity3dInSb3Utility: (filePath) => ipcRenderer.invoke("sb3utility:openUnity3d", filePath),
  openWorkbenchAssetInSb3Utility: (payload) => ipcRenderer.invoke("workbench:openAssetInSb3Utility", payload),
  openDirectory: (directoryPath) => ipcRenderer.invoke("shell:openDirectory", directoryPath),
  openRepository: () => ipcRenderer.invoke("shell:openRepository"),
  deleteSims4ResultDirectory: (directoryPath) => ipcRenderer.invoke("sims4:deleteResultDirectory", directoryPath),
  createWorkbenchProject: (payload) => ipcRenderer.invoke("workbench:createProject", payload),
  deleteWorkbenchProject: (payload) => ipcRenderer.invoke("workbench:deleteProject", payload),
  scanWorkbenchProjects: (payload) => ipcRenderer.invoke("workbench:scanProjects", payload),
  scanWorkbenchItems: (payload) => ipcRenderer.invoke("workbench:scanItems", payload),
  scanWorkbenchAssetFiles: (payload) => ipcRenderer.invoke("workbench:scanAssetFiles", payload),
  loadWorkbenchAssetPreview: (payload) => ipcRenderer.invoke("workbench:loadAssetPreview", payload),
  loadWorkbenchThumbnail: (payload) => ipcRenderer.invoke("workbench:loadThumbnail", payload),
  saveWorkbenchThumbnail: (payload) => ipcRenderer.invoke("workbench:saveThumbnail", payload),
  createWorkbenchItem: (payload) => ipcRenderer.invoke("workbench:createItem", payload),
  deleteWorkbenchItem: (payload) => ipcRenderer.invoke("workbench:deleteItem", payload),
  scanWorkbenchUnity3d: (payload) => ipcRenderer.invoke("workbench:scanUnity3d", payload),
  validateWorkbenchMainResource: (payload) => ipcRenderer.invoke("workbench:validateMainResource", payload),
  previewWorkbenchItem: (payload) => ipcRenderer.invoke("workbench:previewItem", payload),
  openWorkbenchMainResourceInSb3Utility: (payload) => ipcRenderer.invoke("workbench:openMainResourceInSb3Utility", payload),
  importWorkbenchTexture: (payload) => ipcRenderer.invoke("workbench:importTexture", payload),
  exportWorkbenchProcessedTexture: (payload) => ipcRenderer.invoke("workbench:exportProcessedTexture", payload),
  preprocessWorkbenchTemplate: (payload) => ipcRenderer.invoke("workbench:preprocessTemplate", payload),
  updateWorkbenchItemResourceFields: (payload) => ipcRenderer.invoke("workbench:updateItemResourceFields", payload),
  applyWorkbenchMainResource: (payload) => ipcRenderer.invoke("workbench:applyMainResource", payload),
  transformWorkbenchFbx: (payload) => ipcRenderer.invoke("workbench:transformFbx", payload),
  removeWorkbenchFbxSkin: (payload) => ipcRenderer.invoke("workbench:removeFbxSkin", payload),
  bindWorkbenchHs2Skeleton: (payload) => ipcRenderer.invoke("workbench:bindHs2Skeleton", payload),
  transferWorkbenchFbxWeights: (payload) => ipcRenderer.invoke("workbench:transferFbxWeights", payload),
  packageWorkbenchMod: (payload) => ipcRenderer.invoke("workbench:packageMod", payload),
  onWorkbenchPackageProgress: (callback) => {
    const listener = (_event, progress) => callback?.(progress);
    ipcRenderer.on("workbench:packageProgress", listener);
    return () => ipcRenderer.removeListener("workbench:packageProgress", listener);
  },
  loadGameSetup: (gameDir) => ipcRenderer.invoke("game:loadSetup", gameDir),
  saveGameSetup: (gameDir, setup) => ipcRenderer.invoke("game:saveSetup", gameDir, setup),
  ensureGamePlugins: (gameDir) => ipcRenderer.invoke("game:ensurePlugins", gameDir),
  launchGameExecutable: (launchType, gameDir) => ipcRenderer.invoke("game:launchExecutable", launchType, gameDir),
  openFbxInBlender: (blenderPath, fbxPath) => ipcRenderer.invoke("blender:openFbx", blenderPath, fbxPath),
  loadSettings: () => ipcRenderer.invoke("settings:load"),
  saveSettings: (settings) => ipcRenderer.invoke("settings:save", settings),
  backendRequest: (route, options) => ipcRenderer.invoke("backend:request", route, options),
  backendBaseUrl: process.env.STAR_MANAGER_BACKEND_BASE_URL || "http://127.0.0.1:8765"
});
