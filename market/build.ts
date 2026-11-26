import { copyFileSync, mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';
import { readPreview } from './build/preview.ts';
import { readRepository } from './build/repository.ts';
import type { RepositorySite } from './build/repository.ts';
import type { PublicSite } from './src/types/page.ts';
import type { FilePreviewData } from './src/types/preview.ts';
import type { SkillDetails, SkillListing } from './src/types/skill.ts';

const market = fileURLToPath(new URL('./', import.meta.url));
const repositoryDir = join(market, '..');
const dist = join(market, 'dist');
const repository = process.env.GITHUB_REPOSITORY || 'Liang5757/skills-group';
const ref = process.env.GITHUB_SHA || 'main';
const site: RepositorySite = {
  repository,
  ref,
  github: `https://github.com/${repository}`,
  raw: `https://raw.githubusercontent.com/${repository}/${ref}`,
  assetQuery: process.env.GITHUB_SHA ? `?v=${encodeURIComponent(ref)}` : '',
};
const publicSite: PublicSite = { github: site.github, repository, assetQuery: site.assetQuery };

function skillSummary({ name, description, version }: SkillListing): SkillListing {
  return { name, description, version };
}

const skills = readRepository(repositoryDir, site);
const assets = join(dist, 'assets');
const intermediate = join(dist, '.build');
rmSync(dist, { recursive: true, force: true });
mkdirSync(assets, { recursive: true });
copyFileSync(join(market, 'assets', 'favicon.png'), join(assets, 'favicon.png'));

try {
  // Allocate CSS Module names once so the static markup and hydrated UI share them.
  const [, themeInit] = await Promise.all([
    build({
      entryPoints: [join(market, 'src', 'app', 'client.tsx'), join(market, 'src', 'app', 'render.tsx')],
      outdir: intermediate,
      outExtension: { '.js': '.mjs' },
      bundle: true,
      splitting: true,
      minifySyntax: true,
      minifyWhitespace: true,
      jsx: 'automatic',
      platform: 'neutral',
      packages: 'external',
      format: 'esm',
    }),
    build({
      entryPoints: [join(market, 'src', 'theme', 'init.ts')],
      bundle: true,
      minify: true,
      format: 'iife',
      write: false,
    }),
  ]);
  await build({
    entryPoints: [join(intermediate, 'client.mjs')],
    outfile: join(assets, 'market.js'),
    bundle: true,
    minify: true,
    format: 'esm',
  });
  copyFileSync(join(intermediate, 'client.css'), join(assets, 'market.css'));

  const renderer = join(intermediate, 'render.mjs');
  const { renderPage }: typeof import('./src/app/render.tsx') = await import(pathToFileURL(renderer).href);
  const themeScript = themeInit.outputFiles?.[0]?.text;
  if (!themeScript) throw new Error('Theme initialization script was not generated');
  writeFileSync(join(dist, '.nojekyll'), '');
  writeFileSync(
    join(dist, 'index.html'),
    renderPage(
      {
        kind: 'catalog',
        site: publicSite,
        root: './',
        skills: skills.map(skillSummary),
      },
      themeScript,
    ),
  );

  for (const skill of skills) {
    const summary: SkillDetails = {
      ...skillSummary(skill),
      command: skill.command,
      source: skill.source,
      files: skill.files.map(({ path, href }) => ({ path, href })),
    };
    for (const file of skill.files) {
      const directory = join(dist, ...file.route);
      mkdirSync(directory, { recursive: true });
      const initial: FilePreviewData = {
        file: { path: file.path, source: file.source },
        preview: readPreview(repositoryDir, site, skill, file, directory),
      };
      writeFileSync(join(directory, 'preview.json'), JSON.stringify(initial));
      writeFileSync(
        join(directory, 'index.html'),
        renderPage(
          {
            kind: 'skill',
            site: publicSite,
            root: file.root,
            skill: summary,
            initial,
          },
          themeScript,
        ),
      );
    }
  }
} finally {
  rmSync(intermediate, { recursive: true, force: true });
}

const previewCount = skills.reduce((count, skill) => count + skill.files.length, 0);
console.log(`Built Skill Market with ${skills.length} skills and ${previewCount} file pages.`);
