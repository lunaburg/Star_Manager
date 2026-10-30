import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parse as parseSfc } from '@vue/compiler-sfc';
import { parse as parseTemplate } from '@vue/compiler-dom';
import { parse, parseExpression } from '@babel/parser';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const catalog = JSON.parse(fs.readFileSync(path.join(root, 'electron/locales/en.json'), 'utf8'));
const chinese = /\p{Script=Han}/u;
const entries = new Set();
const templateEntries = new Set();
function walk(node, visitor) {
  if (!node || typeof node !== 'object') return;
  visitor(node);
  for (const [key, value] of Object.entries(node)) {
    if (['loc', 'comments', 'tokens'].includes(key)) continue;
    if (Array.isArray(value)) value.forEach((child) => walk(child, visitor));
    else if (value && typeof value === 'object') walk(value, visitor);
  }
}
function collect(node) {
  if (node.type === 'StringLiteral' && chinese.test(node.value)) entries.add(node.value.trim());
  if (node.type === 'TemplateLiteral') {
    const key = node.quasis.map((part, index) => part.value.cooked + (index < node.expressions.length ? `{${index}}` : '')).join('');
    if (chinese.test(key)) entries.add(key.trim());
  }
}
function scan(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const filename = path.join(dir, entry.name);
    if (entry.isDirectory() && entry.name !== 'assets') scan(filename);
    if (!entry.isFile() || !filename.endsWith('.vue')) continue;
    const { descriptor } = parseSfc(fs.readFileSync(filename, 'utf8'));
    if (descriptor.scriptSetup) walk(parse(descriptor.scriptSetup.content, { sourceType: 'module' }), collect);
    if (!descriptor.template) continue;
    walk(parseTemplate(descriptor.template.content), (node) => {
      if (node.type === 2 && chinese.test(node.content)) templateEntries.add(node.content.trim());
      if (node.type === 6 && node.value && chinese.test(node.value.content)) templateEntries.add(node.value.content.trim());
      if (node.type === 4 && !node.isStatic) {
        try { walk(parseExpression(node.content), collect); } catch { /* v-for and statement expressions */ }
      }
    });
  }
}
scan(path.join(root, 'src'));
const missingStatic = [...templateEntries].filter((key) => key !== '简体中文' && !(key in catalog));
const missingScript = [...entries].filter((key) => !(key in catalog));
if (process.argv.includes('--list')) console.log(JSON.stringify(missingScript, null, 2));
else {
  console.log(`English catalog: ${Object.keys(catalog).length} entries; missing template text: ${missingStatic.length}; uncatalogued script strings: ${missingScript.length}`);
  if (missingStatic.length) { console.error(missingStatic); process.exitCode = 1; }
  if (process.argv.includes('--strict') && missingScript.length) { console.error(missingScript); process.exitCode = 1; }
}
