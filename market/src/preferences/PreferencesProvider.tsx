import { createContext, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { LocaleContext } from '../i18n/context.ts';
import { defaultLocale, locales, normalizeLocale } from '../i18n/locales.ts';
import type { Locale } from '../i18n/locales.ts';
import { preferenceKeys, readPreference, savePreference } from './storage.ts';
import { applyTheme, defaultTheme, isTheme, readTheme } from '../theme/theme.ts';
import type { Theme } from '../theme/theme.ts';

interface Preferences {
  locale: Locale;
  theme: Theme;
}

interface PreferencesContextValue extends Preferences {
  ready: boolean;
  changeLocale: (value: string) => void;
  changeTheme: (value: Theme) => void;
}

const PreferencesContext = createContext<PreferencesContextValue | null>(null);
const defaults: Preferences = { locale: defaultLocale, theme: defaultTheme };

export function usePreferences() {
  const preferences = useContext(PreferencesContext);
  if (!preferences) throw new Error('PreferencesProvider is missing');
  return preferences;
}

export function PreferencesProvider({ children }: { children: ReactNode }) {
  const [saved, setSaved] = useState<Preferences | null>(null);
  const { locale, theme } = saved ?? defaults;

  useEffect(() => {
    function restore() {
      setSaved({
        locale: normalizeLocale(readPreference(preferenceKeys.locale)),
        theme: readTheme(),
      });
    }

    function syncStorage(event: StorageEvent) {
      if (!event.key || Object.values(preferenceKeys).includes(event.key)) restore();
    }

    restore();
    window.addEventListener('pageshow', restore);
    window.addEventListener('storage', syncStorage);
    return () => {
      window.removeEventListener('pageshow', restore);
      window.removeEventListener('storage', syncStorage);
    };
  }, []);

  useEffect(() => {
    if (!saved) return;
    document.documentElement.lang = locale;
    applyTheme(theme);
  }, [saved, locale, theme]);

  function changeLocale(value: string) {
    const next = normalizeLocale(value);
    savePreference(preferenceKeys.locale, next);
    setSaved((previous) => ({ ...(previous ?? defaults), locale: next }));
  }

  function changeTheme(value: Theme) {
    if (!isTheme(value)) return;
    savePreference(preferenceKeys.theme, value);
    setSaved((previous) => ({ ...(previous ?? defaults), theme: value }));
  }

  return (
    <LocaleContext.Provider value={locales[locale].messages}>
      <PreferencesContext.Provider value={{ ready: !!saved, locale, theme, changeLocale, changeTheme }}>
        {children}
      </PreferencesContext.Provider>
    </LocaleContext.Provider>
  );
}
