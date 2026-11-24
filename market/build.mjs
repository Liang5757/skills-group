import { execFileSync } from 'node:child_process';
import { copyFileSync, cpSync, lstatSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { extname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import hljs from 'highlight.js';
import MarkdownIt from 'markdown-it';
import { parse } from 'yaml';
import { catalogPage, skillPage } from './pages.mjs';

const market = fileURLToPath(new URL('./', import.meta.url));
const repositoryDir = join(market, '..');
const skillsDir = '.agents/skills';
const dist = join(market, 'dist');
const repository = process.env.GITHUB_REPOSITORY || 'Liang5757/skills-group';
const ref = process.env.GITHUB_SHA || 'main';
const github = `https://github.com/${repository}`;
const raw = `https://raw.githubusercontent.com/${repository}/${ref}`;
const site = { github, repository, assetQuery: process.env.GITHUB_SHA ? `?v=${encodeURIComponent(ref)}` : '' };
const markdown = new MarkdownIt({ html: false, highlight: highlightCode });
const decoder = new TextDecoder('utf-8', { fatal: true });
const textPreviewLimit = 512 * 1024;
const imageExtension = /\.(?:avif|gif|jpe?g|png|webp)$/i;
const encodePath = (path) => path.split('/').map(encodeURIComponent).join('/');
const languageAliases = new Map([['mjs', 'javascript'], ['cjs', 'javascript'], ['ps1', 'powershell']]);

function highlightCode(code, language = '') {
  const name = language.toLowerCase();
  if (!hljs.getLanguage(name)) return markdown.utils.escapeHtml(code);
  return hljs.highlight(code, { language: name, ignoreIllegals: true }).value;
}

function previewLink(target, env, image) {
  if (!target || /^(?:[a-z][a-z\d+.-]*:|\/\/|#)/i.test(target)) return target;
  const resolved = new URL(target, `https://repo.invalid/${env.directory}`);
  const destination = env.routes.get(resolved.pathname);
  if (image && destination?.imageName) return `${env.root}${destination.href}${destination.imageName}${site.assetQuery}`;
  if (!image && destination && !resolved.search && !resolved.hash) {
    return `${env.root}${destination.href}#preview`;
  }
  const base = image ? raw : `${github}/blob/${ref}`;
  return `${base}${resolved.pathname}${resolved.search}${resolved.hash}`;
}

for (const [rule, attribute] of [['link_open', 'href'], ['image', 'src']]) {
  const render = markdown.renderer.rules[rule] ?? ((tokens, index, options, _env, renderer) =>
    renderer.renderToken(tokens, index, options));
  markdown.renderer.rules[rule] = (tokens, index, options, env, renderer) => {
    const token = tokens[index];
    token.attrSet(attribute, previewLink(token.attrGet(attribute), env, rule === 'image'));
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

function trackedSkills() {
  const files = execFileSync('git', ['ls-files', '-z', '--', `${skillsDir}/`], {
    cwd: repositoryDir,
    encoding: 'utf8',
  }).split('\0').filter(Boolean);
  const skills = new Map();
  for (const path of files) {
    const relative = path.slice(skillsDir.length + 1);
    const slash = relative.indexOf('/');
    if (slash < 0) continue;
    const stat = lstatSync(join(repositoryDir, path), { throwIfNoEntry: false });
    if (!stat?.isFile()) continue;

    const name = relative.slice(0, slash);
    if (!skills.has(name)) skills.set(name, []);
    skills.get(name).push({ path: relative.slice(slash + 1), size: stat.size });
  }
  return Array.from(skills).filter(([, files]) => files.some(({ path }) => path === 'SKILL.md'));
}

function readSkill(folder, entries) {
  const directory = `${skillsDir}/${folder}`;
  const document = readFileSync(join(repositoryDir, directory, 'SKILL.md'), 'utf8');
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

  const files = entries.map(({ path, size }) => {
    const entrypoint = path === 'SKILL.md';
    const parts = path.split('/');
    const route = ['skills', name];
    if (!entrypoint) route.push('files', ...parts);
    const repositoryPath = `${directory}/${path}`;
    const encodedPath = encodePath(repositoryPath);
    const extension = path.match(imageExtension)?.[0].toLowerCase();
    return {
      path,
      parts,
      size,
      route,
      repositoryPath,
      encodedPath,
      href: `${encodePath(route.join('/'))}/`,
      root: '../'.repeat(route.length),
      source: `${github}/blob/${ref}/${encodedPath}`,
      imageName: extension ? `image${extension}` : null,
    };
  });
  return {
    name,
    description: description.trim(),
    version: String(metadata?.version ?? '').trim(),
    command: `npx -y skills add ${repository} --skill ${name}`,
    source: `${github}/tree/${ref}/${directory}`,
    files,
    routes: new Map(files.map((file) => [`/${file.encodedPath}`, file])),
    entrypoint: document,
    bodyOffset: frontmatter[0].length,
  };
}

function renderMarkdown(source, file, routes, bodyOffset = 0) {
  const directory = file.encodedPath.slice(0, file.encodedPath.lastIndexOf('/') + 1);
  return {
    kind: 'markdown',
    content: markdown.render(source.slice(bodyOffset), { directory, root: file.root, routes }),
    source: highlightCode(source, 'markdown'),
  };
}

function readPreview(skill, file, page) {
  if (file.path === 'SKILL.md') return renderMarkdown(skill.entrypoint, file, skill.routes, skill.bodyOffset);
  const sourcePath = join(repositoryDir, file.repositoryPath);
  if (file.imageName) {
    copyFileSync(sourcePath, join(page, file.imageName));
    return { kind: 'image', url: `./${file.imageName}${site.assetQuery}` };
  }
  if (file.size > textPreviewLimit) return { kind: 'unavailable', message: '文件较大，可在 GitHub 上查看。' };

  const bytes = readFileSync(sourcePath);
  let content;
  try {
    content = decoder.decode(bytes);
  } catch {
    return { kind: 'unavailable', message: '此文件格式可在 GitHub 上查看。' };
  }
  if (/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(content)) {
    return { kind: 'unavailable', message: '此文件格式可在 GitHub 上查看。' };
  }
  if (/\.(?:md|markdown)$/i.test(file.path)) return renderMarkdown(content, file, skill.routes);
  const extension = extname(file.path).slice(1).toLowerCase();
  return { kind: 'text', content: highlightCode(content, languageAliases.get(extension) ?? extension) };
}

const skills = trackedSkills().map(([name, files]) => readSkill(name, files));

rmSync(dist, { recursive: true, force: true });
mkdirSync(dist, { recursive: true });
cpSync(join(market, 'assets'), join(dist, 'assets'), { recursive: true });
writeFileSync(join(dist, '.nojekyll'), '');
writeFileSync(join(dist, 'index.html'), catalogPage(skills, site));
for (const skill of skills) {
  for (const file of skill.files) {
    const page = join(dist, ...file.route);
    mkdirSync(page, { recursive: true });
    writeFileSync(join(page, 'index.html'), skillPage(skill, file, readPreview(skill, file, page), site));
  }
}
const previewCount = skills.reduce((count, skill) => count + skill.files.length, 0);
console.log(`Built Skill Market with ${skills.length} skills and ${previewCount} file pages.`);
