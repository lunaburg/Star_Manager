import { parse as parseSfc } from '@vue/compiler-sfc';
import { parse as parseTemplate } from '@vue/compiler-dom';
import { parseExpression } from '@babel/parser';

const hasChinese = /\p{Script=Han}/u;
const displayAttributes = new Set(['title', 'placeholder', 'aria-label', 'alt', 'data-tooltip']);
const userData = /(?:\.(?:name|display_name|filename|file_name|fileName|path|relative_path|guid|author|version|tag|tags)|(?:Path|Dir|Name|Guid))\b|\b(?:tag|author|filename|fileName|name|guid|path|version)\b/;

// Translate display boundaries only. Values, keys, events and conditions retain
// the original strings used by the backend and the game's file formats.
export function localizeVue(source) {
  const { descriptor } = parseSfc(source);
  if (!descriptor.template || descriptor.template.lang) return source;
  const template = descriptor.template;
  const edits = [];
  const replace = (loc, value) => edits.push({ start: template.loc.start.offset + loc.start.offset, end: template.loc.start.offset + loc.end.offset, value });
  const visit = (node) => {
    // Vue's parser removes the v-pre directive from props after consuming it.
    if (node.type === 1 && (node.tag === 'pre' || /\sv-pre(?:\s|=|$)/.test(node.loc.source.slice(0, node.loc.source.indexOf('>'))))) return;
    if (node.type === 2 && hasChinese.test(node.content)) {
      replace(node.loc, `{{ $t(${JSON.stringify(node.content)}) }}`);
    }
    if (node.type === 5) {
      const expression = node.content.content;
      // User-authored metadata and paths must never be translated. Translate
      // fallback literals separately by putting them in a labelled UI helper.
      if (!expression.includes('$t(') && !userData.test(expression)) {
        replace(node.content.loc, `$t(${localizeLabels(expression)})`);
      } else if (hasChinese.test(expression) && !expression.includes('$t(')) {
        replace(node.content.loc, localizeFallbacks(expression));
      }
    }
    if (node.type === 1) {
      for (const prop of node.props) {
        if (prop.type === 6 && displayAttributes.has(prop.name) && prop.value && hasChinese.test(prop.value.content)) {
          replace(prop.loc, `:${prop.name}="${escapeAttribute(`$t(${JSON.stringify(prop.value.content)})`)}"`);
        } else if (prop.type === 7 && prop.name === 'bind' && displayAttributes.has(prop.arg?.content) && prop.exp && !prop.exp.content.includes('$t(')) {
          const expression = prop.exp.content;
          if (hasChinese.test(expression) || /(?:label|title|message|tooltip|description|Label|Title|Message|Tooltip)/.test(expression)) {
            const localized = userData.test(expression) ? localizeFallbacks(expression) : `$t(${localizeLabels(expression)})`;
            replace(prop.exp.loc, escapeAttribute(localized));
          }
        }
      }
    }
    node.children?.forEach(visit);
  };
  visit(parseTemplate(template.content));
  for (const edit of edits.sort((a, b) => b.start - a.start)) {
    source = source.slice(0, edit.start) + edit.value + source.slice(edit.end);
  }
  return source;
}

function escapeAttribute(value) {
  return value.replaceAll('&', '&amp;').replaceAll('"', '&quot;').replaceAll("'", '&#39;');
}

function localizeFallbacks(expression) {
  const edits = [];
  const visit = (node, parent) => {
    if (!node || typeof node !== 'object') return;
    if (node.type === 'StringLiteral' && hasChinese.test(node.value)
      && (parent?.type === 'LogicalExpression' || (parent?.type === 'ConditionalExpression' && parent.test !== node))) {
      edits.push({ start: node.start, end: node.end, value: `$t(${JSON.stringify(node.value)})` });
    }
    for (const [key, value] of Object.entries(node)) {
      if (key === 'loc') continue;
      if (Array.isArray(value)) value.forEach((child) => visit(child, node));
      else if (value && typeof value === 'object') visit(value, node);
    }
  };
  visit(parseExpression(expression));
  for (const edit of edits.sort((a, b) => b.start - a.start)) expression = expression.slice(0, edit.start) + edit.value + expression.slice(edit.end);
  return expression;
}

function localizeLabels(expression) {
  const edits = [];
  const visit = (node) => {
    if (!node || typeof node !== 'object') return;
    if ((node.type === 'MemberExpression' || node.type === 'OptionalMemberExpression') && !node.computed && node.property.name === 'label') {
      edits.push({ start: node.start, end: node.end });
      return;
    }
    for (const [key, value] of Object.entries(node)) {
      if (key === 'loc') continue;
      if (Array.isArray(value)) value.forEach(visit);
      else if (value && typeof value === 'object') visit(value);
    }
  };
  visit(parseExpression(expression));
  for (const edit of edits.sort((a, b) => b.start - a.start)) expression = expression.slice(0, edit.start) + `$t(${expression.slice(edit.start, edit.end)})` + expression.slice(edit.end);
  return expression;
}

export default function localizationPlugin() {
  return {
    name: 'star-manager-localization',
    enforce: 'pre',
    transform(source, id) {
      if (!id.endsWith('.vue')) return null;
      return { code: localizeVue(source), map: null };
    }
  };
}
