import { copyFileSync, readFileSync, writeFileSync } from 'node:fs';
import { extname, join } from 'node:path';
import hljs from 'highlight.js';
import MarkdownIt from 'markdown-it';
import type { FilePreview, HighlightedSource } from '../src/types/preview.ts';
import type { RepositoryFile, RepositorySite, RepositorySkill } from './repository.ts';

interface MarkdownEnvironment {
  directory: string;
  root: string;
  routes: ReadonlyMap<string, RepositoryFile>;
  site: RepositorySite;
}

const markdown: MarkdownIt = new MarkdownIt({ html: false, highlight: highlightCode });
const decoder = new TextDecoder('utf-8', { fatal: true });
const textPreviewLimit = 512 * 1024;
const languageAliases = new Map([
  ['mjs', 'javascript'],
  ['cjs', 'javascript'],
  ['ps1', 'powershell'],
]);

function highlightCode(code: string, language = ''): string {
  const name = language.toLowerCase();
  if (!hljs.getLanguage(name)) return markdown.utils.escapeHtml(code);
  return hljs.highlight(code, { language: name, ignoreIllegals: true }).value;
}

function renderSource(source: string, language: string): HighlightedSource {
  const normalized = source.replace(/\r\n?/g, '\n');
  return {
    content: highlightCode(normalized, language),
    lines: normalized.replace(/\n$/, '').split('\n').length,
  };
}

function previewLink(target: string, env: MarkdownEnvironment, image: boolean) {
  if (!target || /^(?:[a-z][a-z\d+.-]*:|\/\/|#)/i.test(target)) return target;
  const resolved = new URL(target, `https://repo.invalid/${env.directory}`);
  const destination = env.routes.get(resolved.pathname);
  if (image && destination?.imageName)
    return `${env.root}${destination.href}${destination.imageName}${env.site.assetQuery}`;
  if (!image && destination && !resolved.search && !resolved.hash) {
    return `${env.root}${destination.href}#preview`;
  }
  const base = image ? env.site.raw : `${env.site.github}/blob/${env.site.ref}`;
  return `${base}${resolved.pathname}${resolved.search}${resolved.hash}`;
}

for (const [rule, attribute] of [
  ['link_open', 'href'],
  ['image', 'src'],
] as const) {
  const render = markdown.renderer.rules[rule];
  markdown.renderer.rules[rule] = (tokens, index, options, env: MarkdownEnvironment, renderer) => {
    const token = tokens[index];
    const target = token?.attrGet(attribute);
    if (token && target != null) token.attrSet(attribute, previewLink(target, env, rule === 'image'));
    return render ? render(tokens, index, options, env, renderer) : renderer.renderToken(tokens, index, options);
  };
}

for (const rule of ['heading_open', 'heading_close']) {
  markdown.renderer.rules[rule] = (tokens, index, options, _env, renderer) => {
    const token = tokens[index];
    if (token) token.tag = `h${Math.min(6, Number(token.tag.slice(1)) + 2)}`;
    return renderer.renderToken(tokens, index, options);
  };
}

function renderMarkdown(
  source: string,
  file: RepositoryFile,
  routes: MarkdownEnvironment['routes'],
  site: RepositorySite,
  page: string,
  bodyOffset = 0,
): FilePreview {
  const directory = file.encodedPath.slice(0, file.encodedPath.lastIndexOf('/') + 1);
  const environment: MarkdownEnvironment = { directory, root: file.root, routes, site };
  writeFileSync(join(page, 'source.json'), JSON.stringify(renderSource(source, 'markdown')));
  return {
    kind: 'markdown',
    content: markdown.render(source.slice(bodyOffset), environment),
    sourceUrl: `./source.json${site.assetQuery}`,
  };
}

export function readPreview(
  repositoryDir: string,
  site: RepositorySite,
  skill: RepositorySkill,
  file: RepositoryFile,
  page: string,
): FilePreview {
  if (file.path === 'SKILL.md')
    return renderMarkdown(skill.entrypoint, file, skill.routes, site, page, skill.bodyOffset);
  const sourcePath = join(repositoryDir, file.repositoryPath);
  if (file.imageName) {
    copyFileSync(sourcePath, join(page, file.imageName));
    return { kind: 'image', url: `./${file.imageName}${site.assetQuery}` };
  }
  if (file.size > textPreviewLimit) return { kind: 'unavailable', reason: 'tooLarge' };

  const bytes = readFileSync(sourcePath);
  let content;
  try {
    content = decoder.decode(bytes);
  } catch {
    return { kind: 'unavailable', reason: 'unsupported' };
  }
  // eslint-disable-next-line no-control-regex -- Reject control characters that indicate binary content.
  if (/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(content)) {
    return { kind: 'unavailable', reason: 'unsupported' };
  }
  if (/\.(?:md|markdown)$/i.test(file.path)) return renderMarkdown(content, file, skill.routes, site, page);
  const extension = extname(file.path).slice(1).toLowerCase();
  return { kind: 'text', source: renderSource(content, languageAliases.get(extension) ?? extension) };
}
