const fs = require("node:fs");
const path = require("node:path");
const {
  REQUIRED_PLUGIN_FILE_NAMES,
  getWindowsFileVersion
} = require("../electron/game-plugins.cjs");

const root = path.join(__dirname, "..");
const bundledDirectory = path.join(root, "tools", "StarManager");
const pluginProjects = new Map([
  ["StarManager.CardMetadata.dll", "star-manager-card-metadata-plugin"],
  ["StarManager.CharacterCardReadProbe.dll", "star-manager-character-card-read-probe"],
  ["StarManager.GameItemProbe.dll", "star-manager-game-item-probe"]
]);

function isFile(filePath) {
  try {
    return fs.statSync(filePath).isFile();
  } catch {
    return false;
  }
}

function parseFileVersion(value) {
  const parts = String(value || "")
    .trim()
    .split(".")
    .map((part) => Number(part));
  return parts.length === 4 && parts.every((part) => Number.isInteger(part) && part >= 0) ? parts : null;
}

function compareVersions(left, right) {
  const a = parseFileVersion(left);
  const b = parseFileVersion(right);
  if (!a || !b) return null;
  for (let index = 0; index < 4; index += 1) {
    if (a[index] !== b[index]) return a[index] > b[index] ? 1 : -1;
  }
  return 0;
}

function shouldStage(sourcePath, bundledPath) {
  if (!isFile(bundledPath)) return true;
  const sourceVersion = getWindowsFileVersion(sourcePath);
  const bundledVersion = getWindowsFileVersion(bundledPath);
  const versionOrder = compareVersions(sourceVersion, bundledVersion);
  if (versionOrder !== null && versionOrder !== 0) return versionOrder > 0;
  if (versionOrder === 0) {
    return fs.statSync(sourcePath).mtimeMs > fs.statSync(bundledPath).mtimeMs;
  }
  return fs.statSync(sourcePath).mtimeMs > fs.statSync(bundledPath).mtimeMs;
}

fs.mkdirSync(bundledDirectory, { recursive: true });
const staged = [];
const skipped = [];
for (const fileName of REQUIRED_PLUGIN_FILE_NAMES) {
  const projectDirectory = pluginProjects.get(fileName);
  const sourcePath = path.join(root, "tools", projectDirectory, "bin", "Release", "net472", fileName);
  const bundledPath = path.join(bundledDirectory, fileName);
  if (!isFile(sourcePath)) {
    skipped.push(`${fileName}（未找到 Release 编译产物，保留现有打包资源）`);
    continue;
  }
  if (!shouldStage(sourcePath, bundledPath)) {
    skipped.push(`${fileName}（打包资源版本不低于编译产物）`);
    continue;
  }
  fs.copyFileSync(sourcePath, bundledPath);
  staged.push(`${fileName}（${getWindowsFileVersion(bundledPath) || "版本未知"}）`);
}

if (staged.length) console.log(`已同步插件打包资源：${staged.join("、")}`);
if (skipped.length) console.log(`插件打包资源未同步：${skipped.join("、")}`);
