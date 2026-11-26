import { CheckIcon, ChevronDownIcon, GlobeIcon, MoonIcon, SunIcon } from '@radix-ui/react-icons';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import * as Toggle from '@radix-ui/react-toggle';
import { useMessages } from '../../i18n/context.ts';
import { locales } from '../../i18n/locales.ts';
import { usePreferences } from '../../preferences/PreferencesProvider.tsx';
import styles from './PreferenceControls.module.css';
import controls from '../../styles/controls.module.css';

export function PreferenceControls() {
  const { preferences } = useMessages();
  const { ready, locale, theme, changeLocale, changeTheme } = usePreferences();
  const isDark = theme === 'dark';
  const nextTheme = isDark ? 'light' : 'dark';
  const ThemeIcon = isDark ? SunIcon : MoonIcon;

  return (
    <div className={styles.displayPreferences} role="group" aria-label={preferences.label} hidden={!ready}>
      <DropdownMenu.Root modal={false}>
        <DropdownMenu.Trigger
          className={`${controls.button} ${styles.languageTrigger}`}
          aria-label={preferences.language}
          title={preferences.language}
        >
          <GlobeIcon className={controls.buttonGlyph} aria-hidden="true" />
          <span className={styles.languageLabel} lang={locale}>
            {locales[locale].label}
          </span>
          <ChevronDownIcon className={`${controls.buttonGlyph} ${styles.languageChevron}`} aria-hidden="true" />
        </DropdownMenu.Trigger>
        <DropdownMenu.Portal>
          <DropdownMenu.Content className={controls.menu} align="end" sideOffset={8} collisionPadding={12}>
            <DropdownMenu.Label className={controls.menuLabel}>{preferences.language}</DropdownMenu.Label>
            <DropdownMenu.RadioGroup value={locale} onValueChange={changeLocale}>
              {Object.entries(locales).map(([value, { label }]) => (
                <DropdownMenu.RadioItem key={value} className={controls.menuItem} value={value} lang={value}>
                  {label}
                  <DropdownMenu.ItemIndicator className={controls.menuIndicator}>
                    <CheckIcon aria-hidden="true" />
                  </DropdownMenu.ItemIndicator>
                </DropdownMenu.RadioItem>
              ))}
            </DropdownMenu.RadioGroup>
          </DropdownMenu.Content>
        </DropdownMenu.Portal>
      </DropdownMenu.Root>
      <Toggle.Root
        className={`${controls.button} ${controls.buttonIcon}`}
        pressed={isDark}
        onPressedChange={(pressed) => changeTheme(pressed ? 'dark' : 'light')}
        aria-label={preferences.darkMode}
        title={preferences.switchTheme(preferences.themes[nextTheme])}
      >
        <ThemeIcon className={controls.buttonGlyph} aria-hidden="true" />
      </Toggle.Root>
    </div>
  );
}
