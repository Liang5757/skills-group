export interface SkillListing {
  name: string;
  description: string;
  version: string;
}

export interface SkillFileLink {
  path: string;
  href: string;
}

export interface SkillDetails extends SkillListing {
  command: string;
  source: string;
  files: readonly SkillFileLink[];
}
