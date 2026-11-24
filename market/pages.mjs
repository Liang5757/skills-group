const entities = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
const escapeHtml = (value) => value.replace(/[&<>"']/g, (character) => entities[character]);

function layout({ title, description, site, root, content }) {
  const { github, assetQuery } = site;
  return `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="${escapeHtml(description)}">
  <title>${escapeHtml(title)}</title>
  <link rel="icon" type="image/png" href="${root}assets/favicon.png${assetQuery}">
  <link rel="stylesheet" href="${root}assets/market.css${assetQuery}">
  <script src="${root}assets/market.js${assetQuery}" defer></script>
</head>
<body>
  <a class="skip-link" href="#main">跳到主要内容</a>
  <header class="site-header">
    <div class="frame header-inner">
      <a class="wordmark" href="${root}" aria-label="Skills Group 首页">Skills Group</a>
      <a class="repository-link" href="${escapeHtml(github)}">GitHub <span aria-hidden="true">↗</span></a>
    </div>
  </header>
  ${content}
</body>
</html>`;
}

function versionBadge(version) {
  const label = version ? `v${version.replace(/^v/i, '')}` : '版本未标注';
  return `<span class="version">${escapeHtml(label)}</span>`;
}

function card(skill) {
  return `<li class="skill-card" data-skill>
    <a class="card-link" href="./skills/${skill.name}/" aria-labelledby="skill-${skill.name}">
      <div class="card-top">
        <h3 id="skill-${skill.name}">${escapeHtml(skill.name)}</h3>
        ${versionBadge(skill.version)}
      </div>
      <p>${escapeHtml(skill.description)}</p>
      <span class="card-action">查看详情 <span aria-hidden="true">→</span></span>
    </a>
  </li>`;
}

export function catalogPage(skills, site) {
  return layout({
    title: 'Skill Market · Skills Group',
    description: '浏览 Skills Group 的技能，预览说明并按需安装。',
    site,
    root: './',
    content: `<main class="frame catalog" id="main">
    <section class="hero" aria-labelledby="market-title">
      <h1 id="market-title" lang="en">Skill Market</h1>
      <p>浏览技能、预览文件，复制命令安装。</p>
    </section>
    <section class="catalog-list" aria-labelledby="catalog-title">
      <div class="catalog-toolbar">
        <div class="catalog-title">
          <h2 id="catalog-title">全部技能</h2>
          <span class="skill-count" id="skill-count" role="status">${skills.length} 个</span>
        </div>
        <label class="search" hidden>
          <span class="search-icon" aria-hidden="true"></span>
          <input type="search" id="skill-search" aria-label="搜索技能名称或描述" placeholder="搜索技能名称或描述" autocomplete="off">
        </label>
      </div>
      <ul class="skill-grid">${skills.map(card).join('\n')}</ul>
      <div class="empty-state" id="search-empty" hidden>
        <p>没有找到匹配的技能。</p>
        <button class="text-button" type="button" id="clear-search">清除搜索</button>
      </div>
    </section>
  </main>`,
  });
}

function fileTree(files, current, depth = 0) {
  const folders = new Map();
  const visibleFiles = [];
  for (const file of files) {
    if (file.parts.length === depth + 1) {
      if (file.path === 'SKILL.md') visibleFiles.unshift(file);
      else visibleFiles.push(file);
      continue;
    }
    const folder = file.parts[depth];
    if (!folders.has(folder)) folders.set(folder, []);
    folders.get(folder).push(file);
  }

  const fileLinks = visibleFiles.map((file) => {
    const href = escapeHtml(`${current.root}${file.href}#preview`);
    const active = file.path === current.path ? ' aria-current="page"' : '';
    return `<li><a href="${href}"${active}>${escapeHtml(file.parts[depth])}</a></li>`;
  });
  const folderLinks = Array.from(folders, ([folder, children]) => {
    const open = children.some((file) => file.path === current.path) ? ' open' : '';
    return `<li><details${open}><summary>${escapeHtml(folder)}</summary>${fileTree(children, current, depth + 1)}</details></li>`;
  });
  return `<ul>${fileLinks.join('')}${folderLinks.join('')}</ul>`;
}

function sourceCode(file, content, hidden = false) {
  return `<pre class="source-code" tabindex="0" aria-label="${escapeHtml(file.path)}"${hidden ? ' hidden' : ''}><code>${content}</code></pre>`;
}

function filePreview(file, preview) {
  switch (preview.kind) {
    case 'markdown':
      return `<div class="markdown">${preview.content}</div>${sourceCode(file, preview.source, true)}`;
    case 'text':
      return sourceCode(file, preview.content);
    case 'image':
      return `<div class="image-preview"><img src="${escapeHtml(preview.url)}" alt="${escapeHtml(file.path)}"></div>`;
    default:
      return `<p class="preview-message">${escapeHtml(preview.message)}</p>`;
  }
}

export function skillPage(skill, file, preview, site) {
  return layout({
    title: file.path === 'SKILL.md' ? `${skill.name} · Skill Market` : `${file.path} · ${skill.name} · Skill Market`,
    description: skill.description,
    site,
    root: file.root,
    content: `<main class="frame detail" id="main">
    <nav aria-label="页面导航"><a class="back-link" href="${file.root}"><span aria-hidden="true">←</span> 全部技能</a></nav>
    <div class="skill-header">
      <header class="skill-summary">
        <div class="skill-heading">
          <h1>${escapeHtml(skill.name)}</h1>
          ${versionBadge(skill.version)}
        </div>
        <p>${escapeHtml(skill.description)}</p>
      </header>
      <aside class="install-panel" aria-labelledby="install-title">
        <h2 id="install-title">安装指引</h2>
        <p>在目标项目的终端运行命令。需要 Node.js 22.20 或更新版本。</p>
        <div class="command-panel">
          <pre><code id="install-command">${escapeHtml(skill.command)}</code></pre>
          <button class="copy-button" id="copy-command" type="button" hidden>复制命令</button>
        </div>
        <span class="visually-hidden" id="copy-status" role="status"></span>
      </aside>
    </div>
    <div class="detail-grid">
      <nav class="file-panel" aria-labelledby="file-title">
        <h2 id="file-title">技能文件</h2>
        <div class="file-tree">${fileTree(skill.files, file)}</div>
      </nav>
      <span class="visually-hidden" id="file-status" role="status"></span>
      <article class="preview" id="preview" aria-labelledby="preview-title">
        <header class="preview-bar">
          <h2 id="preview-title"><code>${escapeHtml(file.path)}</code></h2>
          <div class="preview-actions">
            ${preview.kind === 'markdown' ? `<div class="preview-modes" role="group" aria-label="Markdown 查看方式" hidden>
              <button type="button" data-markdown-mode="preview" aria-pressed="true">预览</button>
              <button type="button" data-markdown-mode="source" aria-pressed="false">源码</button>
            </div>` : ''}
            <a class="source-link" href="${escapeHtml(file.source)}">在 GitHub 查看 <span aria-hidden="true">↗</span></a>
          </div>
        </header>
        ${filePreview(file, preview)}
      </article>
    </div>
  </main>`,
  });
}
