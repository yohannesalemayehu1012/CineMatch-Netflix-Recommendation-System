document.addEventListener('DOMContentLoaded', () => {
  const input = document.querySelector('#title-search');
  const box = document.querySelector('#suggestions');
  let timer;
  if (input && box) {
    input.addEventListener('input', () => {
      clearTimeout(timer);
      const q = input.value.trim();
      if (q.length < 2) { box.innerHTML = ''; box.classList.remove('visible'); return; }
      timer = setTimeout(async () => {
        try {
          const response = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
          const items = await response.json();
          box.innerHTML = items.map(item => `<button type="button" class="suggestion-item" data-title="${escapeHtml(item.title)}"><span>${escapeHtml(item.title)}</span><small>${escapeHtml(item.type)}${item.year ? ` · ${item.year}` : ''}</small></button>`).join('');
          box.classList.toggle('visible', items.length > 0);
          box.querySelectorAll('button').forEach(button => button.addEventListener('click', () => {
            input.value = button.dataset.title; box.innerHTML = ''; box.classList.remove('visible'); input.form.requestSubmit();
          }));
        } catch { box.innerHTML = ''; box.classList.remove('visible'); }
      }, 180);
    });
    document.addEventListener('click', event => { if (!event.target.closest('.search-panel')) box.classList.remove('visible'); });
  }
  document.querySelectorAll('.details-toggle').forEach(button => button.addEventListener('click', () => {
    const details = button.nextElementSibling;
    const open = button.getAttribute('aria-expanded') === 'true';
    button.setAttribute('aria-expanded', String(!open)); details.hidden = open;
    button.innerHTML = open ? 'More details <span>＋</span>' : 'Less details <span>−</span>';
  }));
});
function escapeHtml(value) { return String(value).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char])); }
