import { cpSync, mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import MarkdownIt from 'markdown-it';
import { parse } from 'yaml';
import { catalogPage, skillPage } from './pages.mjs';

const market = fileURLToPath(new URL('./', import.meta.url));
const skillsDir = join(market, '..', '.agents', 'skills');
const dist = join(market, 'dist');
const repository = process.env.GITHUB_REPOSITORY || 'Liang5757/skills-group';
const ref = process.env.GITHUB_SHA || 'main';
const github = `https://github.com/${repository}`;
const raw = `https://raw.githubusercontent.com/${repository}/${ref}`;
const markdown = new MarkdownIt({ html: false });

function repositoryLink(target, directory, base) {
  if (!target || /^(?:[a-z][a-z\d+.-]*:|\/\/|#)/i.test(target)) return target;
  const resolved = new URL(target, `https://repo.invalid/${directory}/`);
  return `${base}${resolved.pathname}${resolved.search}${resolved.hash}`;
}

for (const [rule, attribute] of [['link_open', 'href'], ['image', 'src']]) {
  const render = markdown.renderer.rules[rule] ?? ((tokens, index, options, _env, renderer) =>
    renderer.renderToken(tokens, index, options));
  markdown.renderer.rules[rule] = (tokens, index, options, env, renderer) => {
    const token = tokens[index];
    const base = rule === 'image' ? raw : `${github}/blob/${ref}`;
    token.attrSet(attribute, repositoryLink(token.attrGet(attribute), env.directory, base));
    return render(tokens, index, options, env, renderer);
  };
}

for (const rule of ['heading_open', 'heading_close']) {
  markdown.renderer.rules[rule] = (tokens, index, options, _env, renderer) => {
    const token = tokens[index];
    token.tag = `h${Math.min(6, Number(token.tag.slice(1)) + 2)}`;
    return renderer.renderToken(tokens, index, options);
  };
}

function readSkill(folder) {
  const document = readFileSync(join(skillsDir, folder, 'SKILL.md'), 'utf8');
  const frontmatter = document.match(/^\uFEFF?---[ \t]*\r?\n([\s\S]*?)\r?\n---[ \t]*(?:\r?\n|$)/);
  if (!frontmatter) throw new Error(`${folder}/SKILL.md is missing YAML frontmatter`);

  const data = parse(frontmatter[1]);
  const { name, description, metadata } = data ?? {};
  if (name !== folder || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(name)) {
    throw new Error(`${folder}/SKILL.md must use its directory name in frontmatter`);
  }
  if (typeof description !== 'string' || !description.trim()) {
    throw new Error(`${folder}/SKILL.md needs a description`);
  }

  const directory = `.agents/skills/${folder}`;
  return {
    name,
    description: description.trim(),
    version: String(metadata?.version ?? '').trim(),
    command: `npx -y skills add ${repository} --skill ${name}`,
    source: `${github}/blob/${ref}/${directory}/SKILL.md`,
    preview: markdown.render(document.slice(frontmatter[0].length), { directory }),
  };
}

const skills = readdirSync(skillsDir, { withFileTypes: true })
  .filter((entry) => entry.isDirectory() && !entry.name.startsWith('.'))
  .map((entry) => entry.name)
  .sort()
  .map(readSkill);

rmSync(dist, { recursive: true, force: true });
mkdirSync(dist, { recursive: true });
cpSync(join(market, 'assets'), join(dist, 'assets'), { recursive: true });
writeFileSync(join(dist, '.nojekyll'), '');
writeFileSync(join(dist, 'index.html'), catalogPage(skills, github));
for (const skill of skills) {
  const page = join(dist, 'skills', skill.name);
  mkdirSync(page, { recursive: true });
  writeFileSync(join(page, 'index.html'), skillPage(skill, github));
}
console.log(`Built Skill Market with ${skills.length} skills.`);
