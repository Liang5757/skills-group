export const preferenceKeys = {
  locale: 'skills-market.locale',
  theme: 'skills-market.theme',
};

export function readPreference(key: string) {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

export function savePreference(key: string, value: string) {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // Preferences still apply to the current page when storage is unavailable.
  }
}
