import type { Messages } from '../i18n/types.ts';
import type { PreviewFile } from '../types/preview.ts';
import type { SkillListing } from '../types/skill.ts';

export interface SkillMetadata {
  skill: SkillListing;
  file: PreviewFile;
}

export function pageMetadata(messages: Messages, metadata?: SkillMetadata) {
  const { market } = messages.header;
  if (!metadata) {
    return { title: `${market} · Skills Group`, description: messages.catalog.metaDescription };
  }
  const { skill, file } = metadata;
  const subject = file.path === 'SKILL.md' ? skill.name : `${file.path} · ${skill.name}`;
  return { title: `${subject} · ${market}`, description: skill.description };
}
