const fs = require("node:fs");
const path = require("node:path");
const { REQUIRED_PLUGIN_FILE_NAMES: requiredPluginFileNames } = require("../electron/game-plugins.cjs");

const root = path.join(__dirname, "..");
const remoteIndexPath = path.join(
  root,
  "backend",
  "runtime",
  "remote",
  "remote_zipmod_index.sqlite"
);
const bundledPluginDirectory = path.join(root, "tools", "StarManager");

if (!fs.existsSync(remoteIndexPath) || !fs.statSync(remoteIndexPath).isFile()) {
  console.error(`Required remote mod database is missing: ${remoteIndexPath}`);
  console.error("Build or place the remote index before running npm run package:win.");
  process.exit(1);
}

console.log(`Package input found: ${remoteIndexPath}`);

const missingPlugins = requiredPluginFileNames.filter((fileName) => {
  const filePath = path.join(bundledPluginDirectory, fileName);
  return !fs.existsSync(filePath) || !fs.statSync(filePath).isFile();
});
if (missingPlugins.length) {
  console.error(`Required bundled Star Manager plugins are missing from ${bundledPluginDirectory}:`);
  missingPlugins.forEach((fileName) => console.error(`- ${fileName}`));
  process.exit(1);
}

console.log(`Bundled Star Manager plugins found: ${requiredPluginFileNames.join(", ")}`);
