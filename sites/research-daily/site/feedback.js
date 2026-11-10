const FEEDBACK_SIGNALS = [
  ['interested', '★ 更关注'],
  ['more', '＋ 多来这类'],
  ['less', '− 少来这类'],
  ['question', '? 有问题'],
];

function feedbackPaperId(article) {
  const reviewId = article.querySelector('details[data-review]')?.dataset.review;
  if (reviewId) return reviewId;
  return article.id?.startsWith('paper-') ? article.id.slice(6) : '';
}

function feedbackBriefDate() {
  const archived = location.pathname.match(/\/archive\/(\d{4}-\d{2}-\d{2})\//);
  return archived?.[1] || document.querySelector('.issue')?.textContent.match(/\d{4}-\d{2}-\d{2}/)?.[0] || '2026-11-10';
}

document.querySelectorAll('article.paper').forEach((article) => {
  const main = article.querySelector('.paper-main');
  const paperId = feedbackPaperId(article);
  const title = article.querySelector('h3')?.textContent?.trim() || '';
  if (!main || !paperId || main.querySelector('.feedback-panel')) return;

  const panel = document.createElement('section');
  panel.className = 'feedback-panel';
  panel.dataset.paperId = paperId;
  panel.innerHTML = `
    <div class="feedback-heading">
      <div><span>YOUR SIGNAL</span><h4>这篇文章给你的反馈</h4></div>
      <p>只保存你主动提交的内容，用于调整后续选题与精读重点。</p>
    </div>
    <div class="feedback-signals" role="group" aria-label="反馈类型">
      ${FEEDBACK_SIGNALS.map(([value, label]) => `<button type="button" data-signal="${value}">${label}</button>`).join('')}
    </div>
    <label class="feedback-note">
      <span>你真正关注的问题</span>
      <textarea rows="3" maxlength="4000" placeholder="例如：我更关心它如何处理跨用户泛化；也可以粘贴你在 Gemini 中针对这篇论文提出的问题片段。"></textarea>
    </label>
    <div class="feedback-actions">
      <label><span>内容来源</span><select><option value="site">网页反馈</option><option value="gemini">Gemini 提问片段</option><option value="other">其他笔记</option></select></label>
      <button class="feedback-submit" type="button">保存反馈 →</button>
      <p class="feedback-status" role="status" aria-live="polite"></p>
    </div>`;
  main.append(panel);

  let selectedSignal = 'interested';
  const buttons = panel.querySelectorAll('[data-signal]');
  buttons[0].classList.add('selected');
  buttons.forEach((button) => button.addEventListener('click', () => {
    buttons.forEach((candidate) => candidate.classList.remove('selected'));
    button.classList.add('selected');
    selectedSignal = button.dataset.signal;
  }));

  panel.querySelector('.feedback-submit').addEventListener('click', async () => {
    const submit = panel.querySelector('.feedback-submit');
    const status = panel.querySelector('.feedback-status');
    const note = panel.querySelector('textarea').value.trim();
    const source = panel.querySelector('select').value;
    if ((selectedSignal === 'question' || source === 'gemini') && !note) {
      status.textContent = '请先写下问题或粘贴提问片段。';
      return;
    }
    submit.disabled = true;
    status.textContent = '正在保存…';
    try {
      const response = await fetch('/api/feedback', {
        method: 'POST',
        headers: {'content-type': 'application/json'},
        body: JSON.stringify({paperId, title, briefDate: feedbackBriefDate(), signal: selectedSignal, note, source}),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || '保存失败');
      panel.querySelector('textarea').value = '';
      status.textContent = '已保存。下一期选题会读取这条信号。';
    } catch (error) {
      status.textContent = `未保存：${error.message}`;
    } finally {
      submit.disabled = false;
    }
  });
});
