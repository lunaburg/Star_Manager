import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import * as Vue from 'vue';
import { renderToString } from '@vue/server-renderer';
import { compile } from '@vue/compiler-dom';
import { parse } from '@vue/compiler-sfc';
import { parse as parseJavaScript } from '@babel/parser';
import { normalizeLanguage, translate, translateDialogOptions } from '../electron/localization.mjs';
import { installI18n, locale, setLocale, t } from '../src/i18n/index.js';
import { localizeVue } from './localize-vue.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const catalog = JSON.parse(fs.readFileSync(path.join(root, 'electron/locales/en.json'), 'utf8'));

test('language normalization and reactive switching preserve original Chinese', () => {
  assert.equal(normalizeLanguage('zh-CN'), 'zh-CN');
  for (const input of [null, undefined, '', 'vi', 'en-US']) assert.equal(normalizeLanguage(input), 'en-US');
  const seen = [];
  const effect = Vue.effect(() => seen.push(t('设置')));
  setLocale('zh-CN');
  setLocale('en-US');
  Vue.stop(effect);
  assert.deepEqual(seen, ['Settings', '设置', 'Settings']);
  assert.equal(locale.value, 'en-US');
});

test('exact and parameterized translation preserves whitespace and captured data', () => {
  assert.equal(translate('  设置\n'), '  Settings\n');
  assert.equal(translate('已导出 12 张人物卡'), 'Exported 12 character cards');
  assert.equal(translate('已定位「设置」。'), 'Located “设置”.');
  assert.equal(translate('已定位「角色$&名字」。'), 'Located “角色$&名字”.');
  for (const value of [42, null, undefined, true, { name: '设置' }, 'E:\\模组\\设置.zipmod', '第三方错误：原始诊断', '__proto__']) {
    assert.equal(translate(value), value);
  }
  assert.equal(translate('已导出 12 张人物卡', 'zh-CN'), '已导出 12 张人物卡');
});

test('every English catalog entry preserves its message placeholders', () => {
  const placeholders = (value) => [...value.matchAll(/\{\d+\}/g)].map((match) => match[0]).sort();
  for (const [key, value] of Object.entries(catalog)) {
    assert.ok(value && typeof value === 'string', key);
    assert.deepEqual(placeholders(value), placeholders(key), key);
    assert.equal(/\p{Script=Han}/u.test(value), false, key);
  }
});

test('native dialogs translate copy without changing file paths and extensions', () => {
  const original = {
    title: '选择应用壁纸', buttons: ['取消', '确定'], defaultPath: 'E:\\图片\\设置.png',
    filters: [{ name: '图片', extensions: ['png', 'jpg'] }], properties: ['openFile'],
    detail: '默认值：设置'
  };
  const result = translateDialogOptions(original, 'en-US');
  assert.equal(result.title, 'Choose app wallpaper');
  assert.deepEqual(result.buttons, ['Cancel', 'OK']);
  assert.equal(result.defaultPath, original.defaultPath);
  assert.deepEqual(result.filters, [{ name: 'Images', extensions: ['png', 'jpg'] }]);
  assert.equal(result.detail, 'Default: 设置');
  assert.equal(original.title, '选择应用壁纸');
  assert.deepEqual(translateDialogOptions(original, 'zh-CN'), original);
});

