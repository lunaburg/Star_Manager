const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const childProcess = require("node:child_process");

const REQUIRED_PLUGIN_FILE_NAMES = Object.freeze([
  "StarManager.CardMetadata.dll",
  "StarManager.CharacterCardReadProbe.dll",
  "StarManager.GameItemProbe.dll"
]);

function getFileHash(filePath) {
  try {
    return crypto.createHash("sha256").update(fs.readFileSync(filePath)).digest("hex");
  } catch {
    return "";
  }
}

function getWindowsFileVersion(filePath) {
  if (process.platform !== "win32") return "";
  try {
    const script = [
      "$ErrorActionPreference = 'Stop'",
      "$version = [System.Diagnostics.FileVersionInfo]::GetVersionInfo($env:STAR_MANAGER_PLUGIN_VERSION_PATH).FileVersion",
      "if ($version) { [Console]::Write($version) }"
    ].join("; ");
    const encodedScript = Buffer.from(script, "utf16le").toString("base64");
    const result = childProcess.execFileSync(
      "powershell.exe",
      ["-NoProfile", "-NonInteractive", "-EncodedCommand", encodedScript],
      {
        encoding: "utf8",
        timeout: 5000,
        windowsHide: true,
        env: { ...process.env, STAR_MANAGER_PLUGIN_VERSION_PATH: filePath }
      }
    );
    return String(result || "").trim();
  } catch {
    return "";
  }
}

function readPluginIdentity(filePath) {
  return { version: getWindowsFileVersion(filePath), hash: getFileHash(filePath) };
}

function isRegularFile(filePath) {
  try {
    return fs.statSync(filePath).isFile();
  } catch {
    return false;
  }
}

function isDirectory(filePath) {
  try {
    return fs.statSync(filePath).isDirectory();
  } catch {
    return false;
  }
}

function isHs2GameDirectory(gameDir) {
  return Boolean(gameDir)
    && isDirectory(gameDir)
    && isRegularFile(path.join(gameDir, "HoneySelect2.exe"));
}

function getBundledPluginDirectory({ appIsPackaged = false, resourcesPath = process.resourcesPath, sourceDirectory } = {}) {
  if (appIsPackaged) return path.join(resourcesPath, "StarManager");
  return path.resolve(sourceDirectory || path.join(__dirname, "..", "tools", "StarManager"));
}

function getExistingPluginState(destinationPath) {
  const disabledPath = `${destinationPath.slice(0, -path.extname(destinationPath).length)}.dl_`;
  const interimDisabledPath = `${destinationPath}.dl_`;
  const legacyDisabledPath = `${destinationPath}.disabled`;
  try {
    if (fs.lstatSync(destinationPath).isSymbolicLink()) return { status: "conflict", path: destinationPath };
    if (fs.statSync(destinationPath).isFile()) return { status: "existing", path: destinationPath };
  } catch {
    // The active path is absent; check the disabled form below.
  }
  try {
    if (fs.lstatSync(disabledPath).isSymbolicLink()) return { status: "conflict", path: disabledPath };
    if (fs.statSync(disabledPath).isFile()) return { status: "disabled", path: disabledPath };
  } catch {
    // The current disabled form is absent; check the legacy form below.
  }
  try {
    if (fs.lstatSync(interimDisabledPath).isSymbolicLink()) return { status: "conflict", path: interimDisabledPath };
    if (fs.statSync(interimDisabledPath).isFile()) return { status: "disabled", path: interimDisabledPath };
  } catch {
    // The interim disabled form is absent; check the legacy form below.
  }
  try {
    if (fs.lstatSync(legacyDisabledPath).isSymbolicLink()) return { status: "conflict", path: legacyDisabledPath };
    if (fs.statSync(legacyDisabledPath).isFile()) return { status: "disabled", path: legacyDisabledPath };
  } catch {
    // Neither disabled form is installed.
  }
  return { status: "missing", path: destinationPath };
}

function copyPluginAtomically(sourcePath, destinationPath) {
  const temporaryPath = path.join(
    path.dirname(destinationPath),
    `.${path.basename(destinationPath)}.${process.pid}.${Date.now()}.${Math.random().toString(16).slice(2)}.tmp`
  );
  try {
    fs.copyFileSync(sourcePath, temporaryPath);
    // Windows does not allow renameSync to replace an existing file. The
    // destination has already been checked for symlinks before this point.
    if (fs.existsSync(destinationPath)) fs.rmSync(destinationPath, { force: true });
    fs.renameSync(temporaryPath, destinationPath);
  } finally {
    if (fs.existsSync(temporaryPath)) fs.rmSync(temporaryPath, { force: true });
  }
}

