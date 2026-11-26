import { createContext, useContext } from 'react';
import { defaultLocale, locales } from './locales.ts';
import type { Messages } from './types.ts';

export const LocaleContext = createContext<Messages>(locales[defaultLocale].messages);

export function useMessages() {
  return useContext(LocaleContext);
}
