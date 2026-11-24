const entities = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
const escapeHtml = (value) => value.replace(/[&<>"']/g, (character) => entities[character]);

function layout({ title, description, github, root, content }) {
  return `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="${escapeHtml(description)}">
  <title>${escapeHtml(title)}</title>
  <link rel="icon" type="image/png" href="${root}assets/favicon.png">
  <link rel="stylesheet" href="${root}assets/market.css">
  <script src="${root}assets/market.js" defer></script>
</head>
<body>
  <a class="skip-link" href="#main">跳到主要内容</a>
  <header class="site-header">
    <div class="frame header-inner">
      <a class="wordmark" href="${root}" aria-label="Skills Group 首页">
        <span class="brand-icon" aria-hidden="true"></span>Skills Group
      </a>
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
        <span class="skill-icon" aria-hidden="true"></span>
        ${versionBadge(skill.version)}
      </div>
      <h3 id="skill-${skill.name}">${escapeHtml(skill.name)}</h3>
      <p>${escapeHtml(skill.description)}</p>
      <span class="card-action">查看详情 <span aria-hidden="true">→</span></span>
    </a>
  </li>`;
}

export function catalogPage(skills, github) {
  return layout({
    title: 'Skill Market · Skills Group',
    description: '浏览 Skills Group 的技能，预览说明并按需安装。',
    github,
    root: './',
    content: `<main class="frame catalog" id="main">
    <section class="hero" aria-labelledby="market-title">
      <div class="hero-art" aria-hidden="true"><i></i><i></i><i></i></div>
      <div class="hero-copy">
        <h1 id="market-title" lang="en">Skill Market<span aria-hidden="true">.</span></h1>
        <p>浏览技能、预览说明，复制命令安装。</p>
      </div>
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

export function skillPage(skill, github) {
  return layout({
    title: `${skill.name} · Skill Market`,
    description: skill.description,
    github,
    root: '../../',
    content: `<main class="frame detail" id="main">
    <nav aria-label="页面导航"><a class="back-link" href="../../"><span aria-hidden="true">←</span> 全部技能</a></nav>
    <header class="skill-header">
      <div class="skill-heading">
        <span class="skill-icon" aria-hidden="true"></span>
        <h1>${escapeHtml(skill.name)}</h1>
        ${versionBadge(skill.version)}
      </div>
      <p>${escapeHtml(skill.description)}</p>
    </header>
    <div class="detail-grid">
      <aside class="install-panel" aria-labelledby="install-title">
        <h2 id="install-title">安装指引</h2>
        <p>使用 Node.js 22.20 或更高版本，在目标项目的终端执行命令，再选择要安装到的工具。</p>
        <div class="command-panel">
          <pre><code id="install-command">${escapeHtml(skill.command)}</code></pre>
          <button class="copy-button" id="copy-command" type="button" hidden>复制命令</button>
        </div>
        <span class="visually-hidden" id="copy-status" role="status"></span>
        <a class="source-link" href="${escapeHtml(skill.source)}">在 GitHub 查看原文 <span aria-hidden="true">↗</span></a>
      </aside>
      <article class="preview" aria-labelledby="preview-title">
        <h2 class="preview-title" id="preview-title">技能预览 <code>SKILL.md</code></h2>
        <div class="markdown">${skill.preview}</div>
      </article>
    </div>
  </main>`,
  });
}
