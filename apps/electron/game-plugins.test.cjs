const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  REQUIRED_PLUGIN_FILE_NAMES,
  ensureBundledPlugins,
  getBundledPluginDirectory
} = require("./game-plugins.cjs");

function createPluginFixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "star-manager-plugins-"));
  const gameDir = path.join(root, "game");
  const sourceDir = path.join(root, "bundled");
  fs.mkdirSync(gameDir, { recursive: true });
  fs.mkdirSync(sourceDir, { recursive: true });
  fs.writeFileSync(path.join(gameDir, "HoneySelect2.exe"), "game");
  REQUIRED_PLUGIN_FILE_NAMES.forEach((fileName, index) => {
    fs.writeFileSync(path.join(sourceDir, fileName), `plugin-${index}`);
  });
  return { root, gameDir, sourceDir };
}

function removeFixture(root) {
  fs.rmSync(root, { recursive: true, force: true });
}

test("bundled plugin installation copies only missing plugins atomically", () => {
  const fixture = createPluginFixture();
  try {
    const first = ensureBundledPlugins(fixture.gameDir, { sourceDirectory: fixture.sourceDir });
    assert.equal(first.ok, true);
    assert.equal(first.installed_count, 3);
    for (const fileName of REQUIRED_PLUGIN_FILE_NAMES) {
      assert.equal(
        fs.readFileSync(path.join(fixture.gameDir, "BepInEx", "Plugins", fileName), "utf8").startsWith("plugin-"),
        true
      );
    }

    const target = path.join(fixture.gameDir, "BepInEx", "Plugins", REQUIRED_PLUGIN_FILE_NAMES[0]);
    fs.writeFileSync(target, "user-version");
    const second = ensureBundledPlugins(fixture.gameDir, { sourceDirectory: fixture.sourceDir });
    assert.equal(second.ok, true);
    assert.equal(second.installed_count, 0);
    assert.equal(fs.readFileSync(target, "utf8"), "user-version");
  } finally {
    removeFixture(fixture.root);
  }
});

test("a disabled plugin counts as installed without being re-enabled", () => {
  const fixture = createPluginFixture();
  try {
    const pluginDir = path.join(fixture.gameDir, "BepInEx", "Plugins");
    fs.mkdirSync(pluginDir, { recursive: true });
    fs.writeFileSync(path.join(pluginDir, `${REQUIRED_PLUGIN_FILE_NAMES[0].slice(0, -4)}.dl_`), "disabled");

    const result = ensureBundledPlugins(fixture.gameDir, { sourceDirectory: fixture.sourceDir });
    assert.equal(result.ok, true);
    assert.equal(result.installed_count, 2);
    assert.equal(fs.existsSync(path.join(pluginDir, `${REQUIRED_PLUGIN_FILE_NAMES[0].slice(0, -4)}.dl_`)), true);
    assert.equal(fs.existsSync(path.join(pluginDir, REQUIRED_PLUGIN_FILE_NAMES[0])), false);
  } finally {
    removeFixture(fixture.root);
  }
});

test("a legacy disabled plugin is still treated as installed", () => {
  const fixture = createPluginFixture();
  try {
    const pluginDir = path.join(fixture.gameDir, "BepInEx", "Plugins");
    fs.mkdirSync(pluginDir, { recursive: true });
    fs.writeFileSync(path.join(pluginDir, `${REQUIRED_PLUGIN_FILE_NAMES[0]}.disabled`), "legacy");

    const result = ensureBundledPlugins(fixture.gameDir, { sourceDirectory: fixture.sourceDir });
    assert.equal(result.ok, true);
    assert.equal(result.installed_count, 2);
    assert.equal(fs.existsSync(path.join(pluginDir, `${REQUIRED_PLUGIN_FILE_NAMES[0]}.disabled`)), true);
    assert.equal(fs.existsSync(path.join(pluginDir, REQUIRED_PLUGIN_FILE_NAMES[0])), false);
  } finally {
    removeFixture(fixture.root);
  }
});

test("packaged and development resource paths are resolved separately", () => {
  assert.equal(
    getBundledPluginDirectory({ appIsPackaged: true, resourcesPath: "C:\\app\\resources" }),
    path.join("C:\\app\\resources", "StarManager")
  );
  assert.equal(
    getBundledPluginDirectory({ appIsPackaged: false, sourceDirectory: "C:\\source\\StarManager" }),
    path.resolve("C:\\source\\StarManager")
  );
});
