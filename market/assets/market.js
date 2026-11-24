const search = document.querySelector('#skill-search');

if (search) {
  const cards = Array.from(document.querySelectorAll('[data-skill]'), (element) => ({
    element,
    text: element.querySelector('h3').textContent.concat(' ', element.querySelector('p').textContent).toLowerCase(),
  }));
  const count = document.querySelector('#skill-count');
  const empty = document.querySelector('#search-empty');

  function updateSearch() {
    const terms = search.value.trim().toLowerCase().split(/\s+/);
    let matches = 0;
    for (const { element, text } of cards) {
      const visible = terms.every((term) => text.includes(term));
      element.hidden = !visible;
      if (visible) matches += 1;
    }
    const label = `${matches} 个`;
    if (count.textContent !== label) count.textContent = label;
    empty.hidden = matches > 0;
  }

  search.closest('label').hidden = false;
  search.addEventListener('input', updateSearch);
  document.querySelector('#clear-search').addEventListener('click', () => {
    search.value = '';
    search.focus();
    updateSearch();
  });
  window.addEventListener('pageshow', updateSearch);
  updateSearch();
}

const copy = document.querySelector('#copy-command');

if (copy) {
  const command = document.querySelector('#install-command');
  const status = document.querySelector('#copy-status');
  let reset;
  copy.hidden = false;

  copy.addEventListener('click', async () => {
    window.clearTimeout(reset);
    try {
      await navigator.clipboard.writeText(command.textContent);
      copy.textContent = '已复制';
      status.textContent = '安装命令已复制';
    } catch {
      const range = document.createRange();
      range.selectNodeContents(command);
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
      copy.textContent = '请手动复制';
      status.textContent = '安装命令已选中，请手动复制';
    }
    reset = window.setTimeout(() => {
      copy.textContent = '复制命令';
      status.textContent = '';
    }, 2500);
  });
}

const preview = document.querySelector('#preview');

if (preview) {
  const status = document.querySelector('#file-status');
  const fileTree = document.querySelector('.file-tree');
  const filePanel = fileTree.closest('details');
  let currentPath = window.location.pathname;
  let request;

  function resolveLinks(container, base) {
    for (const element of container.querySelectorAll('a[href], link[href], img[src]')) {
      const attribute = element.matches('img') ? 'src' : 'href';
      const destination = element.getAttribute(attribute);
      if (!/^(?:[a-z][a-z\d+.-]*:|\/\/|#)/i.test(destination)) {
        element.setAttribute(attribute, new URL(destination, base).href);
      }
    }
  }

  function showMarkdownModes() {
    const modes = preview.querySelector('.preview-modes');
    if (modes) modes.hidden = false;
  }

  function revealPreview() {
    const { top } = preview.getBoundingClientRect();
    if (top < 0 || top > window.innerHeight - 100) preview.scrollIntoView({ block: 'start' });
  }

  // The page shell keeps its original links when the address changes to a nested file.
  resolveLinks(document, window.location.href);
  const links = new Map(Array.from(fileTree.querySelectorAll('a'), (link) => [link.pathname, link]));
  showMarkdownModes();

  document.querySelector('#main').addEventListener('click', async (event) => {
    const mode = event.target.closest('[data-markdown-mode]');
    if (mode) {
      const showSource = mode.dataset.markdownMode === 'source';
      preview.querySelector('.markdown').hidden = showSource;
      preview.querySelector('.source-code').hidden = !showSource;
      for (const button of mode.parentElement.querySelectorAll('button')) {
        button.setAttribute('aria-pressed', String(button === mode));
      }
      return;
    }

    const link = event.target.closest('a[href]');
    if (!link || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    if (link.target || link.origin !== window.location.origin || link.hash !== '#preview') return;
    const selected = links.get(link.pathname);
    if (!selected) return;

    event.preventDefault();
    request?.abort();
    if (link.pathname === currentPath) {
      request = undefined;
      preview.removeAttribute('aria-busy');
      revealPreview();
      return;
    }

    const url = new URL(link.href);
    url.hash = '';
    const controller = new AbortController();
    request = controller;
    preview.setAttribute('aria-busy', 'true');
    try {
      const response = await fetch(url, { signal: controller.signal });
      if (!response.ok) throw new Error(`Preview returned ${response.status}`);
      const page = document.createElement('template');
      page.innerHTML = await response.text();
      if (controller.signal.aborted) return;
      const next = page.content.querySelector('#preview');
      if (!next) throw new Error('Preview is missing');

      resolveLinks(next, response.url);
      const focusTree = preview.contains(link) && event.detail === 0;
      window.history.replaceState(window.history.state, '', url);
      document.title = page.content.querySelector('title').textContent;
      preview.replaceChildren(...next.childNodes);
      links.get(currentPath)?.removeAttribute('aria-current');
      selected.setAttribute('aria-current', 'page');
      currentPath = url.pathname;
      for (let folder = selected.closest('details'); folder && fileTree.contains(folder); folder = folder.parentElement.closest('details')) {
        folder.open = true;
      }
      showMarkdownModes();
      revealPreview();
      if (focusTree) {
        const focusTarget = filePanel.open ? selected : filePanel.querySelector('summary');
        focusTarget.focus({ preventScroll: true });
      }
      status.textContent = `已打开 ${preview.querySelector('#preview-title').textContent}`;
    } catch {
      if (!controller.signal.aborted) window.location.replace(link.href);
    } finally {
      if (request === controller) {
        request = undefined;
        preview.removeAttribute('aria-busy');
      }
    }
  });
}
