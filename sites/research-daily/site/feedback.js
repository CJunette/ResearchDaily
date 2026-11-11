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
      <div><span>YOUR NOTES</span><h4>告诉我你的想法</h4></div>
      <p>问题、判断、偏好、反对意见或想继续追的方向都可以直接写。我会在后续早报中归纳，不需要你先分类。</p>
    </div>
    <label class="feedback-note">
      <span>反馈内容</span>
      <textarea rows="5" placeholder="随便写：哪里有意思、哪里不可信、希望多看或少看什么、想让我下次重点解释什么，也可以粘贴你在其他阅读工具中的相关笔记。"></textarea>
    </label>
    <div class="feedback-actions">
      <button class="feedback-submit" type="button">保存反馈 →</button>
      <p class="feedback-status" role="status" aria-live="polite"></p>
    </div>`;
  main.append(panel);

  panel.querySelector('.feedback-submit').addEventListener('click', async () => {
    const submit = panel.querySelector('.feedback-submit');
    const status = panel.querySelector('.feedback-status');
    const note = panel.querySelector('textarea').value.trim();
    if (!note) {
      status.textContent = '请先写下反馈。';
      return;
    }
    submit.disabled = true;
    status.textContent = '正在保存…';
    try {
      const response = await fetch('/api/feedback', {
        method: 'POST',
        headers: {'content-type': 'application/json'},
        body: JSON.stringify({paperId, title, briefDate: feedbackBriefDate(), signal: 'freeform', note, source: 'site'}),
      });
      if (!response.headers.get('content-type')?.includes('application/json')) {
        throw new Error('服务返回异常页面，请刷新登录状态后重试；输入内容已保留。');
      }
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || '保存失败');
      panel.querySelector('textarea').value = '';
      status.textContent = '已保存。我会在后续早报中归纳这条反馈。';
    } catch (error) {
      status.textContent = `未保存：${error.message}`;
    } finally {
      submit.disabled = false;
    }
  });
});
