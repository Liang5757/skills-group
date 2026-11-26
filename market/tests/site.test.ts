import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import {
  cpSync,
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  renameSync,
  rmSync,
  symlinkSync,
  writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { isFilePreviewData, isHighlightedSource } from '../src/lib/previewData.ts';

const market = fileURLToPath(new URL('../', import.meta.url));

test('tracked skill previews have working routes and load Markdown source separately', (t) => {
  const repository = mkdtempSync(join(tmpdir(), 'market-fixture-'));
  t.after(() => rmSync(repository, { recursive: true, force: true }));
  const fixture = join(repository, 'market');
  mkdirSync(fixture);
  for (const path of ['assets', 'build', 'build.ts', 'package.json', 'src']) {
    cpSync(join(market, path), join(fixture, path), { recursive: true });
  }
  symlinkSync(join(market, 'node_modules'), join(fixture, 'node_modules'), 'junction');

  const git = (...args: string[]) => execFileSync('git', args, { cwd: repository });
  git('init', '--quiet');
  const write = (path: string, content: string) => {
    const file = join(repository, '.agents', 'skills', 'example', path);
    mkdirSync(dirname(file), { recursive: true });
    writeFileSync(file, content);
    return file;
  };
  const guide = '中文 #1.md';
  const guideUrl = encodeURIComponent(guide);
  write(
    'SKILL.md',
    `---\nname: example\ndescription: Test skill\n# raw-source-marker\n---\n# Example\n\n[Guide](notes/${guideUrl})\n`,
  );
  const guidePath = write(`notes/${guide}`, '## Chinese file path\n\n```js\nconst example = true;\n```\n');
  git('add', '.agents/skills');
  write('local-only.md', 'Untracked file');

  const build = () =>
    execFileSync(process.execPath, ['--experimental-strip-types', join(fixture, 'build.ts')], {
      cwd: repository,
      env: { ...process.env, GITHUB_REPOSITORY: 'owner/market', GITHUB_SHA: 'test-revision' },
    });
  const dist = join(fixture, 'dist');
  const skill = join(dist, 'skills', 'example');
  const notes = join(skill, 'files', 'notes');
  const read = (...path: string[]) => readFileSync(join(...path), 'utf8');
  build();

  const html = read(skill, 'index.html');
  assert.ok(html.includes(`href="../../skills/example/files/notes/${guideUrl}/#preview"`));
  assert.doesNotMatch(html, /local-only|raw-source-marker|aria-label="SKILL.md"/);
  const preview: unknown = JSON.parse(read(skill, 'preview.json'));
  assert.ok(isFilePreviewData(preview) && preview.preview.kind === 'markdown');
  assert.equal(preview.preview.sourceUrl, './source.json?v=test-revision');
  assert.ok(!('source' in preview.preview));
  const source: unknown = JSON.parse(read(skill, 'source.json'));
  assert.ok(isHighlightedSource(source));
  assert.ok(source.content.includes('raw-source-marker'));

  const guidePreview: unknown = JSON.parse(read(notes, guide, 'preview.json'));
  assert.ok(isFilePreviewData(guidePreview));
  assert.equal(guidePreview.file.path, `notes/${guide}`);
  assert.match(read(notes, guide, 'index.html'), /<h4>Chinese file path<\/h4>/);
  assert.ok(existsSync(join(notes, guide, 'source.json')));

  renameSync(guidePath, join(dirname(guidePath), 'updated.md'));
  git('add', '-A', '.agents/skills/example/notes');
  build();
  assert.equal(existsSync(join(notes, guide)), false);
  assert.ok(existsSync(join(notes, 'updated.md', 'preview.json')));
});
