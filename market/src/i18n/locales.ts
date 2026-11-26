import english from './messages/en.ts';
import simplifiedChinese from './messages/zh-CN.ts';
import type { Messages } from './types.ts';

export const defaultLocale = 'zh-CN';
export const locales = {
  'zh-CN': { label: '简体中文', messages: simplifiedChinese },
  en: { label: 'English', messages: english },
} satisfies Record<string, { label: string; messages: Messages }>;

export type Locale = keyof typeof locales;

function isLocale(value: string | null): value is Locale {
  return value !== null && Object.hasOwn(locales, value);
}

export function normalizeLocale(locale: string | null): Locale {
  return isLocale(locale) ? locale : defaultLocale;
}
