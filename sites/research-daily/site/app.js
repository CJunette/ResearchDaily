const focusToggle = document.querySelector('#focusToggle');
focusToggle?.addEventListener('click', () => {
  document.body.classList.toggle('focus-mode');
  const active = document.body.classList.contains('focus-mode');
  focusToggle.textContent = active ? '退出专注模式' : '开启专注模式';
  if (active) document.querySelector('#core')?.scrollIntoView();
});

const escapeHTML = (value) => String(value)
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;')
  .replaceAll("'", '&#039;');

document.querySelectorAll('details[data-review]').forEach((item) => {
  const note = window.RESEARCH_REVIEWS?.[item.dataset.review];
  if (!note) return;
  const summary = item.querySelector('summary');
  const contributions = note.contributions
    .map((entry, index) => `<li><span>${String(index + 1).padStart(2, '0')}</span><p>${escapeHTML(entry)}</p></li>`)
    .join('');

  item.innerHTML = '';
  item.append(summary);
  item.insertAdjacentHTML('beforeend', `
    <div class="review-sheet">
      <div class="review-kicker"><span>FULL-TEXT NOTES</span><p>以下判断来自方法、结果、讨论与局限部分的全文核验，不是摘要改写。</p></div>
      <div class="review-pair">
        <section class="review-block"><b>01</b><div><h4>研究问题</h4><p>${escapeHTML(note.problem)}</p></div></section>
        <section class="review-block"><b>02</b><div><h4>方法与样本</h4><p>${escapeHTML(note.method)}</p></div></section>
      </div>
      <section class="review-contributions">
        <div class="review-title"><b>03</b><h4>主要贡献</h4><span>作者实际交付了什么</span></div>
        <ol>${contributions}</ol>
      </section>
      <section class="review-delta">
        <div class="review-title"><b>04</b><h4>相较以往的 delta</h4><span>过去做法 → 本文改变 → 仍需付出的代价</span></div>
        <p>${escapeHTML(note.delta)}</p>
      </section>
      <div class="review-pair judgement">
        <section class="review-block evidence"><b>05</b><div><h4>证据够不够</h4><p>${escapeHTML(note.evidence)}</p></div></section>
        <section class="review-block limitations"><b>06</b><div><h4>局限与不可外推之处</h4><p>${escapeHTML(note.limitations)}</p></div></section>
      </div>
      <div class="review-bottom">
        <section><span>WHY READ</span><h4>为什么值得你读</h4><p>${escapeHTML(note.whyRead)}</p></section>
        <section><span>READING PATH</span><h4>如果打开原文，优先看这里</h4><p>${escapeHTML(note.readingPath)}</p></section>
      </div>
    </div>`);
});

document.querySelectorAll('details').forEach((item) => {
  item.addEventListener('toggle', () => {
    if (!item.open) return;
    const section = item.closest('.paper-section');
    section?.querySelectorAll('details[open]').forEach((other) => {
      if (other !== item) other.open = false;
    });
  });
});
