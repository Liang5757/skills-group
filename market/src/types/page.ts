import type { FilePreviewData } from './preview.ts';
import type { SkillDetails, SkillListing } from './skill.ts';

export interface PublicSite {
  repository: string;
  github: string;
  assetQuery: string;
}

interface PageBase {
  site: PublicSite;
  root: string;
}

export interface CatalogPageData extends PageBase {
  kind: 'catalog';
  skills: readonly SkillListing[];
}

export interface SkillPageData extends PageBase {
  kind: 'skill';
  skill: SkillDetails;
  initial: FilePreviewData;
}

export type MarketPage = CatalogPageData | SkillPageData;
