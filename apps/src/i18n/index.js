import { ref } from 'vue';
import { normalizeLanguage, translate } from '../../electron/localization.mjs';

export const locale = ref('en-US');
export const supportedLocales = ['en-US', 'zh-CN'];

export function setLocale(value) {
  locale.value = normalizeLanguage(value);
  if (typeof document !== 'undefined') document.documentElement.lang = locale.value;
}

export function t(value) {
  return translate(value, locale.value);
}

export function installI18n(app) {
  app.config.globalProperties.$t = t;
  setLocale(locale.value);
}
