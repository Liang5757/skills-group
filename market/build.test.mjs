import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, renameSync, rmSync, symlinkSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { test } from 'node:test';

const market = fileURLToPath(new URL('./', import.meta.url));

test('the market follows tracked skill files across builds', (t) => {
  const repository = mkdtempSync(join(tmpdir(), 'market-build-'));
  t.after(() => rmSync(repository, { recursive: true, force: true }));
  const fixtureMarket = join(repository, 'market');
  mkdirSync(fixtureMarket);
  for (const name of ['build.mjs', 'pages.mjs', 'assets']) {
    cpSync(join(market, name), join(fixtureMarket, name), { recursive: true });
  }
  symlinkSync(join(market, 'node_modules'), join(fixtureMarket, 'node_modules'), 'dir');

  const git = (...args) => execFileSync('git', args, { cwd: repository });
  git('init', '--quiet');
  const write = (path, content) => {
    const destination = join(repository, '.agents', 'skills', path);
    mkdirSync(dirname(destination), { recursive: true });
    writeFileSync(destination, content);
    return destination;
  };
  const entry = (name, version, body) => `---\nname: ${name}\ndescription: Example skill\nmetadata:\n  version: ${version}\n---\n${body}`;

  write('example/SKILL.md', entry('example', '1.0.0', '# Example\n\n[Guide](notes/%E4%B8%AD%E6%96%87%20%231.md)'));
  const guide = write('example/notes/中文 #1.md', '## First draft\n\n```bash\necho "example"\n```');
  write('example/parse.py', 'def greet():\n    return "hello"\n');
  write('example/.settings', '<script>doNotRun()</script>');
  write('example/preview.png', readFileSync(join(market, 'assets', 'favicon.png')));
  write('example/data.bin', Buffer.from([0, 255]));
  git('add', '.agents/skills');
  write('example/local-only.txt', 'untracked');

  const build = () => execFileSync(process.execPath, [join(fixtureMarket, 'build.mjs')], {
    cwd: repository,
    env: { ...process.env, GITHUB_REPOSITORY: 'owner/market', GITHUB_SHA: 'test-revision' },
  });
  const dist = join(fixtureMarket, 'dist');
  const page = (...parts) => readFileSync(join(dist, ...parts, 'index.html'), 'utf8');

  build();
  const skillPage = page('skills', 'example');
  assert.match(page(), /v1\.0\.0/);
  assert.match(skillPage, /href="\.\.\/\.\.\/skills\/example\/files\/notes\/%E4%B8%AD%E6%96%87%20%231\.md\/#preview">Guide<\/a>/);
  assert.doesNotMatch(skillPage, /local-only/);
  const guidePage = page('skills', 'example', 'files', 'notes', '中文 #1.md');
  assert.match(guidePage, /<details open>/);
  assert.match(guidePage, /<h4>First draft<\/h4>/);
  assert.match(guidePage, /<code class="language-bash"><span class="hljs-built_in">echo<\/span>/);
  assert.match(guidePage, /<pre class="source-code"[^>]* hidden><code><span class="hljs-section">## First draft<\/span>/);
  assert.match(page('skills', 'example', 'files', 'parse.py'), /<span class="hljs-keyword">def<\/span>/);
  assert.match(page('skills', 'example', 'files', '.settings'), /&lt;script&gt;doNotRun\(\)&lt;\/script&gt;/);
  assert.match(page('skills', 'example', 'files', 'preview.png'), /src="\.\/image\.png\?v=test-revision"/);
  assert.match(page('skills', 'example', 'files', 'data.bin'), /在 GitHub 上查看/);
  assert.ok(existsSync(join(dist, 'skills', 'example', 'files', 'preview.png', 'image.png')));

  const renamed = join(dirname(guide), 'new.md');
  renameSync(guide, renamed);
  writeFileSync(renamed, '# Revised content');
  write('example/SKILL.md', entry('example', '1.1.0', '# Example\n\n[Guide](notes/new.md)'));
  write('new-skill/SKILL.md', entry('new-skill', '1.0.0', '# New skill'));
  rmSync(join(repository, '.agents', 'skills', 'example', 'data.bin'));
  git('add', '-A', '.agents/skills');

  build();
  assert.match(page(), /v1\.1\.0/);
  assert.match(page(), /new-skill/);
  assert.match(page('skills', 'example', 'files', 'notes', 'new.md'), /<h3>Revised content<\/h3>/);
  assert.doesNotMatch(page('skills', 'example'), /data\.bin|%E4%B8%AD%E6%96%87/);
  assert.equal(existsSync(join(dist, 'skills', 'example', 'files', 'notes', '中文 #1.md')), false);
  assert.equal(existsSync(join(dist, 'skills', 'example', 'files', 'data.bin')), false);
});
