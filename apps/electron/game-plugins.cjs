const fs = require("node:fs");
const path = require("node:path");

const REQUIRED_PLUGIN_FILE_NAMES = Object.freeze([
  "StarManager.CardMetadata.dll",
  "StarManager.CharacterCardReadProbe.dll",
  "StarManager.GameItemProbe.dll"
]);

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
    if (fs.lstatSync(destinationPath).isSymbolicLink()) return "conflict";
    if (fs.statSync(destinationPath).isFile()) return "existing";
  } catch {
    // The active path is absent; check the disabled form below.
  }
  try {
    if (fs.lstatSync(disabledPath).isSymbolicLink()) return "conflict";
    if (fs.statSync(disabledPath).isFile()) return "disabled";
  } catch {
    // The current disabled form is absent; check the legacy form below.
  }
  try {
    if (fs.lstatSync(interimDisabledPath).isSymbolicLink()) return "conflict";
    if (fs.statSync(interimDisabledPath).isFile()) return "disabled";
  } catch {
    // The interim disabled form is absent; check the legacy form below.
  }
  try {
    if (fs.lstatSync(legacyDisabledPath).isSymbolicLink()) return "conflict";
    if (fs.statSync(legacyDisabledPath).isFile()) return "disabled";
  } catch {
    // Neither disabled form is installed.
  }
  return "missing";
}

function copyPluginAtomically(sourcePath, destinationPath) {
  const temporaryPath = path.join(
    path.dirname(destinationPath),
    `.${path.basename(destinationPath)}.${process.pid}.${Date.now()}.${Math.random().toString(16).slice(2)}.tmp`
  );
  try {
    fs.copyFileSync(sourcePath, temporaryPath);
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
    destinationPath: path.join(normalizedGameDir, "BepInEx", "Plugins", fileName)
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

  const states = sourcePaths.map(({ fileName, destinationPath }) => ({
    file_name: fileName,
    destination_path: destinationPath,
    status: getExistingPluginState(destinationPath)
  }));
  const conflicts = states.filter((item) => item.status === "conflict");
  if (conflicts.length) {
    return {
      ok: false,
      error: `插件目标是符号链接，未执行安装：${conflicts.map((item) => item.file_name).join("、")}`,
      destination_dir: path.join(normalizedGameDir, "BepInEx", "Plugins"),
      plugins: states
    };
  }

  const installStates = states.filter((item) => item.status === "missing");
  try {
    if (installStates.length) {
      fs.mkdirSync(path.join(normalizedGameDir, "BepInEx", "Plugins"), { recursive: true });
      for (const item of installStates) {
        copyPluginAtomically(path.join(bundledDirectory, item.file_name), item.destination_path);
        item.status = "installed";
      }
    }
  } catch (error) {
    return {
      ok: false,
      error: `安装 Star Manager 插件失败：${error.message}`,
      destination_dir: path.join(normalizedGameDir, "BepInEx", "Plugins"),
      plugins: states
    };
  }

  return {
    ok: true,
    game_dir: normalizedGameDir,
    destination_dir: path.join(normalizedGameDir, "BepInEx", "Plugins"),
    plugins: states,
    installed_count: states.filter((item) => item.status === "installed").length,
    existing_count: states.filter((item) => item.status === "existing" || item.status === "disabled").length
  };
}

module.exports = {
  REQUIRED_PLUGIN_FILE_NAMES,
  getBundledPluginDirectory,
  ensureBundledPlugins
};
