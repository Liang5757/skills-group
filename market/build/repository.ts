import { execFileSync } from 'node:child_process';
import { lstatSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { parse } from 'yaml';
import { isRecord } from '../src/lib/isRecord.ts';
import type { PublicSite } from '../src/types/page.ts';
import type { SkillDetails, SkillFileLink } from '../src/types/skill.ts';

export interface RepositorySite extends PublicSite {
  ref: string;
  raw: string;
}

interface TrackedFile {
  path: string;
  size: number;
}

export interface RepositoryFile extends TrackedFile, SkillFileLink {
  route: string[];
  repositoryPath: string;
  encodedPath: string;
  root: string;
  source: string;
  imageName: string | null;
}

export interface RepositorySkill extends SkillDetails {
  files: RepositoryFile[];
  routes: ReadonlyMap<string, RepositoryFile>;
  entrypoint: string;
  bodyOffset: number;
}

const skillsDir = '.agents/skills';
const imageExtension = /\.(?:avif|gif|jpe?g|png|webp)$/i;
const encodePath = (path: string) => path.split('/').map(encodeURIComponent).join('/');

function trackedSkills(repositoryDir: string) {
  const files = execFileSync('git', ['ls-files', '-z', '--', `${skillsDir}/`], {
    cwd: repositoryDir,
    encoding: 'utf8',
  })
    .split('\0')
    .filter(Boolean);
  const skills = new Map<string, TrackedFile[]>();
  for (const path of files) {
    const relative = path.slice(skillsDir.length + 1);
    const slash = relative.indexOf('/');
    if (slash < 0) continue;
    const stat = lstatSync(join(repositoryDir, path), { throwIfNoEntry: false });
    if (!stat?.isFile()) continue;

    const name = relative.slice(0, slash);
    const entry = { path: relative.slice(slash + 1), size: stat.size };
    const entries = skills.get(name);
    if (entries) entries.push(entry);
    else skills.set(name, [entry]);
  }
  return Array.from(skills).filter(([, files]) => files.some(({ path }) => path === 'SKILL.md'));
}

function readSkill(
  repositoryDir: string,
  site: RepositorySite,
  folder: string,
  entries: TrackedFile[],
): RepositorySkill {
  const directory = `${skillsDir}/${folder}`;
  const document = readFileSync(join(repositoryDir, directory, 'SKILL.md'), 'utf8');
  const frontmatter = document.match(/^\uFEFF?---[ \t]*\r?\n([\s\S]*?)\r?\n---[ \t]*(?:\r?\n|$)/);
  if (frontmatter?.[1] === undefined) throw new Error(`${folder}/SKILL.md is missing YAML frontmatter`);

  const data: unknown = parse(frontmatter[1]);
  const { name, description, metadata } = isRecord(data) ? data : {};
  if (name !== folder || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(name)) {
    throw new Error(`${folder}/SKILL.md must use its directory name in frontmatter`);
  }
  if (typeof description !== 'string' || !description.trim()) {
    throw new Error(`${folder}/SKILL.md needs a description`);
  }

  const files = entries.map(({ path, size }) => {
    const entrypoint = path === 'SKILL.md';
    const route = ['skills', name];
    if (!entrypoint) route.push('files', ...path.split('/'));
    const repositoryPath = `${directory}/${path}`;
    const encodedPath = encodePath(repositoryPath);
    const extension = path.match(imageExtension)?.[0]?.toLowerCase();
    return {
      path,
      size,
      route,
      repositoryPath,
      encodedPath,
      href: `${encodePath(route.join('/'))}/`,
      root: '../'.repeat(route.length),
      source: `${site.github}/blob/${site.ref}/${encodedPath}`,
      imageName: extension ? `image${extension}` : null,
    };
  });
  return {
    name,
    description: description.trim(),
    version: String((isRecord(metadata) ? metadata.version : undefined) ?? '').trim(),
    command: `npx -y skills add ${site.repository} --skill ${name}`,
    source: `${site.github}/tree/${site.ref}/${directory}`,
    files,
    routes: new Map(files.map((file) => [`/${file.encodedPath}`, file])),
    entrypoint: document,
    bodyOffset: frontmatter[0].length,
  };
}

export function readRepository(repositoryDir: string, site: RepositorySite): RepositorySkill[] {
  return trackedSkills(repositoryDir).map(([name, files]) => readSkill(repositoryDir, site, name, files));
}
