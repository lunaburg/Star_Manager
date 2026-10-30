import english from './locales/en.json' with { type: 'json' };

const escapeRegExp = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const patterns = Object.entries(english)
  .filter(([key]) => /\{\d+\}/.test(key))
  .sort(([a], [b]) => b.replace(/\{\d+\}/g, '').length - a.replace(/\{\d+\}/g, '').length)
  .map(([key, value]) => ({
    expression: new RegExp(`^${key.split(/\{\d+\}/).map(escapeRegExp).join('([\\s\\S]*?)')}$`),
    value
  }));
const cache = new Map();

export function normalizeLanguage(value) {
  return value === 'zh-CN' ? 'zh-CN' : 'en-US';
}

// Exact entries and anchored parameterized messages only: never replace words
// inside filenames, paths, GUIDs or unknown third-party diagnostic messages.
export function translate(value, language = 'en-US') {
  if (language !== 'en-US' || typeof value !== 'string') return value;
  if (cache.has(value)) return cache.get(value);
  const trimmed = value.trim();
  let translated = Object.hasOwn(english, trimmed) ? english[trimmed] : undefined;
  if (translated === undefined && /\p{Script=Han}/u.test(trimmed)) {
    for (const pattern of patterns) {
      const match = pattern.expression.exec(trimmed);
      if (match) {
        translated = pattern.value.replace(/\{(\d+)\}/g, (_, index) => match[Number(index) + 1]);
        break;
      }
    }
  }
  const result = translated === undefined ? value : value.slice(0, value.indexOf(trimmed)) + translated + value.slice(value.indexOf(trimmed) + trimmed.length);
  if (cache.size >= 1000) cache.clear();
  cache.set(value, result);
  return result;
}

export function translateDialogOptions(options, language) {
  const translated = { ...options };
  for (const key of ['title', 'message', 'detail', 'buttonLabel']) {
    if (typeof options[key] === 'string') translated[key] = translate(options[key], language);
  }
  if (Array.isArray(options.buttons)) translated.buttons = options.buttons.map((button) => translate(button, language));
  if (Array.isArray(options.filters)) translated.filters = options.filters.map((filter) => ({ ...filter, name: translate(filter.name, language) }));
  return translated;
}