test('actual Electron settings functions persist language across reloads and preserve game paths', () => {
  const mainSource = fs.readFileSync(path.join(root, 'electron/main.cjs'), 'utf8');
  const required = new Set(['normalizeSettings', 'loadSettingsFile', 'writeSettingsFileAtomically', 'saveSettingsFile']);
  const declarations = parseJavaScript(mainSource, { sourceType: 'script' }).program.body
    .filter((node) => node.type === 'FunctionDeclaration' && required.has(node.id.name))
    .map((node) => mainSource.slice(node.start, node.end)).join('\n');
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'star-manager-language-'));
  const file = path.join(directory, 'settings.json');
  const createHarness = () => new Function('fs', 'path', 'settingsPath', 'settingsReadPath', 'getDatabaseWorkerCapacity', 'DEFAULT_SB3UTILITY_EXECUTABLE_PATH',
    `${declarations}\nreturn { load: loadSettingsFile, save: saveSettingsFile };`
  )(fs, path, () => file, () => file, () => ({ workerLimit: 4, logicalProcessorCount: 8 }), '');
  try {
    fs.writeFileSync(file, JSON.stringify({ gameDir: 'E:\\游戏\\HS2', inputDir: 'E:\\人物卡' }), 'utf8');
    const first = createHarness();
    assert.equal(first.load().settings.language, 'en-US');
    assert.equal(first.save({ language: 'zh-CN' }).ok, true);
    const restarted = createHarness();
    assert.equal(restarted.load().settings.language, 'zh-CN');
    assert.equal(restarted.load().settings.gameDir, 'E:\\游戏\\HS2');
    assert.equal(restarted.load().settings.inputDir, 'E:\\人物卡');
    assert.equal(restarted.save({ language: 'invalid' }).settings.language, 'en-US');
    assert.equal(createHarness().load().settings.language, 'en-US');
  } finally {
    assert.equal(path.dirname(directory), path.resolve(os.tmpdir()));
    assert.ok(path.basename(directory).startsWith('star-manager-language-'));
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

async function renderTemplate(source, data, language) {
  setLocale(language);
  const localized = localizeVue(`<template>${source}</template>`);
  const template = parse(localized).descriptor.template.content;
  const render = new Function('Vue', compile(template, { mode: 'function', prefixIdentifiers: true }).code)(Vue);
  const app = Vue.createSSRApp({ setup: () => data, render });
  installI18n(app);
  return renderToString(app);
}

test('compiled Vue translates text, labels, fallback text and display attributes in both languages', async () => {
  const source = '<section><h1>设置</h1><button :title="`筛选${group.label}`">{{ group.label }}</button><input placeholder="搜索标签"><p>{{ count }}</p><small>{{ card.name || "未命名物品" }}</small></section>';
  const data = { group: { label: '服装' }, count: 3, card: { name: '' } };
  const english = await renderTemplate(source, data, 'en-US');
  assert.match(english, /<h1>Settings<\/h1>/);
  assert.match(english, /title="Filter Clothing"/);
  assert.match(english, /placeholder="Search tags"/);
  assert.match(english, /<p>3<\/p>/);
  assert.match(english, /Unnamed item/);
  const chinese = await renderTemplate(source, data, 'zh-CN');
  assert.match(chinese, /<h1>设置<\/h1>/);
  assert.match(chinese, /筛选服装/);
  setLocale('en-US');
});

test('display localization preserves user names and tags even when they equal a catalog key', async () => {
  const html = await renderTemplate('<p :title="card.name || \'未命名物品\'">{{ card.name || "未命名物品" }}</p><small>{{ item.path }}</small><b>{{ tag }}</b><i>{{ author || "全部作者" }}</i><pre>{{ message }}</pre>', {
    card: { name: '设置' }, item: { path: 'E:\\服装\\设置.zipmod' }, tag: '服装', author: '设置', message: '设置'
  }, 'en-US');
  assert.match(html, /<p title="设置">设置<\/p>/);
  assert.match(html, /<b>服装<\/b>/);
  assert.match(html, /<i>设置<\/i>/);
  assert.match(html, /<pre>设置<\/pre>/);
  assert.ok(html.includes('E:\\服装\\设置.zipmod'));
});

test('compiler leaves semantic conditions, model values, events and keys untouched', () => {
  const source = '<template><button v-if="status === \'正常\'" :key="item.name" :value="item.name" @click="send(\'删除\')">删除</button><span v-pre>设置</span></template>';
  const result = localizeVue(source);
  assert.ok(result.includes('v-if="status === \'正常\'"'));
  assert.ok(result.includes(':key="item.name"'));
  assert.ok(result.includes(':value="item.name"'));
  assert.ok(result.includes('@click="send(\'删除\')"'));
  assert.ok(result.includes('<span v-pre>设置</span>'));
  assert.ok(result.includes('$t("删除")'));
});

test('every repository Vue template compiles after localization', () => {
  function scan(dir) {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const filename = path.join(dir, entry.name);
      if (entry.isDirectory() && entry.name !== 'assets') scan(filename);
      if (!entry.isFile() || !filename.endsWith('.vue')) continue;
      const localized = localizeVue(fs.readFileSync(filename, 'utf8'));
      const { descriptor, errors } = parse(localized);
      assert.deepEqual(errors, [], filename);
      if (descriptor.template) assert.doesNotThrow(() => compile(descriptor.template.content), filename);
    }
  }
  scan(path.join(root, 'src'));
});