function ensureBundledPlugins(gameDir, { sourceDirectory } = {}) {
  const normalizedGameDir = path.resolve(String(gameDir || ""));
  if (!isHs2GameDirectory(normalizedGameDir)) {
    return { ok: false, error: "请选择有效的 HS2 游戏目录" };
  }

  const bundledDirectory = path.resolve(String(sourceDirectory || getBundledPluginDirectory()));
  const sourcePaths = REQUIRED_PLUGIN_FILE_NAMES.map((fileName) => ({
    fileName,
    sourcePath: path.join(bundledDirectory, fileName),
    destinationPath: path.join(normalizedGameDir, "BepInEx", "Plugins", "StarManager", fileName)
  }));
  const missingSources = sourcePaths
    .filter(({ sourcePath }) => !isRegularFile(sourcePath))
    .map(({ fileName }) => fileName);
  if (missingSources.length) {
    return {
      ok: false,
      error: `管理器内置插件资源缺失：${missingSources.join("、")}`,
      missing_sources: missingSources
    };
  }

  const sourceIdentities = new Map(
    sourcePaths.map(({ fileName, sourcePath }) => [fileName, readPluginIdentity(sourcePath)])
  );
  const states = sourcePaths.map(({ fileName, destinationPath }) => {
    const existing = getExistingPluginState(destinationPath);
    const sourceIdentity = sourceIdentities.get(fileName) || { version: "", hash: "" };
    const installedIdentity = existing.status === "missing" || existing.status === "conflict"
      ? { version: "", hash: "" }
      : readPluginIdentity(existing.path);
    const versionMatch = existing.status === "missing" || existing.status === "conflict"
      ? null
      : Boolean(sourceIdentity.version && installedIdentity.version && sourceIdentity.version === installedIdentity.version);
    const matches = existing.status !== "missing"
      && existing.status !== "conflict"
      && (versionMatch === true || (!sourceIdentity.version && !installedIdentity.version && Boolean(sourceIdentity.hash && installedIdentity.hash && sourceIdentity.hash === installedIdentity.hash)));
    return {
      file_name: fileName,
      destination_path: destinationPath,
      ...existing,
      source_version: sourceIdentity.version,
      installed_version: installedIdentity.version,
      source_hash: sourceIdentity.hash,
      installed_hash: installedIdentity.hash,
      version_match: versionMatch,
      matches
    };
  });
  const conflicts = states.filter((item) => item.status === "conflict");
  if (conflicts.length) {
    return {
      ok: false,
      error: `插件目标是符号链接，未执行安装：${conflicts.map((item) => item.file_name).join("、")}`,
      destination_dir: path.join(normalizedGameDir, "BepInEx", "Plugins", "StarManager"),
      plugins: states
    };
  }

  const installStates = states.filter((item) => item.status === "missing" || !item.matches);
  try {
    if (installStates.length) {
      fs.mkdirSync(path.join(normalizedGameDir, "BepInEx", "Plugins", "StarManager"), { recursive: true });
      for (const item of installStates) {
        copyPluginAtomically(path.join(bundledDirectory, item.file_name), item.path);
        item.status = item.status === "missing" ? "installed" : "updated";
        item.installed_version = item.source_version;
        item.installed_hash = item.source_hash;
        item.version_match = true;
        item.matches = true;
      }
    }
  } catch (error) {
    return {
      ok: false,
      error: `安装 Star Manager 插件失败：${error.message}`,
      destination_dir: path.join(normalizedGameDir, "BepInEx", "Plugins", "StarManager"),
      plugins: states
    };
  }

  return {
    ok: true,
    game_dir: normalizedGameDir,
    destination_dir: path.join(normalizedGameDir, "BepInEx", "Plugins", "StarManager"),
    plugins: states,
    installed_count: states.filter((item) => item.status === "installed").length,
    updated_count: states.filter((item) => item.status === "updated").length,
    existing_count: states.filter((item) => item.status === "existing" || item.status === "disabled").length
  };
}

module.exports = {
  REQUIRED_PLUGIN_FILE_NAMES,
  getWindowsFileVersion,
  getBundledPluginDirectory,
  ensureBundledPlugins
};
