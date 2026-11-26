import type { SkillListing } from '../types/skill.ts';

const pageSize = 30;

interface CatalogEntry {
  skill: SkillListing;
  text: string;
}

export function createCatalogIndex(skills: readonly SkillListing[]): CatalogEntry[] {
  return skills.map((skill) => ({
    skill,
    text: `${skill.name} ${skill.description}`.toLowerCase(),
  }));
}

export function readCatalogPage(index: readonly CatalogEntry[], query: string, page: number) {
  const terms = query.trim().toLowerCase().split(/\s+/);
  const matches = index.filter(({ text }) => terms.every((term) => text.includes(term)));
  const pageCount = Math.max(1, Math.ceil(matches.length / pageSize));
  const current = Math.min(pageCount, Math.max(1, Number.isSafeInteger(page) ? page : 1));
  const start = (current - 1) * pageSize;
  return { matches, current, pageCount, visible: new Set(matches.slice(start, start + pageSize)) };
}
