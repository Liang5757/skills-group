import { preferenceKeys, readPreference } from '../preferences/storage.ts';

export const defaultTheme = 'dark';
export const themes = ['dark', 'light'] as const;

export type Theme = (typeof themes)[number];

export function isTheme(value: string | null): value is Theme {
  return themes.some((theme) => theme === value);
}

export function readTheme(): Theme {
  const saved = readPreference(preferenceKeys.theme);
  return isTheme(saved) ? saved : defaultTheme;
}

export function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
}
