import { useEffect } from 'react';
import type { Messages } from '../i18n/types.ts';
import { pageMetadata } from '../lib/pageMetadata.ts';
import type { SkillMetadata } from '../lib/pageMetadata.ts';

export function usePageMetadata(messages: Messages, metadata?: SkillMetadata) {
  const { title, description } = pageMetadata(messages, metadata);
  useEffect(() => {
    document.title = title;
    document.querySelector('meta[name="description"]')?.setAttribute('content', description);
  }, [title, description]);
}
