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
