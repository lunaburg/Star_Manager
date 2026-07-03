const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("desktopApi", {
  selectDirectory: (title) => ipcRenderer.invoke("dialog:selectDirectory", title),
  selectImageFile: (title) => ipcRenderer.invoke("dialog:selectImageFile", title),
  promptText: (title, message, defaultValue) => ipcRenderer.invoke("dialog:promptText", title, message, defaultValue),
  showItemInFolder: (filePath) => ipcRenderer.invoke("shell:showItemInFolder", filePath),
  launchGameExecutable: (launchType, gameDir) => ipcRenderer.invoke("game:launchExecutable", launchType, gameDir),
  loadSettings: () => ipcRenderer.invoke("settings:load"),
  saveSettings: (settings) => ipcRenderer.invoke("settings:save", settings),
  backendRequest: (route, options) => ipcRenderer.invoke("backend:request", route, options),
  backendBaseUrl: process.env.STAR_MANAGER_BACKEND_BASE_URL || "http://127.0.0.1:8765"
});
